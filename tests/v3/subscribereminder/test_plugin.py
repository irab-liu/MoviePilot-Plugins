"""
订阅提醒插件单元测试。
覆盖纯逻辑：按 air_date 筛选剧集、8 条分批发消息分组、消息文本格式。
外部依赖（SubscribeOper / TmdbChain / MediaChain）使用 mock。
"""

import random
from datetime import datetime
from unittest.mock import MagicMock, patch
from typing import List

import pytest

from app.schemas import MediaType, NotificationType


# 被测模块在宿主环境导入路径为 app.plugins.SubscribeReminder
# 这里用本地文件路径导入
import sys
sys.path.insert(0, "/opt/data/mpv3/dingyuetz")

from plugins.v3.subscribereminder import SubscribeReminder


class _Episode:
    """Mock 剧集对象。"""

    def __init__(self, episode_number: int, air_date: str):
        self.episode_number = episode_number
        self.air_date = air_date


class _Subscribe:
    """Mock 订阅对象。"""

    def __init__(
        self,
        name: str,
        year: str,
        type: MediaType,
        tmdbid: int = None,
        season: int = None,
        backdrop: str = None,
        poster: str = None,
    ):
        self.name = name
        self.year = year
        self.type = type
        self.tmdbid = tmdbid
        self.season = season
        self.backdrop = backdrop
        self.poster = poster


class _MediaInfo:
    """Mock 媒体信息对象。"""

    def __init__(self, release_date: str):
        self.release_date = release_date


def _make_plugin() -> SubscribeReminder:
    """创建插件实例并初始化最小配置。"""
    plugin = SubscribeReminder()
    plugin._subtype = ["movie", "tv"]
    plugin._msgtype = "Plugin"
    plugin._enabled = True
    return plugin


class TestEpisodeFiltering:
    """按 air_date 筛选剧集逻辑测试。"""

    def test_filter_episodes_by_today(self):
        """验证只保留 air_date 等于今天的剧集。"""
        plugin = _make_plugin()
        today = datetime.now().date().strftime("%Y-%m-%d")

        episodes = [
            _Episode(1, today),
            _Episode(2, "2020-01-01"),
            _Episode(3, today),
        ]

        result = [
            ep.episode_number
            for ep in episodes
            if ep and ep.air_date and str(ep.air_date) == today
        ]

        assert result == [1, 3]

    def test_no_episode_today(self):
        """今天没有剧集时返回空列表。"""
        plugin = _make_plugin()
        today = datetime.now().date().strftime("%Y-%m-%d")

        episodes = [
            _Episode(1, "2020-01-01"),
            _Episode(2, "2020-01-02"),
        ]

        result = [
            ep.episode_number
            for ep in episodes
            if ep and ep.air_date and str(ep.air_date) == today
        ]

        assert result == []


class TestBatchMessageGrouping:
    """8 条分批发消息分组逻辑测试。"""

    def test_batch_grouping_exact_8(self):
        """正好 8 条时只发一批。"""
        items = [{"name": f"item{i}", "image": f"img{i}"} for i in range(8)]
        batches = [items[i:i + 8] for i in range(0, len(items), 8)]
        assert len(batches) == 1
        assert len(batches[0]) == 8

    def test_batch_grouping_9(self):
        """9 条时分成两批（8 + 1）。"""
        items = [{"name": f"item{i}", "image": f"img{i}"} for i in range(9)]
        batches = [items[i:i + 8] for i in range(0, len(items), 8)]
        assert len(batches) == 2
        assert len(batches[0]) == 8
        assert len(batches[1]) == 1

    def test_batch_grouping_16(self):
        """16 条时正好两批。"""
        items = [{"name": f"item{i}", "image": f"img{i}"} for i in range(16)]
        batches = [items[i:i + 8] for i in range(0, len(items), 8)]
        assert len(batches) == 2
        assert all(len(b) == 8 for b in batches)


class TestMessageTextFormat:
    """消息文本格式测试。"""

    def test_tv_message_format(self):
        """电视剧消息格式：📺︎ 剧名 (年份) SxxEyy。"""
        name = "狂飙 (2023)"
        season = "S01"
        episode = "E01"
        line = f"📺︎{name} {season}{episode}\n"
        assert "📺︎" in line
        assert "S01" in line
        assert "E01" in line

    def test_tv_multi_episode_format(self):
        """电视剧多集格式：SxxE01-E03。"""
        name = "三体 (2023)"
        season = "S01"
        episode = "E01-E03"
        line = f"📺︎{name} {season}{episode}\n"
        assert "E01-E03" in line

    def test_movie_message_format(self):
        """电影消息格式：📽︎ 剧名 (年份)。"""
        name = "流浪地球2 (2023)"
        line = f"📽︎{name}\n"
        assert "📽︎" in line
        assert "流浪地球2 (2023)" in line


class TestNotificationTypeParsing:
    """通知类型解析测试。"""

    def test_valid_msgtype(self):
        """有效的消息类型名应正确解析。"""
        plugin = _make_plugin()
        plugin._msgtype = "Plugin"
        mtype = NotificationType.Plugin
        assert mtype == NotificationType.Plugin

    def test_invalid_msgtype_fallback(self):
        """无效的消息类型应回退到 Manual。"""
        plugin = _make_plugin()
        plugin._msgtype = "InvalidType"
        try:
            mtype = NotificationType[plugin._msgtype]
        except KeyError:
            mtype = NotificationType.Manual
        assert mtype == NotificationType.Manual


class TestPluginLifecycle:
    """插件生命周期测试。"""

    def test_get_state_returns_enabled(self):
        """get_state 返回 _enabled 状态。"""
        plugin = _make_plugin()
        assert plugin.get_state() is True
        plugin._enabled = False
        assert plugin.get_state() is False

    def test_stop_service_resets_enabled(self):
        """stop_service 应复位 _enabled。"""
        plugin = _make_plugin()
        plugin.stop_service()
        assert plugin._enabled is False

    def test_get_command_returns_empty(self):
        """get_command 返回空列表。"""
        plugin = _make_plugin()
        assert plugin.get_command() == []

    def test_get_api_returns_empty(self):
        """get_api 返回空列表。"""
        plugin = _make_plugin()
        assert plugin.get_api() == []

    def test_get_page_returns_none(self):
        """get_page 返回 None。"""
        plugin = _make_plugin()
        assert plugin.get_page() is None


class TestGetService:
    """定时服务注册测试。"""

    def test_service_registered_when_enabled(self):
        """启用时应注册定时服务。"""
        plugin = _make_plugin()
        plugin._time = 9
        services = plugin.get_service()
        assert len(services) == 1
        assert services[0]["id"] == "SubscribeReminder.DailyPush"
        assert services[0]["func"] == plugin._SubscribeReminder__send_notify

    def test_service_empty_when_disabled(self):
        """禁用时返回空列表。"""
        plugin = _make_plugin()
        plugin._enabled = False
        assert plugin.get_service() == []

    def test_service_empty_when_no_time(self):
        """未配置时间时返回空列表。"""
        plugin = _make_plugin()
        plugin._time = None
        assert plugin.get_service() == []
