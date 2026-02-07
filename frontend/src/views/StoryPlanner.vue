<template>
  <div class="story-planner">
    <el-row :gutter="20">
      <el-col :span="10">
        <el-card class="input-card">
          <template #header>
            <div class="card-header">
              <el-icon><Guide /></el-icon>
              <span>剧情规划配置</span>
            </div>
          </template>

          <el-form :model="form" label-width="120px">
            <el-form-item label="故事梗概">
              <el-input
                v-model="form.story_outline"
                type="textarea"
                :rows="6"
                placeholder="描述故事的总体梗概..."
              />
            </el-form-item>

            <el-form-item label="人物列表">
              <el-select
                v-model="form.characters"
                multiple
                filterable
                allow-create
                placeholder="选择或输入人物名称"
              >
                <el-option
                  v-for="char in availableCharacters"
                  :key="char"
                  :label="char"
                  :value="char"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="剧情结构">
              <el-select v-model="form.structure_type" placeholder="选择剧情结构">
                <el-option
                  v-for="template in structureTemplates"
                  :key="template.id"
                  :label="template.name"
                  :value="template.id"
                >
                  <span>{{ template.name }}</span>
                  <span style="color: #8492a6; font-size: 12px; margin-left: 8px">
                    {{ template.phases.length }} 阶段
                  </span>
                </el-option>
              </el-select>
            </el-form-item>

            <el-form-item label="总场次">
              <el-input-number
                v-model="form.total_scene_count"
                :min="3"
                :max="50"
                size="small"
              />
              <span class="form-tip">留空则使用默认分布</span>
            </el-form-item>

            <el-divider>自定义阶段分布</el-divider>

            <el-form-item v-for="phase in currentPhases" :key="phase.name" :label="phase.name">
              <el-input-number
                v-model="customPhaseDistribution[phase.name]"
                :min="1"
                :max="20"
                size="small"
                :disabled="!useCustomDistribution"
              />
              <el-tooltip :content="phase.description" placement="top">
                <el-icon class="phase-info-icon"><InfoFilled /></el-icon>
              </el-tooltip>
            </el-form-item>

            <el-form-item>
              <el-checkbox v-model="useCustomDistribution">
                使用自定义分布
              </el-checkbox>
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                :loading="generating"
                @click="handleGenerate"
                size="large"
                style="width: 100%"
              >
                <el-icon><MagicStick /></el-icon>
                生成剧情规划
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card class="structure-info-card">
          <template #header>
            <div class="card-header">
              <el-icon><Reading /></el-icon>
              <span>剧情结构说明</span>
            </div>
          </template>

          <div v-if="selectedTemplate" class="structure-detail">
            <h4>{{ selectedTemplate.name }}</h4>
            <el-timeline>
              <el-timeline-item
                v-for="(phase, index) in selectedTemplate.phases"
                :key="phase.name"
                :timestamp="`阶段 ${index + 1}`"
                placement="top"
              >
                <div class="timeline-content">
                  <strong>{{ phase.name }}</strong>
                  <p>{{ phase.description }}</p>
                  <el-tag size="small" type="info">
                    默认 {{ phase.default_scene_count }} 场
                  </el-tag>
                </div>
              </el-timeline-item>
            </el-timeline>
          </div>
        </el-card>
      </el-col>

      <el-col :span="14">
        <el-card class="output-card">
          <template #header>
            <div class="card-header">
              <el-icon><Document /></el-icon>
              <span>剧情规划结果</span>
              <div v-if="generatedPlan" style="margin-left: auto; display: flex; gap: 8px;">
                <el-button
                  type="success"
                  size="small"
                  @click="handleSavePlan"
                  :loading="saving"
                >
                  <el-icon><FolderAdd /></el-icon>
                  保存规划
                </el-button>
                <el-button
                  type="primary"
                  size="small"
                  @click="handleGenerateScript"
                >
                  <el-icon><VideoPlay /></el-icon>
                  生成完整剧本
                </el-button>
              </div>
            </div>
          </template>

          <div v-if="generatedPlan" class="plan-content">
            <el-alert
              :title="`共 ${generatedPlan.total_scene_count} 场戏 · ${generatedPlan.structure_type} 结构`"
              type="success"
              :closable="false"
              show-icon
            >
              <template #default>
                <div class="plan-meta">
                  <span>规划 ID: {{ generatedPlan.plan_id }}</span>
                  <span>人物: {{ generatedPlan.characters.join(', ') }}</span>
                </div>
              </template>
            </el-alert>

            <el-collapse v-model="activePhases" style="margin-top: 16px">
              <el-collapse-item
                v-for="phase in generatedPlan.phases"
                :key="phase.name"
                :name="phase.name"
              >
                <template #title>
                  <div class="phase-title">
                    <el-tag size="small" :type="getPhaseType(phase.name)">
                      {{ phase.name }}
                    </el-tag>
                    <span>{{ phase.description }}</span>
                    <el-badge :value="phase.scene_count" type="primary" />
                  </div>
                </template>

                <div class="phase-scenes">
                  <div
                    v-for="scene in phase.scenes"
                    :key="scene.scene_number"
                    class="scene-item"
                  >
                    <div class="scene-header">
                      <el-tag>Scene {{ scene.scene_number }}</el-tag>
                      <span class="scene-description">{{ scene.scene_description }}</span>
                    </div>
                    <el-descriptions :column="2" border size="small">
                      <el-descriptions-item label="核心冲突">
                        {{ scene.core_conflict }}
                      </el-descriptions-item>
                      <el-descriptions-item label="情绪目标">
                        {{ scene.emotion_goal }}
                      </el-descriptions-item>
                      <el-descriptions-item label="主要人物">
                        <el-tag
                          v-for="char in scene.main_characters"
                          :key="char"
                          size="small"
                          style="margin-right: 4px"
                        >
                          {{ char }}
                        </el-tag>
                      </el-descriptions-item>
                      <el-descriptions-item label="剧情功能">
                        {{ scene.plot_function }}
                      </el-descriptions-item>
                      <el-descriptions-item label="关键事件" :span="2">
                        {{ scene.key_event }}
                      </el-descriptions-item>
                    </el-descriptions>
                  </div>
                </div>
              </el-collapse-item>
            </el-collapse>
          </div>

          <el-empty v-else description="点击生成按钮开始规划剧情" />
        </el-card>
      </el-col>
    </el-row>

    <el-dialog
      v-model="showScriptDialog"
      title="生成完整剧本"
      width="500px"
    >
      <el-form :model="scriptForm" label-width="120px">
        <el-form-item label="剧本风格">
          <el-select v-model="scriptForm.style">
            <el-option label="标准" value="standard" />
            <el-option label="幽默" value="humorous" />
            <el-option label="严肃" value="serious" />
            <el-option label="浪漫" value="romantic" />
          </el-select>
        </el-form-item>
        <el-form-item label="剧本长度">
          <el-select v-model="scriptForm.length">
            <el-option label="短（300-500字）" value="short" />
            <el-option label="中（500-800字）" value="medium" />
            <el-option label="长（800-1200字）" value="long" />
          </el-select>
        </el-form-item>
        <el-form-item label="创新程度">
          <el-slider
            v-model="scriptForm.innovation_degree"
            :min="0"
            :max="1"
            :step="0.1"
            :marks="{ 0: '保守', 0.5: '适中', 1: '创新' }"
            show-stops
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showScriptDialog = false">取消</el-button>
        <el-button type="primary" :loading="generatingScript" @click="confirmGenerateScript">
          开始生成
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { storyPlanApi } from '@/api/storyPlan'
import { useRouter } from 'vue-router'

const router = useRouter()

const availableCharacters = ref(['主角', '反派', '配角A', '配角B'])

const form = reactive({
  story_outline: '',
  characters: [],
  structure_type: 'three_act',
  total_scene_count: null,
  custom_phase_distribution: null
})

const customPhaseDistribution = reactive({})
const useCustomDistribution = ref(false)
const generating = ref(false)
const saving = ref(false)
const generatedPlan = ref(null)
const activePhases = ref([])
const structureTemplates = ref([])

const showScriptDialog = ref(false)
const generatingScript = ref(false)
const scriptForm = reactive({
  style: 'standard',
  length: 'medium',
  innovation_degree: 0.5
})

const selectedTemplate = computed(() => {
  return structureTemplates.value.find(t => t.id === form.structure_type)
})

const currentPhases = computed(() => {
  return selectedTemplate.value?.phases || []
})

const getPhaseType = (phaseName) => {
  if (phaseName.includes('setup') || phaseName.includes('ordinary')) return 'info'
  if (phaseName.includes('confrontation') || phaseName.includes('ordeal')) return 'danger'
  if (phaseName.includes('resolution') || phaseName.includes('return')) return 'success'
  return 'primary'
}

const loadStructureTemplates = async () => {
  try {
    const templates = await storyPlanApi.getStructureTemplates()
    structureTemplates.value = templates
    templates.forEach(t => {
      customPhaseDistribution[t.id] = {}
      t.phases.forEach(p => {
        customPhaseDistribution[t.id][p.name] = p.default_scene_count
      })
    })
  } catch (error) {
    ElMessage.error('加载剧情结构模板失败')
  }
}

const handleGenerate = async () => {
  if (!form.story_outline) {
    ElMessage.warning('请输入故事梗概')
    return
  }
  if (form.characters.length === 0) {
    ElMessage.warning('请选择人物')
    return
  }

  generating.value = true

  try {
    const request = {
      story_outline: form.story_outline,
      characters: form.characters,
      structure_type: form.structure_type,
      total_scene_count: form.total_scene_count
    }

    if (useCustomDistribution.value && customPhaseDistribution[form.structure_type]) {
      request.custom_phase_distribution = customPhaseDistribution[form.structure_type]
    }

    const result = await storyPlanApi.generateStoryPlan(request)
    generatedPlan.value = result
    activePhases.value = result.phases.map(p => p.name)
    ElMessage.success(`成功生成 ${result.total_scene_count} 场戏的剧情规划`)
  } catch (error) {
    ElMessage.error('生成失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    generating.value = false
  }
}

const handleSavePlan = async () => {
  if (!generatedPlan.value) {
    ElMessage.warning('请先生成剧情规划')
    return
  }

  saving.value = true

  try {
    const saveData = {
      title: `剧情规划 - ${new Date().toLocaleString('zh-CN')}`,
      story_outline: form.story_outline,
      characters: form.characters,
      structure_type: form.structure_type,
      phases_data: generatedPlan.value.phases,
      total_scene_count: generatedPlan.value.total_scene_count,
      status: 'draft'
    }

    await storyPlanApi.saveStoryPlan(saveData)
    ElMessage.success('剧情规划已保存')
  } catch (error) {
    ElMessage.error('保存失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    saving.value = false
  }
}

const handleGenerateScript = () => {
  showScriptDialog.value = true
}

const confirmGenerateScript = async () => {
  if (!generatedPlan.value) return

  generatingScript.value = true

  try {
    await storyPlanApi.generateFullScript({
      plan_id: generatedPlan.value.plan_id,
      style: scriptForm.style,
      length: scriptForm.length,
      innovation_degree: scriptForm.innovation_degree
    })

    showScriptDialog.value = false
    router.push({
      path: '/full-script-generation',
      query: { plan_id: generatedPlan.value.plan_id }
    })
  } catch (error) {
    ElMessage.error('生成剧本失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    generatingScript.value = false
  }
}

onMounted(() => {
  loadStructureTemplates()
})
</script>

<style scoped>
.story-planner {
  padding: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.input-card,
.output-card,
.structure-info-card {
  margin-bottom: 20px;
}

.form-tip {
  margin-left: 8px;
  font-size: 12px;
  color: #909399;
}

.phase-info-icon {
  margin-left: 8px;
  cursor: help;
  color: #909399;
}

.structure-detail h4 {
  margin: 0 0 16px 0;
}

.timeline-content {
  padding: 8px 0;
}

.timeline-content strong {
  display: block;
  margin-bottom: 4px;
}

.timeline-content p {
  margin: 4px 0 8px 0;
  color: #606266;
  font-size: 13px;
}

.plan-content {
  padding: 16px;
}

.plan-meta {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}

.plan-meta span {
  margin-right: 16px;
}

.phase-title {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.phase-scenes {
  padding: 16px;
}

.scene-item {
  margin-bottom: 16px;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 4px;
}

.scene-item:last-child {
  margin-bottom: 0;
}

.scene-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.scene-description {
  font-weight: 500;
  color: #303133;
}
</style>