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
    """订阅提醒v3 - 推送当天订阅更新内容。"""

    plugin_name = "订阅提醒v3"
    plugin_desc = "推送当天订阅更新内容。（v3兼容版）"
    plugin_icon = "subscribe_reminder.png"
    plugin_version = "1.0.7"
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
        self.subscribe_oper = SubscribeOper()
        self.tmdb = TmdbChain()
        self.media = MediaChain()
        if config:
            self._enabled = bool(config.get("enabled"))
            self._onlyonce = bool(config.get("onlyonce"))
            self._time = config.get("time")
            self._subtype = config.get("subtype")
            self._msgtype = config.get("msgtype")
            if self._onlyonce:
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
        media_source = getattr(sub, 'media_source', None)
        media_id = getattr(sub, 'media_id', None)
        if media_source is not None and media_id is not None:
            source_str = str(media_source).lower()
            if 'tmdb' in source_str or 'themoviedb' in source_str:
                try:
                    return int(media_id)
                except (ValueError, TypeError):
                    pass
        if hasattr(sub, 'tmdbid') and sub.tmdbid:
            try:
                return int(sub.tmdbid)
            except (ValueError, TypeError):
                pass
        try:
            meta = MetaInfo(title=sub.name, year=sub.year)
            mediainfo = self.media.recognize_media(meta=meta, mtype=mtype)
            if mediainfo and mediainfo.tmdb_id:
                return int(mediainfo.tmdb_id)
        except Exception:
            pass
        return None

    def __is_tv(self, sub) -> bool:
        t = sub.type
        if t is None:
            return False
        if t == MediaType.TV:
            return True
        return isinstance(t, str) and t.strip() in ("电视剧", "tv", "TV", "Tv", "series", "Series")

    def __is_movie(self, sub) -> bool:
        t = sub.type
        if t is None:
            return False
        if t == MediaType.MOVIE:
            return True
        return isinstance(t, str) and t.strip() in ("电影", "movie", "MOVIE", "Movie")

    def __send_notify(self) -> None:
        if not self.subscribe_oper:
            self.subscribe_oper = SubscribeOper()
        if not self.tmdb:
            self.tmdb = TmdbChain()
        if not self.media:
            self.media = MediaChain()

        subscribes = self.subscribe_oper.list()
        if not subscribes or not self._subtype:
            return

        current_date = datetime.now().date().strftime("%Y-%m-%d")
        mtype = NotificationType.Plugin
        if self._msgtype:
            try:
                mtype = NotificationType[self._msgtype]
            except (KeyError, TypeError):
                mtype = NotificationType.Manual

        current_tv = []
        current_movie = []

        for sub in subscribes:
            if "tv" in self._subtype and self.__is_tv(sub):
                tmdb_id = self.__resolve_tmdb_id(sub, MediaType.TV)
                season = sub.season
                if not tmdb_id or not season:
                    continue
                try:
                    episodes_info = self.tmdb.tmdb_episodes(tmdbid=tmdb_id, season=int(season))
                except Exception:
                    continue
                if not episodes_info:
                    continue
                episodes = [ep.episode_number for ep in episodes_info if ep and ep.air_date and str(ep.air_date) == current_date]
                if episodes:
                    current_tv.append({
                        'name': f"{sub.name} ({sub.year})",
                        'season': f"S{str(season).rjust(2, '0')}",
                        'episode': f"E{str(episodes[0]).rjust(2, '0')}-E{str(episodes[-1]).rjust(2, '0')}" if len(episodes) > 1 else f"E{str(episodes[0]).rjust(2, '0')}",
                        'image': sub.backdrop or sub.poster,
                    })

            if "movie" in self._subtype and self.__is_movie(sub):
                tmdb_id = self.__resolve_tmdb_id(sub, MediaType.MOVIE)
                if not tmdb_id:
                    continue
                try:
                    meta = MetaInfo(title=sub.name, year=sub.year)
                    mediainfo = self.media.recognize_media(meta=meta, mtype=MediaType.MOVIE, media_source=MediaSource.TMDB, media_id=str(int(tmdb_id)))
                except Exception:
                    continue
                if not mediainfo:
                    continue
                if str(mediainfo.release_date) == current_date:
                    current_movie.append({
                        'name': f"{sub.name} ({sub.year})",
                        'image': sub.backdrop or sub.poster,
                    })

        if current_tv:
            self.__send_batch(mtype, "电视剧更新", current_tv, "📺︎", True)
        if current_movie:
            self.__send_batch(mtype, "电影更新", current_movie, "📽︎", False)

        self.save_data('today_updates', {
            'tv': current_tv,
            'movie': current_movie,
            'last_run': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        })

    def __send_batch(self, mtype, title, items, icon, include_season):
        text = ""
        images = []
        count = 0
        for item in items:
            line = f"{icon}{item.get('name')}"
            if include_season:
                line += f" {item.get('season')}{item.get('episode')}"
            text += line + "\n"
            images.append(item.get('image'))
            count += 1
            if count % 8 == 0:
                self.post_message(mtype=mtype, title=title, text=text, image=random.choice(images) if images else None)
                text = ""
                images = []
        if text:
            self.post_message(mtype=mtype, title=title, text=text, image=random.choice(images) if images else None)

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        return []

    def get_api(self) -> List[Dict[str, Any]]:
        return []

    def get_service(self) -> List[Dict[str, Any]]:
        if not self.get_state() or not self._time or not str(self._time).isdigit():
            return []
        return [{
            "id": "IrabSubscribeReminder.DailyPush",
            "name": "订阅提醒v3每日推送",
            "trigger": CronTrigger.from_crontab(f"0 {int(self._time)} * * *"),
            "func": self.__send_notify,
            "kwargs": {},
        }]

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        msg_options = [{"title": item.value, "value": item.name} for item in NotificationType]
        return [{"component": "VForm", "content": [
            {"component": "VRow", "content": [
                {"component": "VCol", "props": {"cols": 12, "md": 4}, "content": [
                    {"component": "VSwitch", "props": {"model": "enabled", "label": "启用插件"}}]},
                {"component": "VCol", "props": {"cols": 12, "md": 4}, "content": [
                    {"component": "VSwitch", "props": {"model": "onlyonce", "label": "立即运行一次"}}]},
            ]},
            {"component": "VRow", "content": [
                {"component": "VCol", "props": {"cols": 12, "md": 4}, "content": [
                    {"component": "VTextField", "props": {"model": "time", "label": "时间", "placeholder": "默认9点"}}]},
                {"component": "VCol", "props": {"cols": 12, "md": 4}, "content": [
                    {"component": "VSelect", "props": {"multiple": True, "chips": True, "model": "subtype", "label": "订阅类型", "items": [
                        {"title": "电影", "value": "movie"}, {"title": "电视剧", "value": "tv"}]}}]},
                {"component": "VCol", "props": {"cols": 12, "md": 4}, "content": [
                    {"component": "VSelect", "props": {"multiple": False, "chips": True, "model": "msgtype", "label": "消息类型", "items": msg_options}}]},
            ]},
            {"component": "VRow", "content": [
                {"component": "VCol", "props": {"cols": 12}, "content": [
                    {"component": "VAlert", "props": {"type": "info", "variant": "tonal", "text": "默认每天9点推送，需开启（订阅）通知类型。"}}]},
            ]},
        ]}], {
            "enabled": False, "onlyonce": False,
            "subtype": ["movie", "tv"], "msgtype": "Plugin", "time": 9,
        }

    def get_page(self) -> List[dict]:
        today_data = self.get_data('today_updates')
        if not today_data:
            return [{"component": "VRow", "content": [{"component": "VCol", "props": {"cols": 12}, "content": [
                {"component": "VAlert", "props": {"type": "info", "variant": "tonal", "text": "暂无更新数据，请运行一次插件或等待定时执行。"}}]}]}]

        tv_items = today_data.get('tv', [])
        movie_items = today_data.get('movie', [])
        last_run = today_data.get('last_run', '未知')
        all_items = (
            [{**item, 'kind': '电视剧'} for item in tv_items] +
            [{**item, 'kind': '动漫'} for item in today_data.get('anime', [])] +
            [{**item, 'kind': '电影'} for item in movie_items]
        )
        contents = []
        contents.append({"component": "VRow", "content": [{"component": "VCol", "props": {"cols": 12}, "content": [
            {"component": "VAlert", "props": {"type": "success", "variant": "tonal", "text": f"最后更新：{last_run}  |  今日更新：{len(all_items)} 条"}}]}]})
        if not all_items:
            contents.append({"component": "VRow", "content": [{"component": "VCol", "props": {"cols": 12}, "content": [
                {"component": "VAlert", "props": {"type": "info", "variant": "tonal", "text": "今日暂无更新内容"}}]}]})
            return contents
        contents.append({"component": "VRow", "props": {"class": "text-caption text-medium-emphasis border-b mb-2"}, "content": [
            {"component": "VCol", "props": {"cols": 1}, "content": [{"component": "div", "text": "#"}]},
            {"component": "VCol", "props": {"cols": 2}, "content": [{"component": "div", "text": "类型"}]},
            {"component": "VCol", "props": {"cols": 6}, "content": [{"component": "div", "text": "名称"}]},
            {"component": "VCol", "props": {"cols": 3}, "content": [{"component": "div", "text": "更新集数"}]},
        ]})
        for idx, item in enumerate(all_items, 1):
            kind = item.get('kind', '电视剧')
            season = item.get('season', '')
            episode = item.get('episode', '')
            update_info = f"{season}{episode}" if season else '上映'
            contents.append({"component": "VRow", "props": {"class": "border-b"}, "content": [
                {"component": "VCol", "props": {"cols": 1}, "content": [{"component": "div", "text": str(idx), "props": {"class": "text-center pa-2 text-caption"}}]},
                {"component": "VCol", "props": {"cols": 2}, "content": [{"component": "div", "text": kind, "props": {"class": "text-center pa-2"}}]},
                {"component": "VCol", "props": {"cols": 6}, "content": [{"component": "div", "text": item.get('name', ''), "props": {"class": "pa-2 font-weight-medium"}}]},
                {"component": "VCol", "props": {"cols": 3}, "content": [{"component": "div", "text": update_info, "props": {"class": "text-center pa-2 text-caption"}}]},
            ]})
        return contents

    def stop_service(self) -> None:
        self._enabled = False
