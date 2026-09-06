<template>
  <VCard flat class="maoyan-config">
    <!-- 标题栏 -->
    <VCardTitle class="d-flex align-center py-3 px-4">
      <VIcon icon="mdi-trending-up" class="mr-2" color="primary" />
      <span>猫眼热度榜设置</span>
      <VSpacer />
      <VBtn icon="mdi-close" variant="text" size="small" @click="emit('close')" />
    </VCardTitle>

    <VDivider />

    <!-- 基础设置 -->
    <VCardText class="py-4">
      <div class="text-subtitle-2 mb-3 grey--text">基础设置</div>
      <div class="d-flex flex-wrap gap-3 mb-3">
        <VSwitch
          v-model="form.enabled"
          label="启用插件"
          color="primary"
          hide-details
          density="compact"
        />
        <VBtn
          variant="tonal"
          color="error"
          :loading="clearingCache"
          size="small"
          @click="clearCache"
        >
          <VIcon start size="small">mdi-delete-sweep</VIcon>
          清理缓存
        </VBtn>
      </div>
      <VSelect
        v-model="form.refresh_interval"
        :items="intervalItems"
        item-title="title"
        item-value="value"
        label="自动刷新间隔"
        variant="outlined"
        density="compact"
        hide-details
        style="max-width: 160px"
      />
    </VCardText>

    <VDivider />

    <!-- 提醒设置 -->
    <VCardText class="py-4">
      <div class="text-subtitle-2 mb-3 grey--text">提醒设置</div>
      <div class="d-flex flex-wrap gap-3 mb-3">
        <VSwitch
          v-model="form.reminder_enabled"
          label="今日上新提醒"
          color="primary"
          hide-details
          density="compact"
        />
        <VSwitch
          v-model="form.run_remind"
          label="立即运行一次提醒"
          color="secondary"
          hide-details
          density="compact"
        />
      </div>
      <div class="d-flex flex-wrap gap-3">
        <VSelect
          v-model="form.reminder_time"
          :items="hourItems"
          label="提醒时间"
          variant="outlined"
          density="compact"
          hide-details
          style="max-width: 160px"
        />
        <VSelect
          v-model="form.reminder_msgtype"
          :items="msgtypeItems"
          label="消息类型"
          variant="outlined"
          density="compact"
          hide-details
          style="max-width: 160px"
        />
      </div>
    </VCardText>

    <VDivider />

    <!-- 保存按钮 -->
    <VCardActions class="px-4 py-3">
      <VSpacer />
      <VBtn color="primary" :loading="saving" @click="save">
        <VIcon start>mdi-content-save</VIcon>
        保存
      </VBtn>
    </VCardActions>
  </VCard>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'

// ---- 组件属性 ----
const props = defineProps<{
  initialConfig?: Record<string, unknown>
  api?: { get: (url: string, params?: any) => Promise<any>; post: (url: string, data?: any) => Promise<any> }
  pluginId?: string
}>()
const emit = defineEmits<{
  save: [config: Record<string, unknown>]
  close: []
}>()

// ---- 常量 ----
const intervalItems = [
  { title: '1小时', value: 1 },
  { title: '2小时', value: 2 },
  { title: '3小时', value: 3 },
  { title: '6小时', value: 6 },
  { title: '12小时', value: 12 },
  { title: '24小时', value: 24 },
]

// 提醒时间（0-23 整点，value 使用字符串与后端默认 '9' 对齐）
const hourItems = Array.from({ length: 24 }, (_, h) => ({
  title: `${h}时`,
  value: String(h),
}))

// 提醒消息类型：与后端 get_form 对齐（NotificationType/MessageType 枚举，
// value 为枚举成员名，title 为中文名；同 irabsubscribereminder 的 msgtype 选项）
const msgtypeItems = [
  { title: '资源下载', value: 'Download' },
  { title: '整理入库', value: 'Organize' },
  { title: '订阅', value: 'Subscribe' },
  { title: '站点', value: 'SiteMessage' },
  { title: '媒体服务器', value: 'MediaServer' },
  { title: '手动处理', value: 'Manual' },
  { title: '插件', value: 'Plugin' },
  { title: '智能体', value: 'Agent' },
  { title: '其它', value: 'Other' },
]

// ---- 响应式状态 ----
const form = reactive({
  enabled: false,
  refresh_interval: 6,
  reminder_enabled: false,
  reminder_time: '9',
  reminder_msgtype: 'Plugin',
  run_remind: false,
})
const saving = ref(false)
const clearingCache = ref(false)

function buildPluginUrl(path: string): string {
  return props.pluginId ? `plugin/${props.pluginId}/${path}` : `plugin/MaoyanDianYing/${path}`
}

async function clearCache() {
  if (!props.api) {
    alert('API 未就绪，请刷新页面重试')
    return
  }
  if (!confirm('确定要清理所有缓存数据吗？（保留提醒数据）并重新抓取新数据。')) {
    return
  }
  clearingCache.value = true
  try {
    const url = buildPluginUrl('clear-cache')
    const data = await props.api.post(url)
    if (data?.success) {
      alert(data?.message || '缓存已清理')
    } else {
      alert(data?.message || '清理失败')
    }
  } catch (e) {
    alert('请求失败：' + e)
  } finally {
    clearingCache.value = false
  }
}

// ---- 监听配置变化 ----
watch(
  () => props.initialConfig,
  config => {
    if (!config) return
    form.enabled = Boolean(config.enabled)
    form.refresh_interval = Number(config.refresh_interval) || 6
    form.reminder_enabled = Boolean(config.reminder_enabled)
    form.reminder_time =
      config.reminder_time !== undefined &&
      config.reminder_time !== null &&
      config.reminder_time !== ''
        ? String(config.reminder_time)
        : '9'
    form.reminder_msgtype = config.reminder_msgtype
      ? String(config.reminder_msgtype)
      : 'Plugin'
    form.run_remind = Boolean(config.run_remind)
  },
  { immediate: true, deep: true },
)

// ---- 方法 ----
function save() {
  saving.value = true
  emit('save', { ...form })
  saving.value = false
}
</script>
