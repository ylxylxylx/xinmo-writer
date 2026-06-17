<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { apiGet, apiPost } from '../api/index.js'

const route = useRoute()
const router = useRouter()
const bookId = route.params.bookId
const selectedId = ref(null)
const loading = ref(false)
const book = ref(null)
const writers = ref([])

onMounted(async () => {
  try {
    writers.value = await apiGet('/writers')
  } catch {}
  try {
    book.value = await apiGet(`/books/${bookId}`)
    if (book.value?.writer_id) {
      selectedId.value = book.value.writer_id
    }
  } catch {}
})

function selectWriter(w) {
  selectedId.value = w.id
}

async function confirmSelection() {
  if (!selectedId.value) {
    ElMessage.error('请先选择一位写手')
    return
  }
  loading.value = true
  try {
    await apiPost(`/writers/${selectedId.value}/apply`, { book_id: bookId })
    ElMessage.success('写手已应用！')
    router.push(`/books/${bookId}`)
  } catch (e) {
    ElMessage.error('应用失败: ' + e.message)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page-header">
    <h2>选择你的写手</h2>
  </div>
  <p style="color:var(--text-secondary);margin-bottom:24px;font-size:14px;">
    每个写手有独特的写作风格，选择最适合你小说的
  </p>

  <div class="writer-grid">
    <div
      v-for="w in writers"
      :key="w.id"
      class="writer-card"
      :class="{ selected: selectedId === w.id }"
      @click="selectWriter(w)"
    >
      <div class="writer-avatar">{{ w.avatar }}</div>
      <div class="writer-info">
        <div class="writer-name">{{ w.name }}</div>
        <div class="writer-style-tag">{{ w.style }}</div>
        <div class="writer-desc">{{ w.description }}</div>
        <div class="writer-genres">
          <el-tag v-for="g in w.genres" :key="g" size="small" type="success" style="font-size:11px;">{{ g }}</el-tag>
        </div>
      </div>
    </div>
  </div>

  <div style="display:flex;gap:12px;margin-top:24px;">
    <el-button
      type="primary"
      :disabled="loading || !selectedId"
      :loading="loading"
      @click="confirmSelection"
    >
      {{ loading ? '应用中...' : '确认选择' }}
    </el-button>
    <router-link :to="'/books/' + bookId"><el-button>取消</el-button></router-link>
  </div>
</template>

<style scoped>
.writer-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

@media (max-width: 1200px) {
  .writer-grid { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 900px) {
  .writer-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 600px) {
  .writer-grid { grid-template-columns: 1fr; }
}

.writer-card {
  background: var(--bg-card);
  border: 2px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.writer-card:hover {
  border-color: var(--gold-dim);
  background: var(--bg-card-hover);
  transform: translateY(-2px);
}

.writer-card.selected {
  border-color: var(--gold);
  background: var(--gold-glow);
  box-shadow: 0 0 20px rgba(212, 175, 55, 0.15);
}

.writer-avatar {
  font-size: 48px;
  margin-bottom: 12px;
  line-height: 1;
}

.writer-name {
  font-family: var(--font-heading);
  font-size: 18px;
  font-weight: 700;
  color: var(--gold-text);
  margin-bottom: 6px;
}

.writer-style-tag {
  display: inline-block;
  font-size: 12px;
  color: var(--gold);
  background: var(--gold-glow);
  border: 1px solid var(--gold-dim);
  border-radius: 4px;
  padding: 2px 10px;
  margin-bottom: 10px;
}

.writer-desc {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.7;
  margin-bottom: 12px;
}

.writer-genres {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  justify-content: center;
}

.genre-tag {
  font-size: 11px;
  color: var(--jade);
  background: rgba(90, 158, 122, 0.1);
  border: 1px solid rgba(90, 158, 122, 0.2);
  border-radius: 3px;
  padding: 2px 8px;
}
</style>
