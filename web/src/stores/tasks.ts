import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { tasksApi, type Task, type TaskListResponse, type TaskFilterParams } from '@/api/tasks'
import { ElMessage } from 'element-plus'

export const useTasksStore = defineStore('tasks', () => {
  // State
  const tasks = ref<Task[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const loading = ref(false)
  const filters = ref<TaskFilterParams>({
    status: undefined,
    content_id: undefined,
    page: 1,
    page_size: 20,
    sort_by: 'created_at',
    sort_order: 'desc',
  })

  // Getters
  const pages = computed(() => Math.ceil(total.value / pageSize.value))

  // Actions
  const fetchTasks = async (params?: TaskFilterParams) => {
    loading.value = true
    try {
      const mergedParams = { ...filters.value, ...params }
      const response: TaskListResponse = await tasksApi.getTasks(mergedParams)
      tasks.value = response.items
      total.value = response.total
      page.value = response.page
      pageSize.value = response.page_size
    } catch (error) {
      ElMessage.error('获取任务列表失败')
    } finally {
      loading.value = false
    }
  }

  const setFilters = (newFilters: Partial<TaskFilterParams>) => {
    filters.value = { ...filters.value, ...newFilters }
  }

  const resetFilters = () => {
    filters.value = {
      status: undefined,
      content_id: undefined,
      page: 1,
      page_size: 20,
      sort_by: 'created_at',
      sort_order: 'desc',
    }
  }

  const retryTask = async (id: number): Promise<boolean> => {
    try {
      const response = await tasksApi.retryTask(id)
      if (response.success) {
        ElMessage.success(response.message)
        await fetchTasks()
        return true
      }
      return false
    } catch (error) {
      ElMessage.error('重试任务失败')
      return false
    }
  }

  const cancelTask = async (id: number): Promise<boolean> => {
    try {
      const response = await tasksApi.cancelTask(id)
      if (response.success) {
        ElMessage.success(response.message)
        await fetchTasks()
        return true
      }
      return false
    } catch (error) {
      ElMessage.error('取消任务失败')
      return false
    }
  }

  const deleteTask = async (id: number): Promise<boolean> => {
    try {
      const response = await tasksApi.deleteTask(id)
      if (response.success) {
        ElMessage.success(response.message)
        await fetchTasks()
        return true
      }
      return false
    } catch (error) {
      ElMessage.error('删除任务失败')
      return false
    }
  }

  return {
    tasks,
    total,
    page,
    pageSize,
    pages,
    loading,
    filters,
    fetchTasks,
    setFilters,
    resetFilters,
    retryTask,
    cancelTask,
    deleteTask,
  }
})
