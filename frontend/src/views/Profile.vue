<template>
  <div class="page-container">
    <div class="page-header">
      <h2>个人中心</h2>
      <p>管理您的账户信息和密码</p>
    </div>
    
    <el-row :gutter="20">
      <!-- 用户信息 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>基本信息</span>
          </template>
          
          <el-descriptions :column="1" border>
            <el-descriptions-item label="用户名">{{ userStore.username }}</el-descriptions-item>
            <el-descriptions-item label="角色">
              <el-tag v-if="userStore.isAdmin" type="danger">管理员</el-tag>
              <el-tag v-else>普通用户</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="注册时间">
              {{ formatDateTime(userStore.userInfo?.created_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="最后登录">
              {{ formatDateTime(userStore.userInfo?.last_login) || '首次登录' }}
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
      
      <!-- 修改密码 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>修改密码</span>
          </template>
          
          <el-form
            ref="passwordFormRef"
            :model="passwordForm"
            :rules="passwordRules"
            label-width="100px"
            style="max-width: 400px;"
          >
            <el-form-item label="当前密码" prop="old_password">
              <el-input
                v-model="passwordForm.old_password"
                type="password"
                show-password
                placeholder="请输入当前密码"
              />
            </el-form-item>
            
            <el-form-item label="新密码" prop="new_password">
              <el-input
                v-model="passwordForm.new_password"
                type="password"
                show-password
                placeholder="请输入新密码（至少6位）"
              />
            </el-form-item>
            
            <el-form-item label="确认新密码" prop="confirm_password">
              <el-input
                v-model="passwordForm.confirm_password"
                type="password"
                show-password
                placeholder="再次输入新密码"
              />
            </el-form-item>
            
            <el-form-item>
              <el-button type="primary" @click="handleChangePassword" :loading="changingPassword">
                修改密码
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useUserStore } from '@/stores/user'
import api from '@/api'
import { ElMessage } from 'element-plus'

const userStore = useUserStore()

const passwordFormRef = ref(null)
const changingPassword = ref(false)

const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

// 密码验证规则
const validateConfirmPassword = (rule, value, callback) => {
  if (value !== passwordForm.new_password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const passwordRules = {
  old_password: [
    { required: true, message: '请输入当前密码', trigger: 'blur' }
  ],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能小于6位', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

// 修改密码
async function handleChangePassword() {
  if (!passwordFormRef.value) return
  
  try {
    // Element Plus 2.x 使用 Promise 形式的 validate
    await passwordFormRef.value.validate()
    
    changingPassword.value = true
    
    try {
      await api.post('/auth/change-password', {
        old_password: passwordForm.old_password,
        new_password: passwordForm.new_password
      })
      
      ElMessage.success('密码修改成功，请重新登录')
      
      // 清空表单
      passwordForm.old_password = ''
      passwordForm.new_password = ''
      passwordForm.confirm_password = ''
      
      // 登出并跳转到登录页
      setTimeout(() => {
        userStore.logout()
        window.location.href = '/login'
      }, 1500)
      
    } catch (error) {
      console.error('修改密码失败:', error)
    } finally {
      changingPassword.value = false
    }
  } catch (error) {
    // 表单验证失败，不处理
  }
}

// 格式化日期时间
function formatDateTime(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}
</script>
