<template>
  <div class="page-container">
    <div class="page-header">
      <h2>我的文件</h2>
      <p>管理您上传的所有文件，支持下载、续期、删除等操作</p>
    </div>
    
    <!-- 搜索和操作栏 -->
    <el-card style="margin-bottom: 20px;">
      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
        <div style="display: flex; gap: 12px; flex: 1; min-width: 300px;">
          <el-input
            v-model="searchQuery"
            placeholder="搜索文件名..."
            prefix-icon="Search"
            clearable
            style="width: 300px;"
            @input="handleSearch"
          />
          
          <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width: 150px;" @change="fetchFiles">
            <el-option label="全部" value="" />
            <el-option label="有效" value="active" />
            <el-option label="已过期" value="expired" />
            <el-option label="已删除" value="deleted" />
          </el-select>
        </div>
        
        <div style="display: flex; gap: 8px;">
          <el-button type="primary" icon="Upload" @click="$router.push('/upload')">
            上传文件
          </el-button>
          
          <el-button
            type="danger"
            :disabled="selectedFileIds.length === 0"
            @click="handleBatchDelete"
          >
            批量删除 ({{ selectedFileIds.length }})
          </el-button>
          
          <el-button
            type="success"
            :disabled="selectedFileIds.length === 0"
            @click="handleBatchDownload"
          >
            批量下载 ({{ selectedFileIds.length }})
          </el-button>
        </div>
      </div>
    </el-card>
    
    <!-- 文件列表 -->
    <el-card>
      <el-table
        :data="files"
        stripe
        style="width: 100%"
        @selection-change="handleSelectionChange"
        v-loading="loading"
      >
        <el-table-column type="selection" width="50" />
        
        <el-table-column prop="original_name" label="文件名" min-width="250">
          <template #default="{ row }">
            <div style="display: flex; align-items: center; gap: 8px;">
              <el-icon :size="24" color="#409EFF"><Document /></el-icon>
              <span :class="{ 'file-expired': row.is_expired || row.status === 'deleted' }">
                {{ row.original_name }}
              </span>
              <el-tag v-if="row.is_expired" type="danger" size="small">已过期</el-tag>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="file_size_display" label="大小" width="100" sortable />
        
        <el-table-column label="访问类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getAccessTypeTagType(row.access_type)" size="small">
              {{ getAccessTypeLabel(row.access_type) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="提取码" width="90">
          <template #default="{ row }">
            <span v-if="row.extract_code" style="font-weight: bold; color: #67C23A;">
              {{ row.extract_code }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="download_count" label="下载次数" width="90" sortable />
        
        <el-table-column label="上传时间" width="170">
          <template #default="{ row }">
            {{ formatDate(row.uploaded_at) }}
          </template>
        </el-table-column>
        
        <el-table-column label="过期时间" width="170">
          <template #default="{ row }">
            <span :class="{ 'text-danger': row.is_expired }">
              {{ formatDate(row.expires_at) }}
            </span>
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-space wrap>
              <el-button text type="primary" size="small" @click="downloadFile(row)">
                下载
              </el-button>
              
              <el-button text type="success" size="small" @click="previewFile(row)" :disabled="!canPreview(row)">
                预览
              </el-button>
              
              <el-button text type="warning" size="small" @click="renewFile(row)" :disabled="row.status === 'deleted'">
                续期
              </el-button>
              
              <el-popconfirm title="确定要删除这个文件吗？" @confirm="deleteFile(row)">
                <template #reference>
                  <el-button text type="danger" size="small">删除</el-button>
                </template>
              </el-popconfirm>
              
              <el-dropdown trigger="click" @command="(cmd) => handleCommand(cmd, row)">
                <el-button text size="small">
                  更多<el-icon class="el-icon--right"><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="copy-link">复制链接</el-dropdown-item>
                    <el-dropdown-item command="copy-code" v-if="row.extract_code">复制提取码</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </el-space>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div style="margin-top: 16px; display: flex; justify-content: space-between; align-items: center;">
        <span style="color: #909399; font-size: 14px;">
          共 {{ total }} 个文件
        </span>
        
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="sizes, prev, pager, next, jumper"
          @size-change="fetchFiles"
          @current-change="fetchFiles"
        />
      </div>
    </el-card>
    
    <!-- 续期对话框 -->
    <el-dialog v-model="renewDialogVisible" title="延长文件保留时间" width="400px">
      <div style="padding: 0 20px;">
        <p>当前过期时间：<strong>{{ formatDateTime(currentRenewFile?.expires_at) }}</strong></p>
        
        <el-form label-width="80px" style="margin-top: 20px;">
          <el-form-item label="延长时间">
            <el-input-number
              v-model="renewHours"
              :min="1"
              :max="720"
              :step="1"
            />
            <span style="margin-left: 8px;">小时</span>
          </el-form-item>
          
          <el-form-item>
            <el-radio-group v-model="renewHours" size="small">
              <el-radio-button :value="24">1天</el-radio-button>
              <el-radio-button :value="72">3天</el-radio-button>
              <el-radio-button :value="168">7天</el-radio-button>
              <el-radio-button :value="720">30天</el-radio-button>
            </el-radio-group>
          </el-form-item>
        </el-form>
      </div>
      
      <template #footer>
        <el-button @click="renewDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmRenew" :loading="renewLoading">确认</el-button>
      </template>
    </el-dialog>
    
    <!-- 文件预览对话框 -->
    <el-dialog v-model="previewVisible" :title="previewFileName" width="80%" top="5vh">
      <div style="text-align: center; min-height: 400px;">
        <img
          v-if="previewUrl && isImage(previewMimeType)"
          :src="previewUrl"
          style="max-width: 100%; max-height: 70vh;"
        />
        
        <iframe
          v-else-if="previewUrl && previewMimeType === 'application/pdf'"
          :src="previewUrl"
          style="width: 100%; height: 70vh; border: none;"
        />
        
        <pre
          v-else-if="previewContent"
          style="text-align: left; background: #f5f7fa; padding: 20px; overflow: auto; max-height: 70vh;"
        >{{ previewContent }}</pre>
        
        <div v-else style="padding: 40px; color: #909399;">
          该文件类型不支持在线预览，请下载查看
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'

const router = useRouter()

// 状态
const files = ref([])
const loading = ref(false)
const searchQuery = ref('')
const statusFilter = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const selectedFileIds = ref([])

// 续期相关
const renewDialogVisible = ref(false)
const currentRenewFile = ref(null)
const renewHours = ref(24)
const renewLoading = ref(false)

// 预览相关
const previewVisible = ref(false)
const previewUrl = ref('')
const previewContent = ref('')
const previewFileName = ref('')
const previewMimeType = ref('')

// 获取文件列表
async function fetchFiles() {
  loading.value = true
  
  try {
    const params = {
      page: currentPage.value,
      per_page: pageSize.value,
      search: searchQuery.value,
      status: statusFilter.value
    }
    
    const res = await api.get('/files/list', { params })
    files.value = res.files || []
    total.value = res.total || 0
    
  } catch (error) {
    console.error('获取文件列表失败:', error)
  } finally {
    loading.value = false
  }
}

// 搜索（防抖）
let searchTimer = null
function handleSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  
  searchTimer = setTimeout(() => {
    currentPage.value = 1
    fetchFiles()
  }, 500)
}

// 选择变化
function handleSelectionChange(selection) {
  selectedFileIds.value = selection.map(item => item.id)
}

// 获取访问类型标签
function getAccessTypeLabel(type) {
  const labels = { public: '公开', code: '提取码', private: '指定用户' }
  return labels[type] || type
}

function getAccessTypeTagType(type) {
  const types = { public: '', code: 'success', private: 'warning' }
  return types[type] || ''
}

// 格式化日期
function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

function formatDateTime(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

// 判断是否可以预览
function canPreview(file) {
  const previewTypes = ['image/', 'text/plain', 'application/json', 'application/pdf']
  return previewTypes.some(t => file.mime_type?.startsWith(t))
}

function isImage(mimeType) {
  return mimeType?.startsWith('image/')
}

// 下载文件
function downloadFile(file) {
  window.open(`/api/files/download/${file.id}`, '_blank')
}

// 预览文件
async function previewFile(file) {
  if (!canPreview(file)) {
    ElMessage.warning('该文件类型不支持在线预览')
    return
  }
  
  previewFileName.value = file.original_name
  previewMimeType.value = file.mime_type
  
  try {
    // 对于图片和PDF，直接使用URL
    if (isImage(file.mime_type) || file.mime_type === 'application/pdf') {
      previewUrl.value = `/api/files/preview/${file.id}`
      previewContent.value = ''
    } else {
      // 文本文件，获取内容
      const response = await fetch(`/api/files/preview/${file.id}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
      })
      previewContent.value = await response.text()
      previewUrl.value = ''
    }
    
    previewVisible.value = true
    
  } catch (error) {
    ElMessage.error('预览失败')
  }
}

// 续期文件
function renewFile(file) {
  currentRenewFile.value = file
  renewHours.value = 24
  renewDialogVisible.value = true
}

// 确认续期
async function confirmRenew() {
  if (!currentRenewFile.value) return
  
  renewLoading.value = true
  
  try {
    await api.post(`/files/renew/${currentRenewFile.value.id}`, {
      additional_hours: renewHours.value
    })
    
    ElMessage.success('续期成功')
    renewDialogVisible.value = false
    fetchFiles()
    
  } catch (error) {
    console.error('续期失败:', error)
  } finally {
    renewLoading.value = false
  }
}

// 删除文件
async function deleteFile(file) {
  try {
    await api.delete(`/files/${file.id}`)
    ElMessage.success(`文件 "${file.original_name}" 已删除`)
    fetchFiles()
  } catch (error) {
    console.error('删除失败:', error)
  }
}

// 批量删除
async function handleBatchDelete() {
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedFileIds.value.length} 个文件吗？`,
      '批量删除',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    
    for (const fileId of selectedFileIds.value) {
      await api.delete(`/files/${fileId}`)
    }
    
    ElMessage.success('批量删除成功')
    fetchFiles()
    
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量删除失败:', error)
    }
  }
}

// 批量下载
function handleBatchDownload() {
  window.open('/api/files/batch-download', '_blank', `POST`, JSON.stringify({
    file_ids: selectedFileIds.value
  }))
}

// 处理更多操作
function handleCommand(command, file) {
  switch (command) {
    case 'copy-link':
      copyLink(file)
      break
    case 'copy-code':
      copyCode(file)
      break
  }
}

function copyLink(file) {
  const url = `${window.location.origin}/api/files/download/${file.id}`
  copyToClipboard(url, '链接已复制到剪贴板')
}

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

onMounted(() => {
  fetchFiles()
})
</script>

<style scoped>
.file-expired {
  text-decoration: line-through;
  color: #f56c6c;
}

.text-danger {
  color: #f56c6c;
}
</style>
