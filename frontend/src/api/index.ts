import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig } from 'axios'
import type { StudentProfile } from '@/stores/profile'
import type { ResourceContent } from '@/stores/resource'

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api'

const client: AxiosInstance = axios.create({
  baseURL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

client.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('eduagent_token')
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  },
)

client.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('eduagent_token')
      window.location.href = '/login'
    }
    const message = error.response?.data?.detail || error.message || '请求失败'
    return Promise.reject(new Error(message))
  },
)

export interface ChatRequest {
  message: string
  conversation_id?: string
}

export interface ChatResponse {
  message: string
  conversation_id: string
}

export interface FeedbackRequest {
  conversation_id: string
  message_id: string
  rating: number
  comment?: string
}

export interface StudyStats {
  total_minutes: number
  today_minutes: number
  total_sessions: number
  today_sessions: number
}

export interface CalendarEntry {
  study_date: string
  total_seconds: number
}

export interface StudyLogResponse {
  id: number
  duration_seconds: number
  total_today: number
}

export interface QuizQuestion {
  id: number
  question: string
  options: string[]
  correct_answer?: string
}

export interface QuizSubmitResult {
  score: number
  total: number
  results: QuizQuestionResult[]
}

export interface QuizQuestionResult {
  question_id: number
  question: string
  options: string[]
  user_answer: string
  correct_answer: string
  is_correct: boolean
}

export interface Badge {
  code: string
  name: string
  condition: string
  earned: boolean
  earned_at: string | null
}

export interface Favorite {
  id: number
  question: string
  answer: string
  node_id: number | null
  created_at: string
}

export const chatApi = {
  async sendMessage(
    content: string,
    onChunk: (chunk: string) => void,
  ): Promise<void> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }
    const token = localStorage.getItem('eduagent_token')
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const response = await fetch(`${baseURL}/chat/stream`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ message: content }),
    })

    if (!response.ok) {
      if (response.status === 401) {
        localStorage.removeItem('eduagent_token')
        window.location.href = '/login'
      }
      throw new Error('Stream request failed')
    }

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('No response body')
    }

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data === '[DONE]') return
          try {
            const parsed = JSON.parse(data)
            if (parsed.content) {
              onChunk(parsed.content)
            }
          } catch {
            onChunk(data)
          }
        }
      }
    }
  },

  async getHistory(conversationId: string): Promise<ChatResponse[]> {
    return client.get(`/chat/history/${conversationId}`)
  },
}

export const profileApi = {
  async get(): Promise<StudentProfile> {
    return client.get('/profile')
  },
  async update(updates: Partial<StudentProfile>): Promise<StudentProfile> {
    return client.put('/profile', updates)
  },
}

export const resourceApi = {
  async get(topic: string): Promise<ResourceContent> {
    return client.get(`/resource/${encodeURIComponent(topic)}`)
  },
  async generate(topic: string): Promise<ResourceContent> {
    return client.post('/resource/generate', { topic })
  },
}

export const feedbackApi = {
  async submit(data: FeedbackRequest): Promise<void> {
    return client.post('/feedback', data)
  },
}

export interface NodeProgress {
  chapter: string
  total_sessions: number
  avg_score: number
  avg_correct_rate: number
  total_problems: number
  total_minutes: number
  status: 'completed' | 'in_progress' | 'pending'
}

export interface NodeProgressResponse {
  nodes: NodeProgress[]
}

export const studyApi = {
  async getStats(): Promise<StudyStats> {
    return client.get('/v1/study/stats')
  },
  async getCalendar(days: number = 90): Promise<CalendarEntry[]> {
    return client.get(`/v1/study/calendar?days=${days}`)
  },
  async log(data: { node_id: number; duration_seconds: number }): Promise<StudyLogResponse> {
    return client.post('/v1/study/log', data)
  },
  async getNodeProgress(): Promise<NodeProgressResponse> {
    return client.get('/v1/study/node-progress')
  },
}

export const quizApi = {
  async generate(nodeId: number): Promise<QuizQuestion[]> {
    return client.post(`/v1/quiz/generate/${nodeId}`)
  },
  async submit(data: { node_id: number; answers: Record<string, string> }): Promise<QuizSubmitResult> {
    return client.post('/v1/quiz/submit', data)
  },
}

export const favoritesApi = {
  async list(): Promise<Favorite[]> {
    return client.get('/v1/favorites')
  },
  async add(data: { question: string; answer: string; node_id?: number | null }): Promise<{ id: number; created_at: string }> {
    return client.post('/v1/favorites', data)
  },
  async remove(id: number): Promise<void> {
    return client.delete(`/v1/favorites/${id}`)
  },
}

export const badgesApi = {
  async list(): Promise<Badge[]> {
    return client.get('/v1/badges')
  },
  async check(): Promise<{ newly_earned: string[] }> {
    return client.get('/v1/badges/check')
  },
}

export interface PromptTemplate {
  code: string
  title: string
  role: string
  variables: string[]
  scenario: string
  template_text: string
}

export const promptTemplatesApi = {
  async list(): Promise<PromptTemplate[]> {
    return client.get('/v1/prompt-templates')
  },
  async get(code: string): Promise<PromptTemplate> {
    return client.get(`/v1/prompt-templates/${code}`)
  },
}

export const settingsApi = {
  async changePassword(data: { old_password: string; new_password: string }): Promise<{ success: boolean }> {
    return client.put('/v1/settings/password', data)
  },
  async updateProfile(data: Record<string, unknown>): Promise<{ success: boolean }> {
    return client.put('/v1/settings/profile', data)
  },
  async clearCache(): Promise<{ success: boolean }> {
    return client.post('/v1/settings/clear-cache')
  },
  async deleteAccount(): Promise<{ success: boolean }> {
    return client.delete('/v1/settings/account')
  },
}

export default client
