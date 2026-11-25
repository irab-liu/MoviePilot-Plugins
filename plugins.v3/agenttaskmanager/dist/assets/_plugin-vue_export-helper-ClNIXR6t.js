/**
 * Agent 定时任务管理插件的前端请求工具。
 *
 * 联邦组件运行在宿主前端内，宿主通过 props.api 注入带鉴权的请求实例，
 * 本模块统一拼接插件 API 路径，并提供 fetch 兜底。
 */

const FALLBACK_PLUGIN_ID = 'AgentTaskManager';

/** 拼接宿主的完整 HTTP 路径（兜底 fetch 用）。 */
function pluginPath(pluginId, path = '') {
  const base = pluginId || FALLBACK_PLUGIN_ID;
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return `/api/v1/plugin/${base}${normalized}`
}

/** 拼接相对宿主 API 基地址的插件路径（props.api 用）。 */
function buildPluginUrl(pluginId, path = '') {
  const base = pluginId || FALLBACK_PLUGIN_ID;
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return `plugin/${base}${normalized}`
}

/** 把 axios 风格的错误对象规整为可展示文案。 */
function errorMessage(error, fallback = '请求失败') {
  return error?.response?.data?.detail || error?.message || fallback
}

/**
 * 调用插件后端 API。
 *
 * @param api 宿主注入的请求实例（axios 风格）
 * @param pluginId 当前插件实例 ID
 * @param path 插件内路径，如 /tasks
 * @param options { method, body, params }
 */
async function pluginRequest(api, pluginId, path = '', options = {}) {
  const apiPath = buildPluginUrl(pluginId, path);
  const method = (options.method || 'GET').toUpperCase();
  const payload = options.body ?? options.payload ?? undefined;
  const config = options.params ? { params: options.params } : undefined;

  if (method === 'POST' && api?.post) {
    return api.post(apiPath, payload || {}, config)
  }
  if (method === 'PUT' && api?.put) {
    return api.put(apiPath, payload || {}, config)
  }
  if (method === 'DELETE' && api?.delete) {
    return api.delete(apiPath, config)
  }
  if (method === 'GET' && api?.get) {
    return api.get(apiPath, config)
  }

  const query = options.params
    ? `?${new URLSearchParams(options.params).toString()}`
    : '';
  const response = await fetch(`${pluginPath(pluginId, path)}${query}`, {
    method,
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    body: method !== 'GET' && payload ? JSON.stringify(payload) : undefined,
  });
  if (!response.ok) {
    let detail = `请求失败（HTTP ${response.status}）`;
    try {
      const data = await response.json();
      if (data?.detail) detail = data.detail;
    } catch {
      // 忽略非 JSON 响应
    }
    throw new Error(detail)
  }
  return response.json()
}

/** 任务状态展示元信息。 */
function statusMeta(status) {
  const map = {
    waiting: { label: '等待中', color: 'grey', chip: 'grey' },
    running: { label: '执行中', color: 'blue', chip: 'info' },
    success: { label: '成功', color: 'green', chip: 'success' },
    failed: { label: '失败', color: 'red', chip: 'error' },
    interrupted: { label: '已中断', color: 'orange', chip: 'warning' },
  };
  return map[status] || { label: status || '未知', color: 'grey', chip: 'grey' }
}

/** 触发类型展示文本。 */
function triggerTypeLabel(type) {
  return type === 'cron' ? '周期' : type === 'date' ? '单次' : type || '未知'
}

/** 触发配置展示文本。 */
function triggerText(item) {
  if (item?.trigger_type === 'cron') return item.cron_expression || '—'
  if (item?.trigger_type === 'date') return item.run_at || '—'
  return '—'
}

const _export_sfc = (sfc, props) => {
  const target = sfc.__vccOpts || sfc;
  for (const [key, val] of props) {
    target[key] = val;
  }
  return target;
};

export { _export_sfc as _, triggerText as a, errorMessage as e, pluginRequest as p, statusMeta as s, triggerTypeLabel as t };
