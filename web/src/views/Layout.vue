<template>
  <el-container class="layout-container">
    <!-- 桌面端侧边栏 -->
    <el-aside v-if="!isMobile" width="220px" class="sidebar">
      <SidebarContent @navigate="drawerVisible = false" />
    </el-aside>

    <!-- 移动端抽屉侧边栏 -->
    <el-drawer
      v-if="isMobile"
      v-model="drawerVisible"
      :with-header="false"
      size="220px"
      direction="ltr"
      class="mobile-sidebar-drawer"
    >
      <SidebarContent @navigate="drawerVisible = false" />
    </el-drawer>

    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-button
            v-if="isMobile"
            :icon="Menu"
            circle
            size="small"
            @click="drawerVisible = true"
            class="menu-btn"
          />
          <div class="breadcrumb">
            {{ $route.meta.title || 'AV Download Manager' }}
          </div>
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
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  Refresh, Sunny, Moon, Menu,
} from '@element-plus/icons-vue'
import { useStatsStore } from '@/stores/stats'
import { useThemeStore } from '@/stores/theme'
import SidebarContent from '@/components/SidebarContent.vue'

const router = useRouter()
const statsStore = useStatsStore()
const themeStore = useThemeStore()

let refreshTimer: number | null = null

const MOBILE_BREAKPOINT = 768
const windowWidth = ref(window.innerWidth)
const isMobile = computed(() => windowWidth.value < MOBILE_BREAKPOINT)
const drawerVisible = ref(false)

const updateWindowWidth = () => {
  windowWidth.value = window.innerWidth
  if (!isMobile.value) {
    drawerVisible.value = false
  }
}

const formatTime = (date: Date) => date.toLocaleTimeString('zh-CN')

const refreshData = () => statsStore.refreshAll()

onMounted(() => {
  statsStore.refreshAll()
  refreshTimer = window.setInterval(() => statsStore.refreshAll(), 5000)
  window.addEventListener('resize', updateWindowWidth)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
  window.removeEventListener('resize', updateWindowWidth)
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

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: var(--dm-bg-header);
  box-shadow: var(--dm-shadow-card);
  z-index: 1;
  transition: background-color 0.3s ease;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.menu-btn {
  flex-shrink: 0;
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

@media (max-width: 768px) {
  .header {
    padding: 0 12px;
  }

  .breadcrumb {
    font-size: 14px;
  }

  .header-actions {
    gap: 8px;
  }

  .header-actions .el-tag {
    display: none;
  }

  .main-content {
    padding: 12px;
  }
}
</style>

<style>
.mobile-sidebar-drawer .el-drawer__body {
  padding: 0 !important;
  background-color: var(--dm-bg-sidebar);
}
</style>
