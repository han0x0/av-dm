import apiClient from './client'

export interface ServiceTestRequest {
  url: string
  username?: string
  password?: string
  api_key?: string
  client_id?: string
  authentication?: string
}

export interface ServiceTestResponse {
  success: boolean
  message: string
  details: Record<string, any>
}

export interface ServiceStatus {
  configured: boolean
  url?: string
  username?: string
  has_auth?: boolean
  has_api_key?: boolean
}

export interface ServicesStatusResponse {
  freshrss: ServiceStatus
  rsshub: ServiceStatus
  bitcomet: ServiceStatus
  javsp: ServiceStatus
  jellyfin: ServiceStatus
}

export const servicesApi = {
  // 测试 FreshRSS 连接
  testFreshRSS: (data: ServiceTestRequest): Promise<ServiceTestResponse> =>
    apiClient.post('/services/test/freshrss', data).then(res => res.data),
  
  // 测试 RSSHub 连接
  testRSSHub: (data: ServiceTestRequest): Promise<ServiceTestResponse> =>
    apiClient.post('/services/test/rsshub', data).then(res => res.data),
  
  // 测试 BitComet 连接
  testBitComet: (data: ServiceTestRequest): Promise<ServiceTestResponse> =>
    apiClient.post('/services/test/bitcomet', data).then(res => res.data),
  
  // 测试 JavSP 连接
  testJavSP: (data: ServiceTestRequest): Promise<ServiceTestResponse> =>
    apiClient.post('/services/test/javsp', data).then(res => res.data),
  
  // 测试 Jellyfin 连接
  testJellyfin: (data: ServiceTestRequest): Promise<ServiceTestResponse> =>
    apiClient.post('/services/test/jellyfin', data).then(res => res.data),
  
  // 获取所有服务状态
  getServicesStatus: (): Promise<ServicesStatusResponse> =>
    apiClient.get('/services/status').then(res => res.data),
}
