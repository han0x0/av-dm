import apiClient from './client'

export interface ConfigResponse {
  app_name: string
  debug: boolean
  log_level: string
  web_password: string
  web_password_configured: boolean
  
  // 工作流调度配置
  workflow1_interval_minutes: number
  workflow2_interval_minutes: number
  workflow3_interval_minutes: number
  
  // JavSP 提交条件
  javsp_submit_share_ratio: number
  javsp_submit_hours: number
  
  // 业务配置
  max_completed_downloads: number
  max_retry_count: number
  retry_delay_seconds: number
  download_timeout_hours: number
  
  // 路径配置
  bitcomet_download_path: string
  javsp_input_path: string
  javsp_output_path: string
  
  // 服务 URL
  freshrss_url: string
  rsshub_base_url: string
  bitcomet_url: string
  javsp_url: string
  jellyfin_url: string
  jellyfin_library_name: string
  
  // 用户名
  freshrss_username: string
  bitcomet_username: string
  javsp_username: string
  
  // 密码/API Key 配置状态（用于前端显示"已配置"）
  freshrss_password_configured: boolean
  bitcomet_password_configured: boolean
  bitcomet_authentication_configured: boolean
  javsp_password_configured: boolean
  jellyfin_api_key_configured: boolean
  
  // 配置状态
  freshrss_configured: boolean
  bitcomet_configured: boolean
  javsp_configured: boolean
  jellyfin_configured: boolean
  rsshub_configured: boolean
}

export interface ConfigUpdateRequest {
  config: Record<string, any>
}

export interface ConfigUpdateResponse {
  success: boolean
  updated: string[]
  message: string
}

export interface ConfigBackupInfo {
  name: string
  path: string
  size: number
  created: string
}

export interface ConfigBackupResponse {
  success: boolean
  backup_path?: string
  message: string
}

export interface ConfigRestoreResponse {
  success: boolean
  message: string
}

export const configApi = {
  // 获取配置
  getConfig: (): Promise<ConfigResponse> =>
    apiClient.get('/config').then(res => res.data),
  
  // 更新配置
  updateConfig: (data: ConfigUpdateRequest): Promise<ConfigUpdateResponse> =>
    apiClient.put('/config', data).then(res => res.data),
  
  // 备份配置
  backupConfig: (backupName?: string): Promise<ConfigBackupResponse> =>
    apiClient.post('/config/backup', null, { params: { backup_name: backupName } }).then(res => res.data),
  
  // 获取备份列表
  listBackups: (): Promise<ConfigBackupInfo[]> =>
    apiClient.get('/config/backups').then(res => res.data.backups),
  
  // 恢复配置
  restoreConfig: (backupName: string): Promise<ConfigRestoreResponse> =>
    apiClient.post('/config/restore', { backup_name: backupName }).then(res => res.data),
  
  // 删除备份
  deleteBackup: (backupName: string): Promise<ConfigRestoreResponse> =>
    apiClient.delete(`/config/backups/${backupName}`).then(res => res.data),
  
  // 导出原始配置（包含敏感信息）
  exportConfig: (): Promise<Record<string, any>> =>
    apiClient.get('/config/raw').then(res => res.data),
}
