"""
猫眼TOP30探索 - MoviePilot V3 插件
抓取猫眼网播热度 TOP30 剧集，作为 MoviePilot 探索数据源。

数据链路：
猫眼榜单 → TMDB 搜索获取 ID 和海报 → MediaInfo → MoviePilot 探索 → 原生详情页
"""

import re
import sys as _sys
import base64
import json
import hashlib
import random
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple

from app.plugins import _PluginBase
from app.schemas import DiscoverMediaSource, DiscoverSourceEventData, Response
from apscheduler.triggers.interval import IntervalTrigger
from app.schemas.types import ChainEventType, MediaSource, MediaType
from app.sdk.config import settings
from app.sdk.events import Event, eventmanager
from app.sdk.logging import logger as _raw_logger
from app.sdk.media import MediaInfo, MetaInfo


class _SafeLogger:
    """Python 3.14 logging 递归保护：接近栈顶时静默跳过日志调用。

    宿主 MoviePilot 自定义 log.py 与 Python 3.14 logging 模块组合后，
    callHandlers 与 hdlr.handle 偶发互递归爆栈（RecursionError）。
    此时若再调 logger 会二次爆栈，故在接近栈顶时直接静默跳过。
    """

    def __init__(self, delegate):
        self._delegate = delegate

    def _safe(self):
        depth = 0
        frame = _sys._getframe()
        while frame:
            depth += 1
            frame = frame.f_back
        return depth < (_sys.getrecursionlimit() - 50)

    def info(self, *a, **k):
        if self._safe():
            self._delegate.info(*a, **k)

    def warning(self, *a, **k):
        if self._safe():
            self._delegate.warning(*a, **k)

    def error(self, *a, **k):
        if self._safe():
            self._delegate.error(*a, **k)

    def debug(self, *a, **k):
        if self._safe():
            self._delegate.debug(*a, **k)

    def exception(self, *a, **k):
        if self._safe():
            self._delegate.exception(*a, **k)


logger = _SafeLogger(_raw_logger)
from app.sdk.network import RequestUtils


# TMDB 类型 ID -> 中文名（电影/剧集/综艺共用 id 体系；28/12/14/878 等为电影 genre）
TMDB_GENRES = {
    28: "动作",
    12: "冒险",
    16: "动画",
    35: "喜剧",
    80: "犯罪",
    99: "纪录",
    18: "剧情",
    10751: "家庭",
    10762: "儿童",
    9648: "悬疑",
    10763: "新闻",
    10764: "真人秀",
    10765: "科幻奇幻",
    10766: "肥皂剧",
    10767: "脱口秀",
    10768: "战争政治",
    37: "西部",
    14: "奇幻",
    878: "科幻",
    53: "惊悚",
    27: "恐怖",
    10752: "战争",
    36: "历史",
    10749: "爱情",
    10402: "音乐",
    10759: "动作冒险",
}

# 各种类下"类型"筛选的静态选项（UI 行内再拼"全部"+"其他"）
TYPE_OPTIONS = {
    "电影": ["剧情", "喜剧", "动作", "冒险", "动画", "奇幻", "科幻", "悬疑",
             "惊悚", "犯罪", "恐怖", "家庭", "战争", "爱情", "历史", "纪录", "西部"],
    "综艺": ["真人秀", "脱口秀"],
    "电视剧+网络剧": ["剧情", "悬疑", "喜剧", "犯罪", "动作冒险",
                    "科幻奇幻", "家庭", "动画"],
}

# 榜单缓存 TTL（秒）：3 小时，过期自动重抓（替代定时刷新）
CACHE_TTL = 3 * 3600
# TMDB 识别缓存 TTL：30 天（标题->ID 映射稳定，命中长期缓存，增量识别新条目）
TMDB_CACHE_TTL = 30 * 24 * 3600
# 豆瓣兜底缓存 TTL：命中 30 天 / miss 7 天
DOUBAN_HIT_TTL = 30 * 24 * 3600
DOUBAN_MISS_TTL = 7 * 24 * 3600
# TMDB miss 缓存 TTL：24 小时（国产片/网络电影每天补一次，避免频繁重搜）
TMDB_MISS_TTL = 24 * 3600
# 综艺/电影独立缓存 key（剧集沿用 _cache_key）
VARIETY_CACHE_KEY = "maoyantop30_variety_data"
MOVIE_CACHE_KEY = "maoyantop30_movie_data"
# 探索识别并发数：TMDB 逐条直连的线程数（8 平衡速度与代理稳定性，测试未见流控）
DISCOVER_CONCURRENCY = 8



# 猫眼热度榜 URL
HEAT_URL = "https://piaofang.maoyan.com/web-heat"
# 综艺热度接口（免签，seriesType=2 为综艺）
VARIETY_URL = "https://piaofang.maoyan.com/dashboard/webHeatData"
# 电影票房榜接口（当年综合票房，SSR HTML，免签）
MOVIE_RANK_URL = "https://piaofang.maoyan.com/rankings/year"
# 电影实时综合票房接口（需签名）
MOVIE_AJAX_URL = "https://piaofang.maoyan.com/dashboard-ajax/movie"
# 签名固定 key（veri.js 混淆还原）
MAOYAN_SIGN_KEY = "A013F70DB97834C0A5492378BD76C53A"

# 种类定义
CATEGORY_ALL = "全部"
CATEGORY_MOVIE = "电影"
CATEGORY_VARIETY = "综艺"
CATEGORY_TV = "电视剧+网络剧"

# 请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://piaofang.maoyan.com/",
}


class MaoyanTop30(_PluginBase):
    """
    猫眼TOP30探索插件
    - 抓取猫眼网播热度 TOP30 剧集
    - 通过 TMDB 搜索获取标准媒体身份
    - 注册为 MoviePilot 探索数据源
    - 支持定时自动刷新（可配置间隔）
    """

    # 插件元数据
    plugin_name = "猫眼TOP30探索"
    plugin_desc = "让探索支持猫眼电视剧-top30，思路来源于DDSRem大佬的项目实现。"
    plugin_icon = "maoyantop30_A.png"
    plugin_version = "2.0.1"
    plugin_author = "irab"
    author_url = "https://github.com/irab-liu"
    plugin_config_prefix = "maoyantop30_"
    plugin_order = 99
    auth_level = 1

    # 私有属性
    _enabled = False
    _cache_key = "maoyantop30_data"
    _tmdb_cache_prefix = "maoyantop30_tmdb_"
    _identity_cache_key = "maoyantop30_identities"
    _warmup_lock = threading.Lock()
    _warmup_done = False

    def init_plugin(self, config: dict = None):
        """
        初始化插件配置。

        :param config: 插件配置字典，包含 enabled / reidentify / refresh
        """
        do_reidentify = do_refresh = False
        if config:
            self._enabled = config.get("enabled", False)
            do_reidentify = bool(config.get("reidentify", False))
            do_refresh = bool(config.get("refresh", False))
        # 启用时异步预热 TMDB 缓存
        if self._enabled:
            self.__start_warmup()
        # 一次性动作开关：勾选后点保存触发，触发后立即复位（避免每次保存都重复执行）。
        # refresh 是 reidentify 的超集（清榜单+清识别+重抓+重识别），同时勾选时只跑
        # refresh，避免两个并发预热线程竞态写缓存。
        if do_refresh:
            self.__run_refresh()
            self.__reset_oneoff(config, "refresh")
            self.__reset_oneoff(config, "reidentify")
        elif do_reidentify:
            self.__run_reidentify()
            self.__reset_oneoff(config, "reidentify")

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
            name="maoyantop30_warmup"
        )
        thread.start()
        logger.info("【预热】线程已启动")

    def __trigger_warmup(self):
        """手动触发一次预热（不受 _warmup_done 限制，后台 daemon 线程跑）。

        供设置界面「重新识别海报」「刷新榜单」按钮调用：点击后清缓存并立即
        重新抓取/识别，不影响插件加载期的正常预热节奏。
        """
        thread = threading.Thread(
            target=self.__warmup,
            daemon=True,
            name="maoyantop30_manual_warmup"
        )
        thread.start()
        logger.info("【预热】手动触发线程已启动")

    def __warmup(self):
        """
        预热：抓取榜单并缓存 TMDB 搜索结果。
        纯同步实现，在 daemon 线程中运行，不依赖事件循环。
        """
        logger.info("【预热】开始...")
        total_cached = 0
        # 三类榜单分别预热（剧集/综艺走 TV，电影走 MOVIE + _movie 缓存后缀）
        for category in (CATEGORY_TV, CATEGORY_VARIETY, CATEGORY_MOVIE):
            try:
                heat_list = self.__fetch_category_list(category)
                if not heat_list:
                    logger.warning("【预热】%s 榜单数据为空，跳过", category)
                    continue
                mtype = MediaType.MOVIE if category == CATEGORY_MOVIE else MediaType.TV
                cache_suffix = "_movie" if category == CATEGORY_MOVIE else ""

                def _preheat_one(item: dict) -> int:
                    title = item.get("name", "")
                    if not title:
                        return 0
                    cache_key = self.__tmdb_cache_key(title) + cache_suffix
                    if self.__cache_fresh(self.get_data(cache_key), TMDB_CACHE_TTL):
                        return 0
                    # TMDB miss 缓存：确认搜不到的国产片/网络电影 6 小时内跳过重搜，
                    # 避免每 2 小时预热都对同一批 miss 条目重复打 TMDB
                    miss_key = cache_key + "_miss"
                    try:
                        if self.__cache_fresh(self.get_data(miss_key), TMDB_MISS_TTL):
                            return 0
                    except Exception:
                        pass
                    try:
                        year = self.__extract_year(item)
                        result = self.__tmdb_search(
                            self.__normalize_title(title), year, mtype)
                        if result:
                            best = self.__best_tmdb_match(title, result, year)
                            if best:
                                self.save_data(cache_key, {"ts": time.time(),
                                   **self.__tmdb_result_to_serializable(best)})
                                return 1
                        # 豆瓣兜底：TMDB miss 或网络故障都尝试（命中时上面已 return）
                        self.__douban_match(title, year, mtype)
                        # 仅"确认无结果"（空列表，非网络故障 None）才写 miss 缓存，
                        # 网络故障不污染 miss 缓存，下次预热仍会重试 TMDB + 豆瓣
                        if isinstance(result, list) and not result:
                            try:
                                self.save_data(miss_key, {"ts": time.time()})
                            except Exception:
                                pass
                    except Exception as e:
                        logger.warning("【预热】TMDB 搜索失败 [%s]: %s",
                                       title, e)
                    return 0

                with ThreadPoolExecutor(max_workers=DISCOVER_CONCURRENCY) as pool:
                    cached_count = sum(pool.map(_preheat_one, heat_list))
                total_cached += cached_count
                logger.info("【预热】%s 完成，缓存 %d 条 TMDB 结果",
                            category, cached_count)
            except Exception as e:
                logger.error("【预热】%s 异常: %s", category, e)
        logger.info("【预热】全部完成，共缓存 %d 条 TMDB 结果", total_cached)

    @staticmethod
    def __tmdb_cache_key(title: str) -> str:
        """生成 TMDB 二级缓存 key（v2 版本，强制失效旧版错误缓存）"""
        md5 = hashlib.md5(title.encode("utf-8")).hexdigest()[:12]
        return f"maoyantop30_tmdb2_{md5}"

    @staticmethod
    def __normalize_title(title: str) -> str:
        """
        规范化搜索标题：去掉季数/期数/年份后缀，提升 TMDB 命中率。

        - "心动的信号 第九季" -> "心动的信号"
        - "地球超新鲜 第2季" -> "地球超新鲜"
        - "说唱巅峰对决2026" -> "说唱巅峰对决"
        """
        if not title:
            return ""
        t = title.strip()
        # 去 "第X季/第X期/第X辑/第X部" 后缀（X 支持中文与阿拉伯数字，含空格分隔）
        t2 = re.sub(r"[\s\-·]*第[一二三四五六七八九十\d]+[季期辑部集]", "", t)
        # 去尾部 4 位年份（"xxx2026" -> "xxx"）
        t2 = re.sub(r"[\s\-·]*\d{4}$", "", t2)
        # 去尾部系列数字（"一饭封神2"/"这是我的西游2" -> 主条目）
        # 注意先剥年份再剥数字，避免把 "2026" 当系列号
        t2 = re.sub(r"[\s\-·]*\d+$", "", t2)
        # 去首尾空白
        return t2.strip()

    @staticmethod
    def __title_variants(title: str) -> list:
        """生成宽松搜索候选标题，用于豆瓣严格匹配失败后的兜底。

        覆盖猫眼片名与豆瓣条目的常见差异：
        - 去书名号/引号（《XX》 -> XX）
        - 去副标题（XX：YY / XX - YY / XX·YY -> XX）
        - 去尾部括号（XX（2026） -> XX）
        只返回与原名不同的候选，按优先级排序。
        """
        variants = []
        t = (title or "").strip()
        if not t:
            return variants
        cleaned = re.sub(r"[《》〈〉「」『』\"'“”]", "", t).strip()
        if cleaned and cleaned != t:
            variants.append(cleaned)
        for sep in ("：", ":", " - ", " — ", "·", "｜", "|"):
            if sep in t:
                head = t.split(sep)[0].strip()
                if head and head != t and head not in variants:
                    variants.append(head)
        stripped = re.sub(r"[（(].*?[）)]\s*$", "", t).strip()
        if stripped and stripped != t and stripped not in variants:
            variants.append(stripped)
        return variants

    @staticmethod
    def __extract_year(item: dict) -> Optional[str]:
        """从榜单条目中提取年份：优先上映日期，其次标题尾部年份。"""
        days = item.get("days", "") or ""
        m = re.search(r"(19|20)\d{2}", days)
        if m:
            return m.group(0)
        name = item.get("name", "") or ""
        m = re.search(r"(19|20)\d{2}$", name.strip())
        if m:
            return m.group(0)
        return None

    def __get_tmdb_api_key(self) -> Optional[str]:
        """读取宿主 TMDB API key（仅实例化，不触发网络请求，不踩雷）。"""
        try:
            from app.modules.themoviedb.tmdbapi import TmdbApi
            key = getattr(TmdbApi(language="zh").tmdb, "api_key", None)
            if key:
                return str(key)
        except Exception:
            pass
        try:
            from app.runtime.config import Settings
            key = getattr(Settings(), "TMDB_API_KEY", None)
            if key:
                return str(key)
        except Exception:
            pass
        return None

    @staticmethod
    def __tmdb_api_domain() -> str:
        """读取宿主 TMDB API 域名（支持镜像域名配置），失败回退官方域名。

        国内环境直连 api.themoviedb.org 常被墙/无 IPv6 路由（Connection refused），
        宿主允许在设置里把 TMDB_API_DOMAIN 配成镜像域名，插件必须跟随宿主配置
        而非硬编码官方域名。
        """
        try:
            domain = getattr(settings, "TMDB_API_DOMAIN", None)
            if isinstance(domain, str) and domain.strip():
                return domain.strip()
        except Exception:
            pass
        return "api.themoviedb.org"

    @staticmethod
    def __tmdb_image_url(path: str, size: str = "w500") -> str:
        """按宿主配置构造 TMDB 图片 URL（支持镜像域名），失败回退官方域名。"""
        if not path:
            return ""
        try:
            fn = getattr(settings, "TMDB_IMAGE_URL", None)
            if callable(fn):
                url = fn(path, size)
                if isinstance(url, str) and url:
                    return url
        except Exception:
            pass
        try:
            domain = getattr(settings, "TMDB_IMAGE_DOMAIN", None)
            if isinstance(domain, str) and domain.strip():
                return f"https://{domain.strip()}/t/p/{size}/{path.lstrip('/')}"
        except Exception:
            pass
        return f"https://image.tmdb.org/t/p/{size}/{path.lstrip('/')}"

    def __tmdb_search(self, title: str, year: Optional[str] = None,
                       mtype: MediaType = MediaType.TV) -> Optional[list]:
        """
        TMDB 搜索（自建直连，绕开宿主 tmdbv3api 的 cookiejar 递归雷）。

        宿主 TmdbApi.search_tvs/search_movies 有子串过滤（"阿凡达3" 搜不到
        "阿凡达：火与烬"）；tmdbv3api 底层请求在容器 Python 3.14 下偶发
        RecursionError（http.cookiejar 互递归）。这里仅从宿主 TmdbApi 读
        API key，用 urllib 裸请求（默认 opener 无 CookieJar，等价 curl）
        直连 TMDB REST API，既保留原始结果又避开宿主网络栈的雷。

        注意：此方法为同步实现，异步场景请用 __tmdb_search_async（线程池包装）。
        """
        api_key = self.__get_tmdb_api_key()
        if not api_key:
            return None
        try:
            import urllib.request
            import urllib.parse
            kind = "movie" if mtype == MediaType.MOVIE else "tv"
            def _do_search(_year):
                params = {"api_key": api_key, "query": title, "language": "zh-CN"}
                if _year:
                    params["year" if kind == "movie" else "first_air_date_year"] = str(_year)
                url = "https://%s/3/search/%s?%s" % (
                    self.__tmdb_api_domain(), kind, urllib.parse.urlencode(params))
                req = urllib.request.Request(url, headers={
                    "User-Agent": "Mozilla/5.0 (MoviePilot MaoyanTop30)"})
                with urllib.request.urlopen(req, timeout=12) as resp:
                    data = json.loads(resp.read().decode("utf-8", "replace"))
                return data.get("results") or []
            results = _do_search(year)
            # 综艺/剧集标题尾部年份是"第N季/年份标识"，非首播年份：
            # 带年份搜不到时降级为不带年份重试（如"披荆斩棘2026"→2021 首播）
            if not results and year:
                results = _do_search(None)
            return results
        except RecursionError:
            return None
        except Exception as e:
            logger.warning("TMDB 直连搜索失败 [%s/%s]: %s", mtype, title, e)
            return None

    async def __tmdb_search_async(self, title: str, year: Optional[str] = None,
                                   mtype: MediaType = MediaType.TV) -> Optional[list]:
        """__tmdb_search 的异步包装：在线程池中执行，不阻塞事件循环。"""
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                None, self.__tmdb_search, title, year, mtype)
        except Exception as e:
            logger.warning("TMDB 异步搜索异常 [%s/%s]: %s", mtype, title, e)
            return None

    def __read_douban_cache(self, title: str, year: Optional[str] = None) -> dict:
        """纯读豆瓣兜底缓存（不触发网络），命中返回 dict（含 id/pic/year），否则 {}。"""
        norm = self.__normalize_title(title)
        if not norm:
            return {}
        cache_key = "maoyantop30_douban2_" + hashlib.md5(
            f"{norm}|{year or ''}".encode("utf-8")).hexdigest()[:12]
        try:
            cached = self.get_data(cache_key)
            if isinstance(cached, dict) and cached.get("id"):
                if self.__cache_fresh(cached, DOUBAN_HIT_TTL):
                    return cached
        except Exception:
            pass
        return {}

    def __douban_match(self, title: str, year: Optional[str] = None,
                       mtype: MediaType = MediaType.MOVIE) -> dict:
        """
        TMDB 未命中时用宿主豆瓣链兜底。

        调用 chain.match_doubaninfo（宿主内置 douban 模块，自带限速重试）。
        结果缓存到 maoyantop30_douban_ 前缀，避免每次探索请求都打豆瓣。
        带年份搜不到时自动去掉年份重试一次（豆瓣条目可能缺年份字段）。
        """
        norm = self.__normalize_title(title)
        if not norm:
            return {}
        cache_key = "maoyantop30_douban2_" + hashlib.md5(
            f"{norm}|{year or ''}".encode("utf-8")).hexdigest()[:12]
        try:
            cached = self.get_data(cache_key)
            if isinstance(cached, dict) and "id" in cached:
                if cached.get("id"):
                    # 命中缓存：6 小时内有效，过期重搜
                    if self.__cache_fresh(cached, DOUBAN_HIT_TTL):
                        return cached
                else:
                    # miss 缓存：7 天内短路不重搜，过期重试
                    if self.__cache_fresh(cached, DOUBAN_MISS_TTL):
                        return {}
        except Exception:
            pass
        try:
            result = self.chain.match_doubaninfo(
                name=norm, mtype=mtype,
                year=str(year) if year else None, raise_exception=False)
            if not result and year:
                result = self.chain.match_doubaninfo(
                    name=norm, mtype=mtype, year=None, raise_exception=False)
            # 宽松匹配：模块响应但搜不到（空 dict）时换候选标题重试；None（模块未启用）则跳过
            if isinstance(result, dict) and not result:
                for variant in self.__title_variants(norm):
                    result = self.chain.match_doubaninfo(
                        name=variant, mtype=mtype, year=None, raise_exception=False)
                    if result and result.get("id"):
                        logger.info(
                            "猫眼TOP30豆瓣宽松匹配 [%s] -> [%s] 命中", norm, variant)
                        break
            if result and result.get("id"):
                item = {
                    "id": str(result.get("id")),
                    "title": result.get("title") or norm,
                    "year": result.get("year"),
                }
                pic_url = self.__douban_poster(result, mtype)
                if pic_url:
                    item["pic"] = pic_url
                try:
                    self.save_data(cache_key, {"ts": time.time(), **item})
                except Exception:
                    pass
                logger.info("猫眼TOP30豆瓣兜底命中 [%s] -> %s", norm, item["id"])
                return item
            # 豆瓣也未命中：区分「模块未响应」vs「搜索无结果」以便定位，再写 miss 缓存
            if result is None:
                logger.warning(
                    "猫眼TOP30豆瓣兜底未命中 [%s]：豆瓣模块未启用或未响应"
                    "（请检查 设置→模块→豆瓣 是否已启用）", norm)
            else:
                logger.warning(
                    "猫眼TOP30豆瓣兜底未命中 [%s/%s]：豆瓣搜索无匹配结果"
                    "（标题或年份对不上，可去豆瓣官网核对条目名）",
                    norm, year or "-")
            try:
                self.save_data(cache_key, {"ts": time.time(), "id": None})
            except Exception:
                pass
        except Exception as e:
            logger.warning("猫眼TOP30豆瓣兜底异常 [%s]: %s", norm, e)
        return {}

    def __douban_poster(self, item: dict, mtype: MediaType) -> str:
        """
        从豆瓣条目/详情提取海报 URL。

        search 接口的 target 通常无 pic 字段；先用 chain.douban_info
        详情接口补一次（详情确认含 pic.large/pic.normal），仍无则退回
        条目自身多字段兜底（cover/cover_img/cover_url/image）。
        """
        pic = item.get("pic") or {}
        if isinstance(pic, dict):
            url = pic.get("large") or pic.get("normal") or ""
            if url:
                return url
        try:
            detail = self.chain.douban_info(
                str(item.get("id")), mtype, raise_exception=False)
            if isinstance(detail, dict):
                dpic = detail.get("pic") or {}
                if isinstance(dpic, dict):
                    url = dpic.get("large") or dpic.get("normal") or ""
                    if url:
                        return url
        except Exception as e:
            logger.warning("猫眼TOP30豆瓣详情海报失败 [%s]: %s",
                           item.get("id"), e)
        for key in ("cover", "cover_img", "cover_url", "image"):
            v = item.get(key) or {}
            if isinstance(v, dict):
                url = v.get("url") or v.get("large") or v.get("normal") or ""
            elif isinstance(v, str):
                url = v
            else:
                url = ""
            if url:
                return url
        return ""

    @staticmethod
    def __best_tmdb_match(title: str, results: list,
                          year: Optional[str] = None) -> Optional[dict]:
        """
        从 TMDB 搜索结果中选最匹配的条目。

        优先级：精确匹配 > 年份一致的候选 > 包含且最短 > 第一条。
        """
        if not results:
            return None
        # 1. 精确匹配
        for r in results:
            if r.get("name", "") == title:
                return r
        # 2. 年份一致优先（release_date / first_air_date 前缀为年份）
        if year:
            for r in results:
                rel = (r.get("release_date") or r.get("first_air_date") or "")
                if rel.startswith(year):
                    return r
        # 3. 双向包含匹配：
        #    - "阿凡达3" in "阿凡达3：火与烬"（搜索词是结果子串）
        #    - "这是我的西游" in "这是我的西游2"（结果是搜索词子串，季数在末尾）
        candidates = [
            r for r in results
            if title in r.get("name", "") or r.get("name", "") in title
        ]
        if candidates:
            # 优先选与搜索词等长的（最贴近），其次最短
            return min(candidates,
                       key=lambda r: abs(len(r.get("name", "")) - len(title)))
        # 4. 规范化标题相等匹配（季数/年份后缀差异）
        norm = MaoyanTop30.__normalize_title(title)
        if norm:
            for r in results:
                if MaoyanTop30.__normalize_title(r.get("name", "")) == norm:
                    return r
        # 5. 兜底：取第一条
        return results[0]

    @staticmethod
    def __tmdb_result_to_serializable(tmdb_info: dict) -> dict:
        """将 TMDB 搜索结果转换为 JSON 可序列化 dict（处理 MediaType 枚举）"""
        if not tmdb_info:
            return tmdb_info
        result = dict(tmdb_info)
        # MediaType 枚举无法直接 JSON 序列化，转为字符串值
        if "media_type" in result and hasattr(result["media_type"], "value"):
            result["media_type"] = result["media_type"].value
        return result

    def __item_type(self, item: dict,
                   category: str = CATEGORY_TV) -> str:
        """
        从 TMDB 二级缓存中解析榜单条目的类型（中文名）。

        电影条目缓存 key 带 _movie 后缀，剧集/综艺用 tmdb2 前缀。
        无缓存或未命中映射表时返回空串（归属“全部”/“其他”）。
        """
        title = item.get("name", "")
        if not title:
            return ""
        cache_key = self.__tmdb_cache_key(title)
        if category == CATEGORY_MOVIE:
            cache_key += "_movie"
        try:
            cached = self.get_data(cache_key)
        except Exception:
            return ""
        if not self.__cache_fresh(cached, TMDB_CACHE_TTL):
            return ""
        for gid in (cached.get("genre_ids") or []):
            if gid in TMDB_GENRES:
                return TMDB_GENRES[gid]
        return ""

    def maoyan_category_filter_ui(self) -> List[dict]:
        """生成探索页种类筛选 UI（电影/综艺/电视剧+网络剧）"""
        chips = [
            {
                "component": "VChip",
                "props": {"filter": True, "tile": True, "value": value},
                "text": value,
            }
            for value in [CATEGORY_TV, CATEGORY_VARIETY, CATEGORY_MOVIE]
        ]
        return [
            {
                "component": "div",
                "props": {"class": "flex justify-start items-center"},
                "content": [
                    {
                        "component": "div",
                        "props": {"class": "mr-5"},
                        "content": [{"component": "VLabel", "text": "种类"}],
                    },
                    {
                        "component": "VChipGroup",
                        "props": {"model": "category"},
                        "content": chips,
                    },
                ],
            }
        ]

    def maoyan_filter_ui(self) -> List[dict]:
        """
        生成探索页类型筛选 UI（随种类联动）。

        电影/综艺/电视剧+网络剧 各一行 VChipGroup，用 show 表达式切换：
        点击种类时仅显示对应类型行（FormRender 支持任意 JS 表达式）。
        每行选项 = 全部 + 该种类静态类型 + 其他（兜底未命中条目）。
        剧集行为默认行：种类未选或为"电视剧+网络剧"时显示。
        """
        def _type_row(show: str, types: list) -> dict:
            chips = [
                {"component": "VChip", "props": {"filter": True, "tile": True,
                                                 "value": value},
                 "text": value}
                for value in ["全部"] + list(types) + ["其他"]
            ]
            return {
                "component": "div",
                "props": {"class": "flex justify-start items-center",
                          "show": show},
                "content": [
                    {
                        "component": "div",
                        "props": {"class": "mr-5"},
                        "content": [{"component": "VLabel", "text": "题材"}],
                    },
                    {
                        "component": "VChipGroup",
                        "props": {"model": "type"},
                        "content": chips,
                    },
                ],
            }

        return [
            _type_row("{{category == '电影'}}", TYPE_OPTIONS[CATEGORY_MOVIE]),
            _type_row("{{category == '综艺'}}", TYPE_OPTIONS[CATEGORY_VARIETY]),
            _type_row("{{category == '电视剧+网络剧' || !category}}",
                      TYPE_OPTIONS[CATEGORY_TV]),
        ]

    def get_state(self) -> bool:
        """返回插件启用状态。"""
        return self._enabled

    def get_service(self) -> list[dict]:
        """
        后台缓存预热：每 3 小时跑一次，补齐 TMDB/豆瓣二级缓存（增量识别）。

        探索页已改为纯读缓存（不现场识别），海报与题材依赖后台预热提前
        写入缓存。命中缓存 TTL 拉长到 30 天后，预热实际只识别新上榜条目
        （老条目命中缓存直接跳过），3 小时周期足够及时补齐新增条目。
        __warmup 为同步实现，APScheduler 在线程池执行。
        """
        if not self.get_state():
            return []
        return [{
            "id": "MaoyanTop30.Warmup",
            "name": "猫眼TOP30缓存预热",
            "trigger": IntervalTrigger(hours=3),
            "func": self.__warmup,
            "kwargs": {},
        }]

    # 注意：不注册 get_module()，避免宿主识别链轮询我们插件。
    # v1.1.4 没有 get_module()，订阅添加时宿主不轮询我们，不会踩雷。

    def __save_identities(self, category: str, heat_list: List[Dict[str, Any]]) -> None:
        """保存 media_id -> 标题/种类 映射，供 recognize_media 反查。"""
        if not heat_list:
            return
        identities = self.get_data(self._identity_cache_key) or {}
        for item in heat_list:
            media_id = str(item.get("seriesId") or item.get("movieId") or "")
            title = item.get("name", "")
            if not media_id or not title:
                continue
            identities[media_id] = {
                "title": title,
                "category": category,
                "year": self.__extract_year(item),
            }
        self.save_data(self._identity_cache_key, dict(list(identities.items())[-2000:]))

    def __cache_fresh(self, cached: dict, ttl: float) -> bool:
        """判断缓存是否在 TTL 有效期内；无 ts 的旧版缓存视为有效（识别结果稳定）。"""
        if not isinstance(cached, dict):
            return False
        ts = cached.get("ts")
        if not ts:
            return True
        return time.time() - ts <= ttl

    def __clear_recognition_cache(self) -> int:
        """清空 TMDB/豆瓣识别缓存（tmdb2_/douban2_ 前缀），返回清除条数。

        供设置界面「重新识别海报」「刷新榜单」按钮调用；榜单数据不受影响。
        """
        cleared = 0
        try:
            rows = self.get_data() or []
        except Exception:
            rows = []
        for row in rows:
            key = getattr(row, "key", None) or ""
            if (key.startswith("maoyantop30_tmdb2_")
                    or key.startswith("maoyantop30_douban2_")):
                try:
                    self.del_data(key)
                    cleared += 1
                except Exception:
                    pass
        return cleared

    def __clear_list_cache(self) -> None:
        """清空三类榜单缓存（剧集/综艺/电影），供「刷新榜单」按钮调用。"""
        for key in (self._cache_key, VARIETY_CACHE_KEY, MOVIE_CACHE_KEY):
            try:
                self.del_data(key)
            except Exception:
                pass

    def __read_cached_list(self, key: str, date_check: bool = False):
        """
        读取榜单缓存：TTL（3 小时）内且（可选）日期一致时返回列表，否则 None。

        :param key: 缓存 key
        :param date_check: 校验缓存日期 == 今天（电影票房按天切换）
        """
        try:
            import datetime
            cached = self.get_data(key)
            if not isinstance(cached, dict) or not isinstance(
                    cached.get("items"), list):
                return None
            ts = cached.get("ts") or 0
            if time.time() - ts > CACHE_TTL:
                return None
            if date_check and cached.get("date") != datetime.date.today().strftime(
                    "%Y%m%d"):
                return None
            return cached["items"]
        except Exception:
            return None

    def __save_cached_list(self, key: str, items: list, date: str = "") -> None:
        """保存榜单缓存（带 ts 时间戳，供 TTL 校验）。"""
        try:
            import datetime
            self.save_data(key, {
                "ts": time.time(),
                "items": items,
                "date": date or datetime.date.today().strftime("%Y%m%d"),
            })
        except Exception:
            pass

    def __fetch_heat_list(self) -> List[Dict[str, Any]]:
        # 先尝试从缓存读取（3 小时 TTL）
        cached = self.__read_cached_list(self._cache_key)
        if cached is not None:
            logger.debug("缓存命中（%d 条）", len(cached))
            return cached

        logger.info("开始抓取猫眼热度列表: %s", HEAT_URL)
        try:
            resp = RequestUtils(headers=HEADERS, timeout=15).get_res(HEAT_URL)
            if resp is None or not resp.ok:
                logger.error("猫眼热度列表请求失败: %s", resp.status_code if resp else "None")
                return []
        except Exception as e:
            logger.error("猫眼热度列表请求异常: %s", e)
            return []

        match = re.search(r'AppData\s*=\s*(\{.*?\});', resp.text, re.DOTALL)
        if not match:
            logger.error("未能从猫眼页面匹配 AppData 数据")
            return []
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError as e:
            logger.error("猫眼 AppData JSON 解析失败: %s", e)
            return []

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
                "seriesId": series.get("seriesId", 0),
                "poster": series.get("poster", "") or series.get("img", ""),
            })
        self.__save_cached_list(self._cache_key, results)
        return results

    def __fetch_variety_list(self) -> List[Dict[str, Any]]:
        """抓取猫眼综艺热度榜（免签 JSON 接口）"""
        cached = self.__read_cached_list(VARIETY_CACHE_KEY)
        if cached is not None:
            logger.debug("综艺缓存命中（%d 条）", len(cached))
            return cached
        logger.info("开始抓取猫眼综艺列表: %s", VARIETY_URL)
        params = {"seriesType": "2", "platformType": "", "showDate": "2",
                  "dateType": "0", "rankType": "0", "limit": ""}
        try:
            resp = RequestUtils(headers=HEADERS, timeout=15).get_res(
                VARIETY_URL, params=params)
            if resp is None or not resp.ok:
                logger.error("综艺列表请求失败: %s",
                             resp.status_code if resp else "None")
                return []
        except Exception as e:
            logger.error("综艺列表请求异常: %s", e)
            return []
        try:
            body = resp.json()
            heat_list = (body.get("dataList", {}).get("list") or [])
        except Exception as e:
            logger.error("综艺数据解析失败: %s", e)
            return []
        results = []
        for idx, item in enumerate(heat_list[:30]):
            series = item.get("seriesInfo", {})
            results.append({
                "rank": idx + 1,
                "name": series.get("name", ""),
                "platform": series.get("platformDesc", ""),
                "days": series.get("releaseInfo", ""),
                "heat": item.get("currHeat", 0),
                "plays": "",
                "seriesId": series.get("seriesId", 0),
                "poster": series.get("poster", "") or series.get("img", ""),
            })
        logger.info("成功解析综艺列表，共 %d 条", len(results))
        self.__save_cached_list(VARIETY_CACHE_KEY, results)
        return results

    @staticmethod
    def __maoyan_sign(params: dict) -> dict:
        """
        生成猫眼签名参数（还原自 veri.js 的 getQueryKey）。

        签名串：method/timeStamp/User-Agent(b64)/index/channelId/sVersion/key
        顺序固定，md5 后作为 signKey；key 字段不随请求发送。
        """
        ts = int(time.time() * 1000)
        ua_b64 = base64.b64encode(HEADERS["User-Agent"].encode()).decode()
        index = int(1000 * random.random() + 1)
        raw = "&".join([
            f"method=GET",
            f"timeStamp={ts}",
            f"User-Agent={ua_b64}",
            f"index={index}",
            f"channelId=40009",
            f"sVersion=2",
            f"key={MAOYAN_SIGN_KEY}",
        ])
        sign = hashlib.md5(raw.encode()).hexdigest()
        signed = dict(params)
        signed.update({
            "method": "GET",
            "timeStamp": str(ts),
            "User-Agent": ua_b64,
            "index": str(index),
            "channelId": "40009",
            "sVersion": "2",
            "signKey": sign,
        })
        return signed

    def __fetch_movie_list(self) -> List[Dict[str, Any]]:
        """抓取猫眼当日实时综合票房榜（dashboard-ajax/movie，需签名）"""
        import datetime
        today = datetime.date.today()
        cached = self.__read_cached_list(MOVIE_CACHE_KEY, date_check=True)
        if cached is not None:
            logger.debug("电影缓存命中（%d 条）", len(cached))
            return cached
        logger.info("开始抓取电影综合票房: %s", MOVIE_AJAX_URL)
        try:
            # 免签：实测 dashboard-ajax/movie 直接带 showDate=YYYYMMDD 即返回
            # 200（连测 5/5 稳定），无需 veri.js 签名。
            params = {"showDate": today.strftime("%Y%m%d")}
            resp = RequestUtils(headers=HEADERS, timeout=15).get_res(
                MOVIE_AJAX_URL, params=params)
            if resp is None or not resp.ok:
                logger.error("电影票房请求失败: %s",
                             resp.status_code if resp else "None")
                return []
            body = resp.json()
        except Exception as e:
            logger.error("电影票房请求异常: %s", e)
            return []
        movie_list = body.get("movieList") or {}
        items = movie_list.get("list") or []
        results = []
        for idx, item in enumerate(items[:30]):
            info = item.get("movieInfo", {})
            # 实时票房为字体加密数字，无法直接解析；用明文累计票房
            results.append({
                "rank": idx + 1,
                "name": info.get("movieName", ""),
                "platform": "院线",
                "days": info.get("releaseInfo", ""),
                "heat": 0,
                "plays": "",
                "seriesId": info.get("movieId", 0),
                "poster": "",
                "box_office": item.get("sumBoxDesc", ""),
                "box_rate": item.get("boxRate", ""),
                "show_count": item.get("showCount", ""),
            })
        logger.info("成功解析电影综合票房，共 %d 条", len(results))
        self.__save_cached_list(MOVIE_CACHE_KEY, results, date=today.strftime("%Y%m%d"))
        return results

    def __fetch_category_list(self, category: str) -> List[Dict[str, Any]]:
        """按种类抓取榜单数据"""
        if category == CATEGORY_MOVIE:
            return self.__fetch_movie_list()
        if category == CATEGORY_VARIETY:
            return self.__fetch_variety_list()
        return self.__fetch_heat_list()

    @staticmethod
    def __source_matches(media_source) -> bool:
        """
        判断媒体来源是否为猫眼TOP30可处理的 TMDB 源。

        兼容两种形态：
        - 枚举：MediaSource.TMDB（str(枚举) 在 Py3.11+ 为 "MediaSource.TMDB"，value 为 "themoviedb"）
        - 字符串："tmdb" / "themoviedb" / "maoyan"
        """
        src = getattr(media_source, "value", media_source)
        src = str(src or "").lower()
        if src in {"themoviedb", "tmdb", "maoyan"}:
            return True
        return "mediasource.tmdb" in src or "mediasource.maoyan" in src

    def __resolve_identity(self, media_id: str) -> Optional[dict]:
        """按 media_id 反查标题与种类（identities 缓存）。"""
        if not media_id:
            return None
        try:
            identities = self.get_data(self._identity_cache_key) or {}
        except Exception:
            return None
        return identities.get(str(media_id))

    def __resolve_media_id(self, title: str, year: Optional[str],
                           media_type: MediaType) -> tuple:
        """
        自解析远端媒体 ID（TMDB -> 豆瓣兜底），不触发宿主识别链。

        直接走本插件 __tmdb_search/__douban_match（自有缓存），拿到的
        ID 交上层以 media_id 方式调宿主识别：宿主按 ID 走原生模块直接
        出结果，不再进入 SUPPLEMENT 插件轮询——消除递归（RecursionError）
        与按标题识别带来的全插件轮询日志放大。

        注意：此方法为同步实现，异步场景请用 __resolve_media_id_async。
        """
        norm = self.__normalize_title(title)
        if norm:
            try:
                tmdb_results = self.__tmdb_search(title, year, media_type)
            except Exception:
                tmdb_results = []
            best = self.__best_tmdb_match(title, tmdb_results, year) \
                if tmdb_results else None
            if best and best.get("id"):
                return MediaSource.TMDB, str(best["id"])
        douban_item = self.__douban_match(title, year, media_type)
        if douban_item and douban_item.get("id"):
            return MediaSource.Douban, str(douban_item["id"])
        return None, None

    async def __resolve_media_id_async(self, title: str, year: Optional[str],
                                        media_type: MediaType) -> tuple:
        """__resolve_media_id 的异步包装：TMDB 搜索在线程池中执行。"""
        norm = self.__normalize_title(title)
        if norm:
            try:
                tmdb_results = await self.__tmdb_search_async(title, year, media_type)
            except Exception:
                tmdb_results = []
            best = self.__best_tmdb_match(title, tmdb_results, year) \
                if tmdb_results else None
            if best and best.get("id"):
                return MediaSource.TMDB, str(best["id"])
        douban_item = self.__douban_match(title, year, media_type)
        if douban_item and douban_item.get("id"):
            return MediaSource.Douban, str(douban_item["id"])
        return None, None

    def recognize_media(self, meta=None, mtype=None, media_source=None, media_id=None,
                        episode_group=None, cache=True, **kwargs):
        """
        按标题识别媒体（探索条目点开详情时宿主兜底调用）。

        猫眼榜单的 media_id 可能不是 TMDB ID（电影/缓存未命中），通过
        identities 反查标题后，先自解析远端 ID（TMDB -> 豆瓣，走插件
        自有缓存），再带 media_id 调宿主识别：宿主按 ID 走原生模块，
        不进入 SUPPLEMENT 轮询，避免递归与日志放大。
        """
        # 仅处理本插件数据源（兼容枚举与字符串形态）
        if not self.__source_matches(media_source):
            return None
        identity = self.__resolve_identity(media_id)
        title = None
        category = CATEGORY_TV
        if identity:
            title = identity.get("title")
            category = identity.get("category", CATEGORY_TV)
        title = title or getattr(meta, "title", None) or getattr(meta, "name", None)
        if not title:
            return None
        media_type = mtype
        if media_type is None:
            media_type = getattr(meta, "type", None)
        if media_type is None:
            media_type = MediaType.MOVIE if category == CATEGORY_MOVIE else MediaType.TV
        year = (identity or {}).get("year") or getattr(meta, "year", None)
        # 自解析远端 ID（TMDB -> 豆瓣兜底），带 ID 调宿主识别
        resolved_source, resolved_id = self.__resolve_media_id(
            title, year, media_type)
        if not resolved_source or not resolved_id:
            return None
        recognize_meta = MetaInfo(title)
        recognize_meta.year = year
        recognize_meta.type = media_type
        try:
            mediainfo = self.chain.run_module(
                "recognize_media",
                meta=recognize_meta,
                mtype=media_type,
                media_source=resolved_source,
                media_id=resolved_id,
                episode_group=episode_group,
                cache=cache,
            )
        except Exception as e:
            logger.warning("猫眼TOP30辅助识别失败 [%s]: %s", title, e)
            return None
        return mediainfo

    async def async_recognize_media(self, meta=None, mtype=None, media_source=None, media_id=None,
                                    episode_group=None, cache=True, **kwargs):
        """异步版按标题识别媒体（同样先自解析 ID 再带 ID 调宿主）。"""
        if not self.__source_matches(media_source):
            return None
        identity = self.__resolve_identity(media_id)
        title = None
        category = CATEGORY_TV
        if identity:
            title = identity.get("title")
            category = identity.get("category", CATEGORY_TV)
        title = title or getattr(meta, "title", None) or getattr(meta, "name", None)
        if not title:
            return None
        media_type = mtype
        if media_type is None:
            media_type = getattr(meta, "type", None)
        if media_type is None:
            media_type = MediaType.MOVIE if category == CATEGORY_MOVIE else MediaType.TV
        year = (identity or {}).get("year") or getattr(meta, "year", None)
        resolved_source, resolved_id = await self.__resolve_media_id_async(
            title, year, media_type)
        if not resolved_source or not resolved_id:
            return None
        recognize_meta = MetaInfo(title)
        recognize_meta.year = year
        recognize_meta.type = media_type
        try:
            mediainfo = await self.chain.async_run_module(
                "async_recognize_media",
                meta=recognize_meta,
                mtype=media_type,
                media_source=resolved_source,
                media_id=resolved_id,
                episode_group=episode_group,
                cache=cache,
            )
        except Exception as e:
            logger.warning("猫眼TOP30异步辅助识别失败 [%s]: %s", title, e)
            return None
        return mediainfo

    @staticmethod
    def __poster_proxy_url(title: str, category: str, year: Optional[str]) -> str:
        """生成指向本插件 poster 代理接口的相对路径（探索页 miss 条目用）。"""
        from urllib.parse import quote
        params = [
            "title=%s" % quote(str(title)),
            "category=%s" % quote(str(category)),
        ]
        if year:
            params.append("year=%s" % quote(str(year)))
        params.append("apikey=%s" % quote(str(settings.API_TOKEN)))
        return "/api/v1/plugin/MaoyanTop30/poster?%s" % "&".join(params)

    def get_poster(self, title: str = None, category: str = None,
                   year: str = None):
        """探索页懒加载海报代理：查缓存 -> 现场识别 -> 302 重定向海报图。

        前端 MediaCard 对 poster_path 非空条目用 <img> 异步加载，加载期间显示
        骨架屏；本接口识别到海报后 302 重定向到真实图片地址，浏览器自动跟进，
        实现"加载中 -> 识别完成自动补图"，无需重新进入探索页。
        """
        from starlette.responses import RedirectResponse, Response
        if not title:
            return Response(status_code=404)
        title = str(title).strip()
        category = category or CATEGORY_TV
        mtype = MediaType.MOVIE if category == CATEGORY_MOVIE else MediaType.TV
        cache_suffix = "_movie" if category == CATEGORY_MOVIE else ""
        cache_key = self.__tmdb_cache_key(title) + cache_suffix
        # 1. TMDB 缓存命中 -> 直接重定向
        try:
            cached = self.get_data(cache_key)
            if self.__cache_fresh(cached, TMDB_CACHE_TTL):
                pp = (cached or {}).get("poster_path", "")
                if pp:
                    return RedirectResponse(self.__tmdb_image_url(pp))
        except Exception:
            pass
        # 2. 豆瓣缓存命中 -> 直接重定向
        try:
            d = self.__read_douban_cache(title, year)
            if d and d.get("pic"):
                return RedirectResponse(str(d["pic"]))
        except Exception:
            pass
        # 3. 现场识别 TMDB（结果写缓存，下次秒回）
        try:
            results = self.__tmdb_search(self.__normalize_title(title), year, mtype)
            if results:
                best = self.__best_tmdb_match(title, results, year)
                if best and best.get("poster_path"):
                    try:
                        self.save_data(cache_key, {"ts": time.time(),
                                     **self.__tmdb_result_to_serializable(best)})
                    except Exception:
                        pass
                    return RedirectResponse(
                        self.__tmdb_image_url(best["poster_path"]))
        except Exception:
            pass
        # 4. 豆瓣兜底（结果自带缓存）
        try:
            d = self.__douban_match(title, year, mtype)
            if d and d.get("pic"):
                return RedirectResponse(str(d["pic"]))
        except Exception:
            pass
        return Response(status_code=404)

    def __run_reidentify(self):
        """重新识别海报/题材：清空识别缓存并后台重识别（保存时触发的一次性动作）。"""
        try:
            cleared = self.__clear_recognition_cache()
            self.__trigger_warmup()
            logger.info("猫眼TOP30重新识别：已清空 %d 条识别缓存，后台重识别中", cleared)
        except Exception as e:
            logger.error("猫眼TOP30重新识别失败: %s", e)

    def __run_refresh(self):
        """刷新榜单：清空榜单+识别缓存，重抓猫眼榜单并重识别（保存时触发的一次性动作）。"""
        try:
            self.__clear_list_cache()
            cleared = self.__clear_recognition_cache()
            self.__trigger_warmup()
            logger.info("猫眼TOP30刷新榜单：已清空榜单缓存与 %d 条识别缓存，后台重抓+重识别中", cleared)
        except Exception as e:
            logger.error("猫眼TOP30刷新榜单失败: %s", e)

    def __reset_oneoff(self, config: dict, key: str):
        """复位一次性动作开关：写回配置置 False，避免每次保存都重复触发。"""
        try:
            cfg = dict(config or {})
            if cfg.get(key):
                cfg[key] = False
                self.update_config(cfg)
        except Exception:
            pass

    def get_api(self) -> List[Dict[str, Any]]:
        return [
            {
                "path": "/maoyan_top30_discover",
                "endpoint": self.maoyan_top30_discover,
                "methods": ["GET"],
                "summary": "猫眼TOP30探索数据源",
            },
            {
                "path": "/poster",
                "endpoint": self.get_poster,
                "methods": ["GET"],
                "summary": "猫眼TOP30懒加载海报代理",
            },
        ]

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
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
                                        "props": {
                                            "model": "enabled",
                                            "label": "启用插件",
                                        },
                                    }
                                ],
                            },
                        ],
                    },
                    {
                        "component": "VAlert",
                        "props": {
                            "type": "info",
                            "variant": "tonal",
                            "density": "compact",
                            "class": "mt-3",
                        },
                        "text": "启用后，探索页面将支持猫眼网播热度TOP30剧集浏览。",
                    },
                    {
                        "component": "VSwitch",
                        "props": {
                            "model": "reidentify",
                            "label": "保存时重新识别海报",
                        },
                    },
                    {
                        "component": "VAlert",
                        "props": {
                            "type": "info",
                            "variant": "tonal",
                            "density": "compact",
                            "class": "mt-1",
                        },
                        "text": "勾选后点击保存：清空已缓存的 TMDB/豆瓣识别结果，后台重新识别海报与题材（海报错误或识别不准时使用）。",
                    },
                    {
                        "component": "VSwitch",
                        "props": {
                            "model": "refresh",
                            "label": "保存时刷新榜单",
                        },
                    },
                    {
                        "component": "VAlert",
                        "props": {
                            "type": "info",
                            "variant": "tonal",
                            "density": "compact",
                            "class": "mt-1",
                        },
                        "text": "勾选后点击保存：清空榜单缓存并重新抓取猫眼榜单、重新匹配海报（榜单数据有误时使用）。",
                    },
                ],
            }
        ], {"enabled": False, "reidentify": False, "refresh": False}

    def maoyan_top30_discover(self,
                             category: str = None,
                             type: str = None,
                             page: int = 1,
                             count: int = 30) -> Response[List[MediaInfo]]:
        def __item_to_media(item: dict, category: str = CATEGORY_TV) -> MediaInfo:
            """纯读缓存：TMDB 命中给完整，豆瓣缓存兜底，双 miss 给标题条目（media_id 空）。"""
            title = item.get("name", "")
            poster = item.get("poster", "") or None
            if category == CATEGORY_MOVIE:
                movie_year = self.__extract_year(item)
                movie_cache_key = self.__tmdb_cache_key(title) + "_movie"
                try:
                    cached_m = self.get_data(movie_cache_key)
                    if self.__cache_fresh(cached_m, TMDB_CACHE_TTL):
                        movie_id = cached_m.get("id")
                        poster_path_m = cached_m.get("poster_path", "")
                        if poster_path_m and not poster:
                            poster = self.__tmdb_image_url(poster_path_m)
                        return MediaInfo(
                            type=MediaType.MOVIE,
                            media_source=MediaSource.TMDB,
                            title=title,
                            year=None,
                            media_id=str(movie_id) if movie_id else "",
                            poster_path=poster,
                            overview=f"票房: {item.get('box_office', '')} | 上映: {item.get('days', '')} | 场次: {item.get('show_count', '')}",
                        )
                except Exception:
                    pass
                douban_item = self.__read_douban_cache(title, movie_year)
                if douban_item:
                    return MediaInfo(
                        type=MediaType.MOVIE,
                        media_source=MediaSource.Douban,
                        title=title,
                        year=douban_item.get("year"),
                        media_id=douban_item["id"],
                        poster_path=douban_item.get("pic") or poster,
                        overview=f"票房: {item.get('box_office', '')} | 上映: {item.get('days', '')} | 场次: {item.get('show_count', '')}",
                    )
                return MediaInfo(
                    type=MediaType.MOVIE,
                    media_source=MediaSource.TMDB,
                    title=title,
                    year=None,
                    media_id="",
                    poster_path=poster or self.__poster_proxy_url(
                        title, category, self.__extract_year(item)),
                    overview=f"票房: {item.get('box_office', '')} | 上映: {item.get('days', '')} | 场次: {item.get('show_count', '')}",
                )
            # 剧集/综艺：纯读 TMDB 缓存 -> 豆瓣缓存兜底 -> 标题条目
            cache_key = self.__tmdb_cache_key(title)
            try:
                cached_info = self.get_data(cache_key)
                if self.__cache_fresh(cached_info, TMDB_CACHE_TTL):
                    tmdbid = cached_info.get("id")
                    poster_path = cached_info.get("poster_path", "")
                    if poster_path and not poster:
                        poster = self.__tmdb_image_url(poster_path)
                    return MediaInfo(
                        type=MediaType.TV,
                        media_source=MediaSource.TMDB,
                        title=title,
                        year=None,
                        media_id=str(tmdbid) if tmdbid else "",
                        poster_path=poster,
                        overview=f"热度: {item.get('heat', 0)} | 播放: {item.get('plays', '')} | 平台: {item.get('platform', '')}",
                    )
            except Exception:
                pass
            douban_item = self.__read_douban_cache(title, self.__extract_year(item))
            if douban_item:
                return MediaInfo(
                    type=MediaType.TV,
                    media_source=MediaSource.Douban,
                    title=title,
                    year=douban_item.get("year"),
                    media_id=douban_item["id"],
                    poster_path=douban_item.get("pic") or poster,
                    overview=f"热度: {item.get('heat', 0)} | 播放: {item.get('plays', '')} | 平台: {item.get('platform', '')}",
                )
            return MediaInfo(
                type=MediaType.TV,
                media_source=MediaSource.TMDB,
                title=title,
                year=None,
                media_id="",
                poster_path=poster or self.__poster_proxy_url(
                    title, category, self.__extract_year(item)),
                overview=f"热度: {item.get('heat', 0)} | 播放: {item.get('plays', '')} | 平台: {item.get('platform', '')}",
            )

        # 种类归一：None/"全部" -> 电视剧+网络剧（默认）
        category = category or CATEGORY_ALL
        if category == CATEGORY_ALL:
            category = CATEGORY_TV
        try:
            heat_list = self.__fetch_category_list(category)
        except Exception as err:
            logger.error("获取猫眼TOP30数据失败: %s", err)
            return Response(success=True, data=[])
        if not heat_list:
            return Response(success=True, data=[])
        # 按类型过滤：type 为空/"全部"不过滤；"其他"反向匹配（无类型/未命中映射表）
        if type and type != "全部":
            known = set(TYPE_OPTIONS.get(category, TYPE_OPTIONS[CATEGORY_TV]))
            if type == "其他":
                heat_list = [item for item in heat_list
                             if self.__item_type(item, category) not in known]
            else:
                heat_list = [item for item in heat_list
                             if self.__item_type(item, category) == type]
        # 并发识别：命中缓存秒回，miss 的并发走 TMDB/豆瓣，8 线程保持顺序
        with ThreadPoolExecutor(max_workers=DISCOVER_CONCURRENCY) as pool:
            results = list(pool.map(
                lambda it: __item_to_media(it, category), heat_list))
        try:
            self.__save_identities(category, heat_list)
        except Exception as e:
            logger.warning("保存识别映射失败: %s", e)
        return Response(success=True, data=results)

    def get_page(self) -> List[dict]:
        pass

    def stop_service(self) -> None:
        with self._warmup_lock:
            self._warmup_done = False
        logger.info("猫眼TOP30探索插件已停止")

    @eventmanager.register(ChainEventType.DiscoverSource)
    def discover_source(self, event: Event):
        if not self._enabled:
            return
        event_data: DiscoverSourceEventData = event.event_data
        maoyan_source = DiscoverMediaSource(
            name="猫眼TOP30",
            media_source=MediaSource.TMDB,
            mediaid_prefix="maoyan",
            api_path=f"plugin/MaoyanTop30/maoyan_top30_discover?apikey={settings.API_TOKEN}",
            filter_params={"category": None, "type": None},
            filter_ui=self.maoyan_category_filter_ui() + self.maoyan_filter_ui(),
            depends={"type": ["category"]},
        )
        if not event_data.extra_sources:
            event_data.extra_sources = [maoyan_source]
        else:
            event_data.extra_sources.append(maoyan_source)