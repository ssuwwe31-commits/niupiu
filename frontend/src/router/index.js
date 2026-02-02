import { createRouter, createWebHistory } from 'vue-router'
import ScriptGeneration from '@/views/ScriptGeneration.vue'
import StoryUnitManager from '@/views/StoryUnitManager.vue'

const routes = [
  {
    path: '/',
    name: 'ScriptGeneration',
    component: ScriptGeneration
  },
  {
    path: '/story-units',
    name: 'StoryUnitManager',
    component: StoryUnitManager
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
