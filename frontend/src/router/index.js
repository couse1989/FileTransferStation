import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'

NProgress.configure({ showSpinner: false })

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
      {
        path: '',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue')
      },
      {
        path: 'files',
        name: 'Files',
        component: () => import('@/views/Files.vue')
      },
      {
        path: 'upload',
        name: 'Upload',
        component: () => import('@/views/Upload.vue')
      },
      {
        path: 'download-code',
        name: 'DownloadCode',
        component: () => import('@/views/DownloadByCode.vue')
      },
      // 管理员路由
      {
        path: 'admin/users',
        name: 'AdminUsers',
        component: () => import('@/views/admin/Users.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'admin/files',
        name: 'AdminFiles',
        component: () => import('@/views/admin/Files.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'admin/logs/login',
        name: 'AdminLoginLogs',
        component: () => import('@/views/admin/LoginLogs.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'admin/logs/operation',
        name: 'AdminOperationLogs',
        component: () => import('@/views/admin/OperationLogs.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'admin/system',
        name: 'AdminSystem',
        component: () => import('@/views/admin/System.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('@/views/Profile.vue')
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach(async (to, from, next) => {
  NProgress.start()
  
  const userStore = useUserStore()
  
  if (to.meta.requiresAuth !== false && !userStore.isLoggedIn) {
    next('/login')
  } else if (to.path === '/login' && userStore.isLoggedIn) {
    next('/')
  } else if (to.meta.requiresAdmin && !userStore.isAdmin) {
    // 非管理员访问管理页面
    next('/')
  } else {
    next()
  }
})

router.afterEach(() => {
  NProgress.done()
})

export default router
