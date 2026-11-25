<script setup>
/**
 * Agent 定时任务管理全页入口包装组件。
 *
 * 宿主侧栏全页优先加载 AppPage；这里直接转发给 Page，保持单一实现。
 */
import Page from './Page.vue'

defineOptions({ inheritAttrs: false })
</script>

<template>
  <Page v-bind="$attrs" />
</template>
