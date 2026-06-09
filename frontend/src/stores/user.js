import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const refreshToken = ref(localStorage.getItem('refresh_token') || '')
  const userInfo = ref(null)
  
  // 初始化userInfo
  try {
    const stored = localStorage.getItem('userInfo')
    if (stored && stored !== 'null' && stored !== 'undefined') {
      userInfo.value = JSON.parse(stored)
    }
  } catch (e) {
    userInfo.value = null
  }
  
  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => userInfo.value?.is_admin === true)
  const username = computed(() => userInfo.value?.username || '')
  
  async function login(credentials) {
    const res = await api.post('/auth/login', credentials)
    
    token.value = res.access_token
    refreshToken.value = res.refresh_token
    userInfo.value = res.user
    
    localStorage.setItem('token', res.access_token)
    localStorage.setItem('refresh_token', res.refresh_token)
    localStorage.setItem('userInfo', JSON.stringify(res.user))
    
    return res
  }
  
  function logout() {
    token.value = ''
    refreshToken.value = ''
    userInfo.value = null
    
    localStorage.removeItem('token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('userInfo')
  }
  
  async function fetchUserInfo() {
    try {
      const res = await api.get('/auth/me')
      userInfo.value = res
      localStorage.setItem('userInfo', JSON.stringify(res))
      return res
    } catch (error) {
      logout()
      throw error
    }
  }
  
  async function refreshAccessToken() {
    try {
      if (!refreshToken.value) return false
      
      const res = await api.post('/auth/refresh', {}, {
        headers: { Authorization: `Bearer ${refreshToken.value}` }
      })
      
      token.value = res.access_token
      localStorage.setItem('token', res.access_token)
      
      return true
    } catch (error) {
      return false
    }
  }
  
  async function changePassword(data) {
    return await api.post('/auth/change-password', data)
  }
  
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
