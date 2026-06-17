<script setup>
import { ref, onMounted, computed, watch, nextTick } from "vue"
import { useRoute } from "vue-router"
import { ElMessage, ElMessageBox } from "element-plus"
import { apiGet, apiPost } from "../api/index.js"

const route = useRoute()
const book = ref({})
const chapters = ref([])
const outlines = ref([])
const volumes = ref([])
const writing = ref(false)
const regenerating = ref(null)
const activeVolId = ref(null)
const generatingBatch = ref(false)
const batchProgress = ref({ done: 0, total: 0, current: 0, phase: 'generating' })
const showGenerateDialog = ref(false)
const generateLog = ref([])
const generateErrors = ref([])
const streamingContent = ref("")
const streamingChapter = ref(0)
const streamingPreviewRef = ref(null)
const showChapterDialog = ref(false)
const expandedChapters = ref(new Set())
const chapterPage = ref(1)
const chapterPageSize = 10
const dialogChapter = ref(null)
const dialogLoading = ref(false)
const editContent = ref("")
const editTitle = ref("")
const savingChapter = ref(false)
// 字数计算：和后端一致，去掉空格和换行
const dialogWordCount = computed(() => {
  if (!editContent.value) return 0
  return editContent.value.replace(/\s/g, '').length
})

// 流式内容自动滚动
watch(streamingContent, () => {
  nextTick(() => {
    if (streamingPreviewRef.value) {
      streamingPreviewRef.value.scrollTop = streamingPreviewRef.value.scrollHeight
    }
  })
})

async function load() {
  try {
    const [ch, ol, vl, bk] = await Promise.all([
      apiGet(`/books/${route.params.bookId}/chapters`),
      apiGet(`/books/${route.params.bookId}/outlines`),
      apiGet(`/books/${route.params.bookId}/volumes`),
      apiGet(`/books/${route.params.bookId}`),
    ])
    chapters.value = ch || []
    outlines.value = ol || []
    volumes.value = vl || []
    book.value = bk || {}
    if (route.query.vol) activeVolId.value = Number(route.query.vol)
    if (!activeVolId.value && volumes.value.length > 0) {
      const vol = volumes.value.find(v => outlines.value.some(o => o.volume_id === v.id))
      activeVolId.value = (vol || volumes.value[0]).id
    }
  } catch (e) { ElMessage.error("加载失败: " + e.message) }
}
onMounted(load)

const activeVol = computed(() => volumes.value.find(v => v.id === activeVolId.value))
const activeOutlines = computed(() => {
  if (!activeVolId.value) return outlines.value.filter(o => !o.volume_id)
  return outlines.value.filter(o => o.volume_id === activeVolId.value).sort((a, b) => a.chapter_number - b.chapter_number)
})
const activeChapters = computed(() => {
  const nums = new Set(activeOutlines.value.map(o => o.chapter_number))
  return chapters.value.filter(ch => nums.has(ch.chapter_number)).sort((a, b) => b.chapter_number - a.chapter_number)
})
const activeWordCount = computed(() => activeChapters.value.reduce((s, c) => s + (c.word_count || 0), 0))

// 可见章节（分页）
const visibleChapters = computed(() => {
  const start = (chapterPage.value - 1) * chapterPageSize
  return activeChapters.value.slice(start, start + chapterPageSize)
})

// 细纲展开/收起
function toggleOutline(chId) {
  if (expandedChapters.value.has(chId)) {
    expandedChapters.value.delete(chId)
  } else {
    expandedChapters.value.add(chId)
  }
}

// 获取某章的细纲数据
function outlineForChapter(chNum) {
  return activeOutlines.value.find(o => o.chapter_number === chNum)
}

const volProgress = computed(() => {
  const total = activeOutlines.value.length
  const done = activeChapters.value.length
  return { total, done, remaining: Math.max(0, total - done) }
})

// ── 伏笔池（仅从细纲中提取，不从设定阶段生成） ──
const foreshadowingPool = computed(() => {
  const writtenNums = new Set(activeChapters.value.map(c => c.chapter_number))
  const items = []

  for (const ol of activeOutlines.value) {
    const ch = ol.chapter_number
    const written = writtenNums.has(ch)
    // 埋伏笔 - 细纲中每章就是一条，不拆分
    if (ol.foreshadowing && ol.foreshadowing.trim()) {
      items.push({ text: ol.foreshadowing.trim(), plantedAt: ch, resolvedAt: null, written })
    }
    // 收伏笔
    if (ol.foreshadowing_payoff && ol.foreshadowing_payoff.trim()) {
      const payText = ol.foreshadowing_payoff.trim()
      const idx = items.findIndex(it => it.resolvedAt === null && (it.text.includes(payText) || payText.includes(it.text)))
      if (idx >= 0) {
        items[idx].resolvedAt = ch
        items[idx].resolvedWritten = written
      } else {
        items.push({ text: payText, plantedAt: null, resolvedAt: ch, written, resolvedWritten: written })
      }
    }
  }
  return items
})
// 未埋：细纲规划了伏笔但对应章节还没写正文
const unplantedFS = computed(() => foreshadowingPool.value.filter(f => f.plantedAt && !f.written))
// 已埋未收：已写章节中埋了但还没回收的
const unresolvedFS = computed(() => foreshadowingPool.value.filter(f => f.written && !f.resolvedAt))
// 已回收
const resolvedFS = computed(() => foreshadowingPool.value.filter(f => f.resolvedAt && f.resolvedWritten !== false))

// 获取某章相关的伏笔
function fsForChapter(chNum) {
  return foreshadowingPool.value.filter(f => f.plantedAt === chNum || f.resolvedAt === chNum)
}

// ── 工具函数 ──
function volWrittenCount(volId) {
  const nums = new Set(outlines.value.filter(o => o.volume_id === volId).map(o => o.chapter_number))
  return chapters.value.filter(ch => nums.has(ch.chapter_number)).length
}
function volTotalCount(volId) {
  return outlines.value.filter(o => o.volume_id === volId).length
}
function formatWords(n) {
  if (!n) return "—"
  if (n >= 10000) return (n / 10000).toFixed(1) + "万字"
  return n + "字"
}

// ── 生成正文（逐章独立生成） ──
async function generateBatch() {
  if (!activeVol.value || generatingBatch.value) return
  const written = new Set(activeChapters.value.map(c => c.chapter_number))
  const pending = activeOutlines.value.filter(o => !written.has(o.chapter_number)).map(o => o.chapter_number).sort((a, b) => a - b)
  if (pending.length === 0) { ElMessage.info("该卷正文已全部生成"); return }
  const batch = pending.slice(0, 1)

  showGenerateDialog.value = true
  generateLog.value = []
  generateErrors.value = []
  generatingBatch.value = true
  batchProgress.value = { done: 0, total: 1, current: 0, phase: 'generating' }

  const addLog = (text, type = 'info') => {
    generateLog.value.push({ text, type, time: new Date().toLocaleTimeString() })
  }

  addLog(`正在生成第${batch[0]}章...`)

  try {
    const res = await fetch(`/api/books/${route.params.bookId}/batch-write`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ start_chapter: batch[0], end_chapter: batch[batch.length - 1] }),
    })
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).error || `HTTP ${res.status}`)
    const reader = res.body.getReader(), decoder = new TextDecoder()
    let buf = ""
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const lines = buf.split("\n"); buf = lines.pop()
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue
        const p = JSON.parse(line.slice(6))

        if (p.phase === 'generate') {
          if (p.status === 'start') {
            batchProgress.value.total = p.total
          } else if (p.status === 'chapter_start') {
            batchProgress.value.current = p.chapter_number
            streamingChapter.value = p.chapter_number
            streamingContent.value = ""
          } else if (p.status === 'token') {
            streamingContent.value = p.content
          } else if (p.status === 'chapter_done') {
            if (p.ok) {
              batchProgress.value.done++
              addLog(`第${p.chapter_number}章完成，${p.word_count}字`, 'success')
            } else {
              const chLabel = p.chapter_number ? `第${p.chapter_number}章` : '章节'
              addLog(`${chLabel}失败: ${p.error || '未知错误'}`, 'error')
              generateErrors.value.push(p.error || '未知错误')
            }
            streamingContent.value = ""
            streamingChapter.value = 0
            await load()
          }
        }
      }
    }
  } catch (e) {
    addLog(`生成失败: ${e.message}`, 'error')
    generateErrors.value.push(e.message)
  } finally {
    generatingBatch.value = false
    await load()
  }
}

async function regenerate(ch) {
  try { await ElMessageBox.confirm(`确定重写第${ch.chapter_number}章？`, "重写确认", { type: "warning" }) } catch { return }
  regenerating.value = ch.id
  try { await apiPost(`/books/${route.params.bookId}/regenerate`, { chapter_number: ch.chapter_number }); ElMessage.success("已重写"); await load() }
  catch (e) { ElMessage.error("重写失败: " + e.message) }
  finally { regenerating.value = null }
}

async function approve(ch) {
  try { await apiPost(`/chapters/${ch.id}/approve`, {}); ElMessage.success("已批准"); await load() }
  catch (e) { ElMessage.error("批准失败: " + e.message) }
}

async function viewChapter(ch) {
  dialogLoading.value = true; showChapterDialog.value = true; dialogChapter.value = null
  editContent.value = ""; editTitle.value = ""
  try {
    dialogChapter.value = await apiGet(`/books/${route.params.bookId}/chapters/${ch.id}`)
    editContent.value = dialogChapter.value.content || ""
    editTitle.value = dialogChapter.value.title || ""
  } catch (e) { ElMessage.error("加载失败: " + e.message) }
  finally { dialogLoading.value = false }
}

async function saveChapter() {
  if (!dialogChapter.value) return
  savingChapter.value = true
  try {
    await apiPost(`/chapters/${dialogChapter.value.id}/update`, {
      content: editContent.value, title: editTitle.value, word_count: editContent.value.length,
    })
    ElMessage.success("保存成功"); showChapterDialog.value = false; await load()
  } catch (e) { ElMessage.error("保存失败: " + e.message) }
  finally { savingChapter.value = false }
}
</script>

<template>
  <div class="chapter-page">
    <div class="page-header"><h2>全书正文</h2></div>

    <!-- 分卷标签栏 -->
    <div class="vol-tabs" v-if="volumes.length > 0">
      <div v-for="v in volumes" :key="v.id" class="vol-tab" :class="{ 'vol-tab--active': activeVolId === v.id }" @click="activeVolId = v.id">
        <span class="vol-tab-name">{{ v.title || `第${v.number}卷` }}</span>
        <span class="vol-tab-badge">{{ volWrittenCount(v.id) }}/{{ volTotalCount(v.id) }}</span>
      </div>
    </div>

    <!-- 当前卷信息 + 生成按钮 -->
    <div v-if="activeVol" class="vol-header">
      <div class="vol-info">
        <span class="vol-num">第{{ activeVol.number }}卷</span>
        <h3>{{ activeVol.title }}</h3>
        <span class="vol-words" v-if="activeWordCount > 0">{{ formatWords(activeWordCount) }}</span>
      </div>
      <div class="vol-actions">
        <div v-if="volProgress.total > 0" class="vol-progress">
          <span>已写 {{ volProgress.done }} / {{ volProgress.total }} 章</span>
          <el-progress :percentage="Math.round(volProgress.done / volProgress.total * 100)" :stroke-width="6" :show-text="false" style="width:120px;" />
        </div>
        <el-button v-if="volProgress.remaining > 0" type="primary" size="small" :loading="generatingBatch" :disabled="writing" @click="generateBatch">
          {{ generatingBatch ? (batchProgress.phase === 'skeleton' ? '规划骨架中...' : `扩写第${batchProgress.current}章 (${batchProgress.done}/${batchProgress.total})`) : "生成正文" }}
        </el-button>
        <el-tag v-else-if="volProgress.total > 0" type="success" size="small">✅ 全部完成</el-tag>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="volumes.length === 0" class="empty-state"><p>还没有分卷，请先到「分卷大纲」页面规划分卷</p></div>
    <div v-else-if="activeOutlines.length === 0" class="empty-state"><p>该卷还没有细纲</p><p class="empty-hint">请先到「整文细纲」页面生成细纲</p></div>
    <div v-else-if="activeChapters.length === 0" class="empty-state"><p>该卷还没有正文</p><p class="empty-hint">点击上方「生成正文」开始创作</p></div>

    <!-- 主内容区：左侧章节列表 + 右侧伏笔池 -->
    <div class="main-layout" v-if="activeChapters.length > 0">
      <!-- 左侧：章节列表 -->
      <div class="chapter-list-panel">
        <div v-for="ch in visibleChapters" :key="ch.id" class="card chapter-card">
          <div class="chapter-row">
            <div class="chapter-left">
              <el-tag size="small">第{{ ch.chapter_number }}章</el-tag>
              <span class="chapter-title" @click="viewChapter(ch)">{{ ch.title || "无标题" }}</span>
              <span class="chapter-words">{{ ch.word_count || 0 }}字</span>
              <el-tag v-if="ch.word_count > 3000" type="danger" size="small" effect="dark">字数超标</el-tag>
            </div>
            <div class="chapter-right">
              <el-button size="small" text @click="toggleOutline(ch.id)">{{ expandedChapters.has(ch.id) ? '收起详情' : '展开详情' }}</el-button>
              <el-button size="small" :loading="regenerating === ch.id" @click="regenerate(ch)">{{ regenerating === ch.id ? "重写中..." : "重写" }}</el-button>
            </div>
          </div>
          <div v-if="ch.summary" class="chapter-summary">{{ ch.summary }}</div>

          <!-- 细纲字段（展开后显示） -->
          <div class="chapter-outline-fields" v-if="expandedChapters.has(ch.id) && outlineForChapter(ch.chapter_number)">
            <div class="outline-fields-grid">
              <div v-if="outlineForChapter(ch.chapter_number).conflict" class="outline-field outline-field--conflict">
                <span class="outline-field-label">冲突：</span>
                <span class="outline-field-value">{{ outlineForChapter(ch.chapter_number).conflict }}</span>
              </div>
              <div v-if="outlineForChapter(ch.chapter_number).excitement" class="outline-field outline-field--excitement">
                <span class="outline-field-label">爽点：</span>
                <span class="outline-field-value">{{ outlineForChapter(ch.chapter_number).excitement }}</span>
              </div>
              <div v-if="outlineForChapter(ch.chapter_number).hook" class="outline-field outline-field--hook">
                <span class="outline-field-label">钩子：</span>
                <span class="outline-field-value">{{ outlineForChapter(ch.chapter_number).hook }}</span>
              </div>
              <div v-if="outlineForChapter(ch.chapter_number).storyline" class="outline-field outline-field--storyline">
                <span class="outline-field-label">故事线：</span>
                <span class="outline-field-value">{{ outlineForChapter(ch.chapter_number).storyline }}</span>
              </div>
              <div v-if="outlineForChapter(ch.chapter_number).foreshadowing" class="outline-field outline-field--foreshadowing">
                <span class="outline-field-label">伏笔：</span>
                <span class="outline-field-value">{{ outlineForChapter(ch.chapter_number).foreshadowing }}</span>
              </div>
              <div v-if="outlineForChapter(ch.chapter_number).foreshadowing_payoff" class="outline-field outline-field--payoff">
                <span class="outline-field-label">伏笔回收：</span>
                <span class="outline-field-value">{{ outlineForChapter(ch.chapter_number).foreshadowing_payoff }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 分页器 -->
        <div class="chapter-pagination" v-if="activeChapters.length > chapterPageSize">
          <el-pagination
            v-model:current-page="chapterPage"
            :page-size="chapterPageSize"
            :total="activeChapters.length"
            layout="prev, pager, next"
            small
            background
          />
        </div>
      </div>

      <!-- 右侧：伏笔池 -->
      <div class="foreshadowing-panel">
        <div class="fs-panel-header">
          <h3>伏笔池</h3>
          <span class="fs-count">{{ unplantedFS.length + unresolvedFS.length }} 待处理 / {{ resolvedFS.length }} 已回收</span>
        </div>

        <div class="fs-section" v-if="unplantedFS.length > 0">
          <div class="fs-section-title">📝 未埋（{{ unplantedFS.length }}）</div>
          <div v-for="fs in unplantedFS" :key="'n-' + fs.text" class="fs-item fs-item--unplanted">
            <span class="fs-text">{{ fs.text }}</span>
            <span class="fs-chapter">第{{ fs.plantedAt }}章（未写）</span>
          </div>
        </div>

        <div class="fs-section" v-if="unresolvedFS.length > 0">
          <div class="fs-section-title">⏳ 已埋未收（{{ unresolvedFS.length }}）</div>
          <div v-for="fs in unresolvedFS" :key="'u-' + fs.text" class="fs-item fs-item--open">
            <span class="fs-text">{{ fs.text }}</span>
            <span class="fs-chapter">第{{ fs.plantedAt }}章埋</span>
          </div>
        </div>

        <div class="fs-section" v-if="resolvedFS.length > 0">
          <div class="fs-section-title">✅ 已回收（{{ resolvedFS.length }}）</div>
          <div v-for="fs in resolvedFS" :key="'r-' + fs.text" class="fs-item fs-item--resolved">
            <span class="fs-text">{{ fs.text }}</span>
            <span v-if="fs.plantedAt" class="fs-chapter">第{{ fs.plantedAt }}章埋 →</span>
            <span v-if="!fs.plantedAt" class="fs-chapter">→</span>
            <span class="fs-chapter fs-chapter--resolve">第{{ fs.resolvedAt }}章收</span>
          </div>
        </div>

        <div v-if="foreshadowingPool.length === 0" class="fs-empty">暂无伏笔数据</div>
      </div>
    </div>
  </div>

  <!-- 生成进度弹窗 -->
  <el-dialog v-model="showGenerateDialog" title="生成正文" width="600px" :close-on-click-modal="false" :close-on-press-escape="false" :show-close="!generatingBatch" append-to-body destroy-on-close>
    <!-- 进度条 -->
    <div style="margin-bottom:16px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
        <span style="font-size:14px;font-weight:600;">
          {{ batchProgress.phase === 'preparing' ? '准备中...' :
             batchProgress.phase === 'skeleton' ? '规划骨架中...' :
             batchProgress.phase === 'expand' ? `扩写中 (${batchProgress.done}/${batchProgress.total})` : '完成' }}
        </span>
        <span style="font-size:12px;color:var(--text-dim);">
          {{ batchProgress.phase === 'expand' ? `第${batchProgress.current}章` : '' }}
        </span>
      </div>
      <el-progress :percentage="batchProgress.total > 0 ? Math.round(batchProgress.done / batchProgress.total * 100) : 0" :stroke-width="8" />
    </div>

    <!-- 实时日志 -->
    <div class="generate-log">
      <div v-for="(log, i) in generateLog" :key="i" class="generate-log-item" :class="'generate-log--' + log.type">
        <span class="generate-log-time">{{ log.time }}</span>
        <span class="generate-log-text">{{ log.text }}</span>
      </div>
      <div v-if="generateLog.length === 0" style="text-align:center;color:var(--text-dim);padding:20px;">等待开始...</div>
    </div>

    <!-- 流式预览 -->
    <div v-if="streamingContent" style="margin-top:12px;">
      <div style="font-size:12px;font-weight:600;color:var(--text-dim);margin-bottom:6px;">第{{ streamingChapter }}章 正在生成...</div>
      <div class="streaming-preview" ref="streamingPreviewRef">{{ streamingContent }}<span class="streaming-cursor">▌</span></div>
    </div>

    <!-- 错误提示 -->
    <div v-if="generateErrors.length > 0" style="margin-top:12px;padding:8px 12px;background:rgba(192,80,58,0.1);border-radius:6px;border:1px solid rgba(192,80,58,0.3);">
      <div style="font-size:12px;color:#c0503a;font-weight:600;">错误：</div>
      <div v-for="(err, i) in generateErrors" :key="i" style="font-size:12px;color:#c0503a;">{{ err }}</div>
    </div>

    <template #footer>
      <el-button @click="showGenerateDialog = false" :disabled="generatingBatch">{{ generatingBatch ? '生成中...' : '关闭' }}</el-button>
    </template>
  </el-dialog>

  <!-- 章节详情弹窗（可编辑） -->
  <el-dialog v-model="showChapterDialog" :title="dialogChapter ? (dialogChapter.title || `第${dialogChapter.chapter_number}章`) : '章节详情'" width="860px" top="2vh" :close-on-click-modal="false" append-to-body destroy-on-close class="chapter-dialog-wrap">
    <div v-if="dialogLoading" style="text-align:center;padding:40px;color:var(--text-dim);">加载中...</div>
    <template v-else-if="dialogChapter">
      <div class="chapter-dialog-toolbar">
        <div class="chapter-dialog-meta">
          <span>字数：{{ dialogWordCount }}</span>
        </div>
        <div class="chapter-dialog-actions">
          <el-input v-model="editTitle" size="small" placeholder="章节标题" style="width:200px;" />
        </div>
      </div>
      <div class="chapter-dialog-editor-wrap">
        <el-input v-model="editContent" type="textarea" placeholder="在此编辑正文..." class="chapter-dialog-editor" />
      </div>
    </template>
    <template #footer>
      <el-button @click="showChapterDialog = false">取消</el-button>
      <el-button type="primary" :loading="savingChapter" @click="saveChapter">保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.chapter-page { padding: 20px 24px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; font-size: 20px; font-weight: 600; }

/* 分卷标签栏 */
.vol-tabs { display: flex; gap: 4px; margin-bottom: 16px; border-bottom: 1px solid var(--border); overflow-x: auto; }
.vol-tab { display: flex; align-items: center; gap: 6px; padding: 10px 16px; cursor: pointer; font-size: 13px; color: var(--text-dim); border-bottom: 2px solid transparent; transition: all 0.2s; white-space: nowrap; }
.vol-tab:hover { color: var(--text); background: var(--bg-input); }
.vol-tab--active { color: var(--gold); border-bottom-color: var(--gold); font-weight: 600; }
.vol-tab-name { max-width: 120px; overflow: hidden; text-overflow: ellipsis; }
.vol-tab-badge { font-size: 11px; color: var(--text-dim); background: var(--bg-input); padding: 1px 6px; border-radius: 8px; }
.vol-tab--active .vol-tab-badge { background: var(--gold-glow); color: var(--gold); }

/* 当前卷信息栏 */
.vol-header { display: flex; justify-content: space-between; align-items: center; background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 14px 18px; margin-bottom: 16px; }
.vol-info { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.vol-num { font-size: 12px; font-weight: 600; color: var(--gold); background: var(--gold-glow); padding: 2px 8px; border-radius: 4px; }
.vol-info h3 { margin: 0; font-size: 15px; font-weight: 600; }
.vol-words { font-size: 12px; color: var(--gold); font-weight: 500; }
.vol-actions { display: flex; align-items: center; gap: 12px; flex-shrink: 0; }
.vol-progress { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--text-dim); }

/* 空状态 */
.empty-state { text-align: center; padding: 48px 20px; color: var(--text-dim); }
.empty-hint { font-size: 13px; color: var(--text-secondary); }

/* 主布局：左章节 + 右伏笔 */
.main-layout { display: flex; gap: 16px; align-items: flex-start; }
.chapter-list-panel { flex: 1; min-width: 0; }

/* 章节卡片 */
.chapter-card { margin-bottom: 8px; }
.chapter-row { display: flex; justify-content: space-between; align-items: center; }
.chapter-left { display: flex; align-items: center; gap: 8px; }
.chapter-title { color: var(--gold); text-decoration: none; font-weight: 500; cursor: pointer; }
.chapter-title:hover { text-decoration: underline; }
.chapter-words { color: var(--text-dim); font-size: 12px; }
.chapter-right { display: flex; gap: 6px; }
.chapter-summary { margin-top: 8px; color: var(--text-secondary); font-size: 13px; }

/* 细纲字段 */
.chapter-outline-fields { margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--border); }

/* 分页器 */
.chapter-pagination { display: flex; justify-content: center; padding: 16px 0; }
.outline-fields-grid { display: flex; flex-wrap: wrap; gap: 6px; }
.outline-field { display: flex; align-items: center; gap: 4px; font-size: 12px; padding: 3px 8px; border-radius: 4px; background: var(--bg-input); }
.outline-field-label { font-weight: 600; white-space: nowrap; }
.outline-field-value { color: var(--text-secondary); }
.outline-field--conflict .outline-field-label { color: #f56c6c; }
.outline-field--excitement .outline-field-label { color: #e6a23c; }
.outline-field--hook .outline-field-label { color: #409eff; }
.outline-field--storyline .outline-field-label { color: #67c23a; }
.outline-field--foreshadowing .outline-field-label { color: #b37feb; }
.outline-field--payoff .outline-field-label { color: #36cfc9; }

/* 伏笔池面板 */
.foreshadowing-panel { width: 280px; flex-shrink: 0; background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; padding: 16px; position: sticky; top: 20px; max-height: calc(100vh - 120px); overflow-y: auto; }
.fs-panel-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; padding-bottom: 10px; border-bottom: 1px solid var(--border); }
.fs-panel-header h3 { margin: 0; font-size: 15px; font-weight: 600; }
.fs-count { font-size: 11px; color: var(--text-dim); }
.fs-section { margin-bottom: 14px; }
.fs-section-title { font-size: 12px; font-weight: 600; color: var(--text-dim); margin-bottom: 8px; }
.fs-item { display: flex; align-items: center; gap: 6px; padding: 6px 8px; border-radius: 6px; margin-bottom: 4px; font-size: 12px; line-height: 1.4; flex-wrap: wrap; }
.fs-item--unplanted { background: rgba(144, 147, 153, 0.08); border: 1px dashed rgba(144, 147, 153, 0.3); opacity: 0.7; }
.fs-item--open { background: rgba(230, 162, 60, 0.08); border: 1px solid rgba(230, 162, 60, 0.2); }
.fs-item--resolved { background: rgba(103, 194, 58, 0.06); border: 1px solid rgba(103, 194, 58, 0.15); opacity: 0.75; }
.fs-text { color: var(--text); font-weight: 500; flex: 1; min-width: 0; word-break: break-all; }
.fs-chapter { font-size: 11px; color: var(--gold); white-space: nowrap; }
.fs-chapter--resolve { color: #67c23a; }
.fs-arrow { color: var(--text-dim); font-size: 11px; }
.fs-empty { text-align: center; color: var(--text-dim); font-size: 13px; padding: 20px 0; }

/* 生成日志 */
.generate-log { max-height: 300px; overflow-y: auto; background: var(--bg-input); border-radius: 6px; padding: 12px; }
.generate-log-item { display: flex; gap: 8px; margin-bottom: 6px; font-size: 13px; line-height: 1.5; }
.generate-log-time { color: var(--text-dim); font-size: 11px; flex-shrink: 0; }
.generate-log-text { flex: 1; }
.generate-log--info .generate-log-text { color: var(--text-secondary); }
.generate-log--success .generate-log-text { color: #67c23a; }
.generate-log--warning .generate-log-text { color: #e6a23c; }
.generate-log--error .generate-log-text { color: #f56c6c; }

/* 流式预览 */
.streaming-preview { background: var(--bg-input); border: 1px solid var(--border); border-radius: 6px; padding: 12px; max-height: 200px; overflow-y: auto; font-size: 14px; line-height: 1.8; color: var(--text-secondary); white-space: pre-wrap; }
.streaming-cursor { animation: blink 1s infinite; color: var(--gold); }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
</style>
<style>
.chapter-dialog-wrap .el-dialog { max-height: 92vh; display: flex; flex-direction: column; margin-bottom: 0; }
.chapter-dialog-wrap .el-dialog__body { flex: 1; overflow: hidden; display: flex; flex-direction: column; padding: 0 20px 10px; height: 600px; }
.chapter-dialog-wrap .el-dialog__header { flex-shrink: 0; }
.chapter-dialog-wrap .el-dialog__footer { flex-shrink: 0; }
.chapter-dialog-toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-shrink: 0; }
.chapter-dialog-meta { display: flex; align-items: center; gap: 12px; font-size: 13px; color: var(--text-dim); }
.chapter-dialog-actions { display: flex; align-items: center; gap: 8px; }
.chapter-dialog-editor-wrap { flex: 1; overflow-y: auto; min-height: 0; }
.chapter-dialog-editor .el-textarea__inner { font-size: 15px; line-height: 2; padding: 16px; background: var(--bg-card); color: var(--text); border-color: var(--border); height: 520px; resize: none; }
.chapter-dialog-editor .el-textarea__inner:focus { border-color: var(--gold); }
</style>
