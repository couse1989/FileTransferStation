<template>
  <div class="page-container">
    <div class="page-header">
      <h2>用户管理</h2>
      <p>管理系统用户，创建、编辑、删除和重置密码</p>
    </div>
    
    <!-- 操作栏 -->
    <el-card style="margin-bottom: 20px;">
      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
        <div style="display: flex; gap: 12px; flex: 1;">
          <el-input
            v-model="searchQuery"
            placeholder="搜索用户名..."
            prefix-icon="Search"
            clearable
            style="width: 300px;"
            @input="handleSearch"
          />
        </div>
        
        <el-button type="primary" icon="Plus" @click="showCreateDialog">
          创建用户
        </el-button>
      </div>
    </el-card>
    
    <!-- 用户列表 -->
    <el-card>
      <el-table :data="users" stripe style="width: 100%" v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        
        <el-table-column prop="username" label="用户名" min-width="120">
          <template #default="{ row }">
            <span style="font-weight: 500;">{{ row.username }}</span>
            <el-tag v-if="row.is_admin" type="danger" size="small" style="margin-left: 8px;">管理员</el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-switch
              :model-value="row.is_active"
              @change="(val) => toggleUserStatus(row, val)"
              active-text="启用"
              inactive-text="禁用"
            />
          </template>
        </el-table-column>
        
        <el-table-column prop="file_count" label="文件数" width="100" sortable />
        
        <el-table-column label="已用空间" width="120">
          <template #default="{ row }">
            {{ row.total_size_display }}
          </template>
        </el-table-column>
        
        <el-table-column label="注册时间" width="170">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        
        <el-table-column label="最后登录" width="170">
          <template #default="{ row }">
            {{ formatDate(row.last_login) || '从未登录' }}
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-space wrap>
              <el-button text type="primary" size="small" @click="showEditDialog(row)">
                编辑
              </el-button>
              
              <el-button text type="warning" size="small" @click="showResetPasswordDialog(row)">
                重置密码
              </el-button>
              
              <el-popconfirm
                title="确定要删除这个用户吗？"
                @confirm="deleteUser(row)"
                :disabled="row.is_admin"
              >
                <template #reference>
                  <el-button text type="danger" size="small" :disabled="row.is_admin">删除</el-button>
                </template>
              </el-popconfirm>
            </el-space>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div style="margin-top: 16px; display: flex; justify-content: space-between; align-items: center;">
        <span style="color: #909399;">共 {{ total }} 个用户</span>
        
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="sizes, prev, pager, next, jumper"
          @size-change="fetchUsers"
          @current-change="fetchUsers"
        />
      </div>
    </el-card>
    
    <!-- 创建/编辑用户对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEditing ? '编辑用户' : '创建用户'" width="450px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" :disabled="isEditing" placeholder="请输入用户名（3-20个字符）" />
        </el-form-item>
        
        <el-form-item v-if="!isEditing" label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="请输入密码（至少6位）" />
        </el-form-item>
        
        <el-form-item label="管理员">
          <el-switch v-model="form.is_admin" />
        </el-form-item>
        
        <el-form-item label="状态">
          <el-switch v-model="form.is_active" active-text="启用" inactive-text="禁用" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
    
    <!-- 重置密码对话框 -->
    <el-dialog v-model="resetPasswordDialogVisible" title="重置密码" width="400px">
      <p>确定要重置用户 <strong>{{ currentUser?.username }}</strong> 的密码吗？</p>
      
      <el-form label-width="80px" style="margin-top: 16px;">
        <el-form-item label="新密码">
          <el-input v-model="newPassword" type="password" show-password placeholder="请输入新密码（至少6位）" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="resetPasswordDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleResetPassword" :loading="resettingPassword">确认重置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

// 状态
const users = ref([])
const loading = ref(false)
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 对话框相关
const dialogVisible = ref(false)
const isEditing = ref(false)
const submitting = ref(false)
const currentUser = ref(null)
const formRef = ref(null)

// 重置密码相关
const resetPasswordDialogVisible = ref(false)
const resettingPassword = ref(false)
const newPassword = ref('')

// 表单数据
const form = reactive({
  username: '',
  password: '',
  is_admin: false,
  is_active: true
})

// 表单验证规则
const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度必须在3-20个字符之间', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能小于6位', trigger: 'blur' }
  ]
}

// 获取用户列表
async function fetchUsers() {
  loading.value = true
  
  try {
    const params = {
      page: currentPage.value,
      per_page: pageSize.value,
      search: searchQuery.value
    }
    
    const res = await api.get('/admin/users', { params })
    users.value = res.users || []
    total.value = res.total || 0
    
  } catch (error) {
    console.error('获取用户列表失败:', error)
  } finally {
    loading.value = false
  }
}

// 搜索（防抖）
let searchTimer = null
function handleSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  
  searchTimer = setTimeout(() => {
    currentPage.value = 1
    fetchUsers()
  }, 500)
}

// 显示创建对话框
function showCreateDialog() {
  isEditing.value = false
  form.username = ''
  form.password = ''
  form.is_admin = false
  form.is_active = true
  dialogVisible.value = true
}

// 显示编辑对话框
function showEditDialog(user) {
  isEditing.value = true
  currentUser.value = user
  form.username = user.username
  form.password = ''
  form.is_admin = user.is_admin
  form.is_active = user.is_active
  dialogVisible.value = true
}

// 切换用户状态
async function toggleUserStatus(user, value) {
  try {
    await api.put(`/admin/users/${user.id}`, { is_active: value })
    
    user.is_active = value
    ElMessage.success(`用户已${value ? '启用' : '禁用'}`)
    
  } catch (error) {
    console.error('更新状态失败:', error)
  }
}

// 提交表单（创建或编辑）
async function handleSubmit() {
  if (!formRef.value) return
  
  await formRef.validate(async (valid) => {
    if (!valid) return
    
    submitting.value = true
    
    try {
      if (isEditing.value) {
        // 编辑用户
        await api.put(`/admin/users/${currentUser.value.id}`, {
          username: form.username,
          is_admin: form.is_admin,
          is_active: form.is_active
        })
        
        ElMessage.success('用户信息更新成功')
      } else {
        // 创建用户
        await api.post('/admin/users', {
          username: form.username,
          password: form.password,
          is_admin: form.is_admin
        })
        
        ElMessage.success('用户创建成功')
      }
      
      dialogVisible.value = false
      fetchUsers()
      
    } catch (error) {
      console.error('操作失败:', error)
    } finally {
      submitting.value = false
    }
  })
}

// 显示重置密码对话框
function showResetPasswordDialog(user) {
  currentUser.value = user
  newPassword.value = ''
  resetPasswordDialogVisible.value = true
}

// 执行重置密码
async function handleResetPassword() {
  if (!newPassword.value || newPassword.value.length < 6) {
    ElMessage.warning('密码长度不能小于6位')
    return
  }
  
  resettingPassword.value = true
  
  try {
    await api.post(`/admin/users/${currentUser.value.id}/reset-password`, {
      password: newPassword.value
    })
    
    ElMessage.success(`用户 ${currentUser.value.username} 的密码已重置`)
    resetPasswordDialogVisible.value = false
    
  } catch (error) {
    console.error('重置密码失败:', error)
  } finally {
    resettingPassword.value = false
  }
}

// 删除用户
async function deleteUser(user) {
  try {
    await api.delete(`/admin/users/${user.id}`)
    ElMessage.success(`用户 ${user.username} 已删除`)
    fetchUsers()
    
  } catch (error) {
    console.error('删除失败:', error)
  }
}

// 格式化日期
function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(() => {
  fetchUsers()
})
</script>
