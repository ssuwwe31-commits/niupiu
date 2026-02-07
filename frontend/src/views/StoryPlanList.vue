<template>
  <div class="story-plan-list">
    <el-card>
      <template #header>
        <div class="card-header">
          <el-icon><FolderOpened /></el-icon>
          <span>剧情规划历史</span>
          <el-button type="primary" @click="handleCreate" style="margin-left: auto">
            <el-icon><Plus /></el-icon>
            新建规划
          </el-button>
        </div>
      </template>

      <div class="search-section">
        <el-row :gutter="10">
          <el-col :span="6">
            <el-input v-model="searchTitle" placeholder="搜索标题..." clearable />
          </el-col>
          <el-col :span="4">
            <el-select v-model="searchStatus" placeholder="状态" clearable>
              <el-option label="草稿" value="draft" />
              <el-option label="进行中" value="in_progress" />
              <el-option label="已完成" value="completed" />
            </el-select>
          </el-col>
          <el-col :span="4">
            <el-select v-model="searchStructure" placeholder="剧情结构" clearable>
              <el-option label="三幕式" value="three_act" />
              <el-option label="英雄之旅" value="heros_journey" />
              <el-option label="布莱克·斯奈德" value="blake_snyder" />
            </el-select>
          </el-col>
          <el-col :span="4">
            <el-button type="primary" @click="handleSearch">搜索</el-button>
          </el-col>
        </el-row>
      </div>

      <el-divider />

      <el-table :data="storyPlans" style="width: 100%" v-loading="loading">
        <el-table-column prop="title" label="标题" min-width="180" />
        <el-table-column prop="structure_type" label="剧情结构" width="120">
          <template #default="{ row }">
            <el-tag :type="getStructureTypeColor(row.structure_type)">
              {{ getStructureTypeName(row.structure_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="total_scene_count" label="总场次" width="80" align="center" />
        <el-table-column label="人物" width="150">
          <template #default="{ row }">
            <el-tag
              v-for="char in row.characters.slice(0, 3)"
              :key="char"
              size="small"
              style="margin-right: 4px; margin-bottom: 4px"
            >
              {{ char }}
            </el-tag>
            <span v-if="row.characters.length > 3" style="font-size: 12px; color: #909399">
              +{{ row.characters.length - 3 }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusName(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleView(row.id)">
              查看
            </el-button>
            <el-button link type="primary" @click="handleEdit(row.id)">
              编辑
            </el-button>
            <el-button link type="danger" @click="handleDelete(row.id)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-section">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <el-dialog
      v-model="showDetailDialog"
      :title="`查看规划 - ${currentPlan?.title}`"
      width="80%"
    >
      <div v-if="currentPlan" class="plan-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="标题" :span="2">
            {{ currentPlan.title }}
          </el-descriptions-item>
          <el-descriptions-item label="剧情结构">
            {{ getStructureTypeName(currentPlan.structure_type) }}
          </el-descriptions-item>
          <el-descriptions-item label="总场次">
            {{ currentPlan.total_scene_count }} 场
          </el-descriptions-item>
          <el-descriptions-item label="人物" :span="2">
            <el-tag
              v-for="char in currentPlan.characters"
              :key="char"
              size="small"
              style="margin-right: 4px; margin-bottom: 4px"
            >
              {{ char }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="故事梗概" :span="2">
            {{ currentPlan.story_outline }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(currentPlan.status)">
              {{ getStatusName(currentPlan.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ formatDate(currentPlan.created_at) }}
          </el-descriptions-item>
        </el-descriptions>

        <el-divider>剧情阶段</el-divider>

        <el-collapse v-model="activePhases">
          <el-collapse-item
            v-for="phase in currentPlan.phases_data"
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

            <div v-if="phase.scenes && phase.scenes.length > 0" class="phase-scenes">
              <div
                v-for="scene in phase.scenes"
                :key="scene.scene_number"
                class="scene-item"
              >
                <div class="scene-header">
                  <el-tag>Scene {{ scene.scene_number }}</el-tag>
                  <span class="scene-description">{{ scene.scene_description }}</span>
                </div>
              </div>
            </div>
            <el-empty v-else description="暂无场景详情" :image-size="60" />
          </el-collapse-item>
        </el-collapse>
      </div>

      <template #footer>
        <el-button @click="showDetailDialog = false">关闭</el-button>
        <el-button type="primary" @click="handleLoadToPlanner">
          加载到规划器
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { storyPlanApi } from '@/api/storyPlan'

const router = useRouter()

const loading = ref(false)
const storyPlans = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const searchTitle = ref('')
const searchStatus = ref('')
const searchStructure = ref('')

const showDetailDialog = ref(false)
const currentPlan = ref(null)
const activePhases = ref([])

const formatDate = (dateString) => {
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

const getStructureTypeName = (type) => {
  const map = {
    'three_act': '三幕式',
    'heros_journey': '英雄之旅',
    'blake_snyder': '布莱克·斯奈德'
  }
  return map[type] || type
}

const getStructureTypeColor = (type) => {
  const map = {
    'three_act': 'primary',
    'heros_journey': 'success',
    'blake_snyder': 'warning'
  }
  return map[type] || 'info'
}

const getStatusName = (status) => {
  const map = {
    'draft': '草稿',
    'in_progress': '进行中',
    'completed': '已完成'
  }
  return map[status] || status
}

const getStatusType = (status) => {
  const map = {
    'draft': 'info',
    'in_progress': 'warning',
    'completed': 'success'
  }
  return map[status] || 'info'
}

const getPhaseType = (phaseName) => {
  if (phaseName.includes('setup') || phaseName.includes('ordinary')) return 'info'
  if (phaseName.includes('confrontation') || phaseName.includes('ordeal')) return 'danger'
  if (phaseName.includes('resolution') || phaseName.includes('return')) return 'success'
  return 'primary'
}

const loadStoryPlans = async () => {
  loading.value = true
  try {
    const params = {
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value
    }

    if (searchStatus.value) params.status = searchStatus.value

    const result = await storyPlanApi.listStoryPlans(params)
    storyPlans.value = result.items
    total.value = result.total
  } catch (error) {
    ElMessage.error('加载规划列表失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  loadStoryPlans()
}

const handleSizeChange = () => {
  currentPage.value = 1
  loadStoryPlans()
}

const handleCurrentChange = () => {
  loadStoryPlans()
}

const handleCreate = () => {
  router.push('/story-planner')
}

const handleView = async (id) => {
  try {
    const plan = await storyPlanApi.getStoryPlan(id)
    currentPlan.value = plan
    activePhases.value = plan.phases_data.map(p => p.name)
    showDetailDialog.value = true
  } catch (error) {
    ElMessage.error('加载规划详情失败: ' + (error.response?.data?.detail || error.message))
  }
}

const handleEdit = (id) => {
  router.push({ path: '/story-planner', query: { plan_id: id } })
}

const handleDelete = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除这个规划吗？', '确认删除', {
      type: 'warning'
    })

    await storyPlanApi.deleteStoryPlan(id)
    ElMessage.success('删除成功')
    loadStoryPlans()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败: ' + (error.response?.data?.detail || error.message))
    }
  }
}

const handleLoadToPlanner = () => {
  if (!currentPlan.value) return
  showDetailDialog.value = false
  router.push({ path: '/story-planner', query: { plan_id: currentPlan.value.id } })
}

onMounted(() => {
  loadStoryPlans()
})
</script>

<style scoped>
.story-plan-list {
  padding: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.search-section {
  margin-bottom: 16px;
}

.pagination-section {
  margin-top: 16px;
  display: flex;
  justify-content: center;
}

.plan-detail {
  padding: 16px;
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
  margin-bottom: 12px;
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
}

.scene-description {
  font-weight: 500;
  color: #303133;
}
</style>
