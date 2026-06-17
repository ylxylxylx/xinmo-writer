<script setup>
import { ref, onMounted, watch } from "vue"
import { useRoute } from "vue-router"
import { ElMessage, ElMessageBox } from "element-plus"
import { apiGet, apiPost } from "../api/index.js"

const props = defineProps({ book: Object })
const route = useRoute()
const bookId = route.params.bookId

const foreshadowing = ref([])
const showDialog = ref(false)
const editIndex = ref(-1)
const form = ref({
  name: "",
  description: "",
  plant_chapter: "",
  resolve_chapter: "",
  status: "planned",
})

const statusMap = {
  planned: "规划中",
  planted: "已埋笔",
  resolved: "已收笔",
  unresolved: "未收笔",
}

async function load() {
  try {
    const d = await apiGet(`/books/${bookId}`)
    let fs = []
    if (typeof d.foreshadowing === "string") {
      try { fs = JSON.parse(d.foreshadowing) } catch { fs = [] }
    } else if (Array.isArray(d.foreshadowing)) {
      fs = d.foreshadowing
    }
    foreshadowing.value = fs
  } catch (e) {
    ElMessage.error("加载失败: " + e.message)
  }
}

onMounted(load)
watch(() => props.book, load)

function openAdd() {
  form.value = { name: "", description: "", plant_chapter: "", resolve_chapter: "", status: "planned" }
  editIndex.value = -1
  showDialog.value = true
}

function openEdit(index) {
  const fs = foreshadowing.value[index]
  form.value = {
    name: fs.name || "",
    description: fs.description || "",
    plant_chapter: fs.plant_chapter || "",
    resolve_chapter: fs.resolve_chapter || "",
    status: fs.status || "planned",
  }
  editIndex.value = index
  showDialog.value = true
}

function closeDialog() {
  showDialog.value = false
  editIndex.value = -1
}

async function save() {
  if (!form.value.name.trim()) {
    ElMessage.error("请填写伏笔名称")
    return
  }
  const list = [...foreshadowing.value]
  const item = { ...form.value }
  if (editIndex.value >= 0) {
    list[editIndex.value] = item
  } else {
    list.push(item)
  }
  try {
    await apiPost(`/books/${bookId}/update`, { foreshadowing: JSON.stringify(list) })
    ElMessage.success("保存成功")
    closeDialog()
    await load()
  } catch (e) {
    ElMessage.error("保存失败: " + e.message)
  }
}

async function remove(index) {
  try {
    await ElMessageBox.confirm("确定删除该伏笔？", "删除确认", { type: "warning" })
  } catch { return }
  const list = foreshadowing.value.filter((_, i) => i !== index)
  try {
    await apiPost(`/books/${bookId}/update`, { foreshadowing: JSON.stringify(list) })
    ElMessage.success("已删除")
    await load()
  } catch (e) {
    ElMessage.error("删除失败: " + e.message)
  }
}

function statusClass(status) {
  const map = { planned: "foreshadowing-planned", planted: "foreshadowing-planted", resolved: "foreshadowing-resolved", unresolved: "foreshadowing-unresolved" }
  return map[status] || "foreshadowing-planned"
}
</script>

<template>
  <div class="page-header">
    <h2>伏笔总表</h2>
    <el-button type="primary" @click="openAdd">+ 新增伏笔</el-button>
  </div>

  <div v-if="foreshadowing.length === 0" class="empty-state">
    <div class="empty-icon">🔗</div>
    <p>暂无伏笔记录，点击「+ 新增伏笔」开始规划</p>
  </div>

  <div v-else class="card" style="padding:0;">
    <el-table :data="foreshadowing" style="width:100%;">
      <el-table-column prop="name" label="名称" width="140" />
      <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
      <el-table-column label="埋笔章" width="100">
        <template #default="{ row }">{{ row.plant_chapter || '-' }}</template>
      </el-table-column>
      <el-table-column label="收笔章" width="100">
        <template #default="{ row }">{{ row.resolve_chapter || '-' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <span class="foreshadowing-status" :class="statusClass(row.status)">
            {{ statusMap[row.status] || row.status || '规划中' }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ $index }">
          <el-button size="small" @click.stop="openEdit($index)">编辑</el-button>
          <el-button size="small" type="danger" @click.stop="remove($index)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>

  <el-dialog v-model="showDialog" :title="editIndex >= 0 ? '编辑伏笔' : '新增伏笔'" width="520px" :close-on-click-modal="true">
    <div class="form-group">
      <label>伏笔名称 *</label>
      <el-input v-model="form.name" placeholder="如：神秘玉佩" />
    </div>
    <div class="form-group">
      <label>描述</label>
      <el-input v-model="form.description" type="textarea" :rows="3" placeholder="描述伏笔的内容和预期走向" />
    </div>
    <div class="form-group">
      <label>状态</label>
      <el-select v-model="form.status" style="width:100%;">
        <el-option value="planned" label="规划中" />
        <el-option value="planted" label="已埋笔" />
        <el-option value="resolved" label="已收笔" />
        <el-option value="unresolved" label="未收笔" />
      </el-select>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>埋笔章</label>
        <el-input v-model="form.plant_chapter" placeholder="如：第3章" />
      </div>
      <div class="form-group">
        <label>收笔章</label>
        <el-input v-model="form.resolve_chapter" placeholder="如：第25章" />
      </div>
    </div>
    <template #footer>
      <el-button @click="closeDialog">取消</el-button>
      <el-button type="primary" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>
