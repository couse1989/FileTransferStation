# 文件中转站

一个功能完整的文件分享与中转平台，支持大文件上传、提取码分享、用户管理等功能。

## 功能特性

### 用户功能
- ✅ **文件上传**：支持单文件和批量上传，最大10GB
- ✅ **分块上传**：超过100MB的文件自动分块上传，支持断点续传
- ✅ **访问控制**：
  - 公开链接（任何人可访问）
  - 提取码模式（4位字母数字混合）
  - 指定用户模式（仅特定用户可访问）
- ✅ **文件管理**：查看、下载、删除、续期、预览
- ✅ **批量操作**：批量下载（打包成ZIP）、批量删除
- ✅ **文件预览**：支持图片、文本、PDF在线预览
- ✅ **提取码下载**：无需登录即可通过提取码下载文件

### 管理员功能
- ✅ **用户管理**：创建、编辑、删除用户，重置密码
- ✅ **文件管理**：查看所有文件，强制删除，清理过期文件
- ✅ **日志系统**：
  - 登录日志（记录IP、时间、成功/失败）
  - 操作日志（记录所有关键操作）
  - 日志自动轮转（防日志文件过大）
- ✅ **系统统计**：仪表盘显示系统状态和使用情况
- ✅ **自动更新**：从GitHub拉取更新，版本检查
- ✅ **自动清理**：定时清理过期文件释放存储空间

### 安全特性
- ✅ **登录验证**：JWT Token认证
- ✅ **密码加密**：bcrypt加盐哈希存储
- ✅ **防暴力破解**：
  - 连续5次失败后要求输入验证码
  - IP临时锁定机制
  - 图形验证码
- ✅ **文件安全**：
  - 文件名随机化存储（防路径遍历）
  - 文件类型检查
  - MD5校验确保完整性

## 技术栈

```
后端: Python 3.10 + Flask + SQLAlchemy (SQLite)
前端: Vue 3 + Vite + Element Plus + Pinia
部署: Gunicorn + Nginx + Systemd
数据库: SQLite（适合中小规模应用）
```

## 系统要求

- **操作系统**: CentOS 7+/8+, Ubuntu 18.04+, Debian 9+
- **架构**: x86_64 或 aarch64
- **内存**: 至少512MB（推荐1GB+）
- **磁盘空间**: 至少5GB可用空间
- **网络**: 需要能访问GitHub（用于代码更新）

## 快速部署

### 一键安装脚本

```bash
# 下载并执行部署脚本
curl -fsSL https://raw.githubusercontent.com/couse1989/FileTransferStation/main/deploy.sh | bash

# 或者手动下载后执行
wget https://raw.githubusercontent.com/couse1989/FileTransferStation/main/deploy.sh
chmod +x deploy.sh
sudo ./deploy.sh
```

部署脚本会自动完成以下工作：
1. 检测操作系统和环境
2. 安装所有依赖（Python、Node.js、Nginx等）
3. 从GitHub克隆代码仓库
4. 构建前端项目
5. 初始化数据库
6. 配置Nginx反向代理
7. 配置Systemd服务（开机自启）
8. 配置防火墙规则
9. 设置自动更新定时任务

### 手动部署（如果一键脚本不适用）

```bash
# 1. 克隆仓库
cd /opt
git clone https://github.com/couse1989/FileTransferStation.git filetransfer
cd filetransfer

# 2. 创建Python虚拟环境
python3 -m venv venv
source venv/bin/activate

# 3. 安装Python依赖
pip install -r requirements.txt
pip install gunicorn eventlet

# 4. 构建前端
cd frontend
npm install
npm run build
cp -r dist/* ../backend/static/
cd ..

# 5. 创建必要目录
mkdir -p uploads logs backups

# 6. 初始化数据库
cd backend
python -c "from app import create_app; app = create_app(); from models import db; db.create_all()"

# 7. 启动服务
gunicorn wsgi:app --workers 4 --bind 127.0.0.1:3000 --timeout 120
```

### 使用Nginx（推荐）

创建配置文件 `/etc/nginx/conf.d/filetransfer.conf`：

```nginx
server {
    listen 3000;
    server_name _;

    location / {
        root /opt/filetransfer/backend/static;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        client_max_body_size 10G;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

重启Nginx：`sudo nginx -t && sudo systemctl restart nginx`

## 默认账户

⚠️ **重要**：部署成功后请立即修改默认管理员密码！

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | admin | Admin@123456 |

## 配置说明

主要配置文件位于 `backend/config.py`：

```python
class Config:
    # 服务端口（默认3000）
    PORT = 3000
    
    # 最大文件大小（10GB）
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024 * 1024
    
    # 大文件分块阈值（100MB）
    LARGE_FILE_THRESHOLD = 100 * 1024 * 1024
    
    # 分块大小（5MB）
    CHUNK_SIZE = 5 * 1024 * 1024
    
    # 默认文件保留时长（24小时）
    DEFAULT_FILE_EXPIRY = 24
    MAX_FILE_EXPIRY = 720  # 最长30天
    
    # 登录失败次数限制
    LOGIN_ATTEMPT_LIMIT = 5
    LOGIN_LOCKOUT_TIME = 900  # 锁定15分钟
    
    # 提取码长度（4位字母数字混合）
    EXTRACT_CODE_LENGTH = 4
    
    # JWT Token过期时间
    JWT_ACCESS_TOKEN_EXPIRES = 86400   # 24小时
    JWT_REFRESH_TOKEN_EXPIRES = 604800 # 7天
```

## 目录结构

```
/opt/filetransfer/
├── backend/                 # 后端代码
│   ├── app.py              # 应用入口
│   ├── config.py           # 配置文件
│   ├── models.py           # 数据库模型
│   ├── wsgi.py             # WSGI入口
│   ├── run.py              # 开发启动入口
│   ├── routes/             # API路由
│   │   ├── auth.py         # 认证相关
│   │   ├── files.py        # 文件管理
│   │   ├── admin.py        # 管理员功能
│   │   └── system.py       # 系统管理
│   ├── utils/              # 工具函数
│   │   ├── rate_limiter.py # 登录限制器
│   │   └── logger.py       # 日志工具
│   └── tasks/              # 定时任务
│       └── scheduler.py    # 任务调度器
├── frontend/               # 前端代码
│   ├── src/                # 源代码
│   ├── dist/               # 构建产物
│   └── package.json        # 前端依赖
├── uploads/                # 上传文件存储目录
├── logs/                   # 日志文件目录
├── filetransfer.db         # SQLite数据库
└── deploy.sh               # 一键部署脚本
```

## 常用命令

### 服务管理

```bash
# 启动服务
sudo systemctl start filetransfer

# 停止服务
sudo systemctl stop filetransfer

# 重启服务
sudo systemctl restart filetransfer

# 查看状态
sudo systemctl status filetransfer

# 查看实时日志
sudo journalctl -u filetransfer -f
```

### 更新系统

```bash
# 方式1：使用Web界面（管理员 → 系统设置 → 点击"立即更新"）

# 方式2：命令行
cd /opt/filetransfer
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
cd frontend && npm install && npm run build && cp -r dist/* ../backend/static/
sudo systemctl restart filetransfer
```

### 数据备份

```bash
# 备份SQLite数据库
cp /opt/filetransfer/filetransfer.db /opt/filetransfer/backups/db_$(date +%Y%m%d_%H%M%S).db

# 备份上传的文件
tar -czf /opt/filetransfer/backups/uploads_$(date +%Y%m%d).tar.gz uploads/
```

## API文档

### 认证接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 用户登录 |
| GET | `/api/auth/captcha` | 获取验证码 |
| POST | `/api/auth/refresh` | 刷新Token |
| GET | `/api/auth/me` | 获取当前用户信息 |
| POST | `/api/auth/change-password` | 修改密码 |

### 文件接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/files/upload` | 上传文件（<100MB）|
| POST | `/api/files/upload/init` | 初始化分块上传 |
| POST | `/api/files/upload/chunk` | 上传文件块 |
| POST | `/api/files/upload/complete` | 完成分块上传 |
| GET | `/api/files/list` | 获取文件列表 |
| GET | `/api/files/:id` | 获取文件详情 |
| GET | `/api/files/download/:id` | 下载文件 |
| GET | `/api/files/preview/:id` | 预览文件 |
| POST | `/api/files/renew/:id` | 续期文件 |
| DELETE | `/api/files/:id` | 删除文件 |
| POST | `/api/files/batch-download` | 批量下载 |
| GET | `/api/files/download/code/:code` | 通过提取码下载 |

### 管理员接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/admin/users` | 用户列表 |
| POST | `/api/admin/users` | 创建用户 |
| PUT | `/api/admin/users/:id` | 编辑用户 |
| POST | `/api/admin/users/:id/reset-password` | 重置密码 |
| DELETE | `/api/admin/users/:id` | 删除用户 |
| GET | `/api/admin/files` | 所有文件列表 |
| DELETE | `/api/admin/files/:id` | 强制删除文件 |
| GET | `/api/admin/logs/login` | 登录日志 |
| GET | `/api/admin/logs/operation` | 操作日志 |
| GET | `/api/admin/stats` | 系统统计 |
| POST | `/api/admin/cleanup` | 清理过期文件 |

### 系统接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/system/health` | 健康检查 |
| GET | `/api/system/version` | 版本信息 |
| POST | `/api/system/check-update` | 检查更新 |
| POST | `/api/system/update` | 执行更新 |

## 安全建议

1. **立即修改默认密码**：首次登录后请立即更改管理员密码
2. **配置HTTPS**：生产环境强烈建议使用Let's Encrypt免费证书
3. **定期备份**：定期备份数据库和重要文件
4. **监控日志**：定期查看登录日志，发现异常及时处理
5. **网络隔离**：如果可能，将服务器放在内网或使用VPN访问
6. **防火墙规则**：只开放必要的端口（默认3000）

## 故障排除

### 服务无法启动

```bash
# 查看详细错误日志
journalctl -u filetransfer -n 50

# 常见原因及解决方法：
# 1. 端口被占用：ss -tlnp | grep :3000
# 2. 数据库锁定：删除 .lock 文件或等待
# 3. 依赖未安装：重新执行 pip install -r requirements.txt
# 4. 权限问题：chown -R root:root /opt/filetransfer
```

### 大文件上传失败

- 检查Nginx配置中的 `client_max_body_size`
- 检查磁盘空间是否充足
- 检查Gunicorn超时设置 `--timeout`
- 检查浏览器超时设置

### 无法连接GitHub

- 检查DNS配置
- 如果在中国大陆，可能需要配置代理
- 可以手动下载代码包上传到服务器

## 性能优化建议

1. **启用Gzip压缩**：在Nginx中启用gzip可以大幅减少传输数据量
2. **静态资源缓存**：为CSS、JS、图片等设置长期缓存
3. **CDN加速**：如果有大量静态资源，考虑使用CDN
4. **数据库优化**：频繁查询的字段添加索引
5. **负载均衡**：如果并发量大，可以使用多实例+负载均衡

## 许可证

MIT License

## 贡献指南

欢迎提交Issue和Pull Request！

1. Fork本项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

## 支持

如果您遇到问题或有建议，请在[GitHub Issues](https://github.com/couse1989/FileTransferStation/issues)提交。

## 更新日志

### v1.0.0 (2024-01-15)
- 🎉 初始版本发布
- 完整的用户认证和管理系统
- 文件上传、下载、预览功能
- 提取码分享机制
- 大文件分块上传支持
- 管理员后台界面
- 自动清理和更新功能
- 完整的操作日志系统
