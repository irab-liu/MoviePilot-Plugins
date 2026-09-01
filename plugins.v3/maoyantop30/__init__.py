"""
猫眼TOP30探索 - MoviePilot V3 插件
抓取猫眼网播热度 TOP30 剧集，作为 MoviePilot 探索数据源。

数据链路：
猫眼榜单 → TMDB 搜索获取 ID 和海报 → MediaInfo → MoviePilot 探索 → 原生详情页
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
    plugin_version = "1.1.2"
    plugin_author = "irab"
    author_url = "https://github.com/irab-liu"
    plugin_config_prefix = "maoyantop30_"
    plugin_order = 99
    auth_level = 1

    # 私有属性
    _enabled = False
    _refresh_interval = 6  # 默认刷新间隔（小时）
    _cache_key = "maoyantop30_data"

    def init_plugin(self, config: dict = None):
        """
        初始化插件配置。

        :param config: 插件配置字典，包含 enabled 和 refresh_interval
        """
        if config:
            self._enabled = config.get("enabled", False)
            self._refresh_interval = int(config.get("refresh_interval", 6))

    def get_state(self) -> bool:
        """返回插件启用状态。"""
        return self._enabled

    def get_service(self) -> list[dict]:
        """
        注册定时自动刷新服务。

        服务会按设定间隔清除缓存，下次用户访问时自动重新抓取最新数据。

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
        """
        声明插件的媒体数据源。

        MoviePilot 探索页面会根据此声明创建对应的数据源入口。

        :return: 媒体数据源声明列表
        """
        return [
            {
                "name": "猫眼TOP30",
                "media_source": MediaSource.TMDB,
                "media_types": [MediaType.TV],
            }
        ]

    def __fetch_heat_list(self) -> List[Dict[str, Any]]:
        """
        抓取猫眼网播热度 TOP30 列表。

        数据从猫眼页面的 AppData JSON 中提取，包含剧名、热度、播放数据等。
        结果缓存 24 小时，避免频繁请求。

        :return: 标准化后的热度数据列表
        """
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

        # 从 HTML 中提取 AppData JSON
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

        # 标准化数据格式
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

        # 保存到缓存
        self.save_data(self._cache_key, results)
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
        """
        同步识别媒体信息。

        注意：此方法当前不主动注册（不通过 get_module），保留以备后续扩展。

        :param meta: 媒体元数据
        :param mtype: 媒体类型
        :param media_source: 媒体来源
        :param media_id: 媒体 ID
        :param episode_group: 剧集组
        :param cache: 是否使用缓存
        :return: 识别成功返回 MediaInfo，失败返回 None
        """
        return None

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
        """
        异步识别媒体信息。

        注意：此方法当前不主动注册（不通过 get_module），保留以备后续扩展。

        :param meta: 媒体元数据
        :param mtype: 媒体类型
        :param media_source: 媒体来源
        :param media_id: 媒体 ID
        :param episode_group: 剧集组
        :param cache: 是否使用缓存
        :return: 识别成功返回 MediaInfo，失败返回 None
        """
        return None

    def get_api(self) -> List[Dict[str, Any]]:
        """
        注册插件 API 端点。

        :return: API 端点配置列表
        """
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
        """
        拼装插件配置页面。

        :return: (页面配置, 默认数据)
        """
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

    def __auto_refresh(self):
        """
        定时自动刷新任务。

        清除缓存数据，下次用户访问时自动重新抓取最新数据。
        """
        logger.info("【定时刷新】开始...")
        try:
            self.del_data(self._cache_key)
            logger.info("【定时刷新】完成，缓存已清除")
        except Exception as e:
            logger.error("【定时刷新】失败: %s", e)

    def maoyan_top30_discover(
        self,
        page: int = 1,
        count: int = 30,
    ) -> Response[List[MediaInfo]]:
        """
        猫眼TOP30探索数据 API。

        核心逻辑：
        1. 从缓存获取猫眼榜单数据
        2. 对每条数据调用 TMDB 搜索，获取 TMDB ID 和海报
        3. 返回标准 MediaInfo 列表

        :param page: 页码（暂未分页，固定返回 TOP30）
        :param count: 数量（暂未使用）
        :return: MediaInfo 响应
        """
        def __item_to_media(item: dict) -> MediaInfo:
            """
            将猫眼数据转换为 MoviePilot 标准 MediaInfo。

            关键：media_id 使用 TMDB ID，确保前端能正确加载详情页。

            :param item: 猫眼热度数据项
            :return: MoviePilot MediaInfo 对象
            """
            title = item.get("name", "")
            poster = item.get("poster", "") or None
            tmdbid = None

            # 通过 TMDB 搜索获取标准媒体身份
            try:
                from app.modules.themoviedb.tmdbapi import TmdbApi
                tmdb_api = TmdbApi(language="zh")
                tmdb_result = tmdb_api.search_tvs(title, "")
                if tmdb_result and len(tmdb_result) > 0:
                    tmdb_info = tmdb_result[0]
                    tmdbid = tmdb_info.get("id")
                    poster_path = tmdb_info.get("poster_path", "")
                    # 如果猫眼没有海报，使用 TMDB 海报
                    if poster_path and not poster:
                        poster = f"https://image.tmdb.org/t/p/w500{poster_path}"
            except Exception:
                pass

            # media_id 优先使用 TMDB ID，确保详情页能正确加载
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
        """
        返回插件详情页配置。

        当前插件使用 MoviePilot 探索页作为数据页，不单独实现详情页。

        :return: 空列表
        """
        return []

    def stop_service(self) -> None:
        """
        停止插件服务。

        插件无后台资源需要释放，留空即可。
        """
        logger.info("猫眼TOP30探索插件已停止")

    @eventmanager.register(ChainEventType.DiscoverSource)
    def discover_source(self, event: Event):
        """
        注册为 MoviePilot 探索数据源。

        监听 DiscoverSource 事件，将猫眼TOP30添加到探索数据源列表中。

        :param event: 探索源事件
        """
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
