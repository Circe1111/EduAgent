import { defineStore } from 'pinia'
import { ref } from 'vue'
import { profileApi } from '@/api'

export interface StudentProfile {
  user_id: string
  knowledge_points: Record<string, number>
  overall_difficulty: number
  learning_style: string
  session_count: number
  accuracy?: number
  updated_at: string
}

export const useProfileStore = defineStore('profile', () => {
  const profile = ref<StudentProfile | null>(null)
  const loading = ref(false)

  async function fetchProfile(): Promise<void> {
    loading.value = true
    try {
      const data = await profileApi.get()
      profile.value = data
    } catch (error) {
      console.error('Failed to fetch profile:', error)
    } finally {
      loading.value = false
    }
  }

  async function updateProfile(updates: Partial<StudentProfile>): Promise<void> {
    loading.value = true
    try {
      const data = await profileApi.update(updates)
      profile.value = data
    } catch (error) {
      console.error('Failed to update profile:', error)
    } finally {
      loading.value = false
    }
  }

  return {
    profile,
    loading,
    fetchProfile,
    updateProfile,
  }
})