<script setup>
import { ref, onMounted } from "vue"
import { useRoute, useRouter } from "vue-router"
import { ElMessage } from "element-plus"
import { apiGet, apiPost } from "../api/index.js"

const props = defineProps({ book: Object })
const route = useRoute()
const router = useRouter()
const chapter = ref(null)

async function load() {
  try {
    const bid = route.params.bookId
    const cid = route.params.chapterId
    chapter.value = await apiGet(`/books/${bid}/chapters/${cid}`)
  } catch (e) { ElMessage.error("加载失败: " + e.message) }
}
onMounted(load)

async function approve() {
  try {
    await apiPost(`/chapters/${route.params.chapterId}/approve`, {})
    ElMessage.success("已批准")
    await load()
  } catch (e) { ElMessage.error("批准失败: " + e.message) }
}

async function qc() {
  try {
    const r = await apiPost(`/chapters/${route.params.chapterId}/qc`, {})
    if (r.report) ElMessage.info("质检完成: " + r.report)
    else ElMessage.success("质检完成")
  } catch (e) { ElMessage.error("质检失败: " + e.message) }
}
</script>

<template>
  <div v-if="chapter" class="chapter-page">
    <div class="page-header">
      <h2>第{{ chapter.chapter_number }}章 {{ chapter.title || "" }}</h2>
      <div style="display:flex;gap:8px;">
        <router-link :to="'/books/'+route.params.bookId+'/chapters'">
          <el-button>← 返回</el-button>
        </router-link>
        <el-button type="success" @click="approve">批准</el-button>
        <el-button @click="qc">QC质检</el-button>
      </div>
    </div>
    <div class="stats" style="margin-bottom:20px;">
      <div class="stat-item"><div class="stat-value">{{ chapter.word_count || 0 }}</div><div class="stat-label">字数</div></div>
      <div class="stat-item"><div class="stat-value"><el-tag :type="chapter.status === 'approved' ? 'success' : 'info'">{{ chapter.status }}</el-tag></div><div class="stat-label">状态</div></div>
    </div>
    <div class="card" style="max-width:800px;margin:0 auto;">
      <div class="chapter-content"><pre>{{ chapter.content }}</pre></div>
    </div>
  </div>
</template>
