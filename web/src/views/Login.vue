<template>
  <div class="login-container">
    <el-card class="login-card" shadow="always">
      <template #header>
        <div class="login-header">
          <div class="login-icon">
            <el-icon :size="48" color="var(--dm-sidebar-active-text)"><Monitor /></el-icon>
          </div>
          <h1>AV Download Manager</h1>
          <p>Web 管理控制台</p>
        </div>
      </template>
      
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        @keyup.enter="handleLogin"
      >
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            :prefix-icon="Lock"
            show-password
            size="large"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="authStore.loading"
            @click="handleLogin"
            style="width: 100%"
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>
      
      <div class="login-footer">
        <el-button
          text
          size="small"
          :icon="themeStore.isDark() ? Sunny : Moon"
          @click="themeStore.toggleTheme"
        >
          {{ themeStore.isDark() ? '浅色模式' : '深色模式' }}
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock, Monitor, Sunny, Moon } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'

const router = useRouter()
const authStore = useAuthStore()
const themeStore = useThemeStore()
const formRef = ref()

const form = reactive({
  password: '',
})

const rules = {
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 1, message: '密码不能为空', trigger: 'blur' },
  ],
}

const handleLogin = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  try {
    const success = await authStore.login(form.password)
    if (success) {
      ElMessage.success('登录成功')
      router.push('/')
    } else {
      ElMessage.error('密码错误')
    }
  } catch (error) {
    console.error('登录异常:', error)
    ElMessage.error('登录失败，请检查网络连接')
  }
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: var(--dm-login-bg);
  transition: background 0.3s ease;
}

.login-card {
  width: 420px;
  max-width: 90%;
  border-radius: 16px;
  background-color: var(--dm-bg-card);
  border-color: var(--dm-border);
  transition: background-color 0.3s ease, border-color 0.3s ease;
}

.login-card :deep(.el-card__header) {
  border-bottom-color: var(--dm-border);
  padding: 30px 20px 20px;
}

.login-header {
  text-align: center;
}

.login-icon {
  width: 80px;
  height: 80px;
  border-radius: 20px;
  background: var(--dm-gradient-blue);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.2);
}

.login-header h1 {
  margin: 0 0 8px;
  font-size: 24px;
  color: var(--dm-text-primary);
  font-weight: 700;
  transition: color 0.3s ease;
}

.login-header p {
  color: var(--dm-text-secondary);
  font-size: 14px;
  transition: color 0.3s ease;
}

.login-footer {
  text-align: center;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--dm-border);
  transition: border-color 0.3s ease;
}
</style>
