<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { favoritesApi } from '@/api'
import type { Favorite } from '@/api'
import { Delete, Star } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const loading = ref(true)
const favorites = ref<Favorite[]>([])

async function loadFavorites(): Promise<void> {
  loading.value = true
  try {
    const data = await favoritesApi.list()
    favorites.value = data
  } catch {
    ElMessage.error('加载收藏失败')
  } finally {
    loading.value = false
  }
}

async function removeFavorite(id: number): Promise<void> {
  try {
    await ElMessageBox.confirm(
      '确定要删除该收藏吗？',
      '确认删除',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      },
    )
    await favoritesApi.remove(id)
    favorites.value = favorites.value.filter((f) => f.id !== id)
    ElMessage.success('已删除收藏')
  } catch {
    // User cancelled or error - handled silently
  }
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${y}-${m}-${day} ${h}:${min}`
}

onMounted(loadFavorites)
</script>

<template>
  <div class="favorites-view">
    <div class="page-header">
      <h2>收藏夹</h2>
      <span class="header-count" v-if="favorites.length > 0"
        >共 {{ favorites.length }} 项</span
      >
    </div>

    <el-skeleton :loading="loading" animated :count="4">
      <template #template>
        <div class="favorites-list">
          <el-skeleton-item
            v-for="i in 4"
            :key="i"
            variant="card"
            style="width: 100%; height: 140px"
          />
        </div>
      </template>

      <template #default>
        <div v-if="favorites.length > 0" class="favorites-list">
          <el-card
            v-for="fav in favorites"
            :key="fav.id"
            class="favorite-card"
            shadow="hover"
          >
            <div class="card-content">
              <div class="card-icon">
                <el-icon :size="20" color="#e6a23c"><Star /></el-icon>
              </div>
              <div class="card-body">
                <div class="question-text">{{ fav.question }}</div>
                <div class="answer-text">{{ fav.answer }}</div>
                <div class="card-meta">
                  <span class="meta-date">{{ formatDate(fav.created_at) }}</span>
                  <el-tag
                    v-if="fav.node_id"
                    size="small"
                    type="info"
                    effect="plain"
                    class="node-tag"
                  >
                    节点 #{{ fav.node_id }}
                  </el-tag>
                </div>
              </div>
              <div class="card-actions">
                <el-button
                  text
                  type="danger"
                  :icon="Delete"
                  circle
                  @click="removeFavorite(fav.id)"
                />
              </div>
            </div>
          </el-card>
        </div>

        <el-empty
          v-else
          description="暂无收藏，在对话中点击⭐收藏"
          :image-size="80"
        >
          <template #image>
            <el-icon :size="64" color="#c0c4cc"><Star /></el-icon>
          </template>
        </el-empty>
      </template>
    </el-skeleton>
  </div>
</template>

<style scoped>
.favorites-view {
  max-width: 800px;
  margin: 0 auto;
  padding: 24px 20px;
}

.page-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 24px;
}

.page-header h2 {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary, #303133);
  margin: 0;
}

.header-count {
  font-size: 13px;
  color: var(--text-secondary, #909399);
}

.favorites-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.favorite-card {
  border-radius: 12px;
}

.card-content {
  display: flex;
  gap: 14px;
  align-items: flex-start;
}

.card-icon {
  flex-shrink: 0;
  padding-top: 2px;
}

.card-body {
  flex: 1;
  min-width: 0;
}

.question-text {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary, #303133);
  margin-bottom: 8px;
  line-height: 1.4;
}

.answer-text {
  font-size: 14px;
  color: var(--text-secondary, #606266);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 8px;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.meta-date {
  font-size: 12px;
  color: var(--text-placeholder, #909399);
}

.node-tag {
  font-size: 12px;
}

.card-actions {
  flex-shrink: 0;
  padding-top: 2px;
}
</style>
