"""
猫眼热度榜 - MoviePilot V3 插件
抓取猫眼网播热度 TOP30 剧集，展示 TMDB 海报和演员。
"""

import json
import re
import time
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import Body
from app.chain.subscribe import SubscribeChain
from app.db.oper.mediaserver import MediaServerOper
from app.db.oper.subscribe import SubscribeOper
from app.modules.themoviedb.tmdbapi import TmdbApi
from app.plugins import _PluginBase
from app.sdk.logging import logger
from app.schemas.types import MediaType


class MaoyanScraper:
    """猫眼网播热度数据抓取器"""

    HEAT_URL = "https://piaofang.maoyan.com/web-heat"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    @classmethod
    def fetch_heat_list(cls) -> List[Dict[str, Any]]:
        """抓取并解析猫眼网播热度榜，返回最多 30 条标准化记录。

        Raises:
            requests.RequestException: 猫眼页面请求失败。
            ValueError: 页面中不存在可解析的 ``AppData`` 数据。
        """
        logger.info("开始抓取猫眼热度列表: %s", cls.HEAT_URL)
        resp = requests.get(cls.HEAT_URL, headers=cls.HEADERS, timeout=15)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        logger.info("HTTP %s, 内容长度 %d bytes", resp.status_code, len(resp.text))

        match = re.search(r'AppData\s*=\s*(\{.*?\});', resp.text, re.DOTALL)
        if not match:
            logger.error("未能从猫眼页面匹配 AppData 数据")
            raise ValueError("未能从猫眼页面提取 AppData 数据")

        data = json.loads(match.group(1))
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
                "tmdbid": 0,
            })
        return results


class TmdbHelper:
    """TMDB 数据辅助器（使用 MoviePilot 内置 TMDB API）"""

    @staticmethod
    def search_tv(name: str) -> Optional[Dict[str, Any]]:
        """按剧名搜索 TMDB，返回首条匹配结果；失败或无结果时返回 ``None``。"""
        try:
            api = TmdbApi(language="zh")
            result = api.search_tvs(name, "")
            if result and len(result) > 0:
                logger.debug("TMDB搜索 '%s' → ID %s", name, result[0].get("id"))
                return result[0]
            else:
                logger.warning("TMDB搜索 '%s' 无结果", name)
        except Exception as e:
            logger.error("TMDB搜索 '%s' 失败: %s", name, e)
        return None

    @staticmethod
    def get_tv_credits(tmdbid: int) -> List[str]:
        """获取前五位演员，并将最终展示名称的总长度限制在 10 个字符内。"""
        try:
            api = TmdbApi(language="zh")
            result = api.tv.credits(tmdbid)
            cast = result.get("cast", [])[:5]
            actors = []
            total_chars = 0
            for c in cast:
                name = c.get("name", "")
                if not name:
                    continue
                if total_chars + len(name) > 10:
                    break
                actors.append(name)
                total_chars += len(name)
            return actors
        except Exception as e:
            logger.error("TMDB获取演员 %s 失败: %s", tmdbid, e)
            return []

    @staticmethod
    def get_poster_url(poster_path: str) -> str:
        """将 TMDB 海报相对路径转换为完整 URL；空路径返回空字符串。"""
        if not poster_path:
            return ""
        if poster_path.startswith("http"):
            return poster_path
        return f"https://image.tmdb.org/t/p/w500{poster_path}"


class MaoyanDianYing(_PluginBase):
    """猫眼热度榜插件主类"""

    plugin_name = "猫眼热度榜"
    plugin_desc = "抓取猫眼网播热度 TOP30 剧集，展示 TMDB 海报和演员。"
    plugin_icon = "Moviepilot_A.png"
    plugin_version = "1.0.0"
    plugin_author = "irab"
    author_url = ""
    plugin_config_prefix = "maoyandingyue_"
    plugin_order = 50
    auth_level = 1

    _enabled = False
    _cache_key = "maoyandingyue_data"
    _refresh_interval = 6  # 默认6小时自动刷新
    _subscribe_oper = None
    _media_oper = None
    _fetch_lock = threading.Lock()

    def init_plugin(self, config: dict | None = None) -> None:
        """读取配置并建立本次运行所需状态。"""
        config = config or {}
        logger.debug("【init_plugin】收到的配置: %s", config)
        # 与 get_form() 默认配置保持一致；关闭开关或重置后必须保持停用。
        self._enabled = bool(config.get("enabled", False))
        self._refresh_interval = int(config.get("refresh_interval", 6))
        self._subscribe_oper = SubscribeOper()
        self._media_oper = MediaServerOper()
        logger.info("插件初始化完成，enabled=%s, refresh_interval=%sh", self._enabled, self._refresh_interval)

    def get_state(self) -> bool:
        """返回插件当前是否启用。"""
        return self._enabled

    @staticmethod
    def get_command() -> list[dict[str, Any]]:
        """当前插件不注册远程命令。"""
        return []

    def get_service(self) -> list[dict]:
        """插件启用时注册周期刷新任务；停用时不向宿主注册任何服务。"""
        if not self.get_state():
            return []
        return [
            {
                "id": "MaoyanDianYing.AutoRefresh",
                "name": "猫眼热度榜自动刷新",
                "trigger": IntervalTrigger(hours=self._refresh_interval),
                "func": self._auto_refresh,
                "kwargs": {},
            }
        ]

    def get_api(self) -> list[dict[str, Any]]:
        """注册后端 API。"""
        return [
            {
                "path": "/refresh",
                "endpoint": self.refresh_tmdb,
                "methods": ["POST"],
                "summary": "刷新数据",
                "description": "重新获取 TMDB 海报和演员数据（不重新抓取猫眼榜单）",
                "auth": "bear",
            },
            {
                "path": "/run-once",
                "endpoint": self.run_once,
                "methods": ["POST"],
                "summary": "立即运行1次",
                "description": "立即执行一次完整抓取（猫眼榜单 + TMDB），返回实时结果并更新缓存",
                "auth": "bear",
            },
            {
                "path": "/subscribe",
                "endpoint": self.add_subscribe,
                "methods": ["POST"],
                "summary": "添加订阅",
                "description": "为指定 TMDB ID 的剧集添加订阅",
                "auth": "bear",
            },
        ]

    def _check_media_status(self, tmdbid: int) -> str:
        """按 TMDB 媒体身份返回“影片已入库”“订阅已添加”或“未添加订阅”。"""
        if not tmdbid:
            logger.debug("【状态检查】tmdbid 为空，返回未添加")
            return "未添加订阅"
        media_source = "themoviedb"
        media_id = str(tmdbid)
        logger.debug("【状态检查】tmdbid=%s, media_source=%s, media_id=%s", tmdbid, media_source, media_id)
        # 使用宿主公开接口判断媒体库状态，明确指定电视剧类型。
        item = self._media_oper.exists(
            media_source=media_source,
            media_id=media_id,
            mtype=MediaType.TV.value,
        )
        # 再查订阅
        subs = self._subscribe_oper.list_by_media_identity(
            media_source=media_source, media_id=media_id
        )
        logger.debug("【状态检查】订阅查询结果: %s", subs)
        if subs:
            return "订阅已添加"
        return "未添加订阅"

    def get_form(self) -> tuple[list[dict], dict[str, Any]]:
        """返回配置页面和默认配置。"""
        return [
            {
                "component": "VForm",
                "content": [
                    {
                        "component": "VSwitch",
                        "props": {
                            "model": "enabled",
                            "label": "启用插件",
                        },
                    },
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
                    },
                    {
                        "component": "VAlert",
                        "props": {
                            "type": "info",
                            "variant": "tonal",
                            "density": "compact",
                            "class": "mt-3",
                        },
                        "text": "启用后，系统会按设定间隔自动抓取猫眼榜单。有 TMDB 数据的条目不会重复获取。",
                    },
                ],
            }
        ], {
            "enabled": False,
            "refresh_interval": 6,
        }

    def get_page(self) -> list[dict]:
        """返回插件详情页（卡片样式）。停用时不得抓取或访问业务数据。"""
        if not self.get_state():
            logger.debug("插件未启用，详情页不执行数据抓取")
            return [
                {
                    "component": "VAlert",
                    "props": {
                        "type": "info",
                        "variant": "tonal",
                        "density": "compact",
                    },
                    "text": "插件当前未启用，请先在插件设置中打开“启用插件”并保存。",
                }
            ]

        data = self._get_cached_data()
        rows = data.get("rows", [])

        cards = []
        for row in rows:
            actors = " / ".join(row.get("actors", [])) if row.get("actors") else "暂无"
            # 检查订阅/入库状态
            status_text = self._check_media_status(row.get("tmdbid", 0))
            if status_text == "影片已入库":
                status_color = "#4CAF50"  # 绿色
            elif status_text == "订阅已添加":
                status_color = "#1976D2"  # 蓝色
            else:
                status_color = "#9E9E9E"  # 灰色
            cards.append({
                "component": "VCard",
                "props": {
                    "variant": "outlined",
                    "class": "mb-2",
                    "rounded": "lg",
                },
                "content": [
                    {
                        "component": "VRow",
                        "props": {"no-gutters": True, "align": "center"},
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": "auto", "class": "pa-2"},
                                "content": [
                                    {
                                        "component": "div",
                                        "props": {"style": "position: relative;"},
                                        "content": [
                                            {
                                                "component": "VImg",
                                                "props": {
                                                    "src": row.get("poster", ""),
                                                    "width": 90,
                                                    "height": 120,
                                                    "cover": True,
                                                    "rounded": "sm",
                                                    "class": "bg-grey-lighten-3",
                                                },
                                            },
                                            {
                                                "component": "div",
                                                "props": {
                                                    "style": f"position: absolute; bottom: 0; left: 0; right: 0; background: {status_color}; color: white; font-size: 9px; text-align: center; padding: 2px 0; border-bottom-left-radius: 4px; border-bottom-right-radius: 4px;"
                                                },
                                                "text": status_text,
                                            },
                                        ],
                                    }
                                ],
                            },
                            {
                                "component": "VCol",
                                "props": {"class": "pa-2"},
                                "content": [
                                    {
                                        "component": "div",
                                        "props": {"class": "d-flex align-center mb-1"},
                                        "content": [
                                            {
                                                "component": "VChip",
                                                "props": {
                                                    "color": "primary",
                                                    "size": "x-small",
                                                    "label": True,
                                                    "class": "mr-1 text-caption",
                                                },
                                                "text": str(row.get("rank", "")),
                                            },
                                            {
                                                "component": "span",
                                                "props": {
                                                    "class": "font-weight-bold",
                                                    "style": "font-size: 10px;"
                                                },
                                                "text": row.get("name", ""),
                                            },
                                        ],
                                    },
                                    {
                                        "component": "div",
                                        "props": {"class": "mb-0.5", "style": "font-size: 10px;"},
                                        "content": [
                                            {"component": "VIcon", "props": {"size": "x-small", "class": "mr-1", "color": "grey"}, "text": "mdi-television-classic"},
                                            {"component": "span", "text": row.get("platform", "")},
                                        ],
                                    },
                                    {
                                        "component": "div",
                                        "props": {"class": "mb-0.5", "style": "font-size: 10px;"},
                                        "content": [
                                            {"component": "VIcon", "props": {"size": "x-small", "class": "mr-1", "color": "grey"}, "text": "mdi-calendar-clock"},
                                            {"component": "span", "text": row.get("days", "")},
                                        ],
                                    },
                                    {
                                        "component": "div",
                                        "props": {"class": "mb-0.5", "style": "font-size: 10px;"},
                                        "content": [
                                            {"component": "VIcon", "props": {"size": "x-small", "class": "mr-1", "color": "red"}, "text": "mdi-fire"},
                                            {"component": "span", "props": {"class": "font-weight-medium"}, "text": str(row.get("heat", ""))},
                                        ],
                                    },
                                    {
                                        "component": "div",
                                        "props": {"class": "mb-0.5", "style": "font-size: 10px;"},
                                        "content": [
                                            {"component": "VIcon", "props": {"size": "x-small", "class": "mr-1", "color": "grey"}, "text": "mdi-play-circle-outline"},
                                            {"component": "span", "text": row.get("plays", "") or "—"},
                                        ],
                                    },
                                    {
                                        "component": "div",
                                        "props": {"style": "font-size: 10px; color: #999;"},
                                        "content": [
                                            {"component": "VIcon", "props": {"size": "x-small", "class": "mr-1", "color": "grey"}, "text": "mdi-account-group-outline"},
                                            {"component": "span", "text": actors},
                                        ],
                                    },
                                    # 订阅按钮
                                    {
                                        "component": "VBtn",
                                        "props": {
                                            "size": "x-small",
                                            "variant": "tonal",
                                            "color": "primary" if status_text == "未添加订阅" else "grey",
                                            "disabled": status_text != "未添加订阅",
                                            "class": "mt-1",
                                        },
                                        "events": {"click": {"api": "plugin/MaoyanDianYing/subscribe", "method": "POST", "params": {"tmdbid": row.get("tmdbid", 0), "name": row.get("name", "")}}},
                                        "text": status_text if status_text != "未添加订阅" else "订阅",
                                    },
                                ],
                            },
                        ],
                    }
                ],
            })

        return [
            {
                "component": "VRow",
                "content": [
                    {
                        "component": "VCol",
                        "props": {"cols": 12},
                        "content": [
                            {
                                "component": "VBtn",
                                "props": {"color": "primary", "variant": "tonal", "prepend-icon": "mdi-play"},
                                "events": {"click": {"api": "plugin/MaoyanDianYing/run-once", "method": "POST", "params": {}}},
                                "text": "立即运行1次",
                            },
                            {
                                "component": "VBtn",
                                "props": {"color": "secondary", "variant": "tonal", "prepend-icon": "mdi-refresh", "class": "ml-2"},
                                "events": {"click": {"api": "plugin/MaoyanDianYing/refresh", "method": "POST", "params": {}}},
                                "text": "刷新数据",
                            },
                            {
                                "component": "span",
                                "props": {"class": "ml-3 text-grey", "style": "align-self: center; font-size: 11px;"},
                                "text": "💡 立即运行：完整抓取榜单+海报 | 刷新数据：仅重取海报演员",
                            },
                            {
                                "component": "VChip",
                                "props": {"color": "info", "size": "small", "variant": "outlined", "class": "ml-auto"},
                                "content": [
                                    {"component": "VIcon", "props": {"size": "x-small", "start": True}, "text": "mdi-clock-outline"},
                                    {"component": "span", "props": {"style": "font-size: 12px;"}, "text": f"更新时间：{data.get('update_time', '暂无数据')}"},
                                ],
                            },
                        ],
                    },
                    {
                        "component": "VCol",
                        "props": {"cols": 12},
                        "content": [
                            {
                                "component": "VRow",
                                "content": [
                                    {"component": "VCol", "props": {"cols": 12, "md": 4}, "content": [card]}
                                    for card in cards
                                ],
                            }
                        ],
                    },
                ],
            }
        ]

    def stop_service(self) -> None:
        """标记插件停用；定时任务由 MoviePilot 根据 ``get_service`` 统一移除。"""
        self._enabled = False
        logger.info("插件已停止")

    def add_subscribe(self, body: dict = Body(...)) -> dict[str, Any]:
        """为指定剧集添加订阅，并返回 MoviePilot 标准响应结构。"""
        tmdbid = body.get("tmdbid")
        name = str(body.get("name", "")).strip()
        logger.info("【添加订阅】收到请求：%s (TMDB ID: %s)", name, tmdbid)

        # 旧缓存可能没有 TMDB ID。按剧名即时补查，不能把 0 提交给订阅链。
        if not tmdbid and name:
            logger.info("【添加订阅】TMDB ID 为空，开始按剧名补查：%s", name)
            tmdb_info = TmdbHelper.search_tv(name)
            if tmdb_info:
                tmdbid = tmdb_info.get("id")
                logger.info("【添加订阅】按剧名补查成功：%s -> %s", name, tmdbid)
                self._update_cached_tmdbid(name=name, tmdbid=tmdbid)

        if not tmdbid:
            logger.warning("【添加订阅】无法获取 TMDB ID：%s", name)
            return {"success": False, "message": f"未能识别《{name or '未知剧集'}》的 TMDB 信息，请先刷新数据", "data": None}

        try:
            tmdbid = int(tmdbid)
            status = self._check_media_status(tmdbid)
            if status == "影片已入库":
                return {"success": False, "message": "影片已入库，无需重复订阅", "data": None}
            if status == "订阅已添加":
                return {"success": False, "message": "已订阅，无需重复订阅", "data": None}

            subscribe_chain = SubscribeChain()
            sub_id, msg = subscribe_chain.add(
                title=name,
                year="",
                mtype=MediaType.TV,
                media_source="themoviedb",
                media_id=str(tmdbid),
                username="admin",
            )
            if sub_id:
                logger.info("【添加订阅】成功：%s (TMDB ID: %s, 订阅 ID: %d)", name, tmdbid, sub_id)
                return {
                    "success": True,
                    "message": f"订阅已添加：{name}",
                    "data": {"subscribe_id": sub_id, "tmdbid": tmdbid},
                }
            logger.warning("【添加订阅】失败：%s (TMDB ID: %s) - %s", name, tmdbid, msg)
            return {"success": False, "message": str(msg or "添加订阅失败"), "data": None}
        except Exception as e:
            logger.exception("【添加订阅】异常：%s", e)
            return {"success": False, "message": str(e), "data": None}

    def _update_cached_tmdbid(self, name: str, tmdbid: int) -> None:
        """把即时识别出的 TMDB ID 回写到插件缓存。"""
        if not name or not tmdbid:
            return
        try:
            cached = super().get_data(self._cache_key)
            if not isinstance(cached, dict):
                return
            changed = False
            for item in cached.get("rows", []):
                if item.get("name") == name:
                    item["tmdbid"] = int(tmdbid)
                    changed = True
                    break
            if changed:
                self.save_data(self._cache_key, cached)
                logger.info("【添加订阅】已回写缓存 TMDB ID：%s -> %s", name, tmdbid)
        except Exception as e:
            logger.warning("【添加订阅】回写缓存失败：%s", e)

    def _auto_refresh(self):
        """定时自动刷新：抓取榜单，仅对新条目获取 TMDB 数据。"""
        logger.info("【定时刷新】开始...")
        try:
            heat_list = MaoyanScraper.fetch_heat_list()

            # 读取现有缓存（可能包含已有 TMDB 数据）
            cached = super().get_data(self._cache_key)
            existing = {}
            if cached and isinstance(cached, dict):
                for item in cached.get("rows", []):
                    name = item.get("name", "")
                    if name:
                        existing[name] = item

            enriched = []
            new_count = 0
            for item in heat_list:
                name = item.get("name", "")
                # 如果已有 TMDB 数据，直接复用
                if name in existing and existing[name].get("tmdbid"):
                    # 已识别条目完整复用 TMDB 字段，避免新榜单的默认 tmdbid=0 覆盖有效缓存。
                    item["tmdbid"] = existing[name]["tmdbid"]
                    item["poster"] = existing[name].get("poster", "")
                    item["actors"] = existing[name].get("actors", [])
                else:
                    # 新条目才获取 TMDB
                    tmdb_info = TmdbHelper.search_tv(name)
                    if tmdb_info:
                        poster_path = tmdb_info.get("poster_path", "")
                        item["poster"] = TmdbHelper.get_poster_url(poster_path)
                        tmdbid = tmdb_info.get("id")
                        if tmdbid:
                            item["tmdbid"] = tmdbid
                            actors = TmdbHelper.get_tv_credits(tmdbid)
                            if actors:
                                item["actors"] = actors
                    new_count += 1
                enriched.append(item)
                time.sleep(0.3)

            result = {
                "rows": enriched,
                "timestamp": time.time(),
                "total": len(enriched),
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            self.save_data(self._cache_key, result)
            logger.info("【定时刷新】完成，共 %d 条，其中 %d 条为新获取 TMDB", len(enriched), new_count)
        except Exception as e:
            logger.error("【定时刷新】失败: %s", e)

    def refresh_tmdb(self):
        """刷新数据 API：重新获取 TMDB 海报和演员数据（不重新抓取猫眼榜单）。"""
        logger.info("【刷新数据】开始重新获取 TMDB 数据...")
        start_time = time.time()
        try:
            cached = super().get_data(self._cache_key)
            if not cached or not isinstance(cached, dict):
                return {"success": False, "message": "暂无缓存数据，请先运行一次抓取", "data": None}

            rows = cached.get("rows", [])
            if not rows:
                return {"success": False, "message": "缓存为空", "data": None}

            logger.info("开始为 %d 条数据重新获取 TMDB 信息...", len(rows))
            updated = 0
            for item in rows:
                name = item.get("name", "")
                tmdb_info = TmdbHelper.search_tv(name)
                if tmdb_info:
                    poster_path = tmdb_info.get("poster_path", "")
                    item["poster"] = TmdbHelper.get_poster_url(poster_path) or item.get("poster", "")
                    tmdbid = tmdb_info.get("id")
                    if tmdbid:
                        item["tmdbid"] = tmdbid
                        actors = TmdbHelper.get_tv_credits(tmdbid)
                        if actors:
                            item["actors"] = actors
                            updated += 1
                time.sleep(0.3)

            cached["rows"] = rows
            cached["timestamp"] = time.time()
            cached["update_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.save_data(self._cache_key, cached)

            elapsed = round(time.time() - start_time, 1)
            logger.info("【刷新数据】完成，耗时 %ss，更新 %d/%d 条", elapsed, updated, len(rows))
            return {"success": True, "message": f"已更新 {updated} 条 TMDB 数据", "data": cached}
        except Exception as e:
            elapsed = round(time.time() - start_time, 1)
            logger.error("【刷新数据】失败（%ss）: %s", elapsed, e)
            return {"success": False, "message": str(e), "data": None}

    def run_once(self):
        """立即运行1次 API（实时抓取并更新缓存）。"""
        logger.info("【立即运行1次】开始实时抓取...")
        start_time = time.time()
        try:
            heat_list = MaoyanScraper.fetch_heat_list()
            logger.info("抓取到 %d 条热度数据，开始补充 TMDB 信息...", len(heat_list))

            enriched = []
            for item in heat_list:
                name = item.get("name", "")
                tmdb_info = TmdbHelper.search_tv(name)
                if tmdb_info:
                    poster_path = tmdb_info.get("poster_path", "")
                    item["poster"] = TmdbHelper.get_poster_url(poster_path) or item.get("poster", "")
                    tmdbid = tmdb_info.get("id")
                    if tmdbid:
                        item["tmdbid"] = tmdbid
                        actors = TmdbHelper.get_tv_credits(tmdbid)
                        if actors:
                            item["actors"] = actors
                enriched.append(item)
                time.sleep(0.3)

            result = {
                "rows": enriched,
                "timestamp": time.time(),
                "total": len(enriched),
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            self.save_data(self._cache_key, result)

            elapsed = round(time.time() - start_time, 1)
            logger.info("【立即运行1次】完成，耗时 %ss，共 %d 条（已更新缓存）", elapsed, len(enriched))
            return {
                "success": True,
                "message": f"运行完成，耗时 {elapsed}s",
                "data": {"rows": enriched, "total": len(enriched), "elapsed": elapsed},
            }
        except Exception as e:
            elapsed = round(time.time() - start_time, 1)
            logger.error("【立即运行1次】失败（%ss）: %s", elapsed, e)
            return {"success": False, "message": str(e), "data": {"rows": [], "total": 0, "elapsed": elapsed}}

    def _get_cached_data(self) -> Dict[str, Any]:
        """返回有效缓存；缓存缺失或过期时串行执行一次完整抓取。

        双重检查用于避免详情页并发请求在等待锁后重复访问猫眼和 TMDB。
        """
        cached = super().get_data(self._cache_key)
        if cached and isinstance(cached, dict):
            timestamp = cached.get("timestamp", 0)
            if time.time() - timestamp < self._refresh_interval * 3600:
                logger.debug("缓存命中（%ds 前）", int(time.time() - timestamp))
                return cached
        logger.debug("缓存未命中或已过期")
        with self._fetch_lock:
            # 等待锁期间其他请求可能已经生成了新缓存。
            cached = super().get_data(self._cache_key)
            if cached and isinstance(cached, dict):
                timestamp = cached.get("timestamp", 0)
                if time.time() - timestamp < self._refresh_interval * 3600:
                    logger.debug("等待抓取锁后命中缓存（%ds 前）", int(time.time() - timestamp))
                    return cached
            return self._fetch_and_cache()

    def _fetch_and_cache(self) -> Dict[str, Any]:
        """抓取猫眼榜单、补充 TMDB 信息并写入插件数据缓存。"""
        try:
            heat_list = MaoyanScraper.fetch_heat_list()
            enriched = []
            for item in heat_list:
                name = item.get("name", "")
                tmdb_info = TmdbHelper.search_tv(name)
                if tmdb_info:
                    poster_path = tmdb_info.get("poster_path", "")
                    item["poster"] = TmdbHelper.get_poster_url(poster_path) or item.get("poster", "")
                    tmdbid = tmdb_info.get("id")
                    if tmdbid:
                        item["tmdbid"] = tmdbid
                        actors = TmdbHelper.get_tv_credits(tmdbid)
                        if actors:
                            item["actors"] = actors
                enriched.append(item)
                time.sleep(0.3)
            result = {
                "rows": enriched,
                "timestamp": time.time(),
                "total": len(enriched),
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            self.save_data(self._cache_key, result)
            return result
        except Exception as e:
            logger.error("抓取并缓存失败: %s", e)
            return {"rows": [], "timestamp": time.time(), "total": 0, "error": str(e)}
