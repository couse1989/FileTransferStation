<template>
  <div class="login-container">
    <div class="login-box">
      <h1 class="login-title">文件中转站</h1>
      
      <el-form ref="formRef" :model="form" :rules="rules" @submit.prevent="handleLogin">
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="用户名"
            prefix-icon="User"
            size="large"
          />
        </el-form-item>
        
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            prefix-icon="Lock"
            size="large"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        
        <!-- 验证码（登录失败多次后显示） -->
        <el-form-item v-if="showCaptcha" prop="captcha">
          <div style="display: flex; gap: 10px; width: 100%;">
            <el-input
              v-model="form.captcha"
              placeholder="验证码"
              size="large"
              style="flex: 1;"
            />
            <img
              :src="captchaImage"
              @click="refreshCaptcha"
              class="captcha-img"
              alt="验证码"
              title="点击刷新"
            />
          </div>
        </el-form-item>
        
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            style="width: 100%;"
            :loading="loading"
            @click="handleLogin"
          >
            登 录
          </el-button>
        </el-form-item>
        
        <div v-if="errorMessage" style="text-align: center; color: #f56c6c; margin-top: 10px;">
          {{ errorMessage }}
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import api from '@/api'
import { ElMessage } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()

const formRef = ref(null)
const loading = ref(false)
const showCaptcha = ref(false)
const captchaImage = ref('')
const captchaKey = ref('')
const errorMessage = ref('')

const form = reactive({
  username: '',
  password: '',
  captcha: ''
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

// 获取验证码
async function refreshCaptcha() {
  try {
    const res = await api.get('/auth/captcha')
    captchaImage.value = res.captcha_image
    captchaKey.value = res.captcha_key
  } catch (error) {
    console.error('获取验证码失败:', error)
  }
}

// 登录
async function handleLogin() {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    loading.value = true
    errorMessage.value = ''
    
    try {
      const loginData = {
        username: form.username,
        password: form.password
      }
      
      // 如果需要验证码
      if (showCaptcha.value) {
        loginData.captcha = form.captcha
        loginData.captcha_key = captchaKey.value
      }
      
      const res = await userStore.login(loginData)
      
      ElMessage.success('登录成功')
      router.push('/')
      
    } catch (error) {
      const data = error.response?.data
      
      // 显示错误信息
      errorMessage.value = data?.error || '登录失败'
      
      // 检查是否需要显示验证码
      if (data?.require_captcha && !showCaptcha.value) {
        showCaptcha.value = true
        await refreshCaptcha()
      } else if (data?.need_new_captcha) {
        await refreshCaptcha()
      }
      
      // 清空验证码输入
      form.captcha = ''
      
    } finally {
      loading.value = false
    }
  })
}

onMounted(() => {
  // 预加载验证码（如果需要）
  if (showCaptcha.value) {
    refreshCaptcha()
  }
})
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 16px;
}

.login-box {
  width: 420px;
  max-width: 100%;
  padding: 40px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 10px 50px rgba(0, 0, 0, 0.2);
}

.login-title {
  text-align: center;
  font-size: 28px;
  color: #303133;
  margin-bottom: 30px;
}

.captcha-img {
  height: 50px;
  cursor: pointer;
  border-radius: 4px;
  flex-shrink: 0;
}

@media (max-width: 768px) {
  .login-box {
    padding: 24px 20px;
  }
  
  .login-title {
    font-size: 22px;
    margin-bottom: 20px;
  }
}
</style>
