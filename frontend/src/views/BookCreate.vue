<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { apiGet, apiPost } from '../api/index.js'

const router = useRouter()
const title = ref('')
const selectedWriterId = ref('')
const loading = ref(false)
const writers = ref([])

onMounted(async () => {
  try { writers.value = await apiGet('/writers') } catch {}
})

async function create() {
  if (!title.value.trim()) return
  loading.value = true
  try {
    const params = { title: title.value.trim() }
    if (selectedWriterId.value) {
      params.writer_id = selectedWriterId.value
    }
    const result = await apiPost('/books', params)
    ElMessage.success('作品创建成功！')
    router.push('/books/' + result.id)
  } catch (e) {
    ElMessage.error('创建失败: ' + e.message)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page-header">
    <h2>新建作品</h2>
  </div>
  <div class="card" style="max-width:480px;">
    <div class="form-group">
      <label>作品名称</label>
      <el-input v-model="title" placeholder="给你的故事取个名字..." @keyup.enter="create" />
    </div>
    <div class="form-group">
      <label>选择写手（可选）</label>
      <el-select v-model="selectedWriterId" placeholder="使用默认风格" style="width:100%;">
        <el-option label="使用默认风格" value="" />
        <el-option v-for="w in writers" :key="w.id" :label="`${w.avatar} ${w.name} · ${w.style}`" :value="w.id" />
      </el-select>
    </div>
    <div style="display:flex;gap:8px;">
      <el-button type="primary" :disabled="loading || !title.trim()" :loading="loading" @click="create">
        {{ loading ? '创建中...' : '创建作品' }}
      </el-button>
      <router-link to="/"><el-button>取消</el-button></router-link>
    </div>
  </div>
</template>
