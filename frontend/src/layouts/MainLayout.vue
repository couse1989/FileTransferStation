<template>
  <el-container style="min-height: 100vh">
    <!-- 侧边栏 -->
    <el-aside width="220px" style="background-color: #304156;">
      <div class="logo-container" @click="$router.push('/')">
        <el-icon :size="28"><FolderOpened /></el-icon>
        <span class="logo-text">文件中转站</span>
      </div>
      
      <el-menu
        :default-active="currentRoute"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
        router
      >
        <el-menu-item index="/">
          <el-icon><Odometer /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        
        <el-menu-item index="/upload">
          <el-icon><Upload /></el-icon>
          <span>上传文件</span>
        </el-menu-item>
        
        <el-menu-item index="/files">
          <el-icon><Document /></el-icon>
          <span>我的文件</span>
        </el-menu-item>
        
        <el-menu-item index="/download-code">
          <el-icon><Download /></el-icon>
          <span>提取码下载</span>
        </el-menu-item>
        
        <!-- 管理员菜单（仅管理员可见） -->
        <template v-if="userStore.isAdmin">
          <el-sub-menu index="admin">
            <template #title>
              <el-icon><Setting /></el-icon>
              <span>系统管理</span>
            </template>
            
            <el-menu-item index="/admin/users">
              <el-icon><User /></el-icon>
              用户管理
            </el-menu-item>
            
            <el-menu-item index="/admin/files">
              <el-icon><Files /></el-icon>
              文件管理
            </el-menu-item>
            
            <el-sub-menu index="admin-logs">
              <template #title>日志管理</template>
              
              <el-menu-item index="/admin/logs/login">
                登录日志
              </el-menu-item>
              
              <el-menu-item index="/admin/logs/operation">
                操作日志
              </el-menu-item>
            </el-sub-menu>
            
            <el-menu-item index="/admin/system">
              <el-icon><Monitor /></el-icon>
              系统设置
            </el-menu-item>
          </el-sub-menu>
        </template>
        
        <div style="flex: 1;"></div>
        
        <el-menu-item index="/profile">
          <el-icon><UserFilled /></el-icon>
          <span>个人中心</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    
    <!-- 主内容区 -->
    <el-container>
      <el-header height="60px" style="background: white; border-bottom: 1px solid #e6e6e6; display: flex; align-items: center; justify-content: space-between; padding: 0 20px;">
        <div style="font-size: 18px; font-weight: 500; color: #303133;">
          {{ pageTitle }}
        </div>
        
        <div style="display: flex; align-items: center; gap: 16px;">
          <el-dropdown trigger="click" @command="handleCommand">
            <span style="cursor: pointer; display: flex; align-items: center; gap: 8px;">
              <el-avatar :size="32" icon="UserFilled" />
              <span>{{ userStore.username }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人中心</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      
      <el-main style="background-color: #f5f7fa; padding: 20px;">
        <router-view />
      </el-main>
      
      <el-footer height="40px" style="text-align: center; color: #909399; font-size: 12px; line-height: 40px; border-top: 1px solid #e6e6e6;">
        文件中转站 v1.0 | 最大支持10GB文件上传
      </el-footer>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessageBox, ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

// 当前路由路径
const currentRoute = computed(() => route.path)

// 页面标题
const pageTitle = computed(() => {
  const titles = {
    '/': '仪表盘',
    '/upload': '上传文件',
    '/files': '我的文件',
    '/download-code': '提取码下载',
    '/profile': '个人中心',
    '/admin/users': '用户管理',
    '/admin/files': '文件管理',
    '/admin/logs/login': '登录日志',
    '/admin/logs/operation': '操作日志',
    '/admin/system': '系统设置'
  }
  return titles[route.path] || '文件中转站'
})

// 处理下拉菜单命令
function handleCommand(command) {
  if (command === 'logout') {
    ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }).then(() => {
      userStore.logout()
      router.push('/login')
      ElMessage.success('已退出登录')
    }).catch(() => {})
  } else if (command === 'profile') {
    router.push('/profile')
  }
}
</script>

<style scoped>
.logo-container {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 20px;
  color: white;
  cursor: pointer;
  
  &:hover {
    background-color: rgba(255, 255, 255, 0.05);
  }
}

.logo-text {
  font-size: 18px;
  font-weight: bold;
}
</style>
