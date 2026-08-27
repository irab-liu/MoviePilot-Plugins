"""
IRAB订阅提醒插件单元测试。
"""

import sys
sys.path.insert(0, "/opt/data/mpv3/dingyuetz")

from plugins.v3.irabsubscribereminder import IrabSubscribeReminder


def _make_plugin():
    plugin = IrabSubscribeReminder()
    plugin._subtype = ["movie", "tv"]
    plugin._msgtype = "Plugin"
    plugin._enabled = True
    return plugin


class TestPluginLifecycle:
    def test_get_state(self):
        plugin = _make_plugin()
        assert plugin.get_state() is True
        plugin._enabled = False
        assert plugin.get_state() is False

    def test_stop_service(self):
        plugin = _make_plugin()
        plugin.stop_service()
        assert plugin._enabled is False

    def test_get_command(self):
        plugin = _make_plugin()
        assert plugin.get_command() == []

    def test_get_api(self):
        plugin = _make_plugin()
        assert plugin.get_api() == []

    def test_get_page(self):
        plugin = _make_plugin()
        assert plugin.get_page() is None


class TestGetService:
    def test_service_registered(self):
        plugin = _make_plugin()
        plugin._time = 9
        services = plugin.get_service()
        assert len(services) == 1
        assert services[0]["id"] == "IrabSubscribeReminder.DailyPush"

    def test_service_empty_when_disabled(self):
        plugin = _make_plugin()
        plugin._enabled = False
        assert plugin.get_service() == []

    def test_service_empty_when_no_time(self):
        plugin = _make_plugin()
        plugin._time = None
        assert plugin.get_service() == []
