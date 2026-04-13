import axios, { AxiosError, type AxiosInstance, type AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

// 创建 axios 实例
const apiClient: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response
  },
  (error: AxiosError) => {
    const status = error.response?.status
    
    if (status === 401) {
      // 清除 token 并重定向到登录页
      localStorage.removeItem('token')
      ElMessage.error('登录已过期，请重新登录')
      router.push('/login')
    } else if (status === 403) {
      ElMessage.error('没有权限执行此操作')
    } else if (status === 500) {
      ElMessage.error('服务器内部错误')
    }
    
    return Promise.reject(error)
  }
)

export default apiClient
