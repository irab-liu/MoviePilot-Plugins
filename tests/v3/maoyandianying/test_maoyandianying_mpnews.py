"""MaoyanDianYing mpnews 图文推送（企业微信）回归测试。

覆盖：开关默认关闭、关闭时行为不变、打开时改走 mpnews、失败自动回退、
素材上传与缓存、access_token 复用宿主实例、42001 过期重试。
"""
import json
import sys
import types
from unittest.mock import MagicMock, patch

import pytest


# ---------- 请求桩 ----------

class _FakeResp:
    def __init__(self, payload=None, content=b"", status_code=200):
        self._payload = payload
        self.content = content
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self.reason = "OK"

    def json(self):
        return self._payload


class _FakeRequestUtils:
    """记录出站请求，按 URL 片段路由响应。"""
    calls = []
    routes = {}

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    @classmethod
    def reset(cls, routes=None):
        cls.calls = []
        cls.routes = routes or {}

    def get_res(self, url, **kwargs):
        type(self).calls.append(("GET", url, None))
        for frag, resp in type(self).routes.items():
            if frag in url:
                return resp() if callable(resp) else resp
        if "gettoken" in url:
            return _FakeResp({"errcode": 0, "access_token": "SELF_TOKEN", "expires_in": 7200})
        return _FakeResp({}, content=b"\x89PNG\r\n\x1a\nIMG")

    def post_res(self, url, data=None, **kwargs):
        type(self).calls.append(("POST", url, data))
        for frag, resp in type(self).routes.items():
            if frag in url:
                return resp() if callable(resp) else resp
        return _FakeResp({"errcode": 0, "errmsg": "ok"})

    def request(self, method, url, **kwargs):
        type(self).calls.append((method.upper(), url, kwargs.get("files")))
        for frag, resp in type(self).routes.items():
            if frag in url:
                return resp() if callable(resp) else resp
        return _FakeResp({"errcode": 0, "media_id": "MEDIA_1"})


WECOM_CONF = {
    "WECHAT_CORPID": "corp1",
    "WECHAT_APP_SECRET": "sec1",
    "WECHAT_APP_ID": "1000002",
    "WECHAT_ADMINS": "zhangsan, lisi",
}


def _make_plugin(mpnews=False):
    """构造带 mpnews 开关的插件实例。"""
    from app.plugins.maoyandianying import MaoyanDianYing
    plugin = object().__new__(MaoyanDianYing)
    plugin._mpnews_enabled = mpnews
    plugin.get_data = MagicMock(return_value=None)
    plugin.save_data = MagicMock()
    plugin.post_message = MagicMock()
    return plugin


def _notify(plugin, **kwargs):
    kwargs.setdefault("mtype", "Plugin")
    kwargs.setdefault("title", "猫眼热度榜今日上新")
    kwargs.setdefault("text", "📺 1. 《剧》\n📺 2. 《剧2》")
    plugin._MaoyanDianYing__notify(**kwargs)


@pytest.fixture(autouse=True)
def _patch_http():
    """所有用例统一替换 RequestUtils 为桩，并清理路由与注入的图片管道桩。"""
    _FakeRequestUtils.reset()
    # 默认移除上一条用例可能注入的 ImageHelper 桩，保证用例间相互隔离
    saved = sys.modules.pop("app.application.image", None)
    with patch("app.plugins.maoyandianying.RequestUtils", _FakeRequestUtils):
        yield
    _FakeRequestUtils.reset()
    sys.modules.pop("app.application.image", None)
    if saved is not None:
        sys.modules["app.application.image"] = saved


# ---------- 开关默认值 ----------

class TestMpnewsDefault:
    """新增开关默认关闭，保证不影响现有行为"""

    def test_switch_defaults_to_false(self):
        from app.plugins.maoyandianying import MaoyanDianYing
        _, default_config = object().__new__(MaoyanDianYing).get_form()
        assert default_config["mpnews_enabled"] is False

    def test_init_plugin_reads_switch(self):
        from app.plugins.maoyandianying import MaoyanDianYing
        plugin = object().__new__(MaoyanDianYing)
        with patch("app.plugins.maoyandianying.SubscribeOper"), \
             patch("app.plugins.maoyandianying.MediaServerOper"), \
             patch("app.plugins.maoyandianying.TransferHistoryOper"):
            plugin.init_plugin({"enabled": False, "mpnews_enabled": True})
        assert plugin._mpnews_enabled is True

    def test_init_plugin_missing_key_keeps_disabled(self):
        from app.plugins.maoyandianying import MaoyanDianYing
        plugin = object().__new__(MaoyanDianYing)
        with patch("app.plugins.maoyandianying.SubscribeOper"), \
             patch("app.plugins.maoyandianying.MediaServerOper"), \
             patch("app.plugins.maoyandianying.TransferHistoryOper"):
            plugin.init_plugin({"enabled": False})
        assert plugin._mpnews_enabled is False


# ---------- 关闭时行为不变 ----------

class TestSwitchOffKeepsLegacyPath:
    """开关关闭时仍走宿主通知链，一个字节都不变"""

    def test_off_uses_post_message(self):
        plugin = _make_plugin(mpnews=False)
        _notify(plugin)
        plugin.post_message.assert_called_once()

    def test_off_makes_no_http_request(self):
        plugin = _make_plugin(mpnews=False)
        _notify(plugin)
        assert _FakeRequestUtils.calls == []

    def test_off_passes_title_text_image(self):
        plugin = _make_plugin(mpnews=False)
        _notify(plugin, text="正文", image="http://img/x.jpg")
        kwargs = plugin.post_message.call_args.kwargs
        assert kwargs["title"] == "猫眼热度榜今日上新"
        assert kwargs["text"] == "正文"
        assert kwargs["image"] == "http://img/x.jpg"


# ---------- 打开时走 mpnews ----------

class TestSwitchOnUsesMpnews:
    """开关打开时改发企业微信 mpnews"""

    def _with_conf(self, plugin, conf=WECOM_CONF):
        plugin._MaoyanDianYing__get_wechat_conf = lambda: conf
        return plugin

    def test_on_sends_mpnews_and_skips_post_message(self):
        plugin = self._with_conf(_make_plugin(mpnews=True))
        _notify(plugin, image="http://img/x.jpg")
        plugin.post_message.assert_not_called()
        sends = [c for c in _FakeRequestUtils.calls if "message/send" in c[1]]
        assert len(sends) == 1
        body = json.loads(sends[0][2].decode("utf-8"))
        assert body["msgtype"] == "mpnews"
        assert body["agentid"] == "1000002"
        assert body["touser"] == "zhangsan|lisi"
        assert "chatid" not in body
        assert body["mpnews"]["articles"][0]["thumb_media_id"] == "MEDIA_1"

    def test_on_uploads_thumb_before_send(self):
        plugin = self._with_conf(_make_plugin(mpnews=True))
        _notify(plugin, image="http://img/x.jpg")
        kinds = [c[0] for c in _FakeRequestUtils.calls]
        assert kinds == ["GET", "GET", "POST", "POST"], kinds
        upload = [c for c in _FakeRequestUtils.calls if "media/upload" in c[1]]
        assert "type=image" in upload[0][1]
        assert isinstance(upload[0][2], dict) and "media" in upload[0][2]

    def test_content_is_html_with_br(self):
        plugin = self._with_conf(_make_plugin(mpnews=True))
        _notify(plugin, text="第一行\n第二行", image="http://img/x.jpg")
        body = json.loads([c for c in _FakeRequestUtils.calls if "message/send" in c[1]][0][2].decode())
        assert "<br/>" in body["mpnews"]["articles"][0]["content"]

    def test_no_image_skips_send_entirely(self):
        plugin = self._with_conf(_make_plugin(mpnews=True))
        _notify(plugin, image=None)
        assert [c for c in _FakeRequestUtils.calls if "message/send" in c[1]] == []


# ---------- 回退保证不丢通知 ----------

class TestFallback:
    """mpnews 任一环节失败都回退宿主通知链，绝不静默丢消息"""

    def test_no_wechat_channel_falls_back(self):
        plugin = _make_plugin(mpnews=True)
        plugin._MaoyanDianYing__get_wechat_conf = lambda: None
        _notify(plugin)
        plugin.post_message.assert_called_once()

    def test_upload_failure_falls_back(self):
        plugin = _make_plugin(mpnews=True)
        plugin._MaoyanDianYing__get_wechat_conf = lambda: WECOM_CONF
        _FakeRequestUtils.routes = {"media/upload": _FakeResp({"errcode": 40001, "errmsg": "bad"})}
        _notify(plugin, image="http://img/x.jpg")
        plugin.post_message.assert_called_once()

    def test_send_failure_falls_back(self):
        plugin = _make_plugin(mpnews=True)
        plugin._MaoyanDianYing__get_wechat_conf = lambda: WECOM_CONF
        _FakeRequestUtils.routes = {"message/send": _FakeResp({"errcode": 40008, "errmsg": "bad"})}
        _notify(plugin, image="http://img/x.jpg")
        plugin.post_message.assert_called_once()

    def test_exception_in_channel_lookup_falls_back(self):
        plugin = _make_plugin(mpnews=True)

        def _boom():
            raise RuntimeError("渠道读取炸了")

        plugin._MaoyanDianYing__get_wechat_conf = _boom
        _notify(plugin, image="http://img/x.jpg")
        plugin.post_message.assert_called_once()

    def test_incomplete_credentials_falls_back(self):
        plugin = _make_plugin(mpnews=True)
        plugin._MaoyanDianYing__get_wechat_conf = lambda: {"WECHAT_ADMINS": "a"}
        _notify(plugin, image="http://img/x.jpg")
        plugin.post_message.assert_called_once()


# ---------- 渠道配置筛选 ----------

class TestChannelLookup:
    """只认自建应用模式的企业微信渠道"""

    def test_bot_mode_channel_is_ignored(self):
        from app.plugins.maoyandianying import MaoyanDianYing
        conf = dict(WECOM_CONF, WECHAT_MODE="bot")
        service = types.SimpleNamespace(
            instance=None,
            config=types.SimpleNamespace(config=conf),
        )
        helper = MagicMock()
        helper.return_value.get_services.return_value = {"wecom": service}
        with patch("app.sdk.services.NotificationHelper", helper):
            assert MaoyanDianYing._MaoyanDianYing__get_wechat_conf() is None

    def test_app_mode_channel_is_returned(self):
        from app.plugins.maoyandianying import MaoyanDianYing
        service = types.SimpleNamespace(
            instance=None,
            config=types.SimpleNamespace(config=WECOM_CONF),
        )
        helper = MagicMock()
        helper.return_value.get_services.return_value = {"wecom": service}
        with patch("app.sdk.services.NotificationHelper", helper):
            assert MaoyanDianYing._MaoyanDianYing__get_wechat_conf() == WECOM_CONF

    def test_incomplete_channel_is_skipped(self):
        from app.plugins.maoyandianying import MaoyanDianYing
        service = types.SimpleNamespace(
            instance=None,
            config=types.SimpleNamespace(config={"WECHAT_ADMINS": "a"}),
        )
        helper = MagicMock()
        helper.return_value.get_services.return_value = {"wecom": service}
        with patch("app.sdk.services.NotificationHelper", helper):
            assert MaoyanDianYing._MaoyanDianYing__get_wechat_conf() is None


# ---------- token 与素材缓存 ----------

class TestTokenAndThumbCache:
    """access_token 优先复用宿主实例；缩略图素材带 TTL 缓存"""

    def test_reuses_host_access_token(self):
        service = types.SimpleNamespace(
            instance=types.SimpleNamespace(_access_token="HOST_TOKEN"),
            config=types.SimpleNamespace(config=WECOM_CONF),
        )
        helper = MagicMock()
        helper.return_value.get_services.return_value = {"wecom": service}
        with patch("app.sdk.services.NotificationHelper", helper):
            from app.plugins.maoyandianying import _WeComMpnews
            sender = _WeComMpnews(MagicMock(), WECOM_CONF)
            sender._upload_thumb("http://img/x.jpg")
        urls = [c[1] for c in _FakeRequestUtils.calls]
        assert not any("gettoken" in u for u in urls), urls
        assert any("access_token=HOST_TOKEN" in u for u in urls), urls

    def test_thumb_media_id_cached(self):
        from app.plugins.maoyandianying import _WeComMpnews
        store = {}

        def _get(key=None):
            return store.get(key)

        def _save(key, value):
            store[key] = value

        owner = types.SimpleNamespace(get_data=_get, save_data=_save)
        _WeComMpnews(owner, WECOM_CONF)._upload_thumb("http://img/x.jpg")
        first = len([c for c in _FakeRequestUtils.calls if "media/upload" in c[1]])
        _FakeRequestUtils.reset()
        _WeComMpnews(owner, WECOM_CONF)._upload_thumb("http://img/x.jpg")
        second = len([c for c in _FakeRequestUtils.calls if "media/upload" in c[1]])
        assert first == 1
        assert second == 0
        assert any("mpthumb" in k for k in store), list(store)

    def test_expired_thumb_cache_refetches(self):
        """缓存过期后必须重新上传，不能沿用临时素材（有效期 3 天）"""
        from app.plugins.maoyandianying import _WeComMpnews
        import hashlib
        import time as _time

        url = "http://img/x.jpg"
        key = "maoyandingyue_mpthumb_" + hashlib.md5(url.encode("utf-8")).hexdigest()[:12]
        # 写入一条已过期的缓存记录
        store = {key: {"media_id": "OLD_MEDIA", "ts": _time.time() - 3 * 86400}}

        owner = types.SimpleNamespace(
            get_data=lambda k=None: store.get(k),
            save_data=MagicMock(side_effect=lambda k, v: store.__setitem__(k, v)),
        )
        sender = _WeComMpnews(owner, WECOM_CONF)
        media_id = sender._upload_thumb(url)
        assert media_id == "MEDIA_1", media_id          # 重新上传，不用 OLD_MEDIA
        assert store[key]["media_id"] == "MEDIA_1"      # 缓存被刷新
        owner.save_data.assert_called_once()

    def test_fresh_thumb_cache_is_used(self):
        """未过期的缓存直接复用，不再发上传请求"""
        from app.plugins.maoyandianying import _WeComMpnews
        import hashlib
        import time as _time

        url = "http://img/x.jpg"
        key = "maoyandingyue_mpthumb_" + hashlib.md5(url.encode("utf-8")).hexdigest()[:12]
        store = {key: {"media_id": "FRESH_MEDIA", "ts": _time.time()}}

        owner = types.SimpleNamespace(get_data=lambda k=None: store.get(k), save_data=MagicMock())
        sender = _WeComMpnews(owner, WECOM_CONF)
        assert sender._upload_thumb(url) == "FRESH_MEDIA"
        assert [c for c in _FakeRequestUtils.calls if "media/upload" in c[1]] == []
        owner.save_data.assert_not_called()

    def test_42001_triggers_retry(self):
        attempts = {"n": 0}

        def _expire_once():
            attempts["n"] += 1
            if attempts["n"] == 1:
                return _FakeResp({"errcode": 42001, "errmsg": "expired"})
            return _FakeResp({"errcode": 0, "errmsg": "ok"})

        _FakeRequestUtils.routes = {"message/send": _expire_once}
        from app.plugins.maoyandianying import _WeComMpnews
        sender = _WeComMpnews(MagicMock(get_data=lambda k: None, save_data=MagicMock()), WECOM_CONF)
        assert sender.send("标题", "正文", "http://img/x.jpg") is True
        assert attempts["n"] == 2
        assert any("gettoken" in c[1] for c in _FakeRequestUtils.calls)


# ---------- 正文构造 ----------

class TestContentBuilding:
    """正文 HTML 转义，避免剧名里的尖括号破坏结构"""

    def test_escapes_angle_brackets(self):
        from app.plugins.maoyandianying import _WeComMpnews
        content = _WeComMpnews._build_content("<script>x</script>")
        assert "<script>" not in content
        assert "&lt;script&gt;" in content

    def test_escapes_ampersand(self):
        from app.plugins.maoyandianying import _WeComMpnews
        assert "&amp;" in _WeComMpnews._build_content("A & B")

    def test_split_ids_handles_separators(self):
        from app.plugins.maoyandianying import _WeComMpnews
        assert _WeComMpnews._split_ids("a, b") == ["a", "b"]
        assert _WeComMpnews._split_ids("a|b") == ["a", "b"]
        assert _WeComMpnews._split_ids(None) == []

    def test_empty_targets_fall_back_to_all(self):
        from app.plugins.maoyandianying import _WeComMpnews
        sender = _WeComMpnews(MagicMock(get_data=lambda k: None, save_data=MagicMock()),
                              dict(WECOM_CONF, WECHAT_ADMINS=""))
        sender.send("标题", "正文", "http://img/x.jpg")
        sends = [c for c in _FakeRequestUtils.calls if "message/send" in c[1]]
        body = json.loads(sends[0][2].decode())
        assert body["touser"] == "@all"


# ---------- clear_cache 覆盖新缓存 ----------

class TestClearCacheCoversThumb:
    """清理缓存需覆盖新增的图文素材缓存"""

    def test_mpthumb_counted_and_removed(self):
        plugin = _make_plugin()
        items = [
            types.SimpleNamespace(key="maoyandingyue_data"),
            types.SimpleNamespace(key="maoyandingyue_mpthumb_abc123"),
        ]
        with patch.object(plugin, "get_data", return_value=items), \
             patch.object(plugin, "del_data") as mock_del, \
             patch.object(plugin, "_auto_refresh"):
            result = plugin.clear_cache()
        assert result["success"] is True
        assert result["data"]["stats"]["maoyandingyue_mpthumb_"] == 1
        assert mock_del.call_count == 2


# ---------- 封面下载走宿主代理 ----------

class TestCoverDownloadProxy:
    """封面下载必须跟随宿主代理，否则国内直连 image.tmdb.org 被拒"""

    def test_download_passes_host_proxies(self):
        from app.plugins.maoyandianying import _WeComMpnews
        seen = {}

        class _Recorder(_FakeRequestUtils):
            def __init__(self, **kwargs):
                seen.update(kwargs)

        proxies = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}
        with patch("app.plugins.maoyandianying.RequestUtils", _Recorder), \
             patch("app.runtime.settings.get_runtime_setting",
                   lambda key, default=None: proxies if key == "PROXY" else default):
            _WeComMpnews(MagicMock(), WECOM_CONF)._download_image("https://image.tmdb.org/t/p/w500/x.jpg")
        assert seen.get("proxies") == proxies, seen

    def test_download_without_proxy_still_works(self):
        """宿主未配代理时按 None 传参，不报错"""
        from app.plugins.maoyandianying import _WeComMpnews
        seen = {}

        class _Recorder(_FakeRequestUtils):
            def __init__(self, **kwargs):
                seen.update(kwargs)

        with patch("app.plugins.maoyandianying.RequestUtils", _Recorder), \
             patch("app.runtime.settings.get_runtime_setting",
                   lambda key, default=None: default):
            _WeComMpnews(MagicMock(), WECOM_CONF)._download_image("https://image.tmdb.org/t/p/w500/x.jpg")
        assert "proxies" in seen and seen["proxies"] is None, seen

    def test_host_proxies_reads_runtime_setting(self):
        from app.plugins.maoyandianying import _WeComMpnews
        proxies = {"https": "http://proxy:8080"}
        with patch("app.runtime.settings.get_runtime_setting",
                   lambda key, default=None: proxies if key == "PROXY" else default):
            assert _WeComMpnews._host_proxies() == proxies

    def test_host_proxies_none_when_unset(self):
        from app.plugins.maoyandianying import _WeComMpnews
        with patch("app.runtime.settings.get_runtime_setting",
                   lambda key, default=None: default):
            assert _WeComMpnews._host_proxies() is None

    def test_host_proxies_survives_broken_settings(self):
        """配置读取异常不得影响主流程"""
        from app.plugins.maoyandianying import _WeComMpnews

        def _boom(*a, **k):
            raise RuntimeError("配置读取炸了")

        with patch("app.runtime.settings.get_runtime_setting", _boom):
            assert _WeComMpnews._host_proxies() is None


# ---------- 封面优先取宿主图片缓存 ----------

class TestCoverFromHostCache:
    """封面优先走宿主图片管道（缓存优先），命中时零网络请求"""

    def _patch_image_helper(self, result=None, raises=None):
        """注入桩 ImageHelper，返回记录调用参数的容器。"""
        seen = {}

        class _StubHelper:
            def fetch_image_with_mime_type(self, url=None, proxy=None, use_cache=True):
                seen.update(url=url, proxy=proxy, use_cache=use_cache)
                if raises:
                    raise raises
                return result

        helper_mod = types.ModuleType("app.application.image")
        helper_mod.ImageHelper = _StubHelper
        app_mod = sys.modules.get("app.application") or types.ModuleType("app.application")
        sys.modules["app.application"] = app_mod
        sys.modules["app.application.image"] = helper_mod
        return seen

    def test_uses_host_pipeline_with_cache_enabled(self):
        from app.plugins.maoyandianying import _WeComMpnews
        seen = self._patch_image_helper(result=(b"\xff\xd8\xffJPEGDATA", "image/jpeg"))
        content, filename, mime = _WeComMpnews(MagicMock(), WECOM_CONF)._download_image(
            "https://image.tmdb.org/t/p/w500/x.jpg"
        )
        assert content == b"\xff\xd8\xffJPEGDATA"
        assert seen["use_cache"] is True, seen      # 必须允许读缓存
        assert seen["proxy"] is None, seen          # 由宿主按配置决定是否用代理
        assert mime == "image/jpeg"
        assert filename == "cover.jpg"

    def test_png_mime_maps_to_png_filename(self):
        from app.plugins.maoyandianying import _WeComMpnews
        self._patch_image_helper(result=(b"\x89PNG\r\n\x1a\nX", "image/png"))
        content, filename, mime = _WeComMpnews(MagicMock(), WECOM_CONF)._download_image(
            "https://image.tmdb.org/t/p/w500/x.jpg"
        )
        assert filename == "cover.png"
        assert mime == "image/png"

    def test_no_network_when_host_cache_hits(self):
        """宿主缓存命中时不应产生任何直连请求"""
        from app.plugins.maoyandianying import _WeComMpnews
        self._patch_image_helper(result=(b"\xff\xd8\xffCACHED", "image/jpeg"))
        _FakeRequestUtils.reset()
        _WeComMpnews(MagicMock(), WECOM_CONF)._download_image("https://image.tmdb.org/t/p/w500/x.jpg")
        assert _FakeRequestUtils.calls == [], _FakeRequestUtils.calls

    def test_falls_back_to_direct_when_pipeline_empty(self):
        """宿主管道取不到时回退到直连下载"""
        from app.plugins.maoyandianying import _WeComMpnews
        self._patch_image_helper(result=None)
        _FakeRequestUtils.reset()
        content, filename, mime = _WeComMpnews(MagicMock(), WECOM_CONF)._download_image(
            "https://image.tmdb.org/t/p/w500/x.jpg"
        )
        assert content, "应回退直连并取到字节"
        assert any("image.tmdb.org" in c[1] for c in _FakeRequestUtils.calls), _FakeRequestUtils.calls

    def test_falls_back_to_direct_when_pipeline_raises(self):
        """宿主管道抛错时不得中断，回退直连"""
        from app.plugins.maoyandianying import _WeComMpnews
        self._patch_image_helper(raises=RuntimeError("图片管道未装配"))
        _FakeRequestUtils.reset()
        content, _, _ = _WeComMpnews(MagicMock(), WECOM_CONF)._download_image(
            "https://image.tmdb.org/t/p/w500/x.jpg"
        )
        assert content, "异常后应回退直连"
        assert any("image.tmdb.org" in c[1] for c in _FakeRequestUtils.calls)

    def test_missing_image_module_does_not_break(self):
        """宿主无该模块时（如老版本）静默回退"""
        from app.plugins.maoyandianying import _WeComMpnews
        sys.modules.pop("app.application.image", None)
        _FakeRequestUtils.reset()
        content, _, _ = _WeComMpnews(MagicMock(), WECOM_CONF)._download_image(
            "https://image.tmdb.org/t/p/w500/x.jpg"
        )
        assert content


# ---------- 正文富文本：演员 / 详情 / 状态 ----------

class TestRichContent:
    """mpnews 正文携带演员、详情与订阅状态"""

    def _content(self, items, text=""):
        from app.plugins.maoyandianying import _WeComMpnews
        return _WeComMpnews._build_content(text, items)

    def test_actors_rendered(self):
        html = self._content([{"rank": 1, "name": "剧A", "actors": ["张三", "李四"]}])
        assert "主演" in html
        assert "张三" in html and "李四" in html

    def test_detail_fields_rendered(self):
        html = self._content([{
            "rank": 1, "name": "剧A", "vote_average": 8.6,
            "first_air_date": "2026-01-15",
            "number_of_seasons": 2, "number_of_episodes": 24,
        }])
        assert "评分：8.6" in html
        assert "首播：2026-01-15" in html
        assert "集数：2 季 24 集" in html

    def test_each_field_on_its_own_line(self):
        """每个字段独立成行（各占一个 <p>），不再用竖线拼接"""
        html = self._content([{
            "rank": 1, "name": "剧A", "vote_average": 8.6,
            "first_air_date": "2026-01-15",
            "number_of_seasons": 1, "number_of_episodes": 30,
            "genres": [{"name": "剧情"}],
            "actors": ["甲", "乙"],
            "overview": "简介内容",
        }])
        # 标题之外，评分/首播/集数/类型/主演/简介 共 6 行
        assert html.count("<p") == 7, html
        assert "评分：8.6</p>" in html
        assert "主演：甲、乙</p>" in html
        assert "简介：简介内容</p>" in html

    def test_episodes_without_seasons(self):
        html = self._content([{"rank": 1, "name": "剧A", "number_of_episodes": 12}])
        assert "集数：共 12 集" in html

    def test_overview_not_truncated(self):
        """简介按用户要求完整显示，不截断"""
        long_text = "字" * 200
        html = self._content([{"rank": 1, "name": "剧A", "overview": long_text}])
        assert long_text in html

    def test_all_genres_rendered(self):
        """类型全部显示，不只取前 3 个"""
        html = self._content([{
            "rank": 1, "name": "剧A",
            "genres": [{"name": f"类型{i}"} for i in range(5)],
        }])
        assert "类型：类型0、类型1、类型2、类型3、类型4" in html

    def test_genres_and_overview_rendered(self):
        html = self._content([{
            "rank": 1, "name": "剧A",
            "genres": [{"name": "剧情"}, {"name": "悬疑"}],
            "overview": "一段简介文字",
        }])
        assert "类型：剧情、悬疑" in html
        assert "一段简介文字" in html

    def test_status_tag_rendered(self):
        html = self._content([{"rank": 1, "name": "剧A", "status_tag": "【未订阅】"}])
        assert "【未订阅】" in html

    def test_platform_rendered(self):
        html = self._content([{"rank": 1, "name": "剧A", "platform": "腾讯视频"}])
        assert "腾讯视频" in html

    def test_falls_back_to_plain_text_without_items(self):
        html = self._content(None, "第一行\n第二行")
        assert "<br/>" in html
        assert "第一行" in html

    def test_escapes_injected_html_in_names(self):
        html = self._content([{"rank": 1, "name": "<script>x</script>", "actors": ["<b>"]}])
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_send_accepts_items_and_builds_rich_content(self):
        from app.plugins.maoyandianying import _WeComMpnews
        sender = _WeComMpnews(MagicMock(get_data=lambda k: None, save_data=MagicMock()), WECOM_CONF)
        ok = sender.send("标题", "兜底", "http://img/x.jpg",
                         items=[{"rank": 1, "name": "剧A", "actors": ["张三"],
                                 "vote_average": 9.0, "status_tag": "【已订阅】"}])
        assert ok is True
        body = json.loads([c for c in _FakeRequestUtils.calls if "message/send" in c[1]][0][2].decode())
        content = body["mpnews"]["articles"][0]["content"]
        assert "张三" in content and "评分：9.0" in content and "【已订阅】" in content


class TestBuildNotifyItem:
    """条目富信息组装：优先命中插件缓存"""

    def _plugin(self, tmdb_info=None, detail=None):
        plugin = _make_plugin(mpnews=True)
        plugin._MaoyanDianYing__search_tmdb_with_cache = MagicMock(return_value=tmdb_info)
        plugin._MaoyanDianYing__get_detail_with_cache = MagicMock(return_value=detail)
        plugin._MaoyanDianYing__notify_status_tag = MagicMock(return_value="【未订阅】")
        return plugin

    def test_collects_detail_fields(self):
        plugin = self._plugin(
            tmdb_info={"id": 100, "poster_path": "/p.jpg"},
            detail={"vote_average": 7.5, "first_air_date": "2026-02-01",
                    "number_of_seasons": 1, "number_of_episodes": 12,
                    "genres": [{"name": "剧情"}], "overview": "简介",
                    "credits": {"cast": [{"name": "演员甲"}, {"name": "演员乙"}]}},
        )
        result = plugin._MaoyanDianYing__build_notify_item({"rank": 3, "name": "剧B"})
        assert result["tmdbid"] == 100
        assert result["vote_average"] == 7.5
        assert result["number_of_episodes"] == 12
        assert result["actors"] == ["演员甲", "演员乙"]
        assert result["status_tag"] == "【未订阅】"

    def test_prefers_existing_actors_from_cache(self):
        plugin = self._plugin(
            tmdb_info={"id": 100},
            detail={"credits": {"cast": [{"name": "演员甲"}]}},
        )
        result = plugin._MaoyanDianYing__build_notify_item(
            {"rank": 1, "name": "剧B", "actors": ["缓存演员"]}
        )
        assert result["actors"] == ["缓存演员"]

    def test_no_tmdbid_still_returns_status(self):
        plugin = self._plugin(tmdb_info=None)
        result = plugin._MaoyanDianYing__build_notify_item({"rank": 1, "name": "剧B"})
        assert result["status_tag"] == "【未订阅】"
        assert "vote_average" not in result

    def test_survives_cache_lookup_failure(self):
        plugin = _make_plugin(mpnews=True)
        plugin._MaoyanDianYing__search_tmdb_with_cache = MagicMock(side_effect=RuntimeError("炸"))
        plugin._MaoyanDianYing__get_detail_with_cache = MagicMock(side_effect=RuntimeError("炸"))
        plugin._MaoyanDianYing__notify_status_tag = MagicMock(return_value="【未订阅】")
        result = plugin._MaoyanDianYing__build_notify_item({"rank": 1, "name": "剧B"})
        assert result["name"] == "剧B"


class TestRichItemOnlyWhenEnabled:
    """富信息组装只在 mpnews 开启时进行，关闭时零额外开销"""

    def _run(self, mpnews, monkeypatch_target):
        plugin = _make_plugin(mpnews=mpnews)
        plugin._enabled = True          # send_remind 会先检查插件启用状态
        plugin._reminder_enabled = True
        plugin._reminder_msgtype = "Plugin"
        plugin.post_message = MagicMock()
        item = {"rank": 1, "name": "剧集1", "platform": "爱奇艺",
                "days": "上映3天", "heat": 1000, "plays": "1.2亿", "tmdbid": 0}
        built = []

        def _fake_build(it):
            built.append(it)
            return {"rank": it.get("rank"), "name": it.get("name")}

        plugin._MaoyanDianYing__build_notify_item = _fake_build
        with patch.object(plugin, "get_data", return_value=None), \
             patch.object(plugin, "save_data"), \
             patch.object(plugin, "_MaoyanDianYing__is_today_new", return_value=True), \
             patch.object(plugin, "_check_media_status", return_value="未添加订阅"), \
             patch.object(plugin, "_MaoyanDianYing__search_tmdb_with_cache",
                          return_value={"id": 1, "poster_path": "/t.jpg"}):
            plugin._MaoyanDianYing__send_remind(force=False, heat_list=[item])
        return built

    def test_not_built_when_switch_off(self):
        assert self._run(mpnews=False, monkeypatch_target=None) == []

    def test_built_when_switch_on(self):
        assert len(self._run(mpnews=True, monkeypatch_target=None)) == 1


# ---------- 标题变体识别（问心2 -> 问心）----------

class TestStripSeason:
    """季数后缀剥离：宿主单向子串过滤导致带季数片名必然搜不到"""

    def _strip(self, name):
        from app.plugins.maoyandianying import TmdbHelper
        return TmdbHelper.strip_season(name)

    def test_trailing_digit(self):
        assert self._strip("问心2") == ("问心", 2)

    def test_chinese_season(self):
        assert self._strip("问心第二季") == ("问心", 2)
        assert self._strip("心动的信号 第九季") == ("心动的信号", 9)

    def test_arabic_season_with_di(self):
        assert self._strip("问心 第2季") == ("问心", 2)
        assert self._strip("斗罗大陆 第10季") == ("斗罗大陆", 10)

    def test_english_season(self):
        assert self._strip("问心 Season 2") == ("问心", 2)
        assert self._strip("问心 S2") == ("问心", 2)

    def test_roman_numeral(self):
        assert self._strip("问心III") == ("问心", 3)
        assert self._strip("问心 II") == ("问心", 2)

    def test_year_is_not_season(self):
        """4 位年份剥离但不当作季号，避免把 2026 认成第 26 季"""
        assert self._strip("说唱巅峰对决2026") == ("说唱巅峰对决", 0)
        assert self._strip("县委大院2026") == ("县委大院", 0)

    def test_plain_title_unchanged(self):
        assert self._strip("云雀叫天录") == ("云雀叫天录", 0)
        assert self._strip("爱情有烟火") == ("爱情有烟火", 0)
        assert self._strip("法医秦明之蚀骨时差") == ("法医秦明之蚀骨时差", 0)

    def test_all_roman_title_not_stripped(self):
        """整个片名都是罗马数字时不应剥离"""
        assert self._strip("XXXIII") == ("XXXIII", 0)

    def test_empty_input(self):
        assert self._strip("") == ("", 0)
        assert self._strip(None) == ("", 0)


class TestSearchTvSeasonFallback:
    """原名搜不到时以主标题重搜，并回填季号"""

    @patch("app.plugins.maoyandianying.TmdbApi")
    def test_retries_with_base_title(self, mock_cls):
        from app.plugins.maoyandianying import TmdbHelper
        api = MagicMock()
        # 原名无结果，主标题命中
        api.search_tvs.side_effect = lambda term, *a: [] if term == "问心2" else [{"id": 233076, "name": "问心"}]
        mock_cls.return_value = api

        result = TmdbHelper.search_tv("问心2")
        assert result["id"] == 233076
        assert result["_season"] == 2
        assert [c.args[0] for c in api.search_tvs.call_args_list] == ["问心2", "问心"]

    @patch("app.plugins.maoyandianying.TmdbApi")
    def test_no_retry_when_base_equals_name(self, mock_cls):
        """无季数后缀时不应多发一次请求"""
        from app.plugins.maoyandianying import TmdbHelper
        api = MagicMock()
        api.search_tvs.return_value = []
        mock_cls.return_value = api

        assert TmdbHelper.search_tv("云雀叫天录") is None
        assert api.search_tvs.call_count == 1

    @patch("app.plugins.maoyandianying.TmdbApi")
    def test_returns_none_when_both_fail(self, mock_cls):
        from app.plugins.maoyandianying import TmdbHelper
        api = MagicMock()
        api.search_tvs.return_value = []
        mock_cls.return_value = api

        assert TmdbHelper.search_tv("问心2") is None
        assert api.search_tvs.call_count == 2

    @patch("app.plugins.maoyandianying.TmdbApi")
    def test_original_hit_keeps_no_season(self, mock_cls):
        """原名直接命中时保持原行为，不注入 _season"""
        from app.plugins.maoyandianying import TmdbHelper
        api = MagicMock()
        api.search_tvs.return_value = [{"id": 1, "name": "云雀叫天录"}]
        mock_cls.return_value = api

        result = TmdbHelper.search_tv("云雀叫天录")
        assert result["id"] == 1
        assert "_season" not in result
        assert api.search_tvs.call_count == 1

    @patch("app.plugins.maoyandianying.TmdbApi")
    def test_constructor_failure_is_contained(self, mock_cls):
        from app.plugins.maoyandianying import TmdbHelper
        mock_cls.side_effect = Exception("boom")
        assert TmdbHelper.search_tv("问心2") is None

    @patch("app.plugins.maoyandianying.TmdbApi")
    def test_base_search_exception_contained(self, mock_cls):
        from app.plugins.maoyandianying import TmdbHelper
        api = MagicMock()
        api.search_tvs.side_effect = [[], Exception("网络炸了")]
        mock_cls.return_value = api
        assert TmdbHelper.search_tv("问心2") is None


# ---------- 季别开播日期判定 ----------

class TestSeasonAwareTodayNew:
    """带季数条目按该季开播日判定今日上新，而非第 1 季日期"""

    def _plugin(self, tmdb_info, season_air=None):
        plugin = _make_plugin(mpnews=False)
        plugin._MaoyanDianYing__search_tmdb_with_cache = MagicMock(return_value=tmdb_info)
        plugin._MaoyanDianYing__get_season_air_date = MagicMock(return_value=season_air)
        return plugin

    def test_season_air_date_match(self):
        from datetime import datetime
        today = datetime.now().date().isoformat()
        plugin = self._plugin({"id": 233076, "season": 2, "first_air_date": "2023-10-07"},
                              season_air=today)
        assert plugin._MaoyanDianYing__is_today_new({"name": "问心2"}) is True

    def test_season_air_date_mismatch(self):
        """第 1 季是今天也不算——有季号时应看该季日期"""
        from datetime import datetime
        today = datetime.now().date().isoformat()
        plugin = self._plugin({"id": 233076, "season": 2, "first_air_date": today},
                              season_air="2026-06-18")
        assert plugin._MaoyanDianYing__is_today_new({"name": "问心2"}) is False

    def test_falls_back_to_first_air_date_without_season(self):
        from datetime import datetime
        today = datetime.now().date().isoformat()
        plugin = self._plugin({"id": 1, "first_air_date": today})
        assert plugin._MaoyanDianYing__is_today_new({"name": "某剧"}) is True

    def test_falls_back_when_season_date_missing(self):
        """季日期取不到时回退主记录，不误判为 False"""
        from datetime import datetime
        today = datetime.now().date().isoformat()
        plugin = self._plugin({"id": 233076, "season": 2, "first_air_date": today},
                              season_air=None)
        assert plugin._MaoyanDianYing__is_today_new({"name": "问心2"}) is True

    def test_no_tmdb_data_returns_false(self):
        plugin = self._plugin(None)
        assert plugin._MaoyanDianYing__is_today_new({"name": "问心2"}) is False

    def test_empty_name_returns_false(self):
        plugin = self._plugin({"id": 1})
        assert plugin._MaoyanDianYing__is_today_new({"name": ""}) is False


class TestGetSeasonAirDate:
    """season 详情查询：先校验季号存在，带 7 天缓存，air_date 为空回退第 1 集"""

    def _plugin(self, seasons=(1, 2)):
        """构造插件，detail 缓存带 seasons 列表供季号校验。"""
        plugin = _make_plugin(mpnews=False)
        plugin.get_data = MagicMock(return_value=None)
        plugin.save_data = MagicMock()
        plugin._MaoyanDianYing__get_detail_with_cache = MagicMock(
            return_value={"seasons": [{"season_number": n} for n in seasons]})
        return plugin

    @patch("app.plugins.maoyandianying.TmdbApi")
    def test_reads_season_air_date(self, mock_cls):
        from app.plugins.maoyandianying import MaoyanDianYing
        api = MagicMock()
        api.season_obj.details.return_value = {"air_date": "2026-06-18", "episodes": []}
        mock_cls.return_value = api
        plugin = self._plugin(seasons=(1, 2))
        assert plugin._MaoyanDianYing__get_season_air_date(233076, 2) == "2026-06-18"
        api.season_obj.details.assert_called_once_with(tv_id=233076, season_num=2)

    @patch("app.plugins.maoyandianying.TmdbApi")
    def test_falls_back_to_first_episode(self, mock_cls):
        from app.plugins.maoyandianying import MaoyanDianYing
        api = MagicMock()
        api.season_obj.details.return_value = {
            "air_date": "", "episodes": [{"air_date": "2026-06-18"}]}
        mock_cls.return_value = api
        plugin = self._plugin(seasons=(1, 2))
        assert plugin._MaoyanDianYing__get_season_air_date(233076, 2) == "2026-06-18"

    @patch("app.plugins.maoyandianying.TmdbApi")
    def test_nonexistent_season_skipped_without_request(self, mock_cls):
        """片名自带数字但 TMDB 只有第 1 季（如「我们的少年时代2」）不应发请求"""
        plugin = self._plugin(seasons=(1,))
        assert plugin._MaoyanDianYing__get_season_air_date(331830, 2) is None
        mock_cls.assert_not_called()

    @patch("app.plugins.maoyandianying.TmdbApi")
    def test_missing_seasons_field_still_queries(self, mock_cls):
        """detail 无 seasons 字段时不做校验，照常查询"""
        from app.plugins.maoyandianying import MaoyanDianYing
        api = MagicMock()
        api.season_obj.details.return_value = {"air_date": "2026-06-18", "episodes": []}
        mock_cls.return_value = api
        plugin = _make_plugin(mpnews=False)
        plugin.get_data = MagicMock(return_value=None)
        plugin.save_data = MagicMock()
        plugin._MaoyanDianYing__get_detail_with_cache = MagicMock(return_value={})
        assert plugin._MaoyanDianYing__get_season_air_date(233076, 2) == "2026-06-18"

    @patch("app.plugins.maoyandianying.TmdbApi")
    def test_cache_hit_skips_network(self, mock_cls):
        plugin = self._plugin()
        plugin.get_data = MagicMock(
            return_value={"data": {"air_date": "2026-06-18"}, "ts": 9e9})
        assert plugin._MaoyanDianYing__get_season_air_date(233076, 2) == "2026-06-18"
        mock_cls.assert_not_called()

    def test_missing_args(self):
        plugin = self._plugin()
        assert plugin._MaoyanDianYing__get_season_air_date(0, 2) is None
        assert plugin._MaoyanDianYing__get_season_air_date(233076, 0) is None

    @patch("app.plugins.maoyandianying.TmdbApi")
    def test_exception_contained(self, mock_cls):
        plugin = self._plugin()
        mock_cls.side_effect = Exception("boom")
        assert plugin._MaoyanDianYing__get_season_air_date(233076, 2) is None


class TestGetSeasonDetail:
    """季详情：供通知正文取该季首播/简介/集数"""

    def _plugin(self, seasons=(1, 2)):
        plugin = _make_plugin(mpnews=False)
        plugin.get_data = MagicMock(return_value=None)
        plugin.save_data = MagicMock()
        plugin._MaoyanDianYing__get_detail_with_cache = MagicMock(
            return_value={"seasons": [{"season_number": n} for n in seasons]})
        return plugin

    @patch("app.plugins.maoyandianying.TmdbApi")
    def test_returns_season_detail(self, mock_cls):
        api = MagicMock()
        api.season_obj.details.return_value = {
            "air_date": "2026-06-18", "overview": "第2季简介", "name": "第 2 季",
            "episodes": [{"air_date": "2026-06-18"}] * 40,
        }
        mock_cls.return_value = api
        plugin = self._plugin()
        detail = plugin._MaoyanDianYing__get_season_detail(233076, 2)
        assert detail["air_date"] == "2026-06-18"
        assert detail["overview"] == "第2季简介"
        assert len(detail["episodes"]) == 40

    @patch("app.plugins.maoyandianying.TmdbApi")
    def test_nonexistent_season_returns_none(self, mock_cls):
        plugin = self._plugin(seasons=(1,))
        assert plugin._MaoyanDianYing__get_season_detail(331830, 2) is None
        mock_cls.assert_not_called()


class TestNotifyItemUsesSeasonData:
    """带季数条目：通知内容取该季数据，而非第 1 季主记录"""

    def _plugin(self, tmdb_info, detail, season_detail):
        plugin = _make_plugin(mpnews=True)
        plugin._MaoyanDianYing__search_tmdb_with_cache = MagicMock(return_value=tmdb_info)
        plugin._MaoyanDianYing__get_detail_with_cache = MagicMock(return_value=detail)
        plugin._MaoyanDianYing__get_season_detail = MagicMock(return_value=season_detail)
        plugin._MaoyanDianYing__notify_status_tag = MagicMock(return_value="【未订阅】")
        return plugin

    def test_season_data_overrides_master_record(self):
        """问心：主记录 2023-10-07/78集 -> 第2季 2026-06-18/40集"""
        plugin = self._plugin(
            tmdb_info={"id": 233076, "season": 2},
            detail={"vote_average": 7.8, "first_air_date": "2023-10-07",
                    "number_of_seasons": 2, "number_of_episodes": 78,
                    "genres": [{"name": "剧情"}], "overview": "第1季简介"},
            season_detail={"air_date": "2026-06-18", "overview": "第2季简介",
                           "name": "第 2 季", "vote_average": 8.0,
                           "episodes": [{}] * 40},
        )
        result = plugin._MaoyanDianYing__build_notify_item({"rank": 1, "name": "问心2"})
        assert result["first_air_date"] == "2026-06-18"     # 覆盖第 1 季日期
        assert result["number_of_episodes"] == 40           # 该季集数，非全季 78
        assert result["overview"] == "第2季简介"
        assert result["vote_average"] == 8.0
        assert result["season"] == 2

    def test_no_season_keeps_master_record(self):
        plugin = self._plugin(
            tmdb_info={"id": 119538},
            detail={"first_air_date": "2017-07-09", "number_of_seasons": 1,
                    "number_of_episodes": 40},
            season_detail=None,
        )
        result = plugin._MaoyanDianYing__build_notify_item({"rank": 1, "name": "我们的少年时代"})
        assert result["first_air_date"] == "2017-07-09"
        assert result["number_of_episodes"] == 40
        assert "season" not in result

    def test_season_detail_missing_falls_back(self):
        plugin = self._plugin(
            tmdb_info={"id": 233076, "season": 2},
            detail={"first_air_date": "2023-10-07", "number_of_episodes": 78},
            season_detail=None,
        )
        result = plugin._MaoyanDianYing__build_notify_item({"rank": 1, "name": "问心2"})
        assert result["first_air_date"] == "2023-10-07"   # 取不到季数据时保持原值

    def test_render_shows_season_episode_line(self):
        """正文集数行应体现季别，避免把全季合计当成该季集数"""
        from app.plugins.maoyandianying import _WeComMpnews
        html = _WeComMpnews._build_content("x", [{
            "rank": 1, "name": "问心2", "season": 2,
            "first_air_date": "2026-06-18", "number_of_episodes": 40,
        }])
        assert "集数：第 2 季 共 40 集" in html


class TestClearCacheCoversSeason:
    """清理缓存需覆盖新增的季别开播缓存"""

    def test_season_counted_and_removed(self):
        plugin = _make_plugin()
        items = [
            types.SimpleNamespace(key="maoyandingyue_data"),
            types.SimpleNamespace(key="maoyandingyue_season_233076_2"),
        ]
        with patch.object(plugin, "get_data", return_value=items), \
             patch.object(plugin, "del_data") as mock_del, \
             patch.object(plugin, "_auto_refresh"):
            result = plugin.clear_cache()
        assert result["success"] is True
        assert result["data"]["stats"]["maoyandingyue_season_"] == 1
        assert mock_del.call_count == 2


# ---------- 订阅按季提交 ----------

class TestSubscribeSeason:
    """带季数剧集订阅时把季号传给订阅链，避免订到第 1 季"""

    def _plugin(self, status="未添加订阅", subs=None):
        plugin = _make_plugin(mpnews=False)
        plugin._check_media_status = MagicMock(return_value=status)
        plugin._subscribe_oper = MagicMock()
        plugin._subscribe_oper.list_by_media_identity.return_value = subs or []
        return plugin

    @patch("app.plugins.maoyandianying.SubscribeChain")
    def test_season_passed_to_chain(self, mock_chain_cls):
        mock_chain = MagicMock()
        mock_chain.add.return_value = (1, "成功")
        mock_chain_cls.return_value = mock_chain
        plugin = self._plugin()

        result = plugin.add_subscribe({"tmdbid": 233076, "name": "问心2", "season": 2})
        assert result["success"] is True
        assert mock_chain.add.call_args.kwargs["season"] == 2
        assert result["data"]["season"] == 2
        assert "第 2 季" in result["message"]

    @patch("app.plugins.maoyandianying.SubscribeChain")
    def test_no_season_passes_none(self, mock_chain_cls):
        """无季号条目保持原行为：season 传 None"""
        mock_chain = MagicMock()
        mock_chain.add.return_value = (1, "成功")
        mock_chain_cls.return_value = mock_chain
        plugin = self._plugin()

        plugin.add_subscribe({"tmdbid": 119538, "name": "我们的少年时代"})
        assert mock_chain.add.call_args.kwargs["season"] is None

    @patch("app.plugins.maoyandianying.SubscribeChain")
    def test_season_inferred_from_cache_when_missing(self, mock_chain_cls):
        """请求未带季号时，从 TMDB 缓存补查"""
        mock_chain = MagicMock()
        mock_chain.add.return_value = (1, "成功")
        mock_chain_cls.return_value = mock_chain
        plugin = _make_plugin(mpnews=False)
        plugin._check_media_status = MagicMock(return_value="未添加订阅")
        plugin._MaoyanDianYing__search_tmdb_with_cache = MagicMock(
            return_value={"id": 233076, "season": 2})

        plugin.add_subscribe({"tmdbid": 0, "name": "问心2"})
        assert mock_chain.add.call_args.kwargs["season"] == 2

    @patch("app.plugins.maoyandianying.SubscribeChain")
    def test_status_checked_with_season(self, mock_chain_cls):
        """状态检查要带季号，否则会被第 1 季的订阅挡住"""
        mock_chain = MagicMock()
        mock_chain.add.return_value = (1, "成功")
        mock_chain_cls.return_value = mock_chain
        plugin = self._plugin()

        plugin.add_subscribe({"tmdbid": 233076, "name": "问心2", "season": 2})
        assert plugin._check_media_status.call_args.args[2] == 2


class TestSeasonAwareStatus:
    """状态检查按季区分：已订第 1 季不应挡住第 2 季"""

    def test_season_subscribed_helper(self):
        from app.plugins.maoyandianying import MaoyanDianYing
        s = types.SimpleNamespace
        subs = [s(season=1), s(season=2)]
        assert MaoyanDianYing._season_subscribed(subs, 2) is True
        assert MaoyanDianYing._season_subscribed([s(season=1)], 2) is False

    def test_legacy_null_season_covers_all(self):
        """历史订阅 season 为空表示整剧订阅，视为覆盖所有季"""
        from app.plugins.maoyandianying import MaoyanDianYing
        subs = [types.SimpleNamespace(season=None)]
        assert MaoyanDianYing._season_subscribed(subs, 2) is True

    def test_no_season_always_true(self):
        from app.plugins.maoyandianying import MaoyanDianYing
        assert MaoyanDianYing._season_subscribed([], 0) is True

    def test_status_cache_key_distinguishes_season(self):
        from app.plugins.maoyandianying import MaoyanDianYing
        assert MaoyanDianYing._status_cache_key(100) == "maoyandingyue_status_100"
        assert MaoyanDianYing._status_cache_key(100, 2) == "maoyandingyue_status_100_s2"

    def test_season_in_library_dict_and_str_keys(self):
        from app.plugins.maoyandianying import MaoyanDianYing
        assert MaoyanDianYing._season_in_library(
            types.SimpleNamespace(seasoninfo={1: [1, 2], 2: [1]}), 2) is True
        assert MaoyanDianYing._season_in_library(
            types.SimpleNamespace(seasoninfo={"2": [1]}), 2) is True
        assert MaoyanDianYing._season_in_library(
            types.SimpleNamespace(seasoninfo={1: [1]}), 2) is False
        assert MaoyanDianYing._season_in_library(None, 2) is False
        assert MaoyanDianYing._season_in_library(
            types.SimpleNamespace(seasoninfo={1: [1]}), 0) is False


class TestSeasonInTransfer:
    """整理记录的 seasons 形如 'S01'，按季判定避免第 1 季挡住第 2 季"""

    def test_matches_s01_form(self):
        from app.plugins.maoyandianying import MaoyanDianYing
        assert MaoyanDianYing._season_in_transfer(
            types.SimpleNamespace(seasons="S02"), 2) is True
        assert MaoyanDianYing._season_in_transfer(
            types.SimpleNamespace(seasons="S01"), 2) is False

    def test_matches_plain_digit(self):
        from app.plugins.maoyandianying import MaoyanDianYing
        assert MaoyanDianYing._season_in_transfer(
            types.SimpleNamespace(seasons="2"), 2) is True

    def test_empty_or_missing(self):
        from app.plugins.maoyandianying import MaoyanDianYing
        assert MaoyanDianYing._season_in_transfer(
            types.SimpleNamespace(seasons=""), 2) is False
        assert MaoyanDianYing._season_in_transfer(None, 2) is False
        assert MaoyanDianYing._season_in_transfer(
            types.SimpleNamespace(seasons="S02"), 0) is False


# ---------- 季详情接口（详情弹窗按季展示）----------

class TestGetSeasonApi:
    """get-season 接口：弹窗按季取简介/首播/海报/演员"""

    def _plugin(self, season_detail=None):
        plugin = _make_plugin(mpnews=False)
        plugin._MaoyanDianYing__get_season_detail = MagicMock(return_value=season_detail)
        return plugin

    def test_returns_season_payload(self):
        plugin = self._plugin({
            "season_number": 2, "name": "第 2 季", "air_date": "2026-06-18",
            "overview": "第2季简介", "poster_path": "/s2.jpg", "vote_average": 8.0,
            "episodes": [{}] * 40,
            "credits": {"cast": [{"name": "赵又廷"}, {"name": "毛晓彤"}]},
        })
        result = plugin.get_season(tmdbid=233076, season=2)
        assert result["success"] is True
        d = result["data"]
        assert d["season_number"] == 2
        assert d["air_date"] == "2026-06-18"
        assert d["overview"] == "第2季简介"
        assert d["poster_path"] == "/s2.jpg"
        assert d["episode_count"] == 40
        assert [c["name"] for c in d["cast"]] == ["赵又廷", "毛晓彤"]

    def test_missing_params(self):
        plugin = self._plugin({})
        assert plugin.get_season(tmdbid=None, season=2)["success"] is False
        assert plugin.get_season(tmdbid=233076, season=None)["success"] is False

    def test_season_not_found(self):
        plugin = self._plugin(None)
        result = plugin.get_season(tmdbid=331830, season=2)
        assert result["success"] is False
        assert "第 2 季" in result["message"]

    def test_bad_param_format(self):
        plugin = self._plugin({})
        assert plugin.get_season(tmdbid="abc", season=2)["success"] is False

    def test_exception_contained(self):
        plugin = _make_plugin(mpnews=False)
        plugin._MaoyanDianYing__get_season_detail = MagicMock(side_effect=RuntimeError("炸"))
        result = plugin.get_season(tmdbid=233076, season=2)
        assert result["success"] is False

    def test_endpoint_registered(self):
        """get-season 需注册到 get_api，前端才能调用"""
        plugin = _make_plugin(mpnews=False)
        paths = [api["path"] for api in plugin.get_api()]
        assert "/get-season" in paths


# ---------- 老缓存补算季号 ----------

class TestSeasonFromCache:
    """season 字段后加，老缓存/老 rows 需按需补算，且不能把片名数字当季号"""

    def _plugin(self, cache):
        plugin = _make_plugin(mpnews=False)
        plugin._MaoyanDianYing__get_cached_tmdb = MagicMock(side_effect=lambda t: cache.get(t))
        return plugin

    def test_backfills_real_season(self):
        """问心2：TMDB 名称不含原名 → 真季号"""
        plugin = self._plugin({"问心2": {"id": 233076, "name": "问心"}})
        assert plugin._MaoyanDianYing__season_from_cache("问心2") == 2

    def test_skips_title_own_digit(self):
        """我们的少年时代2：TMDB 名称就含原名 → 数字属片名，不是季号"""
        plugin = self._plugin({"我们的少年时代2": {"id": 331830, "name": "我们的少年时代2"}})
        assert plugin._MaoyanDianYing__season_from_cache("我们的少年时代2") == 0

    def test_plain_title_returns_zero(self):
        plugin = self._plugin({"云雀叫天录": {"id": 288873, "name": "云雀叫天录"}})
        assert plugin._MaoyanDianYing__season_from_cache("云雀叫天录") == 0

    def test_missing_cache_returns_zero(self):
        plugin = self._plugin({})
        assert plugin._MaoyanDianYing__season_from_cache("问心2") == 0
        assert plugin._MaoyanDianYing__season_from_cache("") == 0

    def test_cache_without_id_returns_zero(self):
        plugin = self._plugin({"问心2": {"name": "问心"}})
        assert plugin._MaoyanDianYing__season_from_cache("问心2") == 0

    def test_get_cache_backfills_rows(self):
        """get_cache 必须给老 rows 补上季号，否则前端拿不到、弹窗显示第 1 季"""
        plugin = _make_plugin(mpnews=False)
        plugin._enabled = True
        rows = [{"name": "问心2", "tmdbid": 233076}]
        plugin._MaoyanDianYing__season_from_cache = MagicMock(return_value=2)
        plugin._check_media_status = MagicMock(return_value="未添加订阅")
        # get_cache 走 super().get_data()，需在基类上打桩
        plugin._PluginBase__dummy = None
        with patch.object(type(plugin).__mro__[1], "get_data", return_value={"rows": rows}):
            result = plugin.get_cache()
        assert result["data"]["rows"][0]["season"] == 2

    def test_get_cache_season_passed_to_status(self):
        """状态检查需带季号，避免第 1 季订阅挡住第 2 季"""
        plugin = _make_plugin(mpnews=False)
        plugin._enabled = True
        rows = [{"name": "问心2", "tmdbid": 233076, "season": 2}]
        plugin._check_media_status = MagicMock(return_value="未添加订阅")
        with patch.object(type(plugin).__mro__[1], "get_data", return_value={"rows": rows}):
            plugin.get_cache()
        assert plugin._check_media_status.call_args.args[2] == 2


# ---------- 消息体结构修正 ----------

class TestNoReadMoreLink:
    """mpnews 不应带 content_source_url（否则点开跳去 MP 页面）"""

    def test_request_has_no_source_url(self):
        from app.plugins.maoyandianying import _WeComMpnews
        sender = _WeComMpnews(MagicMock(get_data=lambda k: None, save_data=MagicMock()), WECOM_CONF)
        sender.send("标题", "正文", "http://img/x.jpg",
                    items=[{"rank": 1, "name": "剧A"}])
        body = json.loads([c for c in _FakeRequestUtils.calls if "message/send" in c[1]][0][2].decode())
        art = body["mpnews"]["articles"][0]
        assert "content_source_url" not in art, art

    def test_source_url_helper_removed(self):
        from app.plugins.maoyandianying import _WeComMpnews
        assert not hasattr(_WeComMpnews, "_source_url")


class TestLeadLineKept:
    """text 里的引导语必须出现在正文（TOP5 提示曾整条丢失）"""

    def _content(self, text, items):
        from app.plugins.maoyandianying import _WeComMpnews
        return _WeComMpnews._build_content(text, items)

    def test_top5_lead_preserved(self):
        text = "今日无新增默认推送top5，\n📺 1. 《一瓯春》（多平台播放）【未订阅】"
        items = [{"rank": 1, "name": "一瓯春", "platform": "多平台播放",
                  "status_tag": "【未订阅】", "first_air_date": "2026-09-17"}]
        html = self._content(text, items)
        assert "今日无新增默认推送top5" in html
        assert "一瓯春" in html

    def test_lead_before_items(self):
        """引导语应排在条目前面"""
        html = self._content("引导语\n📺 1. 《剧A》", [{"rank": 1, "name": "剧A"}])
        assert html.index("引导语") < html.index("剧A")

    def test_no_lead_when_only_items(self):
        html = self._content("📺 1. 《剧A》【未订阅】", [{"rank": 1, "name": "剧A"}])
        assert "📺" not in html.split("剧A")[0]

    def test_lead_not_duplicated_by_numbered_line(self):
        """以序号开头的条目行不应被当成引导语"""
        html = self._content("1. 《剧A》\n📺 2. 《剧B》", [{"rank": 1, "name": "剧A"}])
        assert "1. 《剧A》</p>" not in html.split("<strong>")[0]

    def test_plain_text_path_unchanged(self):
        """无结构化条目时整段原文输出（回退路径不受影响）"""
        html = self._content("第一行\n第二行", None)
        assert "第一行" in html and "第二行" in html


class TestDigest:
    """摘要必须与正常（非 mpnews）图文消息正文完全一致"""

    def test_digest_equals_body_text(self):
        from app.plugins.maoyandianying import _WeComMpnews
        text = ("今日无新增，为您推荐猫眼热度 TOP5：\n"
                "📺 1. 《兰香如故》（腾讯视频独播）【已订阅】\n"
                "📺 2. 《早春晴朗》（优酷独播）【已订阅】")
        digest = _WeComMpnews._build_digest(text, [{"rank": 1, "name": "兰香如故"}])
        assert digest == text, digest

    def test_keeps_emoji_and_platform(self):
        """不能像上一版那样剥掉 📺/序号/平台"""
        from app.plugins.maoyandianying import _WeComMpnews
        text = "📺 1. 《兰香如故》（腾讯视频独播）【已订阅】"
        digest = _WeComMpnews._build_digest(text, [{"rank": 1, "name": "兰香如故"}])
        assert "📺" in digest
        assert "（腾讯视频独播）" in digest
        assert "1." in digest

    def test_keeps_newlines(self):
        from app.plugins.maoyandianying import _WeComMpnews
        assert "\n" in _WeComMpnews._build_digest("第一行\n第二行", None)

    def test_truncated_within_byte_limit(self):
        """超长时按 UTF-8 字节安全截断（mpnews digest 上限 512 字节）"""
        from app.plugins.maoyandianying import _WeComMpnews
        long_text = "\n".join(f"📺 {i}. 《很长的剧名》【已订阅】" for i in range(1, 40))
        digest = _WeComMpnews._build_digest(long_text, None)
        assert len(digest.encode("utf-8")) <= 500
        # 不得截出半个多字节字符
        assert digest == digest.encode("utf-8").decode("utf-8", errors="ignore")

    def test_empty_text(self):
        from app.plugins.maoyandianying import _WeComMpnews
        assert _WeComMpnews._build_digest("", None) == ""
        assert _WeComMpnews._build_digest(None, None) == ""


# ---------- 封面格式规整（40123 invalid image format）----------

WEBP_BYTES = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 24
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 24
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 24
GIF_BYTES = b"GIF89a" + b"\x00" * 24


class TestImageFormatDetect:
    """按文件头识别真实格式（URL 后缀不代表内容）"""

    def _detect(self, data):
        from app.plugins.maoyandianying import _WeComMpnews
        return _WeComMpnews._detect_image_format(data)

    def test_detects_jpeg(self):
        assert self._detect(JPEG_BYTES) == "jpeg"

    def test_detects_png(self):
        assert self._detect(PNG_BYTES) == "png"

    def test_detects_webp(self):
        """宿主管道 Accept 带 image/webp，TMDB 会返回 WebP——必须能识别"""
        assert self._detect(WEBP_BYTES) == "webp"

    def test_detects_gif_and_bmp(self):
        assert self._detect(GIF_BYTES) == "gif"
        assert self._detect(b"BM" + b"\x00" * 24) == "bmp"

    def test_unknown_and_empty(self):
        assert self._detect(b"not an image") == ""
        assert self._detect(b"") == ""


class TestImageNormalize:
    """企业微信素材只接受 JPG/PNG；WebP/GIF/BMP 需转换"""

    def _norm(self, data, filename="cover.jpg", mime="image/jpeg"):
        from app.plugins.maoyandianying import _WeComMpnews
        return _WeComMpnews._normalize_image(data, filename, mime)

    def test_jpeg_passthrough(self):
        c, f, m = self._norm(JPEG_BYTES)
        assert c == JPEG_BYTES and f == "cover.jpg" and m == "image/jpeg"

    def test_png_passthrough(self):
        c, f, m = self._norm(PNG_BYTES, "cover.jpg", "image/jpeg")
        # 内容实际是 PNG，文件名/MIME 应按真实格式纠正
        assert c == PNG_BYTES and f == "cover.png" and m == "image/png"

    def test_webp_converted_to_jpeg(self):
        """核心修复：WebP 必须转成 JPEG，否则企微报 40123"""
        c, f, m = self._norm(WEBP_BYTES)
        if c is None:
            # 无 Pillow 环境下应明确失败，而不是谎报成 JPEG
            assert c is None and f is None and m is None
        else:
            assert c.startswith(b"\xff\xd8\xff"), "转换结果必须是 JPEG"
            assert f == "cover.jpg" and m == "image/jpeg"

    def test_empty_returns_none(self):
        assert self._norm(b"") == (None, None, None)

    def test_unknown_format_passthrough(self):
        c, f, m = self._norm(b"weird bytes", "cover.jpg", "image/jpeg")
        assert c == b"weird bytes" and f == "cover.jpg"


class TestThumbUploadFormat:
    """上传给企微的素材必须是真实 JPG/PNG"""

    def _sender(self, download_result):
        """download_result 为 _download_image 的返回值（已规整过的三元组）。"""
        from app.plugins.maoyandianying import _WeComMpnews
        sender = _WeComMpnews(MagicMock(get_data=lambda k: None, save_data=MagicMock()), WECOM_CONF)
        sender._download_image = MagicMock(return_value=download_result)
        return sender

    def test_download_image_normalizes_host_webp(self):
        """宿主管道返回 WebP 时，_download_image 必须规整为企微可用格式"""
        from app.plugins.maoyandianying import _WeComMpnews
        sender = _WeComMpnews(MagicMock(get_data=lambda k: None, save_data=MagicMock()), WECOM_CONF)
        sender._image_from_host_pipeline = MagicMock(
            return_value=(WEBP_BYTES, "cover.jpg", "image/webp"))
        c, f, m = sender._download_image("http://img/x.jpg")
        if c is not None:
            assert c.startswith(b"\xff\xd8\xff"), "WebP 应转为 JPEG"
            assert m == "image/jpeg"

    def test_normalized_none_aborts_upload(self):
        """规整失败（None）时不得上传，避免企微 40123"""
        sender = self._sender((None, None, None))
        _FakeRequestUtils.reset()
        assert sender._upload_thumb("http://img/x.jpg") is None
        assert [c for c in _FakeRequestUtils.calls if "media/upload" in c[1]] == []

    def test_upload_uses_real_format(self):
        """上传时文件名/MIME 必须与真实内容一致"""
        sender = self._sender((PNG_BYTES, "cover.png", "image/png"))
        _FakeRequestUtils.reset()
        sender._upload_thumb("http://img/x.jpg")
        uploads = [c for c in _FakeRequestUtils.calls if "media/upload" in c[1]]
        assert uploads, _FakeRequestUtils.calls
        files = uploads[0][2]
        assert files["media"][0] == "cover.png"
        assert files["media"][2] == "image/png"

    def test_direct_download_sets_accept_header(self):
        """兜底直连必须声明只接受 jpg/png，避免拿到 WebP"""
        from app.plugins.maoyandianying import _WeComMpnews
        seen = {}

        class _Rec(_FakeRequestUtils):
            def __init__(self, **kw):
                seen.update(kw)

        sender = _WeComMpnews(MagicMock(get_data=lambda k: None, save_data=MagicMock()), WECOM_CONF)
        with patch("app.plugins.maoyandianying.RequestUtils", _Rec):
            sender._download_image_direct("http://img/x.jpg")
        accept = (seen.get("headers") or {}).get("Accept", "")
        assert "image/jpeg" in accept or "image/png" in accept, accept


AVIF_BYTES = b"\x00\x00\x00\x20ftypavif" + b"\x00" * 20
AVIS_BYTES = b"\x00\x00\x00\x20ftypavis" + b"\x00" * 20


class TestAvifDetection:
    """宿主管道 Accept 以 image/avif 居首，TMDB 会优先返回 AVIF"""

    def _detect(self, data):
        from app.plugins.maoyandianying import _WeComMpnews
        return _WeComMpnews._detect_image_format(data)

    def test_detects_avif(self):
        assert self._detect(AVIF_BYTES) == "avif"

    def test_detects_avis(self):
        assert self._detect(AVIS_BYTES) == "avif"

    def test_heic_not_mistaken_for_avif(self):
        """mif1 是 HEIC，不是 AVIF，不应误判"""
        assert self._detect(b"\x00\x00\x00\x20ftypmif1" + b"\x00" * 16) == ""

    def test_mp4_not_mistaken_for_avif(self):
        """isom 是 MP4，不应被当成图片"""
        assert self._detect(b"\x00\x00\x00\x20ftypisom" + b"\x00" * 16) == ""

    def test_avif_converted_or_rejected(self):
        """AVIF 必须转成 JPEG；无 Pillow 时明确失败，绝不谎报 MIME"""
        from app.plugins.maoyandianying import _WeComMpnews
        c, f, m = _WeComMpnews._normalize_image(AVIF_BYTES, "cover.jpg", "image/jpeg")
        if c is not None:
            assert c.startswith(b"\xff\xd8\xff"), "AVIF 应转为 JPEG"
            assert f == "cover.jpg" and m == "image/jpeg"
        else:
            assert (c, f, m) == (None, None, None)
