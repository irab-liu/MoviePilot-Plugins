import random
import threading
from datetime import datetime
from typing import Any, List, Dict, Tuple, Optional

from apscheduler.triggers.cron import CronTrigger

from app.chain.media import MediaChain
from app.chain.tmdb import TmdbChain
from app.db.oper.subscribe import SubscribeOper
from app.plugins import _PluginBase
from app.sdk.logging import logger
from app.sdk.media import MetaInfo
from app.schemas import NotificationType, MediaType, MediaSource


class SubscribeReminder(_PluginBase):
    """订阅提醒 - 推送当天订阅更新内容。"""

    # 插件名称
    plugin_name = "订阅提醒"
    # 插件描述
    plugin_desc = "推送当天订阅更新内容。"
    # 插件图标
    plugin_icon = "subscribe_reminder.png"
    # 插件版本
    plugin_version = "1.0.0"
    # 插件作者
    plugin_author = "thsrite"
    # 作者主页
    author_url = "https://github.com/thsrite"
    # 插件配置项ID前缀
    plugin_config_prefix = "subscribereminder_"
    # 加载顺序
    plugin_order = 33
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _enabled: bool = False
    _onlyonce: bool = False
    _time: Optional[int] = None
    _subtype: Optional[List[str]] = None
    _msgtype: Optional[str] = None
    subscribe_oper: Optional[SubscribeOper] = None
    tmdb: Optional[TmdbChain] = None
    media: Optional[MediaChain] = None

    def init_plugin(self, config: dict = None) -> None:
        """
        初始化插件。
        建立 SubscribeOper / TmdbChain / MediaChain 实例，
        并根据配置注册定时服务或立即运行一次。
        """
        self.subscribe_oper = SubscribeOper()
        self.tmdb = TmdbChain()
        self.media = MediaChain()

        if config:
            self._enabled = bool(config.get("enabled"))
            self._onlyonce = bool(config.get("onlyonce"))
            self._time = config.get("time")
            self._subtype = config.get("subtype")
            self._msgtype = config.get("msgtype")

            # 立即运行一次：启动守护线程执行推送，并复位配置
            if self._onlyonce:
                logger.info("订阅提醒服务启动，立即运行一次")
                threading.Thread(target=self.__send_notify, daemon=True).start()
                self._onlyonce = False
                self.__update_config()

    def __update_config(self) -> None:
        """持久化当前配置。"""
        self.update_config({
            "enabled": self._enabled,
            "onlyonce": self._onlyonce,
            "time": self._time,
            "subtype": self._subtype,
            "msgtype": self._msgtype,
        })

    def __send_notify(self) -> None:
        """
        核心推送逻辑：
        - 遍历所有订阅，按 MediaType.TV / MediaType.MOVIE 分类
        - 电视剧：调用 TmdbChain.tmdb_episodes 获取季内剧集，筛选 air_date == 今天的
        - 电影：调用 MediaChain.recognize_media 识别，筛选 release_date == 今天的
        - 每 8 条分批发消息，带随机封面图
        """
        if not self.subscribe_oper:
            self.subscribe_oper = SubscribeOper()
        if not self.tmdb:
            self.tmdb = TmdbChain()
        if not self.media:
            self.media = MediaChain()

        # 查询所有订阅
        subscribes = self.subscribe_oper.list()
        if not subscribes:
            logger.error("当前没有订阅，跳过处理")
            return

        if not self._subtype:
            logger.error("订阅类型不能为空")
            return

        # 当前日期
        current_date = datetime.now().date().strftime("%Y-%m-%d")

        # 解析消息类型
        mtype = NotificationType.Plugin
        if self._msgtype:
            try:
                mtype = NotificationType[self._msgtype]
            except (KeyError, TypeError):
                logger.warning(f"无效的消息类型：{self._msgtype}，回退到 Manual")
                mtype = NotificationType.Manual

        current_tv_subscribe: List[Dict[str, Any]] = []
        current_movie_subscribe: List[Dict[str, Any]] = []

        # 遍历订阅，查询 TMDB
        for subscribe in subscribes:
            # 电视剧
            if "tv" in self._subtype and subscribe.type == MediaType.TV:
                if not subscribe.tmdbid or not subscribe.season:
                    continue

                # 获取某季所有集
                episodes_info = self.tmdb.tmdb_episodes(
                    tmdbid=subscribe.tmdbid,
                    season=subscribe.season,
                )
                if not episodes_info:
                    continue

                # 筛选当前日期发布的剧集
                episodes = [
                    episode.episode_number
                    for episode in episodes_info
                    if episode and episode.air_date and str(episode.air_date) == current_date
                ]

                if episodes:
                    current_tv_subscribe.append({
                        'name': f"{subscribe.name} ({subscribe.year})",
                        'season': f"S{str(subscribe.season).rjust(2, '0')}",
                        'episode': (
                            f"E{str(episodes[0]).rjust(2, '0')}-E{str(episodes[-1]).rjust(2, '0')}"
                            if len(episodes) > 1
                            else f"E{str(episodes[0]).rjust(2, '0')}"
                        ),
                        'image': subscribe.backdrop or subscribe.poster,
                    })

            # 电影
            if "movie" in self._subtype and subscribe.type == MediaType.MOVIE:
                if not subscribe.tmdbid:
                    continue

                # 识别媒体信息
                meta = MetaInfo(title=subscribe.name, year=subscribe.year)
                mediainfo = self.media.recognize_media(
                    meta=meta,
                    mtype=MediaType.MOVIE,
                    media_source=MediaSource.TMDB,
                    media_id=str(subscribe.tmdbid),
                )
                if not mediainfo:
                    continue

                if str(mediainfo.release_date) == current_date:
                    current_movie_subscribe.append({
                        'name': f"{subscribe.name} ({subscribe.year})",
                        'image': subscribe.backdrop or subscribe.poster,
                    })

        # 推送电视剧
        if "tv" in self._subtype and current_tv_subscribe:
            self.__send_batch_message(
                mtype=mtype,
                title="电视剧更新",
                items=current_tv_subscribe,
                icon="📺︎",
                include_season=True,
            )

        # 推送电影
        if "movie" in self._subtype and current_movie_subscribe:
            self.__send_batch_message(
                mtype=mtype,
                title="电影更新",
                items=current_movie_subscribe,
                icon="📽︎",
                include_season=False,
            )

    def __send_batch_message(
        self,
        mtype: NotificationType,
        title: str,
        items: List[Dict[str, Any]],
        icon: str,
        include_season: bool,
    ) -> None:
        """
        分批发送消息，每 8 条发送一次。

        Args:
            mtype: 通知类型
            title: 消息标题
            items: 订阅条目列表
            icon: 消息前缀图标（📺︎ / 📽︎）
            include_season: 是否包含季/集信息（电视剧为 True）
        """
        text = ""
        images: List[str] = []
        count = 0

        for item in items:
            line = f"{icon}{item.get('name')}"
            if include_season:
                line += f" {item.get('season')}{item.get('episode')}"
            line += "\n"
            text += line
            count += 1
            images.append(item.get('image'))

            if count % 8 == 0:
                self.post_message(
                    mtype=mtype,
                    title=title,
                    text=text,
                    image=random.choice(images) if images else None,
                )
                logger.info(f"推送{title}：{text}")
                text = ""
                images = []

        # 发送剩余内容
        if text:
            self.post_message(
                mtype=mtype,
                title=title,
                text=text,
                image=random.choice(images) if images else None,
            )
            logger.info(f"推送{title}：{text}")

    def get_state(self) -> bool:
        """返回插件是否启用。"""
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        """无需注册远程命令。"""
        return []

    def get_api(self) -> List[Dict[str, Any]]:
        """无需注册 API 端点。"""
        return []

    def get_service(self) -> List[Dict[str, Any]]:
        """
        注册定时服务。
        插件启用时，按配置的时间（默认 9 点）注册每日推送任务。
        """
        if not self.get_state():
            return []
        if not self._time or not str(self._time).isdigit():
            return []
        return [{
            "id": "SubscribeReminder.DailyPush",
            "name": "订阅提醒每日推送",
            "trigger": CronTrigger.from_crontab(f"0 {int(self._time)} * * *"),
            "func": self.__send_notify,
            "kwargs": {},
        }]

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面。
        返回两块数据：1. 页面配置（Vuetify 组件树）；2. 默认数据结构。
        """
        # 遍历 NotificationType 枚举，生成消息类型选项
        MsgTypeOptions = [
            {"title": item.value, "value": item.name}
            for item in NotificationType
        ]

        return [
            {
                'component': 'VForm',
                'content': [
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 4},
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'enabled',
                                            'label': '启用插件',
                                        },
                                    }
                                ],
                            },
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 4},
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'onlyonce',
                                            'label': '立即运行一次',
                                        },
                                    }
                                ],
                            },
                        ],
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 4},
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'time',
                                            'label': '时间',
                                            'placeholder': '默认9点',
                                        },
                                    }
                                ],
                            },
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 4},
                                'content': [
                                    {
                                        'component': 'VSelect',
                                        'props': {
                                            'multiple': True,
                                            'chips': True,
                                            'model': 'subtype',
                                            'label': '订阅类型',
                                            'items': [
                                                {"title": "电影", "value": "movie"},
                                                {"title": "电视剧", "value": "tv"},
                                            ],
                                        },
                                    }
                                ],
                            },
                            {
                                'component': 'VCol',
                                'props': {'cols': 12, 'md': 4},
                                'content': [
                                    {
                                        'component': 'VSelect',
                                        'props': {
                                            'multiple': False,
                                            'chips': True,
                                            'model': 'msgtype',
                                            'label': '消息类型',
                                            'items': MsgTypeOptions,
                                        },
                                    }
                                ],
                            },
                        ],
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {'cols': 12},
                                'content': [
                                    {
                                        'component': 'VAlert',
                                        'props': {
                                            'type': 'info',
                                            'variant': 'tonal',
                                            'text': '默认每天9点推送，需开启（订阅）通知类型。',
                                        },
                                    }
                                ],
                            }
                        ],
                    },
                ],
            }
        ], {
            "enabled": False,
            "onlyonce": False,
            "subtype": ["movie", "tv"],
            "msgtype": "Plugin",
            "time": 9,
        }

    def get_page(self) -> Optional[List[dict]]:
        """无需独立页面。"""
        return None

    def stop_service(self) -> None:
        """
        停用插件。
        V3 使用 get_service() 注册定时任务，宿主负责调度器生命周期，
        此处只需复位启用状态。
        """
        self._enabled = False
