<template>
  <div class="page-container">
    <div class="page-header">
      <h2>上传文件</h2>
      <p>支持单文件上传和批量上传，大文件（≥100MB）自动分块上传</p>
    </div>
    
    <!-- 上传区域 -->
    <el-card>
      <div
        class="upload-area"
        :class="{ 'is-dragover': isDragOver }"
        @drop.prevent="handleDrop"
        @dragover.prevent="isDragOver = true"
        @dragleave.prevent="isDragOver = false"
        @click="triggerFileInput"
      >
        <el-icon class="upload-icon"><UploadFilled /></el-icon>
        <div class="upload-text">将文件拖到此处，或点击选择文件</div>
        <div class="upload-hint">
          支持所有文件类型，单个文件最大10GB
        </div>
        
        <input
          ref="fileInputRef"
          type="file"
          multiple
          style="display: none;"
          @change="handleFileSelect"
        />
      </div>
      
      <!-- 上传设置 -->
      <div v-if="selectedFiles.length > 0" style="margin-top: 20px;">
        <el-divider content-position="left">上传设置</el-divider>
        
        <el-form :model="uploadConfig" label-width="120px" style="max-width: 600px;">
          <el-form-item label="访问权限">
            <el-radio-group v-model="uploadConfig.access_type">
              <el-radio value="public">
                公开链接（任何人可通过链接访问）
              </el-radio>
              <el-radio value="code">
                提取码（需提供提取码才能下载）
              </el-radio>
              <el-radio value="private">
                指定用户（只有指定用户可访问）
              </el-radio>
            </el-radio-group>
          </el-form-item>
          
          <el-form-item v-if="uploadConfig.access_type === 'private'" label="允许的用户">
            <el-select
              v-model="uploadConfig.allowed_users"
              multiple
              placeholder="选择允许访问的用户"
              style="width: 100%;"
            >
              <el-option
                v-for="user in userList"
                :key="user.id"
                :label="user.username"
                :value="user.id"
              />
            </el-select>
          </el-form-item>
          
          <el-form-item label="保留时长">
            <el-input-number
              v-model="uploadConfig.expiry_hours"
              :min="1"
              :max="720"
              :step="1"
            />
            <span style="margin-left: 8px; color: #909399;">小时（最长30天）</span>
          </el-form-item>
          
          <el-form-item>
            <el-button type="primary" size="large" @click="startUpload" :loading="uploading">
              <el-icon><Upload /></el-icon>
              开始上传 ({{ selectedFiles.length }}个文件)
            </el-button>
            <el-button @click="clearFiles" :disabled="uploading">清空</el-button>
          </el-form-item>
        </el-form>
      </div>
      
      <!-- 文件列表 -->
      <div v-if="selectedFiles.length > 0" style="margin-top: 20px;">
        <el-divider content-position="left">待上传文件</el-divider>
        
        <div v-for="(file, index) in selectedFiles" :key="index" class="file-item">
          <el-icon class="file-icon"><Document /></el-icon>
          
          <div class="file-info">
            <div class="file-name">{{ file.name }}</div>
            <div class="file-meta">
              <span>{{ formatSize(file.size) }}</span>
              <span>{{ getAccessTypeLabel(uploadConfig.access_type) }}</span>
            </div>
          </div>
          
          <div style="width: 200px;">
            <el-progress
              :percentage="uploadProgress[index] || 0"
              :status="getProgressStatus(index)"
            />
          </div>
          
          <el-button
            text
            type="danger"
            icon="Delete"
            @click="removeFile(index)"
            :disabled="uploading"
          />
        </div>
      </div>
    </el-card>
    
    <!-- 上传结果 -->
    <el-card v-if="uploadedFiles.length > 0" style="margin-top: 24px;">
      <template #header>
        <span>上传成功</span>
      </template>
      
      <el-table :data="uploadedFiles" stripe>
        <el-table-column prop="original_name" label="文件名" min-width="200" />
        <el-table-column prop="file_size_display" label="大小" width="100" />
        <el-table-column label="提取码" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.extract_code" type="success">{{ row.extract_code }}</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="过期时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.expires_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" @click="copyLink(row)">复制链接</el-button>
            <el-button text type="success" v-if="row.extract_code" @click="copyCode(row)">
              复制提取码
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

const fileInputRef = ref(null)
const selectedFiles = ref([])
const isDragOver = ref(false)
const uploading = ref(false)
const uploadProgress = ref({})
const uploadedFiles = ref([])
const userList = ref([])

// 上传配置
const uploadConfig = reactive({
  access_type: 'public',
  expiry_hours: 24,
  allowed_users: []
})

// 触发文件选择
function triggerFileInput() {
  fileInputRef.value?.click()
}

// 处理文件选择
function handleFileSelect(event) {
  const files = Array.from(event.target.files)
  addFiles(files)
}

// 处理拖拽放置
function handleDrop(event) {
  isDragOver.value = false
  const files = Array.from(event.dataTransfer.files)
  addFiles(files)
}

// 添加文件到列表
function addFiles(files) {
  files.forEach(file => {
    if (!selectedFiles.value.find(f => f.name === file.name && f.size === file.size)) {
      selectedFiles.value.push(file)
    }
  })
}

// 移除文件
function removeFile(index) {
  selectedFiles.value.splice(index, 1)
}

// 清空文件列表
function clearFiles() {
  selectedFiles.value = []
  uploadProgress.value = {}
}

// 获取访问类型标签
function getAccessTypeLabel(type) {
  const labels = {
    public: '公开',
    code: '提取码',
    private: '指定用户'
  }
  return labels[type] || type
}

// 格式化文件大小
function formatSize(bytes) {
  if (!bytes || bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let unitIndex = 0
  let size = bytes
  
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }
  
  return `${size.toFixed(2)} ${units[unitIndex]}`
}

// 格式化日期时间
function formatDateTime(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('zh-CN')
}

// 获取进度状态
function getProgressStatus(index) {
  const progress = uploadProgress.value[index]
  if (progress === 100) return 'success'
  if (progress > 0) return undefined
  return undefined
}

// 开始上传
async function startUpload() {
  if (selectedFiles.value.length === 0) {
    ElMessage.warning('请先选择文件')
    return
  }
  
  uploading.value = true
  uploadedFiles.value = []
  
  for (let i = 0; i < selectedFiles.value.length; i++) {
    const file = selectedFiles.value[i]
    
    try {
      // 大文件使用分块上传
      if (file.size >= 100 * 1024 * 1024) { // >= 100MB
        await uploadChunkedFile(file, i)
      } else {
        await uploadSingleFile(file, i)
      }
    } catch (error) {
      console.error(`文件 ${file.name} 上传失败:`, error)
      ElMessage.error(`文件 ${file.name} 上传失败`)
    }
  }
  
  uploading.value = false
  
  if (uploadedFiles.value.length > 0) {
    ElMessage.success(`成功上传 ${uploadedFiles.value.length} 个文件`)
    clearFiles()
  }
}

// 单文件上传
async function uploadSingleFile(file, index) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('access_type', uploadConfig.access_type)
  formData.append('expiry_hours', uploadConfig.expiry_hours)
  
  if (uploadConfig.access_type === 'private') {
    formData.append('allowed_users', JSON.stringify(uploadConfig.allowed_users))
  }
  
  try {
    const res = await api.post('/files/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
        uploadProgress.value[index] = progress
      },
      timeout: 300000 // 5分钟超时
    })
    
    uploadProgress.value[index] = 100
    uploadedFiles.value.push(res)
    
  } catch (error) {
    throw error
  }
}

// 分块上传
async function uploadChunkedFile(file, index) {
  try {
    // 1. 初始化分块上传
    const initRes = await api.post('/files/upload/init', {
      filename: file.name,
      file_size: file.size,
      mime_type: file.type || 'application/octet-stream',
      access_type: uploadConfig.access_type,
      expiry_hours: uploadConfig.expiry_hours,
      allowed_users: uploadConfig.allowed_users
    })
    
    const { upload_id, file_id, chunk_size, chunk_total } = initRes
    
    // 2. 分块上传
    let uploadedChunks = 0
    
    for (let chunkIndex = 0; chunkIndex < chunk_total; chunkIndex++) {
      const start = chunkIndex * chunk_size
      const end = Math.min(start + chunk_size, file.size)
      const chunk = file.slice(start, end)
      
      const formData = new FormData()
      formData.append('chunk', chunk)
      formData.append('upload_id', upload_id)
      formData.append('chunk_index', chunkIndex)
      formData.append('file_id', file_id)
      
      await api.post('/files/upload/chunk', formData, {
        timeout: 120000
      })
      
      uploadedChunks++
      uploadProgress.value[index] = Math.round((uploadedChunks / chunk_total) * 95)
    }
    
    // 3. 完成上传
    const completeRes = await api.post('/files/upload/complete', {
      file_id: file_id,
      upload_id: upload_id
    })
    
    uploadProgress.value[index] = 100
    uploadedFiles.value.push(completeRes)
    
  } catch (error) {
    throw error
  }
}

// 复制链接
function copyLink(file) {
  const url = `${window.location.origin}/api/files/download/${file.id}`
  copyToClipboard(url, '链接已复制到剪贴板')
}

// 复制提取码
function copyCode(file) {
  copyToClipboard(file.extract_code, `提取码 ${file.extract_code} 已复制`)
}

// 通用复制函数（兼容HTTP环境）
function copyToClipboard(text, successMsg) {
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).then(() => {
      ElMessage.success(successMsg)
    }).catch(() => {
      fallbackCopy(text, successMsg)
    })
  } else {
    fallbackCopy(text, successMsg)
  }
}

function fallbackCopy(text, successMsg) {
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.style.position = 'fixed'
  textarea.style.opacity = '0'
  document.body.appendChild(textarea)
  textarea.select()
  try {
    document.execCommand('copy')
    ElMessage.success(successMsg)
  } catch (e) {
    ElMessage.error('复制失败，请手动复制: ' + text)
  }
  document.body.removeChild(textarea)
}

// 获取用户列表（用于指定用户模式）
onMounted(async () => {
  try {
    const res = await api.get('/admin/users')
    userList.value = res.users || []
  } catch (error) {
    console.error('获取用户列表失败:', error)
  }
})
</script>

<style scoped>
.upload-area {
  border: 2px dashed #dcdfe6;
  border-radius: 6px;
  padding: 40px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
  
  &:hover {
    border-color: #409EFF;
    background-color: #ecf5ff;
  }
  
  &.is-dragover {
    border-color: #409EFF;
    background-color: #ecf5ff;
  }
}

.upload-icon {
  font-size: 64px;
  color: #c0c4cc;
  margin-bottom: 16px;
}

.upload-text {
  font-size: 16px;
  color: #606266;
  margin-bottom: 8px;
}

.upload-hint {
  font-size: 12px;
  color: #909399;
}

.file-item {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #ebeef5;
  
  .file-icon {
    font-size: 32px;
    margin-right: 12px;
    color: #409EFF;
  }
  
  .file-info {
    flex: 1;
    
    .file-name {
      font-weight: 500;
      color: #303133;
      margin-bottom: 4px;
    }
    
    .file-meta {
      font-size: 12px;
      color: #909399;
      
      span {
        margin-right: 16px;
      }
    }
  }
}
</style>
