<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  Guide,
  Check,
  Clock,
  Connection,
  VideoCamera,
  Document,
  EditPen,
  ArrowRight,
} from '@element-plus/icons-vue'
import { studyApi } from '@/api'
import QuizModal from '@/components/QuizModal.vue'
import { ElMessage } from 'element-plus'

interface PathNode {
  knowledge_point: string
  order: number
  resources: string[]
  estimated_time: string
  prerequisites: string[]
  status: 'completed' | 'in_progress' | 'pending'
}

interface ResourceItem {
  type: string
  name: string
  url: string
}

const BILIBILI_SEARCH = (kw: string) =>
  `https://search.bilibili.com/all?keyword=${encodeURIComponent(kw + ' Python 教程')}`

const resourceMap: Record<string, ResourceItem[]> = {
  'Python基础语法': [
    { type: 'video', name: 'Python入门教程', url: BILIBILI_SEARCH('Python入门') },
    { type: 'doc', name: 'Python官方文档', url: 'https://docs.python.org/zh-cn/3/tutorial/' },
  ],
  '变量与数据类型': [
    { type: 'video', name: '变量与数据类型讲解', url: BILIBILI_SEARCH('Python变量数据类型') },
    { type: 'quiz', name: '变量测验', url: '#' },
  ],
  '运算符与表达式': [
    { type: 'video', name: '运算符教学', url: BILIBILI_SEARCH('Python运算符') },
    { type: 'doc', name: '运算符参考', url: 'https://docs.python.org/zh-cn/3/reference/expressions.html' },
  ],
  '控制流': [
    { type: 'video', name: '条件与循环', url: BILIBILI_SEARCH('Python控制流') },
    { type: 'doc', name: '控制流参考', url: 'https://docs.python.org/zh-cn/3/tutorial/controlflow.html' },
  ],
  '字符串': [
    { type: 'video', name: '字符串操作教学', url: BILIBILI_SEARCH('Python字符串') },
    { type: 'quiz', name: '字符串练习', url: '#' },
  ],
  '列表与元组': [
    { type: 'video', name: '列表与元组详解', url: BILIBILI_SEARCH('Python列表元组') },
    { type: 'doc', name: '数据结构文档', url: 'https://docs.python.org/zh-cn/3/tutorial/datastructures.html' },
  ],
  '字典与集合': [
    { type: 'video', name: '字典与集合教学', url: BILIBILI_SEARCH('Python字典集合') },
    { type: 'quiz', name: '字典练习', url: '#' },
  ],
  '函数': [
    { type: 'video', name: '函数编程教学', url: BILIBILI_SEARCH('Python函数') },
    { type: 'doc', name: '函数文档', url: 'https://docs.python.org/zh-cn/3/tutorial/controlflow.html#defining-functions' },
  ],
  '模块与包': [
    { type: 'video', name: '模块与包教学', url: BILIBILI_SEARCH('Python模块包') },
    { type: 'doc', name: '模块文档', url: 'https://docs.python.org/zh-cn/3/tutorial/modules.html' },
  ],
  '文件操作': [
    { type: 'video', name: '文件操作教学', url: BILIBILI_SEARCH('Python文件操作') },
    { type: 'doc', name: '文件IO文档', url: 'https://docs.python.org/zh-cn/3/tutorial/inputoutput.html' },
  ],
  '异常处理': [
    { type: 'video', name: '异常处理教学', url: BILIBILI_SEARCH('Python异常处理') },
    { type: 'quiz', name: '异常处理练习', url: '#' },
  ],
  '面向对象基础': [
    { type: 'video', name: '面向对象教学', url: BILIBILI_SEARCH('Python面向对象') },
    { type: 'doc', name: '类文档', url: 'https://docs.python.org/zh-cn/3/tutorial/classes.html' },
  ],
  '继承与多态': [
    { type: 'video', name: '继承与多态教学', url: BILIBILI_SEARCH('Python继承多态') },
    { type: 'quiz', name: '继承练习', url: '#' },
  ],
  '正则表达式': [
    { type: 'video', name: '正则表达式教学', url: BILIBILI_SEARCH('Python正则表达式') },
    { type: 'doc', name: 're模块文档', url: 'https://docs.python.org/zh-cn/3/library/re.html' },
  ],
  '网络编程': [
    { type: 'video', name: '网络编程教学', url: BILIBILI_SEARCH('Python网络编程') },
    { type: 'doc', name: 'socket文档', url: 'https://docs.python.org/zh-cn/3/library/socket.html' },
  ],
  '数据库编程': [
    { type: 'video', name: '数据库编程教学', url: BILIBILI_SEARCH('Python数据库') },
    { type: 'doc', name: 'sqlite3文档', url: 'https://docs.python.org/zh-cn/3/library/sqlite3.html' },
  ],
  '图形界面': [
    { type: 'video', name: '图形界面教学', url: BILIBILI_SEARCH('Python图形界面') },
    { type: 'doc', name: 'tkinter文档', url: 'https://docs.python.org/zh-cn/3/library/tkinter.html' },
  ],
  '综合项目': [
    { type: 'video', name: '项目实战教程', url: BILIBILI_SEARCH('Python项目实战') },
    { type: 'doc', name: '项目参考', url: 'https://docs.python.org/zh-cn/3/tutorial/' },
  ],
}

const loading = ref(false)
const pathNodes = ref<PathNode[]>([])
const totalTime = ref('')

// Drawer state
const drawerVisible = ref(false)
const selectedNode = ref<PathNode | null>(null)

// Quiz modal
const quizModalVisible = ref(false)
const quizNodeId = ref(0)
const quizNodeName = ref('')

function resourceIcon(type: string): unknown {
  if (type === 'video') return VideoCamera
  if (type === 'doc') return Document
  if (type === 'quiz') return EditPen
  return Document
}

function resourceTypeLabel(type: string): string {
  if (type === 'video') return '视频'
  if (type === 'doc') return '文档'
  if (type === 'quiz') return '测验'
  return '资源'
}

function openDrawer(node: PathNode): void {
  selectedNode.value = node
  drawerVisible.value = true
}

function closeDrawer(): void {
  drawerVisible.value = false
  selectedNode.value = null
}

function getNodeResources(): ResourceItem[] {
  if (!selectedNode.value) return []
  return resourceMap[selectedNode.value.knowledge_point] || []
}

function startLearning(): void {
  if (!selectedNode.value) return
  const resources = getNodeResources()
  const quizResource = resources.find((r) => r.type === 'quiz')
  if (quizResource) {
    quizNodeId.value = selectedNode.value.order
    quizNodeName.value = selectedNode.value.knowledge_point
    quizModalVisible.value = true
  } else {
    if (resources.length > 0) {
      window.open(resources[0].url, '_blank')
    }
  }
}

async function markComplete(): Promise<void> {
  if (!selectedNode.value) return
  try {
    const { studyApi } = await import('@/api')
    await studyApi.log({ node_id: selectedNode.value.order, duration_seconds: 600 })
    selectedNode.value.status = 'completed'
    const node = pathNodes.value.find(n => n.knowledge_point === selectedNode.value!.knowledge_point)
    if (node) node.status = 'completed'
    ElMessage.success('已标记完成')
  } catch {
    ElMessage.error('标记失败')
  }
}

const CHAPTER_MAP: Record<string, { name: string; prereq: string; time: string }> = {
  '第1章-Python基础': { name: 'Python基础语法', prereq: '', time: '1h' },
  '第2章-变量与数据类型': { name: '变量与数据类型', prereq: 'Python基础语法', time: '45m' },
  '第3章-运算符与表达式': { name: '运算符与表达式', prereq: '变量与数据类型', time: '45m' },
  '第4章-流程控制': { name: '控制流', prereq: '运算符与表达式', time: '1h' },
  '第5章-字符串': { name: '字符串', prereq: '控制流', time: '45m' },
  '第6章-列表与元组': { name: '列表与元组', prereq: '字符串', time: '1h' },
  '第7章-字典与集合': { name: '字典与集合', prereq: '列表与元组', time: '1h' },
  '第8章-函数': { name: '函数', prereq: '字典与集合', time: '1h30m' },
  '第9章-模块与包': { name: '模块与包', prereq: '函数', time: '1h' },
  '第10章-文件操作': { name: '文件操作', prereq: '模块与包', time: '1h' },
  '第11章-异常处理': { name: '异常处理', prereq: '文件操作', time: '45m' },
  '第12章-面向对象基础': { name: '面向对象基础', prereq: '异常处理', time: '1h30m' },
  '第13章-继承与多态': { name: '继承与多态', prereq: '面向对象基础', time: '1h' },
  '第14章-正则表达式': { name: '正则表达式', prereq: '继承与多态', time: '45m' },
  '第15章-网络编程': { name: '网络编程', prereq: '正则表达式', time: '1h' },
  '第16章-数据库编程': { name: '数据库编程', prereq: '网络编程', time: '1h' },
  '第17章-图形界面': { name: '图形界面', prereq: '数据库编程', time: '1h' },
  '第18章-综合项目': { name: '综合项目', prereq: '图形界面', time: '2h' },
}

async function loadPath(): Promise<void> {
  loading.value = true
  try {
    const resp = await studyApi.getNodeProgress()
    const apiNodes = resp.nodes || []
    if (apiNodes.length > 0) {
      pathNodes.value = apiNodes.map(node => {
        const map = CHAPTER_MAP[node.chapter] || { name: node.chapter, prereq: '', time: '1h' }
        return {
          knowledge_point: map.name,
          order: 0,
          resources: [],
          estimated_time: map.time,
          prerequisites: map.prereq ? [map.prereq] : [],
          status: node.status as 'completed' | 'in_progress' | 'pending',
        }
      })
      pathNodes.value.forEach((node, i) => { node.order = i + 1 })
      const totalMin = apiNodes.reduce((s, n) => s + n.total_minutes, 0)
      totalTime.value = totalMin >= 60 ? `${Math.floor(totalMin / 60)}h${totalMin % 60}m` : `${totalMin}m`
    }
    // Fallback: use default nodes if no API data
    if (pathNodes.value.length === 0) {
      pathNodes.value = [
        { knowledge_point: 'Python基础语法', order: 1, resources: [], estimated_time: '1h', prerequisites: [], status: 'in_progress' },
        { knowledge_point: '变量与数据类型', order: 2, resources: [], estimated_time: '45m', prerequisites: ['Python基础语法'], status: 'pending' },
        { knowledge_point: '控制流', order: 3, resources: [], estimated_time: '1h', prerequisites: ['变量与数据类型'], status: 'pending' },
      ]
      totalTime.value = '2h45m'
    }
  } catch {
    pathNodes.value = []
  } finally {
    loading.value = false
  }
}

function nodeClass(node: PathNode): string {
  if (node.status === 'completed') return 'node-completed'
  if (node.status === 'in_progress') return 'node-active'
  return 'node-pending'
}

onMounted(loadPath)
</script>

<template>
  <div class="path-view">
    <div class="path-header">
      <h2>学习路径</h2>
      <span class="total-time" v-if="totalTime">预计总时长: {{ totalTime }}</span>
    </div>

    <el-skeleton :loading="loading" animated :count="5">
      <div class="path-timeline" v-if="pathNodes.length > 0">
        <div
          v-for="(node, index) in pathNodes"
          :key="node.order"
          class="path-node-wrapper"
        >
          <div
            class="path-node"
            :class="[nodeClass(node), { clickable: node.status !== 'completed' }]"
            @click="openDrawer(node)"
          >
            <div class="node-index">
              <el-icon v-if="node.status === 'completed'"><Check /></el-icon>
              <span v-else>{{ node.order }}</span>
            </div>
            <div class="node-body">
              <div class="node-title">{{ node.knowledge_point }}</div>
              <div class="node-meta">
                <el-tag
                  v-if="node.status === 'completed'"
                  size="small"
                  type="success"
                >
                  已完成
                </el-tag>
                <el-tag
                  v-else-if="node.status === 'in_progress'"
                  size="small"
                  type="primary"
                  effect="plain"
                >
                  进行中
                </el-tag>
                <el-tag v-else size="small" type="info" effect="plain">
                  待学习
                </el-tag>
                <span class="node-time">
                  <el-icon><Clock /></el-icon>
                  {{ node.estimated_time }}
                </span>
              </div>
              <div class="node-prereqs" v-if="node.prerequisites.length > 0">
                <el-icon><Connection /></el-icon>
                <span>前置: {{ node.prerequisites.join('、') }}</span>
              </div>
            </div>
            <div class="node-action-hint" v-if="node.status !== 'completed'">
              <el-icon><ArrowRight /></el-icon>
            </div>
          </div>
          <div class="path-connector" v-if="index < pathNodes.length - 1">
            <div class="connector-line"></div>
          </div>
        </div>
      </div>

      <el-empty v-else description="暂无学习路径" />
    </el-skeleton>

    <!-- Node Detail Drawer -->
    <el-drawer
      v-model="drawerVisible"
      :title="selectedNode?.knowledge_point || '节点详情'"
      direction="rtl"
      size="360px"
      @close="closeDrawer"
    >
      <template v-if="selectedNode">
        <div class="drawer-section">
          <h4 class="drawer-section-title">基本信息</h4>
          <div class="drawer-info-row">
            <span class="info-label">预计时间</span>
            <span class="info-value">{{ selectedNode.estimated_time }}</span>
          </div>
          <div class="drawer-info-row" v-if="selectedNode.prerequisites.length > 0">
            <span class="info-label">前置知识</span>
            <span class="info-value">{{ selectedNode.prerequisites.join('、') }}</span>
          </div>
          <div class="drawer-info-row">
            <span class="info-label">当前状态</span>
            <el-tag
              v-if="selectedNode.status === 'completed'"
              size="small"
              type="success"
            >
              已完成
            </el-tag>
            <el-tag
              v-else-if="selectedNode.status === 'in_progress'"
              size="small"
              type="primary"
              effect="plain"
            >
              进行中
            </el-tag>
            <el-tag v-else size="small" type="info" effect="plain">
              待学习
            </el-tag>
          </div>
        </div>

        <div class="drawer-section">
          <h4 class="drawer-section-title">学习资源</h4>
          <div v-if="getNodeResources().length > 0" class="resource-list">
            <div
              v-for="(item, idx) in getNodeResources()"
              :key="idx"
              class="resource-item"
            >
              <div class="resource-icon">
                <el-icon><component :is="resourceIcon(item.type)" /></el-icon>
              </div>
              <div class="resource-body">
                <a :href="item.url" class="resource-name" target="_blank">
                  {{ item.name }}
                </a>
                <span class="resource-type">{{ resourceTypeLabel(item.type) }}</span>
              </div>
            </div>
          </div>
          <el-empty
            v-else
            description="暂无资源"
            :image-size="60"
          />
        </div>

        <div class="drawer-actions">
          <el-button
            v-if="selectedNode.status !== 'completed'"
            type="primary"
            size="large"
            class="start-btn"
            @click="startLearning"
          >
            开始学习
          </el-button>
          <el-button
            v-if="selectedNode.status === 'in_progress'"
            type="success"
            size="large"
            plain
            @click="markComplete"
          >
            标记完成
          </el-button>
        </div>
      </template>
    </el-drawer>

    <!-- Quiz Modal -->
    <QuizModal
      :visible="quizModalVisible"
      :node-id="quizNodeId"
      :node-name="quizNodeName"
      @close="quizModalVisible = false"
      @complete="quizModalVisible = false"
    />
  </div>
</template>

<style scoped>
.path-view {
  max-width: 700px;
  margin: 0 auto;
  padding: 24px 20px;
}

.path-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 24px;
}

.path-header h2 {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.total-time {
  font-size: 13px;
  color: #909399;
}

.path-timeline {
  position: relative;
}

.path-node-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.path-node {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  width: 100%;
  padding: 20px;
  border-radius: 12px;
  border: 1px solid #e4e7ed;
  background: #ffffff;
  transition: all 0.2s ease;
}

.path-node.clickable {
  cursor: pointer;
}

.path-node.clickable:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  border-color: #409eff;
}

.node-completed {
  border-left: 4px solid #67c23a;
}

.node-active {
  border-left: 4px solid #409eff;
  background: #f0f7ff;
}

.node-pending {
  border-left: 4px solid #dcdfe6;
}

.node-index {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}

.node-completed .node-index {
  background: #e1f3d8;
  color: #67c23a;
}

.node-active .node-index {
  background: #d9ecff;
  color: #409eff;
}

.node-pending .node-index {
  background: #f5f7fa;
  color: #909399;
}

.node-body {
  flex: 1;
  min-width: 0;
}

.node-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.node-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.node-time {
  font-size: 13px;
  color: #909399;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.node-prereqs {
  margin-top: 8px;
  font-size: 13px;
  color: #909399;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.node-action-hint {
  display: flex;
  align-items: center;
  color: #c0c4cc;
  margin-left: 4px;
}

.path-connector {
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.connector-line {
  width: 2px;
  height: 24px;
  background: #dcdfe6;
}

/* Drawer styles */
.drawer-section {
  margin-bottom: 24px;
}

.drawer-section-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f0f0f0;
}

.drawer-info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  font-size: 14px;
}

.info-label {
  color: #909399;
}

.info-value {
  color: #303133;
  font-weight: 500;
}

.resource-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.resource-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
  transition: background 0.2s;
}

.resource-item:hover {
  background: #f5f7fa;
}

.resource-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #ecf5ff;
  color: #409eff;
  flex-shrink: 0;
}

.resource-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.resource-name {
  font-size: 14px;
  color: #409eff;
  text-decoration: none;
  font-weight: 500;
}

.resource-name:hover {
  text-decoration: underline;
}

.resource-type {
  font-size: 12px;
  color: #909399;
}

.drawer-actions {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

.start-btn {
  width: 100%;
}
</style>
