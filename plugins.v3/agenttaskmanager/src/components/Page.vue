<script setup>
/**
 * Agent 定时任务管理主页面。
 *
 * 纯 HTML/CSS 实现，不依赖宿主 Vuetify 组件，保证在远程联邦组件上下文中
 * 按钮、开关、弹窗与提示都可用。交互错误由后端返回明确文案。
 */
import { computed, onMounted, reactive, ref } from 'vue'
import {
  errorMessage,
  pluginRequest,
  statusMeta,
  triggerText,
  triggerTypeLabel,
} from '../utils/api'

const props = defineProps({
  api: { type: Object, default: () => ({}) },
  pluginId: { type: String, default: '' },
  navKey: { type: String, default: 'main' },
})

const loading = ref(false)
const tasks = ref([])
const total = ref(0)
const aiAgentEnable = ref(true)
const filterEnabled = ref('')
const busyIds = ref(new Set())
const snackbar = reactive({ show: false, text: '', type: 'info' })

const editDialog = ref(false)
const editSaving = ref(false)
const editForm = reactive({
  id: null,
  name: '',
  content: '',
  trigger_type: 'cron',
  cron_expression: '',
  run_at: '',
})

const historyDialog = ref(false)
const historyLoading = ref(false)
const historyTask = ref(null)
const historyRuns = ref([])

const deleteDialog = ref(false)
const deleteTarget = ref(null)
const deleteLoading = ref(false)

const hasTasks = computed(() => tasks.value.length > 0)

/** 触发配置占位提示。 */
const triggerHint = computed(() =>
  editForm.trigger_type === 'cron'
    ? '标准五段 cron 表达式，例如：0 10,22 * * *'
    : '带时区 ISO 8601 时间，例如：2026-12-31 08:00:00',
)

let toastTimer = null

/** 显示一条自动消失的提示。 */
function showToast(text, type = 'info') {
  if (toastTimer) clearTimeout(toastTimer)
  snackbar.text = text
  snackbar.type = type
  snackbar.show = true
  toastTimer = setTimeout(() => {
    snackbar.show = false
    toastTimer = null
  }, 4000)
}

/** 标记某行正在操作。 */
function setBusy(id, busy) {
  const next = new Set(busyIds.value)
  if (busy) next.add(id)
  else next.delete(id)
  busyIds.value = next
}

/** 拉取任务列表。 */
async function loadTasks() {
  loading.value = true
  try {
    const params = {}
    if (filterEnabled.value === 'true' || filterEnabled.value === 'false') {
      params.enabled = filterEnabled.value
    }
    const result = await pluginRequest(props.api, props.pluginId, '/tasks', {
      method: 'GET',
      params,
    })
    tasks.value = result?.tasks || []
    total.value = result?.total || 0
    aiAgentEnable.value = result?.ai_agent_enable !== false
  } catch (error) {
    showToast(errorMessage(error, '加载任务列表失败'), 'error')
  } finally {
    loading.value = false
  }
}

/** 切换启停状态。 */
async function onToggle(row, value) {
  setBusy(row.id, true)
  try {
    const result = await pluginRequest(
      props.api,
      props.pluginId,
      `/tasks/${row.id}/toggle`,
      { method: 'POST', body: { enabled: value } },
    )
    if (result?.task) {
      const index = tasks.value.findIndex((item) => item.id === row.id)
      if (index >= 0) tasks.value[index] = result.task
    } else {
      row.enabled = value
    }
    showToast(result?.message || (value ? '任务已启用' : '任务已停用'), 'success')
  } catch (error) {
    showToast(errorMessage(error, '启停任务失败'), 'error')
    await loadTasks()
  } finally {
    setBusy(row.id, false)
  }
}

/** 立即执行任务。 */
async function onRun(row) {
  setBusy(row.id, true)
  try {
    const result = await pluginRequest(
      props.api,
      props.pluginId,
      `/tasks/${row.id}/run`,
      { method: 'POST' },
    )
    showToast(result?.message || '已提交立即执行', 'success')
    await loadTasks()
  } catch (error) {
    showToast(errorMessage(error, '立即执行失败'), 'error')
  } finally {
    setBusy(row.id, false)
  }
}

/** 打开编辑弹窗并填充表单。 */
function openEdit(row) {
  editForm.id = row.id
  editForm.name = row.name || ''
  editForm.content = row.content || ''
  editForm.trigger_type = row.trigger_type === 'date' ? 'date' : 'cron'
  editForm.cron_expression = row.cron_expression || ''
  editForm.run_at = row.run_at || ''
  editDialog.value = true
}

/** 保存编辑。 */
async function saveEdit() {
  if (!editForm.name.trim()) {
    showToast('任务名称不能为空', 'error')
    return
  }
  if (!editForm.content.trim()) {
    showToast('任务指令不能为空', 'error')
    return
  }
  const body = {
    name: editForm.name.trim(),
    content: editForm.content.trim(),
    trigger_type: editForm.trigger_type,
  }
  if (editForm.trigger_type === 'cron') {
    if (!editForm.cron_expression.trim()) {
      showToast('请填写五段 cron 表达式', 'error')
      return
    }
    body.cron_expression = editForm.cron_expression.trim()
  } else {
    if (!editForm.run_at.trim()) {
      showToast('请填写单次触发时间', 'error')
      return
    }
    body.run_at = editForm.run_at.trim()
  }

  editSaving.value = true
  try {
    const result = await pluginRequest(
      props.api,
      props.pluginId,
      `/tasks/${editForm.id}/update`,
      { method: 'POST', body },
    )
    showToast(result?.message || '任务已更新', 'success')
    editDialog.value = false
    await loadTasks()
  } catch (error) {
    showToast(errorMessage(error, '保存任务失败'), 'error')
  } finally {
    editSaving.value = false
  }
}

/** 打开运行历史弹窗。 */
async function openHistory(row) {
  historyTask.value = row
  historyDialog.value = true
  historyLoading.value = true
  historyRuns.value = []
  try {
    const result = await pluginRequest(
      props.api,
      props.pluginId,
      `/tasks/${row.id}/runs`,
      { method: 'GET', params: { limit: 50 } },
    )
    historyRuns.value = result?.runs || []
  } catch (error) {
    showToast(errorMessage(error, '加载运行历史失败'), 'error')
  } finally {
    historyLoading.value = false
  }
}

/** 打开删除确认弹窗。 */
function openDelete(row) {
  deleteTarget.value = row
  deleteDialog.value = true
}

/** 确认删除。 */
async function confirmDelete() {
  if (!deleteTarget.value) return
  deleteLoading.value = true
  try {
    const result = await pluginRequest(
      props.api,
      props.pluginId,
      `/tasks/${deleteTarget.value.id}/delete`,
      { method: 'POST' },
    )
    showToast(result?.message || '任务已删除', 'success')
    deleteDialog.value = false
    deleteTarget.value = null
    await loadTasks()
  } catch (error) {
    showToast(errorMessage(error, '删除任务失败'), 'error')
  } finally {
    deleteLoading.value = false
  }
}

/** 触发来源展示文本。 */
function triggerSourceLabel(source) {
  return source === 'manual' ? '手动' : source === 'scheduled' ? '定时' : source || '未知'
}

onMounted(loadTasks)
</script>

<template>
  <div class="atm-page">
    <div class="atm-header">
      <div class="atm-title">
        <span class="atm-title-icon">⏰</span>
        <span>Agent 定时任务</span>
        <span class="atm-count">{{ total }}</span>
      </div>
      <button class="atm-btn" :disabled="loading" @click="loadTasks">
        {{ loading ? '刷新中…' : '刷新' }}
      </button>
    </div>

    <div v-if="!aiAgentEnable" class="atm-alert atm-alert--warn">
      AI Agent 未启用（AI_AGENT_ENABLE=false），自主定时任务不会被调度执行。此处仅能查看和管理任务配置。
    </div>

    <div class="atm-toolbar">
      <select v-model="filterEnabled" class="atm-select" @change="loadTasks">
        <option value="">全部状态</option>
        <option value="true">已启用</option>
        <option value="false">已停用</option>
      </select>
    </div>

    <div v-if="loading && !hasTasks" class="atm-empty">正在加载任务列表…</div>

    <div v-else-if="!hasTasks" class="atm-alert atm-alert--info">
      暂无 Agent 定时任务。新建任务仍通过对话让 Agent 使用 agent_task 工具创建。
    </div>

    <div v-else class="atm-table-wrap">
      <table class="atm-table">
        <thead>
          <tr>
            <th>任务</th>
            <th>触发</th>
            <th>最近状态</th>
            <th>上次运行</th>
            <th>次数</th>
            <th>下次运行</th>
            <th>启用</th>
            <th class="atm-right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in tasks" :key="row.id">
            <td>
              <div class="atm-name">{{ row.name }}</div>
              <div v-if="row.owner_username || row.owner_user_id" class="atm-sub">
                归属：{{ row.owner_username || row.owner_user_id }}
              </div>
              <div class="atm-sub">
                ID {{ row.id }} · {{ triggerTypeLabel(row.trigger_type) }}
              </div>
            </td>
            <td class="atm-mono">{{ triggerText(row) }}</td>
            <td>
              <span class="atm-badge" :class="`atm-badge--${statusMeta(row.last_status).chip}`">
                {{ statusMeta(row.last_status).label }}
              </span>
            </td>
            <td class="atm-sub">{{ row.last_run_at || '—' }}</td>
            <td class="atm-sub">{{ row.run_count }}</td>
            <td class="atm-mono">{{ row.next_run_at || '—' }}</td>
            <td>
              <button
                class="atm-btn atm-btn--sm"
                :class="row.enabled ? 'atm-btn--on' : 'atm-btn--off'"
                :disabled="busyIds.has(row.id)"
                @click="onToggle(row, !row.enabled)"
              >
                {{ busyIds.has(row.id) ? '…' : row.enabled ? '停用' : '启用' }}
              </button>
            </td>
            <td class="atm-right">
              <div class="atm-actions">
                <button
                  class="atm-btn atm-btn--sm"
                  :disabled="busyIds.has(row.id)"
                  @click="onRun(row)"
                >
                  执行
                </button>
                <button
                  class="atm-btn atm-btn--sm"
                  :disabled="busyIds.has(row.id)"
                  @click="openEdit(row)"
                >
                  编辑
                </button>
                <button class="atm-btn atm-btn--sm" @click="openHistory(row)">历史</button>
                <button
                  class="atm-btn atm-btn--sm atm-btn--danger"
                  :disabled="busyIds.has(row.id)"
                  @click="openDelete(row)"
                >
                  删除
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 编辑弹窗 -->
    <div v-if="editDialog" class="atm-modal">
      <div class="atm-modal-mask" @click="editDialog = false"></div>
      <div class="atm-modal-box">
        <div class="atm-modal-head">
          <span>编辑任务 #{{ editForm.id }}</span>
          <button class="atm-close" @click="editDialog = false">×</button>
        </div>
        <div class="atm-modal-body">
          <label class="atm-field">
            <span>任务名称</span>
            <input v-model="editForm.name" maxlength="100" />
          </label>
          <div class="atm-row">
            <label class="atm-field">
              <span>触发类型</span>
              <select v-model="editForm.trigger_type">
                <option value="cron">周期（cron）</option>
                <option value="date">单次（date）</option>
              </select>
            </label>
            <label v-if="editForm.trigger_type === 'cron'" class="atm-field">
              <span>cron 表达式</span>
              <input v-model="editForm.cron_expression" />
            </label>
            <label v-else class="atm-field">
              <span>单次触发时间</span>
              <input v-model="editForm.run_at" />
            </label>
          </div>
          <div class="atm-hint">{{ triggerHint }}</div>
          <label class="atm-field">
            <span>任务指令（交给 Agent 执行的完整内容）</span>
            <textarea v-model="editForm.content" rows="6" maxlength="10000"></textarea>
          </label>
        </div>
        <div class="atm-modal-foot">
          <button class="atm-btn" @click="editDialog = false">取消</button>
          <button class="atm-btn atm-btn--primary" :disabled="editSaving" @click="saveEdit">
            {{ editSaving ? '保存中…' : '保存' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 运行历史弹窗 -->
    <div v-if="historyDialog" class="atm-modal">
      <div class="atm-modal-mask" @click="historyDialog = false"></div>
      <div class="atm-modal-box atm-modal-box--wide">
        <div class="atm-modal-head">
          <span>运行历史：{{ historyTask?.name || '' }}</span>
          <button class="atm-close" @click="historyDialog = false">×</button>
        </div>
        <div class="atm-modal-body">
          <div v-if="historyLoading" class="atm-empty">正在加载运行历史…</div>
          <div v-else-if="!historyRuns.length" class="atm-alert atm-alert--info">暂无运行历史。</div>
          <div v-else class="atm-table-wrap">
            <table class="atm-table">
              <thead>
                <tr>
                  <th>Run ID</th>
                  <th>来源</th>
                  <th>状态</th>
                  <th>开始时间</th>
                  <th>结束时间</th>
                  <th>结果</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="run in historyRuns" :key="run.run_id">
                  <td class="atm-mono">{{ run.run_id }}</td>
                  <td class="atm-sub">{{ triggerSourceLabel(run.trigger_source) }}</td>
                  <td>
                    <span class="atm-badge" :class="`atm-badge--${statusMeta(run.status).chip}`">
                      {{ statusMeta(run.status).label }}
                    </span>
                  </td>
                  <td class="atm-sub">{{ run.started_at || '—' }}</td>
                  <td class="atm-sub">{{ run.finished_at || '—' }}</td>
                  <td class="atm-result-cell">
                    <details v-if="run.result">
                      <summary>查看结果</summary>
                      <pre class="atm-result">{{ run.result }}</pre>
                    </details>
                    <span v-else>—</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="atm-modal-foot">
          <button class="atm-btn" @click="historyDialog = false">关闭</button>
        </div>
      </div>
    </div>

    <!-- 删除确认弹窗 -->
    <div v-if="deleteDialog" class="atm-modal">
      <div class="atm-modal-mask" @click="deleteDialog = false"></div>
      <div class="atm-modal-box">
        <div class="atm-modal-head">
          <span>删除任务</span>
          <button class="atm-close" @click="deleteDialog = false">×</button>
        </div>
        <div class="atm-modal-body">
          确定要删除任务「{{ deleteTarget?.name || '' }}」（#{{ deleteTarget?.id || '' }}）吗？
          删除会一并清除其全部运行历史，且不可恢复。
        </div>
        <div class="atm-modal-foot">
          <button class="atm-btn" @click="deleteDialog = false">取消</button>
          <button class="atm-btn atm-btn--danger" :disabled="deleteLoading" @click="confirmDelete">
            {{ deleteLoading ? '删除中…' : '删除' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 全局提示 -->
    <Transition name="atm-toast-fade">
      <div v-if="snackbar.show" class="atm-toast" :class="`atm-toast--${snackbar.type}`">
        {{ snackbar.text }}
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.atm-page {
  padding: 16px;
  font-size: 14px;
  line-height: 1.5;
  color: inherit;
}
.atm-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.atm-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 700;
}
.atm-title-icon {
  font-size: 18px;
}
.atm-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  height: 20px;
  padding: 0 6px;
  border-radius: 10px;
  background: rgba(128, 128, 128, 0.18);
  font-size: 12px;
}
.atm-toolbar {
  margin-bottom: 12px;
}
.atm-select,
.atm-field input,
.atm-field select,
.atm-field textarea {
  width: 100%;
  box-sizing: border-box;
  padding: 8px 10px;
  border: 1px solid rgba(128, 128, 128, 0.4);
  border-radius: 6px;
  background: transparent;
  color: inherit;
  font-size: 14px;
}
.atm-select {
  width: auto;
  min-width: 160px;
}
.atm-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 7px 14px;
  border: 1px solid rgba(128, 128, 128, 0.45);
  border-radius: 6px;
  background: transparent;
  color: inherit;
  font-size: 13px;
  cursor: pointer;
}
.atm-btn:hover:not(:disabled) {
  border-color: currentColor;
}
.atm-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.atm-btn--sm {
  padding: 4px 10px;
  font-size: 12px;
}
.atm-btn--primary {
  border-color: #1976d2;
  background: #1976d2;
  color: #fff;
}
.atm-btn--danger {
  border-color: #d32f2f;
  color: #d32f2f;
}
.atm-btn--on {
  border-color: #2e7d32;
  color: #2e7d32;
}
.atm-btn--off {
  color: #757575;
}
.atm-actions {
  display: inline-flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
}
.atm-alert {
  padding: 10px 12px;
  border-radius: 6px;
  margin-bottom: 12px;
  border: 1px solid transparent;
}
.atm-alert--warn {
  background: rgba(237, 108, 2, 0.12);
  border-color: rgba(237, 108, 2, 0.5);
  color: #ed6c02;
}
.atm-alert--info {
  background: rgba(2, 136, 209, 0.1);
  border-color: rgba(2, 136, 209, 0.4);
}
.atm-empty {
  padding: 32px 8px;
  text-align: center;
  color: rgba(128, 128, 128, 0.9);
}
.atm-table-wrap {
  overflow-x: auto;
  border: 1px solid rgba(128, 128, 128, 0.25);
  border-radius: 8px;
}
.atm-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 920px;
}
.atm-table th,
.atm-table td {
  padding: 8px 10px;
  border-bottom: 1px solid rgba(128, 128, 128, 0.18);
  vertical-align: middle;
  text-align: left;
}
.atm-table th {
  font-size: 12px;
  color: rgba(128, 128, 128, 0.95);
  white-space: nowrap;
}
.atm-table tr:last-child td {
  border-bottom: none;
}
.atm-right {
  text-align: right !important;
}
.atm-name {
  font-weight: 600;
}
.atm-sub {
  font-size: 12px;
  color: rgba(128, 128, 128, 0.95);
}
.atm-mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  white-space: nowrap;
  font-size: 12px;
}
.atm-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
  white-space: nowrap;
}
.atm-badge--grey {
  background: rgba(128, 128, 128, 0.2);
}
.atm-badge--info {
  background: rgba(2, 136, 209, 0.15);
  color: #0288d1;
}
.atm-badge--success {
  background: rgba(46, 125, 50, 0.15);
  color: #2e7d32;
}
.atm-badge--error {
  background: rgba(211, 47, 47, 0.15);
  color: #d32f2f;
}
.atm-badge--warning {
  background: rgba(237, 108, 2, 0.15);
  color: #ed6c02;
}
.atm-modal {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}
.atm-modal-mask {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
}
.atm-modal-box {
  position: relative;
  width: 100%;
  max-width: 720px;
  max-height: 86vh;
  overflow: auto;
  background: #1e1e1e;
  border: 1px solid rgba(128, 128, 128, 0.4);
  border-radius: 10px;
  color: #e0e0e0;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.5);
}
.atm-modal-box--wide {
  max-width: 880px;
}
.atm-modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  font-weight: 700;
  border-bottom: 1px solid rgba(128, 128, 128, 0.25);
}
.atm-modal-body {
  padding: 16px;
}
.atm-modal-foot {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid rgba(128, 128, 128, 0.25);
}
.atm-close {
  border: none;
  background: transparent;
  color: inherit;
  font-size: 20px;
  cursor: pointer;
}
.atm-field {
  display: block;
  margin-bottom: 12px;
}
.atm-field span {
  display: block;
  margin-bottom: 4px;
  font-size: 12px;
  color: rgba(224, 224, 224, 0.7);
}
.atm-row {
  display: flex;
  gap: 12px;
}
.atm-row .atm-field {
  flex: 1;
}
.atm-hint {
  margin: -4px 0 12px;
  font-size: 12px;
  color: rgba(224, 224, 224, 0.55);
}
.atm-result-cell summary {
  cursor: pointer;
  color: #64b5f6;
  user-select: none;
}
.atm-result {
  max-width: 360px;
  max-height: 200px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 6px 0 0;
  font-size: 12px;
  color: rgba(224, 224, 224, 0.8);
}
.atm-toast {
  position: fixed;
  left: 50%;
  bottom: 24px;
  transform: translateX(-50%);
  z-index: 4000;
  max-width: min(480px, calc(100vw - 32px));
  padding: 10px 16px;
  border-radius: 8px;
  background: #333;
  color: #fff;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4);
  word-break: break-all;
}
.atm-toast--success {
  background: #2e7d32;
}
.atm-toast--error {
  background: #c62828;
}
.atm-toast-fade-enter-active,
.atm-toast-fade-leave-active {
  transition: opacity 0.2s ease;
}
.atm-toast-fade-enter-from,
.atm-toast-fade-leave-to {
  opacity: 0;
}
@media (max-width: 640px) {
  .atm-row {
    flex-direction: column;
    gap: 0;
  }
}
</style>
