import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { statsApi, type StatsResponse, type RecentActivity } from '@/api/stats'
import { workflowsApi, type Workflow } from '@/api/workflows'
import { ElMessage } from 'element-plus'

export const useStatsStore = defineStore('stats', () => {
  // State
  const stats = ref<StatsResponse | null>(null)
  const recentActivities = ref<RecentActivity[]>([])
  const workflows = ref<Workflow[]>([])
  const loading = ref(false)
  const lastUpdate = ref<Date | null>(null)

  // Getters
  const isLoading = computed(() => loading.value)

  // Actions
  const fetchStats = async () => {
    try {
      stats.value = await statsApi.getStats()
      lastUpdate.value = new Date()
    } catch (error) {
      console.error('获取统计信息失败', error)
    }
  }

  const fetchRecentActivities = async (limit: number = 10) => {
    try {
      const response = await statsApi.getRecentActivities(limit)
      recentActivities.value = response.activities
    } catch (error) {
      console.error('获取近期活动失败', error)
    }
  }

  const fetchWorkflows = async () => {
    try {
      workflows.value = await workflowsApi.getWorkflows()
    } catch (error) {
      console.error('获取工作流状态失败', error)
    }
  }

  const refreshAll = async () => {
    loading.value = true
    try {
      await Promise.all([
        fetchStats(),
        fetchRecentActivities(),
        fetchWorkflows(),
      ])
    } finally {
      loading.value = false
    }
  }

  const triggerWorkflow = async (name: string): Promise<boolean> => {
    try {
      const response = await workflowsApi.triggerWorkflow(name)
      if (response.success) {
        ElMessage.success(response.message)
        await fetchWorkflows()
        return true
      }
      return false
    } catch (error) {
      ElMessage.error('触发工作流失败')
      return false
    }
  }

  return {
    stats,
    recentActivities,
    workflows,
    loading,
    lastUpdate,
    isLoading,
    fetchStats,
    fetchRecentActivities,
    fetchWorkflows,
    refreshAll,
    triggerWorkflow,
  }
})
