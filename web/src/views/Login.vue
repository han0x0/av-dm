<template>
  <div class="login-container">
    <el-card class="login-card" shadow="always">
      <template #header>
        <div class="login-header">
          <el-icon :size="40" color="#409EFF"><Monitor /></el-icon>
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
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock, Monitor } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
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

  console.log('登录密码长度:', form.password.length)
  
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
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 400px;
  max-width: 90%;
}

.login-header {
  text-align: center;
}

.login-header h1 {
  margin: 16px 0 8px;
  font-size: 24px;
  color: #303133;
}

.login-header p {
  color: #909399;
  font-size: 14px;
}
</style>
