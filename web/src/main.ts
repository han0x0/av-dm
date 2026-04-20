import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'

// Import theme system
import './styles/theme.css'
import { useThemeStore } from './stores/theme'

const app = createApp(App)

// Register all icons
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(createPinia())

// 初始化主题（触发 store 创建，自动应用已保存的主题偏好）
useThemeStore()

app.use(router)
app.use(ElementPlus)

app.mount('#app')
