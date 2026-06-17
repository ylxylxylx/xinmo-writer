<script setup>
import { ref, onMounted, computed, watch } from "vue"
import { useRoute } from "vue-router"
import { ElMessage, ElMessageBox } from "element-plus"
import { apiGet, apiPost } from "../api/index.js"

const route = useRoute()
const bookId = computed(() => route.params.bookId)
const outlines = ref([])
const volumes = ref([])
const showModal = ref(false)
const editing = ref(null)
const activeVolId = ref(null)
const generatingVolId = ref(null)
const outlinePage = ref(1)
const outlinePageSize = 10
const form = ref({
  chapter_number: 1, title: "", outline_content: "", volume_id: null, word_target: 2000,
  conflict: "", excitement: "", hook: "", storyline: "", foreshadowing: "", foreshadowing_payoff: ""
})

async function load() {
  try {
    const o = await apiGet(`/books/${bookId.value}/outlines`)
    outlines.value = o
    try { volumes.value = await apiGet(`/books/${bookId.value}/volumes`) } catch {}
    // 如果 URL 带 vol 参数，自动选中该卷
    if (route.query.vol && !activeVolId.value) {
      activeVolId.value = Number(route.query.vol)
    }
    // 默认选中第一个有细纲的卷，或第一个卷
    if (!activeVolId.value && volumes.value.length > 0) {
      const volWithOutlines = volumes.value.find(v =>
        outlines.value.some(o => o.volume_id === v.id)
      )
      activeVolId.value = (volWithOutlines || volumes.value[0]).id
    }
  } catch (e) { ElMessage.error("加载失败: " + e.message) }
}
onMounted(load)

const maxChapter = computed(() => Math.max(0, ...outlines.value.map(o => o.chapter_number)))

// 当前卷的细纲
const activeVol = computed(() => volumes.value.find(v => v.id === activeVolId.value))
const activeOutlines = computed(() => {
  if (!activeVolId.value) return outlines.value.filter(o => !o.volume_id)
  return outlines.value
    .filter(o => o.volume_id === activeVolId.value)
    .sort((a, b) => a.chapter_number - b.chapter_number)
})

// 分页后的细纲
const paginatedOutlines = computed(() => {
  const start = (outlinePage.value - 1) * outlinePageSize
  return activeOutlines.value.slice(start, start + outlinePageSize)
})

// 切换分卷时重置页码
watch(activeVolId, () => { outlinePage.value = 1 })

// 当前卷的生成进度
const volProgress = computed(() => {
  if (!activeVol.value) return { total: 0, done: 0, remaining: 0 }
  const vol = activeVol.value
  const total = vol.chapter_count || 0
  const done = activeOutlines.value.length
  return { total, done, remaining: Math.max(0, total - done) }
})

// 每卷的细纲计数（用于 tab badge）
function volOutlineCount(volId) {
  return outlines.value.filter(o => o.volume_id === volId).length
}
function volChapterCount(vol) {
  return vol.chapter_count || 0
}

// AI 生成当前卷的下一批细纲（5章）
async function generateBatch() {
  if (!activeVol.value) return
  const vol = activeVol.value
  const count = vol.chapter_count || 20
  const existing = activeOutlines.value.length
  if (existing >= count) {
    ElMessage.info("该卷细纲已全部生成")
    return
  }

  const batchStart = existing > 0
    ? Math.max(...activeOutlines.value.map(o => o.chapter_number)) + 1
    : (vol.chapter_start || 1)
  const batchEnd = Math.min(batchStart + 4, (vol.chapter_start || 1) + count)

  try {
    await ElMessageBox.confirm(
      `将为「${vol.title}」生成第${batchStart}-${batchEnd}章的细纲，是否继续？`,
      "AI 生成细纲", { type: "info" }
    )
  } catch { return }

  generatingVolId.value = activeVolId.value
  try {
    const res = await apiPost(`/volumes/${vol.id}/generate-outlines`, {
      start_chapter: batchStart,
      batch_size: 5
    })
    if (res.done) {
      ElMessage.success(`已生成最后 ${res.count} 章，该卷细纲全部完成！`)
    } else {
      ElMessage.success(`已生成 ${res.count} 章细纲，还剩 ${res.remaining} 章`)
    }
    await load()
  } catch (e) {
    ElMessage.error("生成失败: " + e.message)
  } finally {
    generatingVolId.value = null
  }
}

function openAdd() {
  editing.value = null
  form.value = {
    chapter_number: maxChapter.value + 1, title: "", outline_content: "",
    volume_id: activeVolId.value, word_target: 2000,
    conflict: "", excitement: "", hook: "", storyline: "", foreshadowing: "", foreshadowing_payoff: ""
  }
  showModal.value = true
}
function openEdit(o) {
  editing.value = o
  form.value = {
    chapter_number: o.chapter_number, title: o.title || "", outline_content: o.outline_content || "",
    volume_id: o.volume_id, word_target: o.word_target || 2000,
    conflict: o.conflict || "", excitement: o.excitement || "", hook: o.hook || "",
    storyline: o.storyline || "", foreshadowing: o.foreshadowing || "", foreshadowing_payoff: o.foreshadowing_payoff || ""
  }
  showModal.value = true
}

async function save() {
  if (!form.value.outline_content.trim()) return
  try {
    if (editing.value) { await apiPost(`/outlines/${editing.value.id}/update`, form.value) }
    else { await apiPost(`/books/${bookId.value}/outlines`, form.value) }
    ElMessage.success("保存成功")
    showModal.value = false
    await load()
  } catch (e) { ElMessage.error("保存失败: " + e.message) }
}

async function remove(o) {
  try {
    await ElMessageBox.confirm(`确定删除第${o.chapter_number}章细纲？`, "删除确认", { type: "warning" })
  } catch { return }
  try { await apiPost(`/outlines/${o.id}/delete`, {}); ElMessage.success("已删除"); await load() }
  catch (e) { ElMessage.error("删除失败: " + e.message) }
}
</script>

<template>
  <div class="outline-page">
    <div class="page-header">
      <h2>整文细纲</h2>
      <el-button type="primary" size="small" @click="openAdd">+ 新增细纲</el-button>
    </div>

    <!-- 分卷标签栏 -->
    <div class="vol-tabs" v-if="volumes.length > 0">
      <div
        v-for="v in volumes"
        :key="v.id"
        class="vol-tab"
        :class="{ 'vol-tab--active': activeVolId === v.id }"
        @click="activeVolId = v.id"
      >
        <span class="vol-tab-name">{{ v.title || `第${v.number}卷` }}</span>
        <span class="vol-tab-badge">{{ volOutlineCount(v.id) }}/{{ volChapterCount(v) }}</span>
      </div>
    </div>

    <!-- 当前卷信息 + 生成按钮 -->
    <div v-if="activeVol" class="vol-header">
      <div class="vol-info">
        <span class="vol-num">第{{ activeVol.number }}卷</span>
        <h3>{{ activeVol.title }}</h3>
        <span v-if="activeVol.summary" class="vol-summary-hint">{{ activeVol.summary.slice(0, 60) }}...</span>
      </div>
      <div class="vol-actions">
        <div v-if="volProgress.total > 0" class="vol-progress">
          <span>已生成 {{ volProgress.done }} / {{ volProgress.total }} 章</span>
          <el-progress
            :percentage="Math.round(volProgress.done / volProgress.total * 100)"
            :stroke-width="6"
            :show-text="false"
            style="width:120px;"
          />
        </div>
        <el-button
          v-if="volProgress.remaining > 0"
          type="primary"
          size="small"
          :loading="generatingVolId === activeVolId"
          @click="generateBatch"
        >
          {{ generatingVolId === activeVolId ? "生成中..." : `AI 生成下一批（5章）` }}
        </el-button>
        <el-tag v-else-if="volProgress.total > 0" type="success" size="small">✅ 全部完成</el-tag>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="volumes.length === 0" class="empty-state">
      <p>还没有分卷，请先到「分卷大纲」页面规划分卷</p>
    </div>
    <div v-else-if="activeOutlines.length === 0" class="empty-state">
      <p>该卷还没有细纲</p>
      <p class="empty-hint">点击上方「AI 生成下一批」开始，或手动新增</p>
    </div>

    <!-- 细纲卡片列表 -->
    <div v-for="o in paginatedOutlines" :key="o.id" class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <div style="display:flex;align-items:center;gap:8px;">
          <el-tag size="small">第{{ o.chapter_number }}章</el-tag>
          <strong>{{ o.title || "无标题" }}</strong>
          <span v-if="o.word_target" style="color:var(--text-dim);font-size:12px;">目标{{ o.word_target }}字</span>
        </div>
        <div style="display:flex;gap:6px;">
          <el-button size="small" @click="openEdit(o)">编辑</el-button>
          <el-button size="small" type="danger" @click="remove(o)">删除</el-button>
        </div>
      </div>
      <div v-if="o.outline_content" style="margin-top:8px;color:var(--text-secondary);font-size:13px;white-space:pre-wrap;">{{ o.outline_content }}</div>
      <!-- 详细字段直接展示 -->
      <div class="outline-details" v-if="o.conflict || o.excitement || o.hook || o.storyline || o.foreshadowing || o.foreshadowing_payoff">
        <div style="display:grid;grid-template-columns:repeat(auto-fill, minmax(200px, 1fr));gap:8px;margin-top:10px;">
          <div v-if="o.conflict" class="detail-item detail-item--conflict">
            <span class="detail-label">冲突：</span>
            <span class="detail-value">{{ o.conflict }}</span>
          </div>
          <div v-if="o.excitement" class="detail-item detail-item--excitement">
            <span class="detail-label">爽点：</span>
            <span class="detail-value">{{ o.excitement }}</span>
          </div>
          <div v-if="o.hook" class="detail-item detail-item--hook">
            <span class="detail-label">钩子：</span>
            <span class="detail-value">{{ o.hook }}</span>
          </div>
          <div v-if="o.storyline" class="detail-item detail-item--storyline">
            <span class="detail-label">故事线：</span>
            <span class="detail-value">{{ o.storyline }}</span>
          </div>
          <div v-if="o.foreshadowing" class="detail-item detail-item--foreshadowing">
            <span class="detail-label">伏笔：</span>
            <span class="detail-value">{{ o.foreshadowing }}</span>
          </div>
          <div v-if="o.foreshadowing_payoff" class="detail-item detail-item--payoff">
            <span class="detail-label">伏笔回收：</span>
            <span class="detail-value">{{ o.foreshadowing_payoff }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 分页器 -->
    <div class="outline-pagination" v-if="activeOutlines.length > outlinePageSize">
      <el-pagination
        v-model:current-page="outlinePage"
        :page-size="outlinePageSize"
        :total="activeOutlines.length"
        layout="prev, pager, next"
        small
        background
      />
    </div>
  </div>

  <el-dialog v-model="showModal" :title="editing ? '编辑细纲' : '新增细纲'" width="640px">
    <div class="form-group"><label>章节号</label><el-input-number v-model="form.chapter_number" :min="1" /></div>
    <div class="form-group"><label>章节标题</label><el-input v-model="form.title" /></div>
    <div class="form-group"><label>所属分卷</label>
      <el-select v-model.number="form.volume_id" style="width:100%;">
        <el-option :value="null" label="无" />
        <el-option v-for="v in volumes" :key="v.id" :value="v.id" :label="v.title" />
      </el-select>
    </div>
    <div class="form-group"><label>细纲内容</label><el-input v-model="form.outline_content" type="textarea" :rows="4" placeholder="详细描述本章要写的内容..." /></div>
    <div class="form-group"><label>目标字数</label><el-input-number v-model="form.word_target" :min="500" /></div>
    <div style="border-top:1px solid var(--border);margin:12px 0;padding-top:12px;">
      <div style="font-size:13px;font-weight:600;margin-bottom:8px;">详细字段</div>
      <div class="form-group"><label>冲突</label><el-input v-model="form.conflict" placeholder="核心冲突..." /></div>
      <div class="form-group"><label>爽点</label><el-input v-model="form.excitement" placeholder="爽点设计..." /></div>
      <div class="form-group"><label>钩子</label><el-input v-model="form.hook" placeholder="章末钩子..." /></div>
      <div class="form-group"><label>故事线</label><el-input v-model="form.storyline" placeholder="推进的故事线..." /></div>
      <div class="form-group"><label>伏笔</label><el-input v-model="form.foreshadowing" placeholder="埋下的伏笔..." /></div>
      <div class="form-group"><label>伏笔回收</label><el-input v-model="form.foreshadowing_payoff" placeholder="回收的伏笔..." /></div>
    </div>
    <template #footer>
      <el-button @click="showModal=false">取消</el-button>
      <el-button type="primary" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.outline-page {
  padding: 20px 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

/* 分卷标签栏 */
.vol-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--border);
  padding-bottom: 0;
  overflow-x: auto;
}

.vol-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-dim);
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
  white-space: nowrap;
}

.vol-tab:hover {
  color: var(--text);
  background: var(--bg-input);
}

.vol-tab--active {
  color: var(--gold);
  border-bottom-color: var(--gold);
  font-weight: 600;
}

.vol-tab-name {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.vol-tab-badge {
  font-size: 11px;
  color: var(--text-dim);
  background: var(--bg-input);
  padding: 1px 6px;
  border-radius: 8px;
}

.vol-tab--active .vol-tab-badge {
  background: var(--gold-glow);
  color: var(--gold);
}

/* 当前卷信息栏 */
.vol-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px 18px;
  margin-bottom: 16px;
}

/* 分页器 */
.outline-pagination {
  display: flex;
  justify-content: center;
  padding: 16px 0;
}

.vol-info {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.vol-num {
  font-size: 12px;
  font-weight: 600;
  color: var(--gold);
  background: var(--gold-glow);
  padding: 2px 8px;
  border-radius: 4px;
}

.vol-info h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
}

.vol-summary-hint {
  font-size: 12px;
  color: var(--text-dim);
}

.vol-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.vol-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-dim);
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 48px 20px;
  color: var(--text-dim);
}

.empty-hint {
  font-size: 13px;
  color: var(--text-secondary);
}

/* 细纲详情 */
.detail-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 6px 8px;
  background: var(--bg-input);
  border-radius: 4px;
}
.detail-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.5px;
}
.detail-value {
  font-size: 13px;
  color: var(--text-secondary);
}
.detail-item--conflict .detail-label { color: #f56c6c; }
.detail-item--excitement .detail-label { color: #e6a23c; }
.detail-item--hook .detail-label { color: #409eff; }
.detail-item--storyline .detail-label { color: #67c23a; }
.detail-item--foreshadowing .detail-label { color: #b37feb; }
.detail-item--payoff .detail-label { color: #36cfc9; }
</style>
