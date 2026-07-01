<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { settingsApi } from '@/api'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

const authStore = useAuthStore()
const router = useRouter()

const activeTab = ref('password')

// Password change
const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const changingPassword = ref(false)

async function handleChangePassword() {
  if (!oldPassword.value || !newPassword.value || !confirmPassword.value) {
    ElMessage.warning('请填写所有密码字段')
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  if (newPassword.value.length < 6) {
    ElMessage.warning('新密码至少6位字符')
    return
  }
  changingPassword.value = true
  try {
    await settingsApi.changePassword({
      old_password: oldPassword.value,
      new_password: newPassword.value,
    })
    ElMessage.success('密码修改成功')
    oldPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
  } catch (e) {
    const msg = e instanceof Error ? e.message : '修改失败'
    ElMessage.error(msg)
  } finally {
    changingPassword.value = false
  }
}

// Theme switching
type ThemeMode = 'system' | 'light' | 'dark'
const themeMode = ref<ThemeMode>('system')

let systemThemeMedia: MediaQueryList | null = null

function handleSystemThemeChange(e: MediaQueryListEvent) {
  if (themeMode.value === 'system') {
    document.documentElement.setAttribute('data-theme', e.matches ? 'dark' : 'light')
  }
}

function applyTheme(mode: ThemeMode): void {
  const html = document.documentElement
  if (mode === 'system') {
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    html.setAttribute('data-theme', mq.matches ? 'dark' : 'light')
    systemThemeMedia?.removeEventListener('change', handleSystemThemeChange)
    systemThemeMedia = mq
    systemThemeMedia.addEventListener('change', handleSystemThemeChange)
  } else {
    systemThemeMedia?.removeEventListener('change', handleSystemThemeChange)
    systemThemeMedia = null
    html.setAttribute('data-theme', mode)
  }
}

function loadTheme(): void {
  const saved = localStorage.getItem('eduagent_theme')
  if (saved === 'light' || saved === 'dark' || saved === 'system') {
    themeMode.value = saved
  } else {
    themeMode.value = 'system'
  }
  applyTheme(themeMode.value)
}

function handleThemeChange(mode: ThemeMode): void {
  themeMode.value = mode
  localStorage.setItem('eduagent_theme', mode)
  applyTheme(mode)
}

// Study reminders
const reminderEnabled = ref(false)
const savingReminder = ref(false)

async function handleReminderChange(val: boolean) {
  savingReminder.value = true
  try {
    await settingsApi.updateProfile({ reminder_enabled: val })
    ElMessage.success(val ? '学习提醒已开启' : '学习提醒已关闭')
  } catch (e) {
    reminderEnabled.value = !val
    const msg = e instanceof Error ? e.message : '设置失败'
    ElMessage.error(msg)
  } finally {
    savingReminder.value = false
  }
}

// Clear cache
const clearingCache = ref(false)

async function handleClearCache() {
  clearingCache.value = true
  try {
    await settingsApi.clearCache()
    localStorage.removeItem('eduagent_chat_draft')
    localStorage.removeItem('eduagent_theme')
    ElMessage.success('缓存已清除')
  } catch (e) {
    const msg = e instanceof Error ? e.message : '清除失败'
    ElMessage.error(msg)
  } finally {
    clearingCache.value = false
  }
}

// Delete account
const deletingAccount = ref(false)

async function handleDeleteAccount() {
  try {
    await ElMessageBox.confirm(
      '确定要注销账户吗？此操作不可撤销，所有数据将被永久删除。',
      '危险操作',
      {
        confirmButtonText: '确认注销',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger',
      },
    )
    deletingAccount.value = true
    await settingsApi.deleteAccount()
    ElMessage.success('账户已注销')
    authStore.logout()
    router.push('/login')
  } catch (e) {
    if (e === 'cancel' || e === 'close') return
    const msg = e instanceof Error ? e.message : '注销失败'
    ElMessage.error(msg)
  } finally {
    deletingAccount.value = false
  }
}

onMounted(() => {
  loadTheme()
})

onBeforeUnmount(() => {
  systemThemeMedia?.removeEventListener('change', handleSystemThemeChange)
  systemThemeMedia = null
})
</script>

<template>
  <div class="settings-view">
    <div class="settings-header">
      <h2>设置</h2>
    </div>

    <el-tabs v-model="activeTab" tab-position="left" class="settings-tabs">
      <!-- Change Password -->
      <el-tab-pane label="修改密码" name="password">
        <div class="tab-content">
          <h3 class="tab-title">修改密码</h3>
          <el-form label-width="120px" class="password-form">
            <el-form-item label="当前密码">
              <el-input
                v-model="oldPassword"
                type="password"
                show-password
                placeholder="输入当前密码"
              />
            </el-form-item>
            <el-form-item label="新密码">
              <el-input
                v-model="newPassword"
                type="password"
                show-password
                placeholder="输入新密码（至少6位）"
              />
            </el-form-item>
            <el-form-item label="确认新密码">
              <el-input
                v-model="confirmPassword"
                type="password"
                show-password
                placeholder="再次输入新密码"
              />
            </el-form-item>
            <el-form-item>
              <el-button
                type="primary"
                :loading="changingPassword"
                @click="handleChangePassword"
              >
                修改密码
              </el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>

      <!-- Theme -->
      <el-tab-pane label="主题切换" name="theme">
        <div class="tab-content">
          <h3 class="tab-title">主题切换</h3>
          <p class="tab-desc">选择你偏好的显示主题</p>
          <el-radio-group
            v-model="themeMode"
            @change="handleThemeChange"
            class="theme-radio-group"
          >
            <el-radio-button value="system">跟随系统</el-radio-button>
            <el-radio-button value="light">亮色</el-radio-button>
            <el-radio-button value="dark">暗色</el-radio-button>
          </el-radio-group>
          <div class="theme-preview">
            <div class="preview-card" :class="themeMode">
              <div class="preview-header">预览</div>
              <div class="preview-body">
                <div class="preview-bar preview-bar-primary"></div>
                <div class="preview-bar preview-bar-secondary"></div>
                <div class="preview-bar preview-bar-muted"></div>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- Study Reminder -->
      <el-tab-pane label="学习提醒" name="reminder">
        <div class="tab-content">
          <h3 class="tab-title">学习提醒</h3>
          <p class="tab-desc">开启后，系统将在你长时间未学习时发送提醒通知</p>
          <div class="switch-row">
            <span class="switch-label">开启学习提醒</span>
            <el-switch
              v-model="reminderEnabled"
              :loading="savingReminder"
              @change="handleReminderChange"
            />
          </div>
        </div>
      </el-tab-pane>

      <!-- Clear Cache -->
      <el-tab-pane label="清除缓存" name="cache">
        <div class="tab-content">
          <h3 class="tab-title">清除缓存</h3>
          <p class="tab-desc">清除本地缓存数据，包括聊天草稿和主题设置。此操作不会影响你的账户数据。</p>
          <el-button
            type="warning"
            :loading="clearingCache"
            @click="handleClearCache"
          >
            清除缓存
          </el-button>
        </div>
      </el-tab-pane>

      <!-- Logout -->
      <el-tab-pane label="退出登录" name="logout">
        <div class="tab-content">
          <h3 class="tab-title">切换账号</h3>
          <p class="tab-desc">退出当前账号，返回登录页面。</p>
          <el-button @click="authStore.logout(); router.push('/login')" type="warning">
            退出登录
          </el-button>
        </div>
      </el-tab-pane>

      <!-- Delete Account -->
      <el-tab-pane label="注销账户" name="account">
        <div class="tab-content">
          <h3 class="tab-title">注销账户</h3>
          <p class="tab-desc danger-desc">
            注销账户将永久删除你的所有学习数据，包括学习记录、路径、成就和设置。此操作不可撤销。
          </p>
          <el-button
            type="danger"
            :loading="deletingAccount"
            @click="handleDeleteAccount"
          >
            注销账户
          </el-button>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.settings-view {
  max-width: 800px;
  margin: 0 auto;
  padding: 24px 20px;
}

.settings-header h2 {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 24px;
}

.settings-tabs {
  min-height: 400px;
}

.tab-content {
  padding: 0 16px;
}

.tab-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 8px;
}

.tab-desc {
  font-size: 14px;
  color: var(--text-placeholder);
  margin: 0 0 24px;
  line-height: 1.6;
}

.danger-desc {
  color: #f56c6c;
}

.password-form {
  max-width: 400px;
}

.theme-radio-group {
  margin-bottom: 24px;
}

.theme-preview {
  margin-top: 16px;
}

.preview-card {
  width: 240px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  overflow: hidden;
  transition: all 0.3s;
}

.preview-card.dark {
  background: #1a1a2e;
  border-color: #2d2d44;
}

.preview-card.dark .preview-header {
  color: #e0e0e0;
  border-bottom-color: #2d2d44;
}

.preview-card.dark .preview-body {
  background: #16213e;
}

.preview-card.dark .preview-bar-primary {
  background: #409eff;
}

.preview-card.dark .preview-bar-secondary {
  background: #e6a23c;
}

.preview-card.dark .preview-bar-muted {
  background: #4a4a6a;
}

.preview-header {
  padding: 8px 12px;
  font-size: 13px;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-color);
}

.preview-body {
  padding: 12px;
  background: #fafafa;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.preview-bar {
  height: 8px;
  border-radius: 4px;
  transition: background 0.3s;
}

.preview-bar-primary {
  background: #409eff;
  width: 70%;
}

.preview-bar-secondary {
  background: #e6a23c;
  width: 50%;
}

.preview-bar-muted {
  background: #dcdfe6;
  width: 30%;
}

.switch-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 300px;
  padding: 16px 0;
}

.switch-label {
  font-size: 15px;
  color: var(--text-primary);
}
</style>
