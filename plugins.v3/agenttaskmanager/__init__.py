"""
AgentTaskManager - MoviePilot V3 插件。

为宿主中没有界面、只能靠 Agent 对话操作的「Agent 自主定时任务（AgentTask）」
提供一个侧栏管理页：任务列表、启停、立即执行、编辑、删除与运行历史。

设计约束：
- 只做管理界面，不重新实现调度逻辑，全部复用宿主 ``app.scheduler`` 的
  ``agent-task-{id}`` 内存 job。
- 所有写操作在落库后必须调用 ``update_agent_task_job`` / ``remove_agent_task_job``
  同步内存调度，否则界面显示与实际执行不一致。
- 多用户隔离：非管理员只能看到和操作自己的任务，管理员可看全部并在界面上标明归属。
"""

from typing import Any, Dict, List, Optional, Tuple

from fastapi import Body, Depends, HTTPException, Query, status

from app.api.dependencies.auth import get_current_user
from app.application.agenttask import agent_task_run_to_dict, agent_task_to_dict
from app.application.scheduling import (
    get_agent_task_next_run,
    remove_agent_task_job,
    start_agent_task,
    update_agent_task_job,
)
from app.db.oper.agenttask import AgentTaskOper
from app.plugins import _PluginBase
from app.runtime.scheduling import TimerUtils
from app.runtime.settings import get_runtime_setting
from app.sdk.logging import logger


class AgentTaskManager(_PluginBase):
    """
    Agent 自主定时任务管理插件主类。
    """

    # 插件展示名称
    plugin_name = "Agent 定时任务管理"
    # 插件描述
    plugin_desc = "可视化查看、启停、编辑、删除 MoviePilot 的 Agent 自主定时任务，并查看运行历史。"
    # 插件图标
    plugin_icon = "agenttaskmanager.png"
    # 插件版本
    plugin_version = "1.0.1"
    # 插件作者
    plugin_author = "irab"
    # 作者主页
    author_url = "https://github.com/irab-liu"
    # 插件配置项 ID 前缀
    plugin_config_prefix = "agenttaskmanager_"
    # 加载顺序
    plugin_order = 20
    # 可使用的用户级别：2 表示需要管理员权限
    auth_level = 2

    # 插件是否启用
    _enabled: bool = True

    def init_plugin(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        生效插件配置并建立本次运行所需状态。

        :param config: 插件配置字典，缺省时按启用处理
        """
        config = config or {}
        self._enabled = self._to_bool(config.get("enabled", True))

    def get_state(self) -> bool:
        """
        返回插件当前是否启用。
        """
        return bool(self._enabled)

    @staticmethod
    def get_render_mode() -> Tuple[str, Optional[str]]:
        """
        声明插件使用 Vue 联邦组件渲染。

        :return: 渲染模式与前端构建产物目录
        """
        return "vue", "dist/assets"

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        """
        当前插件不注册远程命令。
        """
        return []

    def get_sidebar_nav(self) -> List[Dict[str, Any]]:
        """
        声明插件在主界面左侧导航栏中的全页入口。
        """
        if not self.get_state():
            return []
        return [{
            "nav_key": "main",
            "title": "Agent 定时任务",
            "icon": "mdi-clock-outline",
            "section": "system",
            "permission": "manage",
            "order": 20,
        }]

    def get_api(self) -> List[Dict[str, Any]]:
        """
        注册插件后端 API。
        """
        return [
            {
                "path": "/tasks",
                "endpoint": self.list_tasks,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "查询 Agent 定时任务列表",
                "description": "按当前用户过滤；管理员可查看全部并附带归属信息",
            },
            {
                "path": "/tasks/{task_id}",
                "endpoint": self.get_task,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "查询 Agent 定时任务详情",
                "description": "返回任务字段与最近 10 条运行历史",
            },
            {
                "path": "/tasks/{task_id}/runs",
                "endpoint": self.list_task_runs,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "查询 Agent 定时任务运行历史",
                "description": "按任务归属过滤，支持 limit 参数",
            },
            {
                "path": "/tasks/{task_id}",
                "endpoint": self.update_task,
                "methods": ["PUT"],
                "auth": "bear",
                "summary": "编辑 Agent 定时任务",
                "description": "仅允许修改 name、content、trigger_type、cron_expression、run_at",
            },
            {
                "path": "/tasks/{task_id}/update",
                "endpoint": self.update_task,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "编辑 Agent 定时任务（POST 别名）",
                "description": "兼容仅提供 POST 的前端请求实例",
            },
            {
                "path": "/tasks/{task_id}/toggle",
                "endpoint": self.toggle_task,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "启停 Agent 定时任务",
                "description": "写入数据库后同步运行时调度",
            },
            {
                "path": "/tasks/{task_id}/run",
                "endpoint": self.run_task,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "立即执行 Agent 定时任务",
                "description": "前置校验启用状态与运行中状态",
            },
            {
                "path": "/tasks/{task_id}",
                "endpoint": self.delete_task,
                "methods": ["DELETE"],
                "auth": "bear",
                "summary": "删除 Agent 定时任务",
                "description": "运行中的任务拒绝删除，删除后移除运行时调度",
            },
            {
                "path": "/tasks/{task_id}/delete",
                "endpoint": self.delete_task,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "删除 Agent 定时任务（POST 别名）",
                "description": "兼容仅提供 POST 的前端请求实例",
            },
            {
                "path": "/config",
                "endpoint": self.get_plugin_config,
                "methods": ["GET"],
                "auth": "bear",
                "summary": "获取插件配置",
            },
            {
                "path": "/config",
                "endpoint": self.save_plugin_config,
                "methods": ["POST"],
                "auth": "bear",
                "summary": "保存插件配置",
            },
        ]

    def get_form(self) -> Tuple[Optional[List[Dict[str, Any]]], Dict[str, Any]]:
        """
        Vue 模式返回空页面配置与当前配置模型。

        :return: 页面配置（Vue 模式为 None）与默认配置数据
        """
        return None, {"enabled": self._enabled}

    def get_page(self) -> List[Dict[str, Any]]:
        """
        Vue 模式不需要返回 Vuetify JSON 页面。
        """
        return []

    def stop_service(self) -> None:
        """
        停止插件：仅标记停用，调度复用宿主，无需清理自有服务。
        """
        self._enabled = False

    # ------------------------------------------------------------------
    # 配置接口
    # ------------------------------------------------------------------

    def get_plugin_config(self) -> Dict[str, Any]:
        """
        返回当前插件配置。
        """
        return {"enabled": self._enabled}

    def save_plugin_config(
        self,
        payload: Dict[str, Any] = Body(default=None),
    ) -> Dict[str, Any]:
        """
        保存插件配置并立即生效。

        :param payload: 配置请求体，允许 enabled 字段
        """
        payload = payload or {}
        config_to_save = {
            "enabled": self._to_bool(payload.get("enabled", self._enabled)),
        }
        self.init_plugin(config_to_save)
        self.update_config(config_to_save)
        return {
            "success": True,
            "message": "配置已保存",
            "data": self.get_plugin_config(),
        }

    # ------------------------------------------------------------------
    # 任务接口
    # ------------------------------------------------------------------

    def list_tasks(
        self,
        enabled: Optional[bool] = Query(
            default=None,
            description="按启用状态筛选，缺省返回全部",
        ),
        current_user: Any = Depends(get_current_user),
    ) -> Dict[str, Any]:
        """
        查询当前用户（或管理员视角下全部）的 Agent 定时任务。

        :param enabled: 启用状态筛选
        :param current_user: 当前登录用户
        """
        tasks = AgentTaskOper().list(
            user_id=self._owner_filter(current_user),
            enabled=enabled,
        )
        return {
            "success": True,
            "total": len(tasks),
            "ai_agent_enable": self._ai_agent_enabled(),
            "tasks": [self._task_to_dict(task) for task in tasks],
        }

    def get_task(
        self,
        task_id: int,
        current_user: Any = Depends(get_current_user),
    ) -> Dict[str, Any]:
        """
        查询单个 Agent 定时任务及其最近运行历史。

        :param task_id: 任务主键
        :param current_user: 当前登录用户
        """
        task = self._get_task_for(task_id, current_user)
        if task is None:
            self._raise_not_found(task_id)
        data = self._task_to_dict(task)
        runs = AgentTaskOper().list_runs(
            task_id=task_id,
            user_id=self._owner_filter(current_user),
            limit=10,
        )
        data["recent_runs"] = [agent_task_run_to_dict(run) for run in runs]
        return {
            "success": True,
            "ai_agent_enable": self._ai_agent_enabled(),
            "task": data,
        }

    def list_task_runs(
        self,
        task_id: int,
        limit: int = Query(default=20, ge=1, le=100, description="最多返回条数"),
        current_user: Any = Depends(get_current_user),
    ) -> Dict[str, Any]:
        """
        查询指定任务的有界运行历史。

        :param task_id: 任务主键
        :param limit: 最多返回条数，默认 20，上限 100
        :param current_user: 当前登录用户
        """
        task = self._get_task_for(task_id, current_user)
        if task is None:
            self._raise_not_found(task_id)
        runs = AgentTaskOper().list_runs(
            task_id=task_id,
            user_id=self._owner_filter(current_user),
            limit=limit,
        )
        return {
            "success": True,
            "total": len(runs),
            "runs": [agent_task_run_to_dict(run) for run in runs],
        }

    def update_task(
        self,
        task_id: int,
        payload: Dict[str, Any] = Body(default=None),
        current_user: Any = Depends(get_current_user),
    ) -> Dict[str, Any]:
        """
        编辑任务字段并同步运行时调度。

        :param task_id: 任务主键
        :param payload: 仅允许 name/content/trigger_type/cron_expression/run_at
        :param current_user: 当前登录用户
        """
        task = self._get_task_for(task_id, current_user)
        if task is None:
            self._raise_not_found(task_id)
        if task.last_status == "running":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Agent 定时任务 {task_id} 正在执行，请稍后再修改",
            )
        update_payload = self._build_update_payload(task, payload or {})
        updated = AgentTaskOper().update(
            task_id=task_id,
            payload=update_payload,
            user_id=self._owner_filter(current_user),
        )
        if not updated:
            current = self._get_task_for(task_id, current_user)
            if current is not None and current.last_status == "running":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Agent 定时任务 {task_id} 正在执行，请稍后再修改",
                )
            self._raise_not_found(task_id)
        self._sync_scheduler_job(task_id)
        fresh = self._get_task_for(task_id, current_user)
        return {
            "success": True,
            "message": "任务已更新",
            "task": self._task_to_dict(fresh) if fresh is not None else {},
        }

    def toggle_task(
        self,
        task_id: int,
        payload: Dict[str, Any] = Body(default=None),
        current_user: Any = Depends(get_current_user),
    ) -> Dict[str, Any]:
        """
        启停任务：先写数据库，再同步运行时调度。

        :param task_id: 任务主键
        :param payload: 请求体，要求 enabled 为布尔值
        :param current_user: 当前登录用户
        """
        payload = payload or {}
        if "enabled" not in payload or not isinstance(payload["enabled"], bool):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="enabled 必须是布尔值",
            )
        value = payload["enabled"]
        task = self._get_task_for(task_id, current_user)
        if task is None:
            self._raise_not_found(task_id)
        if task.last_status == "running":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Agent 定时任务 {task_id} 正在执行，请稍后再修改",
            )
        updated = AgentTaskOper().update(
            task_id=task_id,
            payload={"enabled": value},
            user_id=self._owner_filter(current_user),
        )
        if not updated:
            current = self._get_task_for(task_id, current_user)
            if current is not None and current.last_status == "running":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Agent 定时任务 {task_id} 正在执行，请稍后再修改",
                )
            self._raise_not_found(task_id)
        # 启停都必须同步内存调度：启用时注册/替换 job，停用时移除 job。
        self._sync_scheduler_job(task_id)
        fresh = self._get_task_for(task_id, current_user)
        return {
            "success": True,
            "message": "任务已启用" if value else "任务已停用",
            "task": self._task_to_dict(fresh) if fresh is not None else {},
        }

    def run_task(
        self,
        task_id: int,
        current_user: Any = Depends(get_current_user),
    ) -> Dict[str, Any]:
        """
        立即提交一次已启用且未运行的任务。

        :param task_id: 任务主键
        :param current_user: 当前登录用户
        """
        task = self._get_task_for(task_id, current_user)
        if task is None:
            self._raise_not_found(task_id)
        if not task.enabled:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Agent 定时任务 {task_id} 已暂停，请先恢复后再执行",
            )
        if task.last_status == "running":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Agent 定时任务 {task_id} 正在执行，请勿重复触发",
            )
        if not self._start_task_now(task_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Agent 定时任务 {task_id} 尚未注册到运行时调度器，无法立即执行",
            )
        return {
            "success": True,
            "message": f"Agent 定时任务 {task_id} 已提交立即执行：{task.name}",
        }

    def delete_task(
        self,
        task_id: int,
        current_user: Any = Depends(get_current_user),
    ) -> Dict[str, Any]:
        """
        删除非运行中的任务及其运行历史，并移除运行时调度。

        :param task_id: 任务主键
        :param current_user: 当前登录用户
        """
        task = self._get_task_for(task_id, current_user)
        if task is None:
            self._raise_not_found(task_id)
        if task.last_status == "running":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Agent 定时任务 {task_id} 正在执行，无法删除",
            )
        deleted = AgentTaskOper().delete(
            task_id=task_id,
            user_id=self._owner_filter(current_user),
        )
        if not deleted:
            current = self._get_task_for(task_id, current_user)
            if current is not None and current.last_status == "running":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Agent 定时任务 {task_id} 正在执行，无法删除",
                )
            self._raise_not_found(task_id)
        self._remove_scheduler_job(task_id)
        return {
            "success": True,
            "message": f"Agent 定时任务 {task_id} 已删除",
        }

    # ------------------------------------------------------------------
    # 内部工具方法
    # ------------------------------------------------------------------

    @staticmethod
    def _to_bool(value: Any) -> bool:
        """
        把常见配置值规整为布尔值。
        """
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    @staticmethod
    def _is_admin(current_user: Any) -> bool:
        """
        判断当前用户是否具备管理员视角。

        :param current_user: 宿主解析出的当前用户
        """
        is_superuser = bool(getattr(current_user, "is_superuser", False))
        permissions = getattr(current_user, "permissions", None) or {}
        if isinstance(permissions, str):
            return is_superuser
        return is_superuser or bool(permissions.get("manage"))

    @staticmethod
    def _owner_user_id(current_user: Any) -> str:
        """
        返回当前用户的字符串 ID，用于按 AgentTask.user_id 过滤。
        """
        return str(getattr(current_user, "id", "") or "")

    def _owner_filter(self, current_user: Any) -> Optional[str]:
        """
        计算任务归属过滤条件：管理员返回 None 表示不过滤。
        """
        if self._is_admin(current_user):
            return None
        return self._owner_user_id(current_user)

    def _tz(self) -> str:
        """
        返回宿主配置的时区名称。
        """
        return str(get_runtime_setting("TZ", "Asia/Shanghai") or "Asia/Shanghai")

    def _ai_agent_enabled(self) -> bool:
        """
        返回宿主 AI Agent 是否启用，供前端给出明确提示。
        """
        return self._to_bool(get_runtime_setting("AI_AGENT_ENABLE", True))

    def _get_task_for(self, task_id: int, current_user: Any) -> Any:
        """
        按当前用户归属读取单个任务；管理员不受归属过滤。
        """
        return AgentTaskOper().get(
            task_id=task_id,
            user_id=self._owner_filter(current_user),
        )

    @staticmethod
    def _raise_not_found(task_id: int) -> None:
        """
        抛出任务不存在或不属于当前用户的 404 异常。
        """
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent 定时任务 {task_id} 不存在或不属于当前用户",
        )

    def _task_to_dict(self, task: Any) -> Dict[str, Any]:
        """
        复用宿主转换函数生成任务返回结构，并补充归属信息。

        :param task: AgentTask ORM 对象
        """
        data = agent_task_to_dict(
            task,
            next_run_at=self._scheduler_next_run(task.id),
            timezone=self._tz(),
        )
        data["owner_user_id"] = task.user_id
        data["owner_username"] = task.username
        return data

    def _scheduler_next_run(self, task_id: int) -> Optional[str]:
        """
        安全读取运行时调度器的下一次触发时间。
        """
        try:
            return get_agent_task_next_run(task_id)
        except Exception as exc:  # noqa: BLE001 - 调度器未就绪时降级为 None
            logger.error("读取 Agent 定时任务 %s 下次触发时间失败：%s", task_id, exc)
            return None

    def _sync_scheduler_job(self, task_id: int) -> Optional[str]:
        """
        落库后同步运行时调度，返回下一次触发时间。
        """
        try:
            return update_agent_task_job(task_id)
        except Exception as exc:  # noqa: BLE001 - 同步失败仅记录，不回滚已落库的配置
            logger.error("同步 Agent 定时任务 %s 运行时调度失败：%s", task_id, exc)
            return None

    def _remove_scheduler_job(self, task_id: int) -> None:
        """
        移除任务的运行时调度注册。
        """
        try:
            remove_agent_task_job(task_id)
        except Exception as exc:  # noqa: BLE001 - 删除已落库，移除失败仅记录
            logger.error("移除 Agent 定时任务 %s 运行时调度失败：%s", task_id, exc)

    def _start_task_now(self, task_id: int) -> bool:
        """
        调用宿主调度器立即执行任务。
        """
        try:
            return bool(start_agent_task(task_id))
        except Exception as exc:  # noqa: BLE001 - 调度器未就绪时返回不可执行
            logger.error("立即执行 Agent 定时任务 %s 失败：%s", task_id, exc)
            return False

    def _build_update_payload(
        self,
        task: Any,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        校验编辑请求并构造允许落库的更新字段。

        :param task: 当前任务 ORM 对象
        :param payload: 前端提交的编辑字段
        """
        allowed = {"name", "content", "trigger_type", "cron_expression", "run_at"}
        unknown = set(payload or {}) - allowed
        if unknown:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"不允许修改的字段：{'、'.join(sorted(unknown))}",
            )
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="至少提供一个要更新的字段",
            )

        update_payload: Dict[str, Any] = {}
        if "name" in payload:
            name = str(payload.get("name") or "").strip()
            if not name or len(name) > 100:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="name 不能为空且长度不超过 100",
                )
            update_payload["name"] = name
        if "content" in payload:
            content = str(payload.get("content") or "").strip()
            if not content or len(content) > 10000:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="content 不能为空且长度不超过 10000",
                )
            update_payload["content"] = content

        if "trigger_type" in payload and payload["trigger_type"] is not None:
            trigger_type = str(payload["trigger_type"]).strip().lower()
            if trigger_type not in {"date", "cron"}:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="trigger_type 仅支持 date 或 cron",
                )
            try:
                if trigger_type == "cron":
                    cron_expression = str(payload.get("cron_expression") or "").strip()
                    if not cron_expression:
                        raise ValueError("cron 任务必须提供 cron_expression")
                    normalized_type, normalized_trigger = TimerUtils.normalize_schedule_trigger(
                        trigger_type="cron",
                        trigger_value=cron_expression,
                        timezone_name=self._tz(),
                    )
                    update_payload.update({
                        "trigger_type": normalized_type,
                        "cron_expression": normalized_trigger,
                        "run_at": None,
                        "last_status": "waiting",
                        "last_result": None,
                    })
                else:
                    run_at = str(payload.get("run_at") or "").strip()
                    if not run_at:
                        raise ValueError("date 任务必须提供 run_at")
                    # 与 AgentTaskTool 的 update 语义保持一致：启用中的单次任务改期
                    # 必须安排在未来；已停用的一次性任务允许保留历史时间用于改名等场景。
                    require_future = bool(task.enabled or task.last_status == "interrupted")
                    normalized_type, normalized_trigger = TimerUtils.normalize_schedule_trigger(
                        trigger_type="date",
                        trigger_value=run_at,
                        timezone_name=self._tz(),
                        require_future=require_future,
                    )
                    update_payload.update({
                        "trigger_type": normalized_type,
                        "run_at": normalized_trigger,
                        "cron_expression": None,
                        "last_status": "waiting",
                        "last_result": None,
                    })
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=str(exc),
                )
        elif "cron_expression" in payload or "run_at" in payload:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="修改触发配置时必须提供 trigger_type",
            )
        return update_payload
