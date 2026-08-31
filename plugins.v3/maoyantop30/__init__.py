"""
猫眼TOP30探索 - MoviePilot V3 插件
抓取猫眼网播热度 TOP30 剧集，作为 MoviePilot 探索数据源。
参考：芒果TV探索 (mangguodiscover)
"""

import re
import json
from typing import Any, Dict, List, Optional, Tuple

from app.plugins import _PluginBase
from app.schemas import DiscoverMediaSource, DiscoverSourceEventData, Response
from apscheduler.triggers.interval import IntervalTrigger
from app.schemas.types import ChainEventType, MediaSource, MediaType
from app.sdk.cache import cached
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
    猫眼TOP30探索插件，让探索支持猫眼网播热度榜的数据浏览。
    """

    # 插件名称
    plugin_name = "猫眼TOP30探索"
    # 插件描述
    plugin_desc = "让探索支持猫眼电视剧-top30，思路来源于DDSRem大佬的项目实现。"
    # 插件图标
    plugin_icon = "maoyantop30_A.png"
    # 插件版本
    plugin_version = "1.0.3"
    # 插件作者
    plugin_author = "irab"
    # 作者主页
    author_url = "https://github.com/irab-liu"
    # 插件配置项ID前缀
    plugin_config_prefix = "maoyantop30_"
    # 加载顺序
    plugin_order = 99
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _enabled = False
    _refresh_interval = 6
    _cache_key = "maoyantop30_data"

    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled", False)
            self._refresh_interval = int(config.get("refresh_interval", 6))

    def get_state(self) -> bool:
        return self._enabled

    def get_service(self) -> list[dict]:
        """注册定时自动刷新服务。"""
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

    @staticmethod
    def _normalize_media_type(mtype: Any) -> Optional[MediaType]:
        if isinstance(mtype, MediaType):
            return mtype
        try:
            return MediaType(mtype) if mtype else None
        except (TypeError, ValueError):
            return None

    @cached(region="maoyan_top30_discover", ttl=86400, skip_none=True)
    def __fetch_heat_list(self) -> List[Dict[str, Any]]:
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

        return results

    def recognize_media(
        self,
        meta: Any = None,
        mtype: Any = None,
        media_source: Optional[MediaSource] = None,
        media_id: Optional[str] = None,
        episode_group: Optional[str] = None,
        cache: bool = True,
        **kwargs: Any,
    ) -> Any:
        title = getattr(meta, "title", None)
        if not title:
            return None

        media_type = self._normalize_media_type(mtype or getattr(meta, "type", None))
        recognize_meta = MetaInfo(title)
        recognize_meta.type = media_type

        mediainfo = self.chain.run_module(
            "recognize_media",
            meta=recognize_meta,
            mtype=media_type,
            media_source=MediaSource.TMDB,
            media_id=None,
            episode_group=episode_group,
            cache=cache,
        )

        if not mediainfo:
            return None

        mediainfo.media_source = MediaSource.TMDB
        mediainfo.media_id = media_id
        return mediainfo

    async def async_recognize_media(
        self,
        meta: Any = None,
        mtype: Any = None,
        media_source: Optional[MediaSource] = None,
        media_id: Optional[str] = None,
        episode_group: Optional[str] = None,
        cache: bool = True,
        **kwargs: Any,
    ) -> Any:
        title = getattr(meta, "title", None)
        if not title:
            return None

        media_type = self._normalize_media_type(mtype or getattr(meta, "type", None))
        recognize_meta = MetaInfo(title)
        recognize_meta.type = media_type

        mediainfo = await self.chain.async_run_module(
            "async_recognize_media",
            meta=recognize_meta,
            mtype=media_type,
            media_source=MediaSource.TMDB,
            media_id=None,
            episode_group=episode_group,
            cache=cache,
        )

        if not mediainfo:
            return None

        mediainfo.media_source = MediaSource.TMDB
        mediainfo.media_id = media_id
        return mediainfo

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        return [
            {
                "path": "/maoyan_top30_discover",
                "endpoint": self.maoyan_top30_discover,
                "methods": ["GET"],
                "summary": "猫眼TOP30探索数据源",
                "description": "获取猫眼网播热度TOP30剧集数据",
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
                        "text": "启用后，探索页面将支持猫眼网播热度TOP30剧集浏览。系统会按设定间隔自动刷新榜单数据。",
                    },
                ],
            }
        ], {"enabled": False, "refresh_interval": 6}

    def get_page(self) -> List[dict]:
        pass

    def __auto_refresh(self):
        """定时自动刷新：抓取榜单并更新缓存。"""
        logger.info("【定时刷新】开始...")
        try:
            # 清除缓存，下次请求时自动重新抓取
            self.__fetch_heat_list.invalidate()
            logger.info("【定时刷新】完成，缓存已清除")
        except Exception as e:
            logger.error("【定时刷新】失败: %s", e)

    def maoyan_top30_discover(
        self,
        page: int = 1,
        count: int = 30,
    ) -> Response[List[MediaInfo]]:
        def __item_to_media(item: dict) -> MediaInfo:
            # 先尝试从猫眼数据获取海报
            poster = item.get("poster", "") or None
            
            # 如果没有海报，尝试通过 TMDB 搜索获取
            if not poster:
                try:
                    from app.modules.themoviedb.tmdbapi import TmdbApi
                    tmdb_api = TmdbApi(language="zh")
                    tmdb_result = tmdb_api.search_tvs(item.get("name", ""), "")
                    if tmdb_result and len(tmdb_result) > 0:
                        poster_path = tmdb_result[0].get("poster_path", "")
                        if poster_path:
                            poster = f"https://image.tmdb.org/t/p/w500{poster_path}"
                except Exception:
                    pass
            
            return MediaInfo(
                type=MediaType.TV,
                media_source=MediaSource.TMDB,
                title=item.get("name", ""),
                year=None,
                media_id=str(item.get("seriesId", "")),
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

    def stop_service(self):
        pass
