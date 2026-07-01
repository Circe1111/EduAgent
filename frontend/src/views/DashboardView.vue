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
    return `${minutes}\u5206\u949f`
  }
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  if (mins === 0) {
    return `${hours}\u5c0f\u65f6`
  }
  return `${hours}\u5c0f\u65f6${mins}\u5206\u949f`
}

function formatSeconds(seconds: number): string {
  if (seconds < 60) {
    return `${seconds}\u79d2`
  }
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) {
    return `${minutes}\u5206\u949f`
  }
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  if (mins === 0) {
    return `${hours}\u5c0f\u65f6`
  }
  return `${hours}\u5c0f\u65f6${mins}\u5206\u949f`
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
        \u6b22\u8fce\u56de\u6765\uff0c{{ auth.user?.username || '\u7528\u6237' }}
      </h2>
      <p class="welcome-subtitle">
        \u4eca\u5929\u4e5f\u8981\u52a0\u6cb9\u5b66\u4e60\u54e6\uff01
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
                <div class="stat-label">\u4eca\u65e5\u5b66\u4e60\u65f6\u957f</div>
              </div>
            </div>
          </el-card>

          <el-card class="stat-card" shadow="hover">
            <div class="stat-content">
              <div class="stat-icon stat-icon-week">
                <el-icon :size="24"><Calendar /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ weekStudyDays }}\u5929</div>
                <div class="stat-label">\u672c\u5468\u5b66\u4e60\u5929\u6570</div>
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
                  {{ statsData.total_sessions }}\u6b21
                </div>
                <div class="stat-label">\u603b\u5b66\u4e60\u6b21\u6570</div>
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
                  {{ currentStreak }}\u5929
                </div>
                <div class="stat-label">\u5f53\u524d\u8fde\u7eed\u5929\u6570</div>
              </div>
            </div>
          </el-card>
        </div>

        <el-empty
          v-else
          description="\u6682\u65e0\u5b66\u4e60\u6570\u636e\uff0c\u5feb\u53bb\u5b66\u4e60\u5427"
          :image-size="80"
        />
      </template>
    </el-skeleton>

    <div class="section">
      <h3 class="section-title">\u5feb\u901f\u5165\u53e3</h3>
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
              <div class="action-title">\u7ee7\u7eed\u5b66\u4e60</div>
              <div class="action-desc">\u8fdb\u5165\u5bf9\u8bdd\u4e0eAI\u4e92\u52a8</div>
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
              <div class="action-title">\u67e5\u770b\u5b66\u4e60\u8def\u5f84</div>
              <div class="action-desc">\u4e86\u89e3\u4f60\u7684\u5b66\u4e60\u8ba1\u5212</div>
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
              <div class="action-title">AI\u6d4b\u9a8c</div>
              <div class="action-desc">\u901a\u8fc7\u95ee\u7b54\u68c0\u6d4b\u5b66\u4e60\u6548\u679c</div>
            </div>
          </div>
        </el-card>
      </div>
    </div>

    <div class="section">
      <h3 class="section-title">\u6700\u8fd1\u6d3b\u52a8</h3>
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
            description="\u6682\u65e0\u6d3b\u52a8\u8bb0\u5f55"
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
