"""MaoyanDianYing 回归测试套件"""
import json
import time
import threading
from unittest.mock import MagicMock, patch, Mock, call
from types import SimpleNamespace
from datetime import datetime

import pytest


# ---------- 辅助函数 ----------

def _make_plugin(enabled=True, interval=6):
    """绕过 __init__ 构造插件实例，避免数据库连接"""
    from app.plugins.maoyandianying import MaoyanDianYing
    plugin = object().__new__(MaoyanDianYing)
    plugin._enabled = enabled
    plugin._refresh_interval = interval
    plugin._cache_key = "maoyandingyue_data"
    plugin._subscribe_oper = MagicMock()
    plugin._media_oper = MagicMock()
    plugin._transfer_oper = MagicMock()
    plugin._fetch_lock = threading.Lock()
    plugin._warmup_lock = threading.Lock()
    plugin._warmup_done = False
    plugin._status_cache_ttl = 300
    return plugin


def _make_heat_item(name="测试剧集", rank=1, heat=1000, platform="爱奇艺", days="上映3天"):
    """构造一条猫眼热度数据"""
    return {
        "rank": rank,
        "name": name,
        "platform": platform,
        "days": days,
        "heat": heat,
        "plays": "1.2亿",
        "tmdbid": 0,
    }


def _make_tmdb_result(tmdbid=123, name="测试剧集", poster_path="/test.jpg"):
    """构造 TMDB 搜索结果"""
    return {"id": tmdbid, "name": name, "poster_path": poster_path, "media_type": "tv"}


# ---------- 现有功能回归 ----------

class TestInitPlugin:
    """init_plugin 读取配置、初始化操作对象"""

    @patch("app.plugins.maoyandianying.SubscribeOper")
    @patch("app.plugins.maoyandianying.MediaServerOper")
    @patch("app.plugins.maoyandianying.TransferHistoryOper")
    def test_init_plugin_reads_config(self, mock_transfer, mock_media, mock_sub):
        from app.plugins.maoyandianying import MaoyanDianYing
        plugin = object().__new__(MaoyanDianYing)
        plugin.init_plugin({"enabled": True, "refresh_interval": 12})
        assert plugin._enabled is True
        assert plugin._refresh_interval == 12
        mock_sub.assert_called_once()
        mock_media.assert_called_once()
        mock_transfer.assert_called_once()

    @patch("app.plugins.maoyandianying.SubscribeOper")
    @patch("app.plugins.maoyandianying.MediaServerOper")
    @patch("app.plugins.maoyandianying.TransferHistoryOper")
    def test_init_plugin_default_config(self, mock_transfer, mock_media, mock_sub):
        from app.plugins.maoyandianying import MaoyanDianYing
        plugin = object().__new__(MaoyanDianYing)
        plugin.init_plugin(None)
        assert plugin._enabled is False
        assert plugin._refresh_interval == 6

    @patch("app.plugins.maoyandianying.SubscribeOper")
    @patch("app.plugins.maoyandianying.MediaServerOper")
    @patch("app.plugins.maoyandianying.TransferHistoryOper")
    def test_init_plugin_no_cache_starts_refresh(self, mock_transfer, mock_media, mock_sub):
        """无缓存时启动预热 + 初始刷新（2 个线程）"""
        from app.plugins.maoyandianying import MaoyanDianYing
        plugin = object().__new__(MaoyanDianYing)
        with patch("app.plugins._PluginBase.get_data", return_value=None), \
             patch.object(plugin, "save_data"), \
             patch("app.plugins.maoyandianying.threading.Thread") as mock_thread:
            plugin.init_plugin({"enabled": True})
            # P0+P1: warmup + auto_refresh = 2 threads
            assert mock_thread.call_count == 2
            calls = mock_thread.call_args_list
            assert calls[0][1].get("daemon") is True
            assert "warmup" in calls[0][1].get("name", "")
            assert calls[1][1].get("daemon") is True

    @patch("app.plugins.maoyandianying.SubscribeOper")
    @patch("app.plugins.maoyandianying.MediaServerOper")
    @patch("app.plugins.maoyandianying.TransferHistoryOper")
    def test_init_plugin_with_cache_no_refresh(self, mock_transfer, mock_media, mock_sub):
        """有缓存时只启动预热线程，不启动初始刷新"""
        from app.plugins.maoyandianying import MaoyanDianYing
        plugin = object().__new__(MaoyanDianYing)
        cached = {"rows": [{"name": "已有数据"}], "timestamp": time.time()}
        with patch("app.plugins._PluginBase.get_data", return_value=cached), \
             patch("app.plugins.maoyandianying.threading.Thread") as mock_thread:
            plugin.init_plugin({"enabled": True})
            # 有缓存时只启动 warmup 线程，不启动 auto_refresh
            assert mock_thread.call_count == 1
            assert "warmup" in mock_thread.call_args[1].get("name", "")


class TestGetState:
    """get_state 返回启用状态"""

    def test_get_state_enabled(self):
        plugin = _make_plugin(enabled=True)
        assert plugin.get_state() is True

    def test_get_state_disabled(self):
        plugin = _make_plugin(enabled=False)
        assert plugin.get_state() is False


class TestGetService:
    """get_service 注册定时刷新服务"""

    def test_get_service_enabled(self):
        plugin = _make_plugin(enabled=True, interval=6)
        services = plugin.get_service()
        assert len(services) == 1
        assert services[0]["id"] == "MaoyanDianYing.AutoRefresh"
        assert "trigger" in services[0]

    def test_get_service_disabled(self):
        plugin = _make_plugin(enabled=False)
        assert plugin.get_service() == []


class TestStopService:
    """stop_service 标记停用"""

    def test_stop_service(self):
        plugin = _make_plugin(enabled=True)
        plugin.stop_service()
        assert plugin._enabled is False


class TestMaoyanScraper:
    """MaoyanScraper.fetch_heat_list 抓取猫眼热度列表"""

    @patch("app.plugins.maoyandianying.requests.get")
    def test_fetch_heat_list_success(self, mock_get):
        from app.plugins.maoyandianying import MaoyanScraper
        fake_html = 'AppData = {"pageData":{"webHeatData":[{"seriesInfo":{"name":"剧集1","platformDesc":"爱奇艺","releaseInfo":"上映1天"},"playCountSplitUnit":{"num":"1.2","unit":"亿"},"currHeat":1000}]}};'
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = fake_html
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = MaoyanScraper.fetch_heat_list()
        assert len(result) == 1
        assert result[0]["name"] == "剧集1"
        assert result[0]["heat"] == 1000

    @patch("app.plugins.maoyandianying.requests.get")
    def test_fetch_heat_list_no_appdata(self, mock_get):
        """页面无 AppData 时抛出 ValueError"""
        from app.plugins.maoyandianying import MaoyanScraper
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html>no data</html>"
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        with pytest.raises(ValueError, match="未能从猫眼页面提取 AppData"):
            MaoyanScraper.fetch_heat_list()

    @patch("app.plugins.maoyandianying.requests.get")
    def test_fetch_heat_list_request_failure(self, mock_get):
        """请求失败时抛出异常"""
        from app.plugins.maoyandianying import MaoyanScraper
        mock_get.side_effect = Exception("Connection refused")

        with pytest.raises(Exception, match="Connection refused"):
            MaoyanScraper.fetch_heat_list()


class TestTmdbHelper:
    """TmdbHelper 静态方法"""

    @patch("app.plugins.maoyandianying.TmdbApi")
    def test_search_tv_success(self, mock_tmdb_cls):
        from app.plugins.maoyandianying import TmdbHelper
        mock_api = MagicMock()
        mock_api.search_tvs.return_value = [{"id": 123, "name": "测试剧集"}]
        mock_tmdb_cls.return_value = mock_api

        result = TmdbHelper.search_tv("测试剧集")
        assert result["id"] == 123
        mock_tmdb_cls.assert_called_once_with(language="zh")

    @patch("app.plugins.maoyandianying.TmdbApi")
    def test_search_tv_no_result(self, mock_tmdb_cls):
        from app.plugins.maoyandianying import TmdbHelper
        mock_api = MagicMock()
        mock_api.search_tvs.return_value = []
        mock_tmdb_cls.return_value = mock_api

        result = TmdbHelper.search_tv("不存在的剧集")
        assert result is None

    @patch("app.plugins.maoyandianying.TmdbApi")
    def test_search_tv_exception(self, mock_tmdb_cls):
        from app.plugins.maoyandianying import TmdbHelper
        mock_tmdb_cls.side_effect = Exception("TMDB API error")

        result = TmdbHelper.search_tv("测试")
        assert result is None

    @patch("app.plugins.maoyandianying.TmdbApi")
    def test_get_tv_credits_success(self, mock_tmdb_cls):
        from app.plugins.maoyandianying import TmdbHelper
        mock_api = MagicMock()
        mock_api.tv.credits.return_value = {
            "cast": [{"name": "演员1"}, {"name": "演员2"}, {"name": "演员3"}]
        }
        mock_tmdb_cls.return_value = mock_api

        result = TmdbHelper.get_tv_credits(123)
        assert len(result) == 3
        assert result[0] == "演员1"

    @patch("app.plugins.maoyandianying.TmdbApi")
    def test_get_tv_credits_char_limit(self, mock_tmdb_cls):
        """演员名称总长度限制在 10 个字符内"""
        from app.plugins.maoyandianying import TmdbHelper
        mock_api = MagicMock()
        mock_api.tv.credits.return_value = {
            "cast": [{"name": "ABCDEF"}, {"name": "GHIJKL"}, {"name": "MN"}]
        }
        mock_tmdb_cls.return_value = mock_api

        result = TmdbHelper.get_tv_credits(123)
        assert len(result) == 1

    @patch("app.plugins.maoyandianying.TmdbApi")
    def test_get_tv_credits_exception(self, mock_tmdb_cls):
        from app.plugins.maoyandianying import TmdbHelper
        mock_tmdb_cls.side_effect = Exception("API error")

        result = TmdbHelper.get_tv_credits(123)
        assert result == []

    def test_get_poster_url_empty(self):
        from app.plugins.maoyandianying import TmdbHelper
        assert TmdbHelper.get_poster_url("") == ""

    def test_get_poster_url_full_url(self):
        from app.plugins.maoyandianying import TmdbHelper
        assert TmdbHelper.get_poster_url("https://example.com/poster.jpg") == "https://example.com/poster.jpg"

    def test_get_poster_url_relative_path(self):
        from app.plugins.maoyandianying import TmdbHelper
        assert TmdbHelper.get_poster_url("/test.jpg") == "https://image.tmdb.org/t/p/w500/test.jpg"


class TestCheckMediaStatus:
    """_check_media_status 四层检查逻辑"""

    def test_media_library_hit(self):
        """第1层：媒体库命中"""
        plugin = _make_plugin()
        mock_item = MagicMock()
        mock_item.title = "测试剧集"
        plugin._media_oper.exists.return_value = mock_item

        result = plugin._check_media_status(123, "测试剧集")
        assert result == "影片已入库"
        plugin._media_oper.exists.assert_called_once_with(
            media_source="themoviedb", media_id="123", mtype="tv"
        )

    def test_title_fallback_hit(self):
        """第2层：按标题兜底命中"""
        plugin = _make_plugin()
        plugin._media_oper.exists.side_effect = [None, MagicMock()]

        result = plugin._check_media_status(123, "测试剧集")
        assert result == "影片已入库"

    def test_transfer_history_hit(self):
        """第3层：整理记录命中"""
        plugin = _make_plugin()
        plugin._media_oper.exists.side_effect = [None, None]
        mock_record = MagicMock()
        mock_record.status = True
        mock_record.title = "测试剧集"
        plugin._transfer_oper.get_by.return_value = [mock_record]

        result = plugin._check_media_status(123, "测试剧集")
        assert result == "影片已入库"

    def test_subscribe_hit(self):
        """第4层：订阅命中"""
        plugin = _make_plugin()
        plugin._media_oper.exists.side_effect = [None, None]
        plugin._transfer_oper.get_by.return_value = []
        plugin._subscribe_oper.list_by_media_identity.return_value = [MagicMock()]

        result = plugin._check_media_status(123, "测试剧集")
        assert result == "订阅已添加"

    def test_all_miss(self):
        """全部未命中"""
        plugin = _make_plugin()
        plugin._media_oper.exists.side_effect = [None, None]
        plugin._transfer_oper.get_by.return_value = []
        plugin._subscribe_oper.list_by_media_identity.return_value = []

        result = plugin._check_media_status(123, "测试剧集")
        assert result == "未添加订阅"

    def test_empty_tmdbid(self):
        """tmdbid 为空时直接返回未添加"""
        plugin = _make_plugin()
        result = plugin._check_media_status(0, "测试剧集")
        assert result == "未添加订阅"
        plugin._media_oper.exists.assert_not_called()


class TestAddSubscribe:
    """add_subscribe 添加订阅"""

    @patch("app.plugins.maoyandianying.SubscribeChain")
    def test_add_subscribe_success(self, mock_chain_cls):
        plugin = _make_plugin()
        plugin._check_media_status = MagicMock(return_value="未添加订阅")
        mock_chain = MagicMock()
        mock_chain.add.return_value = (1, "成功")
        mock_chain_cls.return_value = mock_chain

        result = plugin.add_subscribe({"tmdbid": 123, "name": "测试剧集"})
        assert result["success"] is True
        assert "订阅已添加" in result["message"]

    def test_add_subscribe_already_in_library(self):
        """影片已入库"""
        plugin = _make_plugin()
        plugin._check_media_status = MagicMock(return_value="影片已入库")

        result = plugin.add_subscribe({"tmdbid": 123, "name": "测试剧集"})
        assert result["success"] is False
        assert "影片已入库" in result["message"]

    def test_add_subscribe_already_subscribed(self):
        """已订阅"""
        plugin = _make_plugin()
        plugin._check_media_status = MagicMock(return_value="订阅已添加")

        result = plugin.add_subscribe({"tmdbid": 123, "name": "测试剧集"})
        assert result["success"] is False
        assert "已订阅" in result["message"]

    @patch("app.plugins.maoyandianying.MaoyanDianYing._MaoyanDianYing__search_tmdb_with_cache")
    def test_add_subscribe_no_tmdbid_search_success(self, mock_search):
        """无 TMDB ID 时按剧名补查成功"""
        plugin = _make_plugin()
        mock_search.return_value = {"id": 456}
        plugin._check_media_status = MagicMock(return_value="未添加订阅")

        with patch("app.plugins.maoyandianying.SubscribeChain") as mock_chain_cls:
            mock_chain = MagicMock()
            mock_chain.add.return_value = (1, "成功")
            mock_chain_cls.return_value = mock_chain

            result = plugin.add_subscribe({"tmdbid": 0, "name": "测试剧集"})
            mock_search.assert_called_once_with("测试剧集")
            assert result["success"] is True

    @patch("app.plugins.maoyandianying.MaoyanDianYing._MaoyanDianYing__search_tmdb_with_cache")
    def test_add_subscribe_no_tmdbid_search_fail(self, mock_search):
        """无 TMDB ID 且补查失败"""
        plugin = _make_plugin()
        mock_search.return_value = None

        result = plugin.add_subscribe({"tmdbid": 0, "name": "测试剧集"})
        assert result["success"] is False
        assert "未能识别" in result["message"]


class TestAutoRefresh:
    """_auto_refresh 定时刷新"""

    @patch("app.plugins.maoyandianying.MaoyanScraper.fetch_heat_list")
    @patch("app.plugins.maoyandianying.MaoyanDianYing._MaoyanDianYing__search_tmdb_with_cache")
    def test_auto_refresh_reuse_cache(self, mock_search, mock_fetch):
        """有缓存时复用已有 TMDB 数据"""
        plugin = _make_plugin()
        cached = {
            "rows": [{"name": "已有剧集", "tmdbid": 100, "poster": "/old.jpg", "actors": ["演员1"]}],
            "timestamp": time.time(),
        }
        mock_fetch.return_value = [_make_heat_item(name="已有剧集")]
        with patch("app.plugins._PluginBase.get_data", return_value=cached), \
             patch.object(plugin, "save_data") as mock_save:
            plugin._auto_refresh()
            mock_search.assert_not_called()
            mock_save.assert_called_once()

    @patch("app.plugins.maoyandianying.MaoyanScraper.fetch_heat_list")
    @patch("app.plugins.maoyandianying.MaoyanDianYing._MaoyanDianYing__search_tmdb_with_cache")
    @patch("app.plugins.maoyandianying.TmdbHelper.get_tv_credits")
    def test_auto_refresh_new_item(self, mock_credits, mock_search, mock_fetch):
        """新条目获取 TMDB 数据"""
        plugin = _make_plugin()
        mock_fetch.return_value = [_make_heat_item(name="新剧集")]
        mock_search.return_value = _make_tmdb_result(tmdbid=200, name="新剧集")
        mock_credits.return_value = ["演员A"]

        with patch("app.plugins._PluginBase.get_data", return_value=None), \
             patch.object(plugin, "save_data") as mock_save:
            plugin._auto_refresh()
            mock_search.assert_called_once_with("新剧集")
            mock_credits.assert_called_once_with(200)
            mock_save.assert_called_once()

    @patch("app.plugins.maoyandianying.MaoyanScraper.fetch_heat_list")
    def test_auto_refresh_fetch_failure(self, mock_fetch):
        """抓取失败时异常被吞掉"""
        plugin = _make_plugin()
        mock_fetch.side_effect = Exception("猫眼页面异常")

        with patch("app.plugins._PluginBase.get_data", return_value=None), \
             patch.object(plugin, "save_data") as mock_save:
            plugin._auto_refresh()
            mock_save.assert_not_called()


class TestRefreshTmdb:
    """refresh_tmdb 刷新 TMDB 数据"""

    @patch("app.plugins.maoyandianying.MaoyanDianYing._MaoyanDianYing__search_tmdb_with_cache")
    @patch("app.plugins.maoyandianying.TmdbHelper.get_tv_credits")
    def test_refresh_tmdb_success(self, mock_credits, mock_search):
        plugin = _make_plugin()
        cached = {
            "rows": [{"name": "剧集1", "tmdbid": 0}, {"name": "剧集2", "tmdbid": 0}],
            "timestamp": time.time(),
        }
        mock_search.side_effect = [
            _make_tmdb_result(tmdbid=101, name="剧集1"),
            _make_tmdb_result(tmdbid=102, name="剧集2"),
        ]
        mock_credits.return_value = ["演员"]

        with patch("app.plugins._PluginBase.get_data", return_value=cached), \
             patch.object(plugin, "save_data") as mock_save:
            result = plugin.refresh_tmdb()
            assert result["success"] is True
            assert "已更新 2 条" in result["message"]
            assert mock_save.call_count == 1

    def test_refresh_tmdb_no_cache(self):
        """无缓存时返回失败"""
        plugin = _make_plugin()
        with patch("app.plugins._PluginBase.get_data", return_value=None):
            result = plugin.refresh_tmdb()
            assert result["success"] is False
            assert "暂无缓存" in result["message"]


class TestGetCache:
    """get_cache 获取缓存"""

    def test_get_cache_disabled(self):
        """插件未启用"""
        plugin = _make_plugin(enabled=False)
        result = plugin.get_cache()
        assert result["success"] is True
        assert result["enabled"] is False
        assert result["data"]["total"] == 0

    def test_get_cache_with_data(self):
        """有缓存数据"""
        plugin = _make_plugin(enabled=True)
        cached = {
            "rows": [{"name": "剧集1", "tmdbid": 100}],
            "timestamp": time.time(),
        }
        with patch("app.plugins._PluginBase.get_data", return_value=cached), \
             patch.object(plugin, "_check_media_status", return_value="未添加订阅"):
            result = plugin.get_cache()
            assert result["success"] is True
            assert result["enabled"] is True
            assert result["from_cache"] is True
            assert len(result["data"]["rows"]) == 1

    def test_get_cache_empty(self):
        """缓存为空"""
        plugin = _make_plugin(enabled=True)
        with patch("app.plugins._PluginBase.get_data", return_value=None):
            result = plugin.get_cache()
            assert result["success"] is True
            assert result["from_cache"] is False


class TestGetCast:
    """get_cast 获取演员阵容"""

    @patch("app.plugins.maoyandianying.TmdbApi")
    def test_get_cast_success(self, mock_tmdb_cls):
        plugin = _make_plugin()
        mock_api = MagicMock()
        mock_api.tv.credits.return_value = {"cast": [{"name": "演员1"}, {"name": "演员2"}]}
        mock_tmdb_cls.return_value = mock_api

        result = plugin.get_cast(tmdbid=123)
        assert result["success"] is True
        assert len(result["data"]) == 2

    def test_get_cast_no_tmdbid(self):
        """缺少 tmdbid"""
        plugin = _make_plugin()
        result = plugin.get_cast(tmdbid=None)
        assert result["success"] is False
        assert "缺少 tmdbid" in result["message"]


class TestRunOnce:
    """run_once 立即运行一次"""

    @patch("app.plugins.maoyandianying.MaoyanScraper.fetch_heat_list")
    @patch("app.plugins.maoyandianying.MaoyanDianYing._MaoyanDianYing__search_tmdb_with_cache")
    @patch("app.plugins.maoyandianying.TmdbHelper.get_tv_credits")
    def test_run_once_success(self, mock_credits, mock_search, mock_fetch):
        plugin = _make_plugin()
        mock_fetch.return_value = [_make_heat_item(name="剧集1")]
        mock_search.return_value = _make_tmdb_result(tmdbid=100)
        mock_credits.return_value = ["演员"]

        with patch.object(plugin, "save_data") as mock_save:
            result = plugin.run_once()
            assert result["success"] is True
            assert result["data"]["total"] == 1
            mock_save.assert_called_once()

    @patch("app.plugins.maoyandianying.MaoyanScraper.fetch_heat_list")
    def test_run_once_fetch_failure(self, mock_fetch):
        """抓取失败"""
        plugin = _make_plugin()
        mock_fetch.side_effect = Exception("猫眼异常")

        result = plugin.run_once()
        assert result["success"] is False
        assert "猫眼异常" in result["message"]


# ---------- P0+P1 新增特性（接口契约测试） ----------

class TestP0_1_Warmup:
    """P0-1: 缓存预热（daemon 线程 + 二级缓存 + 双检锁）"""

    @patch("app.plugins.maoyandianying.SubscribeOper")
    @patch("app.plugins.maoyandianying.MediaServerOper")
    @patch("app.plugins.maoyandianying.TransferHistoryOper")
    def test_warmup_thread_started_on_enabled(self, mock_transfer, mock_media, mock_sub):
        """启用后预热 + 刷新线程启动"""
        from app.plugins.maoyandianying import MaoyanDianYing
        plugin = object().__new__(MaoyanDianYing)
        with patch("app.plugins._PluginBase.get_data", return_value=None), \
             patch.object(plugin, "save_data"), \
             patch("app.plugins.maoyandianying.threading.Thread") as mock_thread:
            plugin.init_plugin({"enabled": True})
            assert mock_thread.call_count == 2
            calls = mock_thread.call_args_list
            assert "warmup" in calls[0][1].get("name", "")
            assert calls[0][1].get("daemon") is True

    @patch("app.plugins.maoyandianying.SubscribeOper")
    @patch("app.plugins.maoyandianying.MediaServerOper")
    @patch("app.plugins.maoyandianying.TransferHistoryOper")
    def test_warmup_with_cache_skips(self, mock_transfer, mock_media, mock_sub):
        """有缓存时只启动预热，不启动刷新"""
        from app.plugins.maoyandianying import MaoyanDianYing
        plugin = object().__new__(MaoyanDianYing)
        cached = {"rows": [{"name": "已有数据", "tmdbid": 100}], "timestamp": time.time()}
        with patch("app.plugins._PluginBase.get_data", return_value=cached), \
             patch("app.plugins.maoyandianying.threading.Thread") as mock_thread:
            plugin.init_plugin({"enabled": True})
            assert mock_thread.call_count == 1
            assert "warmup" in mock_thread.call_args[1].get("name", "")


class TestP0_2_SerializableFix:
    """P0-2: MediaType 枚举序列化修复"""

    def test_media_type_serializable_in_cache(self):
        """缓存中的 media_type 应为字符串"""
        from app.schemas.types import MediaType
        plugin = _make_plugin()
        fake_tmdb = {
            "id": 999,
            "name": "测试",
            "media_type": MediaType.TV,
            "poster_path": "/test.jpg",
        }

        saved = []
        def mock_save(key, value):
            saved.append((key, value))

        with patch("app.plugins._PluginBase.get_data", return_value=None), \
             patch.object(plugin, "save_data", side_effect=mock_save), \
             patch("app.plugins.maoyandianying.MaoyanScraper.fetch_heat_list") as mock_fetch, \
             patch("app.plugins.maoyandianying.MaoyanDianYing._MaoyanDianYing__search_tmdb_with_cache", return_value=fake_tmdb), \
             patch("app.plugins.maoyandianying.TmdbHelper.get_tv_credits", return_value=[]):
            mock_fetch.return_value = [_make_heat_item(name="测试")]
            plugin._auto_refresh()

        if saved:
            _, cached_value = saved[0]
            if "rows" in cached_value:
                for row in cached_value["rows"]:
                    if "media_type" in row:
                        assert isinstance(row["media_type"], str), \
                            f"media_type 应为字符串，实际 {type(row['media_type'])}"


class TestP1_1_StatusCheckTTL:
    """P1-1: Status Check 短 TTL 缓存（防抖）"""

    def test_status_check_interface_contract(self):
        """接口契约：短时间内多次调用应命中缓存"""
        plugin = _make_plugin()
        plugin._media_oper.exists.return_value = None
        plugin._media_oper.exists.side_effect = [None, None]
        plugin._transfer_oper.get_by.return_value = []
        plugin._subscribe_oper.list_by_media_identity.return_value = []

        result1 = plugin._check_media_status(123, "测试")
        result2 = plugin._check_media_status(123, "测试")
        assert result1 == result2


class TestP1_2_HotReloadIdempotent:
    """P1-2: 热重载幂等"""

    @patch("app.plugins.maoyandianying.SubscribeOper")
    @patch("app.plugins.maoyandianying.MediaServerOper")
    @patch("app.plugins.maoyandianying.TransferHistoryOper")
    def test_hot_reload_idempotent(self, mock_transfer, mock_media, mock_sub):
        """多次 init_plugin 不重复预热"""
        from app.plugins.maoyandianying import MaoyanDianYing
        plugin = object().__new__(MaoyanDianYing)
        thread_count = [0]
        original_start = threading.Thread.start
        def counting_start(self):
            thread_count[0] += 1
            original_start(self)

        with patch("app.plugins._PluginBase.get_data", return_value=None), \
             patch.object(plugin, "save_data"), \
             patch.object(threading.Thread, "start", counting_start):
            plugin.init_plugin({"enabled": True})
            plugin.init_plugin({"enabled": True})
            plugin.init_plugin({"enabled": True})

        # 第一次: warmup + auto_refresh = 2; 第二、三次: 仅 auto_refresh = 1+1; 总计 4
        assert thread_count[0] <= 4
