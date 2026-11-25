<script setup>
/**
 * Agent 定时任务管理插件配置页。
 *
 * 纯 HTML/CSS 实现，在宿主插件设置中渲染，仅提供插件启用开关；
 * 任务管理功能在侧栏全页中完成。
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
    <div class="atm-config-card">
      <div class="atm-config-head">
        <div>
          <div class="atm-config-title">Agent 定时任务管理</div>
          <div class="atm-config-sub">仅提供管理界面，不新建调度器</div>
        </div>
        <button class="atm-config-close" @click="emit('close')">×</button>
      </div>
      <div class="atm-config-body">
        <div class="atm-config-tip">
          启用后可在左侧「系统」分组找到「Agent 定时任务」入口。新建任务仍通过对话让
          Agent 使用 agent_task 工具创建。
        </div>

        <label class="atm-config-switch">
          <input v-model="form.enabled" type="checkbox" />
          <span>启用插件</span>
        </label>

        <div v-if="message.show" class="atm-config-msg" :class="`atm-config-msg--${message.type}`">
          {{ message.text }}
        </div>
      </div>
      <div class="atm-config-foot">
        <button class="atm-config-btn atm-config-btn--primary" :disabled="saving" @click="saveConfig">
          {{ saving ? '保存中…' : '保存' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.atm-config {
  padding: 16px;
  font-size: 14px;
}
.atm-config-card {
  max-width: 640px;
  margin: 0 auto;
  border: 1px solid rgba(128, 128, 128, 0.35);
  border-radius: 10px;
  background: #1e1e1e;
  color: #e0e0e0;
  overflow: hidden;
}
.atm-config-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid rgba(128, 128, 128, 0.25);
}
.atm-config-title {
  font-size: 16px;
  font-weight: 700;
}
.atm-config-sub {
  margin-top: 2px;
  font-size: 12px;
  color: rgba(224, 224, 224, 0.6);
}
.atm-config-close {
  border: none;
  background: transparent;
  color: inherit;
  font-size: 20px;
  cursor: pointer;
}
.atm-config-body {
  padding: 16px;
}
.atm-config-tip {
  margin-bottom: 14px;
  padding: 10px 12px;
  border-radius: 6px;
  background: rgba(2, 136, 209, 0.1);
  border: 1px solid rgba(2, 136, 209, 0.4);
  font-size: 13px;
}
.atm-config-switch {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}
.atm-config-switch input {
  width: 18px;
  height: 18px;
  cursor: pointer;
}
.atm-config-msg {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 6px;
  background: rgba(128, 128, 128, 0.15);
}
.atm-config-msg--success {
  background: rgba(46, 125, 50, 0.2);
  color: #81c784;
}
.atm-config-msg--error {
  background: rgba(198, 40, 40, 0.2);
  color: #ef9a9a;
}
.atm-config-foot {
  display: flex;
  justify-content: flex-end;
  padding: 12px 16px;
  border-top: 1px solid rgba(128, 128, 128, 0.25);
}
.atm-config-btn {
  padding: 8px 18px;
  border: 1px solid rgba(128, 128, 128, 0.45);
  border-radius: 6px;
  background: transparent;
  color: inherit;
  font-size: 13px;
  cursor: pointer;
}
.atm-config-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.atm-config-btn--primary {
  border-color: #1976d2;
  background: #1976d2;
  color: #fff;
}
</style>
