<script setup>
import { ref, onMounted, watch } from "vue"
import { useRoute } from "vue-router"
import { apiGet, apiPost } from "../api/index.js"
import { ElMessage, ElMessageBox } from "element-plus"

const props = defineProps({ book: Object })
const route = useRoute()
const chars = ref([])
const showModal = ref(false)
const editing = ref(null)
const form = ref({ name: "", description: "", background: "", appearance: "", traits: "", relationships: "" })

async function load() {
  try {
    const data = await apiGet(`/books/${route.params.bookId}/characters`)
    chars.value = Array.isArray(data) ? data : []
  } catch (e) {
    ElMessage.error("加载失败: " + e.message)
  }
}
onMounted(load)
watch(() => route.params.bookId, load)

function openAdd() {
  editing.value = null
  form.value = { name: "", description: "", background: "", appearance: "", traits: "", relationships: "", emotion_profile: "" }
  showModal.value = true
}

function openEdit(c) {
  editing.value = c
  form.value = {
    name: c.name || "",
    description: c.description || "",
    background: c.background || "",
    appearance: c.appearance || "",
    traits: Array.isArray(c.traits) ? c.traits.join("、") : (c.traits || ""),
    relationships: Array.isArray(c.relationships)
      ? c.relationships.map(r => `${r.relation}（${r.target}）`).join("、")
      : (typeof c.relationships === "string" ? c.relationships : ""),
    emotion_profile: c.emotion_profile || ""
  }
  showModal.value = true
}

async function save() {
  if (!form.value.name.trim()) return ElMessage.warning("请输入角色姓名")
  try {
    if (editing.value?.id) {
      await apiPost(`/characters/${editing.value.id}/update`, form.value)
    } else {
      await apiPost(`/books/${route.params.bookId}/characters`, form.value)
    }
    ElMessage.success("保存成功")
    showModal.value = false
    await load()
  } catch (e) {
    ElMessage.error("保存失败: " + e.message)
  }
}

async function remove(c) {
  try {
    await ElMessageBox.confirm(`确定删除角色「${c.name}」？`, "提示", { type: "warning" })
    await apiPost(`/characters/${c.id}/delete`, {})
    ElMessage.success("已删除")
    await load()
  } catch (e) {
    if (e !== "cancel") ElMessage.error("删除失败: " + e.message)
  }
}

function parseTraits(t) {
  if (Array.isArray(t)) return t
  if (typeof t === "string" && t.startsWith("[")) { try { return JSON.parse(t) } catch {} }
  if (typeof t === "string") return t.split(/[,，、]/).map(s => s.trim()).filter(Boolean)
  return []
}

function parseRels(r) {
  if (Array.isArray(r)) return r
  if (typeof r === "string") { try { return JSON.parse(r) } catch {} }
  return []
}
</script>

<template>
  <div class="char-page">
    <div class="page-header">
      <h2>角色体系</h2>
      <el-button type="primary" @click="openAdd">+ 新增角色</el-button>
    </div>

    <div v-if="chars.length === 0" class="empty-state">
      <p>还没有角色，开始创建你的角色吧</p>
    </div>

    <div v-else class="char-grid">
      <div v-for="c in chars" :key="c.id" class="char-card">
        <!-- 卡片头部 -->
        <div class="char-card-header">
          <div class="char-avatar">{{ c.name?.charAt(0) }}</div>
          <div class="char-card-title">
            <div class="char-card-name">{{ c.name }}</div>
            <div class="char-card-desc" v-if="c.description">{{ c.description }}</div>
          </div>
          <div class="char-card-actions">
            <el-button size="small" type="primary" @click.stop="openEdit(c)">编辑</el-button>
            <el-button size="small" type="danger" plain @click.stop="remove(c)">删除</el-button>
          </div>
        </div>

        <!-- 性格特质 -->
        <div class="char-section" v-if="parseTraits(c.traits).length">
          <span class="char-label">性格特质</span>
          <div class="char-tags">
            <el-tag v-for="t in parseTraits(c.traits)" :key="t" size="small" type="warning" effect="dark">{{ t }}</el-tag>
          </div>
        </div>

        <!-- 背景故事 -->
        <div class="char-section" v-if="c.background">
          <span class="char-label">背景故事</span>
          <p class="char-text">{{ c.background }}</p>
        </div>

        <!-- 外貌描写 -->
        <div class="char-section" v-if="c.appearance">
          <span class="char-label">外貌描写</span>
          <p class="char-text">{{ c.appearance }}</p>
        </div>

        <!-- 人际关系 -->
        <div class="char-section" v-if="parseRels(c.relationships).length">
          <span class="char-label">人际关系</span>
          <div class="char-rels">
            <div v-for="(r, i) in parseRels(c.relationships)" :key="i" class="char-rel-item">
              <span class="char-rel-type">{{ r.relation }}</span>
              <span class="char-rel-arrow">→</span>
              <span class="char-rel-target">{{ r.target }}</span>
            </div>
          </div>
        </div>
        <!-- 情绪反应模式 -->
        <div class="char-section" v-if="c.emotion_profile">
          <span class="char-label">情绪反应模式</span>
          <p class="char-text">{{ c.emotion_profile }}</p>
        </div>
      </div>
    </div>
  </div>

  <!-- 编辑弹窗 -->
  <el-dialog v-model="showModal" :title="editing ? '编辑角色' : '新增角色'" width="600px" append-to-body destroy-on-close>
    <el-form label-position="top">
      <el-form-item label="姓名 *"><el-input v-model="form.name" /></el-form-item>
      <el-form-item label="角色描述"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
      <el-form-item label="背景故事"><el-input v-model="form.background" type="textarea" :rows="3" /></el-form-item>
      <el-form-item label="外貌描写"><el-input v-model="form.appearance" type="textarea" :rows="2" /></el-form-item>
      <el-form-item label="性格特质（顿号或逗号分隔）"><el-input v-model="form.traits" placeholder="勇敢、机智、内向..." /></el-form-item>
      <el-form-item label="人际关系（顿号或逗号分隔）"><el-input v-model="form.relationships" placeholder="对手（张三）、师徒（李四）..." /></el-form-item>
      <el-form-item label="情绪反应模式"><el-input v-model="form.emotion_profile" type="textarea" :rows="2" placeholder="紧张时会用冷笑话来掩饰，愤怒时反而变得特别冷静…" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showModal=false">取消</el-button>
      <el-button type="primary" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.char-page { padding: 20px 24px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h2 { margin: 0; font-size: 20px; font-weight: 600; }

.char-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 16px;
}

.char-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 16px;
  transition: border-color 0.2s;
}

.char-card:hover {
  border-color: var(--border-light);
}

.char-card-header {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 12px;
}

.char-avatar {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: var(--bg-input);
  border: 2px solid var(--gold-dim);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 700;
  color: var(--gold);
  flex-shrink: 0;
}

.char-card-title { flex: 1; min-width: 0; }
.char-card-name { font-weight: 600; font-size: 15px; }
.char-card-desc { font-size: 12px; color: var(--text-dim); margin-top: 2px; }

.char-card-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s;
}

.char-card:hover .char-card-actions { opacity: 1; }

.char-section { margin-bottom: 10px; }
.char-section:last-child { margin-bottom: 0; }

.char-label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
}

.char-text {
  margin: 0;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
}

.char-tags { display: flex; flex-wrap: wrap; gap: 4px; }

.char-rels { display: flex; flex-wrap: wrap; gap: 6px; }

.char-rel-item {
  font-size: 12px;
  color: var(--text-secondary);
  background: var(--bg-input);
  padding: 2px 8px;
  border-radius: 4px;
}

.char-rel-type { color: var(--gold-dim); }
.char-rel-arrow { margin: 0 4px; color: var(--text-dim); }
.char-rel-target { color: var(--text); }
</style>
