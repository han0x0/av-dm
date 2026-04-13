<template>
  <el-tag :type="statusType" size="small" effect="light">
    {{ statusText }}
  </el-tag>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  status: string
}>()

const statusMap: Record<string, { text: string; type: 'success' | 'warning' | 'danger' | 'info' | '' }> = {
  pending: { text: '等待中', type: 'info' },
  running: { text: '下载中', type: 'warning' },
  completed: { text: '已完成', type: 'success' },
  error: { text: '错误', type: 'danger' },
  javsp_error: { text: '整理失败', type: 'danger' },
  timeout: { text: '超时', type: 'danger' },
  timeout_javsp_pending: { text: '超时待整理', type: 'warning' },
  duplicate_cancelled: { text: '已重复', type: 'info' },
  cancelled: { text: '已取消', type: 'info' },
}

const statusText = computed(() => {
  return statusMap[props.status]?.text || props.status
})

const statusType = computed(() => {
  return statusMap[props.status]?.type || 'info'
})
</script>
