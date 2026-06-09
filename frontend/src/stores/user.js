import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

// 延迟导入api避免循环依赖
let api = null
function getApi() {
  if (!api) {
    api = require('@/api').default
  }
  return api
}

export const useUserStore = defineStore('user', () => {
  // 状态
  const token = ref(localStorage.getItem('token') || '')
  const refreshToken = ref(localStorage.getItem('refresh_token') || '')
  const userInfo = ref(JSON.parse(localStorage.getItem('userInfo') || 'null'))
  
  // 计算属性
  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => userInfo.value?.is_admin || false)
  const username = computed(() => userInfo.value?.username || '')
  
  // 登录
  async function login(credentials) {
    try {
      const apiInstance = getApi()
      const res = await apiInstance.post('/auth/login', credentials)
      
      token.value = res.access_token
      refreshToken.value = res.refresh_token
      userInfo.value = res.user
      
      localStorage.setItem('token', res.access_token)
      localStorage.setItem('refresh_token', res.refresh_token)
      localStorage.setItem('userInfo', JSON.stringify(res.user))
      
      return res
    } catch (error) {
      throw error
    }
  }
  
  // 登出
  function logout() {
    token.value = ''
    refreshToken.value = ''
    userInfo.value = null
    
    localStorage.removeItem('token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('userInfo')
  }
  
  // 获取用户信息
  async function fetchUserInfo() {
    try {
      const apiInstance = getApi()
      const res = await apiInstance.get('/auth/me')
      userInfo.value = res
      localStorage.setItem('userInfo', JSON.stringify(res))
      return res
    } catch (error) {
      logout()
      throw error
    }
  }
  
  // 刷新Token
  async function refreshAccessToken() {
    try {
      if (!refreshToken.value) return false
      
      const apiInstance = getApi()
      const res = await apiInstance.post('/auth/refresh', {}, {
        headers: { Authorization: `Bearer ${refreshToken.value}` }
      })
      
      token.value = res.access_token
      localStorage.setItem('token', res.access_token)
      
      return true
    } catch (error) {
      return false
    }
  }
  
  // 修改密码
  async function changePassword(data) {
    const apiInstance = getApi()
    return await apiInstance.post('/auth/change-password', data)
  }
  
  // 恢复会话（页面刷新时）
  function restoreSession() {
    if (token.value && !userInfo.value) {
      fetchUserInfo()
    }
  }
  
  return {
    token,
    refreshToken,
    userInfo,
    isLoggedIn,
    isAdmin,
    username,
    login,
    logout,
    fetchUserInfo,
    refreshAccessToken,
    changePassword,
    restoreSession
  }
})
