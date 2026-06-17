<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apiGet, apiPost } from '../api/index.js'

const books = ref([])

onMounted(async () => {
  try {
    books.value = await apiGet('/books')
  } catch (e) {
    ElMessage.error('加载作品列表失败: ' + e.message)
  }
})

function formatWordCount(count) {
  if (!count) return '0字'
  if (count >= 10000) return (count / 10000).toFixed(1) + '万字'
  return count + '字'
}

function formatTargetWords(count) {
  if (!count) return ''
  if (count >= 10000) return (count / 10000).toFixed(0) + '万字'
  return count + '字'
}

function calcProgress(book) {
  if (!book.target_words || !book.total_words) return ''
  return Math.min(100, Math.round(book.total_words / book.target_words * 100)) + '%'
}

async function deleteBook(book) {
  try {
    await ElMessageBox.confirm(`确定删除《${book.title}》？此操作不可撤销。`, '删除确认', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch { return }
  try {
    await apiPost(`/books/${book.id}/delete`)
    books.value = books.value.filter(b => b.id !== book.id)
    ElMessage.success('作品已删除')
  } catch (e) {
    ElMessage.error('删除失败: ' + e.message)
  }
}

function handleCommand(command, book) {
  if (command === 'delete') {
    deleteBook(book)
  } else if (command === 'edit') {
    window.location.href = `/books/${book.id}`
  }
}
</script>

<template>
  <div class="page-header">
    <h2>我的书架</h2>
    <router-link to="/wizard">
      <el-button type="primary" style="background:linear-gradient(135deg, var(--gold) 0%, var(--cinnabar) 100%);border-color:var(--gold);">
        + 新建作品
      </el-button>
    </router-link>
  </div>

  <!-- 空状态 -->
  <div v-if="books.length === 0" class="empty-state">
    <div class="empty-icon" style="font-size:64px;">📚</div>
    <p style="font-size:18px;margin-top:16px;color:var(--text-primary);">还没有作品</p>
    <p style="font-size:14px;color:var(--text-dim);margin-top:8px;">开始你的第一篇 AI 小说</p>
    <router-link to="/wizard" style="margin-top:20px;display:inline-block;">
      <el-button type="primary" style="background:linear-gradient(135deg, var(--gold) 0%, var(--cinnabar) 100%);border-color:var(--gold);">
        + 新建作品
      </el-button>
    </router-link>
  </div>

  <!-- 书架网格 -->
  <div v-else class="book-grid">
    <div v-for="book in books" :key="book.id" class="book-card" @click="$router.push(`/books/${book.id}`)">
      <!-- 封面区域 -->
      <div class="book-cover">
        <div class="book-cover-title">{{ book.title }}</div>
        <span v-if="book.genre" class="book-cover-genre">{{ book.genre }}</span>
        <!-- 操作按钮 -->
        <div class="book-card-actions" @click.stop>
          <el-dropdown trigger="click" @command="(cmd) => handleCommand(cmd, book)">
            <span class="action-trigger">⋯</span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="edit">编辑信息</el-dropdown-item>
                <el-dropdown-item command="delete" divided>
                  <span style="color:var(--el-color-danger);">删除</span>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
      <!-- 信息区域 -->
      <div class="book-info">
        <div class="book-info-title">{{ book.title }}</div>
        <div class="book-info-words" v-if="book.target_words">
          目标 {{ formatWordCount(book.target_words) }} · 已写 {{ formatWordCount(book.total_words) }}
          <span v-if="book.target_words > 0">（{{ Math.min(100, Math.round((book.total_words || 0) / book.target_words * 100)) }}%）</span>
        </div>
        <div class="book-info-progress">
          {{ book.chapter_count ?? 0 }}章
          <span v-if="book.writer_name"> · {{ book.writer_name }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.book-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 24px;
}

.book-card {
  cursor: pointer;
  transition: transform 0.2s;
  border-radius: 12px;
  overflow: hidden;
}

.book-card:hover {
  transform: translateY(-4px);
}

.book-cover {
  height: 240px;
  background: linear-gradient(135deg, #1a1a2e, #2d2d50);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
  position: relative;
}

.book-cover-title {
  font-family: var(--font-heading);
  font-size: 26px;
  font-weight: 800;
  color: var(--gold, #c9a96e);
  text-align: center;
  line-height: 1.4;
  word-break: break-all;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.book-cover-genre {
  position: absolute;
  bottom: 12px;
  font-size: 11px;
  color: var(--text-dim, #888);
  background: rgba(0, 0, 0, 0.3);
  padding: 2px 8px;
  border-radius: 4px;
}

.book-card-actions {
  position: absolute;
  top: 8px;
  right: 8px;
}

.action-trigger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.4);
  color: rgba(255, 255, 255, 0.7);
  font-size: 16px;
  cursor: pointer;
  transition: background 0.2s;
  letter-spacing: 2px;
}

.action-trigger:hover {
  background: rgba(0, 0, 0, 0.7);
  color: #fff;
}

.book-info {
  padding: 12px 0;
}

.book-info-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.book-info-words {
  font-size: 12px;
  color: var(--text-dim, #888);
  margin-top: 2px;
}

.book-info-progress {
  font-size: 12px;
  color: var(--text-dim);
  margin-top: 4px;
}

.book-info-writer {
  font-size: 11px;
  color: var(--gold-dim);
  margin-top: 2px;
}
</style>
