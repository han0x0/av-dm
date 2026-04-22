<template>
  <div class="task-detail">
    <el-descriptions :column="1" border>
      <el-descriptions-item label="番号">{{ task.content_id }}</el-descriptions-item>
      <el-descriptions-item label="标题">{{ task.content_title || '-' }}</el-descriptions-item>
      <el-descriptions-item label="状态">
        <StatusBadge :status="task.status" />
      </el-descriptions-item>
      <el-descriptions-item label="进度">
        <el-progress
          v-if="task.progress !== null"
          :percentage="Math.round(task.progress / 10)"
          style="max-width: 200px; width: 100%;"
        />
        <span v-else>-</span>
      </el-descriptions-item>
      <el-descriptions-item label="磁力链接">
        <el-link v-if="task.magnet_url" type="primary" :href="task.magnet_url" target="_blank">
          {{ task.magnet_url.substring(0, 50) }}...
        </el-link>
        <span v-else>-</span>
      </el-descriptions-item>
      <el-descriptions-item label="文件大小">
        {{ task.file_size ? formatSize(task.file_size) : '-' }}
      </el-descriptions-item>
      <el-descriptions-item label="文件路径">
        {{ task.file_path || '-' }}
      </el-descriptions-item>
      <el-descriptions-item label="BitComet 任务ID">
        {{ task.bitcomet_task_id || '-' }}
      </el-descriptions-item>
      <el-descriptions-item label="JavSP 任务ID">
        {{ task.javsp_task_id || '-' }}
      </el-descriptions-item>
      <el-descriptions-item label="下载速度">
        {{ task.download_rate ? formatSpeed(task.download_rate) : '-' }}
      </el-descriptions-item>
      <el-descriptions-item label="上传速度">
        {{ task.upload_rate ? formatSpeed(task.upload_rate) : '-' }}
      </el-descriptions-item>
      <el-descriptions-item label="健康度">
        {{ task.health || '-' }}
      </el-descriptions-item>
      <el-descriptions-item label="分享率">
        {{ task.share_ratio || '-' }}
      </el-descriptions-item>
      <el-descriptions-item label="错误信息">
        <el-alert
          v-if="task.error_message"
          :title="task.error_message"
          type="error"
          :closable="false"
        />
        <span v-else>-</span>
      </el-descriptions-item>
      <el-descriptions-item label="创建时间">
        {{ formatDateTime(task.created_at) }}
      </el-descriptions-item>
      <el-descriptions-item label="更新时间">
        {{ formatDateTime(task.updated_at) }}
      </el-descriptions-item>
    </el-descriptions>
  </div>
</template>

<script setup lang="ts">
import { type Task } from '@/api/tasks'
import StatusBadge from './StatusBadge.vue'

const props = defineProps<{
  task: Task
}>()

const formatSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatSpeed = (bytesPerSecond: number): string => {
  return formatSize(bytesPerSecond) + '/s'
}

const formatDateTime = (isoString: string): string => {
  return new Date(isoString).toLocaleString('zh-CN')
}
</script>

<style scoped>
.task-detail {
  padding: 10px;
}
</style>
