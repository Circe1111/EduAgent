<script setup lang="ts">
import { ref, nextTick, watch, onMounted, onBeforeUnmount, computed } from 'vue'
import { useChatStore } from '@/stores/chat'
import type { ChatMessage } from '@/stores/chat'
import { Promotion, WarningFilled, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'
import StreamReconnector from '@/components/StreamReconnector.vue'
import TimeoutFallback from '@/components/TimeoutFallback.vue'
import ErrorBoundary from '@/components/ErrorBoundary.vue'

const chatStore = useChatStore()
const messageListRef = ref<HTMLElement | null>(null)
const timeoutElapsed = ref(0)
const showTimeout = ref(false)

let timeoutTimer: ReturnType<typeof setInterval> | null = null
let streamStartTime = 0

const MAX_TIMEOUT = 30

const showReconnector = computed(
  () => chatStore.reconnecting && chatStore.isStreaming,
)

function handleSend(): void {
  if (!chatStore.currentInput.trim()) return
  startTimeoutWatch()
  chatStore.sendMessage()
}

function handleKeydown(event: KeyboardEvent): void {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    handleSend()
  }
}

function handleInputChange(): void {
  chatStore.saveDraft(chatStore.currentInput)
}

function startTimeoutWatch(): void {
  stopTimeoutWatch()
  timeoutElapsed.value = 0
  showTimeout.value = false
  streamStartTime = Date.now()

  timeoutTimer = setInterval(() => {
    timeoutElapsed.value = Math.floor((Date.now() - streamStartTime) / 1000)
    if (timeoutElapsed.value >= MAX_TIMEOUT && !showTimeout.value) {
      showTimeout.value = true
    }
  }, 1000)
}

function stopTimeoutWatch(): void {
  if (timeoutTimer) {
    clearInterval(timeoutTimer)
    timeoutTimer = null
  }
  showTimeout.value = false
}

function handleSimplify(): void {
  showTimeout.value = false
  stopTimeoutWatch()
  chatStore.stopStreaming()
  chatStore.addMessage('assistant', '已切换到简化模式，请重新提问以获取简短回答。')
}

function handleTimeoutRetry(): void {
  showTimeout.value = false
  stopTimeoutWatch()
  startTimeoutWatch()
  const lastAssistant = [...chatStore.messages].reverse().find((m) => m.role === 'assistant')
  if (lastAssistant) {
    chatStore.retryMessage(lastAssistant.id)
  }
}

function handleStreamRetry(): void {
  chatStore.reconnectCount = 0
  const lastAssistant = [...chatStore.messages].reverse().find((m) => m.role === 'assistant')
  if (lastAssistant) {
    chatStore.retryMessage(lastAssistant.id)
  }
}

function handleMessageRetry(messageId: string): void {
  chatStore.retryMessage(messageId)
}

function scrollToBottom(): void {
  nextTick(() => {
    if (messageListRef.value) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight
    }
  })
}

watch(
  () => chatStore.messages.length,
  () => scrollToBottom(),
)

watch(
  () => chatStore.messages.map((m) => m.content).join(''),
  () => scrollToBottom(),
)

watch(
  () => chatStore.isStreaming,
  (streaming) => {
    if (!streaming) {
      stopTimeoutWatch()
    }
  },
)

function getAvatarText(role: ChatMessage['role']): string {
  return role === 'user' ? '我' : 'AI'
}

function getMessageClass(role: ChatMessage['role']): string {
  return role === 'user' ? 'message-user' : 'message-assistant'
}

onMounted(() => {
  const draft = chatStore.loadDraft()
  if (draft) {
    chatStore.currentInput = draft
    ElMessage({
      message: '已恢复未发送内容',
      type: 'info',
      duration: 3000,
    })
  }
})

onBeforeUnmount(() => {
  stopTimeoutWatch()
  chatStore.saveDraft(chatStore.currentInput)
})
</script>

<template>
  <div class="chat-container">
    <StreamReconnector
      :visible="showReconnector"
      :retry-count="chatStore.reconnectCount"
      :max-retries="3"
      @retry="handleStreamRetry"
    />

    <div ref="messageListRef" class="message-list">
      <template v-if="chatStore.messages.length === 0">
        <div class="empty-state">
          <div class="empty-icon">
            <el-icon :size="48"><Promotion /></el-icon>
          </div>
          <p class="empty-title">开始你的学习之旅</p>
          <p class="empty-hint">输入你的学习问题，EduAgent 将为你提供个性化解答</p>
        </div>
      </template>

      <template v-else>
        <div
          v-for="message in chatStore.messages"
          :key="message.id"
          class="message-item"
          :class="getMessageClass(message.role)"
        >
          <div class="message-avatar">
            <el-avatar :size="36">{{ getAvatarText(message.role) }}</el-avatar>
          </div>
          <div class="message-body">
            <div class="message-content">
              <div v-if="message.loading && !message.content" class="thinking-indicator">
                <span class="thinking-text">思考中</span>
                <span class="thinking-dots">
                  <span class="dot"></span>
                  <span class="dot"></span>
                  <span class="dot"></span>
                </span>
              </div>

              <template v-else-if="message.error">
                <div class="message-error">
                  <el-icon class="error-icon-inline"><WarningFilled /></el-icon>
                  <span class="error-text-inline">{{ message.error }}</span>
                  <el-button
                    size="small"
                    text
                    type="primary"
                    @click="handleMessageRetry(message.id)"
                  >
                    重试
                  </el-button>
                </div>
              </template>

              <template v-else>
                <ErrorBoundary>
                  <MarkdownRenderer
                    v-if="message.role === 'assistant'"
                    :content="message.content"
                    :loading="message.loading"
                  />
                  <span v-else>{{ message.content }}</span>
                </ErrorBoundary>
              </template>
            </div>

            <TimeoutFallback
              v-if="showTimeout && message.loading && message.role === 'assistant' && !message.content"
              :elapsed="timeoutElapsed"
              @simplify="handleSimplify"
              @retry="handleTimeoutRetry"
            />
          </div>
        </div>
      </template>
    </div>

    <div v-if="chatStore.streamError" class="stream-error-banner">
      <el-alert
        title="请求失败"
        type="error"
        show-icon
        :closable="false"
      >
        <template #default>
          <div class="error-banner-content">
            <span>{{ chatStore.streamError }}</span>
            <el-button
              size="small"
              type="danger"
              :icon="Refresh"
              @click="handleStreamRetry"
            >
              重试
            </el-button>
          </div>
        </template>
      </el-alert>
    </div>

    <div class="input-area">
      <el-input
        v-model="chatStore.currentInput"
        type="textarea"
        :rows="2"
        placeholder="输入你的学习问题..."
        resize="none"
        :disabled="chatStore.isStreaming"
        @keydown="handleKeydown"
        @input="handleInputChange"
      />
      <el-button
        type="primary"
        :icon="Promotion"
        :loading="chatStore.isStreaming"
        :disabled="!chatStore.currentInput.trim()"
        class="send-button"
        @click="handleSend"
      >
        发送
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  max-width: 900px;
  margin: 0 auto;
}

.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 24px 20px;
}

.message-item {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  align-items: flex-start;
}

.message-user {
  flex-direction: row-reverse;
}

.message-avatar {
  flex-shrink: 0;
}

.message-body {
  max-width: 70%;
}

.message-user .message-body {
  text-align: right;
}

.message-content {
  display: inline-block;
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.6;
  font-size: 14px;
  text-align: left;
  word-break: break-word;
}

.message-assistant .message-content {
  background-color: #f5f7fa;
  color: #303133;
}

.message-user .message-content {
  background-color: #409eff;
  color: #ffffff;
}

.thinking-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
}

.thinking-text {
  font-size: 14px;
  color: #909399;
}

.thinking-dots {
  display: inline-flex;
  gap: 4px;
  margin-left: 4px;
}

.thinking-dots .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: #409eff;
  animation: thinking-pulse 1.4s infinite ease-in-out;
}

.thinking-dots .dot:nth-child(2) {
  animation-delay: 0.2s;
}

.thinking-dots .dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes thinking-pulse {
  0%, 80%, 100% {
    opacity: 0.3;
    transform: scale(0.8);
  }
  40% {
    opacity: 1;
    transform: scale(1);
  }
}

.message-error {
  display: flex;
  align-items: center;
  gap: 8px;
}

.error-icon-inline {
  font-size: 16px;
  color: #f56c6c;
  flex-shrink: 0;
}

.error-text-inline {
  font-size: 13px;
  color: #f56c6c;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #909399;
}

.empty-icon {
  margin-bottom: 16px;
  color: #c0c4cc;
}

.empty-title {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #606266;
}

.empty-hint {
  font-size: 14px;
}

.stream-error-banner {
  padding: 0 20px 12px;
}

.error-banner-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.input-area {
  display: flex;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid #e4e7ed;
  background-color: #ffffff;
  align-items: flex-end;
}

.input-area :deep(.el-textarea__inner) {
  font-size: 14px;
}

.send-button {
  height: 60px;
}

@media (max-width: 768px) {
  .message-body {
    max-width: 85%;
  }
}
</style>