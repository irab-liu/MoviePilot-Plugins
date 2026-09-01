"""
猫眼TOP30探索 - MoviePilot V3 插件
抓取猫眼网播热度 TOP30 剧集，作为 MoviePilot 探索数据源。

数据链路：
猫眼榜单 → TMDB 搜索获取 ID 和海报 → MediaInfo → MoviePilot 探索 → 原生详情页
"""

import re
import json
import hashlib
import threading
from typing import Any, Dict, List, Optional, Tuple

from app.plugins import _PluginBase
from app.schemas import DiscoverMediaSource, DiscoverSourceEventData, Response
from apscheduler.triggers.interval import IntervalTrigger
from app.schemas.types import ChainEventType, MediaSource, MediaType
from app.sdk.config import settings
from app.sdk.events import Event, eventmanager
from app.sdk.logging import logger
from app.sdk.media import MediaInfo, MetaInfo
from app.sdk.network import RequestUtils


# 猫眼热度榜 URL
HEAT_URL = "https://piaofang.maoyan.com/web-heat"

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
    plugin_version = "1.1.3"
    plugin_author = "irab"
    author_url = "https://github.com/irab-liu"
    plugin_config_prefix = "maoyantop30_"
    plugin_order = 99
    auth_level = 1

    # 私有属性
    _enabled = False
    _refresh_interval = 6  # 默认刷新间隔（小时）
    _cache_key = "maoyantop30_data"
    _tmdb_cache_prefix = "maoyantop30_tmdb_"
    _warmup_lock = threading.Lock()
    _warmup_done = False

    def init_plugin(self, config: dict = None):
        """
        初始化插件配置。

        :param config: 插件配置字典，包含 enabled 和 refresh_interval
        """
        if config:
            self._enabled = config.get("enabled", False)
            self._refresh_interval = int(config.get("refresh_interval", 6))
        # 启用时异步预热 TMDB 缓存
        if self._enabled:
            self.__start_warmup()

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

    def __warmup(self):
        """
        预热：抓取榜单并缓存 TMDB 搜索结果。
        纯同步实现，在 daemon 线程中运行，不依赖事件循环。
        """
        logger.info("【预热】开始...")
        try:
            heat_list = self.__fetch_heat_list()
            if not heat_list:
                logger.warning("【预热】榜单数据为空，跳过")
                return
            from app.modules.themoviedb.tmdbapi import TmdbApi
            tmdb_api = TmdbApi(language="zh")
            cached_count = 0
            for item in heat_list:
                title = item.get("name", "")
                if not title:
                    continue
                cache_key = self.__tmdb_cache_key(title)
                if self.get_data(cache_key):
                    continue
                try:
                    result = tmdb_api.search_tvs(title, "")
                    if result:
                        self.save_data(cache_key, self.__tmdb_result_to_serializable(result[0]))
                        cached_count += 1
                except Exception as e:
                    logger.warning("【预热】TMDB 搜索失败 [%s]: %s", title, e)
            logger.info("【预热】完成，缓存 %d 条 TMDB 结果", cached_count)
        except Exception as e:
            logger.error("【预热】异常: %s", e)

    @staticmethod
    def __tmdb_cache_key(title: str) -> str:
        """生成 TMDB 二级缓存 key（绑定榜单时间戳通过一级缓存失效自动过期）"""
        md5 = hashlib.md5(title.encode("utf-8")).hexdigest()[:12]
        return f"maoyantop30_tmdb_{md5}"

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

    def get_state(self) -> bool:
        """返回插件启用状态。"""
        return self._enabled

    def get_service(self) -> list[dict]:
        """
        注册定时自动刷新服务。

        :return: APScheduler 服务配置列表
        """
        if not self.get_state():
            return []
        return [
            {
                "id": "MaoyanTop30.AutoRefresh",
                "name": "猫眼TOP30自动刷新",
                "trigger": IntervalTrigger(hours=self._refresh_interval),
                "func": self.__auto_refresh,
                "kwargs": {},
            }
        ]

    @staticmethod
    def get_media_source() -> List[Dict[str, Any]]:
        return [
            {
                "name": "猫眼TOP30",
                "media_source": MediaSource.TMDB,
                "media_types": [MediaType.TV],
            }
        ]

    def __fetch_heat_list(self) -> List[Dict[str, Any]]:
        # 先尝试从缓存读取
        cached = self.get_data(self._cache_key)
        if cached and isinstance(cached, list):
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
        self.save_data(self._cache_key, results)
        return results

    def recognize_media(self, meta=None, mtype=None, media_source=None, media_id=None, episode_group=None, cache=True, **kwargs):
        return None

    async def async_recognize_media(self, meta=None, mtype=None, media_source=None, media_id=None, episode_group=None, cache=True, **kwargs):
        return None

    def get_api(self) -> List[Dict[str, Any]]:
        return [
            {
                "path": "/maoyan_top30_discover",
                "endpoint": self.maoyan_top30_discover,
                "methods": ["GET"],
                "summary": "猫眼TOP30探索数据源",
            }
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
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 4},
                                "content": [
                                    {
                                        "component": "VSelect",
                                        "props": {
                                            "model": "refresh_interval",
                                            "label": "自动刷新间隔（小时）",
                                            "items": [
                                                {"title": "1小时", "value": 1},
                                                {"title": "2小时", "value": 2},
                                                {"title": "3小时", "value": 3},
                                                {"title": "6小时", "value": 6},
                                                {"title": "12小时", "value": 12},
                                                {"title": "24小时", "value": 24},
                                            ],
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
                ],
            }
        ], {"enabled": False, "refresh_interval": 6}

    def __auto_refresh(self):
        logger.info("【定时刷新】开始...")
        try:
            self.del_data(self._cache_key)
            with self._warmup_lock:
                self._warmup_done = False
            logger.info("【定时刷新】完成")
        except Exception as e:
            logger.error("【定时刷新】失败: %s", e)

    def maoyan_top30_discover(self, page: int = 1, count: int = 30) -> Response[List[MediaInfo]]:
        def __item_to_media(item: dict) -> MediaInfo:
            title = item.get("name", "")
            poster = item.get("poster", "") or None
            tmdbid = None
            tmdb_info = None
            cache_key = self.__tmdb_cache_key(title)
            try:
                cached_info = self.get_data(cache_key)
                if cached_info and isinstance(cached_info, dict):
                    tmdb_info = cached_info
                    logger.debug("【缓存】二级缓存命中: %s", title)
            except Exception:
                pass

            if not tmdb_info:
                try:
                    from app.modules.themoviedb.tmdbapi import TmdbApi
                    tmdb_api = TmdbApi(language="zh")
                    tmdb_result = tmdb_api.search_tvs(title, "")
                    if tmdb_result and len(tmdb_result) > 0:
                        tmdb_info = tmdb_result[0]
                        try:
                            self.save_data(cache_key, self.__tmdb_result_to_serializable(tmdb_info))
                        except Exception:
                            pass
                except Exception:
                    pass

            if tmdb_info:
                tmdbid = tmdb_info.get("id")
                poster_path = tmdb_info.get("poster_path", "")
                if poster_path and not poster:
                    poster = f"https://image.tmdb.org/t/p/w500{poster_path}"

            media_id = str(tmdbid) if tmdbid else str(item.get("seriesId", ""))
            return MediaInfo(
                type=MediaType.TV,
                media_source=MediaSource.TMDB,
                title=title,
                year=None,
                media_id=media_id,
                poster_path=poster,
                overview=f"热度: {item.get('heat', 0)} | 播放: {item.get('plays', '')} | 平台: {item.get('platform', '')}",
            )

        try:
            heat_list = self.__fetch_heat_list()
        except Exception as err:
            logger.error("获取猫眼TOP30数据失败: %s", err)
            return Response(success=True, data=[])
        if not heat_list:
            return Response(success=True, data=[])
        results = [__item_to_media(item) for item in heat_list]
        return Response(success=True, data=results)

    def get_page(self) -> List[dict]:
        return []

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
            filter_params={},
            filter_ui=[],
            depends={},
        )
        if not event_data.extra_sources:
            event_data.extra_sources = [maoyan_source]
        else:
            event_data.extra_sources.append(maoyan_source)