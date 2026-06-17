import Dashboard from '../views/Dashboard.vue'
import BookCreate from '../views/BookCreate.vue'
import BookOverview from '../views/BookOverview.vue'
import Characters from '../views/Characters.vue'
import Volumes from '../views/Volumes.vue'
import Outlines from '../views/Outlines.vue'
import Injections from '../views/Injections.vue'
import Chapters from '../views/Chapters.vue'
import ChapterDetail from '../views/ChapterDetail.vue'
import Settings from '../views/Settings.vue'
import Wizard from '../views/Wizard.vue'
import WritingStyle from '../views/WritingStyle.vue'
import WriterSelect from '../views/WriterSelect.vue'

export const routes = [
  { path: '/', component: Dashboard },
  { path: '/wizard', component: Wizard },
  { path: '/books/create', component: BookCreate },
  { path: '/books/:bookId', component: BookOverview, props: true },
  { path: '/books/:bookId/characters', component: Characters, props: true },
  { path: '/books/:bookId/volumes', component: Volumes, props: true },
  { path: '/books/:bookId/outlines', component: Outlines, props: true },
  { path: '/books/:bookId/injections', component: Injections, props: true },
  { path: '/books/:bookId/writing-style', component: WritingStyle, props: true },
  { path: '/books/:bookId/writer-select', component: WriterSelect, props: true },
  { path: '/books/:bookId/chapters', component: Chapters, props: true },
  { path: '/books/:bookId/chapters/:chapterId', component: ChapterDetail, props: true },
  { path: '/books/:bookId/settings', component: Settings, props: true },
  { path: '/settings', component: Settings, props: () => ({ book: null }) },
]
