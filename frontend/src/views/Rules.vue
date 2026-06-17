<script setup>
import { ref, onMounted } from "vue"
import { useRoute } from "vue-router"
import { ElMessage, ElMessageBox } from "element-plus"
import { apiGet, apiPost } from "../api/index.js"

const props = defineProps({ book: Object })
const route = useRoute()
const rules = ref([])
const showModal = ref(false)
const editing = ref(null)
const form = ref({ name: "", description: "", check_content: "", severity: "warning" })

async function load() {
  try { rules.value = await apiGet(`/books/${route.params.bookId}/rules`) }
  catch (e) { ElMessage.error("加载失败: " + e.message) }
}
onMounted(load)

function openAdd() { editing.value = null; form.value = { name: "", description: "", check_content: "", severity: "warning" }; showModal.value = true }
function openEdit(r) { editing.value = r; form.value = { name: r.name, description: r.description || "", check_content: r.check_content || "", severity: r.severity || "warning" }; showModal.value = true }

async function save() {
  if (!form.value.name.trim()) return
  try {
    if (editing.value) { await apiPost(`/rules/${editing.value.id}/update`, form.value) }
    else { await apiPost(`/books/${route.params.bookId}/rules`, form.value) }
    ElMessage.success("保存成功"); showModal.value = false; await load()
  } catch (e) { ElMessage.error("保存失败: " + e.message) }
}

async function remove(r) {
  try {
    await ElMessageBox.confirm(`确定删除「${r.name}」？`, "删除确认", { type: "warning" })
  } catch { return }
  try { await apiPost(`/rules/${r.id}/delete`, {}); ElMessage.success("已删除"); await load() }
  catch (e) { ElMessage.error("删除失败: " + e.message) }
}
</script>

<template>
  <div class="page-header">
    <h2>QC质检</h2>
    <el-button type="primary" @click="openAdd">+ 新增规则</el-button>
  </div>
  <p class="desc-text">配置要避免的问题，生成章节后会自动进行质检。</p>
  <div v-if="rules.length === 0" class="empty-state"><p>还没有质检规则</p></div>
  <div v-for="r in rules" :key="r.id" class="card">
    <div style="display:flex;justify-content:space-between;align-items:center;">
      <div>
        <strong>{{ r.name }}</strong>
        <el-tag :type="r.severity === 'error' ? 'danger' : 'warning'" size="small" style="margin-left:8px;">{{ r.severity }}</el-tag>
      </div>
      <div style="display:flex;gap:6px;">
        <el-button size="small" @click="openEdit(r)">编辑</el-button>
        <el-button size="small" type="danger" @click="remove(r)">删除</el-button>
      </div>
    </div>
    <div v-if="r.description" style="margin-top:6px;color:var(--text-dim);font-size:12px;">{{ r.description }}</div>
  </div>

  <el-dialog v-model="showModal" :title="editing ? '编辑规则' : '新增规则'" width="500px">
    <div class="form-group"><label>规则名称</label><el-input v-model="form.name" /></div>
    <div class="form-group"><label>说明</label><el-input v-model="form.description" type="textarea" :rows="2" /></div>
    <div class="form-group"><label>检查内容</label><el-input v-model="form.check_content" type="textarea" :rows="4" /></div>
    <div class="form-group"><label>严重程度</label>
      <el-select v-model="form.severity" style="width:100%;">
        <el-option value="warning" label="警告" />
        <el-option value="error" label="严重" />
      </el-select>
    </div>
    <template #footer>
      <el-button @click="showModal=false">取消</el-button>
      <el-button type="primary" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>
