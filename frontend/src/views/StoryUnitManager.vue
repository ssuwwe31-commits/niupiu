<template>
  <div class="story-unit-manager">
    <el-card>
      <template #header>
        <div class="card-header">
          <el-icon><List /></el-icon>
          <span>剧情单元管理</span>
        </div>
      </template>

      <el-form :model="form" label-width="100px" class="add-form">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="场景">
              <el-input v-model="form.scene" placeholder="场景" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="核心冲突">
              <el-input v-model="form.core_conflict" placeholder="核心冲突" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="冲突类型">
              <el-select v-model="form.conflict_type" placeholder="冲突类型">
                <el-option label="背叛" value="背叛" />
                <el-option label="复仇" value="复仇" />
                <el-option label="权力斗争" value="权力斗争" />
                <el-option label="误会" value="误会" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="情绪类型">
              <el-select v-model="form.emotion_type" placeholder="情绪类型">
                <el-option label="高燃" value="高燃" />
                <el-option label="爽点" value="爽点" />
                <el-option label="虐点" value="虐点" />
                <el-option label="反转" value="反转" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="剧情功能">
              <el-select v-model="form.plot_function" placeholder="剧情功能">
                <el-option label="开局钩子" value="开局钩子" />
                <el-option label="高潮" value="高潮" />
                <el-option label="低谷" value="低谷" />
                <el-option label="转折" value="转折" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item>
              <el-button type="primary" @click="handleAdd">添加剧情单元</el-button>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="原始文本">
          <el-input v-model="form.original_text" type="textarea" :rows="3" placeholder="剧情原始文本..." />
        </el-form-item>
      </el-form>

      <el-divider />

      <div class="search-section">
        <h3>检索剧情单元</h3>
        <el-row :gutter="10">
          <el-col :span="6">
            <el-input v-model="searchQuery" placeholder="检索查询..." />
          </el-col>
          <el-col :span="4">
            <el-select v-model="searchConflictType" placeholder="冲突类型" clearable>
              <el-option label="背叛" value="背叛" />
              <el-option label="复仇" value="复仇" />
              <el-option label="权力斗争" value="权力斗争" />
              <el-option label="误会" value="误会" />
            </el-select>
          </el-col>
          <el-col :span="4">
            <el-select v-model="searchEmotionType" placeholder="情绪类型" clearable>
              <el-option label="高燃" value="高燃" />
              <el-option label="爽点" value="爽点" />
              <el-option label="虐点" value="虐点" />
              <el-option label="反转" value="反转" />
            </el-select>
          </el-col>
          <el-col :span="4">
            <el-button type="primary" @click="handleSearch">检索</el-button>
          </el-col>
        </el-row>
      </div>

      <el-divider />

      <el-table :data="storyUnits" style="width: 100%">
        <el-table-column prop="scene" label="场景" width="150" />
        <el-table-column prop="core_conflict" label="核心冲突" width="150" />
        <el-table-column prop="conflict_type" label="冲突类型" width="100" />
        <el-table-column prop="emotion_type" label="情绪类型" width="100" />
        <el-table-column prop="original_text" label="原文" show-overflow-tooltip />
        <el-table-column label="评分" width="80">
          <template #default="{ row }">
            <el-tag size="small">{{ (row.score * 100).toFixed(1) }}%</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { scriptApi } from '@/api/script'

const form = reactive({
  scene: '',
  characters: [],
  core_conflict: '',
  emotion_curve: [],
  plot_function: '',
  result: '',
  original_text: '',
  conflict_type: '',
  emotion_type: '',
  character_relationship: '',
  time_position: '',
  pre_dependencies: {},
  post_effects: {},
  chapter: null,
  confidence_score: 0.0
})

const searchQuery = ref('')
const searchConflictType = ref('')
const searchEmotionType = ref('')
const storyUnits = ref([])

const handleAdd = async () => {
  if (!form.scene || !form.core_conflict || !form.original_text) {
    ElMessage.warning('请填写必要字段')
    return
  }

  try {
    await scriptApi.createStoryUnit(form)
    ElMessage.success('添加成功')
    Object.assign(form, {
      scene: '',
      characters: [],
      core_conflict: '',
      emotion_curve: [],
      plot_function: '',
      result: '',
      original_text: '',
      conflict_type: '',
      emotion_type: '',
      character_relationship: '',
      time_position: '',
      pre_dependencies: {},
      post_effects: {},
      chapter: null,
      confidence_score: 0.0
    })
  } catch (error) {
    ElMessage.error('添加失败: ' + (error.response?.data?.detail || error.message))
  }
}

const handleSearch = async () => {
  try {
    const result = await scriptApi.searchStoryUnits({
      query: searchQuery.value,
      conflict_type: searchConflictType.value,
      emotion_type: searchEmotionType.value,
      top_k: 10
    })
    storyUnits.value = result.results.map(item => ({
      scene: item.metadata?.scene || '',
      core_conflict: item.metadata?.core_conflict || '',
      conflict_type: item.metadata?.conflict_type || '',
      emotion_type: item.metadata?.emotion_type || '',
      original_text: item.text,
      score: item.score || 0
    }))
  } catch (error) {
    ElMessage.error('检索失败: ' + (error.response?.data?.detail || error.message))
  }
}

onMounted(() => {
  handleSearch()
})
</script>

<style scoped>
.story-unit-manager {
  padding: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.add-form {
  margin-bottom: 20px;
}

.search-section h3 {
  margin-top: 0;
  margin-bottom: 16px;
}
</style>
