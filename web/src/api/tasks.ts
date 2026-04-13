import apiClient from './client'

export interface Task {
  id: number
  content_id: string
  content_title: string | null
  magnet_url: string | null
  file_size: number | null
  bitcomet_task_id: string | null
  bitcomet_task_guid: string | null
  task_type: string | null
  download_rate: number | null
  upload_rate: number | null
  error_code: string | null
  error_message: string | null
  health: string | null
  file_count: number | null
  share_ratio: number | null
  progress: number | null
  status: string
  file_path: string | null
  tags: string | null
  javsp_task_id: string | null
  javsp_checked: boolean
  folder_cleaned: boolean
  javsp_retry_count: number
  created_at: string
  updated_at: string
  timeout_at: string | null
}

export interface TaskListResponse {
  items: Task[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface TaskFilterParams {
  status?: string
  content_id?: string
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: string
}

export interface TaskActionResponse {
  success: boolean
  message: string
  task_id?: number
}

export const tasksApi = {
  getTasks: (params: TaskFilterParams = {}): Promise<TaskListResponse> =>
    apiClient.get('/tasks', { params }).then(res => res.data),
  
  getTask: (id: number): Promise<Task> =>
    apiClient.get(`/tasks/${id}`).then(res => res.data),
  
  retryTask: (id: number): Promise<TaskActionResponse> =>
    apiClient.post(`/tasks/${id}/retry`).then(res => res.data),
  
  cancelTask: (id: number): Promise<TaskActionResponse> =>
    apiClient.post(`/tasks/${id}/cancel`).then(res => res.data),
  
  deleteTask: (id: number): Promise<TaskActionResponse> =>
    apiClient.delete(`/tasks/${id}`).then(res => res.data),
}
