<script setup>
import { computed } from 'vue'

const props = defineProps({
  book: { type: Object, default: null },
  route: { type: Object, required: true },
  router: { type: Object, required: true },
})

const stepLabels = ['作品概览', '角色体系', '分卷大纲', '整文细纲', '全书正文']
const stepPaths = [
  (id) => `/books/${id}`,
  (id) => `/books/${id}/characters`,
  (id) => `/books/${id}/volumes`,
  (id) => `/books/${id}/outlines`,
  (id) => `/books/${id}/chapters`,
]

const currentStep = computed(() => {
  if (!props.book) return -1
  const p = props.route.path
  for (let i = 0; i < stepPaths.length; i++) {
    if (p === stepPaths[i](props.book.id)) return i
  }
  if (p.includes('settings')) return -1
  return -1
})

const isActive = (path) => props.route.path === path
const isSettingsActive = computed(() => props.book && isActive(`/books/${props.book.id}/settings`) || isActive('/settings'))
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <h1>芯墨</h1>
      <div class="sidebar-sub">写作工坊</div>
    </div>

    <div v-if="book" class="sidebar-book">
      <div class="book-label">当前作品</div>
      <div class="book-name">{{ book.title }}</div>
    </div>

    <nav class="sidebar-nav-global">
      <router-link to="/" :class="{ active: route.path === '/' }">
        <span>📚</span>
        <span>我的作品</span>
      </router-link>
    </nav>

    <div class="sidebar-steps">
      <div class="sidebar-steps-title">创作流程</div>
      <template v-for="(label, i) in stepLabels" :key="i">
        <router-link
          v-if="book"
          :to="stepPaths[i](book.id)"
          class="step-nav-item"
          :class="{ active: currentStep === i, completed: false }"
        >
          <span class="step-num">{{ i + 1 }}</span>
          <span class="step-label">{{ label }}</span>
        </router-link>
        <span v-else class="step-nav-item disabled">
          <span class="step-num">{{ i + 1 }}</span>
          <span class="step-label">{{ label }}</span>
        </span>
      </template>
    </div>

    <div class="sidebar-spacer"></div>

    <nav class="sidebar-nav-global sidebar-nav-bottom">
      <router-link
        v-if="book"
        :to="'/books/' + book.id + '/settings'"
        :class="{ active: isSettingsActive }"
      >
        <span>⚙️</span>
        <span>设置</span>
      </router-link>
      <router-link v-else to="/settings" :class="{ active: isSettingsActive }">
        <span>⚙️</span>
        <span>设置</span>
      </router-link>
    </nav>

    <div class="sidebar-footer">芯墨 v0.2.0</div>
  </aside>
</template>
