<template>
  <div class="character-manager">
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card class="list-card">
          <template #header>
            <div class="card-header">
              <el-icon><User /></el-icon>
              <span>人物列表</span>
              <el-button type="primary" size="small" @click="handleCreate">
                <el-icon><Plus /></el-icon>
                新建人物
              </el-button>
            </div>
          </template>

          <el-input
            v-model="searchKeyword"
            placeholder="搜索人物..."
            clearable
            @input="handleSearch"
            style="margin-bottom: 16px"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>

          <el-scrollbar max-height="calc(100vh - 250px)">
            <div
              v-for="character in filteredCharacters"
              :key="character.id"
              class="character-item"
              :class="{ active: selectedCharacterId === character.id }"
              @click="handleSelect(character)"
            >
              <div class="character-name">{{ character.name }}</div>
              <div class="character-desc">{{ character.description || '暂无描述' }}</div>
            </div>
            <el-empty v-if="filteredCharacters.length === 0" description="暂无人物" />
          </el-scrollbar>
        </el-card>
      </el-col>

      <el-col :span="16">
        <el-card v-if="selectedCharacter" class="detail-card">
          <template #header>
            <div class="card-header">
              <el-icon><UserFilled /></el-icon>
              <span>人物详情</span>
              <el-button type="danger" size="small" @click="handleDelete">
                <el-icon><Delete /></el-icon>
                删除
              </el-button>
            </div>
          </template>

          <el-form :model="form" label-width="120px">
            <el-form-item label="人物名称">
              <el-input v-model="form.name" placeholder="输入人物名称" />
            </el-form-item>

            <el-form-item label="描述">
              <el-input
                v-model="form.description"
                type="textarea"
                :rows="2"
                placeholder="人物简要描述"
              />
            </el-form-item>

            <el-divider>核心设定</el-divider>

            <el-form-item label="核心性格">
              <el-input
                v-model="form.core_personality"
                type="textarea"
                :rows="3"
                placeholder="描述人物的核心性格特征"
              />
            </el-form-item>

            <el-form-item label="背景设定">
              <el-input
                v-model="form.background"
                type="textarea"
                :rows="3"
                placeholder="描述人物的背景故事"
              />
            </el-form-item>

            <el-form-item label="底线">
              <el-input
                v-model="form.bottom_line"
                type="textarea"
                :rows="2"
                placeholder="描述人物的底线和原则"
              />
            </el-form-item>

            <el-divider>当前状态</el-divider>

            <el-form-item label="当前情绪">
              <el-input
                v-model="form.current_emotion"
                type="textarea"
                :rows="2"
                placeholder="描述人物当前的情绪状态"
              />
            </el-form-item>

            <el-form-item label="目标">
              <el-input
                v-model="form.goals"
                type="textarea"
                :rows="2"
                placeholder="描述人物的当前目标"
              />
            </el-form-item>

            <el-form-item label="关系">
              <el-input
                v-model="form.relationships"
                type="textarea"
                :rows="2"
                placeholder="描述人物与其他角色的关系"
              />
            </el-form-item>

            <el-form-item>
              <el-button type="primary" :loading="saving" @click="handleSave">
                <el-icon><Check /></el-icon>
                保存修改
              </el-button>
              <el-button @click="handleRefresh">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card v-else class="empty-card">
          <el-empty description="请选择或创建一个人物" />
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="dialogVisible" title="新建人物" width="500px">
      <el-form :model="newForm" label-width="120px">
        <el-form-item label="人物名称" required>
          <el-input v-model="newForm.name" placeholder="输入人物名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="newForm.description"
            type="textarea"
            :rows="2"
            placeholder="人物简要描述"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleConfirmCreate">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { characterApi } from '@/api/character'

const characters = ref([])
const selectedCharacterId = ref(null)
const searchKeyword = ref('')
const dialogVisible = ref(false)
const saving = ref(false)

const form = reactive({
  id: '',
  name: '',
  description: '',
  core_personality: '',
  background: '',
  bottom_line: '',
  current_emotion: '',
  goals: '',
  relationships: ''
})

const newForm = reactive({
  name: '',
  description: ''
})

const selectedCharacter = computed(() => {
  return characters.value.find(c => c.id === selectedCharacterId.value)
})

const filteredCharacters = computed(() => {
  if (!searchKeyword.value) return characters.value
  return characters.value.filter(c => 
    c.name.toLowerCase().includes(searchKeyword.value.toLowerCase()) ||
    (c.description && c.description.toLowerCase().includes(searchKeyword.value.toLowerCase()))
  )
})

const loadCharacters = async () => {
  try {
    const result = await characterApi.listCharacters(0, 100)
    characters.value = result.items || result || []
  } catch (error) {
    ElMessage.error('加载人物列表失败: ' + (error.response?.data?.detail || error.message))
  }
}

const handleSelect = (character) => {
  selectedCharacterId.value = character.id
  form.id = character.id
  form.name = character.name || ''
  form.description = character.description || ''
  form.core_personality = character.core_personality || ''
  form.background = character.background || ''
  form.bottom_line = character.bottom_line || ''
  form.current_emotion = character.current_emotion || ''
  form.goals = character.goals || ''
  form.relationships = character.relationships || ''
}

const handleCreate = () => {
  newForm.name = ''
  newForm.description = ''
  dialogVisible.value = true
}

const handleConfirmCreate = async () => {
  if (!newForm.name) {
    ElMessage.warning('请输入人物名称')
    return
  }
  try {
    await characterApi.createCharacter(newForm)
    ElMessage.success('创建成功')
    dialogVisible.value = false
    await loadCharacters()
  } catch (error) {
    ElMessage.error('创建失败: ' + (error.response?.data?.detail || error.message))
  }
}

const handleSave = async () => {
  if (!form.id) {
    ElMessage.warning('请先选择一个人物')
    return
  }
  if (!form.name) {
    ElMessage.warning('人物名称不能为空')
    return
  }
  saving.value = true
  try {
    const updateData = {}
    if (form.description !== undefined) updateData.description = form.description
    if (form.core_personality !== undefined) updateData.core_personality = form.core_personality
    if (form.background !== undefined) updateData.background = form.background
    if (form.bottom_line !== undefined) updateData.bottom_line = form.bottom_line
    if (form.current_emotion !== undefined) updateData.current_emotion = form.current_emotion
    if (form.goals !== undefined) updateData.goals = form.goals
    if (form.relationships !== undefined) updateData.relationships = form.relationships

    await characterApi.updateCharacter(form.id, updateData)
    ElMessage.success('保存成功')
    await loadCharacters()
  } catch (error) {
    ElMessage.error('保存失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    saving.value = false
  }
}

const handleRefresh = async () => {
  if (selectedCharacterId.value) {
    try {
      const character = await characterApi.getCharacter(selectedCharacterId.value)
      handleSelect(character)
      ElMessage.success('刷新成功')
    } catch (error) {
      ElMessage.error('刷新失败: ' + (error.response?.data?.detail || error.message))
    }
  }
}

const handleDelete = async () => {
  if (!selectedCharacterId.value) {
    ElMessage.warning('请先选择一个人物')
    return
  }
  try {
    await ElMessageBox.confirm(
      '确定要删除这个人物吗？此操作不可恢复。',
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    await characterApi.deleteCharacter(selectedCharacterId.value)
    ElMessage.success('删除成功')
    selectedCharacterId.value = null
    form.id = ''
    form.name = ''
    form.description = ''
    form.core_personality = ''
    form.background = ''
    form.bottom_line = ''
    form.current_emotion = ''
    form.goals = ''
    form.relationships = ''
    await loadCharacters()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败: ' + (error.response?.data?.detail || error.message))
    }
  }
}

const handleSearch = () => {
}

onMounted(() => {
  loadCharacters()
})
</script>

<style scoped>
.character-manager {
  padding: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  justify-content: space-between;
}

.list-card,
.detail-card {
  height: calc(100vh - 100px);
}

.character-item {
  padding: 12px;
  border-bottom: 1px solid #ebeef5;
  cursor: pointer;
  transition: background-color 0.3s;
}

.character-item:hover {
  background-color: #f5f7fa;
}

.character-item.active {
  background-color: #ecf5ff;
  border-left: 3px solid #409eff;
}

.character-name {
  font-weight: 600;
  margin-bottom: 4px;
}

.character-desc {
  font-size: 12px;
  color: #909399;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-card {
  height: calc(100vh - 100px);
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
