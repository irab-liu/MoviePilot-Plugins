<template>
  <div class="maoyan-config pa-4">
    <div class="text-h6 mb-4">猫眼热度榜设置</div>
    <!-- 启用开关 -->
    <VSwitch v-model="form.enabled" label="启用插件" color="primary" />
    <!-- 自动刷新间隔选择 -->
    <VSelect
      v-model="form.refresh_interval"
      :items="intervalItems"
      item-title="title"
      item-value="value"
      label="自动刷新间隔（小时）"
      class="mt-3"
    />
    <!-- 保存按钮 -->
    <div class="d-flex justify-end mt-4">
      <VBtn color="primary" :loading="saving" @click="save">
        <VIcon start>mdi-content-save</VIcon>
        保存
      </VBtn>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'

// ---- 组件属性 ----
const props = defineProps<{
  initialConfig?: Record<string, unknown>
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

// ---- 响应式状态 ----
const form = reactive({
  enabled: false,
  refresh_interval: 6,
})
const saving = ref(false)

// ---- 监听配置变化 ----
watch(
  () => props.initialConfig,
  config => {
    if (!config) return
    form.enabled = Boolean(config.enabled)
    form.refresh_interval = Number(config.refresh_interval) || 6
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
