<script setup lang="ts">
import { ref, onUnmounted, computed } from 'vue'
import { Clock, VideoPause, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { studyApi } from '@/api'

const dialogVisible = ref(false)
const totalSeconds = ref(25 * 60) // 25 minutes
const elapsedSeconds = ref(0)
const isRunning = ref(false)
const isPaused = ref(false)
const timerStartedAt = ref<number | null>(null)

let intervalId: ReturnType<typeof setInterval> | null = null

const remainingSeconds = computed(() => totalSeconds.value - elapsedSeconds.value)

const displayTime = computed(() => {
  const mins = Math.floor(remainingSeconds.value / 60)
  const secs = remainingSeconds.value % 60
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
})

const progress = computed(() => {
  if (totalSeconds.value === 0) return 0
  return (elapsedSeconds.value / totalSeconds.value) * 100
})

function startTimer() {
  if (isRunning.value) return
  if (remainingSeconds.value <= 0) {
    resetTimer()
    return
  }
  isRunning.value = true
  isPaused.value = false
  timerStartedAt.value = Date.now()
  intervalId = setInterval(tick, 1000)
}

function pauseTimer() {
  if (!isRunning.value) return
  isRunning.value = false
  isPaused.value = true
  if (intervalId) {
    clearInterval(intervalId)
    intervalId = null
  }
}

function resetTimer() {
  isRunning.value = false
  isPaused.value = false
  elapsedSeconds.value = 0
  timerStartedAt.value = null
  if (intervalId) {
    clearInterval(intervalId)
    intervalId = null
  }
}

function tick() {
  if (elapsedSeconds.value >= totalSeconds.value) {
    completeTimer()
    return
  }
  elapsedSeconds.value++
}

async function completeTimer() {
  isRunning.value = false
  if (intervalId) {
    clearInterval(intervalId)
    intervalId = null
  }
  ElMessage.success('太棒了！休息一下吧！')
  await logStudy()
  resetTimer()
}

async function cancelTimer() {
  if (!isRunning.value && !isPaused.value && elapsedSeconds.value === 0) return
  const duration = elapsedSeconds.value
  isRunning.value = false
  isPaused.value = false
  if (intervalId) {
    clearInterval(intervalId)
    intervalId = null
  }
  if (duration > 10) {
    await logStudy(duration)
  }
  resetTimer()
}

async function logStudy(duration?: number) {
  try {
    await studyApi.log({
      node_id: 0,
      duration_seconds: duration ?? totalSeconds.value,
    })
  } catch (e) {
    console.error('Failed to log study duration:', e)
  }
}

function openDialog() {
  if (isRunning.value || isPaused.value) {
    cancelTimer()
  }
  dialogVisible.value = true
}

function handleClose() {
  cancelTimer()
  dialogVisible.value = false
}

onUnmounted(() => {
  if (intervalId) {
    clearInterval(intervalId)
    intervalId = null
  }
})
</script>

<template>
  <!-- FAB button -->
  <div class="focus-fab" @click="openDialog">
    <el-button type="primary" circle size="large" class="fab-button">
      <el-icon :size="22"><Clock /></el-icon>
    </el-button>
    <span class="fab-label">专注学习</span>
  </div>

  <!-- Timer dialog -->
  <el-dialog
    v-model="dialogVisible"
    title="专注学习"
    width="360px"
    :close-on-click-modal="false"
    @close="handleClose"
    class="focus-dialog"
  >
    <div class="timer-container">
      <!-- Circular progress -->
      <div class="timer-ring">
        <svg class="ring-svg" viewBox="0 0 120 120">
          <circle
            class="ring-bg"
            cx="60"
            cy="60"
            r="54"
            fill="none"
            stroke="#e4e7ed"
            stroke-width="8"
          />
          <circle
            class="ring-progress"
            cx="60"
            cy="60"
            r="54"
            fill="none"
            stroke="#409eff"
            stroke-width="8"
            stroke-linecap="round"
            :stroke-dasharray="2 * Math.PI * 54"
            :stroke-dashoffset="2 * Math.PI * 54 * (1 - progress / 100)"
            transform="rotate(-90 60 60)"
          />
        </svg>
        <div class="timer-display">
          <div class="timer-time">{{ displayTime }}</div>
          <div class="timer-status">
            {{ isRunning ? '学习中...' : isPaused ? '已暂停' : '准备开始' }}
          </div>
        </div>
      </div>

      <!-- Controls -->
      <div class="timer-controls">
        <el-button
          v-if="!isRunning && !isPaused"
          type="primary"
          size="large"
          round
          @click="startTimer"
        >
          开始
        </el-button>
        <el-button
          v-if="isRunning"
          type="warning"
          size="large"
          round
          @click="pauseTimer"
        >
          <el-icon><VideoPause /></el-icon>
          暂停
        </el-button>
        <el-button
          v-if="isPaused"
          type="primary"
          size="large"
          round
          @click="startTimer"
        >
          继续
        </el-button>
        <el-button
          size="large"
          round
          @click="resetTimer"
          :disabled="!isPaused && !isRunning && elapsedSeconds === 0"
        >
          <el-icon><Refresh /></el-icon>
          重置
        </el-button>
      </div>

      <div class="timer-hint">
        专注学习25分钟，完成后休息一下
      </div>
    </div>
  </el-dialog>
</template>

<style scoped>
.focus-fab {
  position: fixed;
  bottom: 24px;
  right: 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  z-index: 100;
  cursor: pointer;
  user-select: none;
}

.fab-button {
  box-shadow: 0 4px 16px rgba(64, 158, 255, 0.4);
  transition: transform 0.2s, box-shadow 0.2s;
}

.fab-button:hover {
  transform: scale(1.08);
  box-shadow: 0 6px 24px rgba(64, 158, 255, 0.5);
}

.fab-label {
  font-size: 11px;
  color: #606266;
  white-space: nowrap;
}

.timer-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 0;
}

.timer-ring {
  position: relative;
  width: 200px;
  height: 200px;
  margin-bottom: 24px;
}

.ring-svg {
  width: 100%;
  height: 100%;
}

.ring-progress {
  transition: stroke-dashoffset 0.3s ease;
}

.timer-display {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
}

.timer-time {
  font-size: 40px;
  font-weight: 700;
  color: #303133;
  font-variant-numeric: tabular-nums;
  letter-spacing: 2px;
}

.timer-status {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}

.timer-controls {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.timer-hint {
  font-size: 12px;
  color: #c0c4cc;
}
</style>
