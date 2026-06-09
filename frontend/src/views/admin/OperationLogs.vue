<template>
  <div class="page-container">
    <div class="page-header">
      <h2>操作日志</h2>
      <p>查看系统中的所有操作记录，包括文件上传、下载、删除等</p>
    </div>
    
    <!-- 筛选栏 -->
    <el-card style="margin-bottom: 12px;">
      <div class="log-filters">
        <el-input
          v-model="searchQuery"
          placeholder="搜索用户名..."
          prefix-icon="Search"
          clearable
          @input="handleSearch"
        />
        
        <el-select v-model="operationFilter" placeholder="操作类型" clearable @change="fetchLogs">
          <el-option label="全部" value="" />
          <el-option label="上传" value="upload" />
          <el-option label="下载" value="download" />
          <el-option label="删除" value="delete" />
          <el-option label="续期" value="renew" />
          <el-option label="用户管理" value="create_user" />
          <el-option label="密码重置" value="reset_password" />
        </el-select>
        
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          @change="fetchLogs"
        />
      </div>
    </el-card>
    
    <!-- 日志列表 -->
    <el-card>
      <el-table :data="logs" stripe style="width: 100%;" v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        
        <el-table-column prop="username" label="操作者" min-width="120">
          <template #default="{ row }">
            <span v-if="row.username === 'system'" type="info">系统</span>
            <span v-else-if="row.username === 'anonymous'" type="warning">匿名用户</span>
            <span v-else>{{ row.username }}</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="operation_type" label="操作类型" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ getOperationLabel(row.operation_type) }}</el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="target_type" label="目标类型" width="100">
          <template #default="{ row }">
            <el-tag type="info" size="small">{{ getTargetTypeLabel(row.target_type) }}</el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="详细信息" min-width="250" show-overflow-tooltip>
          <template #default="{ row }">
            {{ formatDetails(row.details) }}
          </template>
        </el-table-column>
        
        <el-table-column prop="ip_address" label="IP地址" width="150" show-overflow-tooltip />
        
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div style="margin-top: 16px; display: flex; justify-content: space-between; align-items: center;">
        <span style="color: #909399;">共 {{ total }} 条记录</span>
        
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="sizes, prev, pager, next, jumper"
          @size-change="fetchLogs"
          @current-change="fetchLogs"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api'

// 状态
const logs = ref([])
const loading = ref(false)
const searchQuery = ref('')
const operationFilter = ref('')
const dateRange = ref(null)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 获取日志列表
async function fetchLogs() {
  loading.value = true
  
  try {
    const params = {
      page: currentPage.value,
      per_page: pageSize.value,
      username: searchQuery.value,
      operation_type: operationFilter.value,
      start_date: dateRange.value?.[0],
      end_date: dateRange.value?.[1]
    }
    
    const res = await api.get('/admin/logs/operation', { params })
    logs.value = res.logs || []
    total.value = res.total || 0
    
  } catch (error) {
    console.error('获取操作日志失败:', error)
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
    fetchLogs()
  }, 500)
}

// 获取操作类型标签
function getOperationLabel(type) {
  const labels = {
    'upload': '上传',
    'download': '下载',
    'download_by_code': '提取码下载',
    'batch_download': '批量下载',
    'delete': '删除',
    'renew': '续期',
    'create_user': '创建用户',
    'update_user': '编辑用户',
    'delete_user': '删除用户',
    'reset_password': '重置密码',
    'change_password': '修改密码',
    'admin_delete_file': '管理员删文件',
    'manual_cleanup': '手动清理',
    'auto_cleanup': '自动清理',
    'check_update': '检查更新',
    'system_update': '系统更新'
  }
  return labels[type] || type
}

// 获取目标类型标签
function getTargetTypeLabel(type) {
  const labels = { file: '文件', user: '用户', system: '系统' }
  return labels[type] || type || '-'
}

// 格式化详细信息
function formatDetails(details) {
  if (!details) return '-'
  
  try {
    const data = JSON.parse(details)
    return Object.entries(data).map(([key, val]) => `${key}: ${val}`).join(', ')
  } catch {
    return details
  }
}

// 格式化日期时间
function formatDateTime(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(() => {
  fetchLogs()
})
</script>

<style scoped>
.log-filters {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}

.log-filters .el-input {
  width: 180px;
}

.log-filters .el-select {
  width: 160px;
}

.log-filters .el-date-editor {
  width: 240px;
}

@media (max-width: 768px) {
  .log-filters {
    flex-direction: column;
  }
  
  .log-filters .el-input {
    width: 100%;
  }
  
  .log-filters .el-select {
    width: 100%;
  }
  
  .log-filters .el-date-editor {
    width: 100%;
  }
}
</style>
