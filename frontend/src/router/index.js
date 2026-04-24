import { createRouter, createWebHistory } from 'vue-router'
import UploadView from '../views/UploadView.vue'
import RecordsView from '../views/RecordsView.vue'

const router = createRouter({
  // 使用相对路径作为 base，适配穿透场景
  history: createWebHistory(import.meta.env.BASE_URL || ''),
  routes: [
    { path: '/', component: UploadView },
    { path: '/upload', component: UploadView },
    { path: '/records', component: RecordsView }
  ]
})

export default router
