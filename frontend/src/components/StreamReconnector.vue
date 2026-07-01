<script setup lang="ts">
import { computed } from 'vue'
import { WarningFilled, Refresh } from '@element-plus/icons-vue'

const props = withDefaults(defineProps<{
  visible: boolean
  retryCount: number
  maxRetries: number
}>(), {
  visible: false,
  retryCount: 0,
  maxRetries: 3,
})

const emit = defineEmits<{
  retry: []
}>()

const isFinalFailure = computed(() => props.retryCount >= props.maxRetries)

const statusText = computed(() => {
  if (isFinalFailure.value) {
    return '连接失败'
  }
  return `连接中断，正在重连... 第 ${props.retryCount}/${props.maxRetries} 次`
})
</script>

<template>
  <Transition name="slide-down">
    <div v-if="visible" class="stream-reconnector">
      <div class="reconnector-content">
        <el-icon class="reconnector-icon" :class="{ 'icon-failed': isFinalFailure }">
          <WarningFilled v-if="isFinalFailure" />
          <Refresh v-else />
        </el-icon>
        <span class="reconnector-text">{{ statusText }}</span>
        <el-button
          v-if="isFinalFailure"
          size="small"
          type="primary"
          @click="emit('retry')"
        >
          手动重试
        </el-button>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.stream-reconnector {
  position: fixed;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  z-index: 2000;
  background-color: #fdf6ec;
  border: 1px solid #f5dab1;
  border-top: none;
  border-radius: 0 0 12px 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  min-width: 320px;
  max-width: 90%;
}

.reconnector-content {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
}

.reconnector-icon {
  font-size: 20px;
  color: #e6a23c;
  animation: pulse-icon 1.5s ease-in-out infinite;
}

.reconnector-icon.icon-failed {
  color: #f56c6c;
  animation: none;
}

.reconnector-text {
  font-size: 14px;
  color: #303133;
  flex: 1;
}

@keyframes pulse-icon {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.6;
    transform: scale(1.15);
  }
}

.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.3s ease;
}

.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-100%);
}
</style>