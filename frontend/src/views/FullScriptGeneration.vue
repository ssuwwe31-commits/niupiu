<template>
  <div class="full-script-generation">
    <el-card>
      <template #header>
        <div class="card-header">
          <el-icon><VideoPlay /></el-icon>
          <span>完整剧本生成</span>
          <el-button
            type="primary"
            size="small"
            @click="goToPlanner"
            style="margin-left: auto"
          >
            <el-icon><Back /></el-icon>
            返回规划
          </el-button>
        </div>
      </template>

      <div v-if="loading" class="loading-container">
        <el-progress
          :percentage="progress"
          :status="progress === 100 ? 'success' : undefined"
        />
        <p class="loading-text">{{ loadingText }}</p>
        <el-descriptions :column="1" border style="margin-top: 16px">
          <el-descriptions-item label="已生成">{{ generatedCount }} / {{ totalScenes }} 场</el-descriptions-item>
          <el-descriptions-item label="已用时间">{{ elapsedTime.toFixed(1) }} 秒</el-descriptions-item>
        </el-descriptions>
      </div>

      <div v-else-if="generatedScripts.length > 0" class="script-content">
        <el-alert
          :title="`共生成 ${generatedScripts.length} 场戏 · 用时 ${generationTime.toFixed(2)} 秒`"
          type="success"
          :closable="false"
          show-icon
          style="margin-bottom: 16px"
        />

        <el-collapse v-model="activeScenes">
          <el-collapse-item
            v-for="(scene, index) in generatedScripts"
            :key="scene.scene_number"
            :name="scene.scene_number"
          >
            <template #title>
              <div class="scene-title">
                <el-tag>Scene {{ scene.scene_number }}</el-tag>
                <span class="scene-description">{{ scene.scene_description }}</span>
                <el-tag
                  :type="getConfidenceType(scene.confidence)"
                  size="small"
                  style="margin-left: auto"
                >
                  {{ (scene.confidence * 100).toFixed(0) }}%
                </el-tag>
              </div>
            </template>

            <div class="scene-script">
              <pre>{{ scene.script }}</pre>
            </div>
          </el-collapse-item>
        </el-collapse>

        <div class="action-bar">
          <el-button type="primary" @click="exportScript">
            <el-icon><Download /></el-icon>
            导出剧本
          </el-button>
          <el-button @click="goToPlanner">
            <el-icon><Back /></el-icon>
            返回规划
          </el-button>
        </div>
      </div>

      <el-empty v-else description="暂无剧本内容" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { storyPlanApi } from '@/api/storyPlan'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const progress = ref(0)
const loadingText = ref('')
const generatedScripts = ref([])
const totalScenes = ref(0)
const generatedCount = ref(0)
const generationTime = ref(0)
const elapsedTime = ref(0)
const activeScenes = ref([])
const timer = ref(null)

const planId = route.query.plan_id

const goToPlanner = () => {
  router.push('/story-planner')
}

const getConfidenceType = (confidence) => {
  if (confidence >= 0.8) return 'success'
  if (confidence >= 0.6) return 'warning'
  return 'danger'
}

const exportScript = () => {
  let content = '完整剧本\n\n'
  
  generatedScripts.value.forEach(scene => {
    content += `Scene ${scene.scene_number}: ${scene.scene_description}\n`
    content += '='.repeat(50) + '\n\n'
    content += scene.script + '\n\n'
    content += '-'.repeat(50) + '\n\n'
  })

  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `script_${planId}.txt`
  link.click()
  URL.revokeObjectURL(url)

  ElMessage.success('剧本导出成功')
}

const loadGeneratedScript = async () => {
  if (!planId) {
    ElMessage.warning('缺少规划 ID')
    goToPlanner()
    return
  }

  loading.value = true
  progress.value = 0
  generatedScripts.value = []
  generatedCount.value = 0
  elapsedTime.value = 0

  timer.value = setInterval(() => {
    elapsedTime.value += 0.1
  }, 100)

  try {
    loadingText.value = '正在生成剧本...'
    
    const result = await storyPlanApi.generateFullScript({
      plan_id: planId,
      style: 'standard',
      length: 'medium',
      innovation_degree: 0.5
    })

    generatedScripts.value = result.generated_scenes
    totalScenes.value = result.total_scene_count
    generationTime.value = result.generation_time_seconds

    const interval = setInterval(() => {
      if (generatedCount.value < generatedScripts.value.length) {
        generatedCount.value += 1
        progress.value = (generatedCount.value / totalScenes.value) * 100
        loadingText.value = `正在生成 Scene ${generatedCount.value} / ${totalScenes.value}...`
      } else {
        clearInterval(interval)
        progress.value = 100
        loadingText.value = '生成完成！'
        
        setTimeout(() => {
          loading.value = false
          if (timer.value) {
            clearInterval(timer.value)
            timer.value = null
          }
          ElMessage.success(`成功生成 ${totalScenes.value} 场戏`)
        }, 500)
      }
    }, 300)

  } catch (error) {
    loading.value = false
    if (timer.value) {
      clearInterval(timer.value)
      timer.value = null
    }
    ElMessage.error('生成失败: ' + (error.response?.data?.detail || error.message))
  }
}

onMounted(() => {
  loadGeneratedScript()
})

onUnmounted(() => {
  if (timer.value) {
    clearInterval(timer.value)
  }
})
</script>

<style scoped>
.full-script-generation {
  padding: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.loading-container {
  padding: 40px;
  text-align: center;
}

.loading-text {
  margin-top: 16px;
  color: #606266;
}

.script-content {
  padding: 16px;
}

.scene-title {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.scene-description {
  flex: 1;
  font-weight: 500;
  color: #303133;
}

.scene-script {
  padding: 16px;
  background: #f5f7fa;
  border-radius: 4px;
  max-height: 400px;
  overflow-y: auto;
}

.scene-script pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0;
  font-family: inherit;
  line-height: 1.8;
  color: #303133;
}

.action-bar {
  margin-top: 16px;
  display: flex;
  gap: 8px;
  justify-content: center;
}
</style>