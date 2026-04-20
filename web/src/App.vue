<template>
  <router-view v-slot="{ Component }">
    <transition name="fade" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
</template>

<script setup lang="ts">
// App root component
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans SC', sans-serif;
}

/* Smooth theme transition for color-related properties on key elements */
html, body, #app, .layout-container, .sidebar, .header, .main-content,
.el-card, .el-dialog, .el-drawer, .el-table, .el-input__wrapper,
.el-menu, .el-pagination, .el-tabs, .el-descriptions,
.stat-card, .stat-value, .stat-label, .card-header,
.disk-item, .disk-label, .disk-value,
.page-title, .text-secondary, .text-muted {
  transition: background-color 0.3s ease, border-color 0.3s ease, color 0.3s ease;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
