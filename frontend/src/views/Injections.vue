<script setup>
import { ref, onMounted } from "vue"
import { useRoute } from "vue-router"
import { ElMessage, ElMessageBox } from "element-plus"
import { apiGet, apiPost } from "../api/index.js"

const props = defineProps({ book: Object })
const route = useRoute()
const injections = ref([])
const showModal = ref(false)
const editing = ref(null)
const form = ref({ name: "", content: "", category: "style" })

async function load() {
  try { injections.value = await apiGet(`/books/${route.params.bookId}/injections`) }
  catch (e) { ElMessage.error("加载失败: " + e.message) }
}
onMounted(load)

function openAdd() { editing.value = null; form.value = { name: "", content: "", category: "style" }; showModal.value = true }
function openEdit(i) { editing.value = i; form.value = { name: i.name, content: i.content || "", category: i.category || "style" }; showModal.value = true }

async function save() {
  if (!form.value.name.trim() || !form.value.content.trim()) return
  try {
    if (editing.value) { await apiPost(`/injections/${editing.value.id}/update`, form.value) }
    else { await apiPost(`/books/${route.params.bookId}/injections`, form.value) }
    ElMessage.success("保存成功"); showModal.value = false; await load()
  } catch (e) { ElMessage.error("保存失败: " + e.message) }
}

async function remove(i) {
  try {
    await ElMessageBox.confirm(`确定删除「${i.name}」？`, "删除确认", { type: "warning" })
  } catch { return }
  try { await apiPost(`/injections/${i.id}/delete`, {}); ElMessage.success("已删除"); await load() }
  catch (e) { ElMessage.error("删除失败: " + e.message) }
}
</script>

<template>
  <div class="page-header">
    <h2>写作风格</h2>
    <el-button type="primary" @click="openAdd">+ 新增指令</el-button>
  </div>
  <p class="desc-text">添加 AI 风格指令，每次写作时会自动注入到 Prompt 中。</p>
  <div v-if="injections.length === 0" class="empty-state"><p>还没有风格指令</p></div>
  <div v-for="i in injections" :key="i.id" class="card">
    <div style="display:flex;justify-content:space-between;align-items:center;">
      <div>
        <strong>{{ i.name }}</strong>
        <el-tag :type="i.is_active ? 'success' : 'info'" size="small" style="margin-left:8px;">{{ i.category }}</el-tag>
      </div>
      <div style="display:flex;gap:6px;">
        <el-button size="small" @click="openEdit(i)">编辑</el-button>
        <el-button size="small" type="danger" @click="remove(i)">删除</el-button>
      </div>
    </div>
    <div style="margin-top:8px;color:var(--text-secondary);font-size:13px;white-space:pre-wrap;">{{ i.content }}</div>
  </div>

  <el-dialog v-model="showModal" :title="editing ? '编辑指令' : '新增指令'" width="500px">
    <div class="form-group"><label>名称</label><el-input v-model="form.name" /></div>
    <div class="form-group"><label>类别</label>
      <el-select v-model="form.category" style="width:100%;">
        <el-option value="style" label="风格" />
        <el-option value="tone" label="语调" />
        <el-option value="format" label="格式" />
        <el-option value="other" label="其他" />
      </el-select>
    </div>
    <div class="form-group"><label>内容</label><el-input v-model="form.content" type="textarea" :rows="6" /></div>
    <template #footer>
      <el-button @click="showModal=false">取消</el-button>
      <el-button type="primary" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>
