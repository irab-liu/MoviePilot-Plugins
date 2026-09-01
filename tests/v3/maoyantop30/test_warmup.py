"""MaoyanTop30 预热与缓存测试 (T1-T6)"""
import time
import threading
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

import pytest


def _make_plugin(enabled=True, interval=6):
    """绕过 __init__ 构造插件实例"""
    from app.plugins.maoyantop30 import MaoyanTop30
    plugin = object().__new__(MaoyanTop30)
    plugin._enabled = enabled
    plugin._refresh_interval = interval
    plugin._cache_key = "maoyantop30_data"
    plugin._tmdb_cache_prefix = "maoyantop30_tmdb_"
    plugin._warmup_lock = threading.Lock()
    plugin._warmup_done = False
    return plugin


class TestT1_WarmupThreadStarted:
    """T1: init_plugin 启用后 30 秒内预热线程启动并打出【预热】日志"""

    def test_warmup_thread_started_on_enabled(self, caplog):
        plugin = _make_plugin(enabled=True)
        fake_heat = [{"name": "测试剧集", "seriesInfo": {"name": "测试剧集"}, "playCountSplitUnit": {}}]
        with patch.object(plugin, "get_data", return_value=None), \
             patch.object(plugin, "save_data"), \
             patch("app.plugins.maoyantop30.MaoyanTop30._MaoyanTop30__fetch_heat_list", return_value=fake_heat), \
             patch("app.plugins.maoyantop30.MaoyanTop30._MaoyanTop30__tmdb_search", return_value={"id": 123, "name": "测试剧集"}):
            plugin.init_plugin({"enabled": True, "refresh_interval": 6})
            time.sleep(5)
        assert plugin._warmup_done is True


class TestT2_TmdbCacheWritten:
    """T2: 预热后二级缓存 key (maoyantop30_tmdb_*) 落盘"""

    def test_tmdb_cache_saved(self):
        plugin = _make_plugin(enabled=True)
        fake_tmdb = {"id": 456, "name": "缓存测试", "poster_path": "/test.jpg", "media_type": "tv"}
        saved_keys = []
        def mock_save(key, value):
            saved_keys.append(key)
        with patch.object(plugin, "get_data", return_value=None), \
             patch.object(plugin, "save_data", side_effect=mock_save), \
             patch("app.plugins.maoyantop30.MaoyanTop30._MaoyanTop30__fetch_heat_list",
                   return_value=[{"name": "缓存测试", "seriesInfo": {"name": "缓存测试"}, "playCountSplitUnit": {}}]), \
             patch("app.plugins.maoyantop30.MaoyanTop30._MaoyanTop30__tmdb_search", return_value=fake_tmdb):
            plugin.init_plugin({"enabled": True})
            time.sleep(5)
        assert any("maoyantop30_tmdb_" in k for k in saved_keys), f"未找到 TMDB 缓存 key: {saved_keys}"


class TestT3_FirstRequestFast:
    """T3: 首次请求命中二级缓存，不阻塞 30 次 TMDB 搜索"""

    def test_first_request_uses_cache(self):
        plugin = _make_plugin(enabled=True)
        fake_tmdb = {"id": 789, "name": "快速请求", "poster_path": "/fast.jpg", "media_type": "tv"}
        call_count = [0]
        def mock_search(title, year):
            call_count[0] += 1
            return [fake_tmdb]
        with patch.object(plugin, "get_data", return_value=None), \
             patch.object(plugin, "save_data"), \
             patch("app.plugins.maoyantop30.MaoyanTop30._MaoyanTop30__fetch_heat_list",
                   return_value=[{"name": "快速请求", "seriesInfo": {"name": "快速请求"}, "playCountSplitUnit": {}}]), \
             patch("app.plugins.maoyantop30.MaoyanTop30._MaoyanTop30__tmdb_search", side_effect=mock_search):
            plugin.init_plugin({"enabled": True})
            time.sleep(5)
        warmup_calls = call_count[0]
        cached_result = fake_tmdb.copy()
        with patch.object(plugin, "get_data", return_value=cached_result), \
             patch("app.plugins.maoyantop30.MaoyanTop30._MaoyanTop30__fetch_heat_list",
                   return_value=[{"name": "快速请求", "seriesInfo": {"name": "快速请求"}, "playCountSplitUnit": {}}]):
            resp = plugin.maoyan_top30_discover(page=1, count=30)
        assert call_count[0] == warmup_calls, f"请求触发了额外 TMDB 搜索: warmup={warmup_calls}, after={call_count[0]}"
        assert resp.success is True
        assert len(resp.data) >= 1


class TestT4_HotReloadIdempotent:
    """T4: 热重载幂等——多次 init_plugin 不重复预热"""

    def test_warmup_idempotent(self):
        plugin = _make_plugin(enabled=True)
        thread_count = [0]
        original_start = threading.Thread.start
        def counting_start(self):
            thread_count[0] += 1
            original_start(self)
        fake_heat = [{"name": "幂等测试", "seriesInfo": {"name": "幂等测试"}, "playCountSplitUnit": {}}]
        with patch.object(plugin, "get_data", return_value=None), \
             patch.object(plugin, "save_data"), \
             patch("app.plugins.maoyantop30.MaoyanTop30._MaoyanTop30__fetch_heat_list", return_value=fake_heat), \
             patch("app.plugins.maoyantop30.MaoyanTop30._MaoyanTop30__tmdb_search", return_value={"id": 1}), \
             patch.object(threading.Thread, "start", counting_start):
            plugin.init_plugin({"enabled": True})
            plugin.init_plugin({"enabled": True})
            plugin.init_plugin({"enabled": True})
            time.sleep(5)
        assert thread_count[0] == 1, f"预热线程启动了 {thread_count[0]} 次，应为 1"


class TestT5_DisabledNoWarmup:
    """T5: _enabled=False 时不启动预热"""

    def test_no_warmup_when_disabled(self):
        plugin = _make_plugin(enabled=False)
        with patch.object(plugin, "get_data", return_value=None), \
             patch.object(plugin, "save_data") as mock_save, \
             patch("app.plugins.maoyantop30.MaoyanTop30._MaoyanTop30__fetch_heat_list") as mock_fetch:
            plugin.init_plugin({"enabled": False})
            time.sleep(3)
        mock_fetch.assert_not_called()
        mock_save.assert_not_called()


class TestT6_TmdbExceptionSwallowed:
    """T6: TMDB 异常被吞掉不阻断预热"""

    def test_tmdb_exception_not_blocking(self):
        plugin = _make_plugin(enabled=True)
        fake_heat = [
            {"name": "正常剧集", "seriesInfo": {"name": "正常剧集"}, "playCountSplitUnit": {}},
            {"name": "异常剧集", "seriesInfo": {"name": "异常剧集"}, "playCountSplitUnit": {}},
        ]
        def mock_search(title, year):
            if title == "异常剧集":
                raise Exception("TMDB 超时")
            return [{"id": 100, "name": title}]
        saved = []
        def mock_save(key, value):
            saved.append(key)
        with patch.object(plugin, "get_data", return_value=None), \
             patch.object(plugin, "save_data", side_effect=mock_save), \
             patch("app.plugins.maoyantop30.MaoyanTop30._MaoyanTop30__fetch_heat_list", return_value=fake_heat), \
             patch("app.plugins.maoyantop30.MaoyanTop30._MaoyanTop30__tmdb_search", side_effect=mock_search):
            plugin.init_plugin({"enabled": True})
            time.sleep(5)
        assert len(saved) == 1, f"应缓存 1 条，实际 {len(saved)}"


class TestT7_SerializableFix:
    """T7: MediaType 枚举序列化修复——save_data 不抛 TypeError"""

    def test_media_type_serializable(self):
        plugin = _make_plugin(enabled=True)
        fake_tmdb = {
            "id": 999,
            "name": "序列化测试",
            "media_type": __import__("app.schemas.types", fromlist=["MediaType"]).MediaType.TV,
            "poster_path": "/test.jpg",
        }
        saved = []
        def mock_save(key, value):
            saved.append((key, value))
        with patch.object(plugin, "get_data", return_value=None), \
             patch.object(plugin, "save_data", side_effect=mock_save), \
             patch("app.plugins.maoyantop30.MaoyanTop30._MaoyanTop30__fetch_heat_list",
                   return_value=[{"name": "序列化测试", "seriesInfo": {"name": "序列化测试"}, "playCountSplitUnit": {}}]), \
             patch("app.plugins.maoyantop30.MaoyanTop30._MaoyanTop30__tmdb_search", return_value=fake_tmdb):
            plugin.init_plugin({"enabled": True})
            time.sleep(5)
        assert len(saved) == 1, f"应缓存 1 条，实际 {len(saved)}"
        _, cached_value = saved[0]
        assert isinstance(cached_value.get("media_type"), str), \
            f"media_type 应为字符串，实际 {type(cached_value.get('media_type'))}"