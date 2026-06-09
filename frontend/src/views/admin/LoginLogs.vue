<template>
  <div class="page-container">
    <div class="page-header">
      <h2>登录日志</h2>
      <p>查看所有用户的登录记录，包括成功和失败的尝试</p>
    </div>
    
    <!-- 筛选栏 -->
    <el-card style="margin-bottom: 20px;">
      <div style="display: flex; gap: 12px; flex-wrap: wrap; align-items: center;">
        <el-input
          v-model="searchQuery"
          placeholder="搜索用户名..."
          prefix-icon="Search"
          clearable
          style="width: 200px;"
          @input="handleSearch"
        />
        
        <el-select v-model="successFilter" placeholder="结果筛选" clearable style="width: 140px;" @change="fetchLogs">
          <el-option label="全部" value="" />
          <el-option label="成功" value="true" />
          <el-option label="失败" value="false" />
        </el-select>
        
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          style="width: 260px;"
          @change="fetchLogs"
        />
      </div>
    </el-card>
    
    <!-- 日志列表 -->
    <el-card>
      <el-table :data="logs" stripe style="width: 100%;" v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        
        <el-table-column prop="username" label="用户名" min-width="120">
          <template #default="{ row }">
            <span style="font-weight: 500;">{{ row.username }}</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="ip_address" label="IP地址" width="150">
          <template #default="{ row }">
            <code style="background: #f5f7fa; padding: 2px 6px; border-radius: 3px;">{{ row.ip_address }}</code>
          </template>
        </el-table-column>
        
        <el-table-column label="结果" width="100">
          <template #default="{ row }">
            <el-tag :type="row.success ? 'success' : 'danger'" size="small">
              {{ row.success ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="失败原因" width="130">
          <template #default="{ row }">
            <span v-if="!row.success && row.fail_reason">{{ getFailReasonLabel(row.fail_reason) }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="user_agent" label="浏览器信息" min-width="200" show-overflow-tooltip />
        
        <el-table-column label="登录时间" width="170">
          <template #default="{ row }">{{ formatDateTime(row.login_time) }}</template>
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
const successFilter = ref('')
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
      success: successFilter.value,
      start_date: dateRange.value?.[0],
      end_date: dateRange.value?.[1]
    }
    
    const res = await api.get('/admin/logs/login', { params })
    logs.value = res.logs || []
    total.value = res.total || 0
    
  } catch (error) {
    console.error('获取登录日志失败:', error)
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

// 获取失败原因标签
function getFailReasonLabel(reason) {
  const labels = {
    'invalid_password': '密码错误',
    'account_disabled': '账户禁用',
    'account_locked': '账户锁定',
    'user_not_found': '用户不存在',
    'captcha_error': '验证码错误'
  }
  return labels[reason] || reason
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
