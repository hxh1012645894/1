import { createRouter, createWebHistory } from 'vue-router'
import UploadView from '../views/UploadView.vue'
import RecordsView from '../views/RecordsView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/upload' },
    { path: '/upload', component: UploadView },
    { path: '/records', component: RecordsView }
  ]
})

export default router
