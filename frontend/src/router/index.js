import { createRouter, createWebHistory } from 'vue-router'
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'

NProgress.configure({ showSpinner: false })

// 路由定义 - 不导入store
const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'Dashboard', component: () => import('@/views/Dashboard.vue') },
      { path: 'files', name: 'Files', component: () => import('@/views/Files.vue') },
      { path: 'upload', name: 'Upload', component: () => import('@/views/Upload.vue') },
      { 
        path: 'download-code', 
        name: 'DownloadCode', 
        component: () => import('@/views/DownloadByCode.vue'),
        meta: { requiresAuth: false }  // 通过提取码下载不需要登录
      },
      { path: 'admin/users', name: 'AdminUsers', component: () => import('@/views/admin/Users.vue'), meta: { requiresAdmin: true } },
      { path: 'admin/files', name: 'AdminFiles', component: () => import('@/views/admin/Files.vue'), meta: { requiresAdmin: true } },
      { path: 'admin/logs/login', name: 'AdminLoginLogs', component: () => import('@/views/admin/LoginLogs.vue'), meta: { requiresAdmin: true } },
      { path: 'admin/logs/operation', name: 'AdminOperationLogs', component: () => import('@/views/admin/OperationLogs.vue'), meta: { requiresAdmin: true } },
      { path: 'admin/system', name: 'AdminSystem', component: () => import('@/views/admin/System.vue'), meta: { requiresAdmin: true } },
      { path: 'profile', name: 'Profile', component: () => import('@/views/Profile.vue') }
    ]
  },
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫 - 使用动态导入避免循环依赖
router.beforeEach(async (to, from, next) => {
  NProgress.start()
  
  // 动态导入 store
  const { useUserStore } = await import('@/stores/user')
  const userStore = useUserStore()
  
  // 检查是否需要认证（download-code 页面不需要）
  const requiresAuth = to.meta.requiresAuth !== false && to.path !== '/download-code'
  
  if (requiresAuth && !userStore.isLoggedIn) {
    next('/login')
  } else if (to.path === '/login' && userStore.isLoggedIn) {
    next('/')
  } else if (to.meta.requiresAdmin && !userStore.isAdmin) {
    next('/')
  } else {
    next()
  }
})

router.afterEach(() => {
  NProgress.done()
})

export default router
