import base64
import re
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pytz
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.sdk.config import settings
from app.sdk.logging import logger
from app.plugins import _PluginBase
from app.schemas import NotificationType

# 绿联云官网 API 地址
API_BASE = "https://api.ugnas.com"

# 公测反馈 状态
BETA_STATUS_ZH = {
    "PENDING": "待处理",
    "REPORTED": "已提报",
    "VERIFIED": "已验证",
    "CANNOT_REPRODUCE": "无法重现",
    "DUPLICATE": "重复问题",
    "RESOLVED": "已解决",
    "REJECTED": "已拒绝",
}

# 需求反馈 状态码 -> 状态
DEMAND_STATUS_MAP = {
    0: "PENDING",
    1: "EVALUATING",
    2: "ADOPTED",
    3: "ADOPTED",
    4: "LAUNCHED",
    5: "NO_PLAN",
}

# 状态中文文案
STATUS_ZH = {
    "PENDING": "待处理",
    "REPORTED": "已提报",
    "VERIFIED": "已验证",
    "CANNOT_REPRODUCE": "无法重现",
    "DUPLICATE": "重复问题",
    "RESOLVED": "已解决",
    "REJECTED": "已拒绝",
    "EVALUATING": "待评估",
    "ADOPTED": "已采纳",
    "LAUNCHED": "已上线",
    "NO_PLAN": "暂无计划",
}


class ugnasfeedback(_PluginBase):
    plugin_name = "绿联云反馈监控"
    plugin_desc = "通过账号密码自动登录或手动Cookie登录绿联云官网，获取「我的反馈」分类（公测反馈/需求反馈）的信息与状态并推送通知"
    plugin_icon = "ugreen-nas.png"
    plugin_version = "1.0.0"
    plugin_author = "时也，命也"
    author_url = "https://github.com/irab-liu"
    plugin_config_prefix = "ugnasfeedback_"
    plugin_order = 2
    auth_level = 1

    _enabled = False
    _notify = True
    _onlyonce = False
    _notify_only_changed = True
    _cron = "0 9 * * *"
    _cookie = ""
    _username = ""
    _password = ""
    _history_days = 30
    _scheduler: Optional[BackgroundScheduler] = None

    # 本次运行缓存的 token / cookie
    _token: Optional[str] = None
    _cookie_header: Optional[str] = None

    def init_plugin(self, config: dict = None):
        self.stop_service()
        if config:
            self._enabled = config.get("enabled", False)
            self._notify = config.get("notify", True)
            self._onlyonce = config.get("onlyonce", False)
            self._notify_only_changed = config.get("notify_only_changed", True)
            self._cron = config.get("cron", "0 9 * * *")
            self._cookie = (config.get("cookie") or "").strip()
            self._username = (config.get("username") or "").strip()
            self._password = (config.get("password") or "").strip()
            try:
                self._history_days = int(config.get("history_days", 30))
            except Exception:
                self._history_days = 30
        self._token = None
        self._cookie_header = None
        if self._onlyonce:
            self._scheduler = BackgroundScheduler(timezone=settings.TZ)
            self._scheduler.add_job(func=self.sync, trigger='date',
                                    run_date=datetime.now() + timedelta(seconds=3),
                                    name="绿联云反馈监控")
            self._onlyonce = False
            self.update_config({
                "enabled": self._enabled,
                "notify": self._notify,
                "onlyonce": False,
                "notify_only_changed": self._notify_only_changed,
                "cookie": self._cookie,
                "cron": self._cron,
                "username": self._username,
                "password": self._password,
                "history_days": self._history_days,
            })
            if self._scheduler.get_jobs():
                self._scheduler.start()
        if self._enabled and self._cron:
            logger.info(f"注册定时服务: {self._cron}")

    # ==================== 登录/鉴权 ====================

    def _ensure_token(self) -> bool:
        """确保存在可用的鉴权信息（Cookie 或 access_token）"""
        if self._cookie:
            return self._parse_cookie(self._cookie)
        # 尝试使用上次登录保存的 token
        saved = self.get_data('ugnas_access_token')
        if saved:
            self._token = saved
            if self._token_valid():
                return True
            self._token = None
        # 使用账号密码自动登录
        if self._username and self._password:
            return self._auto_login()
        return False

    def _parse_cookie(self, cookie: str) -> bool:
        """解析配置的 Cookie：优先识别 access_token，否则作为 Cookie 头使用"""
        cookie = (cookie or "").strip()
        if not cookie:
            return False
        # 形如 access_token=xxx 或 xxx.xxx.xxx（JWT）时按 token 处理
        m = re.search(r'(?:access_?token|token)=([^\s;]+)', cookie, re.I)
        if m:
            self._token = m.group(1)
            self._cookie_header = None
            return True
        if "=" in cookie and not self._is_jwt(cookie):
            self._cookie_header = cookie
            self._token = None
            return True
        self._token = cookie
        self._cookie_header = None
        return True

    @staticmethod
    def _is_jwt(value: str) -> bool:
        return value.count('.') == 2 and len(value) > 40

    def _token_valid(self) -> bool:
        if not self._token:
            return False
        ok, _, _ = self._fetch_lists()
        return ok

    def _auto_login(self) -> bool:
        """通过账号密码 + RSA 加密调用 oauth/token 获取 access_token"""
        try:
            headers = {
                'User-Agent': self._ua(),
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN',
            }
            # 1. 获取 RSA 公钥与 uuid
            r1 = requests.get(f"{API_BASE}/api/user/v3/sa/auth/seed",
                              headers=headers, timeout=15)
            if r1.status_code != 200:
                logger.warning(f"获取加密密钥失败: HTTP {r1.status_code}")
                return False
            data = r1.json() or {}
            seed = data.get('data') or {}
            encrypt_key = seed.get('encryptKey')
            api_uuid = seed.get('uuid')
            if not encrypt_key or not api_uuid:
                logger.warning(f"未获取到有效加密密钥: {data}")
                return False

            # 2. RSA 加密账号密码
            enc_user, enc_pwd = self._rsa_encrypt_pair(encrypt_key,
                                                       self._username,
                                                       self._password)
            if not enc_user or not enc_pwd:
                logger.warning("RSA 加密账号密码失败")
                return False

            # 3. multipart 登录
            bid = uuid.uuid4().hex
            files = {
                'platform': (None, 'PC'),
                'clientType': (None, 'browser'),
                'osVer': (None, '126.0.0.0'),
                'model': (None, 'Chrome/126.0.0.0'),
                'bid': (None, bid),
                'alias': (None, 'web'),
                'grant_type': (None, 'password'),
                'username': (None, enc_user),
                'password': (None, enc_pwd),
                'uuid': (None, api_uuid),
                'deviceType': (None, '官网'),
                'deviceModel': (None, 'web'),
            }
            r2 = requests.post(f"{API_BASE}/api/oauth/token",
                               headers=headers, files=files, timeout=20)
            if r2.status_code != 200:
                logger.warning(f"登录请求失败: HTTP {r2.status_code}")
                return False
            body = r2.json() or {}
            if body.get('code') != 200:
                logger.warning(f"登录失败: {body.get('msg') or body}")
                return False
            login_data = body.get('data') or {}
            access_token = None
            at = login_data.get('accessToken') or {}
            if isinstance(at, dict):
                access_token = at.get('access_token') or at.get('accessToken')
            if not access_token:
                access_token = login_data.get('access_token')
            if not access_token:
                logger.warning(f"登录响应中未找到 access_token: {str(login_data)[:200]}")
                return False
            self._token = access_token
            self._cookie_header = None
            self.save_data('ugnas_access_token', access_token)
            nick = ''
            user = login_data.get('user') or {}
            if isinstance(user, dict):
                nick = user.get('nicName') or user.get('username') or ''
            logger.info(f"自动登录成功: {nick or '用户'} (token 已保存)")
            return True
        except Exception as e:
            logger.warning(f"自动登录异常: {e}")
            return False

    def _rsa_encrypt_pair(self, encrypt_key: str, username: str, password: str) -> Tuple[str, str]:
        try:
            from Crypto.Cipher import PKCS1_v1_5
            from Crypto.PublicKey import RSA
            der = base64.b64decode(encrypt_key)
            pub = RSA.import_key(der)
            cipher = PKCS1_v1_5.new(pub)
            enc_u = base64.b64encode(cipher.encrypt(username.encode('utf-8'))).decode('utf-8')
            enc_p = base64.b64encode(cipher.encrypt(password.encode('utf-8'))).decode('utf-8')
            return enc_u, enc_p
        except Exception as e:
            logger.warning(f"RSA 加密失败: {e}")
            return "", ""

    @staticmethod
    def _ua() -> str:
        return ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')

    # ==================== 数据获取 ====================

    def _api_headers(self) -> Dict[str, str]:
        headers = {
            'User-Agent': self._ua(),
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN',
        }
        if self._token:
            headers['Authorization'] = self._token
        if self._cookie_header:
            headers['Cookie'] = self._cookie_header
        return headers

    def _fetch_lists(self) -> Tuple[bool, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """获取公测反馈与需求反馈列表。返回 (是否成功, beta列表, demand列表)"""
        beta = self._fetch_beta_list()
        demand = self._fetch_demand_list()
        if beta is None and demand is None:
            return False, [], []
        return True, (beta or []), (demand or [])

    def _fetch_beta_list(self) -> Optional[List[Dict[str, Any]]]:
        """公测反馈: POST wos/v1/ta/order/recruit/fb/my/list"""
        try:
            resp = requests.post(
                f"{API_BASE}/api/wos/v1/ta/order/recruit/fb/my/list",
                headers=self._api_headers(),
                json={"pageNum": 1, "pageSize": 100},
                timeout=20,
            )
            body = resp.json() or {}
            if body.get('code') != 200:
                if body.get('code') == 401:
                    return None
                logger.warning(f"公测反馈列表获取失败: {body.get('msg')}")
                return []
            records = (body.get('data') or {}).get('records') or []
            items = []
            for r in records:
                status = str(r.get('status') or 'PENDING').strip().upper()
                if status not in BETA_STATUS_ZH:
                    status = 'PENDING'
                items.append({
                    "key": f"beta:{r.get('id')}",
                    "category": "beta",
                    "category_name": "公测反馈",
                    "id": str(r.get('id') or ''),
                    "status": status,
                    "status_name": r.get('statusName') or BETA_STATUS_ZH.get(status, status),
                    "title": self._parse_beta_title(r.get('funModule')) or '（无标题）',
                    "content": (r.get('funDesc') or '').strip(),
                    "create_time": self._fmt_time(r.get('occurTime')),
                    "official_reply": (r.get('officialReply') or '').strip(),
                    "reply_time": self._fmt_time(r.get('replyTime')),
                })
            return items
        except Exception as e:
            logger.error(f"公测反馈列表请求异常: {e}")
            return []

    @staticmethod
    def _parse_beta_title(fun_module: Any) -> str:
        if not fun_module:
            return ""
        parts = [p.strip() for p in str(fun_module).split(',') if p.strip()]
        names = []
        for p in parts:
            seg = [s.strip() for s in p.split('/') if s.strip()]
            names.append(seg[-1] if len(seg) >= 2 else seg[0])
        return "、".join([n for n in names if n])

    def _fetch_demand_list(self) -> Optional[List[Dict[str, Any]]]:
        """需求反馈: POST wos/v1/sa/demand/collection/myFeedbackList"""
        try:
            resp = requests.post(
                f"{API_BASE}/api/wos/v1/sa/demand/collection/myFeedbackList",
                headers=self._api_headers(),
                json={"pageNum": 1, "pageSize": 100},
                timeout=20,
            )
            body = resp.json() or {}
            if body.get('code') != 200:
                if body.get('code') == 401:
                    return None
                logger.warning(f"需求反馈列表获取失败: {body.get('msg')}")
                return []
            records = (body.get('data') or {}).get('records') or []
            items = []
            for r in records:
                try:
                    raw_status = int(r.get('status'))
                except Exception:
                    raw_status = 0
                status = DEMAND_STATUS_MAP.get(raw_status, 'PENDING')
                info = " - ".join([str(x) for x in
                                   [r.get('functionalClassify'), r.get('functionalModule')]
                                   if x]) or ''
                items.append({
                    "key": f"demand:{r.get('demandNumber')}",
                    "category": "demand",
                    "category_name": "需求反馈",
                    "id": str(r.get('demandNumber') or ''),
                    "status": status,
                    "status_name": r.get('statusName') or STATUS_ZH.get(status, status),
                    "title": info or '（无标题）',
                    "content": (r.get('description') or '').strip(),
                    "create_time": self._fmt_time(r.get('createTime')),
                    "official_reply": (r.get('officialReply') or '').strip(),
                    "reply_time": self._fmt_time(r.get('replyTime') or r.get('updateTime')),
                })
            return items
        except Exception as e:
            logger.error(f"需求反馈列表请求异常: {e}")
            return []

    @staticmethod
    def _fmt_time(value: Any) -> str:
        if not value:
            return ""
        try:
            if isinstance(value, (int, float)):
                if value > 10 ** 12:
                    value = value / 1000
                return datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')
            s = str(value).strip()
            m = re.search(r'(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})', s)
            if m:
                return f"{m.group(1)}-{m.group(2)}-{m.group(3)} {m.group(4)}:{m.group(5)}:{m.group(6)}"
            m2 = re.search(r'(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})', s)
            if m2:
                return f"{m2.group(1)}-{m2.group(2)}-{m2.group(3)} {m2.group(4)}:{m2.group(5)}"
            return s[:19]
        except Exception:
            return str(value)[:19]

    # ==================== 主流程 ====================

    def sync(self, *args, **kwargs):
        logger.info("开始获取绿联云「我的反馈」信息")
        d = {
            "date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "status": "失败",
            "message": "",
            "total": 0,
            "changes": [],
        }
        # 1. 鉴权
        if not self._ensure_token():
            d["message"] = "鉴权失败：请检查 Cookie 或账号密码配置"
            self._save_history(d)
            if self._notify:
                self.post_message(
                    mtype=NotificationType.SiteMessage,
                    title="🔴 绿联云反馈监控失败",
                    text=f"⏰ {d['date']}\n❌ {d['message']}",
                )
            return d

        # 2. 获取列表（401 时自动重新登录一次）
        ok, beta, demand = self._fetch_lists()
        if not ok and self._username and self._password:
            logger.info("鉴权失效，尝试重新自动登录")
            self._token = None
            self.save_data('ugnas_access_token', None)
            if self._auto_login():
                ok, beta, demand = self._fetch_lists()
        if not ok:
            d["message"] = "获取反馈列表失败（鉴权失效）"
            self._save_history(d)
            if self._notify:
                self.post_message(
                    mtype=NotificationType.SiteMessage,
                    title="🔴 绿联云反馈监控失败",
                    text=f"⏰ {d['date']}\n❌ {d['message']}",
                )
            return d

        current = beta + demand
        d["total"] = len(current)
        changes = self._diff(current)
        d["changes"] = changes
        if changes:
            d["status"] = "有更新"
            d["message"] = f"发现 {len(changes)} 条变更"
        else:
            d["status"] = "无更新"
            d["message"] = f"共 {len(beta)} 条公测反馈、{len(demand)} 条需求反馈，无状态变化"
        self.save_data('ugnas_feedback_state', current)
        self._save_history(d)
        logger.info(f"反馈获取完成: 公测 {len(beta)} 条, 需求 {len(demand)} 条, 变更 {len(changes)} 条")

        # 3. 推送
        if self._notify:
            if changes:
                self._notify_changes(changes, beta, demand)
            elif not self._notify_only_changed:
                self._notify_summary(beta, demand, d['date'])
        return d

    def _diff(self, current: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """对比上次状态，返回变更列表"""
        old = self.get_data('ugnas_feedback_state') or []
        old_map = {o.get('key'): o for o in old if o.get('key')}
        changes = []
        for item in current:
            key = item.get('key')
            prev = old_map.get(key)
            if not prev:
                changes.append({
                    "type": "new",
                    "category_name": item.get('category_name', ''),
                    "title": item.get('title', ''),
                    "status_name": item.get('status_name', ''),
                    "create_time": item.get('create_time', ''),
                    "content": item.get('content', ''),
                    "official_reply": item.get('official_reply', ''),
                })
                continue
            if prev.get('status') != item.get('status'):
                changes.append({
                    "type": "status",
                    "category_name": item.get('category_name', ''),
                    "title": item.get('title', ''),
                    "old_status": STATUS_ZH.get(prev.get('status', ''), prev.get('status', '')),
                    "new_status": STATUS_ZH.get(item.get('status', ''), item.get('status', '')),
                    "reply_time": item.get('reply_time', ''),
                    "official_reply": item.get('official_reply', ''),
                })
            elif (item.get('official_reply') or '') and (prev.get('official_reply') or '') != (item.get('official_reply') or ''):
                changes.append({
                    "type": "reply",
                    "category_name": item.get('category_name', ''),
                    "title": item.get('title', ''),
                    "status_name": item.get('status_name', ''),
                    "official_reply": item.get('official_reply', ''),
                    "reply_time": item.get('reply_time', ''),
                })
        return changes

    def _notify_changes(self, changes: List[Dict[str, Any]], beta: List[Dict[str, Any]], demand: List[Dict[str, Any]]):
        title = f"🔔 绿联云反馈更新（{len(changes)} 条）"
        lines = [f"📊 公测反馈 {len(beta)} 条 | 需求反馈 {len(demand)} 条", "━━━━━━━━━━"]
        for c in changes:
            t = c.get('type')
            if t == 'new':
                lines.append("🆕 新增")
                lines.append(f"• [{c.get('category_name')}] {c.get('title')}")
                lines.append(f"  📌 状态：{c.get('status_name')}  ⏰ {c.get('create_time')}")
            elif t == 'status':
                lines.append(f"🔄 状态更新")
                lines.append(f"• [{c.get('category_name')}] {c.get('title')}")
                lines.append(f"  {c.get('old_status')} → {c.get('new_status')}")
            else:
                lines.append(f"💬 官方回复")
                lines.append(f"• [{c.get('category_name')}] {c.get('title')}")
                reply = c.get('official_reply', '')
                if len(reply) > 120:
                    reply = reply[:120] + "…"
                lines.append(f"  {reply}")
        text = "\n".join(lines)
        self.post_message(mtype=NotificationType.SiteMessage, title=title, text=text)

    def _notify_summary(self, beta: List[Dict[str, Any]], demand: List[Dict[str, Any]], date_str: str):
        title = "📋 绿联云反馈状态"
        lines = [
            f"⏰ {date_str}",
            "━━━━━━━━━━",
            f"📌 公测反馈：{len(beta)} 条",
            f"📌 需求反馈：{len(demand)} 条",
        ]
        text = "\n".join(lines)
        self.post_message(mtype=NotificationType.SiteMessage, title=title, text=text)

    def _save_history(self, record: Dict[str, Any]):
        try:
            history = self.get_data('feedback_history') or []
            history.append(record)
            tz = pytz.timezone(settings.TZ)
            now = datetime.now(tz)
            keep = []
            for r in history:
                try:
                    dt_str = r.get('date', '')
                    if dt_str:
                        dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
                        dt = tz.localize(dt) if dt.tzinfo is None else dt
                    else:
                        dt = now
                except Exception:
                    dt = now
                if (now - dt).days < int(self._history_days):
                    keep.append(r)
            self.save_data('feedback_history', keep)
            logger.info(f"历史记录已保存，当前保留 {len(keep)} 条")
        except Exception as e:
            logger.error(f"保存历史记录失败: {e}")

    # ==================== 插件框架方法 ====================

    def get_state(self) -> bool:
        return self._enabled

    def get_service(self) -> List[Dict[str, Any]]:
        if self._enabled and self._cron:
            return [{
                "id": "ugnasfeedback",
                "name": "绿联云反馈监控",
                "trigger": CronTrigger.from_crontab(self._cron),
                "func": self.sync,
                "kwargs": {}
            }]
        return []

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        return [
            {
                'component': 'VForm',
                'content': [
                    {'component': 'VRow', 'content': [
                        {'component': 'VCol', 'props': {'cols': 12, 'md': 4}, 'content': [{'component': 'VSwitch', 'props': {'model': 'enabled', 'label': '启用插件'}}]},
                        {'component': 'VCol', 'props': {'cols': 12, 'md': 4}, 'content': [{'component': 'VSwitch', 'props': {'model': 'notify', 'label': '开启通知'}}]},
                        {'component': 'VCol', 'props': {'cols': 12, 'md': 4}, 'content': [{'component': 'VSwitch', 'props': {'model': 'onlyonce', 'label': '立即运行一次'}}]},
                    ]},
                    {'component': 'VRow', 'content': [
                        {'component': 'VCol', 'props': {'cols': 12}, 'content': [
                            {'component': 'VSwitch', 'props': {'model': 'notify_only_changed', 'label': '仅变更时通知（关闭则每次推送当前状态汇总）'}}
                        ]},
                    ]},
                    {'component': 'VRow', 'content': [
                        {'component': 'VCol', 'props': {'cols': 12}, 'content': [
                            {'component': 'VAlert', 'props': {'type': 'info', 'variant': 'tonal', 'text': '💡 登录方式：① 填写账号密码自动登录（推荐）；② 手动填 Cookie。Cookie 获取方法：登录 https://web.ugnas.com/ 后按 F12 打开开发者工具，Application > Local Storage 中复制 access_token，或从请求头中复制 Cookie。'}}
                        ]},
                    ]},
                    {'component': 'VRow', 'content': [
                        {'component': 'VCol', 'props': {'cols': 12, 'md': 6}, 'content': [{'component': 'VTextField', 'props': {'model': 'username', 'label': '用户名/手机号/邮箱', 'placeholder': '用于自动登录（可选）'}}]},
                        {'component': 'VCol', 'props': {'cols': 12, 'md': 6}, 'content': [{'component': 'VTextField', 'props': {'model': 'password', 'label': '密码', 'type': 'password', 'placeholder': '用于自动登录（可选）'}}]},
                    ]},
                    {'component': 'VRow', 'content': [
                        {'component': 'VCol', 'props': {'cols': 12}, 'content': [{'component': 'VTextarea', 'props': {'model': 'cookie', 'label': 'Cookie / access_token', 'placeholder': 'access_token=xxx 或完整 Cookie 字符串（与账号密码二选一）', 'rows': 3}}]},
                    ]},
                    {'component': 'VRow', 'content': [
                        {'component': 'VCol', 'props': {'cols': 12, 'md': 6}, 'content': [{'component': 'VCronField', 'props': {'model': 'cron', 'label': '监控周期'}}]},
                        {'component': 'VCol', 'props': {'cols': 12, 'md': 6}, 'content': [{'component': 'VTextField', 'props': {'model': 'history_days', 'label': '历史保留天数', 'type': 'number', 'placeholder': '30'}}]},
                    ]},
                ]
            }
        ], {
            "enabled": False,
            "notify": True,
            "onlyonce": False,
            "notify_only_changed": True,
            "cookie": "",
            "cron": "0 9 * * *",
            "username": "",
            "password": "",
            "history_days": 30,
        }

    def get_page(self) -> List[dict]:
        """插件详情页面"""
        state = self.get_data('ugnas_feedback_state') or []
        history = self.get_data('feedback_history') or []
        if not state and not history:
            return [{
                'component': 'VAlert',
                'props': {
                    'type': 'info',
                    'variant': 'tonal',
                    'text': '暂无反馈记录，请先配置 Cookie 或账号密码并启用插件后运行一次',
                    'class': 'mb-2'
                }
            }]

        cards = []
        if state:
            beta = [x for x in state if x.get('category') == 'beta']
            demand = [x for x in state if x.get('category') == 'demand']
            rows = []
            for item in beta + demand:
                status_name = item.get('status_name') or STATUS_ZH.get(item.get('status', ''), '-')
                rows.append({
                    'component': 'tr',
                    'content': [
                        {'component': 'td', 'props': {'class': 'text-caption'}, 'text': item.get('category_name', '')},
                        {'component': 'td', 'props': {'class': 'text-caption'}, 'text': item.get('create_time', '')},
                        {'component': 'td', 'props': {'class': 'text-caption'}, 'text': item.get('title', '')},
                        {'component': 'td', 'content': [{'component': 'VChip', 'props': {'size': 'small', 'variant': 'outlined'}, 'text': status_name}]},
                        {'component': 'td', 'props': {'class': 'text-caption'}, 'text': ('有' if item.get('official_reply') else '无')},
                    ]
                })
            cards.append({
                'component': 'VCard',
                'props': {'variant': 'elevated', 'elevation': 2, 'rounded': 'lg', 'class': 'mb-4'},
                'content': [
                    {'component': 'VCardTitle', 'props': {'class': 'text-h6 font-weight-bold'}, 'text': f'📋 我的反馈 (公测 {len(beta)} 条 | 需求 {len(demand)} 条)'},
                    {'component': 'VCardText', 'content': [
                        {'component': 'VTable', 'props': {'hover': True, 'density': 'comfortable'}, 'content': [
                            {'component': 'thead', 'content': [{'component': 'tr', 'content': [
                                {'component': 'th', 'props': {'class': 'text-body-2'}, 'text': '分类'},
                                {'component': 'th', 'props': {'class': 'text-body-2'}, 'text': '创建时间'},
                                {'component': 'th', 'props': {'class': 'text-body-2'}, 'text': '标题'},
                                {'component': 'th', 'props': {'class': 'text-body-2'}, 'text': '状态'},
                                {'component': 'th', 'props': {'class': 'text-body-2'}, 'text': '官方回复'},
                            ]}]},
                            {'component': 'tbody', 'content': rows}
                        ]}
                    ]}
                ]
            })

        if history:
            history = sorted(history, key=lambda x: x.get('date', ''), reverse=True)
            rows = []
            for h in history[:50]:
                status = h.get('status', '')
                color = 'success' if status in ('无更新', '有更新') else 'error'
                rows.append({
                    'component': 'tr',
                    'content': [
                        {'component': 'td', 'props': {'class': 'text-caption'}, 'text': h.get('date', '')},
                        {'component': 'td', 'content': [{'component': 'VChip', 'props': {'size': 'small', 'variant': 'outlined', 'color': color}, 'text': status}]},
                        {'component': 'td', 'props': {'class': 'text-caption'}, 'text': f"公测/需求共 {h.get('total', 0)} 条"},
                        {'component': 'td', 'props': {'class': 'text-caption'}, 'text': h.get('message', '')},
                    ]
                })
            cards.append({
                'component': 'VCard',
                'props': {'variant': 'elevated', 'elevation': 2, 'rounded': 'lg', 'class': 'mb-4'},
                'content': [
                    {'component': 'VCardTitle', 'props': {'class': 'text-h6 font-weight-bold'}, 'text': f'📊 监控历史 (近{len(rows)}条)'},
                    {'component': 'VCardText', 'content': [
                        {'component': 'VTable', 'props': {'hover': True, 'density': 'comfortable'}, 'content': [
                            {'component': 'thead', 'content': [{'component': 'tr', 'content': [
                                {'component': 'th', 'props': {'class': 'text-body-2'}, 'text': '时间'},
                                {'component': 'th', 'props': {'class': 'text-body-2'}, 'text': '状态'},
                                {'component': 'th', 'props': {'class': 'text-body-2'}, 'text': '条数'},
                                {'component': 'th', 'props': {'class': 'text-body-2'}, 'text': '消息'},
                            ]}]},
                            {'component': 'tbody', 'content': rows}
                        ]}
                    ]}
                ]
            })
        return cards

    def stop_service(self):
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None
        return True

    def get_command(self) -> List[Dict[str, Any]]:
        return [{
            'cmd': '/ugnas_feedback',
            'event': self.sync,
            'desc': '绿联云反馈监控',
            'category': ''
        }]

    def get_api(self) -> List[Dict[str, Any]]:
        return []
