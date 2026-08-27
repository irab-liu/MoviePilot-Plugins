import random
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


class IrabSubscribeReminder(_PluginBase):
    """IRAB订阅提醒 - 推送当天订阅更新内容。"""

    plugin_name = "IRAB订阅提醒"
    plugin_desc = "推送当天订阅更新内容。（v3兼容版）"
    plugin_icon = "subscribe_reminder.png"
    plugin_version = "1.0.4"
    plugin_author = "irab"
    author_url = "https://github.com/irab-liu"
    plugin_config_prefix = "irabsubscribe_reminder_"
    plugin_order = 34
    auth_level = 1

    _enabled: bool = False
    _onlyonce: bool = False
    _time: Optional[int] = None
    _subtype: Optional[List[str]] = None
    _msgtype: Optional[str] = None
    subscribe_oper: Optional[SubscribeOper] = None
    tmdb: Optional[TmdbChain] = None
    media: Optional[MediaChain] = None

    def init_plugin(self, config: dict = None) -> None:
        """初始化插件。"""
        self.subscribe_oper = SubscribeOper()
        self.tmdb = TmdbChain()
        self.media = MediaChain()

        if config:
            self._enabled = bool(config.get("enabled"))
            self._onlyonce = bool(config.get("onlyonce"))
            self._time = config.get("time")
            self._subtype = config.get("subtype")
            self._msgtype = config.get("msgtype")
            logger.info(f"[IRAB] init_plugin: enabled={self._enabled}, onlyonce={self._onlyonce}, subtype={self._subtype}")

            if self._onlyonce:
                logger.info("[IRAB] 立即运行一次")
                try:
                    self.__send_notify()
                except Exception as e:
                    logger.error(f"[IRAB] 立即运行失败: {e}", exc_info=True)
                self._onlyonce = False
                self.__update_config()

    def __update_config(self) -> None:
        self.update_config({
            "enabled": self._enabled,
            "onlyonce": self._onlyonce,
            "time": self._time,
            "subtype": self._subtype,
            "msgtype": self._msgtype,
        })

    def __resolve_tmdb_id(self, sub, mtype: MediaType = MediaType.TV) -> Optional[int]:
        """
        解析订阅的 TMDB ID。
        V3 模型：media_source + media_id
        兼容：tmdbid（旧模型）
        """
        # 1. 直接检查 media_source + media_id
        media_source = getattr(sub, 'media_source', None)
        media_id = getattr(sub, 'media_id', None)
        
        if media_source is not None and media_id is not None:
            source_str = str(media_source).lower()
            if 'tmdb' in source_str or 'themoviedb' in source_str:
                try:
                    return int(media_id)
                except (ValueError, TypeError):
                    pass
        
        # 2. 兼容旧模型的 tmdbid 属性
        if hasattr(sub, 'tmdbid') and sub.tmdbid:
            try:
                return int(sub.tmdbid)
            except (ValueError, TypeError):
                pass
        
        # 3. 用 recognize_media 识别
        try:
            meta = MetaInfo(title=sub.name, year=sub.year)
            mediainfo = self.media.recognize_media(meta=meta, mtype=mtype)
            if mediainfo and mediainfo.tmdb_id:
                return int(mediainfo.tmdb_id)
        except Exception:
            pass
        
        return None

    def __is_tv(self, sub) -> bool:
        """判断是否为电视剧。"""
        t = sub.type
        if t is None:
            return False
        if t == MediaType.TV:
            return True
        tv_values = ["电视剧", "tv", "TV", "Tv", "series", "Series"]
        if isinstance(t, str) and t.strip() in tv_values:
            return True
        return False

    def __is_movie(self, sub) -> bool:
        """判断是否为电影。"""
        t = sub.type
        if t is None:
            return False
        if t == MediaType.MOVIE:
            return True
        movie_values = ["电影", "movie", "MOVIE", "Movie"]
        if isinstance(t, str) and t.strip() in movie_values:
            return True
        return False

    def __send_notify(self) -> None:
        """核心推送逻辑。"""
        logger.info("[IRAB] __send_notify 开始执行")

        if not self.subscribe_oper:
            self.subscribe_oper = SubscribeOper()
        if not self.tmdb:
            self.tmdb = TmdbChain()
        if not self.media:
            self.media = MediaChain()

        subscribes = self.subscribe_oper.list()
        if not subscribes:
            logger.error("[IRAB] 当前没有订阅，跳过处理")
            return

        logger.info(f"[IRAB] 共 {len(subscribes)} 条订阅, subtype={self._subtype}")

        if not self._subtype:
            logger.error("[IRAB] 订阅类型不能为空")
            return

        current_date = datetime.now().date().strftime("%Y-%m-%d")
        logger.info(f"[IRAB] 当前日期: {current_date}")

        mtype = NotificationType.Plugin
        if self._msgtype:
            try:
                mtype = NotificationType[self._msgtype]
            except (KeyError, TypeError):
                logger.warning(f"[IRAB] 无效的消息类型：{self._msgtype}，回退到 Manual")
                mtype = NotificationType.Manual

        current_tv_subscribe: List[Dict[str, Any]] = []
        current_movie_subscribe: List[Dict[str, Any]] = []

        for i, subscribe in enumerate(subscribes):
            logger.info(f"[IRAB] 订阅[{i}]: name={subscribe.name}, type={subscribe.type}, media_source={getattr(subscribe, 'media_source', 'N/A')}, media_id={getattr(subscribe, 'media_id', 'N/A')}, season={getattr(subscribe, 'season', None)}")
            
            if self.__is_tv(subscribe):
                tmdb_id = self.__resolve_tmdb_id(subscribe, MediaType.TV)
                season = subscribe.season
                
                if not tmdb_id or not season:
                    logger.info(f"[IRAB]  跳过 {subscribe.name}: tmdb_id={tmdb_id}, season={season}")
                    continue

                try:
                    episodes_info = self.tmdb.tmdb_episodes(
                        tmdbid=tmdb_id,
                        season=int(season),
                    )
                except Exception as e:
                    logger.error(f"[IRAB] 获取剧集失败 {subscribe.name}: {e}")
                    continue

                if not episodes_info:
                    logger.info(f"[IRAB]  {subscribe.name} 无剧集数据")
                    continue

                episodes = [
                    episode.episode_number
                    for episode in episodes_info
                    if episode and episode.air_date and str(episode.air_date) == current_date
                ]

                if episodes:
                    logger.info(f"[IRAB]  {subscribe.name} S{season} 今日更新: {episodes}")
                    current_tv_subscribe.append({
                        'name': f"{subscribe.name} ({subscribe.year})",
                        'season': f"S{str(season).rjust(2, '0')}",
                        'episode': (
                            f"E{str(episodes[0]).rjust(2, '0')}-E{str(episodes[-1]).rjust(2, '0')}"
                            if len(episodes) > 1
                            else f"E{str(episodes[0]).rjust(2, '0')}"
                        ),
                        'image': subscribe.backdrop or subscribe.poster,
                    })
                else:
                    logger.info(f"[IRAB]  {subscribe.name} 今日无更新")

            # 电影
            if "movie" in self._subtype and self.__is_movie(subscribe):
                tmdb_id = self.__resolve_tmdb_id(subscribe, MediaType.MOVIE)
                
                if not tmdb_id:
                    logger.info(f"[IRAB]  跳过 {subscribe.name}: 缺少 tmdbid")
                    continue

                try:
                    meta = MetaInfo(title=subscribe.name, year=subscribe.year)
                    mediainfo = self.media.recognize_media(
                        meta=meta,
                        mtype=MediaType.MOVIE,
                        media_source=MediaSource.TMDB,
                        media_id=str(int(tmdb_id)),
                    )
                except Exception as e:
                    logger.error(f"[IRAB] 识别媒体失败 {subscribe.name}: {e}")
                    continue

                if not mediainfo:
                    logger.info(f"[IRAB]  {subscribe.name} 未识别到媒体信息")
                    continue

                if str(mediainfo.release_date) == current_date:
                    logger.info(f"[IRAB]  {subscribe.name} 今日上映!")
                    current_movie_subscribe.append({
                        'name': f"{subscribe.name} ({subscribe.year})",
                        'image': subscribe.backdrop or subscribe.poster,
                    })
                else:
                    logger.info(f"[IRAB]  {subscribe.name} release_date={mediainfo.release_date}")

        # 推送
        if "tv" in self._subtype and current_tv_subscribe:
            logger.info(f"[IRAB] 准备推送 {len(current_tv_subscribe)} 条电视剧更新")
            self.__send_batch_message(
                mtype=mtype,
                title="电视剧更新",
                items=current_tv_subscribe,
                icon="📺︎",
                include_season=True,
            )

        if "movie" in self._subtype and current_movie_subscribe:
            logger.info(f"[IRAB] 准备推送 {len(current_movie_subscribe)} 条电影更新")
            self.__send_batch_message(
                mtype=mtype,
                title="电影更新",
                items=current_movie_subscribe,
                icon="📽︎",
                include_season=False,
            )

        if not current_tv_subscribe and not current_movie_subscribe:
            logger.info("[IRAB] 今日无匹配更新，不推送")

    def __send_batch_message(
        self,
        mtype: NotificationType,
        title: str,
        items: List[Dict[str, Any]],
        icon: str,
        include_season: bool,
    ) -> None:
        """分批发送消息，每 8 条发送一次。"""
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
                logger.info(f"[IRAB] 发送{title}: {text.strip()}")
                self.post_message(
                    mtype=mtype,
                    title=title,
                    text=text,
                    image=random.choice(images) if images else None,
                )
                text = ""
                images = []

        if text:
            logger.info(f"[IRAB] 发送{title}: {text.strip()}")
            self.post_message(
                mtype=mtype,
                title=title,
                text=text,
                image=random.choice(images) if images else None,
            )

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        return []

    def get_api(self) -> List[Dict[str, Any]]:
        return []

    def get_service(self) -> List[Dict[str, Any]]:
        if not self.get_state():
            return []
        if not self._time or not str(self._time).isdigit():
            return []
        return [{
            "id": "IrabSubscribeReminder.DailyPush",
            "name": "IRAB订阅提醒每日推送",
            "trigger": CronTrigger.from_crontab(f"0 {int(self._time)} * * *"),
            "func": self.__send_notify,
            "kwargs": {},
        }]

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
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
        return None

    def stop_service(self) -> None:
        self._enabled = False
