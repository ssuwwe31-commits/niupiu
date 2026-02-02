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

            <el-form-item>
              <el-button
                type="primary"
                :loading="generating"
                @click="handleGenerate"
                size="large"
              >
                <el-icon><MagicStick /></el-icon>
                生成剧本
              </el-button>
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

          <div v-if="generatedScript" class="script-content">
            <div class="script-text">{{ generatedScript }}</div>
            <div class="meta-info">
              <el-tag size="small">置信度: {{ confidence }}</el-tag>
              <el-tag size="small" type="info">参考剧情: {{ referencedUnits.length }}</el-tag>
            </div>
          </div>

          <el-empty v-else description="点击生成按钮开始生成剧本" />
        </el-card>

        <el-card class="reference-card">
          <template #header>
            <div class="card-header">
              <el-icon><Reading /></el-icon>
              <span>参考剧情单元</span>
            </div>
          </template>

          <div v-if="referencedUnits.length > 0" class="reference-list">
            <div
              v-for="(unit, index) in referencedUnits"
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
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { scriptApi } from '@/api/script'

const form = reactive({
  plot_context: '',
  required_conflict: '',
  required_emotion: '',
  characters: [],
  scene: '',
  constraints: {}
})

const generating = ref(false)
const generatedScript = ref('')
const confidence = ref(0)
const referencedUnits = ref([])

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
  try {
    const result = await scriptApi.generateScript(form)
    generatedScript.value = result.generated_script
    confidence.value = (result.confidence * 100).toFixed(1) + '%'
    referencedUnits.value = result.referenced_units
    ElMessage.success('剧本生成成功')
  } catch (error) {
    ElMessage.error('生成失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    generating.value = false
  }
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
