<template>
  <div class="tasks-page">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>任务管理</span>
          <div class="header-actions">
            <el-input
              v-model="searchQuery"
              placeholder="搜索番号..."
              style="width: 200px;"
              clearable
              @keyup.enter="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            
            <el-select
              v-model="statusFilter"
              placeholder="状态筛选"
              clearable
              style="width: 120px;"
            >
              <el-option label="全部" value="" />
              <el-option label="等待中" value="pending" />
              <el-option label="下载中" value="running" />
              <el-option label="已完成" value="completed" />
              <el-option label="错误" value="error" />
              <el-option label="超时" value="timeout" />
            </el-select>
            
            <el-button type="primary" :icon="Refresh" @click="refreshTasks">
              刷新
            </el-button>
          </div>
        </div>
      </template>
      
      <el-table
        v-loading="tasksStore.loading"
        :data="tasksStore.tasks"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="content_id" label="番号" width="140" sortable>
          <template #default="{ row }">
            <el-link type="primary" @click="showDetail(row)">
              {{ row.content_id }}
            </el-link>
          </template>
        </el-table-column>
        
        <el-table-column prop="content_title" label="标题" min-width="200" show-overflow-tooltip />
        
        <el-table-column prop="status" label="状态" width="110">
          <template #default="{ row }">
            <StatusBadge :status="row.status" />
          </template>
        </el-table-column>
        
        <el-table-column prop="progress" label="进度" width="120">
          <template #default="{ row }">
            <el-progress
              v-if="row.progress !== null"
              :percentage="Math.round(row.progress / 10)"
              :status="getProgressStatus(row)"
            />
            <span v-else>-</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="file_size" label="大小" width="100">
          <template #default="{ row }">
            {{ row.file_size ? formatSize(row.file_size) : '-' }}
          </template>
        </el-table-column>
        
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="canRetry(row.status)"
              link
              type="primary"
              size="small"
              @click="handleRetry(row)"
            >
              重试
            </el-button>
            <el-button
              v-if="row.status === 'pending'"
              link
              type="warning"
              size="small"
              @click="handleCancel(row)"
            >
              取消
            </el-button>
            <el-button
              link
              type="danger"
              size="small"
              @click="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="tasksStore.page"
          v-model:page-size="tasksStore.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="tasksStore.total"
          layout="total, sizes, prev, pager, next"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>
    
    <!-- 任务详情抽屉 -->
    <el-drawer
      v-model="detailVisible"
      title="任务详情"
      size="500px"
    >
      <TaskDetail v-if="selectedTask" :task="selectedTask" />
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { Search, Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useTasksStore } from '@/stores/tasks'
import { type Task } from '@/api/tasks'
import StatusBadge from '@/components/StatusBadge.vue'
import TaskDetail from '@/components/TaskDetail.vue'

const tasksStore = useTasksStore()

const searchQuery = ref('')
const statusFilter = ref('')
const detailVisible = ref(false)
const selectedTask = ref<Task | null>(null)

// 从 store 获取任务列表
const refreshTasks = () => {
  tasksStore.fetchTasks({
    content_id: searchQuery.value || undefined,
    status: statusFilter.value || undefined,
  })
}

// 搜索
const handleSearch = () => {
  tasksStore.setFilters({ page: 1 })
  refreshTasks()
}

// 分页
const handlePageChange = (page: number) => {
  tasksStore.setFilters({ page })
  refreshTasks()
}

const handleSizeChange = (size: number) => {
  tasksStore.setFilters({ page_size: size, page: 1 })
  refreshTasks()
}

// 监听筛选条件变化
watch([statusFilter], () => {
  tasksStore.setFilters({ page: 1, status: statusFilter.value || undefined })
  refreshTasks()
})

// 工具函数
const formatSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatDateTime = (isoString: string): string => {
  return new Date(isoString).toLocaleString('zh-CN')
}

const getProgressStatus = (row: Task) => {
  if (row.status === 'error' || row.status === 'timeout') return 'exception'
  if (row.progress && row.progress >= 1000) return 'success'
  return ''
}

const canRetry = (status: string): boolean => {
  return ['error', 'javsp_error', 'timeout'].includes(status)
}

// 操作处理
const showDetail = (task: Task) => {
  selectedTask.value = task
  detailVisible.value = true
}

const handleRetry = async (task: Task) => {
  try {
    await ElMessageBox.confirm(`确定要重试任务 ${task.content_id} 吗？`, '提示')
    await tasksStore.retryTask(task.id)
  } catch {
    // 取消
  }
}

const handleCancel = async (task: Task) => {
  try {
    await ElMessageBox.confirm(`确定要取消任务 ${task.content_id} 吗？`, '提示')
    await tasksStore.cancelTask(task.id)
  } catch {
    // 取消
  }
}

const handleDelete = async (task: Task) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除任务 ${task.content_id} 吗？此操作不可恢复！`,
      '警告',
      { type: 'warning' }
    )
    await tasksStore.deleteTask(task.id)
  } catch {
    // 取消
  }
}

onMounted(() => {
  refreshTasks()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}
</style>
