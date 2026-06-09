import axios from 'axios'
import { ElMessage } from 'element-plus'

// 创建axios实例
const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    // 直接从localStorage读取token，不依赖store
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    // 文件上传不设置Content-Type
    if (config.data instanceof FormData) {
      delete config.headers['Content-Type']
    }
    
    return config
  },
  error => Promise.reject(error)
)

// 响应拦截器
api.interceptors.response.use(
  response => response.data,
  error => {
    if (error.response) {
      const { status, data } = error.response
      
      switch (status) {
        case 401:
          ElMessage.error(data?.error || '登录已过期，请重新登录')
          // 清除本地存储并跳转
          localStorage.removeItem('token')
          localStorage.removeItem('refresh_token')
          localStorage.removeItem('userInfo')
          window.location.href = '/login'
          break
        case 403:
          ElMessage.error(data?.error || '没有权限')
          break
        case 404:
          ElMessage.error(data?.error || '资源不存在')
          break
        case 413:
          ElMessage.error('文件过大')
          break
        default:
          ElMessage.error(data?.error || `请求失败 (${status})`)
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
