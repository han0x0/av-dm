import apiClient from './client'

export interface DiskUsage {
  total: number
  used: number
  free: number
  percent: number
}

export interface WorkflowStatus {
  name: string
  display_name: string
  status: string
  last_run?: string
  next_run?: string
  interval: string
}

export interface TaskStatusCount {
  status: string
  count: number
}

export interface StatsResponse {
  total_tasks: number
  running_tasks: number
  pending_tasks: number
  completed_tasks: number
  failed_tasks: number
  timeout_tasks: number
  completed_today: number
  created_today: number
  status_distribution: TaskStatusCount[]
  disk_usage: DiskUsage | null
  workflow_status: WorkflowStatus[]
}

export interface RecentActivity {
  id: number
  content_id: string
  action: string
  status: string
  message: string | null
  created_at: string
}

export interface RecentStatsResponse {
  activities: RecentActivity[]
  total: number
}

export const statsApi = {
  getStats: (): Promise<StatsResponse> =>
    apiClient.get('/stats').then(res => res.data),
  
  getRecentActivities: (limit: number = 10): Promise<RecentStatsResponse> =>
    apiClient.get('/stats/recent', { params: { limit } }).then(res => res.data),
}
