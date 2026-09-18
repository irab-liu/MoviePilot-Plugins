"""
猫眼热度榜 - MoviePilot V3 插件
猫眼网播【电视剧+网剧】热度 TOP30 剧集订阅情况，一键订阅。
"""

import json
import random
import re
import time
import hashlib
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.sdk.network import RequestUtils
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import Body
from app.chain.subscribe import SubscribeChain
from app.db.oper.mediaserver import MediaServerOper
from app.db.oper.subscribe import SubscribeOper
from app.db.oper.transferhistory import TransferHistoryOper
from app.modules.themoviedb.tmdbapi import TmdbApi
from app.plugins import _PluginBase
from app.sdk.events import Event, eventmanager
from app.sdk.logging import logger
from app.schemas.types import EventType, MediaType

def _create_meta_info(title: str):
    """创建 MoviePilot V3 MetaInfo，兼容 TMDB chain/cache。"""
    try:
        from app.schemas import MetaInfo
    except Exception as e:
        logger.warning("导入 MoviePilot MetaInfo 失败: %s", e)
        return None

    try:
        try:
            meta = MetaInfo(name=title, type=MediaType.TV)
        except Exception:
            meta = MetaInfo()

        for key, value in {
            "name": title,
            "title": title,
            "original_name": title,
            "type": MediaType.TV,
        }.items():
            try:
                setattr(meta, key, value)
            except Exception:
                try:
                    object.__setattr__(meta, key, value)
                except Exception:
                    pass

        return meta
    except Exception as e:
        logger.warning("创建 MoviePilot MetaInfo 失败: %s", e)
        return None



class MaoyanScraper:
    """猫眼网播热度数据抓取器"""

    HEAT_URL = "https://piaofang.maoyan.com/web-heat"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    @classmethod
    def fetch_heat_list(cls) -> List[Dict[str, Any]]:
        """抓取并解析猫眼网播热度榜，返回最多 30 条标准化记录。

        Raises:
            ConnectionError: 猫眼页面请求失败。
            ValueError: 页面中不存在可解析的 ``AppData`` 数据。
        """
        logger.info("开始抓取猫眼热度列表: %s", cls.HEAT_URL)
        resp = RequestUtils(headers=cls.HEADERS, timeout=15).get_res(cls.HEAT_URL)
        if resp is None or not resp.ok:
            raise ConnectionError(f"猫眼热度列表请求失败: HTTP {resp.status_code if resp else 'None'}")
        resp.encoding = "utf-8"
        logger.info("HTTP %s, 内容长度 %d bytes", resp.status_code, len(resp.text))

        match = re.search(r'AppData\s*=\s*(\{.*?\});', resp.text, re.DOTALL)
        if not match:
            logger.error("未能从猫眼页面匹配 AppData 数据")
            raise ValueError("未能从猫眼页面提取 AppData 数据")

        data = json.loads(match.group(1))
        heat_data = data.get("pageData", {}).get("webHeatData", [])
        logger.info("成功解析 webHeatData，共 %d 条", len(heat_data))

        results = []
        for idx, item in enumerate(heat_data[:30]):
            series = item.get("seriesInfo", {})
            play_unit = item.get("playCountSplitUnit", {})
            plays = ""
            if play_unit:
                plays = f"{play_unit.get('num', '')}{play_unit.get('unit', '')}"
            results.append({
                "rank": idx + 1,
                "name": series.get("name", ""),
                "platform": series.get("platformDesc", ""),
                "days": series.get("releaseInfo", ""),
                "heat": item.get("currHeat", 0),
                "plays": plays,
                "tmdbid": 0,
            })
        return results


class TmdbHelper:
    """TMDB 数据辅助器（使用 MoviePilot 内置 TMDB API）"""

    # 中文数字 -> 阿拉伯数字，用于解析「第二季」形态的季号
    _CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
               "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}

    @classmethod
    def strip_season(cls, name: str) -> tuple:
        """剥离标题中的季数后缀，返回 (主标题, 季号)。

        宿主 ``_project_search_results`` 只做单向子串过滤（要求传入标题是 TMDB
        返回名称的子串），而 TMDB 主记录名不含季数，因此「问心2」这类片名必然
        搜不到。这里先剥离季数再搜索，季号供后续季别开播日期判定使用。

        - "问心2"       -> ("问心", 2)
        - "问心 第2季"  -> ("问心", 2)
        - "问心第二季"  -> ("问心", 2)
        - "问心 Season 2" -> ("问心", 2)
        - "问心III"     -> ("问心", 3)
        - "说唱巅峰对决2026" -> ("说唱巅峰对决", 0)   年份不算季号
        - "云雀叫天录"  -> ("云雀叫天录", 0)
        """
        text = (name or "").strip()
        if not text:
            return "", 0

        # 1. 中文「第X季」：第2季 / 第二季 / 第 2 季（同时覆盖期/辑/部/集）
        match = re.search(r"[\s\-·]*第\s*([一二三四五六七八九十\d]+)\s*[季期辑部集]\s*$", text)
        if match:
            return text[: match.start()].strip(), cls._to_season(match.group(1))

        # 2. 英文「Season X」/「Series X」/「S2」
        match = re.search(r"[\s\-·]*(?:season|series|s)\s*(\d{1,2})\s*$", text, re.IGNORECASE)
        if match:
            return text[: match.start()].strip(), int(match.group(1))

        # 3. 罗马数字后缀：III / 问心III / 问心 II（单字母需带分隔符，避免误伤片名）
        match = re.search(r"([\s\-·]+)([IVX]{1,5})\s*$", text)
        if match:
            value = cls._roman_to_int(match.group(2))
            if value:
                return text[: match.start()].strip(), value
        match = re.search(r"([IVX]{2,5})\s*$", text)
        if match:
            head = text[: match.start()].strip()
            # 主标题需含非罗马字符，否则整个片名都是罗马数字（如 "XXXIII"），不应剥离
            if head and re.search(r"[^IVX\s]", head):
                value = cls._roman_to_int(match.group(1))
                if value:
                    return head, value

        # 4. 尾部 4 位年份（19xx/20xx）：剥离以便搜索，但不视为季号
        match = re.search(r"[\s\-·]*((?:19|20)\d{2})\s*$", text)
        if match:
            head = text[: match.start()].strip()
            if head:
                return head, 0

        # 5. 纯数字后缀：问心2 -> (问心, 2)；限定 1~2 位，避免把年份当季号
        match = re.search(r"[\s\-·]*(\d{1,2})\s*$", text)
        if match:
            head = text[: match.start()].strip()
            if head:
                return head, int(match.group(1))

        return text, 0

    @classmethod
    def _to_season(cls, token: str) -> int:
        """把「二」/「2」形式的季号转为整数；无法识别返回 0。"""
        token = (token or "").strip()
        if not token:
            return 0
        if token.isdigit():
            return int(token)
        if len(token) == 1:
            return cls._CN_NUM.get(token, 0)
        # 十一 ~ 十九
        if token.startswith("十") and len(token) == 2:
            return 10 + cls._CN_NUM.get(token[1], 0)
        if token.endswith("十") and len(token) == 2:
            return cls._CN_NUM.get(token[0], 0) * 10
        return 0

    @classmethod
    def _roman_to_int(cls, token: str) -> int:
        """罗马数字转整数；非法输入返回 0。"""
        values = {"I": 1, "V": 5, "X": 10}
        total, prev = 0, 0
        for char in reversed((token or "").upper()):
            if char not in values:
                return 0
            value = values[char]
            if value < prev:
                total -= value
            else:
                total += value
            prev = value
        return total

    @staticmethod
    def search_tv(name: str) -> Optional[Dict[str, Any]]:
        """按剧名搜索 TMDB，返回首条匹配结果；失败或无结果时返回 ``None``。

        原名搜不到时，剥离季数后缀重搜一次（如「问心2」-> 「问心」），
        命中后回填 ``season`` 字段，供季别开播日期判定使用。
        """
        try:
            api = TmdbApi(language="zh")
        except Exception as e:
            logger.error("TMDB客户端初始化失败: %s", e)
            return None

        try:
            result = api.search_tvs(name, "")
            if result and len(result) > 0:
                logger.debug("TMDB搜索 '%s' → ID %s", name, result[0].get("id"))
                return result[0]
        except Exception as e:
            logger.error("TMDB搜索 '%s' 失败: %s", name, e)
            return None

        # 原名无结果：剥离季数后缀重试
        base, season = TmdbHelper.strip_season(name)
        if base and base != name:
            try:
                logger.info("TMDB搜索 '%s' 无结果，改以主标题 '%s' 重试（季号=%s）", name, base, season)
                result = api.search_tvs(base, "")
                if result and len(result) > 0:
                    hit = dict(result[0])
                    hit["_season"] = season
                    logger.info("TMDB搜索 '%s' → 主标题 '%s' 命中 ID %s",
                                name, base, hit.get("id"))
                    return hit
            except Exception as e:
                logger.error("TMDB搜索 '%s'（主标题 '%s'）失败: %s", name, base, e)
                return None

        logger.warning("TMDB搜索 '%s' 无结果", name)
        return None

    @staticmethod
    def get_poster_url(poster_path: str) -> str:
        """将 TMDB 海报相对路径转换为 MP 代理 URL；空路径返回空字符串。"""
        if not poster_path:
            return ""
        if poster_path.startswith("http"):
            # TMDB URL → proxy through MP
            if "image.tmdb.org" in poster_path:
                return f"/api/v1/system/img/1?imgurl={poster_path}"
            # Non-TMDB URL → pass through
            return poster_path
        return f"/api/v1/system/img/1?imgurl=https://image.tmdb.org/t/p/w500{poster_path}"


class _WeComMpnews:
    """企业微信 mpnews 图文消息发送器。

    复用宿主「企业微信」通知渠道的应用凭证与 access_token，自行实现
    ``media/upload`` 素材上传与 ``message/send`` 图文消息推送。
    不经过宿主通知链，因此只影响调用方指定的这一条消息。
    """

    # 企业微信接口路径（与宿主 app/modules/wechat/wechat.py 保持一致）
    _TOKEN_PATH = "cgi-bin/gettoken?corpid={corpid}&corpsecret={corpsecret}"
    _UPLOAD_PATH = "cgi-bin/media/upload?access_token={access_token}&type=image"
    _SEND_PATH = "cgi-bin/message/send?access_token={access_token}"
    # 临时素材有效期 3 天，留出余量按 2 天缓存缩略图 media_id
    _THUMB_TTL = 2 * 86400
    # 宿主 token 剩余有效期不可知，复用后保守续用 30 分钟
    _REUSE_TTL = 1800
    # 正文长度保守上限（官方上限未实证，仅作防爆保护）
    _CONTENT_LIMIT = 500000

    def __init__(self, owner, config: dict):
        """从通知渠道配置中解析企业微信应用凭证。

        :param owner: 插件实例，用于读写缩略图素材缓存。
        :param config: 宿主企业微信渠道的 ``config`` 字典。
        """
        config = config or {}
        self._owner = owner
        self._corpid = config.get("WECHAT_CORPID")
        self._appsecret = config.get("WECHAT_APP_SECRET")
        self._agentid = config.get("WECHAT_APP_ID")
        self._proxy = config.get("WECHAT_PROXY") or "https://qyapi.weixin.qq.com"
        self._targets = config.get("WECHAT_ADMINS")
        self._access_token = None
        self._access_token_expire_at = 0.0

    def send(self, title: str, text: str, image: Optional[str] = None,
             items: Optional[List[dict]] = None) -> bool:
        """推送一条 mpnews 图文消息。

        :param items: 结构化条目（含演员/详情/状态）；提供时正文按富文本渲染。
        :return: 是否发送成功；任一步失败返回 False，由调用方回退宿主通知渠道。
        """
        if not (self._corpid and self._appsecret and self._agentid):
            logger.error("【企微图文】企业微信配置不完整（缺少 Corpid/AppSecret/AgentId），跳过")
            return False

        thumb_media_id = self._upload_thumb(image) if image else None
        if not thumb_media_id:
            logger.warning("【企微图文】封面素材不可用，mpnews 无法发送")
            return False

        req_json = {
            "touser": "|".join(self._split_ids(self._targets)) or "@all",
            "msgtype": "mpnews",
            "agentid": self._agentid,
            "mpnews": {
                "articles": [
                    {
                        "title": title or "猫眼热度榜",
                        "thumb_media_id": thumb_media_id,
                        "author": "MoviePilot",
                        "content": self._build_content(text, items),
                        "digest": self._build_digest(text, items),
                    }
                ]
            },
            "safe": 0,
            "enable_id_trans": 0,
            "enable_duplicate_check": 0,
        }

        result = self._post_json(self._SEND_PATH, req_json)
        # token 过期：强制重取后重试一次
        if result is not None and result.get("errcode") == 42001:
            logger.warning("【企微图文】access_token 已过期，强制重取后重试")
            self._access_token = None
            self._access_token_expire_at = 0.0
            if not self._fetch_access_token():
                return False
            result = self._post_json(self._SEND_PATH, req_json)

        if result is None:
            return False
        if result.get("errcode") != 0:
            logger.error("【企微图文】发送失败：errcode=%s, errmsg=%s",
                         result.get("errcode"), result.get("errmsg"))
            return False
        logger.info("【企微图文】mpnews 已发送，接收人=%s", req_json["touser"])
        return True

    @staticmethod
    def _split_ids(raw) -> List[str]:
        """解析逗号/竖线分隔的成员 ID 列表。"""
        items = str(raw or "").replace("|", ",").split(",")
        return [item.strip() for item in items if item.strip()]

    @staticmethod
    def _escape_html(text: str) -> str:
        """转义 HTML 特殊字符，避免剧名/演员名里的尖括号破坏结构。"""
        return (str(text or "")
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))

    @classmethod
    def _build_content(cls, text: str, items: Optional[List[dict]] = None) -> str:
        """构造 mpnews 正文 HTML。

        :param text: 纯文本正文。有结构化条目时取其首行作为引导语（如 TOP5 提示），
            避免调用方写在 text 里的说明被丢弃；无条目时整段作为正文。
        :param items: 结构化条目；每条渲染为「标题 + 评分/首播/集数/类型/主演/简介」多行区块。
        """
        # 引导语：text 里除条目行之外的说明文字（如「今日无新增，为您推荐…」）
        lead = cls._extract_lead(text) if items else ""

        if not items:
            lines = [cls._escape_html(line).strip() for line in (text or "").split("\n")]
            return "<br/>".join(lines).strip()[: cls._CONTENT_LIMIT]

        blocks = []
        if lead:
            blocks.append(f"<p>{cls._escape_html(lead)}</p>")
        for idx, item in enumerate(items, start=1):
            blocks.append(cls._render_item(item, idx))
        body = "".join(blocks)
        return body.strip()[: cls._CONTENT_LIMIT]

    @staticmethod
    def _extract_lead(text: str) -> str:
        """提取正文里的引导语：跳过条目行（以 📺 或序号开头），返回其余首行说明。"""
        for line in (text or "").split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("📺") or re.match(r"^\d+[.、]", stripped):
                continue
            return stripped
        return ""

    @classmethod
    def _render_item(cls, item: dict, index: int) -> str:
        """渲染单个条目区块：标题一行，之后每个字段各占一行。"""
        name = cls._escape_html(item.get("name", ""))
        rank = item.get("rank") or index
        platform = cls._escape_html(item.get("platform", ""))
        status = cls._escape_html(item.get("status_tag", "") or "")

        title = f"{rank}. 《{name}》"
        if platform:
            title += f"（{platform}）"
        parts = [f"<p><strong>{title}</strong>"]
        if status:
            parts[0] += f" <span style=\"color:#c0392b\">{status}</span>"
        parts[0] += "</p>"

        # 每个字段独立一行，便于手机端阅读
        for line in cls._render_detail_lines(item):
            parts.append(f"<p style=\"color:#555;font-size:13px\">{line}</p>")
        return "".join(parts)

    @classmethod
    def _render_detail_lines(cls, item: dict) -> List[str]:
        """按「标签：值」构造逐行详情：评分 / 首播 / 集数 / 类型 / 主演 / 简介。"""
        lines = []

        vote = item.get("vote_average")
        try:
            if vote:
                lines.append(f"评分：{float(vote):.1f}")
        except (TypeError, ValueError):
            pass

        air_date = item.get("first_air_date")
        if air_date:
            lines.append(f"首播：{cls._escape_html(air_date)}")

        seasons = item.get("number_of_seasons")
        episodes = item.get("number_of_episodes")
        season = item.get("season") or 0
        if season and episodes:
            # 带季数：只报该季集数，避免显示全季合计造成误导
            lines.append(f"集数：第 {season} 季 共 {episodes} 集")
        elif seasons and episodes:
            lines.append(f"集数：{seasons} 季 {episodes} 集")
        elif episodes:
            lines.append(f"集数：共 {episodes} 集")

        genres = item.get("genres") or []
        if genres:
            names = [g.get("name") if isinstance(g, dict) else str(g) for g in genres]
            names = [n for n in names if n]
            if names:
                lines.append(f"类型：{cls._escape_html('、'.join(names))}")

        actors = item.get("actors") or []
        if actors:
            actor_text = cls._escape_html("、".join(str(a) for a in actors))
            lines.append(f"主演：{actor_text}")

        overview = item.get("overview")
        if overview:
            text = str(overview).replace("\n", " ").strip()
            if text:
                lines.append(f"简介：{cls._escape_html(text)}")

        return lines

    @classmethod
    def _build_digest(cls, text: str, items: Optional[List[dict]] = None) -> str:
        """摘要：与正常（非 mpnews）图文消息的正文保持一致。

        企业微信聊天列表展示「封面 + 标题 + 摘要」，用户要求摘要与宿主通知
        正文完全一致（同样的 📺、序号、平台、订阅状态），因此这里直接沿用
        ``text``，不做二次加工。

        仅做保守的字节截断：mpnews 的 digest 长度上限未能从官方文档实证，
        按 500 字节封顶并保证不切断多字节字符，避免整条消息被拒。
        """
        digest = (text or "").strip()
        encoded = digest.encode("utf-8")
        if len(encoded) <= 500:
            return digest
        # 按字节截断到 500 以内，且不切断多字节字符
        return encoded[:500].decode("utf-8", errors="ignore").strip()

    def _url(self, endpoint: str) -> str:
        """按渠道配置的 WECHAT_PROXY 组合出完整接口地址。"""
        try:
            from app.sdk.network import UrlUtils
            return UrlUtils.adapt_request_url(self._proxy, endpoint) or endpoint
        except Exception:
            return f"{self._proxy.rstrip('/')}/{endpoint.lstrip('/')}"

    def _get_access_token(self) -> Optional[str]:
        """获取 access_token：优先复用宿主已缓存的 token，失败才自行获取。"""
        now = time.time()
        if self._access_token and now < self._access_token_expire_at:
            return self._access_token
        token = self._host_access_token()
        if token:
            self._access_token = token
            self._access_token_expire_at = now + self._REUSE_TTL
            return token
        return self._fetch_access_token()

    def _host_access_token(self) -> Optional[str]:
        """从宿主运行中的企业微信实例读取已缓存的 access_token。

        自行调用 gettoken 会顶掉宿主 token，导致宿主通知间歇性失败，故优先复用。
        """
        try:
            from app.sdk.services import NotificationHelper
            services = NotificationHelper().get_services(type_filter="wechat")
            for service in services.values():
                config = getattr(service.config, "config", None) or {}
                if config.get("WECHAT_CORPID") != self._corpid:
                    continue
                token = getattr(getattr(service, "instance", None), "_access_token", None)
                if token:
                    logger.debug("【企微图文】复用宿主 access_token")
                    return token
        except Exception as e:
            logger.debug("【企微图文】读取宿主 access_token 失败: %s", e)
        return None

    def _fetch_access_token(self) -> Optional[str]:
        """自行获取 access_token（复用失败时的兜底，会顶掉宿主 token）。"""
        if not (self._corpid and self._appsecret):
            return None
        try:
            resp = RequestUtils(timeout=15).get_res(
                self._url(self._TOKEN_PATH.format(corpid=self._corpid, corpsecret=self._appsecret))
            )
            if resp is None or not resp.ok:
                logger.error("【企微图文】获取 access_token 失败：HTTP %s",
                             resp.status_code if resp else None)
                return None
            data = resp.json()
            if data.get("errcode") != 0:
                logger.error("【企微图文】获取 access_token 失败：errcode=%s, errmsg=%s",
                             data.get("errcode"), data.get("errmsg"))
                return None
            self._access_token = data.get("access_token")
            self._access_token_expire_at = time.time() + max(
                int(data.get("expires_in", 7200)) - 300, 60
            )
            logger.info("【企微图文】已自行获取 access_token（expires_in=%s）", data.get("expires_in"))
            return self._access_token
        except Exception as e:
            logger.error("【企微图文】获取 access_token 异常: %s", e)
            return None

    def _upload_thumb(self, image_url: str) -> Optional[str]:
        """下载封面并上传为企业微信临时素材，返回 thumb_media_id（带 2 天缓存）。"""
        cache_key = "maoyandingyue_mpthumb_" + hashlib.md5(
            image_url.encode("utf-8")
        ).hexdigest()[:12]
        try:
            cached = self._owner.get_data(cache_key)
            if isinstance(cached, dict) and time.time() - cached.get("ts", 0) < self._THUMB_TTL:
                media_id = cached.get("media_id")
                if media_id:
                    logger.debug("【企微图文】缩略图素材命中缓存")
                    return media_id
        except Exception:
            pass

        content, filename, mime = self._download_image(image_url)
        if not content:
            return None
        token = self._get_access_token()
        if not token:
            return None
        try:
            resp = RequestUtils(timeout=60).request(
                method="post",
                url=self._url(self._UPLOAD_PATH.format(access_token=token)),
                headers={"Accept": "application/json"},
                files={"media": (filename, content, mime)},
            )
            if resp is None or not resp.ok:
                logger.error("【企微图文】上传缩略图素材失败：HTTP %s",
                             resp.status_code if resp else None)
                return None
            data = resp.json()
            if data.get("errcode") != 0:
                logger.error("【企微图文】上传缩略图素材失败：errcode=%s, errmsg=%s",
                             data.get("errcode"), data.get("errmsg"))
                return None
            media_id = data.get("media_id")
            if not media_id:
                return None
            try:
                self._owner.save_data(cache_key, {"media_id": media_id, "ts": time.time()})
            except Exception:
                pass
            logger.info("【企微图文】缩略图素材已上传：media_id=%s", media_id)
            return media_id
        except Exception as e:
            logger.error("【企微图文】上传缩略图素材异常: %s", e)
            return None

    @staticmethod
    def _host_proxies() -> Optional[dict]:
        """读取宿主配置的系统代理（与宿主 TMDB 客户端同源）。

        国内直连 image.tmdb.org 常被拒（Connection refused），必须跟随宿主
        的 PROXY_HOST / 环境变量代理，否则封面下载必然失败。
        """
        try:
            from app.runtime.settings import get_runtime_setting
            proxies = get_runtime_setting("PROXY", None)
            if isinstance(proxies, dict) and proxies:
                return proxies
        except Exception as e:
            logger.debug("【企微图文】读取宿主代理配置失败: %s", e)
        return None

    def _download_image(self, image_url: str):
        """获取封面图片字节，返回 (字节内容, 文件名, MIME)；失败返回 (None, None, None)。

        两级取图，避免不必要的网络请求：

        1. 宿主图片管道（``ImageHelper``）：先读磁盘缓存（region=``images``）。
           海报在前端展示时已由宿主图片代理写入该缓存，命中即零网络请求；
           未命中时由宿主自行按配置的代理下载并回填缓存。
        2. 兜底直连：宿主管道不可用时，自行携带宿主代理下载。

        注意：宿主管道带 ``Accept: image/avif,image/webp,*/*``，TMDB 会按内容协商
        返回 **WebP**；而企业微信素材只接受 JPG/PNG，直接上传会报 40123
        （invalid image format）。因此这里统一做一次格式规整。
        """
        via_host = self._image_from_host_pipeline(image_url)
        if via_host:
            return self._normalize_image(*via_host)
        return self._normalize_image(*self._download_image_direct(image_url))

    @staticmethod
    def _detect_image_format(content: bytes) -> str:
        """按文件头识别真实图片格式。

        返回 'jpeg'/'png'/'webp'/'avif'/'gif'/'bmp'/''。

        注意 AVIF 属 ISO BMFF 容器：``[4:8] == b'ftyp'``，major brand 在 ``[8:12]``。
        宿主管道的 Accept 头把 ``image/avif`` 排在首位，TMDB 会优先返回 AVIF，
        必须识别，否则会以错误 MIME 上传被企微拒绝（40123）。
        """
        if not content:
            return ""
        if content[:3] == b"\xff\xd8\xff":
            return "jpeg"
        if content[:8] == b"\x89PNG\r\n\x1a\n":
            return "png"
        if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
            return "webp"
        if content[4:8] == b"ftyp" and content[8:12] in (b"avif", b"avis"):
            return "avif"
        if content[:6] in (b"GIF87a", b"GIF89a"):
            return "gif"
        if content[:2] == b"BM":
            return "bmp"
        return ""

    @classmethod
    def _normalize_image(cls, content, filename, mime):
        """把任意图片字节规整为企业微信可接受的 JPG/PNG。

        AVIF/WebP/GIF/BMP 等格式用 Pillow 转成 JPEG（宿主已装 pillow +
        pillow-avif-plugin，可解 AVIF）；转换不可用时返回 (None, None, None)，
        宁可放弃本次 mpnews（由调用方回退宿主通知），也不要发错格式被企微拒绝。
        """
        if not content:
            return None, None, None
        fmt = cls._detect_image_format(content)
        if fmt in ("jpeg", "png"):
            # 已是企微可接受格式，按真实格式给出文件名/MIME
            if fmt == "png":
                return content, "cover.png", "image/png"
            return content, "cover.jpg", "image/jpeg"
        if not fmt:
            logger.warning("【企微图文】封面格式无法识别（%s bytes），按原样尝试", len(content))
            return content, filename or "cover.jpg", mime or "image/jpeg"
        # WebP/GIF/BMP -> JPEG
        try:
            import io
            from PIL import Image
            with Image.open(io.BytesIO(content)) as img:
                rgb = img.convert("RGB")
                buf = io.BytesIO()
                rgb.save(buf, format="JPEG", quality=90)
                converted = buf.getvalue()
            logger.info("【企微图文】封面格式 %s 已转为 JPEG（%d -> %d bytes）",
                        fmt, len(content), len(converted))
            return converted, "cover.jpg", "image/jpeg"
        except Exception as e:
            logger.warning("【企微图文】封面格式 %s 转换失败: %s", fmt, e)
            return None, None, None

    @staticmethod
    def _image_from_host_pipeline(image_url: str):
        """经宿主图片管道取图（缓存优先，回退宿主代理）。"""
        try:
            from app.application.image import ImageHelper
            result = ImageHelper().fetch_image_with_mime_type(
                url=image_url, proxy=None, use_cache=True,
            )
        except Exception as e:
            logger.debug("【企微图文】宿主图片管道不可用，改用直连下载: %s", e)
            return None
        if not result or not result[0]:
            return None
        content, mime = result
        logger.info("【企微图文】封面取自宿主图片缓存/代理：%d bytes, %s", len(content), mime)
        return content, "cover.jpg", mime or "image/jpeg"

    def _download_image_direct(self, image_url: str):
        """兜底：自行携带宿主代理下载封面，返回 (字节, 文件名, MIME)。

        显式声明 ``Accept: image/jpeg,image/png``，避免拿到 WebP/AVIF
        （企业微信素材只接受 JPG/PNG）。
        """
        proxies = self._host_proxies()
        try:
            resp = RequestUtils(
                timeout=30,
                proxies=proxies,
                headers={"Accept": "image/jpeg,image/png,image/*;q=0.8"},
            ).get_res(image_url)
            if resp is None or not resp.ok or not resp.content:
                logger.warning("【企微图文】封面下载失败: %s（代理=%s）",
                               image_url, bool(proxies))
                return None, None, None
            content = resp.content
        except Exception as e:
            logger.warning("【企微图文】封面下载异常: %s（代理=%s）", e, bool(proxies))
            return None, None, None
        fmt = self._detect_image_format(content)
        if fmt == "png":
            return content, "cover.png", "image/png"
        if fmt == "jpeg":
            return content, "cover.jpg", "image/jpeg"
        # 其它格式交由 _normalize_image 统一转换
        return content, "cover.bin", "application/octet-stream"

    def _post_json(self, path: str, req_json: dict) -> Optional[dict]:
        """携带 access_token 向企业微信 POST JSON，返回解析后的响应体。"""
        token = self._get_access_token()
        if not token:
            return None
        try:
            resp = RequestUtils(content_type="application/json", timeout=20).post_res(
                url=self._url(path.format(access_token=token)),
                data=json.dumps(req_json, ensure_ascii=False).encode("utf-8"),
            )
            if resp is None or not resp.ok:
                logger.error("【企微图文】请求失败：HTTP %s", resp.status_code if resp else None)
                return None
            return resp.json()
        except Exception as e:
            logger.error("【企微图文】请求异常: %s", e)
            return None


class MaoyanDianYing(_PluginBase):
    _render_mode_logged = False
    """猫眼热度榜插件主类"""

    plugin_name = "猫眼热度榜"
    plugin_desc = "猫眼网播【电视剧+网剧】热度 TOP30 剧集订阅情况，一键订阅。v2.0.2：新增「使用图文消息推送」开关（企业微信 mpnews，正文含演员/详情/状态）；修复带季数片名（如「问心2」）识别失败，并按季别开播日判定上新。"
    plugin_icon = "Moviepilot_A.png"
    plugin_version = "2.0.2"
    plugin_author = "irab"
    author_url = "https://github.com/irab-liu"
    plugin_config_prefix = "maoyandingyue_"
    plugin_order = 50
    auth_level = 1

    _enabled = False
    _mpnews_enabled = False  # 是否改用企业微信 mpnews 图文消息推送
    _cache_key = "maoyandingyue_data"
    _refresh_interval = 6  # 默认6小时自动刷新
    _subscribe_oper = None
    _media_oper = None
    _fetch_lock = threading.Lock()
    _warmup_lock = threading.Lock()
    _warmup_done = False
    _tmdb_cache_prefix = "maoyandingyue_tmdb_"
    _status_cache_ttl = 1800  # Status Check 短 TTL 缓存（秒）
    _detail_cache_ttl = 7 * 86400  # TV 详情缓存 TTL（7天）
    _tmdb_cache_ttl = 7 * 86400  # TMDB 搜索二级缓存 TTL（7天），避免永久积累

    def init_plugin(self, config: dict | None = None) -> None:
        """读取配置并建立本次运行所需状态。"""
        config = config or {}
        logger.debug("【init_plugin】收到的配置: %s", config)
        self._enabled = bool(config.get("enabled", False))
        self._refresh_interval = int(config.get("refresh_interval", 6))
        self._reminder_enabled = bool(config.get("reminder_enabled", False))
        self._reminder_msgtype = config.get("reminder_msgtype", "Plugin")
        self._mpnews_enabled = bool(config.get("mpnews_enabled", False))
        self._subscribe_oper = SubscribeOper()
        self._media_oper = MediaServerOper()
        self._transfer_oper = TransferHistoryOper()
        logger.info("插件初始化完成，enabled=%s, refresh_interval=%sh", self._enabled, self._refresh_interval)

        # 立即运行一次提醒（开关方式）
        if config.get("run_remind"):
            try:
                self.__send_remind(force=True)
            except Exception as e:
                logger.error("【init_plugin】立即运行提醒失败: %s", e)
            self.update_config({**config, "run_remind": False})

        if self._enabled:
            self.__start_warmup()
            cached = super().get_data(self._cache_key)
            if not cached or not isinstance(cached, dict) or not cached.get("rows"):
                logger.info("【启用后抓取】未发现有效缓存，启动首次后台抓取")
                threading.Thread(
                    target=self._auto_refresh,
                    name="MaoyanDianYing.InitialRefresh",
                    daemon=True,
                ).start()
            else:
                logger.info("【启用后抓取】发现已有缓存，共 %d 条，不重复抓取", len(cached.get("rows", [])))

    def __start_warmup(self):
        """启动 daemon 线程执行预热，避免阻塞插件加载"""
        if self._warmup_done:
            return
        with self._warmup_lock:
            if self._warmup_done:
                return
            self._warmup_done = True
        thread = threading.Thread(
            target=self.__warmup,
            daemon=True,
            name="maoyandingyue_warmup"
        )
        thread.start()
        logger.info("【预热】线程已启动")

    def __warmup(self):
        """
        预热：抓取榜单并缓存 TMDB 搜索结果。
        纯同步实现，在 daemon 线程中运行，不依赖事件循环。
        """
        logger.info("【预热】开始...")
        try:
            heat_list = MaoyanScraper.fetch_heat_list()
            if not heat_list:
                logger.warning("【预热】榜单数据为空，跳过")
                return
            cached_count = 0
            for idx, item in enumerate(heat_list):
                title = item.get("name", "")
                if not title:
                    continue
                cache_key = self.__tmdb_cache_key(title)
                if self.get_data(cache_key):
                    continue
                try:
                    # 直接通过 TMDB 官方 API 搜索电视剧，避免走全局链触发 ImdbModule 异常
                    tv = TmdbHelper.search_tv(title)
                    if tv and tv.get("id"):
                        tmdb_id = tv["id"]
                        logger.info("【TMDB确认】%s ID=%s", title, tmdb_id)
                        detail = self.__get_detail_with_cache(tmdb_id)
                        result = {
                            "id": tmdb_id,
                            "name": (detail or {}).get("name") or tv.get("name") or title,
                            "poster_path": (detail or {}).get("poster_path") or tv.get("poster_path"),
                            "backdrop_path": (detail or {}).get("backdrop_path") or tv.get("backdrop_path"),
                            "first_air_date": (detail or {}).get("first_air_date") or tv.get("first_air_date"),
                            "media_type": "TV",
                        }
                        # 季号只取「剥季重搜」路径的回填值：原名直接命中说明 TMDB
                        # 条目名就含该数字（如「我们的少年时代2」是独立剧集），
                        # 不能把片名里的数字当季号，否则会去查不存在的季。
                        season = tv.get("_season") or 0
                        if season:
                            result["season"] = season
                        self.__save_cached_tmdb(title, result)
                        cached_count += 1
                    else:
                        logger.warning("【TMDB未命中】剧名 '%s' 在 TMDB 未找到匹配项", title)
                except Exception as e:
                    logger.warning("【预热】TMDB 搜索失败 [%s]: %s", title, e)
            logger.info("【预热】完成，缓存 %d 条 TMDB 结果", cached_count)
        except Exception as e:
            logger.error("【预热】异常: %s", e)

    @staticmethod
    def __tmdb_cache_key(title: str) -> str:
        """生成 TMDB 二级缓存 key"""
        md5 = hashlib.md5(title.encode("utf-8")).hexdigest()[:12]
        return f"maoyandingyue_tmdb_{md5}"

    @staticmethod
    def __tmdb_result_to_serializable(tmdb_info: dict) -> dict:
        """将 TMDB 搜索结果转换为 JSON 可序列化 dict（处理 MediaType 枚举）"""
        if not tmdb_info:
            return tmdb_info
        result = dict(tmdb_info)
        if "media_type" in result and hasattr(result["media_type"], "value"):
            result["media_type"] = result["media_type"].value
        return result

    def __get_cached_tmdb(self, title: str) -> Optional[dict]:
        """从二级缓存读取 TMDB 数据（7 天 TTL；旧版无 ts 字段的数据视为过期，避免永久积累）"""
        cache_key = self.__tmdb_cache_key(title)
        try:
            cached = self.get_data(cache_key)
            if cached and isinstance(cached, dict):
                ts = cached.get("ts")
                if ts is not None and time.time() - ts < self._tmdb_cache_ttl:
                    return cached
        except Exception:
            pass
        return None

    def __save_cached_tmdb(self, title: str, tmdb_info: dict) -> None:
        """保存 TMDB 数据到二级缓存（带 ts 时间戳，7 天 TTL）"""
        cache_key = self.__tmdb_cache_key(title)
        try:
            data = self.__tmdb_result_to_serializable(tmdb_info)
            if isinstance(data, dict):
                data["ts"] = time.time()
            self.save_data(cache_key, data)
        except Exception:
            pass

    def __search_tmdb_with_cache(self, title: str) -> Optional[dict]:
        """带二级缓存的 TMDB 搜索（优先直接使用 TmdbHelper 查询官方 TMDB）"""
        cached = self.__get_cached_tmdb(title)
        if cached:
            # 老缓存可能缺 season（本字段后加）。仅当"原名搜不到、需剥季重搜"时
            # 才补算季号，避免把片名自带数字（如「我们的少年时代2」）误判为季号。
            if cached.get("id") and "season" not in cached:
                base, season = TmdbHelper.strip_season(title)
                if season and base != title:
                    cached["season"] = season
                    self.__save_cached_tmdb(title, cached)
                    logger.info("【TMDB缓存】'%s' 补算季号=%s（主标题 '%s'）",
                                title, season, base)
            if cached.get("id") and (not cached.get("poster_path") or not cached.get("first_air_date")):
                detail = self.__get_detail_with_cache(cached.get("id"))
                if detail:
                    cached["poster_path"] = cached.get("poster_path") or detail.get("poster_path")
                    cached["backdrop_path"] = cached.get("backdrop_path") or detail.get("backdrop_path")
                    cached["first_air_date"] = cached.get("first_air_date") or detail.get("first_air_date")
                    cached["name"] = detail.get("name") or cached.get("name") or title
                    self.__save_cached_tmdb(title, cached)
            return cached
        try:
            tv = TmdbHelper.search_tv(title)
            if tv and tv.get("id"):
                tmdb_id = tv["id"]
                detail = self.__get_detail_with_cache(tmdb_id)
                result = {
                    "id": tmdb_id,
                    "name": (detail or {}).get("name") or tv.get("name") or title,
                    "poster_path": (detail or {}).get("poster_path") or tv.get("poster_path"),
                    "backdrop_path": (detail or {}).get("backdrop_path") or tv.get("backdrop_path"),
                    "first_air_date": (detail or {}).get("first_air_date") or tv.get("first_air_date"),
                    "media_type": "TV",
                }
                # 季号仅来自「剥季重搜」路径，原名命中的片名数字不算季号
                season = tv.get("_season") or 0
                if season:
                    result["season"] = season
                self.__save_cached_tmdb(title, result)
                logger.debug("【TMDB搜索】'%s' → ID %s", title, tmdb_id)
                return result
        except Exception as e:
            logger.warning("【TMDB搜索】'%s' 失败: %s", title, e)
        return None

    @staticmethod
    def _status_cache_key(tmdbid: int, season: int = 0) -> str:
        """状态缓存键：无季号沿用旧键，有季号追加季后缀，避免跨季串用。"""
        if season:
            return f"maoyandingyue_status_{tmdbid}_s{season}"
        return f"maoyandingyue_status_{tmdbid}"

    def _get_cached_status(self, tmdbid: int, name: str = "", season: int = 0) -> Optional[str]:
        """从短 TTL 缓存读取状态"""
        if not tmdbid:
            return None
        cache_key = self._status_cache_key(tmdbid, season)
        try:
            cached = self.get_data(cache_key)
            if cached and isinstance(cached, dict):
                if time.time() - cached.get("ts", 0) < self._status_cache_ttl:
                    return cached.get("status")
        except Exception:
            pass
        return None

    def _save_cached_status(self, tmdbid: int, status: str, season: int = 0) -> None:
        """保存状态到短 TTL 缓存"""
        if not tmdbid:
            return
        cache_key = self._status_cache_key(tmdbid, season)
        try:
            self.save_data(cache_key, {"status": status, "ts": time.time()})
        except Exception:
            pass

    def __get_cached_cast(self, tmdbid: int) -> Optional[list]:
        """读取演员数据二级缓存（短 TTL，命中即免 TMDB 请求）"""
        if not tmdbid:
            return None
        cache_key = f"maoyandingyue_cast_{tmdbid}"
        try:
            cached = self.get_data(cache_key)
            if cached and isinstance(cached, dict):
                if time.time() - cached.get("ts", 0) < self._status_cache_ttl:
                    return cached.get("data")
        except Exception:
            pass
        return None

    def __save_cached_cast(self, tmdbid: int, data: list) -> None:
        """写入演员数据二级缓存"""
        if not tmdbid:
            return
        cache_key = f"maoyandingyue_cast_{tmdbid}"
        try:
            self.save_data(cache_key, {"data": data, "ts": time.time()})
        except Exception:
            pass

    def __get_cached_detail(self, tmdbid: int) -> Optional[dict]:
        """读取 TV 详情缓存（含 cast + first_air_date，7天 TTL）"""
        if not tmdbid:
            return None
        cache_key = f"maoyandingyue_detail_{tmdbid}"
        try:
            cached = self.get_data(cache_key)
            if cached and isinstance(cached, dict):
                if time.time() - cached.get("ts", 0) < self._detail_cache_ttl:
                    return cached.get("data")
        except Exception:
            pass
        return None

    def __save_cached_detail(self, tmdbid: int, data: dict) -> None:
        """写入 TV 详情缓存"""
        if not tmdbid:
            return
        cache_key = f"maoyandingyue_detail_{tmdbid}"
        try:
            self.save_data(cache_key, {"data": data, "ts": time.time()})
        except Exception:
            pass

    def __get_detail_with_cache(self, tmdbid: int) -> Optional[dict]:
        """读取 TV 详情（含 poster_path/first_air_date/credits），走 7 天缓存；失败返回 None。

        海报、首播日期、演员统一从这里取，不再依赖 recognize_media 的顺带字段。
        """
        if not tmdbid:
            return None
        try:
            detail = self.__get_cached_detail(tmdbid)
            if detail and (not detail.get("poster_path") or not detail.get("first_air_date")):
                # 脏缓存（曾写入缺字段数据），丢弃并重新查询 TMDB
                logger.warning("【详情缓存】tmdbid=%s 命中脏缓存（缺海报/首播日期），重新查询 TMDB", tmdbid)
                detail = None
            if not detail:
                api = TmdbApi(language="zh")
                detail = api.tv.details(tmdbid)
                if detail:
                    self.__save_cached_detail(tmdbid, detail)
            if detail and (not detail.get("poster_path") or not detail.get("first_air_date")):
                logger.warning("【详情缓存】tmdbid=%s 重新查询后仍缺字段：poster=%r first_air_date=%r",
                               tmdbid, detail.get("poster_path"), detail.get("first_air_date"))
            return detail
        except Exception as e:
            logger.warning("【详情缓存】获取 tmdbid=%s 详情失败: %s", tmdbid, e)
            return None

    def get_tv_credits(self, tmdbid: int) -> List[str]:
        """获取前五位演员（使用 detail 缓存，一次请求获取 cast+first_air_date）。"""
        try:
            detail = self.__get_detail_with_cache(tmdbid)
            if not detail:
                return []
            cast = detail.get("credits", {}).get("cast", [])[:5]
            actors = []
            total_chars = 0
            for c in cast:
                name = c.get("name", "")
                if not name:
                    continue
                if total_chars + len(name) > 10:
                    break
                actors.append(name)
                total_chars += len(name)
            return actors
        except Exception as e:
            logger.error("TMDB获取演员 %s 失败: %s", tmdbid, e)
            return []

    def get_state(self) -> bool:
        """返回插件当前是否启用。"""
        return self._enabled

    @classmethod
    def get_render_mode(cls) -> tuple[str, str]:
        """返回 Vue 远程组件渲染模式及产物目录。"""
        render_mode = ("vue", "dist/assets")
        if not cls._render_mode_logged:
            cls._render_mode_logged = True
            logger.info("【联邦组件】渲染模式：mode=%s, path=%s", render_mode[0], render_mode[1])
        return render_mode

    @staticmethod
    def get_command() -> list[dict[str, Any]]:
        """当前插件不注册远程命令。"""
        return []

    def get_service(self) -> list[dict]:
        """插件启用时注册周期刷新任务；通知随自动刷新触发，不再单独注册定时任务。"""
        if not self.get_state():
            return []
        return [
            {
                "id": "MaoyanDianYing.AutoRefresh",
                "name": "猫眼热度榜自动刷新",
                "trigger": IntervalTrigger(hours=self._refresh_interval),
                "func": self._auto_refresh,
                "kwargs": {},
            }
        ]

    def get_api(self) -> list[dict[str, Any]]:
        """注册后端 API。"""
        return [
            {
                "path": "/refresh",
                "endpoint": self.refresh_tmdb,
                "methods": ["POST"],
                "summary": "刷新数据",
                "description": "重新获取 TMDB 海报和演员数据（不重新抓取猫眼榜单）",
                "auth": "bear",
            },
            {
                "path": "/run-once",
                "endpoint": self.run_once,
                "methods": ["POST"],
                "summary": "立即运行1次",
                "description": "立即执行一次完整抓取（猫眼榜单 + TMDB），返回实时结果并更新缓存",
                "auth": "bear",
            },
            {
                "path": "/subscribe",
                "endpoint": self.add_subscribe,
                "methods": ["POST"],
                "summary": "添加订阅",
                "description": "为指定 TMDB ID 的剧集添加订阅",
                "auth": "bear",
            },
            {
                "path": "/get-cache",
                "endpoint": self.get_cache,
                "methods": ["GET"],
                "summary": "获取缓存数据",
                "description": "返回当前缓存的猫眼热度数据，不触发数据抓取",
                "auth": "bear",
            },
            {
                "path": "/get-cast",
                "endpoint": self.get_cast,
                "methods": ["GET"],
                "summary": "获取演员阵容",
                "description": "根据 TMDB ID 获取演员阵容数据",
                "auth": "bear",
            },
            {
                "path": "/get-season",
                "endpoint": self.get_season,
                "methods": ["GET"],
                "summary": "获取季详情",
                "description": "根据 TMDB ID 与季号获取该季详情（简介/首播/海报/演员），供详情弹窗按季展示",
                "auth": "bear",
            },
            {
                "path": "/clear-cache",
                "endpoint": self.clear_cache,
                "methods": ["POST"],
                "summary": "清理插件缓存",
                "description": "清理所有插件产生的缓存数据（TMDB、猫眼抓取数据等），不清理定时任务数据和提醒数据",
                "auth": "bear",
            },
        ]

    @staticmethod
    def _season_in_library(item, season: int) -> bool:
        """判断媒体库条目是否已包含指定季（兼容 JSON 往返后变字符串的键）。"""
        if not item or not season:
            return False
        seasoninfo = getattr(item, "seasoninfo", None) or {}
        if isinstance(seasoninfo, dict):
            return season in seasoninfo or str(season) in seasoninfo
        return False

    @staticmethod
    def _season_in_transfer(record, season: int) -> bool:
        """判断整理记录是否覆盖指定季（``seasons`` 为 'S01' 形态的字符串）。"""
        if not record or not season:
            return False
        raw = str(getattr(record, "seasons", "") or "")
        if not raw:
            return False
        candidates = {f"S{season:02d}", f"S{season}", str(season)}
        return any(item in raw for item in candidates)

    def _check_media_status(self, tmdbid: int, name: str = "", season: int = 0) -> str:
        """按 TMDB 媒体身份返回"影片已入库""订阅已添加"或"未添加订阅"。

        :param season: 季号；>0 时按季判定，避免「已订第 1 季」把第 2 季误判为已订阅。
        """
        if not tmdbid:
            logger.debug("【状态检查】tmdbid 为空，返回未添加")
            return "未添加订阅"

        # 短 TTL 缓存检查（带季号区分，避免跨季串用状态）
        cached_status = self._get_cached_status(tmdbid, name, season)
        if cached_status is not None:
            logger.debug("【状态检查】缓存命中：tmdbid=%s, 季=%s, status=%s",
                         tmdbid, season or "无", cached_status)
            return cached_status

        media_source = "themoviedb"
        media_id = str(tmdbid)
        logger.info(
            "【状态检查】开始：tmdbid=%s, media_source=%s, media_id=%s, mtype=%s",
            tmdbid,
            media_source,
            media_id,
            MediaType.TV.value,
        )

        # 1. 查询媒体库（按 TMDB 媒体身份）
        try:
            item = self._media_oper.exists(
                media_source=media_source,
                media_id=media_id,
                mtype=MediaType.TV.value,
            )
        except Exception as e:
            logger.error("【状态检查】媒体库查询异常：media_id=%s, error=%s", media_id, e)
            self._save_cached_status(tmdbid, "未添加订阅", season)
            return "未添加订阅"

        if item:
            logger.info(
                "【状态检查】媒体库命中：title=%s, media_source=%s, media_id=%s, item_type=%s",
                getattr(item, "title", ""),
                getattr(item, "media_source", ""),
                getattr(item, "media_id", ""),
                getattr(item, "item_type", ""),
            )
            # 带季号：需确认该季已入库，避免「第 1 季入库」把第 2 季误判为已入库
            if season and not self._season_in_library(item, season):
                logger.info("【状态检查】媒体库命中但第 %s 季未入库：tmdbid=%s", season, tmdbid)
            else:
                self._save_cached_status(tmdbid, "影片已入库", season)
                return "影片已入库"

        logger.info("【状态检查】媒体库身份未命中：media_source=%s, media_id=%s", media_source, media_id)

        # 2. 兼容历史媒体库记录：按剧名和电视剧类型做兜底匹配
        if name:
            try:
                title_item = self._media_oper.exists(
                    title=name,
                    mtype=MediaType.TV.value,
                )
            except Exception as e:
                logger.error("【状态检查】按标题查询媒体库异常：title=%s, error=%s", name, e)
                title_item = None
            if title_item:
                logger.info(
                    "【状态检查】按标题命中媒体库：title=%s, stored_title=%s, "
                    "stored_media_source=%s, stored_media_id=%s, stored_item_type=%s",
                    name,
                    getattr(title_item, "title", ""),
                    getattr(title_item, "media_source", ""),
                    getattr(title_item, "media_id", ""),
                    getattr(title_item, "item_type", ""),
                )
                if season and not self._season_in_library(title_item, season):
                    logger.info("【状态检查】按标题命中但第 %s 季未入库：title=%s", season, name)
                else:
                    self._save_cached_status(tmdbid, "影片已入库", season)
                    return "影片已入库"
            logger.info("【状态检查】按标题也未命中：title=%s, mtype=%s", name, MediaType.TV.value)

        # 3. 兼容飞牛/绿联等不支持媒体服务器同步协议的环境：通过文件整理记录表判断
        try:
            transfer_records = self._transfer_oper.get_by(
                media_source=media_source,
                media_id=media_id,
                mtype=MediaType.TV.value,
            )
            transfer_record = next(
                (record for record in transfer_records if getattr(record, "status", False)),
                None,
            )
        except Exception as e:
            logger.error("【状态检查】整理记录查询异常：media_id=%s, error=%s", media_id, e)
            transfer_record = None
        if transfer_record:
            logger.info(
                "【状态检查】整理记录命中：title=%s, dest=%s",
                getattr(transfer_record, "title", ""),
                getattr(transfer_record, "dest", ""),
            )
            if season and not self._season_in_transfer(transfer_record, season):
                logger.info("【状态检查】整理记录命中但第 %s 季未入库：seasons=%s",
                            season, getattr(transfer_record, "seasons", ""))
            else:
                self._save_cached_status(tmdbid, "影片已入库", season)
                return "影片已入库"
        logger.info("【状态检查】整理记录未命中：media_source=%s, media_id=%s", media_source, media_id)

        # 4. 最后查询订阅表
        try:
            subs = self._subscribe_oper.list_by_media_identity(
                media_source=media_source, media_id=media_id
            )
        except Exception as e:
            logger.error("【状态检查】订阅查询异常：media_id=%s, error=%s", media_id, e)
            self._save_cached_status(tmdbid, "未添加订阅", season)
            return "未添加订阅"

        if subs:
            # 带季号：只有该季已被订阅才算「订阅已添加」，否则第 2 季会被第 1 季挡住
            if season and not self._season_subscribed(subs, season):
                logger.info("【状态检查】订阅存在但无第 %s 季：media_id=%s, 已订季号=%s",
                            season, media_id, self._subscribed_seasons(subs))
            else:
                logger.info("【状态检查】订阅命中：media_source=%s, media_id=%s, count=%s",
                            media_source, media_id, len(subs))
                self._save_cached_status(tmdbid, "订阅已添加", season)
                return "订阅已添加"

        logger.info("【状态检查】媒体库、整理记录和订阅均未命中：media_source=%s, media_id=%s", media_source, media_id)
        self._save_cached_status(tmdbid, "未添加订阅", season)
        return "未添加订阅"

    @staticmethod
    def _subscribed_seasons(subs) -> list:
        """返回订阅记录中已订阅的季号列表（兼容 season 为空的历史记录）。"""
        seasons = []
        for sub in subs or []:
            season = getattr(sub, "season", None)
            seasons.append(season)
        return seasons

    @classmethod
    def _season_subscribed(cls, subs, season: int) -> bool:
        """判断订阅记录是否覆盖指定季。

        历史订阅记录的 season 可能为空（表示整剧订阅），此时视为已覆盖所有季。
        """
        if not season:
            return True
        for sub in subs or []:
            sub_season = getattr(sub, "season", None)
            if sub_season is None or int(sub_season) == int(season):
                return True
        return False

    def get_form(self) -> tuple[list[dict], dict[str, Any]]:
        """返回配置页面和默认配置。手机版用 Vuetify JSON 栅格渲染，电脑版用远程 Config 组件。"""
        logger.info("【配置页面】返回 Vuetify 配置表单（Vue 模式使用远程 Config 组件）")
        from app.schemas.types import MessageType
        return [
            {
                "component": "VForm",
                "content": [
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {"model": "enabled", "label": "启用插件"},
                                    },
                                ],
                            },
                        ],
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VSelect",
                                        "props": {
                                            "model": "refresh_interval",
                                            "label": "自动刷新间隔（小时）",
                                            "variant": "outlined",
                                            "density": "compact",
                                            "items": [
                                                {"title": "1小时", "value": 1},
                                                {"title": "2小时", "value": 2},
                                                {"title": "3小时", "value": 3},
                                                {"title": "6小时", "value": 6},
                                                {"title": "12小时", "value": 12},
                                                {"title": "24小时", "value": 24},
                                            ],
                                        },
                                    },
                                ],
                            },
                        ],
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {"model": "reminder_enabled", "label": "开启通知"},
                                    },
                                ],
                            },
                        ],
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VSelect",
                                        "props": {
                                            "model": "reminder_msgtype",
                                            "label": "消息类型",
                                            "variant": "outlined",
                                            "density": "compact",
                                            "items": [
                                                {"title": item.value, "value": item.name}
                                                for item in MessageType
                                            ],
                                        },
                                    },
                                    {
                                        "component": "VSwitch",
                                        "props": {"model": "enable_discovery", "label": "在发现页显示"},
                                    },
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "mpnews_enabled",
                                            "label": "使用图文消息推送",
                                            "hint": "改用企业微信图文消息(mpnews)发送，复用宿主企业微信应用凭证",
                                        },
                                    },
                                ],
                            },
                        ],
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12},
                                "content": [
                                    {
                                        "component": "VAlert",
                                        "props": {
                                            "type": "info",
                                            "variant": "tonal",
                                            "density": "compact",
                                            "class": "mt-3",
                                        },
                                        "text": "开启通知后，系统会在每次自动刷新后检查今日新增影片并推送，已经推送过的不会重复推送。“立即运行一次提醒”在无新增时会推送 TOP5 推荐。",
                                    },
                                ],
                            },
                        ],
                    },
                ],
            }
        ], {
            "enabled": False,
            "refresh_interval": 6,
            "reminder_enabled": False,
            "reminder_msgtype": "Plugin",
            "run_remind": False,
            "enable_discovery": False,
            "mpnews_enabled": False,
        }

    def get_page(self) -> list[dict]:
        """Vue 远程组件模式下不再使用 Vuetify JSON 渲染。"""
        logger.info("【数据页面】返回空 JSON，交由远程 Page 组件渲染")
        return []

    def get_sidebar_nav(self) -> list[dict[str, Any]]:
        """返回侧边栏导航配置"""
        enable = False
        if hasattr(self, "_config") and self._config:
            enable = self._config.get("enable_discovery", False)
        elif hasattr(self, "config") and self.config:
            enable = self.config.get("enable_discovery", False)
        elif hasattr(self, "get_config"):
            config = self.get_config()
            if config:
                enable = config.get("enable_discovery", False)
            
        # return empty for default implicit mounting under 'Plugin', unless section discovery is explicitly opted-in
        if not enable:
            return [{
                "nav_key": "main", # 这个不能省略，基座要读
                "title": "猫眼榜单",
                "icon": "mdi-cat",
                "order": 1,
            }]
            
        return [
            {
                "nav_key": "main",
                "title": "猫眼榜单",
                "icon": "mdi-cat",
                "section": "discovery", 
                "order": 10,
            }
        ]

    def stop_service(self) -> None:
        """标记插件停用；定时任务由 MoviePilot 根据 ``get_service`` 统一移除。"""
        self._enabled = False
        with self._warmup_lock:
            self._warmup_done = False
        logger.info("插件已停止")

    # ─── 宿主订阅变更事件监听 ───
    # 用户在 MoviePilot「订阅管理」里增/删/改订阅时宿主不回调插件，只广播
    # subscribe.added/modified/deleted；本插件按媒体身份清除对应剧集的状态
    # 短缓存，避免插件页最长 _status_cache_ttl(1800s) 显示陈旧状态。
    # 生命周期：类定义期注册 → 宿主分发时绑定到运行中插件实例；
    # 插件停用/停止时宿主先 disable 本类 handler 再调 stop_service，
    # 因此无需（也不应）在 stop_service 中手动注销。
    @eventmanager.register(
        [
            EventType.SubscribeDeleted,    # 用户在系统订阅管理取消订阅
            EventType.SubscribeModified,   # 订阅被外部修改（状态/字段变更）
            EventType.SubscribeAdded,      # 用户直接在系统里添加同一剧集订阅
        ]
    )
    def on_subscribe_changed(self, event: Event) -> None:
        """宿主订阅增删改事件：失效对应剧集的短状态缓存。"""
        if not getattr(self, "_enabled", False):
            return
        try:
            data = event.event_data if isinstance(event.event_data, dict) else {}
            # Deleted/Modified → subscribe_info（快照）；Added → mediainfo（写入字段）
            snap = data.get("subscribe_info") if isinstance(data.get("subscribe_info"), dict) else {}
            media = data.get("mediainfo") if isinstance(data.get("mediainfo"), dict) else {}
            info = snap or media
            source = str(info.get("media_source") or "").strip().lower()
            if source and source != "themoviedb":
                logger.debug("【订阅事件】非 themoviedb 来源 %s，忽略", source)
                return
            raw_id = info.get("media_id") or info.get("tmdb_id") or info.get("tmdbid")
            if raw_id is None or str(raw_id).strip() == "":
                logger.debug("【订阅事件】payload 无媒体身份，跳过：%s", getattr(event.event_type, "value", event.event_type))
                return
            tmdbid = int(str(raw_id).strip())
        except Exception as e:
            logger.warning("【订阅事件】解析媒体身份失败：%s", e)
            return
        try:
            self.del_data(f"maoyandingyue_status_{tmdbid}")
            logger.info("【订阅事件】%s：已清除 tmdbid=%s 状态缓存", getattr(event.event_type, "value", event.event_type), tmdbid)
        except Exception as e:
            logger.warning("【订阅事件】清除 tmdbid=%s 状态缓存失败：%s", tmdbid, e)

    def add_subscribe(self, body: dict = Body(...)) -> dict[str, Any]:
        """为指定剧集添加订阅，并返回 MoviePilot 标准响应结构。

        带季数的剧集（如「问心2」）会把季号传给订阅链，避免订阅到第 1 季。
        """
        tmdbid = body.get("tmdbid")
        name = str(body.get("name", "")).strip()
        try:
            season = int(body.get("season") or 0)
        except (TypeError, ValueError):
            season = 0
        logger.info("【添加订阅】收到请求：%s (TMDB ID: %s, 季号: %s)", name, tmdbid, season or "无")

        # 旧缓存可能没有 TMDB ID。按剧名即时补查，不能把 0 提交给订阅链。
        if not tmdbid and name:
            logger.info("【添加订阅】TMDB ID 为空，开始按剧名补查：%s", name)
            tmdb_info = self.__search_tmdb_with_cache(name)
            if tmdb_info:
                tmdbid = tmdb_info.get("id")
                if not season and tmdb_info.get("season"):
                    season = int(tmdb_info["season"])
                logger.info("【添加订阅】按剧名补查成功：%s -> %s（季号=%s）",
                            name, tmdbid, season or "无")
                self._update_cached_tmdbid(name=name, tmdbid=tmdbid)

        if not tmdbid:
            logger.warning("【添加订阅】无法获取 TMDB ID：%s", name)
            return {"success": False, "message": f"未能识别《{name or '未知剧集'}》的 TMDB 信息，请先刷新数据", "data": None}

        try:
            tmdbid = int(tmdbid)
            status = self._check_media_status(tmdbid, name, season)
            if status == "影片已入库":
                return {"success": False, "message": "影片已入库，无需重复订阅", "data": None}
            if status == "订阅已添加":
                return {"success": False, "message": "已订阅，无需重复订阅", "data": None}

            subscribe_chain = SubscribeChain()
            sub_id, msg = subscribe_chain.add(
                title=name,
                year="",
                mtype=MediaType.TV,
                season=season or None,
                media_source="themoviedb",
                media_id=str(tmdbid),
                username="猫眼热度",
            )
            if sub_id:
                logger.info("【添加订阅】成功：%s (TMDB ID: %s, 季号: %s, 订阅 ID: %d)",
                            name, tmdbid, season or "无", sub_id)
                # 清除该剧的状态缓存，避免 loadCache() 命中旧缓存将按钮刷回"未添加订阅"
                try:
                    self.del_data(f"maoyandingyue_status_{tmdbid}")
                except Exception:
                    pass
                return {
                    "success": True,
                    "message": f"订阅已添加：{name}" + (f" 第 {season} 季" if season else ""),
                    "data": {"subscribe_id": sub_id, "tmdbid": tmdbid, "season": season},
                }
            logger.warning("【添加订阅】失败：%s (TMDB ID: %s) - %s", name, tmdbid, msg)
            return {"success": False, "message": str(msg or "添加订阅失败"), "data": None}
        except Exception as e:
            logger.error("【添加订阅】异常：%s", e)
            return {"success": False, "message": str(e), "data": None}

    def _update_cached_tmdbid(self, name: str, tmdbid: int) -> None:
        """把即时识别出的 TMDB ID 回写到插件缓存。"""
        if not name or not tmdbid:
            return
        try:
            cached = super().get_data(self._cache_key)
            if not isinstance(cached, dict):
                return
            changed = False
            for item in cached.get("rows", []):
                if item.get("name") == name:
                    item["tmdbid"] = int(tmdbid)
                    changed = True
                    break
            if changed:
                self.save_data(self._cache_key, cached)
                logger.info("【添加订阅】已回写缓存 TMDB ID：%s -> %s", name, tmdbid)
        except Exception as e:
            logger.warning("【添加订阅】回写缓存失败：%s", e)

    def clear_cache(self):
        """API：清理全部插件缓存（TMDB 搜索/状态/演员/详情/主数据/通知推送记录），
        并静默重建（不触发通知推送）。"""
        try:
            all_items = self.get_data() or []
            stats = {
                "maoyandingyue_data": 0,
                "maoyandingyue_tmdb_": 0,
                "maoyandingyue_status_": 0,
                "maoyandingyue_cast_": 0,
                "maoyandingyue_detail_": 0,
                "maoyandingyue_remind": 0,
                "maoyandingyue_mpthumb_": 0,
                "maoyandingyue_season_": 0,
                "other": 0,
            }
            removed = 0
            for item in all_items:
                key = item.key
                self.del_data(key)
                removed += 1
                if key == self._cache_key:
                    stats["maoyandingyue_data"] += 1
                elif key.startswith("maoyandingyue_tmdb_"):
                    stats["maoyandingyue_tmdb_"] += 1
                elif key.startswith("maoyandingyue_status_"):
                    stats["maoyandingyue_status_"] += 1
                elif key.startswith("maoyandingyue_cast_"):
                    stats["maoyandingyue_cast_"] += 1
                elif key.startswith("maoyandingyue_detail_"):
                    stats["maoyandingyue_detail_"] += 1
                elif key == "maoyandingyue_remind":
                    stats["maoyandingyue_remind"] += 1
                elif key.startswith("maoyandingyue_mpthumb_"):
                    stats["maoyandingyue_mpthumb_"] += 1
                elif key.startswith("maoyandingyue_season_"):
                    stats["maoyandingyue_season_"] += 1
                else:
                    stats["other"] += 1
            logger.info("【清理缓存】已清理 %d 个缓存项（tmdb=%d, status=%d, cast=%d, detail=%d, 主数据=%d, 通知记录=%d%s），开始静默重建",
                        removed, stats["maoyandingyue_tmdb_"], stats["maoyandingyue_status_"],
                        stats["maoyandingyue_cast_"], stats["maoyandingyue_detail_"], stats["maoyandingyue_data"],
                        stats["maoyandingyue_remind"],
                        f"，其他={stats['other']}" if stats["other"] else "")
            # 静默重建：不触发今日新增通知
            try:
                self._auto_refresh(notify=False)
                detail = (f"TMDB搜索 {stats['maoyandingyue_tmdb_']} 个、状态 {stats['maoyandingyue_status_']} 个、"
                          f"演员 {stats['maoyandingyue_cast_']} 个、详情 {stats['maoyandingyue_detail_']} 个、"
                          f"主数据 {stats['maoyandingyue_data']} 个、通知推送记录 {stats['maoyandingyue_remind']} 个、"
                          f"图文素材 {stats['maoyandingyue_mpthumb_']} 个、季别开播 {stats['maoyandingyue_season_']} 个")
                msg = f"已清理 {removed} 个缓存项（{detail}），并重新抓取最新数据"
            except Exception as e:
                logger.error("【清理缓存】重新抓取失败: %s", e)
                msg = f"已清理 {removed} 个缓存项，但重新抓取失败：{e}"
            return {"success": True, "message": msg, "data": {"count": removed, "stats": stats}}
        except Exception as e:
            logger.error("【清理缓存】失败: %s", e)
            return {"success": False, "message": str(e)}

    def __send_remind(self, force: bool = False, heat_list: Optional[list] = None) -> None:
        """通知：遍历猫眼热度榜，推送今日上新（first_air_date/release_date == 今天）的剧集。

        - force=False（自动）：随自动刷新触发，仅当“开启通知”开启时执行；
          只推送今天尚未推送过的影片，没有未推送项时静默（不发 TOP5）。
        - force=True（手动“立即运行一次提醒”）：绕过“开启通知”开关；
          今日有新增则推送，没有今日新增时推送 TOP5 + TOP1 封面。
        """
        try:
            logger.info("【今日上新提醒】任务启动，enabled=%s, msgtype=%s, force=%s",
                        getattr(self, "_reminder_enabled", False),
                        getattr(self, "_reminder_msgtype", "Plugin"),
                        force)
            if not self.get_state():
                logger.info("【今日上新提醒】插件未启用，跳过")
                return
            if not force and not getattr(self, "_reminder_enabled", False):
                logger.info("【今日上新提醒】通知开关未开启，跳过")
                return
            from app.schemas.types import MessageType
            msgtype_name = str(getattr(self, "_reminder_msgtype", "Plugin") or "Plugin")
            try:
                mtype = MessageType[msgtype_name]
            except (KeyError, TypeError):
                mtype = MessageType.Manual
            today = datetime.now().date().isoformat()

            # 已推送记录：仅当记录日期是今天时才生效（跨天自动重置）
            record = self.get_data("maoyandingyue_remind") or {}
            sent_ids = set()
            if isinstance(record, dict) and record.get("date") == today:
                raw = record.get("sent_items") or []
                sent_ids = {str(x) for x in raw}

            if heat_list is None:
                heat_list = MaoyanScraper.fetch_heat_list()

            hits = []
            for item in heat_list or []:
                if not item or not item.get("name"):
                    continue
                if self.__is_today_new(item):
                    hits.append(item)
            logger.info("【今日上新提醒】扫描 %d 条热度榜条目，今日上新 %d 条",
                        len(heat_list or []), len(hits))

            def _send_id(item: dict) -> str:
                """推送去重标识：优先 TMDB ID，无 TMDB 数据时用名称兜底。"""
                try:
                    tmdb_info = self.__search_tmdb_with_cache(item.get("name", ""))
                    if tmdb_info and tmdb_info.get("id"):
                        return f"tmdb:{tmdb_info.get('id')}"
                except Exception:
                    pass
                return f"name:{item.get('name', '')}"

            if force:
                # 手动模式：全部今日新增都推送（便于手动测试），成功后同步写入去重记录
                pending = hits
                send_top5 = not hits
            else:
                # 自动模式：只推送尚未推送过的，无未推送项时静默
                pending = [h for h in hits if _send_id(h) not in sent_ids]
                send_top5 = False

            if pending:
                # 仿 IrabSubscribeReminder 图文消息：拼装图片列表 + 文字，每 8 条一批带图推送
                images = []
                lines = []
                batch = []
                for hit in pending:
                    name = hit.get("name", "")
                    platform = hit.get("platform", "")
                    status_tag = self.__notify_status_tag(hit)
                    line = f"📺 {hit.get('rank', 0)}. 《{name}》"
                    if platform:
                        line += f"（{platform}）"
                    line += status_tag
                    lines.append(line)
                    # 富信息条目：演员/详情/状态均优先取插件缓存，供 mpnews 正文渲染。
                    # 仅在 mpnews 开启时组装，避免关闭时产生额外缓存/网络开销。
                    hit["status_tag"] = status_tag
                    if self._mpnews_enabled:
                        batch.append(self.__build_notify_item(hit))
                    # 从 TMDB 缓存拿海报（__is_today_new 已经搜过，命中缓存）
                    poster_path = ""
                    try:
                        tmdb_info = self.__search_tmdb_with_cache(name)
                        if tmdb_info:
                            poster_path = tmdb_info.get("poster_path") or ""
                    except Exception:
                        pass
                    if poster_path:
                        if poster_path.startswith("http"):
                            images.append(poster_path)
                        else:
                            images.append(f"https://image.tmdb.org/t/p/w500{poster_path}")
                    if len(lines) >= 8:
                        self.__notify(
                            mtype=mtype,
                            title="猫眼热度榜今日上新",
                            text="\n".join(lines),
                            image=random.choice(images) if images else None,
                            items=batch,
                        )
                        lines = []
                        images = []
                        batch = []
                if lines:
                    self.__notify(
                        mtype=mtype,
                        title="猫眼热度榜今日上新",
                        text="\n".join(lines),
                        image=random.choice(images) if images else None,
                        items=batch,
                    )
                logger.info("【今日上新提醒】推送完成，今日上新 %d 条", len(pending))
                # 推送成功后记录（手动也会写入，避免随后自动刷新重复推送）
                for hit in pending:
                    sent_ids.add(_send_id(hit))
            elif send_top5:
                # 仅手动模式且今日无新增：推送 TOP5 + TOP1 封面
                top5 = (heat_list or [])[:5]
                top1_image = None
                lines = ["今日无新增，为您推荐猫眼热度 TOP5："]
                batch = []
                for item in top5:
                    rank = item.get("rank", 0)
                    name = item.get("name", "")
                    platform = item.get("platform", "")
                    status_tag = self.__notify_status_tag(item)
                    line = f"📺 {rank}. 《{name}》"
                    if platform:
                        line += f"（{platform}）"
                    line += status_tag
                    lines.append(line)
                    item["status_tag"] = status_tag
                    if self._mpnews_enabled:
                        batch.append(self.__build_notify_item(item))
                    # 取 TOP1 封面
                    if rank == 1 and not top1_image:
                        try:
                            tmdb_info = self.__search_tmdb_with_cache(name)
                            if tmdb_info:
                                poster_path = tmdb_info.get("poster_path") or ""
                                if poster_path:
                                    if poster_path.startswith("http"):
                                        top1_image = poster_path
                                    else:
                                        top1_image = f"https://image.tmdb.org/t/p/w500{poster_path}"
                        except Exception:
                            pass
                self.__notify(
                    mtype=mtype,
                    title="猫眼热度榜今日上新",
                    text="\n".join(lines),
                    image=top1_image,
                    items=batch,
                )
                logger.info("【今日上新提醒】今日无新增，推送 TOP5 推荐")
            else:
                logger.info("【今日上新提醒】无未推送的今日新增，本次不推送")

            self.save_data("maoyandingyue_remind", {
                "date": today,
                "count": len(pending),
                "items": [
                    {
                        "rank": hit.get("rank", 0),
                        "name": hit.get("name", ""),
                        "platform": hit.get("platform", ""),
                    }
                    for hit in hits
                ],
                "sent_items": sorted(sent_ids),
                "last_run": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
        except Exception as e:
            logger.error("【今日上新提醒】执行失败: %s", e)

    def __notify(self, mtype, title: str, text: str, image: Optional[str] = None,
                 items: Optional[List[dict]] = None) -> None:
        """统一通知出口。

        - mpnews 开关关闭：走原有宿主通知链，行为与历史版本完全一致。
        - mpnews 开关开启：改用企业微信 mpnews 图文消息推送（正文含演员/详情/状态）；
          失败时自动回退宿主通知链，确保开启该开关不会导致通知丢失。
        """
        if not self._mpnews_enabled:
            self.post_message(mtype=mtype, title=title, text=text, image=image)
            return
        try:
            conf = self.__get_wechat_conf()
            if conf is not None:
                sender = _WeComMpnews(self, conf)
                if sender.send(title=title, text=text, image=image, items=items):
                    return
                logger.warning("【企微图文】推送未成功，回退宿主通知渠道")
            else:
                logger.warning("【企微图文】未找到可用的企业微信渠道配置，回退宿主通知渠道")
        except Exception as e:
            logger.error("【企微图文】发送异常，回退宿主通知渠道: %s", e)
        self.post_message(mtype=mtype, title=title, text=text, image=image)

    def __build_notify_item(self, item: dict) -> dict:
        """把榜单条目补齐为通知所需的富信息（全部优先命中插件缓存，缺失才联网）。

        读取顺序：TMDB 二级缓存 -> 详情缓存（含 credits）-> 详情接口（带 7 天缓存）。
        带季数的条目用该季详情覆盖首播/简介/集数，避免显示第 1 季数据。
        """
        name = item.get("name", "")
        enriched = {
            "rank": item.get("rank", 0),
            "name": name,
            "platform": item.get("platform", ""),
            "status_tag": item.get("status_tag") or self.__notify_status_tag(item),
        }
        if not name:
            return enriched
        try:
            tmdb_info = self.__search_tmdb_with_cache(name) or {}
        except Exception:
            tmdb_info = {}
        tmdbid = tmdb_info.get("id") or item.get("tmdbid") or 0
        enriched["tmdbid"] = tmdbid
        if item.get("actors"):
            enriched["actors"] = item.get("actors")
        if not tmdbid:
            return enriched
        try:
            detail = self.__get_detail_with_cache(tmdbid) or {}
        except Exception:
            detail = {}
        for key in ("vote_average", "first_air_date", "number_of_seasons",
                    "number_of_episodes", "genres", "overview"):
            if detail.get(key):
                enriched[key] = detail[key]

        # 带季数：以该季数据为准（首播日期、简介、集数、季海报）
        season = tmdb_info.get("season") or 0
        if season:
            try:
                season_detail = self.__get_season_detail(tmdbid, season) or {}
            except Exception:
                season_detail = {}
            if season_detail:
                enriched["season"] = season
                if season_detail.get("air_date"):
                    enriched["first_air_date"] = season_detail["air_date"]
                if season_detail.get("overview"):
                    enriched["overview"] = season_detail["overview"]
                if season_detail.get("vote_average"):
                    enriched["vote_average"] = season_detail["vote_average"]
                episodes = season_detail.get("episodes") or []
                if episodes:
                    enriched["number_of_episodes"] = len(episodes)
                    enriched["number_of_seasons"] = season
                if season_detail.get("name"):
                    enriched["season_name"] = season_detail["name"]

        if not enriched.get("actors"):
            cast = (detail.get("credits") or {}).get("cast") or []
            names = [c.get("name") for c in cast[:5] if c.get("name")]
            if names:
                enriched["actors"] = names
        return enriched

    @staticmethod
    def __get_wechat_conf() -> Optional[dict]:
        """读取宿主已启用的企业微信通知渠道配置（非机器人模式）。"""
        try:
            from app.sdk.services import NotificationHelper
            services = NotificationHelper().get_services(type_filter="wechat")
            for service in services.values():
                config = getattr(service.config, "config", None) or {}
                if not config.get("WECHAT_CORPID") or not config.get("WECHAT_APP_ID"):
                    continue
                # 机器人模式走的是另一套协议，不具备自建应用凭证
                if config.get("WECHAT_MODE", "app") == "bot":
                    continue
                return config
        except Exception as e:
            logger.error("【企微图文】读取企业微信渠道配置失败: %s", e)
        return None

    def __notify_status_tag(self, item: dict) -> str:
        """通知行附注订阅状态：【已订阅】/【未订阅】（基于媒体库/整理记录/订阅判断）。

        映射：影片已入库、订阅已添加 -> 【已订阅】；未添加订阅 -> 【未订阅】。
        带季数的条目按季判定，避免「已订第 1 季」显示为第 2 季已订阅。
        """
        try:
            name = item.get("name", "")
            tmdbid = item.get("tmdbid") or 0
            season = item.get("season") or 0
            if not tmdbid:
                tmdb_info = self.__search_tmdb_with_cache(name)
                tmdbid = (tmdb_info or {}).get("id") or 0
                if not season:
                    season = (tmdb_info or {}).get("season") or 0
            status = self._check_media_status(tmdbid, name, season)
            return "【未订阅】" if status == "未添加订阅" else "【已订阅】"
        except Exception:
            return ""

    def __get_season_detail(self, tmdbid: int, season: int) -> Optional[dict]:
        """读取指定季的详情（含 air_date/overview/集数），带 7 天缓存。

        季不存在或取不到返回 None。查询前先校验季号存在，避免对「我们的少年时代2」
        这类片名自带数字、但 TMDB 只有第 1 季的条目发起无效请求（会返回 404）。
        """
        if not tmdbid or not season:
            return None
        cache_key = f"maoyandingyue_season_{tmdbid}_{season}"
        try:
            cached = self.get_data(cache_key)
            if cached and isinstance(cached, dict):
                if time.time() - cached.get("ts", 0) < self._detail_cache_ttl:
                    return cached.get("data") or None
        except Exception:
            pass
        # 先校验季号是否存在：片名自带的数字（「XXX2」）并不等于 TMDB 的季号
        detail = self.__get_detail_with_cache(tmdbid) or {}
        seasons = detail.get("seasons") or []
        if seasons:
            valid = {s.get("season_number") for s in seasons if isinstance(s, dict)}
            if season not in valid:
                logger.debug("【季别详情】tmdbid=%s 无第 %s 季（有效季号=%s），跳过",
                             tmdbid, season, sorted(v for v in valid if v is not None))
                return None
        try:
            api = TmdbApi(language="zh")
            season_detail = api.season_obj.details(tv_id=tmdbid, season_num=season)
            if not season_detail:
                return None
            # 季级 air_date 偶尔为空，回退到该季第 1 集
            if not season_detail.get("air_date"):
                episodes = season_detail.get("episodes") or []
                if episodes and episodes[0].get("air_date"):
                    season_detail["air_date"] = episodes[0].get("air_date")
            try:
                self.save_data(cache_key, {"data": season_detail, "ts": time.time()})
            except Exception:
                pass
            logger.debug("【季别详情】tmdbid=%s 第 %s 季 air_date=%s",
                         tmdbid, season, season_detail.get("air_date"))
            return season_detail
        except Exception as e:
            logger.warning("【季别详情】获取 tmdbid=%s 第 %s 季失败: %s", tmdbid, season, e)
        return None

    def __get_season_air_date(self, tmdbid: int, season: int) -> Optional[str]:
        """读取指定季的开播日期；季不存在或取不到返回 None。"""
        season_detail = self.__get_season_detail(tmdbid, season)
        if not season_detail:
            return None
        air_date = season_detail.get("air_date")
        return str(air_date) if air_date else None

    def __is_today_new(self, item: dict) -> bool:
        """判定榜单条目是否为今日上新。

        - 无季号：比对剧集主记录 ``first_air_date``（原有行为）。
        - 有季号：比对该季开播日（season 详情），避免用第 1 季日期误判。
        优先使用 detail/season 缓存，命中时无网络请求。
        """
        try:
            name = (item or {}).get("name", "")
            if not name:
                return False
            tmdb_info = self.__search_tmdb_with_cache(name)
            if not tmdb_info:
                logger.debug("【今日上新提醒】'%s' 无 TMDB 数据，跳过", name)
                return False
            tmdbid = tmdb_info.get("id")
            season = tmdb_info.get("season") or 0
            today = datetime.now().date().isoformat()

            # 带季号：用该季开播日判定
            if tmdbid and season:
                season_air = self.__get_season_air_date(tmdbid, season)
                if season_air:
                    logger.debug("【今日上新提醒】'%s' 第 %s 季开播日=%s",
                                 name, season, season_air)
                    return str(season_air) == today
                logger.debug("【今日上新提醒】'%s' 第 %s 季取不到开播日，回退主记录判定",
                             name, season)

            air_date = tmdb_info.get("first_air_date") or ""
            if not air_date and tmdbid:
                detail = self.__get_cached_detail(tmdbid)
                if not detail:
                    api = TmdbApi(language="zh")
                    detail = api.tv.details(tmdbid)
                    if detail:
                        self.__save_cached_detail(tmdbid, detail)
                if detail:
                    air_date = detail.get("first_air_date") or ""
            if not air_date:
                logger.debug("【今日上新提醒】'%s' 缺少开播日期，跳过", name)
                return False
            return str(air_date) == today
        except Exception as e:
            logger.error("【今日上新提醒】判定'%s'是否今日上新失败: %s",
                         (item or {}).get("name", ""), e)
            return False

    def _auto_refresh(self, notify: bool = True):
        """定时自动刷新：抓取榜单，仅对新条目获取 TMDB 数据。

        :param notify: 刷新完成后是否触发今日新增通知（清理缓存等静默重建时传 False）。
        """
        logger.info("【定时刷新】开始...")
        try:
            heat_list = MaoyanScraper.fetch_heat_list()

            # 读取现有缓存（可能包含已有 TMDB 数据）
            cached = super().get_data(self._cache_key)
            existing = {}
            if cached and isinstance(cached, dict):
                for item in cached.get("rows", []):
                    name = item.get("name", "")
                    if name:
                        existing[name] = item

            enriched = []
            new_count = 0
            for item in heat_list:
                name = item.get("name", "")
                # 如果已有 TMDB 数据，直接复用
                if name in existing and existing[name].get("tmdbid"):
                    # 已识别条目完整复用 TMDB 字段，避免新榜单的默认 tmdbid=0 覆盖有效缓存。
                    item["tmdbid"] = existing[name]["tmdbid"]
                    item["poster"] = existing[name].get("poster", "")
                    item["actors"] = existing[name].get("actors", [])
                    # 季号：优先用 rows 里已有的；缺失时纯读 TMDB 二级缓存补算
                    # （season 字段后加，老 rows 没有；不补的话前端拿不到季号）。
                    # 这里不调用搜索，避免对已识别条目产生额外网络请求。
                    season = existing[name].get("season") or self.__season_from_cache(name)
                    if season:
                        item["season"] = season
                else:
                    # 新条目才获取 TMDB（带二级缓存）
                    tmdb_info = self.__search_tmdb_with_cache(name)
                    if tmdb_info:
                        poster_path = tmdb_info.get("poster_path", "")
                        item["poster"] = TmdbHelper.get_poster_url(poster_path)
                        tmdbid = tmdb_info.get("id")
                        if tmdbid:
                            item["tmdbid"] = tmdbid
                            actors = self.get_tv_credits(tmdbid)
                            if actors:
                                item["actors"] = actors
                        if tmdb_info.get("season"):
                            item["season"] = tmdb_info["season"]
                    new_count += 1
                enriched.append(item)
                time.sleep(0.15)

            result = {
                "rows": enriched,
                "timestamp": time.time(),
                "total": len(enriched),
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            self.save_data(self._cache_key, result)
            logger.info("【定时刷新】完成，共 %d 条，其中 %d 条为新获取 TMDB", len(enriched), new_count)
            # 自动通知：随每次自动刷新触发（内部按“开启通知”开关和去重记录决定是否推送）
            if notify:
                self.__send_remind(force=False, heat_list=enriched)
            else:
                logger.info("【定时刷新】静默重建（清理缓存触发），不发送通知")
        except Exception as e:
            logger.error("【定时刷新】失败: %s", e)

    def refresh_tmdb(self):
        """刷新数据 API：重新获取 TMDB 海报和演员数据（不重新抓取猫眼榜单）。"""
        logger.info("【刷新数据API】收到请求")
        logger.info("【刷新数据】开始重新获取 TMDB 数据...")
        start_time = time.time()
        try:
            cached = super().get_data(self._cache_key)
            if not cached or not isinstance(cached, dict):
                return {"success": False, "message": "暂无缓存数据，请先运行一次抓取", "data": None}

            rows = cached.get("rows", [])
            if not rows:
                return {"success": False, "message": "缓存为空", "data": None}

            logger.info("开始为 %d 条数据重新获取 TMDB 信息...", len(rows))
            updated = 0
            for item in rows:
                name = item.get("name", "")
                tmdb_info = self.__search_tmdb_with_cache(name)
                if tmdb_info:
                    poster_path = tmdb_info.get("poster_path", "")
                    item["poster"] = TmdbHelper.get_poster_url(poster_path) or item.get("poster", "")
                    tmdbid = tmdb_info.get("id")
                    if tmdbid:
                        item["tmdbid"] = tmdbid
                        if tmdb_info.get("season"):
                            item["season"] = tmdb_info["season"]
                        actors = self.get_tv_credits(tmdbid)
                        if actors:
                            item["actors"] = actors
                            updated += 1
                time.sleep(0.15)

            cached["rows"] = rows
            cached["timestamp"] = time.time()
            cached["update_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.save_data(self._cache_key, cached)

            elapsed = round(time.time() - start_time, 1)
            logger.info("【刷新数据】完成，耗时 %ss，更新 %d/%d 条", elapsed, updated, len(rows))
            return {"success": True, "message": f"已更新 {updated} 条 TMDB 数据", "data": cached}
        except Exception as e:
            elapsed = round(time.time() - start_time, 1)
            logger.error("【刷新数据】失败（%ss）: %s", elapsed, e)
            return {"success": False, "message": str(e), "data": None}

    def __season_from_cache(self, title: str) -> int:
        """从 TMDB 二级缓存补算季号（纯缓存读取，不联网、不写回）。

        season 字段是后加的，老 rows/老缓存都没有，这里按需补算。

        判据与搜索路径一致：宿主 ``_project_search_results`` 只做单向子串过滤，
        因此「原名能直接命中」说明 TMDB 条目名就含该数字（如「我们的少年时代2」
        是独立剧集），不是季号；只有「原名搜不到、TMDB 名称不含原名」的情形
        （如「问心2」对应 TMDB 的「问心」）才是真季号。
        """
        if not title:
            return 0
        base, season = TmdbHelper.strip_season(title)
        if not season or base == title:
            return 0
        try:
            cached = self.__get_cached_tmdb(title)
        except Exception:
            cached = None
        if not cached or not cached.get("id"):
            return 0
        # 原名仍是 TMDB 名称的子串 → 当初原名就能命中，数字属于片名本身
        if title in (cached.get("name") or ""):
            return 0
        return season

    def get_cache(self):
        """获取缓存数据，不触发抓取。"""
        logger.info("【获取缓存API】收到请求：enabled=%s", self.get_state())
        if not self.get_state():
            logger.info("【获取缓存API】插件未启用，返回未启用状态")
            return {
                "success": True,
                "enabled": False,
                "data": {"rows": [], "total": 0},
                "from_cache": False,
            }
        cached = super().get_data(self._cache_key)
        if cached and isinstance(cached, dict) and cached.get("rows"):
            # 每次读取缓存都重新计算状态，确保订阅/入库操作后状态最新
            for item in cached.get("rows", []):
                # 季号兜底：老 rows 没有该字段，按 TMDB 二级缓存补算（纯缓存读取，不联网），
                # 保证前端能拿到季号，详情弹窗与订阅才能按季工作。
                if item.get("tmdbid") and not item.get("season"):
                    season = self.__season_from_cache(item.get("name", ""))
                    if season:
                        item["season"] = season
                item["status"] = self._check_media_status(
                    item.get("tmdbid", 0), item.get("name", ""), item.get("season") or 0
                )
            logger.info("【获取缓存API】返回缓存数据，共 %d 条", len(cached.get("rows", [])))
            return {"success": True, "enabled": True, "data": cached, "from_cache": True}
        logger.info("【获取缓存API】缓存为空")
        return {"success": True, "enabled": True, "data": {"rows": [], "total": 0}, "from_cache": False}

    def get_season(self, tmdbid: int = None, season: int = None):
        """获取指定季的详情，供详情弹窗按季展示。

        详情弹窗默认走宿主 ``/media/{id}``，返回的是剧集主记录（第 1 季视角）。
        带季数的条目改由本接口取该季的简介/首播/海报/演员。
        """
        logger.info("【获取季详情API】收到请求：tmdbid=%s, season=%s", tmdbid, season)
        if not tmdbid or not season:
            return {"success": False, "message": "缺少 tmdbid 或 season 参数", "data": None}
        try:
            tmdbid = int(tmdbid)
            season = int(season)
        except (TypeError, ValueError):
            return {"success": False, "message": "参数格式不正确", "data": None}
        try:
            detail = self.__get_season_detail(tmdbid, season)
            if not detail:
                return {"success": False, "message": f"未获取到第 {season} 季信息", "data": None}
            cast = ((detail.get("credits") or {}).get("cast") or [])[:20]
            episodes = detail.get("episodes") or []
            data = {
                "season_number": detail.get("season_number") or season,
                "name": detail.get("name") or f"第 {season} 季",
                "overview": detail.get("overview") or "",
                "air_date": detail.get("air_date") or "",
                "poster_path": detail.get("poster_path") or "",
                "vote_average": detail.get("vote_average"),
                "episode_count": len(episodes),
                "cast": cast,
            }
            logger.info("【获取季详情API】返回第 %s 季：%d 集, air_date=%s",
                        season, len(episodes), data["air_date"])
            return {"success": True, "data": data}
        except Exception as e:
            logger.error("【获取季详情API】失败：%s", e)
            return {"success": False, "message": str(e), "data": None}

    def get_cast(self, tmdbid: int = None):
        """获取演员阵容数据（使用 7 天 detail 缓存，一次请求获取 cast+first_air_date）。"""
        logger.info("【获取演员API】收到请求：tmdbid=%s", tmdbid)
        if not tmdbid:
            return {"success": False, "message": "缺少 tmdbid 参数", "data": None}
        try:
            detail = self.__get_cached_detail(tmdbid)
            if not detail:
                api = TmdbApi(language="zh")
                detail = api.tv.details(tmdbid)
                if detail:
                    self.__save_cached_detail(tmdbid, detail)
            if not detail:
                return {"success": False, "message": "获取详情失败", "data": None}
            cast = detail.get("credits", {}).get("cast", [])[:20]
            logger.info("【获取演员API】返回 %d 条演员数据", len(cast))
            return {"success": True, "data": cast}
        except Exception as e:
            logger.error("【获取演员API】失败：%s", e)
            return {"success": False, "message": str(e), "data": None}

    def run_once(self):
        """立即运行1次 API（实时抓取并更新缓存）。"""
        logger.info("【立即运行1次API】收到请求")
        logger.info("【立即运行1次】开始实时抓取...")
        start_time = time.time()
        try:
            heat_list = MaoyanScraper.fetch_heat_list()
            logger.info("抓取到 %d 条热度数据，开始补充 TMDB 信息...", len(heat_list))

            enriched = []
            for item in heat_list:
                name = item.get("name", "")
                tmdb_info = self.__search_tmdb_with_cache(name)
                if tmdb_info:
                    poster_path = tmdb_info.get("poster_path", "")
                    item["poster"] = TmdbHelper.get_poster_url(poster_path) or item.get("poster", "")
                    tmdbid = tmdb_info.get("id")
                    if tmdbid:
                        item["tmdbid"] = tmdbid
                        if tmdb_info.get("season"):
                            item["season"] = tmdb_info["season"]
                        item["status"] = self._check_media_status(
                            tmdbid, name, item.get("season") or 0
                        )
                        actors = self.get_tv_credits(tmdbid)
                        if actors:
                            item["actors"] = actors
                enriched.append(item)
                time.sleep(0.15)

            result = {
                "rows": enriched,
                "timestamp": time.time(),
                "total": len(enriched),
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            self.save_data(self._cache_key, result)

            # 手动刷新也随抓取触发今日上新通知（与自动刷新一致；失败不影响抓取结果）
            try:
                self.__send_remind(force=False, heat_list=enriched)
            except Exception as e:
                logger.error("【立即运行1次】触发今日上新提醒失败: %s", e)

            elapsed = round(time.time() - start_time, 1)
            logger.info("【立即运行1次】完成，耗时 %ss，共 %d 条（已更新缓存）", elapsed, len(enriched))
            return {
                "success": True,
                "message": f"运行完成，耗时 {elapsed}s",
                "data": {"rows": enriched, "total": len(enriched), "elapsed": elapsed},
            }
        except Exception as e:
            elapsed = round(time.time() - start_time, 1)
            logger.error("【立即运行1次】失败（%ss）: %s", elapsed, e)
            return {"success": False, "message": str(e), "data": {"rows": [], "total": 0, "elapsed": elapsed}}
