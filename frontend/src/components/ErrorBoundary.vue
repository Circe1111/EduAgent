<script setup lang="ts">
import { ref, onErrorCaptured } from 'vue'
import { WarningFilled, Refresh } from '@element-plus/icons-vue'

const hasError = ref(false)
const renderKey = ref(0)

onErrorCaptured((err: unknown) => {
  hasError.value = true
  if (err instanceof Error) {
    console.error('[ErrorBoundary]', err.message)
  } else {
    console.error('[ErrorBoundary]', String(err))
  }
  return false
})

function handleRetry(): void {
  hasError.value = false
  renderKey.value += 1
}
</script>

<template>
  <div class="error-boundary">
    <div v-if="hasError" class="error-fallback">
      <el-icon class="error-icon"><WarningFilled /></el-icon>
      <span class="error-text">部分内容加载失败</span>
      <el-button
        size="small"
        type="primary"
        :icon="Refresh"
        @click="handleRetry"
      >
        重试
      </el-button>
    </div>
    <div v-else :key="renderKey" class="error-boundary-content">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.error-boundary {
  width: 100%;
}

.error-boundary-content {
  width: 100%;
}

.error-fallback {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background-color: #fef0f0;
  border: 1px solid #fbc4c4;
  border-radius: 8px;
}

.error-icon {
  font-size: 20px;
  color: #f56c6c;
  flex-shrink: 0;
}

.error-text {
  font-size: 14px;
  color: #303133;
  flex: 1;
}
</style>