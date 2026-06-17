<script setup>
import { ref, onMounted, watch, computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import { ElMessage } from "element-plus"
import { apiGet, apiPost } from "../api/index.js"

const props = defineProps({ book: Object })
const route = useRoute()
const router = useRouter()
const data = ref(null)
const allWriters = ref([])
const writerMap = computed(() => Object.fromEntries(allWriters.value.map(w => [w.id, w])))
const currentWriter = computed(() => data.value?.writer_id ? writerMap.value[data.value.writer_id] : null)
const editing = ref(false)
const form = ref({
  title: "", genre: "", brief: "", author_intent: "",
  excitement_direction: "", hook_type: "", storylines: [],
  world_building: "",
})

// 解析世界观中的【xxx】标记，返回分段数组
function parseWorldSections(text) {
  if (!text) return []
  const sections = []
  const regex = /【([^】]+)】/g
  let lastIndex = 0
  let match
  let currentTitle = ""
  let currentContent = ""

  // 先检查是否有【xxx】标记
  const matches = [...text.matchAll(regex)]
  if (matches.length === 0) {
    // 没有标记，整段作为一个区块
    return [{ title: "", content: text }]
  }

  for (let i = 0; i < matches.length; i++) {
    // 收集前一段内容
    if (i === 0 && matches[i].index > 0) {
      const prefix = text.substring(0, matches[i].index).trim()
      if (prefix) sections.push({ title: "", content: prefix })
    }
    // 收集当前段内容
    const title = matches[i][1]
    const start = matches[i].index + matches[i][0].length
    const end = i + 1 < matches.length ? matches[i + 1].index : text.length
    const content = text.substring(start, end).trim()
    if (content) sections.push({ title, content })
  }
  return sections
}

async function load() {
  try {
    allWriters.value = await apiGet("/writers")
  } catch {}
  try {
    const d = await apiGet(`/books/${route.params.bookId}`)
    let storylines = []
    if (typeof d.storylines === "string") {
      try { storylines = JSON.parse(d.storylines) } catch { storylines = [] }
    } else if (Array.isArray(d.storylines)) {
      storylines = d.storylines
    }
    d.storylines_parsed = storylines
    data.value = d
    form.value = {
      title: d.title || "", genre: d.genre || "", brief: d.brief || "",
      author_intent: d.author_intent || "",
      excitement_direction: d.excitement_direction || "",
      hook_type: d.hook_type || "",
      storylines: storylines,
      world_building: d.world_building || "",
    }
  } catch (e) { ElMessage.error("加载失败: " + e.message) }
}
onMounted(load)
watch(() => props.book, load)

async function saveBook() {
  try {
    await apiPost(`/books/${route.params.bookId}/update`, {
      ...form.value,
      storylines: JSON.stringify(form.value.storylines),
      world_building: form.value.world_building,
    })
    ElMessage.success("保存成功")
    editing.value = false
    await load()
  } catch (e) { ElMessage.error("保存失败: " + e.message) }
}

function addStoryline() {
  form.value.storylines.push({ name: "", type: "side", description: "" })
}
function removeStoryline(i) {
  form.value.storylines.splice(i, 1)
}
</script>

<template>
  <div class="page-header">
    <h2>创作蓝图</h2>
    <div style="display:flex;gap:8px;">
      <el-button v-if="!editing" @click="editing=true">编辑信息</el-button>
      <router-link :to="'/books/'+route.params.bookId+'/chapters'">
        <el-button type="primary">开始写作</el-button>
      </router-link>
    </div>
  </div>

  <div v-if="data" class="stats">
    <div class="stat-item"><div class="stat-value">{{ data.characters?.length || 0 }}</div><div class="stat-label">角色</div></div>
    <div class="stat-item"><div class="stat-value">{{ data.volumes?.length || 0 }}</div><div class="stat-label">分卷</div></div>
    <div class="stat-item"><div class="stat-value">{{ data.outlines?.length || 0 }}</div><div class="stat-label">细纲</div></div>
    <div class="stat-item"><div class="stat-value">{{ data.chapters?.length || 0 }}</div><div class="stat-label">章节</div></div>
  </div>

  <template v-if="!editing && data">
    <div class="overview-grid">
      <div class="card">
        <div class="card-header"><h3>基本信息</h3></div>
        <div style="margin-bottom:12px;"><strong style="color:var(--text-dim);font-size:12px;display:block;margin-bottom:4px;">作品名称</strong>{{ data.title }}</div>
        <div v-if="data.genre" style="margin-bottom:12px;"><strong style="color:var(--text-dim);font-size:12px;display:block;margin-bottom:4px;">类型</strong>{{ data.genre }}</div>
        <div v-if="currentWriter" style="margin-bottom:12px;">
          <strong style="color:var(--text-dim);font-size:12px;display:block;margin-bottom:4px;">写手</strong>
          <div style="display:flex;align-items:center;gap:8px;">
            <span style="font-size:24px;">{{ currentWriter.avatar }}</span>
            <div>
              <div style="font-weight:600;color:var(--gold-text);">{{ currentWriter.name }} <span style="font-size:12px;color:var(--gold);font-weight:400;">· {{ currentWriter.style }}</span></div>
              <div style="font-size:12px;color:var(--text-secondary);">{{ currentWriter.description }}</div>
            </div>
            <router-link :to="'/books/'+route.params.bookId+'/writer-select'" style="margin-left:auto;">
              <el-button size="small">更换写手</el-button>
            </router-link>
          </div>
        </div>
        <div v-if="!currentWriter" style="margin-bottom:12px;">
          <strong style="color:var(--text-dim);font-size:12px;display:block;margin-bottom:4px;">写手</strong>
          <div style="display:flex;align-items:center;gap:8px;">
            <span style="font-size:13px;color:var(--text-dim);">未选择写手（使用全局默认风格）</span>
            <router-link :to="'/books/'+route.params.bookId+'/writer-select'">
              <el-button size="small">选择写手</el-button>
            </router-link>
          </div>
        </div>
        <div v-if="data.brief" style="margin-bottom:12px;"><strong style="color:var(--text-dim);font-size:12px;display:block;margin-bottom:4px;">故事简介</strong><div style="color:var(--text-secondary);line-height:1.8;">{{ data.brief }}</div></div>
        <div v-if="data.author_intent" style="margin-bottom:12px;"><strong style="color:var(--text-dim);font-size:12px;display:block;margin-bottom:4px;">创作意图</strong><div style="color:var(--text-secondary);line-height:1.8;">{{ data.author_intent }}</div></div>
      </div>

      <div class="card">
        <div class="card-header"><h3>创作设定</h3></div>
        <div v-if="data.excitement_direction" style="margin-bottom:12px;"><strong style="color:var(--text-dim);font-size:12px;display:block;margin-bottom:4px;">爽点方向</strong><div style="color:var(--text-secondary);line-height:1.8;">{{ data.excitement_direction }}</div></div>
        <div v-if="data.hook_type" style="margin-bottom:12px;"><strong style="color:var(--text-dim);font-size:12px;display:block;margin-bottom:4px;">钩子类型</strong><div style="color:var(--text-secondary);line-height:1.8;">{{ data.hook_type }}</div></div>
        <div v-if="data.storylines_parsed && data.storylines_parsed.length > 0" style="margin-bottom:12px;">
          <strong style="color:var(--text-dim);font-size:12px;display:block;margin-bottom:8px;">故事线</strong>
          <div v-for="(sl, i) in data.storylines_parsed" :key="i" class="card" style="margin-bottom:8px;padding:12px;">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
              <span style="font-weight:600;font-size:14px;">{{ sl.name }}</span>
              <el-tag :type="sl.type === 'main' ? 'success' : 'info'" size="small">{{ sl.type === 'main' ? '主线' : '支线' }}</el-tag>
            </div>
            <div style="font-size:13px;color:var(--text-secondary);line-height:1.7;">{{ sl.description }}</div>
          </div>
        </div>
        <div v-if="data.world_building" style="margin-bottom:0;">
          <strong style="color:var(--text-dim);font-size:12px;display:block;margin-bottom:8px;">世界观设定</strong>
          <div v-for="(sec, i) in parseWorldSections(data.world_building)" :key="i" class="world-section">
            <div v-if="sec.title" class="world-section-title">{{ sec.title }}</div>
            <div class="world-section-content">{{ sec.content }}</div>
          </div>
        </div>
        <div v-if="!data.world_building && !data.excitement_direction && !data.hook_type && (!data.storylines_parsed || data.storylines_parsed.length === 0)" class="empty-state" style="padding:24px;">
          <p>暂无创作设定，点击"编辑信息"添加</p>
        </div>
      </div>
    </div>
  </template>

  <div v-if="editing" class="card">
    <div class="card-header"><h3>编辑作品信息</h3></div>
    <div class="form-group"><label>作品名称</label><el-input v-model="form.title" /></div>
    <div class="form-group"><label>类型</label><el-input v-model="form.genre" placeholder="玄幻, 科幻, 言情..." /></div>
    <div class="form-group"><label>故事简介</label><el-input v-model="form.brief" type="textarea" :rows="4" placeholder="简要描述整个故事的背景和主线..." /></div>
    <div class="form-group"><label>创作意图</label><el-input v-model="form.author_intent" type="textarea" :rows="4" placeholder="你想通过这个故事表达什么？" /></div>
    <div class="form-group"><label>爽点方向</label><el-input v-model="form.excitement_direction" type="textarea" :rows="3" placeholder="描述本书的核心爽感来源" /></div>
    <div class="form-group"><label>钩子类型</label><el-input v-model="form.hook_type" type="textarea" :rows="3" placeholder="描述断章钩子策略" /></div>
    <div class="form-group">
      <label>故事线</label>
      <div v-for="(sl, i) in form.storylines" :key="i" style="border:1px solid var(--border);border-radius:var(--radius-sm);padding:12px;margin-bottom:8px;">
        <div style="display:flex;gap:8px;margin-bottom:8px;">
          <el-input v-model="sl.name" placeholder="故事线名称" style="flex:1;" />
          <el-select v-model="sl.type" style="width:100px;"><el-option value="main" label="主线" /><el-option value="side" label="支线" /></el-select>
        </div>
        <el-input v-model="sl.description" type="textarea" :rows="2" placeholder="故事线描述" style="margin-bottom:8px;" />
        <div style="display:flex;gap:8px;align-items:center;justify-content:flex-end;">
          <el-button size="small" type="danger" @click="removeStoryline(i)">删除</el-button>
        </div>
      </div>
      <el-button size="small" @click="addStoryline">+ 添加故事线</el-button>
    </div>
    <div class="form-group">
      <label>世界观设定</label>
      <el-input v-model="form.world_building" type="textarea" :rows="6" placeholder="描述本书的世界观..." />
    </div>
    <div style="display:flex;gap:8px;">
      <el-button type="primary" @click="saveBook">保存</el-button>
      <el-button @click="editing=false">取消</el-button>
    </div>
  </div>
</template>

<style scoped>
.overview-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

@media (max-width: 1024px) {
  .overview-grid {
    grid-template-columns: 1fr;
  }
}

.world-section {
  margin-bottom: 12px;
  background: var(--bg-input);
  border-radius: 6px;
  padding: 10px 14px;
  border-left: 3px solid var(--gold-dim);
}

.world-section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--gold);
  margin-bottom: 6px;
}

.world-section-content {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.8;
}
</style>
