<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { studyApi } from '@/api'
import type { StudyStats, CalendarEntry } from '@/api'
import {
  Timer,
  Calendar,
  TrendCharts,
  Aim,
  ArrowRight,
} from '@element-plus/icons-vue'

const router = useRouter()
const auth = useAuthStore()

const loading = ref(true)
const statsData = ref<StudyStats | null>(null)
const calendarWeek = ref<CalendarEntry[]>([])
const calendarMonth = ref<CalendarEntry[]>([])

const weekStudyDays = ref(0)
const currentStreak = ref(0)
const recentActivity = ref<CalendarEntry[]>([])

function formatDate(date: Date): string {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

function calculateStreak(entries: CalendarEntry[]): number {
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  const todayStr = formatDate(today)
  const hasToday = entries.some(
    (e) => e.study_date === todayStr && e.total_seconds > 0,
  )

  let streak = 0
  const checkDate = new Date(today)
  if (!hasToday) {
    checkDate.setDate(checkDate.getDate() - 1)
  }

  while (true) {
    const dateStr = formatDate(checkDate)
    const entry = entries.find((e) => e.study_date === dateStr)
    if (entry && entry.total_seconds > 0) {
      streak++
      checkDate.setDate(checkDate.getDate() - 1)
    } else {
      break
    }
  }

  return streak
}

function countWeekStudyDays(entries: CalendarEntry[]): number {
  return entries.filter((e) => e.total_seconds > 0).length
}

function formatMinutes(minutes: number): string {
  if (minutes < 60) {
    return `${minutes}分钟`
  }
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  if (mins === 0) {
    return `${hours}小时`
  }
  return `${hours}小时${mins}分钟`
}

function formatSeconds(seconds: number): string {
  if (seconds < 60) {
    return `${seconds}秒`
  }
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) {
    return `${minutes}分钟`
  }
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  if (mins === 0) {
    return `${hours}小时`
  }
  return `${hours}小时${mins}分钟`
}

async function loadData(): Promise<void> {
  loading.value = true
  try {
    const [stats, weekData, monthData] = await Promise.all([
      studyApi.getStats(),
      studyApi.getCalendar(7),
      studyApi.getCalendar(30),
    ])

    statsData.value = stats
    calendarWeek.value = weekData
    calendarMonth.value = monthData

    weekStudyDays.value = countWeekStudyDays(weekData)
    currentStreak.value = calculateStreak(monthData)

    // Recent activity: last 5 entries with study time, most recent first
    const activeEntries = monthData
      .filter((e) => e.total_seconds > 0)
      .sort(
        (a, b) =>
          new Date(b.study_date).getTime() - new Date(a.study_date).getTime(),
      )
    recentActivity.value = activeEntries.slice(0, 5)
  } catch {
    // Stats load silently - dashboard shows empty state
  } finally {
    loading.value = false
  }
}

function navigateTo(path: string): void {
  router.push(path)
}

onMounted(loadData)
</script>

<template>
  <div class="dashboard-view">
    <div class="welcome-section">
      <h2 class="welcome-title">
        欢迎回来，{{ auth.user?.username || '用户' }}
      </h2>
      <p class="welcome-subtitle">
        今天也要加油学习哦！
      </p>
    </div>

    <el-skeleton :loading="loading" animated :count="1">
      <template #template>
        <div class="stats-row">
          <el-skeleton-item
            v-for="i in 4"
            :key="i"
            variant="card"
            style="width: 100%; height: 120px"
          />
        </div>
      </template>

      <template #default>
        <div class="stats-row" v-if="statsData">
          <el-card class="stat-card" shadow="hover">
            <div class="stat-content">
              <div class="stat-icon stat-icon-time">
                <el-icon :size="24"><Timer /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">
                  {{ formatMinutes(statsData.today_minutes) }}
                </div>
                <div class="stat-label">今日学习时长</div>
              </div>
            </div>
          </el-card>

          <el-card class="stat-card" shadow="hover">
            <div class="stat-content">
              <div class="stat-icon stat-icon-week">
                <el-icon :size="24"><Calendar /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ weekStudyDays }}天</div>
                <div class="stat-label">本周学习天数</div>
              </div>
            </div>
          </el-card>

          <el-card class="stat-card" shadow="hover">
            <div class="stat-content">
              <div class="stat-icon stat-icon-total">
                <el-icon :size="24"><TrendCharts /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">
                  {{ statsData.total_sessions }}次
                </div>
                <div class="stat-label">总学习次数</div>
              </div>
            </div>
          </el-card>

          <el-card class="stat-card" shadow="hover">
            <div class="stat-content">
              <div class="stat-icon stat-icon-streak">
                <el-icon :size="24"><Aim /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">
                  {{ currentStreak }}天
                </div>
                <div class="stat-label">当前连续天数</div>
              </div>
            </div>
          </el-card>
        </div>

        <el-empty
          v-else
          description="暂无学习数据，快去学习吧"
          :image-size="80"
        />
      </template>
    </el-skeleton>

    <div class="section">
      <h3 class="section-title">快速入口</h3>
      <div class="quick-actions">
        <el-card
          class="action-card"
          shadow="hover"
          @click="navigateTo('/')"
        >
          <div class="action-content">
            <div class="action-icon action-icon-primary">
              <el-icon :size="28"><ArrowRight /></el-icon>
            </div>
            <div class="action-text">
              <div class="action-title">继续学习</div>
              <div class="action-desc">进入对话与AI互动</div>
            </div>
          </div>
        </el-card>

        <el-card
          class="action-card"
          shadow="hover"
          @click="navigateTo('/path')"
        >
          <div class="action-content">
            <div class="action-icon action-icon-success">
              <el-icon :size="28"><ArrowRight /></el-icon>
            </div>
            <div class="action-text">
              <div class="action-title">查看学习路径</div>
              <div class="action-desc">了解你的学习计划</div>
            </div>
          </div>
        </el-card>

        <el-card
          class="action-card"
          shadow="hover"
          @click="navigateTo('/')"
        >
          <div class="action-content">
            <div class="action-icon action-icon-warning">
              <el-icon :size="28"><ArrowRight /></el-icon>
            </div>
            <div class="action-text">
              <div class="action-title">AI测验</div>
              <div class="action-desc">通过问答检测学习效果</div>
            </div>
          </div>
        </el-card>
      </div>
    </div>

    <div class="section">
      <h3 class="section-title">最近活动</h3>
      <el-skeleton :loading="loading" animated :count="3">
        <template #default>
          <el-card v-if="recentActivity.length > 0" shadow="never" class="activity-card">
            <div
              v-for="(entry, index) in recentActivity"
              :key="entry.study_date"
              class="activity-item"
              :class="{ 'activity-item-last': index === recentActivity.length - 1 }"
            >
              <div class="activity-dot"></div>
              <div class="activity-body">
                <span class="activity-date">{{ entry.study_date }}</span>
                <span class="activity-duration">{{
                  formatSeconds(entry.total_seconds)
                }}</span>
              </div>
            </div>
          </el-card>

          <el-empty
            v-else
            description="暂无活动记录"
            :image-size="60"
          />
        </template>
      </el-skeleton>
    </div>
  </div>
</template>

<style scoped>
.dashboard-view {
  max-width: 900px;
  margin: 0 auto;
  padding: 24px 20px;
}

.welcome-section {
  margin-bottom: 28px;
}

.welcome-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary, #303133);
  margin: 0 0 6px;
}

.welcome-subtitle {
  font-size: 14px;
  color: var(--text-secondary, #909399);
  margin: 0;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 28px;
}

.stat-card {
  border-radius: 12px;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 14px;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-icon-time {
  background: #ecf5ff;
  color: #409eff;
}

.stat-icon-week {
  background: #f0f9eb;
  color: #67c23a;
}

.stat-icon-total {
  background: #fdf6ec;
  color: #e6a23c;
}

.stat-icon-streak {
  background: #fef0f0;
  color: #f56c6c;
}

.stat-info {
  flex: 1;
  min-width: 0;
}

.stat-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary, #303133);
  line-height: 1.2;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 13px;
  color: var(--text-secondary, #909399);
}

.section {
  margin-bottom: 28px;
}

.section-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--text-primary, #303133);
  margin: 0 0 16px;
}

.quick-actions {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.action-card {
  border-radius: 12px;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.action-card:hover {
  transform: translateY(-2px);
}

.action-content {
  display: flex;
  align-items: center;
  gap: 14px;
}

.action-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.action-icon-primary {
  background: #ecf5ff;
  color: #409eff;
}

.action-icon-success {
  background: #f0f9eb;
  color: #67c23a;
}

.action-icon-warning {
  background: #fdf6ec;
  color: #e6a23c;
}

.action-text {
  flex: 1;
  min-width: 0;
}

.action-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary, #303133);
  margin-bottom: 2px;
}

.action-desc {
  font-size: 13px;
  color: var(--text-secondary, #909399);
}

.activity-card {
  border-radius: 12px;
}

.activity-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-color, #f0f0f0);
}

.activity-item-last {
  border-bottom: none;
}

.activity-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #409eff;
  flex-shrink: 0;
}

.activity-body {
  flex: 1;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.activity-date {
  font-size: 14px;
  color: var(--text-primary, #303133);
  font-weight: 500;
}

.activity-duration {
  font-size: 13px;
  color: var(--text-secondary, #909399);
}

@media (max-width: 768px) {
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }

  .quick-actions {
    grid-template-columns: 1fr;
  }
}
</style>
