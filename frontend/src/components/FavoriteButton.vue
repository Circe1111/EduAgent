<script setup lang="ts">
import { ref } from 'vue'
import { favoritesApi } from '@/api'
import { ElMessage } from 'element-plus'

const props = withDefaults(
  defineProps<{
    question: string
    answer: string
    nodeId?: number | null
    initiallyStarred?: boolean
  }>(),
  {
    nodeId: null,
    initiallyStarred: false,
  },
)

const starred = ref(props.initiallyStarred)
const loading = ref(false)

async function toggleFavorite() {
  if (loading.value) return
  loading.value = true
  try {
    await favoritesApi.add({
      question: props.question,
      answer: props.answer,
      node_id: props.nodeId,
    })
    starred.value = !starred.value
    ElMessage.success(starred.value ? '已收藏' : '已取消收藏')
  } catch (e) {
    const msg = e instanceof Error ? e.message : '操作失败'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <el-button
    :type="starred ? 'warning' : 'default'"
    :icon="null"
    size="small"
    circle
    :loading="loading"
    class="favorite-btn"
    :class="{ starred }"
    @click.stop="toggleFavorite"
  >
    <svg
      viewBox="0 0 24 24"
      width="16"
      height="16"
      :fill="starred ? '#e6a23c' : 'none'"
      :stroke="starred ? '#e6a23c' : '#c0c4cc'"
      stroke-width="2"
    >
      <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
    </svg>
  </el-button>
</template>

<style scoped>
.favorite-btn {
  transition: all 0.2s ease;
  border: none;
}

.favorite-btn:not(.starred) {
  background: transparent;
}

.favorite-btn.starred {
  background: #fdf6ec;
  border-color: #e6a23c;
}

.favorite-btn:hover {
  transform: scale(1.15);
}
</style>
