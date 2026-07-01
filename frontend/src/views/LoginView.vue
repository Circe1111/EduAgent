<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'

const router = useRouter()
const auth = useAuthStore()

const username = ref('')
const password = ref('')
const loading = ref(false)

async function handleLogin(): Promise<void> {
  if (!username.value.trim()) {
    ElMessage.warning('请输入用户名')
    return
  }
  if (!password.value) {
    ElMessage.warning('请输入密码')
    return
  }

  loading.value = true
  try {
    await auth.login(username.value.trim(), password.value)
    ElMessage.success('登录成功')
    router.push('/')
  } catch (error) {
    const msg = error instanceof Error ? error.message : '登录失败'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <div class="card-header">
        <h1 class="app-title">EduAgent</h1>
        <p class="app-subtitle">个性化学习助手</p>
      </div>

      <el-form
        class="login-form"
        @submit.prevent="handleLogin"
        label-position="top"
      >
        <el-form-item label="用户名">
          <el-input
            v-model="username"
            placeholder="请输入用户名"
            :prefix-icon="User"
            size="large"
          />
        </el-form-item>

        <el-form-item label="密码">
          <el-input
            v-model="password"
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
            class="submit-btn"
            :loading="loading"
            @click="handleLogin"
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>

      <div class="form-footer">
        <span class="footer-text">没有账号？</span>
        <router-link to="/register" class="footer-link">去注册</router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 400px;
  padding: 40px;
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
}

.card-header {
  text-align: center;
  margin-bottom: 32px;
}

.app-title {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
  margin: 0 0 8px;
}

.app-subtitle {
  font-size: 14px;
  color: #909399;
  margin: 0;
}

.login-form {
  margin-bottom: 16px;
}

.login-form :deep(.el-form-item) {
  margin-bottom: 24px;
}

.login-form :deep(.el-form-item__label) {
  font-weight: 500;
  color: #606266;
}

.submit-btn {
  width: 100%;
}

.form-footer {
  text-align: center;
  font-size: 14px;
}

.footer-text {
  color: #909399;
}

.footer-link {
  color: #409eff;
  text-decoration: none;
  font-weight: 500;
}

.footer-link:hover {
  text-decoration: underline;
}
</style>
