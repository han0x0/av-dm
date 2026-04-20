<template>
  <div class="logs-page">
    <el-card shadow="hover" class="logs-card">
      <template #header>
        <div class="card-header">
          <span class="page-title">日志查看</span>
          <div class="header-actions">
            <el-select
              v-model="levelFilter"
              placeholder="日志级别"
              clearable
              style="width: 130px;"
            >
              <el-option label="全部" value="" />
              <el-option label="INFO" value="INFO" />
              <el-option label="WARNING" value="WARNING" />
              <el-option label="ERROR" value="ERROR" />
              <el-option label="DEBUG" value="DEBUG" />
            </el-select>
            
            <el-input
              v-model="searchQuery"
              placeholder="搜索关键字..."
              style="width: 220px;"
              clearable
              @keyup.enter="refreshLogs"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            
            <el-button
              :type="autoRefresh ? 'success' : 'default'"
              @click="toggleAutoRefresh"
            >
              {{ autoRefresh ? '暂停' : '实时' }}
            </el-button>
            
            <el-button :icon="Refresh" @click="refreshLogs">
              刷新
            </el-button>
          </div>
        </div>
      </template>
      
      <div v-loading="loading" class="log-container">
        <div
          v-for="(log, index) in logs"
          :key="index"
          class="log-line"
          :class="`level-${log.level.toLowerCase()}`"
        >
          <span class="log-time">{{ formatTime(log.timestamp) }}</span>
          <span class="log-level">[{{ log.level }}]</span>
          <span v-if="log.module" class="log-module">{{ log.module }}:</span>
          <span class="log-message">{{ log.message }}</span>
        </div>
        
        <el-empty v-if="logs.length === 0" description="暂无日志" />
      </div>
      
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[50, 100, 200, 500]"
          :total="total"
          layout="total, sizes, prev, pager, next"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { Search, Refresh } from '@element-plus/icons-vue'
import { logsApi, type LogEntry } from '@/api/logs'

const logs = ref<LogEntry[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)
const loading = ref(false)
const levelFilter = ref('')
const searchQuery = ref('')
const autoRefresh = ref(false)
let refreshTimer: number | null = null

const fetchLogs = async () => {
  loading.value = true
  try {
    const response = await logsApi.getLogs({
      level: levelFilter.value || undefined,
      search: searchQuery.value || undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    logs.value = response.entries
    total.value = response.total
  } catch (error) {
    console.error('获取日志失败', error)
  } finally {
    loading.value = false
  }
}

const refreshLogs = () => {
  page.value = 1
  fetchLogs()
}

const handlePageChange = (newPage: number) => {
  page.value = newPage
  fetchLogs()
}

const handleSizeChange = (newSize: number) => {
  pageSize.value = newSize
  page.value = 1
  fetchLogs()
}

const toggleAutoRefresh = () => {
  autoRefresh.value = !autoRefresh.value
  if (autoRefresh.value) {
    refreshTimer = window.setInterval(fetchLogs, 3000)
  } else if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

const formatTime = (isoString: string): string => {
  const date = new Date(isoString)
  return date.toLocaleTimeString('zh-CN')
}

// 监听筛选条件变化
watch([levelFilter], () => {
  page.value = 1
  fetchLogs()
})

onMounted(() => {
  fetchLogs()
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.logs-card {
  border-radius: 12px;
}

.page-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--dm-text-primary);
  transition: color 0.3s ease;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.log-container {
  max-height: 600px;
  overflow-y: auto;
  font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.7;
  background-color: var(--dm-log-bg);
  color: var(--dm-log-text);
  padding: 16px;
  border-radius: 10px;
  border: 1px solid var(--dm-border);
  transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease;
}

.log-line {
  padding: 3px 0;
  white-space: pre-wrap;
  word-break: break-all;
}

.log-time {
  color: var(--dm-log-time);
  margin-right: 10px;
  font-size: 12px;
  transition: color 0.3s ease;
}

.log-level {
  font-weight: bold;
  margin-right: 10px;
  font-size: 12px;
  transition: color 0.3s ease;
}

.level-info .log-level {
  color: var(--dm-log-info);
}

.level-warning .log-level {
  color: var(--dm-log-warning);
}

.level-error .log-level {
  color: var(--dm-log-error);
}

.level-debug .log-level {
  color: var(--dm-log-debug);
}

.log-module {
  color: var(--dm-log-module);
  margin-right: 10px;
  font-size: 12px;
  transition: color 0.3s ease;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}
</style>
