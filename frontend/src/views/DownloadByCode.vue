<template>
  <div class="page-container">
    <div class="page-header">
      <h2>提取码下载</h2>
      <p>输入提取码即可下载文件，无需登录</p>
    </div>
    
    <el-card style="max-width: 600px; margin: 0 auto;">
      <div style="text-align: center; padding: 40px 20px;">
        <el-icon :size="80" color="#409EFF" style="margin-bottom: 24px;"><Key /></el-icon>
        
        <h3 style="margin-bottom: 8px; color: #303133;">输入提取码下载文件</h3>
        <p style="color: #909399; margin-bottom: 32px; font-size: 14px;">
          请向文件上传者索取4位提取码
        </p>
        
        <!-- 提取码输入 -->
        <div style="display: flex; justify-content: center; gap: 12px; margin-bottom: 32px;">
          <div
            v-for="(char, index) in codeChars"
            :key="index"
            class="code-input"
            :class="{ 'is-filled': char, 'is-focused': focusedIndex === index }"
            @click="focusInput(index)"
          >
            {{ char }}
          </div>
          
          <input
            ref="codeInputRef"
            v-model="extractCode"
            maxlength="4"
            class="hidden-input"
            @input="handleInput"
            @keydown="handleKeydown"
            @focus="focusedIndex = extractCode.length"
            @blur="focusedIndex = -1"
          />
        </div>
        
        <!-- 操作按钮 -->
        <div style="display: flex; justify-content: center; gap: 16px;">
          <el-button type="primary" size="large" @click="handleDownload" :loading="downloading">
            <el-icon><Download /></el-icon>
            下载文件
          </el-button>
          
          <el-button size="large" @click="clearCode">清空</el-button>
        </div>
        
        <!-- 错误提示 -->
        <div v-if="errorMessage" style="margin-top: 20px; color: #f56c6c; text-align: center;">
          {{ errorMessage }}
        </div>
      </div>
      
      <!-- 文件信息（找到后显示） -->
      <div v-if="fileInfo && !errorMessage" style="margin-top: 24px; padding-top: 24px; border-top: 1px solid #ebeef5;">
        <h4 style="margin-bottom: 16px; color: #303133;">文件信息</h4>
        
        <el-descriptions :column="1" border>
          <el-descriptions-item label="文件名">{{ fileInfo.original_name }}</el-descriptions-item>
          <el-descriptions-item label="文件大小">{{ formatSize(fileInfo.file_size) }}</el-descriptions-item>
          <el-descriptions-item label="上传者">{{ fileInfo.uploader_name || '未知' }}</el-descriptions-item>
          <el-descriptions-item label="上传时间">{{ formatDate(fileInfo.uploaded_at) }}</el-descriptions-item>
          <el-descriptions-item label="过期时间">{{ formatDate(fileInfo.expires_at) }}</el-descriptions-item>
          <el-descriptions-item label="已下载次数">{{ fileInfo.download_count }} 次</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-card>
    
    <!-- 使用说明 -->
    <el-card style="max-width: 600px; margin: 24px auto;">
      <template #header>
        <span>使用说明</span>
      </template>
      
      <el-steps :active="0" direction="vertical" simple style="width: 100%;">
        <el-step title="获取提取码" description="从文件分享者处获取4位字母数字混合的提取码" />
        <el-step title="输入提取码" description="在上方输入框中输入提取码" />
        <el-step title="查看文件信息" description="系统会显示文件的详细信息供您确认" />
        <el-step title="点击下载" description="确认无误后点击下载按钮开始下载" />
      </el-steps>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

const codeInputRef = ref(null)
const extractCode = ref('')
const focusedIndex = ref(-1)
const downloading = ref(false)
const errorMessage = ref('')
const fileInfo = ref(null)

// 提取码字符数组（用于显示）
const codeChars = computed(() => {
  return extractCode.value.split('').concat(['', '', '', '']).slice(0, 4)
})

// 聚焦到指定位置
function focusInput(index) {
  codeInputRef.value?.focus()
}

// 处理输入
function handleInput() {
  // 自动转大写
  extractCode.value = extractCode.value.toUpperCase().replace(/[^A-Z0-9]/g, '')
  
  if (extractCode.value.length >= 4) {
    // 输入满4位自动查询
    queryFile()
  }
}

// 处理键盘事件
function handleKeydown(e) {
  // 退格键处理
  if (e.key === 'Backspace' && !extractCode.value) {
    // 已经为空，不处理
    return
  }
}

// 清空
function clearCode() {
  extractCode.value = ''
  errorMessage.value = ''
  fileInfo.value = null
  codeInputRef.value?.focus()
}

// 查询文件
async function queryFile() {
  if (extractCode.value.length !== 4) {
    ElMessage.warning('请输入完整的4位提取码')
    return
  }
  
  downloading.value = true
  errorMessage.value = ''
  fileInfo.value = null
  
  try {
    // 先尝试获取文件信息（通过API模拟）
    const response = await fetch(`/api/files/code/${extractCode.value}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    })
    
    if (!response.ok) {
      const data = await response.json()
      throw new Error(data.error || '查询失败')
    }
    
    fileInfo.value = await response.json()
    
  } catch (error) {
    errorMessage.value = error.message || '未找到对应的文件'
    console.error('查询失败:', error)
  } finally {
    downloading.value = false
  }
}

// 下载文件
async function handleDownload() {
  if (extractCode.value.length !== 4) {
    ElMessage.warning('请输入完整的4位提取码')
    return
  }
  
  downloading.value = true
  
  try {
    // 直接触发下载（通过隐藏的a标签或window.open）
    window.location.href = `/api/files/download/code/${extractCode.value}`
    
  } catch (error) {
    ElMessage.error('下载失败')
    console.error('下载失败:', error)
  } finally {
    downloading.value = false
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
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(() => {
  nextTick(() => {
    codeInputRef.value?.focus()
  })
})
</script>

<style scoped>
.code-input {
  width: 60px;
  height: 60px;
  border: 2px solid #dcdfe6;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  font-weight: bold;
  color: #303133;
  cursor: text;
  transition: all 0.2s;
  
  &.is-filled {
    border-color: #409EFF;
    background-color: #ecf5ff;
  }
  
  &.is-focused {
    border-color: #409EFF;
    box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
  }
}

.hidden-input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}
</style>
