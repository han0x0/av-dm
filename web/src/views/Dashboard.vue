<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <el-row :gutter="20">
      <el-col :xs="24" :sm="12" :md="8" :lg="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon" style="background: var(--dm-gradient-blue);">
            <el-icon :size="32" color="#fff"><List /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats?.total_tasks || 0 }}</div>
            <div class="stat-label">总任务数</div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :xs="24" :sm="12" :md="8" :lg="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon" style="background: var(--dm-gradient-green);">
            <el-icon :size="32" color="#fff"><Download /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats?.running_tasks || 0 }}</div>
            <div class="stat-label">下载中</div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :xs="24" :sm="12" :md="8" :lg="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon" style="background: var(--dm-gradient-orange);">
            <el-icon :size="32" color="#fff"><CircleCheck /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats?.completed_today || 0 }}</div>
            <div class="stat-label">今日完成</div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :xs="24" :sm="12" :md="8" :lg="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon" style="background: var(--dm-gradient-red);">
            <el-icon :size="32" color="#fff"><Warning /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ (stats?.failed_tasks || 0) + (stats?.timeout_tasks || 0) }}</div>
            <div class="stat-label">异常任务</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 磁盘使用和工作流状态 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :xs="24" :md="12">
        <el-card shadow="hover" class="dashboard-card">
          <template #header>
            <div class="card-header">
              <span><el-icon><Folder /></el-icon> 磁盘使用情况</span>
            </div>
          </template>
          <div v-if="stats?.disk_usage">
            <el-progress
              :percentage="stats.disk_usage.percent"
              :status="getDiskStatus(stats.disk_usage.percent)"
              :stroke-width="20"
              :color="getProgressColor(stats.disk_usage.percent)"
            />
            <div class="disk-info">
              <div class="disk-item">
                <span class="disk-label">已用</span>
                <span class="disk-value">{{ formatSize(stats.disk_usage.used) }}</span>
              </div>
              <div class="disk-item">
                <span class="disk-label">可用</span>
                <span class="disk-value">{{ formatSize(stats.disk_usage.free) }}</span>
              </div>
              <div class="disk-item">
                <span class="disk-label">总计</span>
                <span class="disk-value">{{ formatSize(stats.disk_usage.total) }}</span>
              </div>
            </div>
          </div>
          <el-empty v-else description="无法获取磁盘信息" />
        </el-card>
      </el-col>
      
      <el-col :xs="24" :md="12">
        <el-card shadow="hover" class="dashboard-card">
          <template #header>
            <div class="card-header">
              <span><el-icon><Connection /></el-icon> 工作流状态</span>
            </div>
          </template>
          <el-table :data="workflows" size="small" class="workflow-table">
            <el-table-column prop="display_name" label="工作流" />
            <el-table-column prop="interval" label="执行间隔" width="120" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.status === 'running' ? 'success' : 'info'" size="small" effect="dark">
                  {{ row.status === 'running' ? '运行中' : '已停止' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" align="center">
              <template #default="{ row }">
                <el-button
                  link
                  type="primary"
                  size="small"
                  @click="triggerWorkflow(row.name)"
                >
                  执行
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 近期活动 -->
    <el-row style="margin-top: 20px;">
      <el-col :span="24">
        <el-card shadow="hover" class="dashboard-card">
          <template #header>
            <div class="card-header">
              <span><el-icon><Clock /></el-icon> 近期活动</span>
              <el-button link type="primary" @click="$router.push('/tasks')">
                查看全部 <el-icon><ArrowRight /></el-icon>
              </el-button>
            </div>
          </template>
          <el-table :data="recentActivities" size="small" class="activity-table">
            <el-table-column prop="content_id" label="番号" width="150">
              <template #default="{ row }">
                <el-tag size="small" effect="plain" type="info">{{ row.content_id }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="action" label="操作" width="100" />
            <el-table-column prop="status" label="状态" width="120">
              <template #default="{ row }">
                <StatusBadge :status="row.status" />
              </template>
            </el-table-column>
            <el-table-column prop="message" label="消息" show-overflow-tooltip />
            <el-table-column prop="created_at" label="时间" width="180">
              <template #default="{ row }">
                {{ formatDateTime(row.created_at) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  List,
  Download,
  CircleCheck,
  Warning,
  Folder,
  Connection,
  Clock,
  ArrowRight,
} from '@element-plus/icons-vue'
import { useStatsStore } from '@/stores/stats'
import StatusBadge from '@/components/StatusBadge.vue'
import { ElMessage } from 'element-plus'

const statsStore = useStatsStore()

const stats = computed(() => statsStore.stats)
const workflows = computed(() => statsStore.workflows)
const recentActivities = computed(() => statsStore.recentActivities.slice(0, 10))

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

const getDiskStatus = (percent: number): string => {
  if (percent > 90) return 'exception'
  if (percent > 70) return 'warning'
  return ''
}

const getProgressColor = (percent: number): string => {
  if (percent > 90) return '#f85149'
  if (percent > 70) return '#d29922'
  return '#58a6ff'
}

const triggerWorkflow = async (name: string) => {
  const success = await statsStore.triggerWorkflow(name)
  if (success) {
    ElMessage.success('工作流已触发')
  }
}
</script>

<style scoped>
.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  padding: 20px;
}

.stat-icon {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 16px;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.15);
  transition: transform 0.2s ease;
}

.stat-card:hover .stat-icon {
  transform: scale(1.05);
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: var(--dm-text-primary);
  line-height: 1.2;
  transition: color 0.3s ease;
}

.stat-label {
  font-size: 14px;
  color: var(--dm-text-secondary);
  margin-top: 4px;
  transition: color 0.3s ease;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  font-size: 15px;
  color: var(--dm-text-primary);
  transition: color 0.3s ease;
}

.card-header .el-icon {
  margin-right: 6px;
  vertical-align: middle;
}

.disk-info {
  display: flex;
  justify-content: space-between;
  margin-top: 20px;
  gap: 16px;
}

.disk-item {
  flex: 1;
  text-align: center;
  padding: 12px;
  background-color: var(--dm-bg-hover);
  border-radius: 10px;
  transition: background-color 0.3s ease;
}

.disk-label {
  display: block;
  font-size: 12px;
  color: var(--dm-text-muted);
  margin-bottom: 4px;
  transition: color 0.3s ease;
}

.disk-value {
  display: block;
  font-size: 16px;
  font-weight: 600;
  color: var(--dm-text-primary);
  transition: color 0.3s ease;
}

.dashboard-card {
  border-radius: 12px;
}

.workflow-table :deep(.el-table__row) {
  transition: background-color 0.2s ease;
}

.activity-table :deep(.el-table__row) {
  transition: background-color 0.2s ease;
}
</style>
