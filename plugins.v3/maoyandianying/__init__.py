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

    @staticmethod
    def search_tv(name: str) -> Optional[Dict[str, Any]]:
        """按剧名搜索 TMDB，返回首条匹配结果；失败或无结果时返回 ``None``。"""
        try:
            api = TmdbApi(language="zh")
            result = api.search_tvs(name, "")
            if result and len(result) > 0:
                logger.debug("TMDB搜索 '%s' → ID %s", name, result[0].get("id"))
                return result[0]
            else:
                logger.warning("TMDB搜索 '%s' 无结果", name)
        except Exception as e:
            logger.error("TMDB搜索 '%s' 失败: %s", name, e)
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


class MaoyanDianYing(_PluginBase):
    _render_mode_logged = False
    """猫眼热度榜插件主类"""

    plugin_name = "猫眼热度榜"
    plugin_desc = "猫眼网播【电视剧+网剧】热度 TOP30 剧集订阅情况，一键订阅。v1.2.1：修改通知触发条件，根据定时抓取到的数据提醒，已推送不重复推送并附订阅状态。"
    plugin_icon = "Moviepilot_A.png"
    plugin_version = "1.2.1"
    plugin_author = "irab"
    author_url = "https://github.com/irab-liu"
    plugin_config_prefix = "maoyandingyue_"
    plugin_order = 50
    auth_level = 1

    _enabled = False
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
            for item in heat_list:
                title = item.get("name", "")
                if not title:
                    continue
                cache_key = self.__tmdb_cache_key(title)
                if self.get_data(cache_key):
                    continue
                try:
                    meta = _create_meta_info(title)
                    if not meta:
                        raise RuntimeError("MoviePilot MetaInfo 不可用")
                    media_info = self.chain.recognize_media(meta=meta, cache=True)
                    if media_info and getattr(media_info, "tmdb_id", None):
                        source = str(getattr(media_info, "media_source", "") or "").lower()
                        if source and source not in ("themoviedb", "tmdb"):
                            logger.warning("【TMDB过滤】%s 返回来源=%s，跳过", title, source)
                            continue
                        logger.info("【TMDB确认】%s 来源=%s ID=%s", title, source or "themoviedb", getattr(media_info, "tmdb_id", None))
                        tmdb_id = getattr(media_info, "tmdb_id", None)
                        # 海报/首播日期/背景图改从 TV 详情（档案）获取，识别只负责提供 tmdb_id
                        detail = self.__get_detail_with_cache(tmdb_id)
                        result = {
                            "id": tmdb_id,
                            "name": (detail or {}).get("name") or media_info.title or title,
                            "poster_path": (detail or {}).get("poster_path") or getattr(media_info, "poster_path", None),
                            "backdrop_path": (detail or {}).get("backdrop_path") or getattr(media_info, "backdrop_path", None),
                            "first_air_date": (detail or {}).get("first_air_date") or getattr(media_info, "first_air_date", None),
                            "media_type": "TV",
                        }
                        self.__save_cached_tmdb(title, result)
                        cached_count += 1
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
        """带二级缓存的 TMDB 搜索（优先复用 host TmdbCache via chain.recognize_media）"""
        cached = self.__get_cached_tmdb(title)
        if cached:
            # 兼容历史缓存：旧数据可能缺海报/首播日期（曾从识别返回值落空写入），
            # 命中时若富信息缺失则补查 TV 详情并回写，避免空值被缓存固化 7 天。
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
            meta = _create_meta_info(title)
            if not meta:
                raise RuntimeError("MoviePilot MetaInfo 不可用")
            media_info = self.chain.recognize_media(meta=meta, cache=True)
            if media_info and getattr(media_info, "tmdb_id", None):
                source = str(getattr(media_info, "media_source", "") or "").lower()
                if source and source not in ("themoviedb", "tmdb"):
                    logger.warning("【TMDB过滤】%s 返回来源=%s，跳过", title, source)
                else:
                    logger.info("【TMDB确认】%s 来源=%s ID=%s", title, source or "themoviedb", getattr(media_info, "tmdb_id", None))
                    tmdb_id = getattr(media_info, "tmdb_id", None)
                    # 海报/首播日期/背景图改从 TV 详情（档案）获取，识别只负责提供 tmdb_id
                    detail = self.__get_detail_with_cache(tmdb_id)
                    result = {
                        "id": tmdb_id,
                        "name": (detail or {}).get("name") or media_info.title or title,
                        "poster_path": (detail or {}).get("poster_path") or getattr(media_info, "poster_path", None),
                        "backdrop_path": (detail or {}).get("backdrop_path") or getattr(media_info, "backdrop_path", None),
                        "first_air_date": (detail or {}).get("first_air_date") or getattr(media_info, "first_air_date", None),
                        "media_type": "TV",
                    }
                    self.__save_cached_tmdb(title, result)
                    logger.debug("【TMDB搜索】'%s' → ID %s (host cache)", title, tmdb_id)
                    return result
        except Exception as e:
            logger.warning("【TMDB搜索】chain.recognize_media '%s' 失败: %s", title, e)
        # Fallback: direct TmdbApi
        try:
            api = TmdbApi(language="zh")
            result = api.search_tvs(title, "")
            if result and len(result) > 0:
                self.__save_cached_tmdb(title, result[0])
                return result[0]
        except Exception as e:
            logger.error("【TMDB搜索】'%s' 失败: %s", title, e)
        return None

    def _get_cached_status(self, tmdbid: int, name: str = "") -> Optional[str]:
        """从短 TTL 缓存读取状态"""
        if not tmdbid:
            return None
        cache_key = f"maoyandingyue_status_{tmdbid}"
        try:
            cached = self.get_data(cache_key)
            if cached and isinstance(cached, dict):
                if time.time() - cached.get("ts", 0) < self._status_cache_ttl:
                    return cached.get("status")
        except Exception:
            pass
        return None

    def _save_cached_status(self, tmdbid: int, status: str) -> None:
        """保存状态到短 TTL 缓存"""
        if not tmdbid:
            return
        cache_key = f"maoyandingyue_status_{tmdbid}"
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
                "path": "/clear-cache",
                "endpoint": self.clear_cache,
                "methods": ["POST"],
                "summary": "清理插件缓存",
                "description": "清理所有插件产生的缓存数据（TMDB、猫眼抓取数据等），不清理定时任务数据和提醒数据",
                "auth": "bear",
            },
        ]

    def _check_media_status(self, tmdbid: int, name: str = "") -> str:
        """按 TMDB 媒体身份返回"影片已入库""订阅已添加"或"未添加订阅"。"""
        if not tmdbid:
            logger.debug("【状态检查】tmdbid 为空，返回未添加")
            return "未添加订阅"

        # 短 TTL 缓存检查
        cached_status = self._get_cached_status(tmdbid, name)
        if cached_status is not None:
            logger.debug("【状态检查】缓存命中：tmdbid=%s, status=%s", tmdbid, cached_status)
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
            self._save_cached_status(tmdbid, "未添加订阅")
            return "未添加订阅"

        if item:
            logger.info(
                "【状态检查】媒体库命中：title=%s, media_source=%s, media_id=%s, item_type=%s",
                getattr(item, "title", ""),
                getattr(item, "media_source", ""),
                getattr(item, "media_id", ""),
                getattr(item, "item_type", ""),
            )
            self._save_cached_status(tmdbid, "影片已入库")
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
                self._save_cached_status(tmdbid, "影片已入库")
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
            self._save_cached_status(tmdbid, "影片已入库")
            return "影片已入库"
        logger.info("【状态检查】整理记录未命中：media_source=%s, media_id=%s", media_source, media_id)

        # 4. 最后查询订阅表
        try:
            subs = self._subscribe_oper.list_by_media_identity(
                media_source=media_source, media_id=media_id
            )
        except Exception as e:
            logger.error("【状态检查】订阅查询异常：media_id=%s, error=%s", media_id, e)
            self._save_cached_status(tmdbid, "未添加订阅")
            return "未添加订阅"

        if subs:
            logger.info("【状态检查】订阅命中：media_source=%s, media_id=%s, count=%s", media_source, media_id, len(subs))
            self._save_cached_status(tmdbid, "订阅已添加")
            return "订阅已添加"

        logger.info("【状态检查】媒体库、整理记录和订阅均未命中：media_source=%s, media_id=%s", media_source, media_id)
        self._save_cached_status(tmdbid, "未添加订阅")
        return "未添加订阅"

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
        }

    def get_page(self) -> list[dict]:
        """Vue 远程组件模式下不再使用 Vuetify JSON 渲染。"""
        logger.info("【数据页面】返回空 JSON，交由远程 Page 组件渲染")
        return []

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
        """为指定剧集添加订阅，并返回 MoviePilot 标准响应结构。"""
        tmdbid = body.get("tmdbid")
        name = str(body.get("name", "")).strip()
        logger.info("【添加订阅】收到请求：%s (TMDB ID: %s)", name, tmdbid)

        # 旧缓存可能没有 TMDB ID。按剧名即时补查，不能把 0 提交给订阅链。
        if not tmdbid and name:
            logger.info("【添加订阅】TMDB ID 为空，开始按剧名补查：%s", name)
            tmdb_info = self.__search_tmdb_with_cache(name)
            if tmdb_info:
                tmdbid = tmdb_info.get("id")
                logger.info("【添加订阅】按剧名补查成功：%s -> %s", name, tmdbid)
                self._update_cached_tmdbid(name=name, tmdbid=tmdbid)

        if not tmdbid:
            logger.warning("【添加订阅】无法获取 TMDB ID：%s", name)
            return {"success": False, "message": f"未能识别《{name or '未知剧集'}》的 TMDB 信息，请先刷新数据", "data": None}

        try:
            tmdbid = int(tmdbid)
            status = self._check_media_status(tmdbid)
            if status == "影片已入库":
                return {"success": False, "message": "影片已入库，无需重复订阅", "data": None}
            if status == "订阅已添加":
                return {"success": False, "message": "已订阅，无需重复订阅", "data": None}

            subscribe_chain = SubscribeChain()
            sub_id, msg = subscribe_chain.add(
                title=name,
                year="",
                mtype=MediaType.TV,
                media_source="themoviedb",
                media_id=str(tmdbid),
                username=None,
            )
            if sub_id:
                logger.info("【添加订阅】成功：%s (TMDB ID: %s, 订阅 ID: %d)", name, tmdbid, sub_id)
                # 清除该剧的状态缓存，避免 loadCache() 命中旧缓存将按钮刷回"未添加订阅"
                try:
                    self.del_data(f"maoyandingyue_status_{tmdbid}")
                except Exception:
                    pass
                return {
                    "success": True,
                    "message": f"订阅已添加：{name}",
                    "data": {"subscribe_id": sub_id, "tmdbid": tmdbid},
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
                          f"主数据 {stats['maoyandingyue_data']} 个、通知推送记录 {stats['maoyandingyue_remind']} 个")
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
                for hit in pending:
                    name = hit.get("name", "")
                    platform = hit.get("platform", "")
                    line = f"📺 {hit.get('rank', 0)}. 《{name}》"
                    if platform:
                        line += f"（{platform}）"
                    line += self.__notify_status_tag(hit)
                    lines.append(line)
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
                        self.post_message(
                            mtype=mtype,
                            title="猫眼热度榜今日上新",
                            text="\n".join(lines),
                            image=random.choice(images) if images else None,
                        )
                        lines = []
                        images = []
                if lines:
                    self.post_message(
                        mtype=mtype,
                        title="猫眼热度榜今日上新",
                        text="\n".join(lines),
                        image=random.choice(images) if images else None,
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
                for item in top5:
                    rank = item.get("rank", 0)
                    name = item.get("name", "")
                    platform = item.get("platform", "")
                    line = f"📺 {rank}. 《{name}》"
                    if platform:
                        line += f"（{platform}）"
                    line += self.__notify_status_tag(item)
                    lines.append(line)
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
                self.post_message(
                    mtype=mtype,
                    title="猫眼热度榜今日上新",
                    text="\n".join(lines),
                    image=top1_image,
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

    def __notify_status_tag(self, item: dict) -> str:
        """通知行附注订阅状态：【已订阅】/【未订阅】（基于媒体库/整理记录/订阅判断）。

        映射：影片已入库、订阅已添加 -> 【已订阅】；未添加订阅 -> 【未订阅】。
        """
        try:
            name = item.get("name", "")
            tmdbid = item.get("tmdbid") or 0
            if not tmdbid:
                tmdb_info = self.__search_tmdb_with_cache(name)
                tmdbid = (tmdb_info or {}).get("id") or 0
            status = self._check_media_status(tmdbid, name)
            return "【未订阅】" if status == "未添加订阅" else "【已订阅】"
        except Exception:
            return ""

    def __is_today_new(self, item: dict) -> bool:
        """判定榜单条目是否为今日上新：TMDB first_air_date 与今天相等。

        使用 detail 缓存（含 first_air_date），命中时无网络请求。
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
            return str(air_date) == datetime.now().date().isoformat()
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
                item["status"] = self._check_media_status(
                    item.get("tmdbid", 0), item.get("name", "")
                )
            logger.info("【获取缓存API】返回缓存数据，共 %d 条", len(cached.get("rows", [])))
            return {"success": True, "enabled": True, "data": cached, "from_cache": True}
        logger.info("【获取缓存API】缓存为空")
        return {"success": True, "enabled": True, "data": {"rows": [], "total": 0}, "from_cache": False}

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
                        item["status"] = self._check_media_status(tmdbid, name)
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
