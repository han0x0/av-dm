import apiClient from './client'

export interface LoginRequest {
  password: string
}

export interface LoginResponse {
  success: boolean
  access_token: string
  token_type: string
  message: string
}

export interface UserInfo {
  username: string
  is_authenticated: boolean
}

export const authApi = {
  login: (password: string): Promise<LoginResponse> =>
    apiClient.post('/auth/login', { password }).then(res => res.data),
  
  logout: (): Promise<void> =>
    apiClient.post('/auth/logout').then(res => res.data),
  
  getMe: (): Promise<UserInfo> =>
    apiClient.get('/auth/me').then(res => res.data),
}
