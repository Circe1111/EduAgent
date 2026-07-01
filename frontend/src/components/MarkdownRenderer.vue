<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, shallowRef } from 'vue'

const props = withDefaults(defineProps<{
  content: string
  loading?: boolean
}>(), {
  loading: false,
})

interface MarkdownLibs {
  marked: {
    parse: (src: string, options?: Record<string, unknown>) => string
  }
  hljs: {
    highlight: (code: string, opts: { language: string }) => { value: string }
    highlightAuto: (code: string) => { value: string }
  }
  katex: {
    renderToString: (tex: string, opts?: Record<string, unknown>) => string
  }
  mermaid: {
    initialize: (opts: Record<string, unknown>) => void
    render: (id: string, code: string) => Promise<{ svg: string }>
  }
}

const renderedHtml = ref('')
const containerRef = ref<HTMLElement | null>(null)
const libs = shallowRef<MarkdownLibs | null>(null)

let mermaidCounter = 0

async function loadLibs(): Promise<void> {
  const [markedMod, hljsMod, katexMod, mermaidMod] = await Promise.all([
    import('marked'),
    import('highlight.js'),
    import('katex'),
    import('mermaid'),
  ])

  void import('katex/dist/katex.min.css')

  const mermaidLib = (mermaidMod as any).default || mermaidMod
  mermaidLib.initialize({
    startOnLoad: false,
    theme: 'default',
    securityLevel: 'loose',
  })

  libs.value = {
    marked: (markedMod as any).default || markedMod.marked || (markedMod as any),
    hljs: (hljsMod as any).default || hljsMod,
    katex: (katexMod as any).default || katexMod,
    mermaid: (mermaidMod as any).default || mermaidMod,
  }
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function renderKatex(text: string, displayMode: boolean): string {
  if (!libs.value) return escapeHtml(text)
  try {
    return libs.value.katex.renderToString(text, {
      displayMode,
      throwOnError: false,
      errorColor: '#cc0000',
    })
  } catch {
    return escapeHtml(text)
  }
}

function processMath(html: string): string {
  const blockRegex = /\$\$([\s\S]+?)\$\$/g
  const inlineRegex = /(?<!\\)\$([^\n$]+?)(?<!\\)\$/g

  let result = html.replace(blockRegex, (_, expr: string) => {
    return renderKatex(expr.trim(), true)
  })

  result = result.replace(inlineRegex, (_, expr: string) => {
    return renderKatex(expr.trim(), false)
  })

  return result
}

function extractMermaidBlocks(html: string): {
  html: string
  blocks: { id: string; code: string }[]
} {
  const blocks: { id: string; code: string }[] = []
  const regex = /<pre><code class="language-mermaid">([\s\S]*?)<\/code><\/pre>/g

  const result = html.replace(regex, (_, code: string) => {
    const id = `mermaid-diagram-${mermaidCounter++}`
    const decoded = code
      .replace(/&amp;/g, '&')
      .replace(/&lt;/g, '<')
      .replace(/&gt;/g, '>')
      .replace(/&quot;/g, '"')
      .replace(/&#39;/g, "'")
    blocks.push({ id, code: decoded })
    return `<div id="${id}" class="mermaid-container"></div>`
  })

  return { html: result, blocks }
}

async function renderMermaidBlocks(
  blocks: { id: string; code: string }[],
): Promise<void> {
  if (!libs.value || blocks.length === 0) return

  for (const block of blocks) {
    try {
      const { svg } = await libs.value.mermaid.render(
        `mermaid-svg-${block.id}`,
        block.code,
      )
      const el = document.getElementById(block.id)
      if (el) {
        el.innerHTML = svg
      }
    } catch {
      const el = document.getElementById(block.id)
      if (el) {
        el.innerHTML = '<div class="mermaid-error">图表渲染失败</div>'
      }
    }
  }
}

function addCopyButtons(): void {
  if (!containerRef.value) return
  const codeBlocks = containerRef.value.querySelectorAll('pre > code')
  codeBlocks.forEach((codeEl) => {
    const pre = codeEl.parentElement
    if (!pre || pre.querySelector('.code-copy-btn')) return

    const btn = document.createElement('button')
    btn.className = 'code-copy-btn'
    btn.textContent = '复制'
    btn.addEventListener('click', () => {
      const text = codeEl.textContent || ''
      navigator.clipboard.writeText(text).then(() => {
        btn.textContent = '已复制'
        setTimeout(() => {
          btn.textContent = '复制'
        }, 2000)
      })
    })
    pre.appendChild(btn)
  })
}

function renderContent(): void {
  if (!libs.value || !props.content) {
    renderedHtml.value = ''
    return
  }

  const raw = props.content
  const html = libs.value.marked.parse(raw, {
    breaks: true,
    gfm: true,
  }) as string

  const withCodeHighlight = html.replace(
    /<pre><code class="language-(\w+)">([\s\S]*?)<\/code><\/pre>/g,
    (_, lang: string, code: string) => {
      const decoded = code
        .replace(/&amp;/g, '&')
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&quot;/g, '"')
        .replace(/&#39;/g, "'")
      try {
        const highlighted = libs.value!.hljs.highlight(decoded, {
          language: lang,
        }).value
        return `<pre><code class="hljs language-${lang}">${highlighted}</code></pre>`
      } catch {
        const auto = libs.value!.hljs.highlightAuto(decoded).value
        return `<pre><code class="hljs">${auto}</code></pre>`
      }
    },
  )

  const withMath = processMath(withCodeHighlight)
  const { html: withMermaid, blocks } = extractMermaidBlocks(withMath)

  const withLinks = withMermaid.replace(
    /<a /g,
    '<a target="_blank" rel="noopener noreferrer" ',
  )

  renderedHtml.value = withLinks

  requestAnimationFrame(() => {
    addCopyButtons()
    renderMermaidBlocks(blocks)
  })
}

watch(
  () => props.content,
  () => renderContent(),
)

onMounted(async () => {
  await loadLibs()
  renderContent()
})

onBeforeUnmount(() => {
  libs.value = null
})
</script>

<template>
  <div class="markdown-renderer" ref="containerRef">
    <div
      v-if="loading && !content"
      class="markdown-loading"
    >
      <span class="loading-dots">
        <span class="dot"></span>
        <span class="dot"></span>
        <span class="dot"></span>
      </span>
    </div>
    <div
      v-else
      class="markdown-body"
      v-html="renderedHtml"
    ></div>
  </div>
</template>

<style scoped>
.markdown-renderer {
  max-width: 100%;
  word-break: break-word;
}

.markdown-body {
  font-size: 14px;
  line-height: 1.7;
  color: #303133;
}

.markdown-body :deep(h1) {
  font-size: 22px;
  font-weight: 700;
  margin: 20px 0 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e4e7ed;
}

.markdown-body :deep(h2) {
  font-size: 18px;
  font-weight: 600;
  margin: 18px 0 10px;
}

.markdown-body :deep(h3) {
  font-size: 16px;
  font-weight: 600;
  margin: 16px 0 8px;
}

.markdown-body :deep(h4) {
  font-size: 15px;
  font-weight: 600;
  margin: 14px 0 6px;
}

.markdown-body :deep(h5) {
  font-size: 14px;
  font-weight: 600;
  margin: 12px 0 4px;
}

.markdown-body :deep(h6) {
  font-size: 13px;
  font-weight: 600;
  margin: 10px 0 4px;
  color: #606266;
}

.markdown-body :deep(p) {
  margin: 8px 0;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin: 8px 0;
  padding-left: 24px;
}

.markdown-body :deep(li) {
  margin: 4px 0;
}

.markdown-body :deep(ul) {
  list-style: disc;
}

.markdown-body :deep(ol) {
  list-style: decimal;
}

.markdown-body :deep(blockquote) {
  margin: 12px 0;
  padding: 8px 16px;
  border-left: 4px solid #409eff;
  background-color: #f5f7fa;
  color: #606266;
  border-radius: 0 8px 8px 0;
}

.markdown-body :deep(blockquote p) {
  margin: 4px 0;
}

.markdown-body :deep(a) {
  color: #409eff;
  text-decoration: none;
}

.markdown-body :deep(a:hover) {
  text-decoration: underline;
}

.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
  font-size: 13px;
  overflow-x: auto;
  display: block;
}

.markdown-body :deep(thead) {
  background-color: #f5f7fa;
}

.markdown-body :deep(th) {
  padding: 8px 12px;
  border: 1px solid #e4e7ed;
  font-weight: 600;
  text-align: left;
}

.markdown-body :deep(td) {
  padding: 8px 12px;
  border: 1px solid #e4e7ed;
}

.markdown-body :deep(tbody tr:nth-child(even)) {
  background-color: #fafafa;
}

.markdown-body :deep(tbody tr:nth-child(odd)) {
  background-color: #ffffff;
}

.markdown-body :deep(pre) {
  position: relative;
  background-color: #1e1e1e;
  border-radius: 8px;
  padding: 16px;
  overflow-x: auto;
  margin: 12px 0;
}

.markdown-body :deep(pre code) {
  font-size: 13px;
  font-family: 'Fira Code', 'Consolas', 'Monaco', monospace;
  color: #d4d4d4;
  background: none;
  padding: 0;
}

.markdown-body :deep(code:not(pre code)) {
  font-size: 13px;
  font-family: 'Fira Code', 'Consolas', 'Monaco', monospace;
  background-color: #f0f0f0;
  padding: 2px 6px;
  border-radius: 4px;
  color: #c62828;
}

.markdown-body :deep(.code-copy-btn) {
  position: absolute;
  top: 8px;
  right: 8px;
  padding: 4px 10px;
  font-size: 12px;
  color: #ffffff;
  background-color: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.markdown-body :deep(.code-copy-btn:hover) {
  background-color: rgba(255, 255, 255, 0.25);
}

.markdown-body :deep(.mermaid-container) {
  display: flex;
  justify-content: center;
  margin: 12px 0;
  padding: 16px;
  background-color: #f5f7fa;
  border-radius: 8px;
}

.markdown-body :deep(.mermaid-error) {
  color: #f56c6c;
  font-size: 13px;
  text-align: center;
}

.markdown-body :deep(.katex-display) {
  overflow-x: auto;
  overflow-y: hidden;
  padding: 4px 0;
}

.markdown-body :deep(.katex) {
  font-size: 1.05em;
}

.markdown-body :deep(hr) {
  border: none;
  border-top: 1px solid #e4e7ed;
  margin: 16px 0;
}

.markdown-body :deep(img) {
  max-width: 100%;
  border-radius: 8px;
}

.markdown-loading {
  display: flex;
  align-items: center;
  padding: 4px 0;
}

.loading-dots {
  display: inline-flex;
  gap: 4px;
}

.loading-dots .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: #409eff;
  animation: dot-pulse 1.4s infinite ease-in-out;
}

.loading-dots .dot:nth-child(2) {
  animation-delay: 0.2s;
}

.loading-dots .dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes dot-pulse {
  0%, 80%, 100% {
    opacity: 0.3;
    transform: scale(0.8);
  }
  40% {
    opacity: 1;
    transform: scale(1);
  }
}
</style>