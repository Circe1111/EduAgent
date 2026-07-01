<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { promptTemplatesApi } from '@/api'
import type { PromptTemplate } from '@/api'
import {
  Search,
  CopyDocument,
  Promotion,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const loading = ref(true)
const templates = ref<PromptTemplate[]>([])
const searchQuery = ref('')
const drawerVisible = ref(false)
const selectedTemplate = ref<PromptTemplate | null>(null)
const varValues = ref<Record<string, string>>({})
const filledText = ref('')

const filteredTemplates = computed(() => {
  if (!searchQuery.value.trim()) {
    return templates.value
  }
  const q = searchQuery.value.trim().toLowerCase()
  return templates.value.filter(
    (t) =>
      t.title.toLowerCase().includes(q) ||
      t.code.toLowerCase().includes(q) ||
      t.scenario.toLowerCase().includes(q),
  )
})

async function loadTemplates(): Promise<void> {
  loading.value = true
  try {
    const data = await promptTemplatesApi.list()
    templates.value = data
  } catch {
    ElMessage.error('加载Prompt模板失败')
  } finally {
    loading.value = false
  }
}

function openDetail(template: PromptTemplate): void {
  selectedTemplate.value = template
  const vars: Record<string, string> = {}
  if (template.variables && template.variables.length > 0) {
    template.variables.forEach(v => { vars[v] = '' })
  }
  varValues.value = vars
  filledText.value = ''
  drawerVisible.value = true
}

function closeDetail(): void {
  drawerVisible.value = false
  selectedTemplate.value = null
  varValues.value = {}
  filledText.value = ''
}

async function copyTemplateText(): Promise<void> {
  if (!selectedTemplate.value) return
  try {
    await navigator.clipboard.writeText(selectedTemplate.value.template_text)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败')
  }
}

function updateFilledTemplate(): void {
  if (!selectedTemplate.value) return
  let text = selectedTemplate.value.template_text
  for (const [key, val] of Object.entries(varValues.value)) {
    if (val) {
      text = text.replace(new RegExp(`\\{${key}\\}`, 'g'), val)
    }
  }
  filledText.value = text
}

async function copyFilledText(): Promise<void> {
  if (!filledText.value) return
  try {
    await navigator.clipboard.writeText(filledText.value)
    ElMessage.success('已复制填充后的模板')
  } catch {
    ElMessage.error('复制失败')
  }
}

async function sendToChat(): Promise<void> {
  if (!filledText.value) return
  const { useChatStore } = await import('@/stores/chat')
  const chatStore = useChatStore()
  chatStore.currentInput = filledText.value
  drawerVisible.value = false
  selectedTemplate.value = null
  varValues.value = {}
  filledText.value = ''
  ElMessage.success('已填入对话输入框，点击发送即可使用')
}

onMounted(loadTemplates)
</script>

<template>
  <div class="prompts-view">
    <div class="page-header">
      <div class="header-info">
        <h2>Prompt模板库</h2>
        <span class="header-count"
          >共 {{ filteredTemplates.length }} 个模板</span
        >
      </div>
      <el-input
        v-model="searchQuery"
        class="search-input"
        placeholder="搜索模板名称、编码或场景..."
        clearable
        :prefix-icon="Search"
      />
    </div>

    <el-skeleton :loading="loading" animated :count="6">
      <template #template>
        <div class="template-grid">
          <el-skeleton-item
            v-for="i in 6"
            :key="i"
            variant="card"
            style="width: 100%; height: 180px"
          />
        </div>
      </template>

      <template #default>
        <div v-if="filteredTemplates.length > 0" class="template-grid">
          <el-card
            v-for="template in filteredTemplates"
            :key="template.code"
            class="template-card"
            shadow="hover"
            @click="openDetail(template)"
          >
            <div class="card-header">
              <el-tag size="small" type="primary" effect="plain">
                {{ template.code }}
              </el-tag>
            </div>
            <h3 class="card-title">{{ template.title }}</h3>
            <div class="card-role">
              <span class="role-label">角色设定：</span>
              <span class="role-value">{{ template.role }}</span>
            </div>
            <div class="card-variables" v-if="template.variables && template.variables.length > 0">
              <el-tag
                v-for="v in template.variables"
                :key="v"
                size="small"
                type="info"
                effect="plain"
                class="var-tag"
              >
                {{ v }}
              </el-tag>
            </div>
            <div class="card-scenario">
              <span class="scenario-label">使用场景：</span>
              <span class="scenario-value">{{ template.scenario }}</span>
            </div>
          </el-card>
        </div>

        <el-empty
          v-else
          description="暂无模板"
          :image-size="80"
        />
      </template>
    </el-skeleton>

    <!-- Detail Drawer -->
    <el-drawer
      v-model="drawerVisible"
      :title="selectedTemplate?.title || 'Prompt详情'"
      direction="rtl"
      size="480px"
      @close="closeDetail"
    >
      <template v-if="selectedTemplate">
        <div class="drawer-section">
          <div class="drawer-field">
            <span class="field-label">模板编码</span>
            <el-tag size="small" type="primary" effect="plain">
              {{ selectedTemplate.code }}
            </el-tag>
          </div>
          <div class="drawer-field">
            <span class="field-label">标题</span>
            <span class="field-value">{{ selectedTemplate.title }}</span>
          </div>
          <div class="drawer-field">
            <span class="field-label">角色设定</span>
            <span class="field-value">{{ selectedTemplate.role }}</span>
          </div>
          <div class="drawer-field">
            <span class="field-label">变量</span>
            <div v-if="selectedTemplate.variables && selectedTemplate.variables.length > 0" class="var-inputs">
              <div v-for="v in selectedTemplate.variables" :key="v" class="var-input-row">
                <span class="var-input-label">{{ v }}:</span>
                <el-input
                  v-model="varValues[v]"
                  :placeholder="'输入' + v"
                  size="small"
                  class="var-input"
                  @input="updateFilledTemplate"
                />
              </div>
            </div>
            <span v-else class="field-value-none">无</span>
          </div>
          <div class="drawer-field">
            <span class="field-label">使用场景</span>
            <span class="field-value">{{ selectedTemplate.scenario }}</span>
          </div>
        </div>

        <div class="drawer-section">
          <div class="drawer-section-header">
            <h4 class="drawer-section-title">模板内容</h4>
            <el-button
              size="small"
              text
              type="primary"
              :icon="CopyDocument"
              @click="copyTemplateText"
            >
              复制原文
            </el-button>
          </div>
          <pre class="template-code"><code>{{ selectedTemplate.template_text }}</code></pre>
        </div>

        <div v-if="filledText" class="drawer-section">
          <div class="drawer-section-header">
            <h4 class="drawer-section-title">填充后内容</h4>
            <div class="drawer-actions-row">
              <el-button size="small" text type="primary" :icon="CopyDocument" @click="copyFilledText">
                复制
              </el-button>
              <el-button size="small" type="primary" :icon="Promotion" @click="sendToChat">
                发送到对话
              </el-button>
            </div>
          </div>
          <pre class="template-code filled"><code>{{ filledText }}</code></pre>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<style scoped>
.prompts-view {
  max-width: 1000px;
  margin: 0 auto;
  padding: 24px 20px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  gap: 16px;
  flex-wrap: wrap;
}

.header-info {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.header-info h2 {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary, #303133);
  margin: 0;
}

.header-count {
  font-size: 13px;
  color: var(--text-secondary, #909399);
}

.search-input {
  width: 300px;
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.template-card {
  border-radius: 12px;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.template-card:hover {
  transform: translateY(-2px);
}

.card-header {
  margin-bottom: 12px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary, #303133);
  margin: 0 0 8px;
  line-height: 1.4;
}

.card-role {
  font-size: 13px;
  color: var(--text-secondary, #606266);
  margin-bottom: 8px;
}

.role-label,
.scenario-label {
  color: var(--text-placeholder, #909399);
}

.role-value,
.scenario-value {
  color: var(--text-secondary, #606266);
}

.card-variables {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 8px;
}

.var-tag {
  margin-right: 2px;
}

.card-scenario {
  font-size: 13px;
  color: var(--text-secondary, #606266);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Drawer styles */
.drawer-section {
  margin-bottom: 24px;
}

.drawer-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-color, #f0f0f0);
}

.field-label {
  font-size: 12px;
  color: var(--text-placeholder, #909399);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.field-value {
  font-size: 14px;
  color: var(--text-primary, #303133);
}

.field-value-none {
  font-size: 14px;
  color: var(--text-placeholder, #909399);
}

.drawer-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.drawer-section-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary, #303133);
  margin: 0;
}

.template-code {
  background: var(--bg-secondary, #f5f7fa);
  border: 1px solid var(--border-color, #e4e7ed);
  border-radius: 8px;
  padding: 16px;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-primary, #303133);
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: stretch;
  }

  .search-input {
    width: 100%;
  }

  .template-grid {
    grid-template-columns: 1fr;
  }
}
</style>
