import { createRouter, createWebHistory } from 'vue-router'
import ScriptGeneration from '@/views/ScriptGeneration.vue'
import StoryUnitManager from '@/views/StoryUnitManager.vue'
import NovelManager from '@/views/NovelManager.vue'
import CharacterManager from '@/views/CharacterManager.vue'
import StoryPlanner from '@/views/StoryPlanner.vue'
import StoryPlanList from '@/views/StoryPlanList.vue'
import FullScriptGeneration from '@/views/FullScriptGeneration.vue'

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
  },
  {
    path: '/novels',
    name: 'NovelManager',
    component: NovelManager
  },
  {
    path: '/characters',
    name: 'CharacterManager',
    component: CharacterManager
  },
  {
    path: '/story-planner',
    name: 'StoryPlanner',
    component: StoryPlanner
  },
  {
    path: '/story-plans',
    name: 'StoryPlanList',
    component: StoryPlanList
  },
  {
    path: '/full-script-generation',
    name: 'FullScriptGeneration',
    component: FullScriptGeneration
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
