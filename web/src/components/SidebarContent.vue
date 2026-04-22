<template>
  <div class="sidebar-inner">
    <div class="logo">
      <el-icon :size="28" color="var(--dm-sidebar-active-text)">
        <VideoPlay />
      </el-icon>
      <span>AV-DM 管理</span>
    </div>

    <el-menu
      :default-active="route.path"
      router
      class="sidebar-menu"
      :background-color="'transparent'"
      :text-color="'var(--dm-sidebar-text)'"
      :active-text-color="'var(--dm-sidebar-active-text)'"
      @select="handleSelect"
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
  </div>
</template>

<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  VideoPlay, Odometer, List, Document, Setting, SwitchButton,
} from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const emit = defineEmits<{
  navigate: []
}>()

const handleSelect = () => {
  emit('navigate')
}

const handleLogout = async () => {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', { type: 'warning' })
    await authStore.logout()
    router.push('/login')
    ElMessage.success('已退出登录')
  } catch {
    // cancel
  }
}
</script>

<style scoped>
.sidebar-inner {
  height: 100%;
  display: flex;
  flex-direction: column;
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
</style>
