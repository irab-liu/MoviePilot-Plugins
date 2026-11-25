<script setup>
/**
 * Agent 定时任务管理插件配置页。
 *
 * 在宿主插件设置中渲染，使用宿主全局注册的 Vuetify 组件；
 * 仅提供插件启用开关，任务管理功能在侧栏全页中完成。
 */
import { onBeforeUnmount, reactive, ref } from 'vue'
import { errorMessage, pluginRequest } from '../utils/api'

const props = defineProps({
  api: { type: Object, default: () => ({}) },
  pluginId: { type: String, default: '' },
  initialConfig: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['close'])

const saving = ref(false)
const message = reactive({ show: false, type: 'info', text: '' })
const form = reactive({
  enabled: true,
  ...(props.initialConfig || {}),
})
let messageTimer = null

/** 显示一条自动消失的提示。 */
function showMessage(text, type = 'info') {
  if (messageTimer) clearTimeout(messageTimer)
  message.text = text
  message.type = type
  message.show = true
  messageTimer = setTimeout(() => {
    message.show = false
    messageTimer = null
  }, 4000)
}

/** 保存插件配置。 */
async function saveConfig() {
  saving.value = true
  try {
    const result = await pluginRequest(props.api, props.pluginId, '/config', {
      method: 'POST',
      body: { enabled: !!form.enabled },
    })
    if (!result?.success) {
      throw new Error(result?.message || '保存失败')
    }
    showMessage('配置已保存', 'success')
  } catch (error) {
    showMessage(errorMessage(error, '保存失败'), 'error')
  } finally {
    saving.value = false
  }
}

onBeforeUnmount(() => {
  if (messageTimer) clearTimeout(messageTimer)
})
</script>

<template>
  <div class="atm-config">
    <v-card variant="outlined" rounded="lg">
      <v-card-title class="d-flex align-center">
        Agent 定时任务管理
        <v-spacer />
        <v-btn size="small" variant="text" icon="mdi-close" @click="emit('close')" />
      </v-card-title>
      <v-card-text>
        <v-alert type="info" variant="tonal" class="mb-4" density="compact">
          本插件只提供 Agent 自主定时任务的管理界面，不新建调度器。启用后可在左侧「系统」分组找到入口。
        </v-alert>

        <div class="d-flex align-center mb-4">
          <v-switch
            v-model="form.enabled"
            color="primary"
            density="compact"
            hide-details
            label="启用插件"
            class="mr-4"
          />
        </div>

        <Transition name="fade">
          <v-alert
            v-if="message.show"
            :type="message.type"
            variant="tonal"
            density="compact"
          >
            {{ message.text }}
          </v-alert>
        </Transition>
      </v-card-text>
      <v-card-actions class="px-4 pb-4">
        <v-spacer />
        <v-btn color="primary" :loading="saving" @click="saveConfig">保存</v-btn>
      </v-card-actions>
    </v-card>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
