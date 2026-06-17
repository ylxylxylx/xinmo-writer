<script setup>
import { ref, computed, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import Sidebar from "./components/Sidebar.vue"
import { apiGet } from "./api/index.js"

const route = useRoute()
const router = useRouter()
const book = ref(null)

async function loadBook() {
  const bid = route.params.bookId
  console.log('[App] loadBook, bookId =', bid)
  if (!bid) { book.value = null; return }
  try {
    const b = await apiGet(`/books/${bid}`)
    console.log('[App] book loaded:', b?.title)
    book.value = b
  } catch (e) {
    console.error('[App] loadBook error:', e)
    book.value = null
  }
}

watch(() => route.params.bookId, loadBook, { immediate: true })
</script>

<template>
  <div class="app-layout">
    <Sidebar :book="book" :route="route" :router="router" />
    <main class="main">
      <router-view :book="book" />
    </main>
  </div>
</template>
