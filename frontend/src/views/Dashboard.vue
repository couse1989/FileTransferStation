<template>
  <div class="page-container">
    <div class="page-header">
      <h2>仪表盘</h2>
      <p>欢迎使用文件中转站，快速了解系统状态</p>
    </div>
    
    <!-- 统计卡片 -->
    <el-row :gutter="20" style="margin-bottom: 24px;">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div class="stat-value">{{ stats.my_files || 0 }}</div>
              <div class="stat-label">我的文件</div>
            </div>
            <el-icon class="stat-icon" color="#409EFF"><Document /></el-icon>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div class="stat-value">{{ formatSize(stats.total_size || 0) }}</div>
              <div class="stat-label">已用空间</div>
            </div>
            <el-icon class="stat-icon" color="#67C23A"><Folder /></el-icon>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div class="stat-value">{{ stats.total_downloads || 0 }}</div>
              <div class="stat-label">下载次数</div>
            </div>
            <el-icon class="stat-icon" color="#E6A23C"><Download /></el-icon>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
              <div class="stat-value">{{ stats.expiring_soon || 0 }}</div>
              <div class="stat-label">即将过期</div>
            </div>
            <el-icon class="stat-icon" color="#F56C6C"><Warning /></el-icon>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 快捷操作 -->
    <el-row :gutter="20" style="margin-bottom: 24px;">
      <el-col :span="12">
        <el-card>
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span>快捷操作</span>
            </div>
          </template>
          
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
            <el-button type="primary" size="large" @click="$router.push('/upload')">
              <el-icon><Upload /></el-icon>
              上传文件
            </el-button>
            
            <el-button type="success" size="large" @click="$router.push('/files')">
              <el-icon><Document /></el-icon>
              管理文件
            </el-button>
            
            <el-button type="warning" size="large" @click="$router.push('/download-code')">
              <el-icon><Key /></el-icon>
              提取码下载
            </el-button>
            
            <el-button type="info" size="large" @click="$router.push('/profile')">
              <el-icon><UserFilled /></el-icon>
              个人中心
            </el-button>
          </div>
        </el-card>
      </el-col>
      
      <!-- 最近上传的文件 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span>最近上传</span>
              <el-button text type="primary" @click="$router.push('/files')">查看全部</el-button>
            </div>
          </template>
          
          <div v-if="recentFiles.length === 0" style="text-align: center; padding: 40px; color: #909399;">
            暂无文件，快去上传吧~
          </div>
          
          <div v-else>
            <div v-for="file in recentFiles" :key="file.id" class="file-item">
              <div class="file-info">
                <div class="file-name">{{ file.original_name }}</div>
                <div class="file-meta">
                  <span>{{ file.file_size_display }}</span>
                  <span>{{ formatDate(file.uploaded_at) }}</span>
                </div>
              </div>
              
              <div style="color: #909399; font-size: 12px;">
                {{ file.download_count }} 次下载
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api'

const stats = ref({})
const recentFiles = ref([])

// 获取统计数据
async function fetchStats() {
  try {
    // 获取我的文件列表（第一页，只取5个）
    const res = await api.get('/files/list', { params: { per_page: 5 } })
    recentFiles.value = res.files || []
    
    // 计算统计信息
    const allFilesRes = await api.get('/files/list', { params: { per_page: 9999 } })
    const allFiles = allFilesRes.files || []
    
    stats.value = {
      my_files: allFiles.length,
      total_size: allFiles.reduce((sum, f) => sum + (f.file_size || 0), 0),
      total_downloads: allFiles.reduce((sum, f) => sum + (f.download_count || 0), 0),
      expiring_soon: allFiles.filter(f => {
        if (!f.expires_at) return false
        const expireDate = new Date(f.expires_at)
        const now = new Date()
        const diff = (expireDate - now) / (1000 * 60 * 60)
        return diff > 0 && diff <= 24
      }).length
    }
  } catch (error) {
    console.error('获取统计数据失败:', error)
  }
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

// 格式化日期
function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

onMounted(() => {
  fetchStats()
})
</script>
