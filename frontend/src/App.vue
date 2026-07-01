<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import {
  ChatDotRound,
  Guide,
  User,
  Fold,
  Expand,
  Odometer,
  Star,
  Promotion,
} from '@element-plus/icons-vue'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const uiStore = useUiStore()
const auth = useAuthStore()

const isCollapse = ref(false)

const activeMenu = computed(() => route.path)

const isAuthPage = computed(
  () => route.path === '/login' || route.path === '/register',
)

const menuItems = [
  { index: '/dashboard', label: '\u9996\u9875', icon: Odometer },
  { index: '/', label: '\u5bf9\u8bdd', icon: ChatDotRound },
  { index: '/path', label: '\u5b66\u4e60\u8def\u5f84', icon: Guide },
  { index: '/profile', label: '\u5b66\u751f\u753b\u50cf', icon: User },
  { index: '/favorites', label: '\u6536\u85cf\u5939', icon: Star },
  { index: '/prompts', label: 'Prompt\u6a21\u677f', icon: Promotion },
]

function toggleSidebar() {
  isCollapse.value = !isCollapse.value
}

function toggleSidebarVisible() {
  uiStore.toggleSidebar()
}

// Theme management
type ThemeMode = 'system' | 'light' | 'dark'
let currentThemeMode: ThemeMode = 'system'
let systemThemeMedia: MediaQueryList | null = null

function handleSystemThemeChange(e: MediaQueryListEvent) {
  if (currentThemeMode === 'system') {
    document.documentElement.setAttribute('data-theme', e.matches ? 'dark' : 'light')
  }
}

function applyTheme(mode: ThemeMode): void {
  currentThemeMode = mode
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

function initTheme(): void {
  const saved = localStorage.getItem('eduagent_theme')
  if (saved === 'light' || saved === 'dark' || saved === 'system') {
    applyTheme(saved)
  } else {
    applyTheme('system')
  }
}

onMounted(() => {
  if (auth.isAuthenticated) {
    auth.fetchMe()
  }
  initTheme()
})

onBeforeUnmount(() => {
  systemThemeMedia?.removeEventListener('change', handleSystemThemeChange)
  systemThemeMedia = null
})
</script>

<template>
  <template v-if="isAuthPage">
    <router-view />
  </template>

  <template v-else>
    <el-container class="app-container">
      <el-aside
        v-if="uiStore.sidebarVisible"
        :width="isCollapse ? '64px' : '220px'"
        class="app-aside"
      >
        <div class="logo-area">
          <span v-if="!isCollapse" class="logo-text">EduAgent</span>
          <span v-else class="logo-text-mini">EA</span>
        </div>
        <el-menu
          :default-active="activeMenu"
          :collapse="isCollapse"
          router
          class="app-menu"
        >
          <el-menu-item
            v-for="item in menuItems"
            :key="item.index"
            :index="item.index"
          >
            <el-icon><component :is="item.icon" /></el-icon>
            <template #title>{{ item.label }}</template>
          </el-menu-item>
        </el-menu>
        <div class="collapse-btn" @click="toggleSidebar">
          <el-icon v-if="isCollapse"><Expand /></el-icon>
          <el-icon v-else><Fold /></el-icon>
        </div>
      </el-aside>

      <el-container class="main-container">
        <el-header class="app-header">
          <div class="header-left">
            <el-button
              text
              class="sidebar-toggle"
              @click="toggleSidebarVisible"
            >
              <el-icon><Fold v-if="uiStore.sidebarVisible" /><Expand v-else /></el-icon>
            </el-button>
            <span class="header-title">EduAgent - 个性化学习助手</span>
          </div>
          <div class="header-right">
            <router-link to="/settings">
              <el-button text>设置</el-button>
            </router-link>
          </div>
        </el-header>

        <el-main class="app-main">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </template>
</template>

<style>
/* Light theme (default) */
:root,
html[data-theme="light"] {
  --bg-primary: #ffffff;
  --bg-secondary: #f5f7fa;
  --text-primary: #303133;
  --text-secondary: #606266;
  --text-placeholder: #909399;
  --border-color: #e4e7ed;
  --card-bg: #ffffff;
  --header-bg: #ffffff;
}

/* Dark theme */
html[data-theme="dark"] {
  --bg-primary: #1a1a2e;
  --bg-secondary: #16213e;
  --text-primary: #e0e0e0;
  --text-secondary: #a0a0a0;
  --text-placeholder: #707070;
  --border-color: #2a2a4a;
  --card-bg: #16213e;
  --header-bg: #0f3460;
}

/* System preference fallback */
@media (prefers-color-scheme: dark) {
  :root {
    --bg-primary: #1a1a2e;
    --bg-secondary: #16213e;
    --text-primary: #e0e0e0;
    --text-secondary: #a0a0a0;
    --text-placeholder: #707070;
    --border-color: #2a2a4a;
    --card-bg: #16213e;
    --header-bg: #0f3460;
  }
}

body {
  background: var(--bg-primary);
  margin: 0;
}
</style>

<style scoped>
.app-container {
  height: 100vh;
  width: 100%;
}

.app-aside {
  background-color: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  overflow: hidden;
}

.logo-area {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: 1px;
}

.logo-text-mini {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

.app-menu {
  border-right: none;
  flex: 1;
}

.collapse-btn {
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  border-top: 1px solid var(--border-color);
  color: var(--text-secondary);
  flex-shrink: 0;
}

.collapse-btn:hover {
  background-color: #ecf0f5;
}

.main-container {
  flex: 1;
  overflow: hidden;
}

.app-header {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border-color);
  background-color: var(--header-bg);
  padding: 0 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.sidebar-toggle {
  padding: 4px;
}

.header-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.header-right {
  display: flex;
  align-items: center;
}

.app-main {
  padding: 0;
  overflow-y: auto;
  background-color: var(--bg-primary);
}

@media (max-width: 768px) {
  .app-aside {
    position: absolute;
    z-index: 100;
    height: 100vh;
  }
}
</style>
