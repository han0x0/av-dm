import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/Login.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      name: 'Layout',
      component: () => import('@/views/Layout.vue'),
      redirect: '/dashboard',
      children: [
        {
          path: 'dashboard',
          name: 'Dashboard',
          component: () => import('@/views/Dashboard.vue'),
          meta: { title: '概览' },
        },
        {
          path: 'tasks',
          name: 'Tasks',
          component: () => import('@/views/Tasks.vue'),
          meta: { title: '任务管理' },
        },
        {
          path: 'logs',
          name: 'Logs',
          component: () => import('@/views/Logs.vue'),
          meta: { title: '日志查看' },
        },
        {
          path: 'settings',
          name: 'Settings',
          component: () => import('@/views/Settings.vue'),
          meta: { title: '系统设置' },
        },
      ],
    },
  ],
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  
  if (to.meta.public) {
    next()
  } else if (!authStore.isAuthenticated) {
    next('/login')
  } else {
    next()
  }
})

export default router
