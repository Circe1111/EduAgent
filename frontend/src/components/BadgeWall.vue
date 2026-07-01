<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { badgesApi } from '@/api'
import type { Badge } from '@/api'

const badges = ref<Badge[]>([])
const loading = ref(false)

const defaultBadges: Badge[] = [
  { code: 'FIRST_COMPLETE', name: '破晓者', condition: '完成第一个节点学习', earned: false, earned_at: null },
  { code: 'STREAK_7', name: '连击达人', condition: '连续7天学习大于等于15分钟', earned: false, earned_at: null },
  { code: 'SCHOLAR', name: '学霸', condition: '任意3个节点测验大于等于90分', earned: false, earned_at: null },
  { code: 'SPEED_RUNNER', name: '极速先锋', condition: '单次学习超过60分钟', earned: false, earned_at: null },
  { code: 'QUIZ_MASTER', name: '测验大师', condition: '累计完成10次测验', earned: false, earned_at: null },
  { code: 'EXPLORER', name: '探索者', condition: '完成所有知识节点学习', earned: false, earned_at: null },
]

interface BadgeIcon {
  icon: string
  color: string
  gradient: string
}

function badgeInfo(code: string): BadgeIcon {
  const map: Record<string, BadgeIcon> = {
    FIRST_COMPLETE: { icon: '★', color: '#f56c6c', gradient: 'linear-gradient(135deg, #f56c6c, #e74c3c)' },
    STREAK_7: { icon: '♨', color: '#e6a23c', gradient: 'linear-gradient(135deg, #e6a23c, #f39c12)' },
    SCHOLAR: { icon: '♥', color: '#409eff', gradient: 'linear-gradient(135deg, #409eff, #2980b9)' },
    SPEED_RUNNER: { icon: '⚡', color: '#67c23a', gradient: 'linear-gradient(135deg, #67c23a, #27ae60)' },
    QUIZ_MASTER: { icon: '✦', color: '#909399', gradient: 'linear-gradient(135deg, #a0a4a8, #7f8c8d)' },
    EXPLORER: { icon: '♦', color: '#b37feb', gradient: 'linear-gradient(135deg, #b37feb, #8e44ad)' },
  }
  return map[code] || { icon: '?', color: '#909399', gradient: 'linear-gradient(135deg, #bdc3c7, #95a5a6)' }
}

async function loadBadges() {
  loading.value = true
  try {
    const data = await badgesApi.list()
    // Merge with defaults
    const earnedMap = new Map<string, Badge>()
    for (const b of data) {
      earnedMap.set(b.code, b)
    }
    badges.value = defaultBadges.map((db) => {
      const earned = earnedMap.get(db.code)
      if (earned) {
        return { ...db, earned: earned.earned, earned_at: earned.earned_at }
      }
      return db
    })
  } catch {
    // Use defaults when API unavailable
    badges.value = defaultBadges
  } finally {
    loading.value = false
  }
}

onMounted(loadBadges)
</script>

<template>
  <div class="badge-wall">
    <el-skeleton :loading="loading" animated :count="3">
      <template #template>
        <div class="skeleton-grid">
          <div v-for="i in 6" :key="i" class="skeleton-badge">
            <el-skeleton-item variant="circle" style="width: 56px; height: 56px" />
            <el-skeleton-item variant="text" style="width: 60%; height: 14px; margin-top: 8px" />
          </div>
        </div>
      </template>

      <template #default>
        <div v-if="badges.length > 0" class="badge-grid">
          <div
            v-for="badge in badges"
            :key="badge.code"
            class="badge-card"
            :class="{ earned: badge.earned, unearned: !badge.earned }"
          >
            <div
              class="badge-icon-wrapper"
              :style="{ background: badge.earned ? badgeInfo(badge.code).gradient : '#f0f0f0' }"
            >
              <span class="badge-icon-text" :class="{ earned: badge.earned }">{{ badgeInfo(badge.code).icon }}</span>
            </div>
            <div class="badge-name">{{ badge.name }}</div>
            <div class="badge-condition">{{ badge.condition }}</div>
            <div v-if="badge.earned && badge.earned_at" class="badge-earned-at">
              获得于 {{ badge.earned_at.slice(0, 10) }}
            </div>
            <div v-if="!badge.earned" class="badge-lock">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="#c0c4cc">
                <path d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1s3.1 1.39 3.1 3.1v2z" />
              </svg>
            </div>
          </div>
        </div>
        <el-empty v-else description="暂无徽章数据" :image-size="80" />
      </template>
    </el-skeleton>
  </div>
</template>

<style scoped>
.badge-wall {
  padding: 8px 0;
}

.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.skeleton-badge {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
}

.badge-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.badge-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px 12px;
  border-radius: 12px;
  border: 1px solid #e4e7ed;
  text-align: center;
  transition: all 0.25s ease;
  position: relative;
}

.badge-card.earned {
  background: #ffffff;
}

.badge-card.unearned {
  background: #fafafa;
  opacity: 0.7;
}

.badge-card.unearned:hover {
  opacity: 0.85;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.badge-card.earned:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  border-color: transparent;
}

.badge-card.earned .badge-icon-text.earned {
  filter: drop-shadow(0 0 6px currentColor);
  animation: badgePulse 3s ease-in-out infinite;
}

@keyframes badgePulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.08); opacity: 0.85; }
}

.badge-icon-wrapper {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
  transition: all 0.3s;
}

.badge-card.earned .badge-icon-wrapper {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
}

.badge-icon-text {
  font-size: 22px;
  font-weight: 800;
  color: #ffffff;
  font-family: Georgia, 'Times New Roman', serif;
}

.badge-name {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 6px;
}

.badge-condition {
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
}

.badge-earned-at {
  font-size: 11px;
  color: #67c23a;
  margin-top: 6px;
}

.badge-lock {
  position: absolute;
  top: 12px;
  right: 12px;
}

@media (max-width: 600px) {
  .badge-grid,
  .skeleton-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
