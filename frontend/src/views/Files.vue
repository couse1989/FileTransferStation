<template>
  <div class="page-container">
    <div class="page-header">
      <h2>我的文件</h2>
      <p>管理您上传的所有文件，支持下载、续期、删除等操作</p>
    </div>
    
    <!-- 搜索和操作栏 -->
    <el-card style="margin-bottom: 12px;">
      <div class="files-toolbar">
        <div class="files-search">
          <el-input
            v-model="searchQuery"
            placeholder="搜索文件名..."
            prefix-icon="Search"
            clearable
            @input="handleSearch"
          />
          
          <el-select v-model="statusFilter" placeholder="状态筛选" clearable @change="fetchFiles">
            <el-option label="全部" value="" />
            <el-option label="有效" value="active" />
            <el-option label="已过期" value="expired" />
            <el-option label="已删除" value="deleted" />
          </el-select>
        </div>
        
        <div class="files-actions">
          <el-button type="primary" icon="Upload" @click="$router.push('/upload')">
            上传文件
          </el-button>
          
          <el-button
            type="danger"
            :disabled="selectedFileIds.length === 0"
            @click="handleBatchDelete"
          >
            批量删除 <span v-if="selectedFileIds.length">({{ selectedFileIds.length }})</span>
          </el-button>
          
          <el-button
            type="success"
            :disabled="selectedFileIds.length === 0"
            @click="handleBatchDownload"
          >
            批量下载 <span v-if="selectedFileIds.length">({{ selectedFileIds.length }})</span>
          </el-button>
        </div>
      </div>
    </el-card>
    
    <!-- 文件列表 - 桌面端表格 -->
    <el-card class="desktop-table">
      <el-table
        :data="files"
        stripe
        style="width: 100%"
        @selection-change="handleSelectionChange"
        v-loading="loading"
      >
        <el-table-column type="selection" width="50" />
        
        <el-table-column prop="original_name" label="文件名" min-width="200">
          <template #default="{ row }">
            <div class="file-name-cell">
              <el-icon :size="24" color="#409EFF"><Document /></el-icon>
              <span :class="{ 'file-expired': row.is_expired || row.status === 'deleted' }">
                {{ row.original_name }}
              </span>
              <el-tag v-if="row.is_expired" type="danger" size="small">已过期</el-tag>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="file_size_display" label="大小" width="100" sortable />
        
        <el-table-column label="访问类型" width="100">
          <template #default="{ row }">
            <el-tag :type="getAccessTypeTagType(row.access_type)" size="small">
              {{ getAccessTypeLabel(row.access_type) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="提取码" width="80">
          <template #default="{ row }">
            <span v-if="row.extract_code" style="font-weight: bold; color: #67C23A;">
              {{ row.extract_code }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="download_count" label="下载" width="70" sortable />
        
        <el-table-column label="上传时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.uploaded_at) }}
          </template>
        </el-table-column>
        
        <el-table-column label="过期时间" width="160">
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
      <div class="files-pagination">
        <span class="files-total">共 {{ total }} 个文件</span>
        
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="sizes, prev, pager, next, jumper"
          @size-change="fetchFiles"
          @current-change="fetchFiles"
          small
        />
      </div>
    </el-card>
    
    <!-- 文件列表 - 移动端卡片 -->
    <div class="mobile-cards">
      <div v-if="loading" style="text-align: center; padding: 40px;">
        <el-icon class="is-loading" :size="32"><Loading /></el-icon>
        <p style="color: #909399; margin-top: 8px;">加载中...</p>
      </div>
      
      <div v-else-if="files.length === 0" style="text-align: center; padding: 40px; color: #909399;">
        暂无文件
      </div>
      
      <div v-else>
        <div v-for="file in files" :key="file.id" class="file-card-mobile">
          <div class="file-card-header">
            <div class="file-card-name">
              <el-icon :size="22" color="#409EFF"><Document /></el-icon>
              <span :class="{ 'file-expired': file.is_expired || file.status === 'deleted' }">
                {{ file.original_name }}
              </span>
            </div>
            <el-tag v-if="file.is_expired" type="danger" size="small">已过期</el-tag>
            <el-tag v-else-if="file.status === 'deleted'" type="info" size="small">已删除</el-tag>
          </div>
          
          <div class="file-card-meta">
            <span>{{ file.file_size_display }}</span>
            <span>{{ getAccessTypeLabel(file.access_type) }}</span>
            <span v-if="file.extract_code" style="color: #67C23A;">提取码: {{ file.extract_code }}</span>
            <span>{{ file.download_count }}次下载</span>
          </div>
          
          <div class="file-card-time">
            <span>上传: {{ formatDate(file.uploaded_at) }}</span>
            <span>过期: {{ formatDate(file.expires_at) }}</span>
          </div>
          
          <div class="file-card-actions">
            <el-button size="small" @click="downloadFile(file)">下载</el-button>
            <el-button size="small" @click="previewFile(file)" :disabled="!canPreview(file)">预览</el-button>
            <el-button size="small" type="warning" @click="renewFile(file)" :disabled="file.status === 'deleted'">续期</el-button>
            <el-button size="small" type="danger" @click="deleteFile(file)">删除</el-button>
            <el-button size="small" @click="copyLink(file)">复制链接</el-button>
          </div>
        </div>
        
        <div class="files-pagination">
          <span class="files-total">共 {{ total }} 个文件</span>
          
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :total="total"
            :page-sizes="[10, 20, 50]"
            layout="prev, pager, next"
            @size-change="fetchFiles"
            @current-change="fetchFiles"
            small
          />
        </div>
      </div>
    </div>
    
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
  // 公开文件使用公开下载链接，私有文件使用认证下载链接
  const path = file.access_type === 'public' 
    ? `/api/files/download/public/${file.id}`
    : `/api/files/download/${file.id}`
  const url = `${window.location.origin}${path}`
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

/* 工具栏 */
.files-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.files-search {
  display: flex;
  gap: 10px;
  flex: 1;
  min-width: 200px;
}

.files-search .el-input {
  width: 260px;
}

.files-search .el-select {
  width: 130px;
}

.files-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

/* 文件名单元格 */
.file-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 分页 */
.files-pagination {
  margin-top: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.files-total {
  color: #909399;
  font-size: 13px;
}

/* 移动端卡片视图 */
.mobile-cards {
  display: none;
}

.file-card-mobile {
  background: white;
  border-radius: 8px;
  padding: 14px;
  margin-bottom: 10px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.file-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.file-card-name {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  min-width: 0;
  font-weight: 500;
  font-size: 14px;
}

.file-card-name span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 12px;
  color: #909399;
  margin-bottom: 6px;
}

.file-card-time {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 11px;
  color: #c0c4cc;
  margin-bottom: 10px;
}

.file-card-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding-top: 8px;
  border-top: 1px solid #f0f0f0;
}

/* 响应式 */
@media (max-width: 768px) {
  .desktop-table {
    display: none;
  }
  
  .mobile-cards {
    display: block;
  }
  
  .files-toolbar {
    flex-direction: column;
    align-items: stretch;
  }
  
  .files-search {
    flex-direction: column;
  }
  
  .files-search .el-input {
    width: 100%;
  }
  
  .files-search .el-select {
    width: 100%;
  }
  
  .files-actions {
    justify-content: flex-start;
  }
  
  .files-pagination {
    justify-content: center;
  }
}

@media (min-width: 769px) {
  .mobile-cards {
    display: none !important;
  }
}
</style>
