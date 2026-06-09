import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'
import { useUserStore } from '@/stores/user'

// 创建axios实例
const api = axios.create({
  baseURL: '/api',
  timeout: 30000, // 30秒超时（大文件上传可能需要更长时间）
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器 - 添加Token
api.interceptors.request.use(
  config => {
    const userStore = useUserStore()
    if (userStore.token) {
      config.headers.Authorization = `Bearer ${userStore.token}`
    }
    
    // 如果是文件上传，不要设置Content-Type，让浏览器自动设置
    if (config.data instanceof FormData) {
      delete config.headers['Content-Type']
    }
    
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器 - 统一错误处理
api.interceptors.response.use(
  response => {
    const res = response.data
    
    // 某些接口直接返回数据
    return res
  },
  error => {
    const userStore = useUserStore()
    
    if (error.response) {
      const { status, data } = error.response
      
      switch (status) {
        case 401:
          // Token过期或无效
          ElMessage.error(data.error || '登录已过期，请重新登录')
          userStore.logout()
          router.push('/login')
          break
        case 403:
          ElMessage.error(data.error || '没有权限')
          break
        case 404:
          ElMessage.error(data.error || '资源不存在')
          break
        case 413:
          ElMessage.error('文件过大')
          break
        default:
          ElMessage.error(data.error || `请求失败 (${status})`)
      }
    } else if (error.code === 'ECONNABORTED') {
      ElMessage.error('请求超时，请稍后重试')
    } else {
      ElMessage.error('网络错误，请检查网络连接')
    }
    
    return Promise.reject(error)
  }
)

export default api
