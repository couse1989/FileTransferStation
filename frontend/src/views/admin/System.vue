<template>
  <div class="page-container">
    <div class="page-header">
      <h2>系统设置</h2>
      <p>查看系统状态、检查更新、管理存储空间</p>
    </div>
    
    <!-- 系统统计 -->
    <el-row :gutter="20" style="margin-bottom: 24px;">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ stats.total_users || 0 }}</div>
          <div class="stat-label">用户总数</div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ stats.active_files || 0 }}</div>
          <div class="stat-label">有效文件</div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ formatSize(stats.total_storage_used || 0) }}</div>
          <div class="stat-label">已用存储</div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value" style="color: #67C23A;">{{ stats.today_uploads || 0 }}</div>
          <div class="stat-label">今日上传</div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 详细统计和操作 -->
    <el-row :gutter="20">
      <el-col :span="16">
        <el-card>
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span>详细统计</span>
              <el-button text type="primary" @click="fetchStats">刷新</el-button>
            </div>
          </template>
          
          <el-descriptions :column="3" border>
            <el-descriptions-item label="活跃用户">{{ stats.active_users || 0 }} 人</el-descriptions-item>
            <el-descriptions-item label="管理员数量">{{ stats.admin_users || 0 }} 人</el-descriptions-item>
            <el-descriptions-item label="过期文件">{{ stats.expired_files || 0 }} 个</el-descriptions-item>
            
            <el-descriptions-item label="已删除文件">{{ stats.deleted_files || 0 }} 个</el-descriptions-item>
            <el-descriptions-item label="今日下载">{{ stats.today_downloads || 0 }} 次</el-descriptions-item>
            <el-descriptions-item label="今日登录成功">{{ stats.today_logins || 0 }} 次</el-descriptions-item>
            
            <el-descriptions-item label="今日登录失败">{{ stats.today_failed_logins || 0 }} 次</el-descriptions-item>
          </el-descriptions>
        </el-card>
        
        <!-- 存储信息 -->
        <el-card style="margin-top: 20px;">
          <template #header>存储使用情况</template>
          
          <div v-if="stats.storage_info">
            <p><strong>存储目录：</strong>{{ stats.storage_info.upload_folder }}</p>
            <p><strong>目录状态：</strong>
              <el-tag :type="stats.storage_info.exists ? 'success' : 'danger'" size="small">
                {{ stats.storage_info.exists ? '正常' : '不存在' }}
              </el-tag>
            </p>
            <p v-if="stats.storage_info.used_bytes !== undefined">
              <strong>已用空间：</strong>{{ formatSize(stats.storage_info.used_bytes) }}
            </p>
          </div>
          
          <el-progress
            v-if="storageUsagePercent > 0"
            :percentage="storageUsagePercent"
            :status="storageStatus"
            style="margin-top: 16px;"
          />
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <!-- 版本信息 -->
        <el-card style="margin-bottom: 20px;">
          <template #header>
            <span>版本与更新</span>
          </template>
          
          <el-descriptions :column="1" border>
            <el-descriptions-item label="当前版本">{{ versionInfo.current_version }}</el-descriptions-item>
            <el-descriptions-item label="最新版本">
              {{ versionInfo.latest_version || '未知' }}
            </el-descriptions-item>
            <el-descriptions-item label="更新状态">
              <el-tag
                v-if="versionInfo.update_available"
                type="warning"
                size="small"
              >
                有新版本
              </el-tag>
              <el-tag
                v-else-if="versionInfo.latest_version"
                type="success"
                size="small"
              >
                已是最新
              </el-tag>
              <span v-else>-</span>
            </el-descriptions-item>
          </el-descriptions>
          
          <div style="margin-top: 16px; display: flex; gap: 12px;">
            <el-button type="primary" @click="checkUpdate" :loading="checking">
              检查更新
            </el-button>
            
            <el-button
              type="success"
              @click="performUpdate"
              :disabled="!versionInfo.update_available"
              :loading="updating"
            >
              立即更新
            </el-button>
          </div>
        </el-card>
        
        <!-- 快捷操作 -->
        <el-card>
          <template #header>快捷操作</template>
          
          <div style="display: flex; flex-direction: column; gap: 12px;">
            <el-button icon="Delete" @click="$router.push('/admin/files')">
              文件管理
            </el-button>
            
            <el-button icon="User" @click="$router.push('/admin/users')">
              用户管理
            </el-button>
            
            <el-button
              type="danger"
              icon="DeleteFilled"
              @click="showCleanupDialog"
            >
              清理过期文件
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
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
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'

// 统计数据
const stats = ref({})
const versionInfo = ref({})
const checking = ref(false)
const updating = ref(false)

// 清理相关
const cleanupDialogVisible = ref(false)
const cleaningUp = ref(false)

// 存储使用率（假设总容量100GB）
const MAX_STORAGE = 100 * 1024 * 1024 * 1024 // 100GB

const storageUsagePercent = computed(() => {
  const used = stats.value.total_storage_used || 0
  return Math.round((used / MAX_STORAGE) * 100 * 10) / 10
})

const storageStatus = computed(() => {
  if (storageUsagePercent.value >= 90) return 'exception'
  if (storageUsagePercent.value >= 70) return 'warning'
  return ''
})

// 获取统计数据
async function fetchStats() {
  try {
    const res = await api.get('/admin/stats')
    stats.value = res
  } catch (error) {
    console.error('获取统计数据失败:', error)
  }
}

// 获取版本信息
async function fetchVersionInfo() {
  try {
    const res = await api.get('/system/version')
    versionInfo.value = res
  } catch (error) {
    console.error('获取版本信息失败:', error)
  }
}

// 检查更新
async function checkUpdate() {
  checking.value = true
  
  try {
    const res = await api.post('/system/check-update')
    versionInfo.value = res
    
    if (res.update_available) {
      ElMessage.info(`发现新版本: ${res.latest_version}`)
    } else {
      ElMessage.success(res.message || '当前已是最新版本')
    }
    
  } catch (error) {
    ElMessage.error('检查更新失败')
  } finally {
    checking.value = false
  }
}

// 执行更新
async function performUpdate() {
  try {
    await ElMessageBox.confirm(
      '系统即将从GitHub拉取最新代码并重启服务，确定要继续吗？',
      '确认更新',
      { confirmButtonText: '确定更新', cancelButtonText: '取消', type: 'warning' }
    )
    
    updating.value = true
    
    const res = await api.post('/system/update')
    
    ElMessage.success(res.message || '更新成功，正在重启...')
    
    // 5秒后提示用户刷新页面（因为服务器会重启）
    setTimeout(() => {
      ElMessageBox.alert(
        '系统已完成更新并重启完成，请点击确定刷新页面。',
        '更新完成',
        { confirmButtonText: '刷新页面' }
      ).then(() => {
        window.location.reload()
      })
    }, 5000)
    
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.error || '更新失败')
    }
  } finally {
    updating.value = false
  }
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
    
    ElMessage.success(`${res.message}，释放空间 ${res.freed_space}`)
    cleanupDialogVisible.value = false
    fetchStats()
    
  } catch (error) {
    ElMessage.error('清理失败')
  } finally {
    cleaningUp.value = false
  }
}

// 格式化大小
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

onMounted(() => {
  Promise.all([
    fetchStats(),
    fetchVersionInfo()
  ])
})
</script>

<style scoped>
.stat-card .stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #409EFF;
  margin-bottom: 8px;
}

.stat-card .stat-label {
  font-size: 14px;
  color: #909399;
}
</style>
