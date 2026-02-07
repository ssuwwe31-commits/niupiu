<template>
  <div class="script-generation">
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card class="input-card">
          <template #header>
            <div class="card-header">
              <el-icon><Edit /></el-icon>
              <span>剧本生成配置</span>
            </div>
          </template>

          <el-form :model="form" label-width="120px">
            <el-form-item label="剧情上下文">
              <el-input
                v-model="form.plot_context"
                type="textarea"
                :rows="4"
                placeholder="描述当前的剧情背景和上下文..."
              />
            </el-form-item>

            <el-form-item label="冲突类型">
              <el-select v-model="form.required_conflict" placeholder="选择冲突类型">
                <el-option label="背叛" value="背叛" />
                <el-option label="复仇" value="复仇" />
                <el-option label="权力斗争" value="权力斗争" />
                <el-option label="误会" value="误会" />
                <el-option label="身份冲突" value="身份冲突" />
              </el-select>
            </el-form-item>

            <el-form-item label="情绪类型">
              <el-select v-model="form.required_emotion" placeholder="选择情绪类型">
                <el-option label="高燃" value="高燃" />
                <el-option label="爽点" value="爽点" />
                <el-option label="虐点" value="虐点" />
                <el-option label="反转" value="反转" />
                <el-option label="温馨" value="温馨" />
              </el-select>
            </el-form-item>

            <el-form-item label="出场人物">
              <el-select
                v-model="form.characters"
                multiple
                placeholder="选择出场人物"
              >
                <el-option label="主角" value="主角" />
                <el-option label="反派" value="反派" />
                <el-option label="配角A" value="配角A" />
                <el-option label="配角B" value="配角B" />
              </el-select>
            </el-form-item>

            <el-form-item label="场景">
              <el-input
                v-model="form.scene"
                placeholder="如：监控室、战场、会议室..."
              />
            </el-form-item>

            <el-divider>生成配置</el-divider>

            <el-form-item label="剧本风格">
              <el-select v-model="form.style" placeholder="选择风格">
                <el-option label="标准" value="standard" />
                <el-option label="幽默" value="humorous" />
                <el-option label="严肃" value="serious" />
                <el-option label="浪漫" value="romantic" />
              </el-select>
            </el-form-item>

            <el-form-item label="剧本长度">
              <el-select v-model="form.length" placeholder="选择长度">
                <el-option label="短（300-500字）" value="short" />
                <el-option label="中（500-800字）" value="medium" />
                <el-option label="长（800-1200字）" value="long" />
              </el-select>
            </el-form-item>

            <el-form-item label="创新程度">
              <el-slider
                v-model="form.innovation_degree"
                :min="0"
                :max="1"
                :step="0.1"
                :marks="{ 0: '保守', 0.5: '适中', 1: '创新' }"
                show-stops
              />
            </el-form-item>

            <el-form-item label="目标驱动">
              <el-switch v-model="form.goal_driven" />
              <span class="form-tip">启用人物目标驱动生成</span>
            </el-form-item>

            <el-divider>质量评估配置</el-divider>

            <el-form-item label="启用评估">
              <el-switch v-model="form.enable_quality_evaluation" />
              <span class="form-tip">生成后自动进行质量评估</span>
            </el-form-item>

            <el-form-item v-if="form.enable_quality_evaluation" label="自定义权重">
              <div class="weight-sliders">
                <div class="weight-slider">
                  <span class="weight-label">冲突强度</span>
                  <el-slider
                    v-model.number="form.weights.conflict_intensity"
                    :min="0"
                    :max="1"
                    :step="0.05"
                    show-input
                    input-size="small"
                  />
                </div>
                <div class="weight-slider">
                  <span class="weight-label">情绪渲染</span>
                  <el-slider
                    v-model.number="form.weights.emotion_rendering"
                    :min="0"
                    :max="1"
                    :step="0.05"
                    show-input
                    input-size="small"
                  />
                </div>
                <div class="weight-slider">
                  <span class="weight-label">人物一致性</span>
                  <el-slider
                    v-model.number="form.weights.character_consistency"
                    :min="0"
                    :max="1"
                    :step="0.05"
                    show-input
                    input-size="small"
                  />
                </div>
                <div class="weight-slider">
                  <span class="weight-label">对话自然度</span>
                  <el-slider
                    v-model.number="form.weights.dialogue_naturalness"
                    :min="0"
                    :max="1"
                    :step="0.05"
                    show-input
                    input-size="small"
                  />
                </div>
                <div class="weight-slider">
                  <span class="weight-label">剧情张力</span>
                  <el-slider
                    v-model.number="form.weights.dramatic_tension"
                    :min="0"
                    :max="1"
                    :step="0.05"
                    show-input
                    input-size="small"
                  />
                </div>
                <div class="weight-slider">
                  <span class="weight-label">整体连贯性</span>
                  <el-slider
                    v-model.number="form.weights.overall_coherence"
                    :min="0"
                    :max="1"
                    :step="0.05"
                    show-input
                    input-size="small"
                  />
                </div>
              </div>
            </el-form-item>

            <el-form-item v-if="form.enable_quality_evaluation">
              <el-button size="small" @click="resetWeights">重置权重</el-button>
              <el-tag size="small" type="info" style="margin-left: 8px">
                总权重: {{ totalWeight.toFixed(2) }}
              </el-tag>
            </el-form-item>

            <el-divider>批次生成</el-divider>

            <el-form-item label="生成数量">
              <el-input-number
                v-model="form.batch_size"
                :min="1"
                :max="10"
                size="small"
              />
              <span class="form-tip">一次生成1-10个剧本</span>
            </el-form-item>

            <el-form-item label="仅返回最佳">
              <el-switch v-model="form.return_best_only" />
              <span class="form-tip">仅返回评分最高的剧本</span>
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                :loading="generating"
                @click="handleGenerate"
                size="large"
              >
                <el-icon><MagicStick /></el-icon>
                {{ form.batch_size > 1 ? '批次生成' : '生成剧本' }}
              </el-button>
              <el-button @click="handleReset" size="large">重置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card class="output-card">
          <template #header>
            <div class="card-header">
              <el-icon><Document /></el-icon>
              <span>生成结果</span>
            </div>
          </template>

          <div v-if="batchResults.length > 1" class="batch-tabs">
            <el-radio-group v-model="activeScriptIndex" size="small">
              <el-radio-button
                v-for="(script, index) in batchResults"
                :key="index"
                :label="index"
              >
                剧本{{ index + 1 }}
                <el-tag v-if="index === bestScriptIndex" type="success" size="small" style="margin-left: 4px">
                  最佳
                </el-tag>
              </el-radio-button>
            </el-radio-group>
          </div>

          <div v-if="currentScript" class="script-content">
            <div class="script-text">{{ currentScript.generated_script }}</div>
            <div class="meta-info">
              <el-tag size="small">置信度: {{ (currentScript.confidence * 100).toFixed(1) }}%</el-tag>
              <el-tag size="small" type="info">参考剧情: {{ currentScript.referenced_units?.length || 0 }}</el-tag>
              <el-tag v-if="currentScript.style" size="small" type="warning">{{ getStyleLabel(currentScript.style) }}</el-tag>
              <el-tag v-if="currentScript.length" size="small" type="success">{{ getLengthLabel(currentScript.length) }}</el-tag>
            </div>
            <div v-if="currentScript.evaluation" class="evaluation">
              <el-divider>质量评估</el-divider>
              <el-row :gutter="8">
                <el-col :span="8" v-for="(score, key) in getEvaluationScores(currentScript.evaluation)" :key="key">
                  <div class="score-item">
                    <div class="score-label">{{ getEvaluationLabel(key) }}</div>
                    <el-progress :percentage="score * 10" :color="getScoreColor(score)" />
                  </div>
                </el-col>
              </el-row>
              <div class="overall-score">
                <span>总体评分: </span>
                <el-tag :type="getQualityLevelColor(currentScript.evaluation.overall_score)" size="large">
                  {{ currentScript.evaluation.overall_score.toFixed(1) }} - {{ currentScript.evaluation.quality_level }}
                </el-tag>
              </div>
            </div>
          </div>

          <el-empty v-else description="点击生成按钮开始生成剧本" />

          <div v-if="batchResults.length > 1" class="batch-stats">
            <el-divider>批次统计</el-divider>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="生成数量">{{ batchResults.length }}</el-descriptions-item>
              <el-descriptions-item label="生成耗时">{{ generationTime.toFixed(2) }}秒</el-descriptions-item>
              <el-descriptions-item label="最佳剧本索引">{{ bestScriptIndex + 1 }}</el-descriptions-item>
              <el-descriptions-item label="平均评分">{{ averageScore.toFixed(1) }}</el-descriptions-item>
            </el-descriptions>
          </div>
        </el-card>

        <el-card class="reference-card">
          <template #header>
            <div class="card-header">
              <el-icon><Reading /></el-icon>
              <span>参考剧情单元</span>
            </div>
          </template>

          <div v-if="currentScript?.referenced_units?.length > 0" class="reference-list">
            <div
              v-for="(unit, index) in currentScript.referenced_units"
              :key="index"
              class="reference-item"
            >
              <el-tag size="small" type="success">剧情{{ index + 1 }}</el-tag>
              <span class="reference-text">{{ unit }}</span>
            </div>
          </div>

          <el-empty v-else description="暂无参考剧情" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { scriptApi } from '@/api/script'

const form = reactive({
  plot_context: '',
  required_conflict: '',
  required_emotion: '',
  characters: [],
  scene: '',
  constraints: {},
  style: 'standard',
  length: 'medium',
  innovation_degree: 0.5,
  goal_driven: false,
  batch_size: 1,
  return_best_only: false,
  enable_quality_evaluation: false,
  weights: {
    conflict_intensity: 0.2,
    emotion_rendering: 0.15,
    character_consistency: 0.2,
    dialogue_naturalness: 0.15,
    dramatic_tension: 0.15,
    overall_coherence: 0.15
  }
})

const generating = ref(false)
const batchResults = ref([])
const activeScriptIndex = ref(0)
const bestScriptIndex = ref(0)
const generationTime = ref(0)

const currentScript = computed(() => {
  if (batchResults.value.length === 0) return null
  return batchResults.value[activeScriptIndex.value]
})

const averageScore = computed(() => {
  if (batchResults.value.length === 0) return 0
  const scores = batchResults.value
    .map(s => s.evaluation?.overall_score || 0)
    .filter(s => s > 0)
  if (scores.length === 0) return 0
  return scores.reduce((a, b) => a + b, 0) / scores.length
})

const totalWeight = computed(() => {
  return Object.values(form.weights).reduce((sum, val) => sum + val, 0)
})

const getStyleLabel = (style) => {
  const labels = {
    standard: '标准',
    humorous: '幽默',
    serious: '严肃',
    romantic: '浪漫'
  }
  return labels[style] || style
}

const getLengthLabel = (length) => {
  const labels = {
    short: '短',
    medium: '中',
    long: '长'
  }
  return labels[length] || length
}

const getEvaluationScores = (evaluation) => {
  return {
    conflict_intensity: evaluation.conflict_intensity?.score || 0,
    emotion_rendering: evaluation.emotion_rendering?.score || 0,
    character_consistency: evaluation.character_consistency?.score || 0,
    dialogue_naturalness: evaluation.dialogue_naturalness?.score || 0,
    dramatic_tension: evaluation.dramatic_tension?.score || 0,
    overall_coherence: evaluation.overall_coherence?.score || 0
  }
}

const getEvaluationLabel = (key) => {
  const labels = {
    conflict_intensity: '冲突强度',
    emotion_rendering: '情绪渲染',
    character_consistency: '人物一致性',
    dialogue_naturalness: '对话自然度',
    dramatic_tension: '剧情张力',
    overall_coherence: '整体连贯性'
  }
  return labels[key] || key
}

const getScoreColor = (score) => {
  if (score >= 8) return '#67c23a'
  if (score >= 6) return '#e6a23c'
  return '#f56c6c'
}

const getQualityLevelColor = (score) => {
  if (score >= 8.5) return 'success'
  if (score >= 7.0) return 'primary'
  if (score >= 5.5) return 'warning'
  return 'danger'
}

const handleGenerate = async () => {
  if (!form.plot_context) {
    ElMessage.warning('请输入剧情上下文')
    return
  }
  if (!form.required_conflict) {
    ElMessage.warning('请选择冲突类型')
    return
  }
  if (!form.required_emotion) {
    ElMessage.warning('请选择情绪类型')
    return
  }
  if (form.characters.length === 0) {
    ElMessage.warning('请选择出场人物')
    return
  }

  generating.value = true
  batchResults.value = []
  activeScriptIndex.value = 0
  bestScriptIndex.value = 0

  try {
    const requestData = {
      ...form,
      enable_quality_evaluation: form.enable_quality_evaluation
    }

    if (form.batch_size > 1) {
      const result = await scriptApi.generateScriptBatch(requestData)
      batchResults.value = result.scripts

      if (form.enable_quality_evaluation) {
        const evaluations = await scriptApi.evaluateQualityBatch({
          scripts: result.scripts.map((s, i) => ({ id: i.toString(), content: s.generated_script })),
          custom_weights: form.weights
        })
        batchResults.value = result.scripts.map((script, index) => {
          const evalResult = evaluations.results.find(r => r.script_id === index.toString())
          return {
            ...script,
            evaluation: evalResult?.evaluation
          }
        })
        if (evaluations.best_script) {
          const bestId = parseInt(evaluations.best_script.script_id)
          bestScriptIndex.value = result.scripts.findIndex((_, i) => i === bestId)
        }
      } else {
        bestScriptIndex.value = result.best_script_index || 0
      }
      generationTime.value = result.generation_time_seconds || 0
      ElMessage.success(`成功生成 ${batchResults.value.length} 个剧本`)
    } else {
      const result = await scriptApi.generateScript(requestData)
      batchResults.value = [result]

      if (form.enable_quality_evaluation) {
        const evaluation = await scriptApi.evaluateQuality({
          script_content: result.generated_script,
          custom_weights: form.weights
        })
        batchResults.value[0].evaluation = evaluation
      }

      generationTime.value = 0
      ElMessage.success('剧本生成成功')
    }
  } catch (error) {
    ElMessage.error('生成失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    generating.value = false
  }
}

const resetWeights = () => {
  form.weights = {
    conflict_intensity: 0.2,
    emotion_rendering: 0.15,
    character_consistency: 0.2,
    dialogue_naturalness: 0.15,
    dramatic_tension: 0.15,
    overall_coherence: 0.15
  }
}

const handleReset = () => {
  form.plot_context = ''
  form.required_conflict = ''
  form.required_emotion = ''
  form.characters = []
  form.scene = ''
  form.style = 'standard'
  form.length = 'medium'
  form.innovation_degree = 0.5
  form.goal_driven = false
  form.batch_size = 1
  form.return_best_only = false
  form.enable_quality_evaluation = false
  form.weights = {
    conflict_intensity: 0.2,
    emotion_rendering: 0.15,
    character_consistency: 0.2,
    dialogue_naturalness: 0.15,
    dramatic_tension: 0.15,
    overall_coherence: 0.15
  }
  batchResults.value = []
  activeScriptIndex.value = 0
  bestScriptIndex.value = 0
  generationTime.value = 0
}
</script>

<style scoped>
.script-generation {
  padding: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.input-card,
.output-card {
  margin-bottom: 20px;
}

.form-tip {
  margin-left: 8px;
  font-size: 12px;
  color: #909399;
}

.weight-sliders {
  padding: 12px;
  background: #f5f7fa;
  border-radius: 4px;
}

.weight-slider {
  margin-bottom: 16px;
}

.weight-slider:last-child {
  margin-bottom: 0;
}

.weight-label {
  display: block;
  margin-bottom: 8px;
  font-size: 13px;
  color: #606266;
  font-weight: 500;
}

.batch-tabs {
  margin-bottom: 16px;
}

.script-content {
  padding: 16px;
  background: #f5f7fa;
  border-radius: 4px;
}

.script-text {
  white-space: pre-wrap;
  line-height: 1.8;
  margin-bottom: 16px;
}

.meta-info {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.evaluation {
  margin-top: 16px;
}

.score-item {
  margin-bottom: 12px;
}

.score-label {
  font-size: 12px;
  color: #606266;
  margin-bottom: 4px;
}

.overall-score {
  text-align: center;
  margin-top: 16px;
  font-size: 16px;
  font-weight: 600;
}

.batch-stats {
  margin-top: 16px;
}

.reference-list {
  max-height: 300px;
  overflow-y: auto;
}

.reference-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  border-bottom: 1px solid #ebeef5;
}

.reference-item:last-child {
  border-bottom: none;
}

.reference-text {
  flex: 1;
  font-size: 14px;
  color: #606266;
}
</style>
