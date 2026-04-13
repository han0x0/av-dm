import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, type UserInfo } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  // State
  const token = ref<string>(localStorage.getItem('token') || '')
  const user = ref<UserInfo | null>(null)
  const loading = ref(false)

  // Getters
  const isAuthenticated = computed(() => !!token.value)

  // Actions
  const login = async (password: string): Promise<boolean> => {
    loading.value = true
    try {
      const response = await authApi.login(password)
      if (response.success) {
        token.value = response.access_token
        localStorage.setItem('token', response.access_token)
        return true
      }
      return false
    } catch (error) {
      console.error('登录失败:', error)
      return false
    } finally {
      loading.value = false
    }
  }

  const logout = async () => {
    try {
      await authApi.logout()
    } finally {
      token.value = ''
      user.value = null
      localStorage.removeItem('token')
    }
  }

  const fetchUser = async () => {
    try {
      const userInfo = await authApi.getMe()
      user.value = userInfo
    } catch {
      // 获取失败则清除 token
      token.value = ''
      localStorage.removeItem('token')
    }
  }

  return {
    token,
    user,
    loading,
    isAuthenticated,
    login,
    logout,
    fetchUser,
  }
})
