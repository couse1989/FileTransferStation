<template>
  <div class="page-container">
    <div class="page-header">
      <h2>文件管理</h2>
      <p>管理系统中的所有文件，可强制删除</p>
    </div>
    
    <!-- 操作栏 -->
    <el-card style="margin-bottom: 20px;">
      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
        <div style="display: flex; gap: 12px; flex: 1;">
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
          
          <el-select v-model="uploaderFilter" placeholder="上传者筛选" clearable filterable style="width: 180px;" @change="fetchFiles">
            <el-option
              v-for="user in userList"
              :key="user.id"
              :label="user.username"
              :value="user.id"
            />
          </el-select>
        </div>
        
        <el-button type="danger" icon="Delete" @click="showCleanupDialog">
          清理过期文件
        </el-button>
      </div>
    </el-card>
    
    <!-- 文件列表 -->
    <el-card>
      <el-table :data="files" stripe style="width: 100%" v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        
        <el-table-column prop="original_name" label="文件名" min-width="250">
          <template #default="{ row }">
            <span :class="{ 'text-danger': row.status === 'deleted' }">{{ row.original_name }}</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="file_size_display" label="大小" width="100" sortable />
        
        <el-table-column label="上传者" width="120">
          <template #default="{ row }">
            {{ row.uploader_name || '未知' }}
          </template>
        </el-table-column>
        
        <el-table-column label="访问类型" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ getAccessTypeLabel(row.access_type) }}</el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="download_count" label="下载次数" width="90" />
        
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">{{ getStatusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="上传时间" width="170">
          <template #default="{ row }">{{ formatDate(row.uploaded_at) }}</template>
        </el-table-column>
        
        <el-table-column label="过期时间" width="170">
          <template #default="{ row }">{{ formatDate(row.expires_at) || '永不过期' }}</template>
        </el-table-column>
        
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-popconfirm title="确定要删除这个文件吗？" @confirm="deleteFile(row)">
              <template #reference>
                <el-button text type="danger" size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div style="margin-top: 16px; display: flex; justify-content: space-between; align-items: center;">
        <span style="color: #909399;">共 {{ total }} 个文件</span>
        
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
    
    <!-- 清理对话框 -->
    <el-dialog v-model="cleanupDialogVisible" title="清理过期文件" width="400px">
      <p>这将删除所有已过期的文件，释放存储空间。确定要继续吗？</p>
      
      <template #footer>
        <el-button @click="cleanupDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="handleCleanup" :loading="cleaningUp">确认清理</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

// 状态
const files = ref([])
const loading = ref(false)
const searchQuery = ref('')
const statusFilter = ref('')
const uploaderFilter = ref(null)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const userList = ref([])

// 清理相关
const cleanupDialogVisible = ref(false)
const cleaningUp = ref(false)

// 获取文件列表
async function fetchFiles() {
  loading.value = true
  
  try {
    const params = {
      page: currentPage.value,
      per_page: pageSize.value,
      search: searchQuery.value,
      status: statusFilter.value,
      uploader_id: uploaderFilter.value
    }
    
    const res = await api.get('/admin/files', { params })
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

// 获取访问类型标签
function getAccessTypeLabel(type) {
  const labels = { public: '公开', code: '提取码', private: '指定用户' }
  return labels[type] || type
}

// 获取状态标签类型
function getStatusType(status) {
  const types = { active: '', expired: 'warning', deleted: 'danger' }
  return types[status] || ''
}

// 获取状态标签文本
function getStatusLabel(status) {
  const labels = { active: '有效', expired: '已过期', deleted: '已删除' }
  return labels[status] || status
}

// 格式化日期
function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

// 显示清理对话框
function showCleanupDialog() {
  cleanupDialogVisible.value = true
}

// 执行清理
async function handleCleanup() {
  cleaningUp.value = true
  
  try {
    const res = await api.post('/admin/cleanup')
    
    ElMessage.success(res.message || '清理完成')
    cleanupDialogVisible.value = false
    fetchFiles()
    
  } catch (error) {
    console.error('清理失败:', error)
  } finally {
    cleaningUp.value = false
  }
}

// 删除文件
async function deleteFile(file) {
  try {
    await api.delete(`/admin/files/${file.id}`)
    ElMessage.success(`文件 "${file.original_name}" 已删除`)
    fetchFiles()
    
  } catch (error) {
    console.error('删除失败:', error)
  }
}

onMounted(async () => {
  // 获取文件列表和用户列表（并行）
  Promise.all([
    fetchFiles(),
    api.get('/admin/users').then(res => {
      userList.value = res.users || []
    }).catch(() => {})
  ])
})
</script>

<style scoped>
.text-danger {
  color: #f56c6c;
  text-decoration: line-through;
}
</style>
