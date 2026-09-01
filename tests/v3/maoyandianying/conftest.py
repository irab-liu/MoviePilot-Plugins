"""MaoyanDianYing 测试配置 — mock 第三方依赖 + 加载真实插件代码"""
import sys
import os
import types
from enum import Enum
from unittest.mock import MagicMock


def _make_module(name, attrs=None):
    mod = types.ModuleType(name)
    if attrs:
        for k, v in attrs.items():
            setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


# 1. mock 第三方依赖（apscheduler / fastapi / requests）
apscheduler = _make_module('apscheduler')
apscheduler.triggers = _make_module('apscheduler.triggers')
apscheduler.triggers.interval = _make_module('apscheduler.triggers.interval', {'IntervalTrigger': MagicMock()})

fastapi = _make_module('fastapi', {'Body': MagicMock()})

requests_mock = _make_module('requests')
requests_mock.get = MagicMock(return_value=MagicMock(status_code=200, text='{}', json=lambda: {}))
requests_mock.post = MagicMock(return_value=MagicMock(status_code=200, text='{}', json=lambda: {}))
requests_mock.Session = MagicMock

# 2. mock 宿主 app 模块层级
class _PluginBase:
    def __init__(self, *args, **kwargs):
        pass

    def get_data(self, key):
        return None

    def save_data(self, key, value):
        pass

    def del_data(self, key):
        pass

    def get_cmd(self, cmd):
        return None


class MediaType(Enum):
    TV = "tv"
    MOVIE = "movie"


app = _make_module('app')
app.plugins = _make_module('app.plugins', {'_PluginBase': _PluginBase})
app.chain = _make_module('app.chain')
app.chain.subscribe = _make_module('app.chain.subscribe', {'SubscribeChain': type('SubscribeChain', (), {'add': staticmethod(lambda *a, **k: None)})()})
app.db = _make_module('app.db')
app.db.oper = _make_module('app.db.oper')
app.db.oper.mediaserver = _make_module('app.db.oper.mediaserver', {'MediaServerOper': type('MediaServerOper', (), {'exists': staticmethod(lambda *a, **k: None)})()})
app.db.oper.subscribe = _make_module('app.db.oper.subscribe', {'SubscribeOper': type('SubscribeOper', (), {'exists': staticmethod(lambda *a, **k: False)})()})
app.db.oper.transferhistory = _make_module('app.db.oper.transferhistory', {'TransferHistoryOper': type('TransferHistoryOper', (), {'get': staticmethod(lambda *a, **k: None)})()})
app.modules = _make_module('app.modules')
app.modules.themoviedb = _make_module('app.modules.themoviedb')
app.modules.themoviedb.tmdbapi = _make_module('app.modules.themoviedb.tmdbapi', {'TmdbApi': type('TmdbApi', (), {'search_tv': staticmethod(lambda *a, **k: [])})()})
app.sdk = _make_module('app.sdk')
app.sdk.logging = _make_module('app.sdk.logging', {'logger': MagicMock()})
app.schemas = _make_module('app.schemas')
app.schemas.types = _make_module('app.schemas.types', {'MediaType': MediaType})

# 3. 添加 plugins.v3 目录到 sys.path 并导入真实插件
v3_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'plugins.v3'))
if v3_path not in sys.path:
    sys.path.insert(0, v3_path)

import importlib
maoyan_mod = importlib.import_module('maoyandianying')
sys.modules['app.plugins.maoyandianying'] = maoyan_mod
app.plugins.maoyandianying = maoyan_mod
