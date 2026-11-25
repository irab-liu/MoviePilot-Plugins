<script setup>
/**
 * Agent 定时任务管理主页面。
 *
 * 使用宿主全局注册的 Vuetify 组件渲染；按钮不因 running/停用状态被禁用，
 * 不可执行时由后端返回明确提示，避免出现按钮全灰无法点击的问题。
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
const filterEnabled = ref(null)
const busyIds = ref(new Set())
const snackbar = reactive({ show: false, text: '', color: 'info' })

const filterOptions = [
  { title: '全部', value: null },
  { title: '已启用', value: true },
  { title: '已停用', value: false },
]

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

/** 显示一条顶部提示。 */
function showSnackbar(text, color = 'info') {
  snackbar.text = text
  snackbar.color = color
  snackbar.show = true
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
    if (filterEnabled.value !== null) params.enabled = filterEnabled.value ? 'true' : 'false'
    const result = await pluginRequest(props.api, props.pluginId, '/tasks', {
      method: 'GET',
      params,
    })
    tasks.value = result?.tasks || []
    total.value = result?.total || 0
    aiAgentEnable.value = result?.ai_agent_enable !== false
  } catch (error) {
    showSnackbar(errorMessage(error, '加载任务列表失败'), 'error')
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
    showSnackbar(result?.message || (value ? '任务已启用' : '任务已停用'), 'success')
  } catch (error) {
    showSnackbar(errorMessage(error, '启停任务失败'), 'error')
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
    showSnackbar(result?.message || '已提交立即执行', 'success')
    await loadTasks()
  } catch (error) {
    showSnackbar(errorMessage(error, '立即执行失败'), 'error')
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
    showSnackbar('任务名称不能为空', 'error')
    return
  }
  if (!editForm.content.trim()) {
    showSnackbar('任务指令不能为空', 'error')
    return
  }
  const body = {
    name: editForm.name.trim(),
    content: editForm.content.trim(),
    trigger_type: editForm.trigger_type,
  }
  if (editForm.trigger_type === 'cron') {
    if (!editForm.cron_expression.trim()) {
      showSnackbar('请填写五段 cron 表达式', 'error')
      return
    }
    body.cron_expression = editForm.cron_expression.trim()
  } else {
    if (!editForm.run_at.trim()) {
      showSnackbar('请填写单次触发时间', 'error')
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
    showSnackbar(result?.message || '任务已更新', 'success')
    editDialog.value = false
    await loadTasks()
  } catch (error) {
    showSnackbar(errorMessage(error, '保存任务失败'), 'error')
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
    showSnackbar(errorMessage(error, '加载运行历史失败'), 'error')
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
    showSnackbar(result?.message || '任务已删除', 'success')
    deleteDialog.value = false
    deleteTarget.value = null
    await loadTasks()
  } catch (error) {
    showSnackbar(errorMessage(error, '删除任务失败'), 'error')
  } finally {
    deleteLoading.value = false
  }
}

/** 触发来源展示文本。 */
function triggerSourceLabel(source) {
  return source === 'manual' ? '手动' : source === 'scheduled' ? '定时' : source || '未知'
}

/** 触发配置占位提示。 */
const triggerHint = computed(() =>
  editForm.trigger_type === 'cron'
    ? '标准五段 cron 表达式，例如：0 10,22 * * *'
    : '带时区 ISO 8601 时间，例如：2026-12-31 08:00:00',
)

onMounted(loadTasks)
</script>

<template>
  <div class="atm-page">
    <v-container fluid class="pa-4">
      <v-row>
        <v-col cols="12">
          <div class="d-flex align-center flex-wrap gap-2 mb-4">
            <v-icon size="x-small" class="mr-1">mdi-clock-outline</v-icon>
            <span class="text-h6 font-weight-bold">Agent 定时任务</span>
            <v-chip size="small" color="primary" variant="tonal">{{ total }}</v-chip>
            <v-spacer />
            <v-btn
              size="small"
              color="primary"
              variant="tonal"
              :loading="loading"
              @click="loadTasks"
            >
              <v-icon start>mdi-refresh</v-icon>
              刷新
            </v-btn>
          </div>
        </v-col>
      </v-row>

      <v-row>
        <v-col cols="12">
          <v-alert
            v-if="!aiAgentEnable"
            type="warning"
            variant="tonal"
            class="mb-4"
            icon="mdi-alert"
            prominent
          >
            AI Agent 未启用（AI_AGENT_ENABLE=false），自主定时任务不会被调度执行。此处仅能查看和管理任务配置。
          </v-alert>

          <v-card variant="outlined" rounded="lg">
            <v-card-text>
              <div class="d-flex align-center mb-3">
                <v-select
                  v-model="filterEnabled"
                  :items="filterOptions"
                  label="启用状态"
                  variant="outlined"
                  density="compact"
                  hide-details
                  class="atm-filter"
                  @update:model-value="loadTasks"
                />
              </div>

              <div v-if="loading && !hasTasks" class="text-center py-8">
                <v-progress-circular indeterminate color="primary" />
                <div class="text-caption text-grey mt-2">正在加载任务列表…</div>
              </div>

              <v-alert
                v-else-if="!hasTasks"
                type="info"
                variant="tonal"
                icon="mdi-information"
              >
                暂无 Agent 定时任务。新建任务仍通过对话让 Agent 使用 agent_task 工具创建。
              </v-alert>

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
                      <th class="text-right">操作</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="row in tasks" :key="row.id">
                      <td>
                        <div class="font-weight-medium">{{ row.name }}</div>
                        <div
                          v-if="row.owner_username || row.owner_user_id"
                          class="text-caption text-grey"
                        >
                          归属：{{ row.owner_username || row.owner_user_id }}
                        </div>
                        <div class="text-caption text-grey">
                          ID {{ row.id }}
                          <v-chip size="x-small" variant="tonal" class="ml-1">
                            {{ triggerTypeLabel(row.trigger_type) }}
                          </v-chip>
                        </div>
                      </td>
                      <td class="text-caption atm-mono">{{ triggerText(row) }}</td>
                      <td>
                        <v-chip size="small" :color="statusMeta(row.last_status).chip">
                          {{ statusMeta(row.last_status).label }}
                        </v-chip>
                      </td>
                      <td class="text-caption">{{ row.last_run_at || '—' }}</td>
                      <td class="text-caption">{{ row.run_count }}</td>
                      <td class="text-caption atm-mono">{{ row.next_run_at || '—' }}</td>
                      <td>
                        <v-switch
                          :model-value="Boolean(row.enabled)"
                          :disabled="busyIds.has(row.id)"
                          density="compact"
                          hide-details
                          color="primary"
                          @update:model-value="(value) => onToggle(row, value)"
                        />
                      </td>
                      <td class="text-right">
                        <div class="d-inline-flex flex-wrap justify-end gap-1">
                          <v-btn
                            size="x-small"
                            variant="tonal"
                            color="primary"
                            :disabled="busyIds.has(row.id)"
                            @click="onRun(row)"
                          >
                            执行
                          </v-btn>
                          <v-btn
                            size="x-small"
                            variant="tonal"
                            :disabled="busyIds.has(row.id)"
                            @click="openEdit(row)"
                          >
                            编辑
                          </v-btn>
                          <v-btn
                            size="x-small"
                            variant="tonal"
                            @click="openHistory(row)"
                          >
                            历史
                          </v-btn>
                          <v-btn
                            size="x-small"
                            variant="tonal"
                            color="error"
                            :disabled="busyIds.has(row.id)"
                            @click="openDelete(row)"
                          >
                            删除
                          </v-btn>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-container>

    <!-- 编辑弹窗 -->
    <v-dialog v-model="editDialog" max-width="720" persistent>
      <v-card rounded="lg">
        <v-card-title class="d-flex align-center">
          编辑任务 #{{ editForm.id }}
          <v-spacer />
          <v-btn size="small" variant="text" icon="mdi-close" @click="editDialog = false" />
        </v-card-title>
        <v-card-text>
          <v-text-field
            v-model="editForm.name"
            label="任务名称"
            variant="outlined"
            density="compact"
            maxlength="100"
            class="mb-3"
          />
          <div class="d-flex gap-2 mb-3">
            <v-select
              v-model="editForm.trigger_type"
              :items="[
                { title: '周期（cron）', value: 'cron' },
                { title: '单次（date）', value: 'date' },
              ]"
              label="触发类型"
              variant="outlined"
              density="compact"
              hide-details
              class="atm-trigger-select"
            />
            <v-text-field
              v-if="editForm.trigger_type === 'cron'"
              v-model="editForm.cron_expression"
              label="cron 表达式"
              variant="outlined"
              density="compact"
              hide-details
            />
            <v-text-field
              v-else
              v-model="editForm.run_at"
              label="单次触发时间"
              variant="outlined"
              density="compact"
              hide-details
            />
          </div>
          <div class="text-caption text-grey mb-3">{{ triggerHint }}</div>
          <v-textarea
            v-model="editForm.content"
            label="任务指令（交给 Agent 执行的完整内容）"
            variant="outlined"
            density="compact"
            rows="6"
            maxlength="10000"
            hide-details
          />
        </v-card-text>
        <v-card-actions class="px-4 pb-4">
          <v-spacer />
          <v-btn variant="text" @click="editDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="editSaving" @click="saveEdit">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 运行历史弹窗 -->
    <v-dialog v-model="historyDialog" max-width="860">
      <v-card rounded="lg">
        <v-card-title class="d-flex align-center">
          运行历史：{{ historyTask?.name || '' }}
          <v-spacer />
          <v-btn size="small" variant="text" icon="mdi-close" @click="historyDialog = false" />
        </v-card-title>
        <v-card-text>
          <div v-if="historyLoading" class="text-center py-8">
            <v-progress-circular indeterminate color="primary" />
          </div>
          <v-alert
            v-else-if="!historyRuns.length"
            type="info"
            variant="tonal"
          >
            暂无运行历史。
          </v-alert>
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
                  <td class="text-caption atm-mono">{{ run.run_id }}</td>
                  <td class="text-caption">{{ triggerSourceLabel(run.trigger_source) }}</td>
                  <td>
                    <v-chip size="small" :color="statusMeta(run.status).chip">
                      {{ statusMeta(run.status).label }}
                    </v-chip>
                  </td>
                  <td class="text-caption">{{ run.started_at || '—' }}</td>
                  <td class="text-caption">{{ run.finished_at || '—' }}</td>
                  <td class="text-caption atm-result-cell">
                    <template v-if="run.result">
                      <details>
                        <summary class="atm-result-toggle">查看结果</summary>
                        <pre class="atm-result">{{ run.result }}</pre>
                      </details>
                    </template>
                    <template v-else>—</template>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </v-card-text>
        <v-card-actions class="px-4 pb-4">
          <v-spacer />
          <v-btn variant="text" @click="historyDialog = false">关闭</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 删除确认弹窗 -->
    <v-dialog v-model="deleteDialog" max-width="480" persistent>
      <v-card rounded="lg">
        <v-card-title>删除任务</v-card-title>
        <v-card-text>
          确定要删除任务「{{ deleteTarget?.name || '' }}」（#{{ deleteTarget?.id || '' }}）吗？
          删除会一并清除其全部运行历史，且不可恢复。
        </v-card-text>
        <v-card-actions class="px-4 pb-4">
          <v-spacer />
          <v-btn variant="text" @click="deleteDialog = false">取消</v-btn>
          <v-btn color="error" :loading="deleteLoading" @click="confirmDelete">删除</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snackbar.show" :color="snackbar.color" timeout="3000">
      {{ snackbar.text }}
    </v-snackbar>
  </div>
</template>

<style scoped>
.atm-filter {
  max-width: 220px;
}
.atm-trigger-select {
  max-width: 220px;
}
.atm-table-wrap {
  overflow-x: auto;
}
.atm-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 960px;
}
.atm-table th,
.atm-table td {
  padding: 8px 10px;
  border-bottom: 1px solid rgba(var(--v-border-color), 0.12);
  vertical-align: middle;
  text-align: left;
}
.atm-table th {
  font-size: 12px;
  color: rgba(var(--v-theme-on-surface), 0.6);
  white-space: nowrap;
}
.atm-mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  white-space: nowrap;
}
.atm-result-toggle {
  cursor: pointer;
  color: rgb(var(--v-theme-primary));
  user-select: none;
}
.atm-result {
  max-width: 360px;
  max-height: 200px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 4px 0 0;
  font-size: 11px;
  color: rgba(var(--v-theme-on-surface), 0.75);
}
</style>
