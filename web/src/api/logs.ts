import apiClient from './client'

export interface LogEntry {
  timestamp: string
  level: string
  message: string
  module: string | null
  line: number | null
}

export interface LogResponse {
  entries: LogEntry[]
  total: number
  page: number
  page_size: number
}

export interface LogFilterParams {
  level?: string
  search?: string
  page?: number
  page_size?: number
}

export const logsApi = {
  getLogs: (params: LogFilterParams = {}): Promise<LogResponse> =>
    apiClient.get('/logs', { params }).then(res => res.data),
  
  getRawLogs: (lines: number = 100): Promise<string> =>
    apiClient.get('/logs/raw', { params: { lines } }).then(res => res.data),
}
