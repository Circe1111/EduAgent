<script setup lang="ts">
import { computed } from 'vue'
import { Clock, RefreshRight, Document } from '@element-plus/icons-vue'

const props = withDefaults(defineProps<{
  elapsed: number
}>(), {
  elapsed: 0,
})

const emit = defineEmits<{
  simplify: []
  retry: []
}>()

const displayTime = computed(() => Math.floor(props.elapsed))
</script>

<template>
  <div class="timeout-fallback">
    <div class="timeout-card">
      <div class="timeout-header">
        <el-icon class="timeout-icon"><Clock /></el-icon>
        <span class="timeout-title">内容生成较久，请稍候</span>
      </div>
      <div class="timeout-body">
        <span class="timeout-elapsed">已等待 {{ displayTime }} 秒</span>
        <div class="timeout-progress">
          <div class="timeout-progress-bar"></div>
        </div>
      </div>
      <div class="timeout-actions">
        <el-button
          size="small"
          @click="emit('simplify')"
        >
          <el-icon class="btn-icon"><Document /></el-icon>
          简化模式
        </el-button>
        <el-button
          size="small"
          type="primary"
          @click="emit('retry')"
        >
          <el-icon class="btn-icon"><RefreshRight /></el-icon>
          重新生成
        </el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.timeout-fallback {
  margin: 12px 0;
}

.timeout-card {
  background-color: #fdf6ec;
  border: 1px solid #f5dab1;
  border-radius: 12px;
  padding: 16px 20px;
}

.timeout-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.timeout-icon {
  font-size: 20px;
  color: #e6a23c;
}

.timeout-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.timeout-body {
  margin-bottom: 12px;
}

.timeout-elapsed {
  font-size: 13px;
  color: #909399;
  display: block;
  margin-bottom: 8px;
}

.timeout-progress {
  height: 4px;
  background-color: #f5f7fa;
  border-radius: 2px;
  overflow: hidden;
  position: relative;
}

.timeout-progress-bar {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  width: 40%;
  background-color: #e6a23c;
  border-radius: 2px;
  animation: progress-indeterminate 2s ease-in-out infinite;
}

@keyframes progress-indeterminate {
  0% {
    left: -40%;
  }
  50% {
    left: 50%;
  }
  100% {
    left: 100%;
  }
}

.timeout-actions {
  display: flex;
  gap: 12px;
}

.btn-icon {
  margin-right: 4px;
}
</style>