import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUiStore = defineStore('ui', () => {
  const sidebarVisible = ref(true)
  const isOnline = ref(navigator.onLine)
  const errorMessage = ref('')

  function toggleSidebar(): void {
    sidebarVisible.value = !sidebarVisible.value
  }

  function setSidebarVisible(visible: boolean): void {
    sidebarVisible.value = visible
  }

  function showError(message: string): void {
    errorMessage.value = message
  }

  function hideError(): void {
    errorMessage.value = ''
  }

  function setOnline(status: boolean): void {
    isOnline.value = status
  }

  return {
    sidebarVisible,
    isOnline,
    errorMessage,
    toggleSidebar,
    setSidebarVisible,
    showError,
    hideError,
    setOnline,
  }
})