<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  User,
  Timer,
  TrendCharts,
  Trophy,
  Calendar as CalendarIcon,
  List,
  DataAnalysis,
  Clock,
} from '@element-plus/icons-vue'
import { useProfileStore } from '@/stores/profile'
import { studyApi, badgesApi } from '@/api'
import BadgeWall from '@/components/BadgeWall.vue'
import { ElMessage } from 'element-plus'

const profileStore = useProfileStore()

// Study stats
const studyStats = ref({
  total_minutes: 0,
  today_minutes: 0,
  total_sessions: 0,
  today_sessions: 0,
})
const statsLoading = ref(true)

// Calendar data
const calendarData = ref<{ study_date: string; total_seconds: number }[]>([])
const calendarLoading = ref(false)

// Quiz history (from profile / optional endpoint)
const quizHistory = ref<{
  question: string
  user_answer: string
  correct_answer: string
  is_correct: boolean
}[]>([])
const quizHistoryLoading = ref(false)

// Active tab
const activeTab = ref('overview')

// Profile computed
const masteryList = computed(() => {
  const kp = profileStore.profile?.knowledge_points
  if (!kp || Object.keys(kp).length === 0) return []
  return Object.entries(kp)
    .map(([name, score]) => ({
      name,
      score: typeof score === 'number' ? score : parseFloat(score) || 0,
    }))
    .sort((a, b) => b.score - a.score)
})

const overallAccuracy = computed(() => {
  const acc = profileStore.profile?.accuracy ?? 0
  return typeof acc === 'number' ? acc : parseFloat(acc) || 0
})

const sessionCount = computed(() => profileStore.profile?.session_count ?? 0)
const learningStyle = computed(() => profileStore.profile?.learning_style ?? 'adaptive')
const difficultyVal = computed(() => {
  const d = profileStore.profile?.overall_difficulty ?? 0.5
  return typeof d === 'number' ? d : parseFloat(d) || 0.5
})

// Calendar heatmap
interface CalendarHeatmapCell {
  date: string
  dayOfWeek: number
  seconds: number
  weekIndex: number
}

const heatmapWeeks = computed(() => {
  const cells: CalendarHeatmapCell[] = []
  const dateMap = new Map<string, number>()
  for (const entry of calendarData.value) {
    dateMap.set(entry.study_date, entry.total_seconds)
  }

  // Generate last 90 days
  const end = new Date()
  const start = new Date()
  start.setDate(start.getDate() - 89)

  for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
    const dateStr = d.toISOString().slice(0, 10)
    const dayOfWeek = d.getDay()
    cells.push({
      date: dateStr,
      dayOfWeek,
      seconds: dateMap.get(dateStr) || 0,
      weekIndex: 0,
    })
  }

  // Group by week
  const weeks: CalendarHeatmapCell[][] = []
  let currentWeek: CalendarHeatmapCell[] = []
  for (let i = 0; i < 7; i++) {
    // Fill empty days before start
    if (i < start.getDay()) {
      currentWeek.push({
        date: '',
        dayOfWeek: i,
        seconds: 0,
        weekIndex: -1,
      })
    }
  }
  for (const cell of cells) {
    currentWeek.push(cell)
    if (currentWeek.length === 7) {
      cell.weekIndex = weeks.length
      weeks.push(currentWeek)
      currentWeek = []
    }
  }
  if (currentWeek.length > 0) {
    weeks.push(currentWeek)
  }
  return weeks
})

function heatmapColor(seconds: number): string {
  if (seconds === 0) return '#ebedf0'
  if (seconds < 600) return '#c6e48b' // < 10 min
  if (seconds < 1800) return '#7bc96f' // < 30 min
  if (seconds < 3600) return '#239a3b' // < 60 min
  return '#196127' // >= 60 min
}

function formatMinutes(seconds: number): string {
  const mins = Math.round(seconds / 60)
  if (mins < 60) return `${mins}分钟`
  const h = Math.floor(mins / 60)
  const m = mins % 60
  return m > 0 ? `${h}小时${m}分钟` : `${h}小时`
}

const weekdayLabels = ['日', '一', '二', '三', '四', '五', '六']

// Timeline
const timelineEntries = ref<
  { type: string; content: string; time: string }[]
>([])

// Score functions
function scoreColor(score: number): string {
  if (score >= 0.7) return '#67c23a'
  if (score >= 0.4) return '#e6a23c'
  return '#f56c6c'
}

function scoreLabel(score: number): string {
  if (score >= 0.8) return '熟练'
  if (score >= 0.6) return '掌握'
  if (score >= 0.4) return '了解'
  return '薄弱'
}

function difficultyLabel(d: number): string {
  if (d >= 0.7) return '进阶'
  if (d >= 0.4) return '适中'
  return '基础'
}

function styleLabel(s: string): string {
  const map: Record<string, string> = {
    advanced: '自主进阶型',
    adaptive: '均衡适应型',
    guided: '引导学习型',
  }
  return map[s] || s
}

// API calls
async function loadStats() {
  statsLoading.value = true
  try {
    const data = await studyApi.getStats()
    studyStats.value = data
  } catch (e) {
    console.error('Failed to load study stats:', e)
  } finally {
    statsLoading.value = false
  }
}

async function loadCalendar() {
  calendarLoading.value = true
  try {
    const data = await studyApi.getCalendar(90)
    calendarData.value = data
    // Build timeline from calendar
    const recent = [...data].sort(
      (a, b) => new Date(b.study_date).getTime() - new Date(a.study_date).getTime(),
    )
    timelineEntries.value = recent.slice(0, 10).map((entry) => ({
      type: 'study',
      content: `学习了 ${formatMinutes(entry.total_seconds)}`,
      time: entry.study_date,
    }))
  } catch (e) {
    console.error('Failed to load calendar:', e)
  } finally {
    calendarLoading.value = false
  }
}

async function loadQuizHistory() {
  quizHistoryLoading.value = true
  try {
    // Try fetching quiz history; fall back to profile accuracy
    const response = await fetch(
      `${import.meta.env.VITE_API_BASE_URL || '/api'}/quiz/history`,
      { headers: { Authorization: `Bearer ${localStorage.getItem('eduagent_token')}` } },
    )
    if (response.ok) {
      const data = await response.json()
      quizHistory.value = data
    }
  } catch {
    // No quiz history endpoint - leave empty
  } finally {
    quizHistoryLoading.value = false
  }
}

function handleRetryQuiz(): void {
  ElMessage.info('请在学习路径中选择节点开始测验')
}

onMounted(() => {
  profileStore.fetchProfile()
  loadStats()
  loadCalendar()
  loadQuizHistory()
})
</script>

<template>
  <div class="profile-view">
    <div class="profile-header">
      <h2>学生画像</h2>
    </div>

    <!-- Today's study highlight -->
    <div class="today-highlight" v-if="!statsLoading">
      <div class="today-number">{{ studyStats.today_minutes }}</div>
      <div class="today-label">今日已学（分钟）</div>
    </div>

    <el-skeleton :loading="statsLoading" animated>
      <div class="stats-row">
        <el-card shadow="never" class="stat-card">
          <div class="stat-value">{{ studyStats.total_sessions }}</div>
          <div class="stat-label">
            <el-icon><Timer /></el-icon>
            累计学习次数
          </div>
        </el-card>
        <el-card shadow="never" class="stat-card">
          <div class="stat-value">{{ (overallAccuracy * 100).toFixed(0) }}%</div>
          <div class="stat-label">
            <el-icon><TrendCharts /></el-icon>
            总体准确率
          </div>
        </el-card>
        <el-card shadow="never" class="stat-card">
          <div class="stat-value">{{ difficultyLabel(difficultyVal) }}</div>
          <div class="stat-label">
            <el-icon><Trophy /></el-icon>
            难度偏好 ({{ difficultyVal.toFixed(1) }})
          </div>
        </el-card>
      </div>
    </el-skeleton>

    <!-- Main tabs -->
    <el-tabs v-model="activeTab" class="profile-tabs">
      <!-- Overview tab -->
      <el-tab-pane label="学习概况" name="overview">
        <el-skeleton :loading="profileStore.loading" animated>
          <template #default>
            <div v-if="profileStore.profile">
              <!-- Learning style -->
              <el-card shadow="never" class="section-card">
                <template #header>
                  <span class="section-title">学习风格</span>
                </template>
                <div class="style-tag-wrapper">
                  <el-tag size="large" type="primary" effect="dark">
                    {{ styleLabel(learningStyle) }}
                  </el-tag>
                </div>
              </el-card>

              <!-- Knowledge mastery -->
              <el-card shadow="never" class="section-card">
                <template #header>
                  <span class="section-title">知识点掌握度</span>
                </template>
                <div v-if="masteryList.length > 0" class="mastery-list">
                  <div v-for="item in masteryList" :key="item.name" class="mastery-item">
                    <div class="mastery-header">
                      <span class="mastery-name">{{ item.name }}</span>
                      <span
                        class="mastery-score"
                        :style="{ color: scoreColor(item.score) }"
                      >
                        {{ scoreLabel(item.score) }}
                        ({{ (item.score * 100).toFixed(0) }}%)
                      </span>
                    </div>
                    <el-progress
                      :percentage="Math.round(item.score * 100)"
                      :color="scoreColor(item.score)"
                      :stroke-width="10"
                      :show-text="false"
                    />
                  </div>
                </div>
                <el-empty
                  v-else
                  description="暂无知识点数据，开始学习后将自动记录"
                  :image-size="80"
                />
              </el-card>
            </div>
          </template>
        </el-skeleton>

        <!-- Calendar heatmap -->
        <el-card shadow="never" class="section-card">
          <template #header>
            <span class="section-title">
              <el-icon><CalendarIcon /></el-icon>
              学习日历（近90天）
            </span>
          </template>
          <div class="calendar-wrapper">
            <div class="calendar-grid">
              <div class="calendar-weekdays">
                <div
                  v-for="(label, i) in weekdayLabels"
                  :key="i"
                  class="weekday-label"
                >
                  {{ label }}
                </div>
              </div>
              <div class="calendar-weeks">
                <div
                  v-for="(week, wi) in heatmapWeeks"
                  :key="wi"
                  class="calendar-week"
                >
                  <div
                    v-for="(cell, ci) in week"
                    :key="ci"
                    class="calendar-cell"
                    :style="{ backgroundColor: heatmapColor(cell.seconds) }"
                    :title="cell.date ? `${cell.date}: ${formatMinutes(cell.seconds)}` : ''"
                  />
                </div>
              </div>
            </div>
            <div class="calendar-legend">
              <span class="legend-label">少</span>
              <span
                v-for="color in ['#ebedf0', '#c6e48b', '#7bc96f', '#239a3b', '#196127']"
                :key="color"
                class="legend-cell"
                :style="{ backgroundColor: color }"
              />
              <span class="legend-label">多</span>
            </div>
          </div>
        </el-card>

        <!-- Timeline -->
        <el-card shadow="never" class="section-card">
          <template #header>
            <span class="section-title">
              <el-icon><List /></el-icon>
              近期学习记录
            </span>
          </template>
          <div v-if="timelineEntries.length > 0" class="timeline">
            <div v-for="(entry, i) in timelineEntries" :key="i" class="timeline-item">
              <div class="timeline-dot" />
              <div class="timeline-body">
                <div class="timeline-content">{{ entry.content }}</div>
                <div class="timeline-time">{{ entry.time }}</div>
              </div>
            </div>
          </div>
          <el-empty v-else description="暂无学习记录" :image-size="60" />
        </el-card>
      </el-tab-pane>

      <!-- Quiz History tab -->
      <el-tab-pane label="错题本" name="quiz">
        <el-card shadow="never" class="section-card">
          <template #header>
            <span class="section-title">测验记录</span>
          </template>
          <div v-if="quizHistory.length > 0" class="quiz-history-table">
            <el-table :data="quizHistory" stripe style="width: 100%">
              <el-table-column prop="question" label="题目" min-width="200" />
              <el-table-column prop="user_answer" label="你的答案" width="120" />
              <el-table-column prop="correct_answer" label="正确答案" width="120" />
              <el-table-column label="结果" width="80">
                <template #default="{ row }">
                  <el-tag
                    :type="row.is_correct ? 'success' : 'danger'"
                    size="small"
                  >
                    {{ row.is_correct ? '正确' : '错误' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="100">
                <template #default>
                  <el-button size="small" type="primary" link @click="handleRetryQuiz">
                    重新练习
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
          <div v-else class="quiz-empty">
            <el-empty
              description="暂无测验记录，完成测验后将在此显示错题"
              :image-size="80"
            >
              <template #image>
                <el-icon :size="64" style="color: #c0c4cc"><DataAnalysis /></el-icon>
              </template>
            </el-empty>
            <div v-if="overallAccuracy > 0" class="accuracy-summary">
              <span>当前总体准确率：</span>
              <span class="accuracy-value" :style="{ color: scoreColor(overallAccuracy) }">
                {{ (overallAccuracy * 100).toFixed(0) }}%
              </span>
            </div>
          </div>
        </el-card>
      </el-tab-pane>

      <!-- Badges tab -->
      <el-tab-pane label="成就徽章" name="badges">
        <el-card shadow="never" class="section-card">
          <template #header>
            <span class="section-title">成就徽章墙</span>
          </template>
          <BadgeWall />
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.profile-view {
  max-width: 800px;
  margin: 0 auto;
  padding: 24px 20px;
}

.profile-header h2 {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 16px;
}

.today-highlight {
  text-align: center;
  padding: 24px;
  background: linear-gradient(135deg, #ecf5ff 0%, #f0f9eb 100%);
  border-radius: 12px;
  margin-bottom: 20px;
}

.today-number {
  font-size: 48px;
  font-weight: 800;
  color: #409eff;
  line-height: 1.1;
}

.today-label {
  font-size: 14px;
  color: #606266;
  margin-top: 8px;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  text-align: center;
  border-radius: 12px;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
  line-height: 1.2;
}

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-top: 8px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.profile-tabs {
  margin-top: 8px;
}

.section-card {
  margin-bottom: 20px;
  border-radius: 12px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.style-tag-wrapper {
  display: flex;
  justify-content: center;
  padding: 12px 0;
}

.mastery-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.mastery-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.mastery-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.mastery-name {
  font-size: 14px;
  color: #303133;
  font-weight: 500;
}

.mastery-score {
  font-size: 13px;
  font-weight: 600;
}

/* Calendar heatmap */
.calendar-wrapper {
  overflow-x: auto;
  padding: 8px 0;
}

.calendar-grid {
  display: flex;
  gap: 4px;
}

.calendar-weekdays {
  display: flex;
  flex-direction: column;
  gap: 3px;
  margin-right: 4px;
}

.weekday-label {
  width: 16px;
  height: 14px;
  font-size: 10px;
  color: #909399;
  text-align: center;
  line-height: 14px;
}

.calendar-weeks {
  display: flex;
  gap: 3px;
}

.calendar-week {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.calendar-cell {
  width: 14px;
  height: 14px;
  border-radius: 2px;
  transition: all 0.15s;
}

.calendar-cell:hover {
  transform: scale(1.5);
  outline: 1px solid #606266;
  z-index: 1;
}

.calendar-legend {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 12px;
  justify-content: flex-end;
}

.legend-label {
  font-size: 11px;
  color: #909399;
}

.legend-cell {
  width: 12px;
  height: 12px;
  border-radius: 2px;
}

/* Timeline */
.timeline {
  position: relative;
  padding-left: 20px;
}

.timeline-item {
  position: relative;
  padding-bottom: 16px;
  padding-left: 16px;
}

.timeline-item:last-child {
  padding-bottom: 0;
}

.timeline-dot {
  position: absolute;
  left: -20px;
  top: 4px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #409eff;
  border: 2px solid #ecf5ff;
}

.timeline-item::before {
  content: '';
  position: absolute;
  left: -17px;
  top: 14px;
  width: 2px;
  height: calc(100% - 10px);
  background: #e4e7ed;
}

.timeline-item:last-child::before {
  display: none;
}

.timeline-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.timeline-content {
  font-size: 14px;
  color: #303133;
}

.timeline-time {
  font-size: 12px;
  color: #909399;
}

/* Quiz */
.quiz-history-table {
  width: 100%;
}

.quiz-empty {
  text-align: center;
}

.accuracy-summary {
  font-size: 14px;
  color: #606266;
  margin-top: 8px;
}

.accuracy-value {
  font-weight: 700;
  font-size: 18px;
}

@media (max-width: 600px) {
  .stats-row {
    grid-template-columns: 1fr;
  }
}
</style>
