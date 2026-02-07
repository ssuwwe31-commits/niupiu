<template>
  <div class="novel-manager">
    <el-card>
      <template #header>
        <div class="card-header">
          <el-icon><Reading /></el-icon>
          <span>小说管理</span>
        </div>
      </template>

      <el-button type="primary" @click="showUploadDialog = true">
        <el-icon><Upload /></el-icon>
        上传小说
      </el-button>

      <el-table :data="novels" style="width: 100%; margin-top: 20px">
        <el-table-column prop="title" label="小说名称" width="250" />
        <el-table-column prop="author" label="作者" width="150" />
        <el-table-column prop="file_type" label="类型" width="80">
          <template #default="{ row }">
            <el-tag size="small">{{ row.file_type.toUpperCase() }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="文件大小" width="100">
          <template #default="{ row }">
            {{ formatFileSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column label="章节/单元" width="120">
          <template #default="{ row }">
            {{ row.total_chapters }}章 / {{ row.total_units }}单元
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280">
          <template #default="{ row }">
            <el-button size="small" @click="handleDecompose(row)">
              <el-icon><MagicStick /></el-icon>
              拆解剧情
            </el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="showUploadDialog"
      title="上传小说"
      width="600px"
    >
      <el-form :model="uploadForm" label-width="100px">
        <el-form-item label="小说文件">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            accept=".txt,.epub"
            :on-change="handleFileChange"
          >
            <el-button>选择文件</el-button>
            <template #tip>
              <div class="el-upload__tip">
                支持 .txt 或 .epub 格式
              </div>
            </template>
          </el-upload>
        </el-form-item>

        <el-form-item label="小说名称">
          <el-input v-model="uploadForm.title" placeholder="请输入小说名称" />
        </el-form-item>

        <el-form-item label="作者">
          <el-input v-model="uploadForm.author" placeholder="请输入作者名称（可选）" />
        </el-form-item>

        <el-form-item label="简介">
          <el-input
            v-model="uploadForm.summary"
            type="textarea"
            :rows="3"
            placeholder="请输入小说简介（可选）"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="handleUpload">
          上传
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="showDecomposeDialog"
      title="拆解剧情单元"
      width="500px"
    >
      <el-form :model="decomposeForm" label-width="120px">
        <el-form-item label="小说名称">
          <span>{{ currentNovel?.title }}</span>
        </el-form-item>

        <el-form-item label="章节范围">
          <el-input-number v-model="decomposeForm.startChapter" :min="1" placeholder="开始章节" />
          <span style="margin: 0 10px">-</span>
          <el-input-number v-model="decomposeForm.endChapter" :min="1" placeholder="结束章节" />
        </el-form-item>

        <el-form-item>
          <el-checkbox v-model="decomposeForm.allChapters">拆解所有章节</el-checkbox>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showDecomposeDialog = false">取消</el-button>
        <el-button type="primary" :loading="decomposing" @click="confirmDecompose">
          开始拆解
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { novelApi } from '@/api/novel'

const novels = ref([])
const showUploadDialog = ref(false)
const showDecomposeDialog = ref(false)
const currentNovel = ref(null)
const uploading = ref(false)
const decomposing = ref(false)
const uploadRef = ref(null)

const uploadForm = reactive({
  file: null,
  title: '',
  author: '',
  summary: ''
})

const decomposeForm = reactive({
  startChapter: 1,
  endChapter: 1000,
  allChapters: true
})

const handleFileChange = (file) => {
  uploadForm.file = file.raw
  if (!uploadForm.title) {
    uploadForm.title = file.name.replace(/\.[^/.]+$/, '')
  }
}

const handleUpload = async () => {
  if (!uploadForm.file) {
    ElMessage.warning('请选择小说文件')
    return
  }
  if (!uploadForm.title) {
    ElMessage.warning('请输入小说名称')
    return
  }

  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', uploadForm.file)
    formData.append('title', uploadForm.title)
    formData.append('author', uploadForm.author)
    formData.append('summary', uploadForm.summary)

    await novelApi.uploadNovel(formData)
    ElMessage.success('上传成功')
    showUploadDialog.value = false
    await loadNovels()

    Object.assign(uploadForm, {
      file: null,
      title: '',
      author: '',
      summary: ''
    })
    uploadRef.value?.clearFiles()
  } catch (error) {
    ElMessage.error('上传失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    uploading.value = false
  }
}

const handleDecompose = (novel) => {
  currentNovel.value = novel
  decomposeForm.startChapter = 1
  decomposeForm.endChapter = novel.total_chapters || 1000
  decomposeForm.allChapters = true
  showDecomposeDialog.value = true
}

const confirmDecompose = async () => {
  let chapterRange = null
  if (!decomposeForm.allChapters) {
    chapterRange = [decomposeForm.startChapter, decomposeForm.endChapter]
  }

  decomposing.value = true
  try {
    const result = await novelApi.decomposeNovel(currentNovel.value.id, {
      chapter_range: chapterRange
    })
    ElMessage.success(`拆解完成: ${result.message}`)
    showDecomposeDialog.value = false
    await loadNovels()
  } catch (error) {
    ElMessage.error('拆解失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    decomposing.value = false
  }
}

const handleDelete = async (novel) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除小说"${novel.title}"吗？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await novelApi.deleteNovel(novel.id)
    ElMessage.success('删除成功')
    await loadNovels()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败: ' + (error.response?.data?.detail || error.message))
    }
  }
}

const loadNovels = async () => {
  try {
    novels.value = await novelApi.listNovels()
  } catch (error) {
    ElMessage.error('加载小说列表失败: ' + (error.response?.data?.detail || error.message))
  }
}

const formatFileSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}

const getStatusType = (status) => {
  const typeMap = {
    'uploaded': 'info',
    'decomposed': 'success',
    'decomposing': 'warning',
    'failed': 'danger'
  }
  return typeMap[status] || 'info'
}

const getStatusText = (status) => {
  const textMap = {
    'uploaded': '已上传',
    'decomposed': '已拆解',
    'decomposing': '拆解中',
    'failed': '失败'
  }
  return textMap[status] || status
}

onMounted(() => {
  loadNovels()
})
</script>

<style scoped>
.novel-manager {
  padding: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}
</style>
