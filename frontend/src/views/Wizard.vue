<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { apiGet, apiPost } from '../api/index.js'

const router = useRouter()
const writers = ref([])

const step = ref(0)
const idea = ref('')
const loading = ref(false)
const genres = ref([])
const selectedGenre = ref(null)
const names = ref([])
const selectedName = ref(null)
const targetWords = ref(600000)
const selectedWriterId = ref('')
const ideas = ref([])
const customWords = ref(60)
const showCustomWords = computed(() => targetWords.value === -1)

onMounted(async () => {
  try { writers.value = await apiGet('/writers') } catch {}
})

async function suggestIdeas() {
  loading.value = true
  try {
    const res = await apiPost("/wizard/suggest-ideas", {})
    ideas.value = res.candidates || []
  } catch (e) {
    ElMessage.error("创意推荐失败: " + e.message)
  } finally {
    loading.value = false
  }
}

function selectIdea(ideaText) {
  idea.value = ideaText
  ideas.value = []
  fetchGenres()
}

async function fetchGenres() {
  if (!idea.value.trim()) return
  loading.value = true
  try {
    const res = await apiPost('/wizard/genres', { idea: idea.value.trim() })
    genres.value = res.candidates || []
    if (genres.value.length === 0) {
      ElMessage.error('未获取到推荐题材，请重试')
    } else {
      step.value = 1
    }
  } catch (e) {
    ElMessage.error('生成失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

function selectGenre(g) {
  selectedGenre.value = g
  step.value = 2
  fetchNames()
}

async function fetchNames() {
  loading.value = true
  try {
    const res = await apiPost('/wizard/names', {
      idea: idea.value.trim(),
      genre: selectedGenre.value.name,
    })
    names.value = res.candidates || []
    if (names.value.length === 0) ElMessage.error('未获取到书名推荐，请重试')
  } catch (e) {
    ElMessage.error('生成失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

function selectName(n) {
  selectedName.value = n
  step.value = 3
}

function selectWriter(w) {
  selectedWriterId.value = w.id
}

function confirmWriter() {
  step.value = 4
}

async function generate() {
  loading.value = true
  try {
    const params = {
      idea: idea.value.trim(),
      genre: selectedGenre.value.name,
      title: selectedName.value.title,
      brief: selectedName.value.brief,
      target_words: targetWords.value,
    }
    if (selectedWriterId.value) {
      params.writer_id = selectedWriterId.value
    }
    const res = await apiPost('/wizard/generate', params)
    ElMessage.success('设定生成完成！')
    router.push('/books/' + res.book_id)
  } catch (e) {
    ElMessage.error('生成失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

function goBack() {
  if (step.value === 1) { step.value = 0; selectedGenre.value = null; genres.value = [] }
  else if (step.value === 2) { step.value = 1; selectedName.value = null }
  else if (step.value === 3) { step.value = 2 }
  else if (step.value === 4) { step.value = 3 }
}
</script>

<template>
  <div class="page-header">
    <h2>创作向导</h2>
  </div>

  <!-- Step indicator -->
  <el-steps :active="step" finish-status="success" align-center style="margin-bottom: 24px;">
    <el-step title="输入创意" />
    <el-step title="选择题材" />
    <el-step title="选择书名" />
    <el-step title="选择写手" />
    <el-step title="生成设定" />
  </el-steps>

  <!-- Step 0: 输入创意 -->
  <div v-if="step === 0" class="card">
    <el-input
      v-model="idea"
      type="textarea"
      :rows="4"
      placeholder="描述你的小说创意，越详细越好...例如：一个普通人穿越到末日世界，发现自己拥有了一辆可以升级的房车，他从独狼开始，一步步建立起自己的联盟..."
    />
    <div style="display:flex;gap:8px;margin-top:16px;">
      <el-button :disabled="loading" :loading="loading" @click="suggestIdeas">💡 创意推荐</el-button>
      <el-button type="primary" :disabled="loading || !idea.trim()" :loading="loading" @click="fetchGenres">
        {{ loading ? 'AI 思考中...' : '生成题材' }}
      </el-button>
    </div>

    <div v-if="ideas.length > 0" style="margin-top:20px;">
      <div class="idea-cards">
        <div
          v-for="(item, idx) in ideas"
          :key="idx"
          class="idea-card"
          @click="selectIdea(typeof item === 'string' ? item : (item.idea + (item.brief ? '——' + item.brief : '')))"
        >
          <div class="idea-card-text">{{ typeof item === 'string' ? item : item.idea }}</div>
          <div v-if="typeof item === 'object' && item.brief" class="idea-card-brief">{{ item.brief }}</div>
        </div>
      </div>
    </div>
  </div>

  <!-- Step 1: 选择题材 -->
  <div v-if="step === 1" class="card">
    <div style="margin-bottom:16px;">
      <span style="color:var(--text-dim);font-size:12px;">创意：</span>
      <span style="font-size:13px;">{{ idea }}</span>
    </div>

    <div v-if="loading" style="text-align:center;padding:32px;color:var(--text-dim);">
      AI 正在推荐题材...
    </div>

    <div v-else-if="genres.length > 0" class="wizard-cards">
      <div class="wizard-card" v-for="g in genres" :key="g.name" @click="selectGenre(g)">
        <div class="wizard-card-title">{{ g.name }}</div>
        <div class="wizard-card-desc">{{ g.brief }}</div>
      </div>
    </div>

    <el-button style="margin-top:16px;" @click="goBack">返回上一步</el-button>
  </div>

  <!-- Step 2: 选择书名 -->
  <div v-if="step === 2" class="card">
    <div style="margin-bottom:16px;">
      <span style="color:var(--text-dim);font-size:12px;">创意：</span>
      <span style="font-size:13px;">{{ idea }}</span>
      <span style="color:var(--gold);font-size:12px;margin-left:12px;">题材：</span>
      <span style="font-size:13px;">{{ selectedGenre?.name }}</span>
    </div>

    <div v-if="loading" style="text-align:center;padding:32px;color:var(--text-dim);">
      AI 正在构思书名...
    </div>

    <div v-else-if="names.length > 0" class="wizard-cards">
      <div class="wizard-card" v-for="n in names" :key="n.title" @click="selectName(n)">
        <div class="wizard-card-title">{{ n.title }}</div>
        <div class="wizard-card-desc">{{ n.brief }}</div>
        <div class="wizard-card-hook">{{ n.hook }}</div>
      </div>
    </div>

    <el-button style="margin-top:16px;" @click="goBack">返回上一步</el-button>
  </div>

  <!-- Step 3: 选择写手 -->
  <div v-if="step === 3" class="card">
    <div style="margin-bottom:16px;">
      <span style="color:var(--text-dim);font-size:12px;">书名：</span>
      <span style="font-size:14px;color:var(--gold);font-weight:600;">{{ selectedName?.title }}</span>
    </div>
    <p style="color:var(--text-secondary);margin-bottom:20px;font-size:13px;">
      选择一位写手来定义你的小说风格（可选，也可跳过）
    </p>

    <div class="wizard-writer-grid">
      <div
        v-for="w in writers"
        :key="w.id"
        class="wizard-writer-card"
        :class="{ selected: selectedWriterId === w.id }"
        @click="selectWriter(w)"
      >
        <div class="wizard-writer-avatar">{{ w.avatar }}</div>
        <div class="wizard-writer-name">{{ w.name }}</div>
        <div class="wizard-writer-style">{{ w.style }}</div>
        <div class="wizard-writer-desc">{{ w.description }}</div>
      </div>
    </div>

    <div style="display:flex;gap:8px;margin-top:20px;">
      <el-button type="primary" @click="confirmWriter">
        {{ selectedWriterId ? '确认选择' : '跳过，使用默认风格' }}
      </el-button>
      <el-button @click="goBack">返回上一步</el-button>
    </div>
  </div>

  <!-- Step 4: 生成设定 -->
  <div v-if="step === 4" class="card">
    <div style="margin-bottom:20px;">
      <div style="margin-bottom:12px;">
        <span style="color:var(--text-dim);font-size:12px;display:block;margin-bottom:4px;">书名</span>
        <span style="font-size:18px;font-weight:600;color:var(--gold);font-family:var(--font-heading);">{{ selectedName?.title }}</span>
      </div>
      <div style="margin-bottom:12px;">
        <span style="color:var(--text-dim);font-size:12px;display:block;margin-bottom:4px;">简介</span>
        <span style="font-size:13px;color:var(--text-secondary);line-height:1.8;">{{ selectedName?.brief }}</span>
      </div>
      <div style="margin-bottom:12px;">
        <span style="color:var(--text-dim);font-size:12px;display:block;margin-bottom:4px;">卖点</span>
        <span style="font-size:13px;">{{ selectedName?.hook }}</span>
      </div>
      <div v-if="selectedWriterId">
        <span style="color:var(--text-dim);font-size:12px;display:block;margin-bottom:4px;">写手</span>
        <span style="font-size:13px;">{{ writers.find(w => w.id === selectedWriterId)?.avatar }} {{ writers.find(w => w.id === selectedWriterId)?.name }} · {{ writers.find(w => w.id === selectedWriterId)?.style }}</span>
      </div>
    </div>

    <div class="form-group" style="max-width:280px;">
      <label>目标总字数</label>
      <el-select v-model="targetWords" style="width:100%;">
        <el-option :value="200000" label="20 万字（短篇）" />
        <el-option :value="400000" label="40 万字（中篇）" />
        <el-option :value="600000" label="60 万字（长篇）" />
        <el-option :value="1000000" label="100 万字（超长篇）" />
        <el-option :value="-1" label="自定义" />
      </el-select>
      <div v-if="showCustomWords" style="margin-top: 8px;">
        <el-input-number v-model="customWords" :min="5" :max="500" :step="10" />
        <span style="margin-left: 8px; color: var(--text-dim); font-size: 13px;">万字</span>
      </div>
    </div>

    <div style="display:flex;gap:8px;">
      <el-button type="primary" :disabled="loading" :loading="loading" @click="generate">
        {{ loading ? '正在生成设定，预计 30-60 秒...' : '一键生成设定' }}
      </el-button>
      <el-button :disabled="loading" @click="goBack">返回上一步</el-button>
    </div>

    <div v-if="loading" style="text-align:center;padding:24px 0;color:var(--text-dim);font-size:13px;">
      <div style="margin-bottom:8px;">AI 正在构建完整世界观、角色...</div>
      <div style="margin-bottom:12px;font-size:12px;color:var(--text-secondary);">
        三步生成：核心设定 → 故事架构 → 整合校验（预计 30-60 秒）
      </div>
      <div class="progress"><div class="progress-bar" style="width:60%;animation:wizard-progress 2s ease infinite;"></div></div>
    </div>
  </div>
</template>

<style scoped>
.idea-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 12px;
}

.idea-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px 16px;
  cursor: pointer;
  transition: all 0.15s;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.7;
}

.idea-card:hover {
  border-color: var(--gold-dim);
  background: var(--bg-card-hover);
}

.idea-card.selected {
  border-color: var(--gold);
  background: var(--gold-glow);
}

.idea-card-text {
  font-size: 13px;
  color: var(--text-primary);
  line-height: 1.7;
}

.wizard-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}

.wizard-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 18px;
  cursor: pointer;
  transition: all 0.15s;
}

.wizard-card:hover {
  border-color: var(--gold-dim);
  background: var(--bg-card-hover);
  transform: translateY(-1px);
}

.wizard-card-title {
  font-family: var(--font-heading);
  font-size: 16px;
  font-weight: 600;
  color: var(--gold-text);
  margin-bottom: 8px;
}

.wizard-card-desc {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: 8px;
}

.wizard-card-hook {
  font-size: 12px;
  color: var(--jade);
  padding: 4px 8px;
  background: rgba(90, 158, 122, 0.08);
  border-radius: var(--radius-sm);
  display: inline-block;
}

/* Writer cards in wizard */
.wizard-writer-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

@media (max-width: 1100px) {
  .wizard-writer-grid { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 800px) {
  .wizard-writer-grid { grid-template-columns: repeat(2, 1fr); }
}

.wizard-writer-card {
  background: var(--bg-card);
  border: 2px solid var(--border);
  border-radius: var(--radius);
  padding: 16px;
  cursor: pointer;
  transition: all 0.15s;
  text-align: center;
}

.wizard-writer-card:hover {
  border-color: var(--gold-dim);
  background: var(--bg-card-hover);
}

.wizard-writer-card.selected {
  border-color: var(--gold);
  background: var(--gold-glow);
}

.wizard-writer-avatar {
  font-size: 36px;
  margin-bottom: 8px;
  line-height: 1;
}

.wizard-writer-name {
  font-family: var(--font-heading);
  font-size: 15px;
  font-weight: 700;
  color: var(--gold-text);
  margin-bottom: 4px;
}

.wizard-writer-style {
  font-size: 11px;
  color: var(--gold);
  background: var(--gold-glow);
  border: 1px solid var(--gold-dim);
  border-radius: 3px;
  padding: 1px 8px;
  display: inline-block;
  margin-bottom: 8px;
}

.wizard-writer-desc {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.6;
}

@keyframes wizard-progress {
  0% { width: 20%; }
  50% { width: 80%; }
  100% { width: 20%; }
}
</style>
