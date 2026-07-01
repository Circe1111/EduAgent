<script setup lang="ts">
import { ref, watch } from 'vue'
import { Check, Close } from '@element-plus/icons-vue'
import { quizApi } from '@/api'
import { ElMessage } from 'element-plus'

const props = withDefaults(
  defineProps<{
    visible: boolean
    nodeId: number
    nodeName?: string
  }>(),
  { nodeName: '' },
)

const emit = defineEmits<{
  close: []
  complete: [score: number]
}>()

interface Question {
  id: number
  question: string
  options: string[]
  correct_answer?: string
}

interface ResultEntry {
  question_id: number
  question: string
  options: string[]
  user_answer: string
  correct_answer: string
  is_correct: boolean
}

const questions = ref<Question[]>([])
const loading = ref(false)
const answers = ref<Record<string, string>>({})
const submitted = ref(false)
const score = ref(0)
const total = ref(0)
const results = ref<ResultEntry[]>([])

const optionLabels = ['A', 'B', 'C', 'D']

function loadQuestions() {
  if (!props.nodeId || props.nodeId <= 0) return
  loading.value = true
  submitted.value = false
  answers.value = {}
  questions.value = []
  score.value = 0
  total.value = 0
  results.value = []

  quizApi
    .generate(props.nodeId)
    .then((data) => {
      questions.value = data.map((q, i) => ({
        ...q,
        id: q.id || i + 1,
      }))
    })
    .catch((e) => {
      const msg = e instanceof Error ? e.message : '生成题目失败'
      ElMessage.error(msg)
    })
    .finally(() => {
      loading.value = false
    })
}

async function handleSubmit() {
  // Check all answered
  const unanswered = questions.value.filter((q) => !answers.value[String(q.id)])
  if (unanswered.length > 0) {
    ElMessage.warning(`还有 ${unanswered.length} 道题未作答`)
    return
  }

  loading.value = true
  try {
    const result = await quizApi.submit({
      node_id: props.nodeId,
      answers: answers.value,
    })
    score.value = result.score
    total.value = result.total
    results.value = result.results || []
    submitted.value = true
    emit('complete', result.score)
    if (result.score < 60) {
      ElMessage.warning('得分低于60%，需要继续复习')
    } else {
      ElMessage.success(`测验完成！得分：${result.score}/${result.total}`)
    }
  } catch (e) {
    const msg = e instanceof Error ? e.message : '提交失败'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}

function handleRetry() {
  submitted.value = false
  answers.value = {}
  questions.value = []
  loadQuestions()
}

function handleClose() {
  emit('close')
}

function handleDialogClose() {
  handleClose()
}

watch(
  () => props.visible,
  (val) => {
    if (val) {
      loadQuestions()
    }
  },
)
</script>

<template>
  <el-dialog
    :model-value="visible"
    :title="nodeName ? `${nodeName} - 测验` : '测验'"
    width="640px"
    :close-on-click-modal="false"
    @close="handleDialogClose"
    class="quiz-dialog"
  >
    <!-- Loading skeleton -->
    <div v-if="loading && questions.length === 0" class="quiz-loading">
      <el-skeleton :count="3" animated>
        <template #template>
          <div class="skeleton-item">
            <el-skeleton-item variant="text" style="width: 80%; height: 18px" />
            <div style="display: flex; flex-direction: column; gap: 8px; margin-top: 12px">
              <el-skeleton-item variant="text" style="width: 60%; height: 14px" />
              <el-skeleton-item variant="text" style="width: 60%; height: 14px" />
              <el-skeleton-item variant="text" style="width: 60%; height: 14px" />
            </div>
          </div>
        </template>
      </el-skeleton>
      <div class="loading-hint">正在生成题目...</div>
    </div>

    <!-- Questions (not submitted) -->
    <div v-else-if="!submitted && questions.length > 0" class="quiz-questions">
      <div v-for="(q, idx) in questions" :key="q.id" class="question-item">
        <div class="question-header">
          <span class="question-number">{{ idx + 1 }}.</span>
          <span class="question-text">{{ q.question }}</span>
        </div>
        <div class="question-options">
          <div
            v-for="(opt, oi) in q.options"
            :key="oi"
            class="option-row"
            @click="answers[String(q.id)] = optionLabels[oi]"
          >
            <el-radio
              :model-value="answers[String(q.id)] === optionLabels[oi]"
              :label="optionLabels[oi]"
              @change="answers[String(q.id)] = optionLabels[oi]"
              size="large"
            >
              <span class="option-text">{{ optionLabels[oi] }}. {{ opt }}</span>
            </el-radio>
          </div>
        </div>
      </div>
    </div>

    <!-- Results (submitted) -->
    <div v-else-if="submitted" class="quiz-results">
      <div class="result-summary">
        <div class="result-score" :class="{ pass: score / total >= 0.6, fail: score / total < 0.6 }">
          <span class="score-number">{{ score }}</span>
          <span class="score-divider">/</span>
          <span class="score-total">{{ total }}</span>
        </div>
        <div class="result-label">
          <el-tag v-if="score / total >= 0.6" type="success" size="large" effect="dark">
            通过
          </el-tag>
          <el-tag v-else type="danger" size="large" effect="dark">
            待复习
          </el-tag>
        </div>
        <div v-if="score / total < 0.6" class="result-hint">
          得分低于60%，建议重新学习该节点内容后再次测验
        </div>
      </div>

      <div class="result-detail">
        <div
          v-for="(r, idx) in results"
          :key="r.question_id"
          class="result-item"
          :class="{ incorrect: !r.is_correct }"
        >
          <div class="result-q-header">
            <span class="result-q-num">{{ idx + 1 }}.</span>
            <span class="result-q-text">{{ r.question }}</span>
            <el-icon v-if="r.is_correct" class="result-icon correct-icon" :size="18">
              <Check />
            </el-icon>
            <el-icon v-else class="result-icon wrong-icon" :size="18">
              <Close />
            </el-icon>
          </div>
          <div class="result-options">
            <div
              v-for="(opt, oi) in r.options"
              :key="oi"
              class="result-option"
              :class="{
                'is-correct-answer': optionLabels[oi] === r.correct_answer && !r.is_correct,
                'is-user-wrong': optionLabels[oi] === r.user_answer && !r.is_correct,
                'is-correct-user': optionLabels[oi] === r.user_answer && r.is_correct,
              }"
            >
              {{ optionLabels[oi] }}. {{ opt }}
              <span
                v-if="optionLabels[oi] === r.correct_answer && !r.is_correct"
                class="correct-tag"
              >
                正确答案
              </span>
              <span
                v-if="optionLabels[oi] === r.user_answer && !r.is_correct"
                class="wrong-tag"
              >
                你的选择
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else-if="!loading" class="quiz-empty">
      <el-empty description="暂无题目数据" :image-size="80" />
    </div>

    <!-- Footer buttons -->
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">关闭</el-button>
        <el-button
          v-if="!submitted && questions.length > 0"
          type="primary"
          :loading="loading"
          @click="handleSubmit"
        >
          交卷
        </el-button>
        <el-button
          v-if="submitted"
          type="primary"
          @click="handleRetry"
        >
          重新测验
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.quiz-loading {
  padding: 20px 0;
}

.skeleton-item {
  padding: 16px 0;
}

.loading-hint {
  text-align: center;
  color: #909399;
  font-size: 14px;
  margin-top: 8px;
}

.quiz-questions {
  max-height: 400px;
  overflow-y: auto;
  padding: 4px 0;
}

.question-item {
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid #f0f0f0;
}

.question-item:last-child {
  border-bottom: none;
  margin-bottom: 0;
}

.question-header {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.question-number {
  font-weight: 700;
  color: #409eff;
  font-size: 15px;
  flex-shrink: 0;
}

.question-text {
  font-size: 15px;
  color: #303133;
  line-height: 1.5;
}

.question-options {
  margin-left: 24px;
}

.option-row {
  padding: 6px 0;
  cursor: pointer;
  border-radius: 6px;
  transition: background 0.15s;
}

.option-row:hover {
  background: #f5f7fa;
}

.option-text {
  font-size: 14px;
  color: #606266;
}

/* Results */
.quiz-results {
  max-height: 500px;
  overflow-y: auto;
}

.result-summary {
  text-align: center;
  padding: 20px;
  background: #fafafa;
  border-radius: 12px;
  margin-bottom: 20px;
}

.result-score {
  font-size: 40px;
  font-weight: 800;
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 4px;
}

.result-score.pass {
  color: #67c23a;
}

.result-score.fail {
  color: #f56c6c;
}

.score-number {
  font-size: 48px;
}

.score-divider {
  font-size: 28px;
  color: #c0c4cc;
}

.score-total {
  font-size: 28px;
  color: #909399;
}

.result-label {
  margin: 12px 0;
}

.result-hint {
  font-size: 13px;
  color: #f56c6c;
}

.result-detail {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-item {
  padding: 12px;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
}

.result-item.incorrect {
  border-color: #fde2e2;
  background: #fef0f0;
}

.result-q-header {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 8px;
}

.result-q-num {
  font-weight: 700;
  color: #409eff;
  font-size: 14px;
  flex-shrink: 0;
}

.result-q-text {
  font-size: 14px;
  color: #303133;
  flex: 1;
}

.result-icon {
  flex-shrink: 0;
}

.correct-icon {
  color: #67c23a;
}

.wrong-icon {
  color: #f56c6c;
}

.result-options {
  margin-left: 20px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.result-option {
  font-size: 13px;
  color: #606266;
  padding: 4px 8px;
  border-radius: 4px;
}

.result-option.is-correct-answer {
  background: #f0f9eb;
  color: #67c23a;
  font-weight: 500;
}

.result-option.is-user-wrong {
  background: #fef0f0;
  color: #f56c6c;
  text-decoration: line-through;
}

.result-option.is-correct-user {
  background: #f0f9eb;
  color: #67c23a;
  font-weight: 500;
}

.correct-tag {
  font-size: 11px;
  color: #67c23a;
  margin-left: 6px;
  font-weight: 600;
}

.wrong-tag {
  font-size: 11px;
  color: #f56c6c;
  margin-left: 6px;
  font-weight: 600;
}

.quiz-empty {
  padding: 20px 0;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

:deep(.el-radio__label) {
  padding-left: 4px;
}
</style>
