import { defineStore } from 'pinia'
import { ref } from 'vue'
import { resourceApi } from '@/api'

export interface ResourceContent {
  id: string
  title: string
  content: string
  type: 'explanation' | 'exercise' | 'summary'
  createdAt: number
}

export const useResourceStore = defineStore('resource', () => {
  const currentResource = ref<ResourceContent | null>(null)
  const resourceHistory = ref<ResourceContent[]>([])

  async function fetchResource(topic: string): Promise<void> {
    try {
      const data = await resourceApi.get(topic)
      setResource(data)
    } catch (error) {
      console.error('Failed to fetch resource:', error)
    }
  }

  function setResource(resource: ResourceContent): void {
    currentResource.value = resource
    resourceHistory.value.unshift(resource)
    if (resourceHistory.value.length > 50) {
      resourceHistory.value.pop()
    }
  }

  return {
    currentResource,
    resourceHistory,
    fetchResource,
    setResource,
  }
})