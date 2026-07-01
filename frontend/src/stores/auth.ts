import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import router from '@/router'
import client from '@/api'

export interface UserInfo {
  id: number
  username: string
  phone: string
  daily_goal: number
  total_xp: number
  created_at: string
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('eduagent_token'))
  const user = ref<UserInfo | null>(null)
  const isAuthenticated = computed(() => !!token.value)

  async function login(username: string, password: string): Promise<void> {
    const response = await fetch(
      `${import.meta.env.VITE_API_BASE_URL || '/api'}/auth/login`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      },
    )

    if (!response.ok) {
      throw new Error('用户名或密码错误')
    }

    const data = await response.json()
    token.value = data.access_token
    localStorage.setItem('eduagent_token', data.access_token)
  }

  async function register(
    username: string,
    password: string,
    phone?: string,
  ): Promise<void> {
    const response = await fetch(
      `${import.meta.env.VITE_API_BASE_URL || '/api'}/auth/register`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, phone: phone || '' }),
      },
    )

    if (!response.ok) {
      const error = await response.json().catch(() => null)
      throw new Error(error?.detail || '注册失败，请稍后重试')
    }

    const data = await response.json()
    token.value = data.access_token
    localStorage.setItem('eduagent_token', data.access_token)
  }

  function logout(): void {
    token.value = null
    user.value = null
    localStorage.removeItem('eduagent_token')
    router.push('/login')
  }

  async function fetchMe(): Promise<void> {
    if (!token.value) return
    try {
      const data = await client.get('/auth/me')
      user.value = data as unknown as UserInfo
    } catch {
      logout()
    }
  }

  function getAuthHeaders(): Record<string, string> {
    if (token.value) {
      return { Authorization: `Bearer ${token.value}` }
    }
    return {}
  }

  return {
    token,
    user,
    isAuthenticated,
    login,
    register,
    logout,
    fetchMe,
    getAuthHeaders,
  }
})
