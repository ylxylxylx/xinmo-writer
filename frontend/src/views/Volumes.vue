<script setup>
import { ref, onMounted, computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import { ElMessage, ElMessageBox } from "element-plus"
import { apiGet, apiPost } from "../api/index.js"

const route = useRoute()
const router = useRouter()
const bookId = computed(() => route.params.bookId)
const volumes = ref([])
const book = ref({})
const editingId = ref(null)
const planning = ref(false)
const generatingVol = ref(null)
const editForm = ref({})

const storylines = computed(() => {
  try { return JSON.parse(book.value.storylines || "[]") }
  catch { return [] }
})

const generatedVolumes = computed(() => volumes.value.filter(v => v.summary))
const totalVolumes = computed(() => volumes.value.length)
const plannedVolumes = computed(() => book.value.planned_volumes || 0)
const allGenerated = computed(() => totalVolumes.value > 0 && generatedVolumes.value.length === totalVolumes.value)

async function load() {
  try {
    const [vols, bookData] = await Promise.all([
      apiGet(`/books/${bookId.value}/volumes`),
      apiGet(`/books/${bookId.value}`)
    ])
    volumes.value = vols || []
    book.value = bookData || {}
  } catch (e) {
    ElMessage.error("加载失败: " + e.message)
  }
}
onMounted(load)

// 解析 JSON 字段，返回数组
function parseArr(str) {
  if (!str) return []
  try {
    const arr = typeof str === "string" ? JSON.parse(str) : str
    return Array.isArray(arr) ? arr : []
  } catch { return [] }
}

// 格式化万字
function formatWords(n) {
  if (!n) return "—"
  if (n >= 10000) return (n / 10000).toFixed(1) + "万字"
  return n + "字"
}

// 章节范围文本
function chapterRange(v) {
  if (v.chapter_start && v.chapter_end) return `第${v.chapter_start}-${v.chapter_end}章`
  if (v.chapter_count) return `共${v.chapter_count}章`
  return ""
}

// 阶段一：AI 规划分卷结构
async function planVolumes() {
  const isReplan = totalVolumes.value > 0
  const msg = isReplan
    ? "重新规划将清除所有已生成的分卷详情，是否继续？"
    : "将根据目标字数用 AI 规划全书分卷结构，是否继续？"
  try {
    await ElMessageBox.confirm(msg, isReplan ? "重新规划" : "AI 规划分卷", { type: "warning" })
  } catch { return }

  planning.value = true
  try {
    const res = await apiPost(`/books/${bookId.value}/plan-volumes`, {})
    ElMessage.success(`已规划全书 ${res.total_volumes} 卷，点击各卷卡片生成详细大纲`)
    await load()
  } catch (e) {
    ElMessage.error("规划失败: " + e.message)
  } finally {
    planning.value = false
  }
}

// 阶段二：AI 生成指定卷的详细大纲
async function generateVol(v) {
  try {
    await ElMessageBox.confirm(
      `将用 AI 生成第${v.number}卷「${v.title}」的详细大纲，是否继续？`,
      "AI 生成本卷", { type: "info" }
    )
  } catch { return }

  generatingVol.value = v.id
  try {
    await apiPost(`/books/${bookId.value}/generate-volume`, { volume_number: v.number })
    ElMessage.success(`第${v.number}卷大纲已生成`)
    await load()
  } catch (e) {
    ElMessage.error("生成失败: " + e.message)
  } finally {
    generatingVol.value = null
  }
}

// 跳转到整文细纲页面（定位到指定分卷）
function goToOutlines(v) {
  router.push(`/books/${bookId.value}/outlines?vol=${v.id}`)
}

// 编辑
function startEdit(v) {
  editingId.value = v.id
  editForm.value = {
    title: v.title || "",
    subtitle: v.subtitle || "",
    summary: v.summary || "",
    chapter_count: v.chapter_count || 0,
    chapter_start: v.chapter_start || 0,
    chapter_end: v.chapter_end || 0,
    key_nodes: (parseArr(v.key_nodes)).join("\n"),
    emotion_arc: v.emotion_arc || "",
    characters_in_vol: (parseArr(v.characters_in_vol)).join("、"),
    end_hook: v.end_hook || "",
    estimated_words: v.estimated_words || 0,
    theme: v.theme || "",
    main_conflict: v.main_conflict || "",
    turning_point: v.turning_point || "",
    character_arc: v.character_arc || "",
    world_change: v.world_change || "",
    foreshadowing_plan: v.foreshadowing_plan || "",
    emotional_tone: v.emotional_tone || "",
    climax: v.climax || "",
  }
}

async function saveEdit(v) {
  const f = editForm.value
  const payload = {
    title: f.title,
    subtitle: f.subtitle,
    summary: f.summary,
    chapter_count: Number(f.chapter_count) || 0,
    chapter_start: Number(f.chapter_start) || 0,
    chapter_end: Number(f.chapter_end) || 0,
    key_nodes: JSON.stringify(f.key_nodes.split("\n").filter(Boolean)),
    emotion_arc: f.emotion_arc,
    characters_in_vol: JSON.stringify(f.characters_in_vol.split(/[、,，]/).filter(Boolean)),
    end_hook: f.end_hook,
    estimated_words: Number(f.estimated_words) || 0,
    theme: f.theme,
    main_conflict: f.main_conflict,
    turning_point: f.turning_point,
    character_arc: f.character_arc,
    world_change: f.world_change,
    foreshadowing_plan: f.foreshadowing_plan,
    emotional_tone: f.emotional_tone,
    climax: f.climax,
  }
  try {
    await apiPost(`/volumes/${v.id}/update`, payload)
    ElMessage.success("保存成功")
    editingId.value = null
    await load()
  } catch (e) {
    ElMessage.error("保存失败: " + e.message)
  }
}

function cancelEdit() {
  editingId.value = null
}

// 删除
async function removeVol(v) {
  try {
    await ElMessageBox.confirm(`确定删除第${v.number}卷「${v.title}」？`, "删除确认", { type: "warning" })
  } catch { return }
  try {
    await apiPost(`/volumes/${v.id}/delete`, {})
    ElMessage.success("已删除")
    await load()
  } catch (e) {
    ElMessage.error("删除失败: " + e.message)
  }
}

// 跳转到全书正文页面（定位到指定分卷）
async function viewChapters(v) {
  router.push(`/books/${bookId.value}/chapters?vol=${v.id}`)
}

// 下一卷是否可以生成：只要有任意一卷没有 summary 就可以继续
const canGenerateNext = computed(() => {
  if (volumes.value.length === 0) return false
  return volumes.value.some(v => !v.summary)
})
</script>

<template>
  <div class="vol-page">
    <!-- 顶部标题栏 -->
    <div class="vol-page-header">
      <div class="vol-page-title">
        <h2>分卷大纲</h2>
        <span class="vol-page-count" v-if="totalVolumes > 0">
          已生成 {{ generatedVolumes.length }} / {{ totalVolumes }} 卷
        </span>
      </div>
      <div style="display:flex;gap:8px;align-items:center;">
        <el-button
          v-if="totalVolumes > 0 && !allGenerated"
          type="success"
          size="small"
          plain
          :loading="planning"
          @click="planVolumes"
        >
          重新规划
        </el-button>
        <el-button
          type="primary"
          :loading="planning"
          @click="planVolumes"
          v-if="totalVolumes === 0"
        >
          <el-icon v-if="!planning" style="margin-right:4px;"><i class="el-icon-magic-stick" /></el-icon>
          {{ planning ? "AI 规划中..." : "AI 规划分卷" }}
        </el-button>
      </div>
    </div>

    <!-- 故事线标签区 -->
    <div class="vol-storylines" v-if="storylines.length > 0">
      <span class="vol-storylines-label">故事线</span>
      <el-tag
        v-for="s in storylines"
        :key="s.name"
        :type="s.type === 'main' ? 'danger' : 'primary'"
        size="small"
        effect="light"
        class="vol-storyline-tag"
      >
        {{ s.name }}
      </el-tag>
    </div>

    <!-- 空状态 -->
    <div v-if="totalVolumes === 0 && !planning" class="vol-empty">
      <div class="vol-empty-icon">📚</div>
      <p>还没有分卷大纲</p>
      <p class="vol-empty-hint">点击上方「AI 规划分卷」开始</p>
    </div>

    <!-- 全部完成提示 -->
    <div v-if="allGenerated" class="vol-all-done">
      <span>✅ 全部 {{ totalVolumes }} 卷大纲已生成完毕</span>
      <el-button size="small" type="primary" plain :loading="planning" @click="planVolumes">重新规划</el-button>
    </div>

    <!-- 卷卡片列表 -->
    <div class="vol-cards">
      <div
        v-for="v in volumes"
        :key="v.id"
        class="vol-card"
        :class="{ 'vol-card--empty': !v.summary, 'vol-card--editing': editingId === v.id }"
      >
        <!-- 卡片头部 -->
        <div class="vol-card-head">
          <div class="vol-card-title-row">
            <span class="vol-card-number">第{{ v.number }}卷</span>
            <span v-if="chapterRange(v)" class="vol-card-chapters">{{ chapterRange(v) }}</span>
            <el-tag
              v-if="v.summary"
              type="success"
              size="small"
              effect="dark"
              class="vol-card-status"
            >已生成</el-tag>
            <el-tag
              v-else
              type="info"
              size="small"
              effect="plain"
              class="vol-card-status"
            >待生成</el-tag>
          </div>
          <h3 v-if="editingId !== v.id" class="vol-card-name">
            {{ v.title || "未命名" }}
            <span v-if="v.subtitle" class="vol-card-subtitle">：{{ v.subtitle }}</span>
          </h3>
        </div>

        <!-- 编辑模式 -->
        <div v-if="editingId === v.id" class="vol-edit">
          <div class="vol-edit-row">
            <div class="vol-edit-field">
              <label>卷名</label>
              <el-input v-model="editForm.title" size="small" />
            </div>
            <div class="vol-edit-field">
              <label>副标题</label>
              <el-input v-model="editForm.subtitle" size="small" />
            </div>
          </div>
          <div class="vol-edit-row">
            <div class="vol-edit-field">
              <label>起始章节</label>
              <el-input-number v-model="editForm.chapter_start" :min="0" size="small" controls-position="right" />
            </div>
            <div class="vol-edit-field">
              <label>结束章节</label>
              <el-input-number v-model="editForm.chapter_end" :min="0" size="small" controls-position="right" />
            </div>
            <div class="vol-edit-field">
              <label>章节数</label>
              <el-input-number v-model="editForm.chapter_count" :min="0" size="small" controls-position="right" />
            </div>
            <div class="vol-edit-field">
              <label>预估字数</label>
              <el-input-number v-model="editForm.estimated_words" :min="0" :step="5000" size="small" controls-position="right" />
            </div>
          </div>
          <div class="vol-edit-field">
            <label>剧情概要</label>
            <el-input v-model="editForm.summary" type="textarea" :rows="3" />
          </div>
          <div class="vol-edit-row">
            <div class="vol-edit-field">
              <label>核心主题</label>
              <el-input v-model="editForm.theme" size="small" />
            </div>
            <div class="vol-edit-field">
              <label>情感基调</label>
              <el-input v-model="editForm.emotional_tone" size="small" />
            </div>
          </div>
          <div class="vol-edit-row">
            <div class="vol-edit-field">
              <label>主要冲突</label>
              <el-input v-model="editForm.main_conflict" type="textarea" :rows="2" />
            </div>
            <div class="vol-edit-field">
              <label>关键转折</label>
              <el-input v-model="editForm.turning_point" type="textarea" :rows="2" />
            </div>
          </div>
          <div class="vol-edit-row">
            <div class="vol-edit-field">
              <label>角色弧线</label>
              <el-input v-model="editForm.character_arc" type="textarea" :rows="2" />
            </div>
            <div class="vol-edit-field">
              <label>世界观变化</label>
              <el-input v-model="editForm.world_change" type="textarea" :rows="2" />
            </div>
          </div>
          <div class="vol-edit-row">
            <div class="vol-edit-field">
              <label>伏笔规划</label>
              <el-input v-model="editForm.foreshadowing_plan" type="textarea" :rows="2" />
            </div>
            <div class="vol-edit-field">
              <label>高潮设计</label>
              <el-input v-model="editForm.climax" type="textarea" :rows="2" />
            </div>
          </div>
          <div class="vol-edit-field">
            <label>情绪弧线</label>
            <el-input v-model="editForm.emotion_arc" placeholder="如：绝望→希望→愤怒→觉醒" size="small" />
          </div>
          <div class="vol-edit-field">
            <label>关键节点（每行一个）</label>
            <el-input v-model="editForm.key_nodes" type="textarea" :rows="3" placeholder="每行一个关键节点" />
          </div>
          <div class="vol-edit-row">
            <div class="vol-edit-field">
              <label>本卷角色（顿号分隔）</label>
              <el-input v-model="editForm.characters_in_vol" size="small" placeholder="角色A、角色B" />
            </div>
            <div class="vol-edit-field">
              <label>卷尾钩子</label>
              <el-input v-model="editForm.end_hook" type="textarea" :rows="2" />
            </div>
          </div>
          <div class="vol-edit-actions">
            <el-button size="small" @click="cancelEdit">取消</el-button>
            <el-button size="small" type="primary" @click="saveEdit(v)">保存</el-button>
          </div>
        </div>

        <!-- 展示模式 -->
        <template v-else>
          <!-- 未生成的卷 -->
          <div v-if="!v.summary" class="vol-card-empty-body">
            <p>该卷尚未生成详细大纲</p>
            <div class="vol-card-empty-actions">
              <el-button
                size="small"
                type="primary"
                :loading="generatingVol === v.id"
                @click="generateVol(v)"
              >
                {{ generatingVol === v.id ? "生成中..." : "AI 生成本卷" }}
              </el-button>
              <el-button size="small" @click="startEdit(v)">手动编辑</el-button>
              <el-button size="small" type="danger" plain @click="removeVol(v)">删除</el-button>
            </div>
          </div>

          <!-- 已生成的卷 -->
          <template v-else>
            <div v-if="v.summary" class="vol-card-section">
              <span class="vol-card-label">剧情概要</span>
              <p class="vol-card-text">{{ v.summary }}</p>
            </div>

            <div v-if="parseArr(v.key_nodes).length" class="vol-card-section">
              <span class="vol-card-label">关键节点</span>
              <div class="vol-key-nodes">
                <span v-for="(node, i) in parseArr(v.key_nodes)" :key="i" class="vol-key-node">
                  <em class="vol-key-node-num">{{ i + 1 }}</em>{{ node }}
                </span>
              </div>
            </div>

            <div v-if="v.emotion_arc" class="vol-card-section">
              <span class="vol-card-label">情绪弧线</span>
              <div class="vol-emotion-arc">
                <template v-for="(seg, i) in v.emotion_arc.split(/→|->/)" :key="i">
                  <span class="vol-emotion-seg">{{ seg.trim() }}</span>
                  <span v-if="i < v.emotion_arc.split(/→|->/).length - 1" class="vol-emotion-arrow">→</span>
                </template>
              </div>
            </div>

            <div class="vol-card-meta-grid">
              <div v-if="parseArr(v.characters_in_vol).length" class="vol-card-meta">
                <span class="vol-card-label">本卷角色</span>
                <span class="vol-card-meta-val">{{ parseArr(v.characters_in_vol).join("、") }}</span>
              </div>
              <div v-if="v.theme" class="vol-card-meta">
                <span class="vol-card-label">核心主题</span>
                <span class="vol-card-meta-val">{{ v.theme }}</span>
              </div>
              <div v-if="v.main_conflict" class="vol-card-meta">
                <span class="vol-card-label">主要冲突</span>
                <span class="vol-card-meta-val">{{ v.main_conflict }}</span>
              </div>
              <div v-if="v.climax" class="vol-card-meta">
                <span class="vol-card-label">高潮设计</span>
                <span class="vol-card-meta-val">{{ v.climax }}</span>
              </div>
              <div v-if="v.character_arc" class="vol-card-meta">
                <span class="vol-card-label">角色弧线</span>
                <span class="vol-card-meta-val">{{ v.character_arc }}</span>
              </div>
              <div v-if="v.world_change" class="vol-card-meta">
                <span class="vol-card-label">世界观变化</span>
                <span class="vol-card-meta-val">{{ v.world_change }}</span>
              </div>
              <div v-if="v.foreshadowing_plan" class="vol-card-meta">
                <span class="vol-card-label">伏笔规划</span>
                <span class="vol-card-meta-val">{{ v.foreshadowing_plan }}</span>
              </div>
              <div v-if="v.turning_point" class="vol-card-meta">
                <span class="vol-card-label">关键转折</span>
                <span class="vol-card-meta-val">{{ v.turning_point }}</span>
              </div>
              <div v-if="v.emotional_tone" class="vol-card-meta">
                <span class="vol-card-label">情感基调</span>
                <span class="vol-card-meta-val">{{ v.emotional_tone }}</span>
              </div>
            </div>

            <div v-if="v.end_hook" class="vol-card-section vol-card-hook">
              <span class="vol-card-label">卷尾钩子</span>
              <p class="vol-card-text vol-card-hook-text">{{ v.end_hook }}</p>
            </div>

            <div class="vol-card-footer">
              <span v-if="v.estimated_words" class="vol-card-words">
                预估 {{ formatWords(v.estimated_words) }}
              </span>
              <div class="vol-card-footer-actions">
                <el-button size="small" @click="startEdit(v)">编辑</el-button>
                <el-button
                  size="small"
                  type="primary"
                  @click="goToOutlines(v)"
                >
                  查看细纲
                </el-button>
                <el-button
                  size="small"
                  type="success"
                  @click="viewChapters(v)"
                >
                  查看正文
                </el-button>
                <el-button
                  size="small"
                  type="warning"
                  plain
                  :loading="generatingVol === v.id"
                  @click="generateVol(v)"
                >
                  重新生成
                </el-button>
                <el-button size="small" type="danger" plain @click="removeVol(v)">删除</el-button>
              </div>
            </div>
          </template>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.vol-page {
  padding: 20px 24px;
}

.vol-page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.vol-page-title h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--text);
}

.vol-page-count {
  font-size: 13px;
  color: var(--text-dim);
  margin-top: 2px;
  display: block;
}

/* 故事线标签 */
.vol-storylines {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.vol-storylines-label {
  font-size: 13px;
  color: var(--text-dim);
  flex-shrink: 0;
}

.vol-storyline-tag {
  border-radius: 12px;
}

/* 空状态 */
.vol-empty {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-dim);
}

.vol-empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.vol-empty-hint {
  font-size: 13px;
  color: var(--text-secondary);
}

/* 全部完成 */
.vol-all-done {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: linear-gradient(135deg, rgba(103, 194, 58, 0.1), transparent);
  border: 1px solid rgba(103, 194, 58, 0.3);
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 16px;
  font-size: 14px;
  color: #67c23a;
  font-weight: 500;
}

/* 卡片列表 */
.vol-cards {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.vol-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 20px 24px;
  transition: box-shadow 0.2s, border-color 0.2s;
}

.vol-card:hover {
  border-color: var(--border-light);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.2);
}

.vol-card--empty {
  border-style: dashed;
  border-color: var(--border-light);
  background: var(--bg-input);
}

.vol-card--editing {
  border-color: var(--gold);
  box-shadow: 0 0 0 1px var(--gold);
}

/* 卡片头部 */
.vol-card-head {
  margin-bottom: 14px;
}

.vol-card-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.vol-card-number {
  font-size: 12px;
  font-weight: 600;
  color: var(--gold);
  background: var(--gold-glow);
  padding: 2px 8px;
  border-radius: 4px;
}

.vol-card-chapters {
  font-size: 12px;
  color: var(--text-dim);
}

.vol-card-status {
  margin-left: auto;
}

.vol-card-name {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
  line-height: 1.4;
}

.vol-card-subtitle {
  font-weight: 400;
  color: var(--text-secondary);
  font-size: 14px;
}

/* 内容区块 */
.vol-card-section {
  margin-bottom: 12px;
}

.vol-card-label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
}

.vol-card-text {
  margin: 0;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.7;
}

/* 关键节点 */
.vol-key-nodes {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.vol-key-node {
  font-size: 13px;
  color: var(--text-secondary);
  display: flex;
  align-items: baseline;
  gap: 8px;
  line-height: 1.5;
}

.vol-key-node-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  font-size: 11px;
  font-style: normal;
  font-weight: 600;
  color: var(--bg-deep);
  background: var(--gold);
  border-radius: 50%;
  flex-shrink: 0;
}

/* 情绪弧线 */
.vol-emotion-arc {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}

.vol-emotion-seg {
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
  background: var(--bg-input);
  padding: 2px 10px;
  border-radius: 12px;
  border: 1px solid var(--border);
}

.vol-emotion-arrow {
  color: var(--text-dim);
  font-size: 14px;
  margin: 0 2px;
}

/* 元信息网格 */
.vol-card-meta-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 12px;
}

.vol-card-meta {
  background: var(--bg-input);
  border-radius: 6px;
  padding: 8px 12px;
  border: 1px solid var(--border);
}

.vol-card-meta .vol-card-label {
  margin-bottom: 2px;
}

.vol-card-meta-val {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
}

/* 卷尾钩子 */
.vol-card-hook {
  background: linear-gradient(135deg, rgba(212, 163, 115, 0.08), transparent);
  border: 1px solid rgba(212, 163, 115, 0.2);
  border-radius: 8px;
  padding: 12px 14px;
  margin-bottom: 12px;
}

.vol-card-hook-text {
  color: var(--gold) !important;
  font-style: italic;
}

/* 底栏 */
.vol-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid var(--border);
  margin-top: 4px;
}

.vol-card-words {
  font-size: 13px;
  color: var(--gold);
  font-weight: 500;
}

.vol-card-footer-actions {
  display: flex;
  gap: 6px;
}

/* 未生成卷 */
.vol-card-empty-body {
  text-align: center;
  padding: 16px 0 8px;
  color: var(--text-dim);
  font-size: 13px;
}

.vol-card-empty-actions {
  margin-top: 12px;
  display: flex;
  justify-content: center;
  gap: 8px;
}

/* 编辑模式 */
.vol-edit {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.vol-edit-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.vol-edit-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.vol-edit-field label {
  font-size: 12px;
  color: var(--text-dim);
  font-weight: 500;
}

.vol-edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--border);
}
</style>
