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
      <VRow class="mb-3">
        <VCol cols="12" sm="6" md="3">
          <VSwitch
            v-model="form.enabled"
            label="启用插件"
            color="primary"
            hide-details
            density="compact"
          />
        </VCol>
        <VCol cols="12" sm="auto">
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
        </VCol>
      </VRow>
      <VRow>
        <VCol cols="12" sm="6" md="3">
          <VSelect
            v-model="form.refresh_interval"
            :items="intervalItems"
            item-title="title"
            item-value="value"
            label="自动刷新间隔"
            variant="outlined"
            density="compact"
            hide-details
            class="maoyan-select"
          />
        </VCol>
      </VRow>
    </VCardText>

    <VDivider />

    <!-- 通知设置 -->
    <VCardText class="py-4">
      <div class="text-subtitle-2 mb-3 grey--text">通知设置</div>
      <VRow class="mb-3">
        <VCol cols="12" sm="6" md="3">
          <VSwitch
            v-model="form.reminder_enabled"
            label="开启通知"
            color="primary"
            hide-details
            density="compact"
          />
        </VCol>
        <VCol cols="12" sm="6" md="5">
          <VSwitch
            v-model="form.run_remind"
            label="立即运行一次提醒"
            color="secondary"
            hide-details
            density="compact"
          />
        </VCol>
      </VRow>
      <div class="text-caption grey--text mb-3" style="max-width: 560px">
        根据插件设置的自动刷新间隔推送今日新增影片，已经推送过的不会重复推送。“立即运行一次提醒”在无新增时会推送 TOP5 推荐。
      </div>
      <VRow>
        <VCol cols="12" sm="6" md="3">
          <VSelect
            v-model="form.reminder_msgtype"
            :items="msgtypeItems"
            label="消息类型"
            variant="outlined"
            density="compact"
            hide-details
            class="maoyan-select"
          />
        </VCol>
      </VRow>
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
  if (!confirm('确定要清理所有缓存数据吗？将清空 TMDB 搜索、状态、演员、详情、通知推送记录等缓存并重新抓取新数据。')) {
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

<style scoped>
/* 手机无 hover，outlined 边框默认 opacity 0.38 太浅、与背景融合；
   提升到高强调度，与电脑版 hover 观感一致 */
.maoyan-select :deep(.v-field__outline) {
  --v-field-border-opacity: 1;
}
</style>
