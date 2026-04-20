<template>
  <el-container class="layout-container">
    <el-aside width="220px" class="sidebar">
      <div class="logo">
        <el-icon :size="28" color="var(--dm-sidebar-active-text)"><VideoPlay /></el-icon>
        <span>AV-DM 管理</span>
      </div>
      
      <el-menu
        :default-active="$route.path"
        router
        class="sidebar-menu"
        :background-color="'transparent'"
        :text-color="'var(--dm-sidebar-text)'"
        :active-text-color="'var(--dm-sidebar-active-text)'"
      >
        <el-menu-item index="/dashboard">
          <el-icon><Odometer /></el-icon>
          <span>概览</span>
        </el-menu-item>
        
        <el-menu-item index="/tasks">
          <el-icon><List /></el-icon>
          <span>任务管理</span>
        </el-menu-item>
        
        <el-menu-item index="/logs">
          <el-icon><Document /></el-icon>
          <span>日志查看</span>
        </el-menu-item>
        
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <span>系统设置</span>
        </el-menu-item>
      </el-menu>
      
      <div class="sidebar-footer">
        <el-button type="danger" text @click="handleLogout">
          <el-icon><SwitchButton /></el-icon>
          退出登录
        </el-button>
      </div>
    </el-aside>
    
    <el-container>
      <el-header class="header">
        <div class="breadcrumb">
          {{ $route.meta.title || 'AV Download Manager' }}
        </div>
        <div class="header-actions">
          <el-tag v-if="statsStore.lastUpdate" type="info" size="small" effect="plain">
            更新于: {{ formatTime(statsStore.lastUpdate) }}
          </el-tag>
          <el-tooltip :content="themeStore.isDark() ? '切换到浅色模式' : '切换到深色模式'" placement="bottom">
            <el-button
              :icon="themeStore.isDark() ? Sunny : Moon"
              circle
              size="small"
              @click="themeStore.toggleTheme"
            />
          </el-tooltip>
          <el-button
            :icon="Refresh"
            circle
            size="small"
            :loading="statsStore.loading"
            @click="refreshData"
          />
        </div>
      </el-header>
      
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  VideoPlay,
  Odometer,
  List,
  Document,
  Setting,
  SwitchButton,
  Refresh,
  Sunny,
  Moon,
} from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { useStatsStore } from '@/stores/stats'
import { useThemeStore } from '@/stores/theme'

const router = useRouter()
const authStore = useAuthStore()
const statsStore = useStatsStore()
const themeStore = useThemeStore()

let refreshTimer: number | null = null

const formatTime = (date: Date) => {
  return date.toLocaleTimeString('zh-CN')
}

const refreshData = () => {
  statsStore.refreshAll()
}

const handleLogout = async () => {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      type: 'warning',
    })
    await authStore.logout()
    router.push('/login')
    ElMessage.success('已退出登录')
  } catch {
    // 取消退出
  }
}

onMounted(() => {
  // 初始加载数据
  statsStore.refreshAll()
  
  // 每 5 秒自动刷新
  refreshTimer = window.setInterval(() => {
    statsStore.refreshAll()
  }, 5000)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.sidebar {
  background-color: var(--dm-bg-sidebar);
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--dm-border);
  transition: background-color 0.3s ease, border-color 0.3s ease;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--dm-text-primary);
  font-size: 18px;
  font-weight: bold;
  border-bottom: 1px solid var(--dm-border);
  transition: color 0.3s ease, border-color 0.3s ease;
}

.sidebar-menu {
  flex: 1;
  border-right: none;
}

.sidebar-menu :deep(.el-menu-item) {
  border-radius: 8px;
  margin: 4px 12px;
  height: 48px;
  line-height: 48px;
}

.sidebar-menu :deep(.el-menu-item.is-active) {
  font-weight: 600;
}

.sidebar-menu :deep(.el-menu-item .el-icon) {
  font-size: 18px;
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid var(--dm-border);
  text-align: center;
  transition: border-color 0.3s ease;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: var(--dm-bg-header);
  box-shadow: var(--dm-shadow-card);
  z-index: 1;
  transition: background-color 0.3s ease;
}

.breadcrumb {
  font-size: 16px;
  font-weight: 500;
  color: var(--dm-text-primary);
  transition: color 0.3s ease;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.main-content {
  background-color: var(--dm-bg-body);
  padding: 20px;
  overflow-y: auto;
  transition: background-color 0.3s ease;
}
</style>
