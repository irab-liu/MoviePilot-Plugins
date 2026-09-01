"""
猫眼热度榜 - MoviePilot V3 插件
猫眼网播【电视剧+网剧】热度 TOP30 剧集订阅情况，一键订阅。
"""

import json
import re
import time
import hashlib
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import Body
from app.chain.subscribe import SubscribeChain
from app.db.oper.mediaserver import MediaServerOper
from app.db.oper.subscribe import SubscribeOper
from app.db.oper.transferhistory import TransferHistoryOper
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
    plugin_desc = "猫眼网播【电视剧+网剧】热度 TOP30 剧集订阅情况，一键订阅。"
    plugin_icon = "Moviepilot_A.png"
    plugin_version = "1.1.1"
    plugin_author = "irab"
    author_url = "https://github.com/irab-liu"
    plugin_config_prefix = "maoyandingyue_"
    plugin_order = 50
    auth_level = 1

    _enabled = False
    _cache_key = "maoyandingyue_data"
    _refresh_interval = 6  # 默认6小时自动刷新
    _subscribe_oper = None
    _media_oper = None
    _fetch_lock = threading.Lock()
    _warmup_lock = threading.Lock()
    _warmup_done = False
    _tmdb_cache_prefix = "maoyandingyue_tmdb_"
    _status_cache_ttl = 300  # Status Check 短 TTL 缓存（秒）

    def init_plugin(self, config: dict | None = None) -> None:
        """读取配置并建立本次运行所需状态。"""
        config = config or {}
        logger.debug("【init_plugin】收到的配置: %s", config)
        self._enabled = bool(config.get("enabled", False))
        self._refresh_interval = int(config.get("refresh_interval", 6))
        self._subscribe_oper = SubscribeOper()
        self._media_oper = MediaServerOper()
        self._transfer_oper = TransferHistoryOper()
        logger.info("插件初始化完成，enabled=%s, refresh_interval=%sh", self._enabled, self._refresh_interval)
        if self._enabled:
            self.__start_warmup()
            cached = super().get_data(self._cache_key)
            if not cached or not isinstance(cached, dict) or not cached.get("rows"):
                logger.info("【启用后抓取】未发现有效缓存，启动首次后台抓取")
                threading.Thread(
                    target=self._auto_refresh,
                    name="MaoyanDianYing.InitialRefresh",
                    daemon=True,
                ).start()
            else:
                logger.info("【启用后抓取】发现已有缓存，共 %d 条，不重复抓取", len(cached.get("rows", [])))

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
            name="maoyandingyue_warmup"
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
            heat_list = MaoyanScraper.fetch_heat_list()
            if not heat_list:
                logger.warning("【预热】榜单数据为空，跳过")
                return
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
        """生成 TMDB 二级缓存 key"""
        md5 = hashlib.md5(title.encode("utf-8")).hexdigest()[:12]
        return f"maoyandingyue_tmdb_{md5}"

    @staticmethod
    def __tmdb_result_to_serializable(tmdb_info: dict) -> dict:
        """将 TMDB 搜索结果转换为 JSON 可序列化 dict（处理 MediaType 枚举）"""
        if not tmdb_info:
            return tmdb_info
        result = dict(tmdb_info)
        if "media_type" in result and hasattr(result["media_type"], "value"):
            result["media_type"] = result["media_type"].value
        return result

    def __get_cached_tmdb(self, title: str) -> Optional[dict]:
        """从二级缓存读取 TMDB 数据"""
        cache_key = self.__tmdb_cache_key(title)
        try:
            cached = self.get_data(cache_key)
            if cached and isinstance(cached, dict):
                return cached
        except Exception:
            pass
        return None

    def __save_cached_tmdb(self, title: str, tmdb_info: dict) -> None:
        """保存 TMDB 数据到二级缓存"""
        cache_key = self.__tmdb_cache_key(title)
        try:
            self.save_data(cache_key, self.__tmdb_result_to_serializable(tmdb_info))
        except Exception:
            pass

    def __search_tmdb_with_cache(self, title: str) -> Optional[dict]:
        """带二级缓存的 TMDB 搜索"""
        cached = self.__get_cached_tmdb(title)
        if cached:
            return cached
        try:
            api = TmdbApi(language="zh")
            result = api.search_tvs(title, "")
            if result and len(result) > 0:
                self.__save_cached_tmdb(title, result[0])
                return result[0]
        except Exception as e:
            logger.error("【TMDB搜索】'%s' 失败: %s", title, e)
        return None

    def _get_cached_status(self, tmdbid: int, name: str = "") -> Optional[str]:
        """从短 TTL 缓存读取状态"""
        if not tmdbid:
            return None
        cache_key = f"maoyandingyue_status_{tmdbid}"
        try:
            cached = self.get_data(cache_key)
            if cached and isinstance(cached, dict):
                if time.time() - cached.get("ts", 0) < self._status_cache_ttl:
                    return cached.get("status")
        except Exception:
            pass
        return None

    def _save_cached_status(self, tmdbid: int, status: str) -> None:
        """保存状态到短 TTL 缓存"""
        if not tmdbid:
            return
        cache_key = f"maoyandingyue_status_{tmdbid}"
        try:
            self.save_data(cache_key, {"status": status, "ts": time.time()})
        except Exception:
            pass

    def get_state(self) -> bool:
        """返回插件当前是否启用。"""
        return self._enabled

    @staticmethod
    def get_render_mode() -> tuple[str, str]:
        """返回 Vue 远程组件渲染模式及产物目录。"""
        render_mode = ("vue", "dist/assets")
        logger.info("【联邦组件】渲染模式：mode=%s, path=%s", render_mode[0], render_mode[1])
        return render_mode

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
            {
                "path": "/get-cache",
                "endpoint": self.get_cache,
                "methods": ["GET"],
                "summary": "获取缓存数据",
                "description": "返回当前缓存的猫眼热度数据，不触发数据抓取",
                "auth": "bear",
            },
            {
                "path": "/get-cast",
                "endpoint": self.get_cast,
                "methods": ["GET"],
                "summary": "获取演员阵容",
                "description": "根据 TMDB ID 获取演员阵容数据",
                "auth": "bear",
            },
        ]

    def _check_media_status(self, tmdbid: int, name: str = "") -> str:
        """按 TMDB 媒体身份返回"影片已入库""订阅已添加"或"未添加订阅"。"""
        if not tmdbid:
            logger.debug("【状态检查】tmdbid 为空，返回未添加")
            return "未添加订阅"

        # 短 TTL 缓存检查
        cached_status = self._get_cached_status(tmdbid, name)
        if cached_status is not None:
            logger.debug("【状态检查】缓存命中：tmdbid=%s, status=%s", tmdbid, cached_status)
            return cached_status

        media_source = "themoviedb"
        media_id = str(tmdbid)
        logger.info(
            "【状态检查】开始：tmdbid=%s, media_source=%s, media_id=%s, mtype=%s",
            tmdbid,
            media_source,
            media_id,
            MediaType.TV.value,
        )

        # 1. 查询媒体库（按 TMDB 媒体身份）
        try:
            item = self._media_oper.exists(
                media_source=media_source,
                media_id=media_id,
                mtype=MediaType.TV.value,
            )
        except Exception as e:
            logger.error("【状态检查】媒体库查询异常：media_id=%s, error=%s", media_id, e)
            self._save_cached_status(tmdbid, "未添加订阅")
            return "未添加订阅"

        if item:
            logger.info(
                "【状态检查】媒体库命中：title=%s, media_source=%s, media_id=%s, item_type=%s",
                getattr(item, "title", ""),
                getattr(item, "media_source", ""),
                getattr(item, "media_id", ""),
                getattr(item, "item_type", ""),
            )
            self._save_cached_status(tmdbid, "影片已入库")
            return "影片已入库"

        logger.info("【状态检查】媒体库身份未命中：media_source=%s, media_id=%s", media_source, media_id)

        # 2. 兼容历史媒体库记录：按剧名和电视剧类型做兜底匹配
        if name:
            try:
                title_item = self._media_oper.exists(
                    title=name,
                    mtype=MediaType.TV.value,
                )
            except Exception as e:
                logger.error("【状态检查】按标题查询媒体库异常：title=%s, error=%s", name, e)
                title_item = None
            if title_item:
                logger.info(
                    "【状态检查】按标题命中媒体库：title=%s, stored_title=%s, "
                    "stored_media_source=%s, stored_media_id=%s, stored_item_type=%s",
                    name,
                    getattr(title_item, "title", ""),
                    getattr(title_item, "media_source", ""),
                    getattr(title_item, "media_id", ""),
                    getattr(title_item, "item_type", ""),
                )
                self._save_cached_status(tmdbid, "影片已入库")
                return "影片已入库"
            logger.info("【状态检查】按标题也未命中：title=%s, mtype=%s", name, MediaType.TV.value)

        # 3. 兼容飞牛/绿联等不支持媒体服务器同步协议的环境：通过文件整理记录表判断
        try:
            transfer_records = self._transfer_oper.get_by(
                media_source=media_source,
                media_id=media_id,
                mtype=MediaType.TV.value,
            )
            transfer_record = next(
                (record for record in transfer_records if getattr(record, "status", False)),
                None,
            )
        except Exception as e:
            logger.error("【状态检查】整理记录查询异常：media_id=%s, error=%s", media_id, e)
            transfer_record = None
        if transfer_record:
            logger.info(
                "【状态检查】整理记录命中：title=%s, dest=%s",
                getattr(transfer_record, "title", ""),
                getattr(transfer_record, "dest", ""),
            )
            self._save_cached_status(tmdbid, "影片已入库")
            return "影片已入库"
        logger.info("【状态检查】整理记录未命中：media_source=%s, media_id=%s", media_source, media_id)

        # 4. 最后查询订阅表
        try:
            subs = self._subscribe_oper.list_by_media_identity(
                media_source=media_source, media_id=media_id
            )
        except Exception as e:
            logger.error("【状态检查】订阅查询异常：media_id=%s, error=%s", media_id, e)
            self._save_cached_status(tmdbid, "未添加订阅")
            return "未添加订阅"

        if subs:
            logger.info("【状态检查】订阅命中：media_source=%s, media_id=%s, count=%s", media_source, media_id, len(subs))
            self._save_cached_status(tmdbid, "订阅已添加")
            return "订阅已添加"

        logger.info("【状态检查】媒体库、整理记录和订阅均未命中：media_source=%s, media_id=%s", media_source, media_id)
        self._save_cached_status(tmdbid, "未添加订阅")
        return "未添加订阅"

    def get_form(self) -> tuple[list[dict], dict[str, Any]]:
        """返回配置页面和默认配置。"""
        logger.info("【配置页面】返回 Vuetify 配置表单（Vue 模式使用远程 Config 组件）")
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
        """Vue 远程组件模式下不再使用 Vuetify JSON 渲染。"""
        logger.info("【数据页面】返回空 JSON，交由远程 Page 组件渲染")
        return []

    def stop_service(self) -> None:
        """标记插件停用；定时任务由 MoviePilot 根据 ``get_service`` 统一移除。"""
        self._enabled = False
        with self._warmup_lock:
            self._warmup_done = False
        logger.info("插件已停止")

    def add_subscribe(self, body: dict = Body(...)) -> dict[str, Any]:
        """为指定剧集添加订阅，并返回 MoviePilot 标准响应结构。"""
        tmdbid = body.get("tmdbid")
        name = str(body.get("name", "")).strip()
        logger.info("【添加订阅】收到请求：%s (TMDB ID: %s)", name, tmdbid)

        # 旧缓存可能没有 TMDB ID。按剧名即时补查，不能把 0 提交给订阅链。
        if not tmdbid and name:
            logger.info("【添加订阅】TMDB ID 为空，开始按剧名补查：%s", name)
            tmdb_info = self.__search_tmdb_with_cache(name)
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
            logger.error("【添加订阅】异常：%s", e)
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
                    # 新条目才获取 TMDB（带二级缓存）
                    tmdb_info = self.__search_tmdb_with_cache(name)
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
        logger.info("【刷新数据API】收到请求")
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
                tmdb_info = self.__search_tmdb_with_cache(name)
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

    def get_cache(self):
        """获取缓存数据，不触发抓取。"""
        logger.info("【获取缓存API】收到请求：enabled=%s", self.get_state())
        if not self.get_state():
            logger.info("【获取缓存API】插件未启用，返回未启用状态")
            return {
                "success": True,
                "enabled": False,
                "data": {"rows": [], "total": 0},
                "from_cache": False,
            }
        cached = super().get_data(self._cache_key)
        if cached and isinstance(cached, dict) and cached.get("rows"):
            # 每次读取缓存都重新计算状态，确保订阅/入库操作后状态最新
            for item in cached.get("rows", []):
                item["status"] = self._check_media_status(
                    item.get("tmdbid", 0), item.get("name", "")
                )
            logger.info("【获取缓存API】返回缓存数据，共 %d 条", len(cached.get("rows", [])))
            return {"success": True, "enabled": True, "data": cached, "from_cache": True}
        logger.info("【获取缓存API】缓存为空")
        return {"success": True, "enabled": True, "data": {"rows": [], "total": 0}, "from_cache": False}

    def get_cast(self, tmdbid: int = None):
        """获取演员阵容数据。"""
        logger.info("【获取演员API】收到请求：tmdbid=%s", tmdbid)
        if not tmdbid:
            return {"success": False, "message": "缺少 tmdbid 参数", "data": None}
        try:
            api = TmdbApi(language="zh")
            result = api.tv.credits(tmdbid)
            cast = result.get("cast", [])[:20]
            logger.info("【获取演员API】返回 %d 条演员数据", len(cast))
            return {"success": True, "data": cast}
        except Exception as e:
            logger.error("【获取演员API】失败：%s", e)
            return {"success": False, "message": str(e), "data": None}

    def run_once(self):
        """立即运行1次 API（实时抓取并更新缓存）。"""
        logger.info("【立即运行1次API】收到请求")
        logger.info("【立即运行1次】开始实时抓取...")
        start_time = time.time()
        try:
            heat_list = MaoyanScraper.fetch_heat_list()
            logger.info("抓取到 %d 条热度数据，开始补充 TMDB 信息...", len(heat_list))

            enriched = []
            for item in heat_list:
                name = item.get("name", "")
                tmdb_info = self.__search_tmdb_with_cache(name)
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
