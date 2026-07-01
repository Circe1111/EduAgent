import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  loading?: boolean
  error?: string
}

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'
const STREAM_ENDPOINT = `${BASE_URL}/v1/chat/stream`
const FALLBACK_ENDPOINT = `${BASE_URL}/v1/chat`
const DRAFT_KEY = 'eduagent_chat_draft'
const MAX_RETRIES = 3
const TIMEOUT_MS = 30000

let messageCounter = 0

function generateId(): string {
  messageCounter += 1
  return `msg-${Date.now()}-${messageCounter}`
}

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const currentInput = ref('')
  const isStreaming = ref(false)
  const streamError = ref<string | null>(null)
  const reconnecting = ref(false)
  const reconnectCount = ref(0)

  let abortController: AbortController | null = null
  let lastUserQuery = ''
  let lastSessionId = ''
  let lastUserId = ''

  function addMessage(role: ChatMessage['role'], content: string): ChatMessage {
    const msg: ChatMessage = {
      id: generateId(),
      role,
      content,
      timestamp: Date.now(),
    }
    messages.value.push(msg)
    return msg
  }

  function appendStreamChunk(messageId: string, chunk: string): void {
    const msg = messages.value.find((m) => m.id === messageId)
    if (msg) {
      msg.content += chunk
    }
  }

  function clearMessages(): void {
    messages.value = []
    streamError.value = null
    reconnecting.value = false
    reconnectCount.value = 0
  }

  function saveDraft(text: string): void {
    if (text.trim()) {
      localStorage.setItem(DRAFT_KEY, text)
    } else {
      localStorage.removeItem(DRAFT_KEY)
    }
  }

  function loadDraft(): string {
    return localStorage.getItem(DRAFT_KEY) || ''
  }

  function clearDraft(): void {
    localStorage.removeItem(DRAFT_KEY)
  }

  async function processSSEStream(
    response: Response,
    assistantMessageId: string,
  ): Promise<void> {
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
        if (!line.startsWith('data: ')) continue
        const data = line.slice(6)
        if (data === '[DONE]') return
        try {
          const parsed = JSON.parse(data)
          if (parsed.content) {
            appendStreamChunk(assistantMessageId, parsed.content)
          }
        } catch {
          appendStreamChunk(assistantMessageId, data)
        }
      }
    }
  }

  async function attemptStream(
    query: string,
    sessionId: string,
    userId: string,
    assistantMessageId: string,
  ): Promise<void> {
    abortController = new AbortController()
    const timeoutId = window.setTimeout(
      () => abortController?.abort(),
      TIMEOUT_MS,
    )

    try {
      const response = await fetch(STREAM_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          user_id: userId,
          query,
        }),
        signal: abortController.signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      await processSSEStream(response, assistantMessageId)
    } finally {
      clearTimeout(timeoutId)
      abortController = null
    }
  }

  async function fallbackChat(
    query: string,
    sessionId: string,
    userId: string,
    assistantMessageId: string,
  ): Promise<void> {
    const response = await fetch(FALLBACK_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        user_id: userId,
        query,
      }),
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const data = await response.json()
    const content =
      data.message || data.content || data.response || JSON.stringify(data)
    appendStreamChunk(assistantMessageId, content)
  }

  async function sendMessage(content?: string): Promise<void> {
    const text = (content ?? currentInput.value).trim()
    if (!text || isStreaming.value) return

    lastUserQuery = text
    lastSessionId = `session-${Date.now()}`
    lastUserId = 'default-user'

    addMessage('user', text)
    currentInput.value = ''
    clearDraft()

    const assistantMsg: ChatMessage = {
      id: generateId(),
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      loading: true,
    }
    messages.value.push(assistantMsg)

    isStreaming.value = true
    streamError.value = null
    reconnecting.value = false
    reconnectCount.value = 0

    let success = false
    let lastError = ''

    for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
      try {
        if (attempt > 0) {
          reconnecting.value = true
          reconnectCount.value = attempt
          await new Promise((r) => setTimeout(r, 1000 * attempt))
        }

        await attemptStream(
          lastUserQuery,
          lastSessionId,
          lastUserId,
          assistantMsg.id,
        )
        success = true
        break
      } catch (err) {
        lastError = err instanceof Error ? err.message : String(err)
        if (attempt < MAX_RETRIES - 1) {
          reconnecting.value = true
          reconnectCount.value = attempt + 1
          continue
        }
      }
    }

    reconnecting.value = false

    if (!success) {
      try {
        await fallbackChat(
          lastUserQuery,
          lastSessionId,
          lastUserId,
          assistantMsg.id,
        )
        success = true
      } catch (err) {
        lastError = err instanceof Error ? err.message : String(err)
      }
    }

    if (!success) {
      streamError.value = lastError
      const idx = messages.value.findIndex((m) => m.id === assistantMsg.id)
      if (idx !== -1) {
        messages.value[idx].error = lastError
        messages.value[idx].loading = false
      }
    }

    const idx = messages.value.findIndex((m) => m.id === assistantMsg.id)
    if (idx !== -1) {
      messages.value[idx].loading = false
    }

    isStreaming.value = false
  }

  async function retryMessage(messageId: string): Promise<void> {
    const msg = messages.value.find((m) => m.id === messageId)
    if (!msg || msg.role !== 'assistant') return

    const userMsgIdx = messages.value.findIndex((m) => m.id === messageId) - 1
    const userMsg = userMsgIdx >= 0 ? messages.value[userMsgIdx] : null
    if (!userMsg || userMsg.role !== 'user') return

    msg.content = ''
    msg.loading = true
    msg.error = undefined
    streamError.value = null

    isStreaming.value = true

    try {
      await attemptStream(userMsg.content, lastSessionId, lastUserId, msg.id)
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : String(err)
      msg.error = errMsg
      streamError.value = errMsg
    } finally {
      msg.loading = false
      isStreaming.value = false
    }
  }

  function stopStreaming(): void {
    if (abortController) {
      abortController.abort()
      abortController = null
    }
    isStreaming.value = false
    reconnecting.value = false
  }

  return {
    messages,
    currentInput,
    isStreaming,
    streamError,
    reconnecting,
    reconnectCount,
    sendMessage,
    processSSEStream,
    retryMessage,
    clearMessages,
    addMessage,
    appendStreamChunk,
    saveDraft,
    loadDraft,
    clearDraft,
    stopStreaming,
  }
})