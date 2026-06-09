#!/bin/bash
# ============================================================
# 文件中转站 - 一键部署脚本
# 适用于 CentOS/Ubuntu/Debian 系统
# ============================================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量
PROJECT_NAME="filetransfer"
INSTALL_DIR="/opt/${PROJECT_NAME}"
GITHUB_REPO="https://github.com/couse1989/FileTransferStation.git"
GITHUB_BRANCH="main"
PYTHON_VERSION="3.10"
PORT=3000
BACKEND_PORT=5000  # Gunicorn内部监听端口（Nginx代理到外部PORT）

# GitHub Token（用于私有仓库或自动更新）
# 请设置环境变量: export GITHUB_TOKEN="your_token_here"
GITHUB_TOKEN="${GITHUB_TOKEN:-}"

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "\n${BLUE}[STEP]${NC} $1"
    echo "========================================"
}

# 检查是否为root用户
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "请使用 root 用户运行此脚本"
        exit 1
    fi
    log_info "当前用户: $(whoami) (OK)"
}

# 检测操作系统类型
detect_os() {
    log_step "检测操作系统..."
    
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS_ID=$ID
        OS_VERSION=$VERSION_ID
        
        case "$OS_ID" in
            centos|rhel|rocky|alma)
                OS_TYPE="rhel"
                PKG_MGR="yum"
                ;;
            ubuntu|debian)
                OS_TYPE="debian"
                PKG_MGR="apt-get"
                ;;
            *)
                log_error "不支持的操作系统: $OS_ID"
                log_error "仅支持: CentOS/RHEL, Ubuntu, Debian"
                exit 1
                ;;
        esac
        
        log_info "检测到: ${PRETTY_NAME} (${OS_TYPE})"
        
    else
        log_error "无法检测操作系统类型"
        exit 1
    fi
}

# 检查系统要求
check_requirements() {
    log_step "检查系统要求..."
    
    # 检查系统架构
    ARCH=$(uname -m)
    if [[ ! "$ARCH" =~ ^(x86_64|aarch64)$ ]]; then
        log_error "不支持的架构: $ARCH (需要 x86_64 或 aarch64)"
        exit 1
    fi
    log_info "系统架构: ${ARCH} (OK)"
    
    # 检查可用磁盘空间 (至少需要5GB)
    AVAILABLE_SPACE=$(df -BG / | tail -1 | awk '{print $4}' | tr -d 'G')
    if [ "$AVAILABLE_SPACE" -lt 5 ]; then
        log_error "可用磁盘空间不足: 当前${AVAILABLE_SPACE}GB，至少需要5GB"
        exit 1
    fi
    log_info "可用磁盘空间: ${AVAILABLE_SPACE}GB (OK)"
    
    # 检查可用内存 (至少需要512MB)
    TOTAL_MEM=$(free -m | awk '/^Mem:/{print $2}')
    if [ "$TOTAL_MEM" -lt 512 ]; then
        log_error "可用内存不足: 当前${TOTAL_MEM}MB，至少需要512MB"
        exit 1
    fi
    log_info "总内存: ${TOTAL_MEM}MB (OK)"
    
    # 检查端口占用
    if ss -tlnp | grep -q ":${PORT} "; then
        log_warn "端口 ${PORT} 已被占用"
        read -p "是否继续？(将尝试停止占用的服务) [y/N]: " choice
        if [[ "$choice" != "y" && "$choice" != "Y" ]]; then
            exit 1
        fi
    else
        log_info "端口 ${PORT} 可用 (OK)"
    fi
    
    # 网络连通性测试
    log_info "测试网络连通性..."
    if ping -c 1 -W 3 github.com > /dev/null 2>&1; then
        log_info "GitHub 连通性: OK"
    else
        log_error "无法连接 GitHub，请检查网络连接或DNS配置"
        exit 1
    fi
}

# 安装基础依赖
install_base_dependencies() {
    log_step "安装基础依赖..."
    
    case "$OS_TYPE" in
        rhel)
            yum update -y
            
            # 安装EPEL（如果尚未安装）
            if ! rpm -q epel-release >/dev/null 2>&1; then
                yum install -y epel-release || true
            fi
            
            # RHEL/CentOS 8+ 使用 dnf
            if command -v dnf &> /dev/null; then
                PKG_MGR="dnf"
            fi
            
            $PKG_MGR groupinstall -y "Development Tools" || true
            $PKG_MGR install -y \
                python3 python3-pip python3-devel \
                git wget curl \
                nginx \
                sqlite-devel \
                libffi-dev \
                gcc-c++
            
            # 安装Python 3.10（如果没有）
            if ! command -v python3.10 &> /dev/null && [ "$OS_ID" = "centos" ] && [ "${VERSION%%.*}" -ge 8 ]; then
                log_info "安装 Python 3.10..."
                $PKG_MGR install -y python310 python310-pip python310-devel || true
                
                if command -v python3.10 &> /dev/null; then
                    alternatives --set python3 /usr/bin/python3.10 || true
                    PYTHON_CMD="python3.10"
                    PIP_CMD="pip3.10"
                fi
            fi
            ;;
            
        debian)
            apt-get update -y
            apt-get upgrade -y
            
            apt-get install -y \
                python3 python3-pip python3-venv python3-dev \
                git wget curl nginx \
                sqlite3 libsqlite3-dev \
                libffi-dev build-essential \
                python3-cairo
            ;;
    esac
    
    log_info "基础依赖安装完成"
}

# 设置Python环境
setup_python_env() {
    log_step "设置Python环境..."
    
    # 检测Python命令
    if command -v python3.10 &> /dev/null; then
        PYTHON_CMD="python3.10"
    elif command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    else
        log_error "未找到 Python 3，安装失败"
        exit 1
    fi
    
    # 获取Python版本
    PY_VER=$($PYTHON_CMD --version | awk '{print $2}')
    log_info "检测到 Python 版本: ${PY_VER}"
    
    log_info "Python环境将在克隆代码后配置"
}

# 克隆代码仓库
clone_repository() {
    log_step "克隆代码仓库..."
    
    # 如果目录已存在，先备份（但保留venv目录如果存在）
    if [ -d "$INSTALL_DIR" ]; then
        # 检查是否有虚拟环境需要保留
        if [ -d "${INSTALL_DIR}/venv" ]; then
            log_info "保留现有虚拟环境..."
            VENV_BACKUP="/tmp/filetransfer_venv_backup_$(date +%s)"
            cp -r "${INSTALL_DIR}/venv" "$VENV_BACKUP"
        fi
        
        BACKUP_DIR="${INSTALL_DIR}_backup_$(date +%Y%m%d_%H%M%S)"
        log_warn "目标目录已存在，备份到: ${BACKUP_DIR}"
        rm -rf "$BACKUP_DIR" 2>/dev/null || true
        mv "$INSTALL_DIR" "$BACKUP_DIR"
        
        # 恢复虚拟环境
        if [ -d "$VENV_BACKUP" ]; then
            mkdir -p "$INSTALL_DIR"
            mv "$VENV_BACKUP" "${INSTALL_DIR}/venv"
            log_info "虚拟环境已保留"
        fi
    fi
    
    # 如果目录不存在（首次安装或没有旧venv），创建它
    if [ ! -d "$INSTALL_DIR" ]; then
        mkdir -p "$INSTALL_DIR"
    fi
    
    # 克隆仓库到临时目录（避免覆盖已有的venv）
    TEMP_DIR="/tmp/filetransfer_clone_$(date +%s)"
    
    # 克隆仓库（如果设置了Token则使用认证）
    if [ -n "$GITHUB_TOKEN" ]; then
        GIT_URL="https://${GITHUB_TOKEN}@github.com/couse1989/FileTransferStation.git"
    else
        GIT_URL="$GITHUB_REPO"
    fi
    
    git clone --branch "$GITHUB_BRANCH" "$GIT_URL" "$TEMP_DIR"
    
    if [ $? -ne 0 ]; then
        log_error "Git克隆失败，请检查网络连接和仓库地址"
        rm -rf "$TEMP_DIR"
        exit 1
    fi
    
    # 将克隆的文件移动到安装目录（保留现有的venv）
    cd "$TEMP_DIR"
    
    # 复制所有文件除了venv目录
    for item in * .*; do
        # 跳过 . 和 ..
        [[ "$item" == "." || "$item" == ".." ]] && continue
        # 跳过venv目录（我们可能已经有一个）
        [[ "$item" == "venv" ]] && continue
        
        # 如果目标是目录，先删除再复制
        if [ -e "${INSTALL_DIR}/${item}" ] || [ -L "${INSTALL_DIR}/${item}" ]; then
            rm -rf "${INSTALL_DIR}/${item}"
        fi
        
        if [ -e "$item" ] || [ -L "$item" ]; then
            mv "$item" "${INSTALL_DIR}/"
        fi
    done
    
    # 清理临时目录
    rm -rf "$TEMP_DIR"
    
    cd $INSTALL_DIR
    log_info "代码克隆完成"
    
    # 显示版本信息
    if [ -f VERSION ]; then
        log_info "项目版本: $(cat VERSION)"
    fi
}

# 安装Python依赖
install_python_dependencies() {
    log_step "安装Python依赖..."
    
    cd $INSTALL_DIR
    
    # 设置虚拟环境目录
    VENV_DIR="${INSTALL_DIR}/venv"
    
    # 创建虚拟环境（如果不存在）
    if [ ! -d "$VENV_DIR" ]; then
        log_info "创建Python虚拟环境..."
        $PYTHON_CMD -m venv "$VENV_DIR"
        
        if [ $? -ne 0 ]; then
            log_error "虚拟环境创建失败"
            exit 1
        fi
    else
        log_info "使用现有虚拟环境"
    fi
    
    # 验证虚拟环境是否存在
    if [ ! -f "$VENV_DIR/bin/activate" ]; then
        log_error "虚拟环境不完整，请检查安装"
        exit 1
    fi
    
    # 使用虚拟环境中的pip
    source "$VENV_DIR/bin/activate"
    
    # 显示使用的Python和pip路径
    log_info "Python路径: $(which python)"
    log_info "Pip路径: $(which pip)"
    
    # 升级pip
    pip install --upgrade pip setuptools wheel
    
    # 从requirements.txt安装依赖（在后端目录中）
    if [ -f requirements.txt ]; then
        log_info "从 requirements.txt 安装依赖..."
        pip install -r requirements.txt
        
        if [ $? -ne 0 ]; then
            log_error "依赖安装失败，请查看上方错误信息"
            exit 1
        fi
    else
        log_warn "未找到 requirements.txt，尝试手动安装核心依赖..."
        pip install Flask Flask-SQLAlchemy flask-cors flask-jwt-extended bcrypt Pillow PyJWT gunicorn gevent requests
    fi
    
    # 验证关键依赖是否安装成功
    log_info "验证关键依赖..."
    python -c "
try:
    import flask
    import flask_sqlalchemy
    import flask_cors
    import flask_jwt_extended
    import bcrypt
    from PIL import Image
    print('所有关键依赖验证通过!')
except ImportError as e:
    print(f'ERROR: 缺少依赖: {e}')
    exit(1)
"
    
    if [ $? -ne 0 ]; then
        log_error "依赖验证失败！某些包未正确安装"
        exit 1
    fi
    
    log_info "Python依赖安装完成（已验证）"
}

# 构建前端
build_frontend() {
    log_step "构建前端..."
    
    cd $INSTALL_DIR/frontend
    
    # 检查Node.js是否已安装
    if ! command -v node &> /dev/null; then
        log_info "安装Node.js..."
        case "$OS_TYPE" in
            rhel)
                $PKG_MGR install -y nodejs npm
                ;;
            debian)
                # 安装最新的LTS版本
                curl -fsSL https://deb.nodesource.com/setup_lts.x | bash -
                apt-get install -y nodejs
                ;;
        esac
    fi
    
    NODE_VER=$(node --version)
    log_info "Node.js版本: ${NODE_VER}"
    
    # 安装前端依赖
    npm install
    
    # 构建
    npm run build
    
    if [ $? -ne 0 ]; then
        log_error "前端构建失败"
        exit 1
    fi
    
    # 将构建产物复制到后端静态文件目录
    mkdir -p $INSTALL_DIR/backend/static
    cp -r $INSTALL_DIR/frontend/dist/* $INSTALL_DIR/backend/static/
    
    log_info "前端构建完成"
}

# 配置Nginx
configure_nginx() {
    log_step "配置 Nginx..."
    
    NGINX_CONF="/etc/nginx/conf.d/${PROJECT_NAME}.conf"
    
    cat > $NGINX_CONF << EOF
# 文件中转站 Nginx 配置
server {
    listen ${PORT};
    server_name _;

    # 前端静态文件
    location / {
        root ${INSTALL_DIR}/backend/static;
        try_files \$uri \$uri/ /index.html;
        
        # 前端路由支持
        location ~* \.(html|css|js|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 30d;
            add_header Cache-Control "public, immutable";
        }
    }

    # API代理到后端（Gunicorn监听在内部端口）
    location /api/ {
        proxy_pass http://127.0.0.1:${BACKEND_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        
        # 大文件上传支持
        client_max_body_size 10G;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # 文件下载（直接代理）
    location /download/ {
        proxy_pass http://127.0.0.1:${BACKEND_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        
        # 下载限速（可选，单位：字节/秒）
        limit_rate 50M;
    }
}
EOF

    # 测试Nginx配置
    nginx -t
    
    if [ $? -eq 0 ]; then
        systemctl restart nginx
        systemctl enable nginx
        log_info "Nginx 配置完成"
    else
        log_error "Nginx 配置错误，请手动检查"
        exit 1
    fi
}

# 配置Systemd服务
configure_systemd_service() {
    log_step "配置 Systemd 服务..."
    
    SERVICE_FILE="/etc/systemd/system/${PROJECT_NAME}.service"
    
    cat > $SERVICE_FILE << EOF
[Unit]
Description=File Transfer Station
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}/backend
Environment=PATH=${INSTALL_DIR}/venv/bin
    ExecStart=${INSTALL_DIR}/venv/bin/gunicorn wsgi:app \\
    --workers 2 \\
    --worker-class gevent \\
    --bind 127.0.0.1:${BACKEND_PORT} \\
    --timeout 120 \\
    --keep-alive 5 \\
    --max-requests 1000 \\
    --max-requests-jitter 100 \\
    --access-logfile ${INSTALL_DIR}/logs/gunicorn_access.log \\
    --error-logfile ${INSTALL_DIR}/logs/gunicorn_error.log

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    # 重载systemd并启用服务
    systemctl daemon-reload
    systemctl enable $PROJECT_NAME
    systemctl start $PROJECT_NAME
    
    sleep 3
    
    # 检查服务状态
    if systemctl is-active --quiet $PROJECT_NAME; then
        log_info "服务启动成功"
    else
        log_error "服务启动失败，请查看日志:"
        journalctl -u $PROJECT_NAME -n 20
        exit 1
    fi
}

# 配置防火墙
configure_firewall() {
    log_step "配置防火墙..."
    
    case "$OS_TYPE" in
        rhel)
            if command -v firewall-cmd &> /dev/null; then
                firewall-cmd --permanent --add-port=${PORT}/tcp
                firewall-cmd --reload
                log_info "防火墙规则已添加 (firewalld)"
            elif command -v iptables &> /dev/null; then
                iptables -I INPUT -p tcp --dport ${PORT} -j ACCEPT
                service iptables save 2>/dev/null || true
                log_info "防火墙规则已添加 (iptables)"
            fi
            ;;
            
        debian)
            if command -v ufw &> /dev/null; then
                ufw allow ${PORT}/tcp
                ufw reload
                log_info "防火墙规则已添加 (ufw)"
            elif command -v iptables &> /dev/null; then
                iptables -I INPUT -p tcp --dport ${PORT} -j ACCEPT
                iptables-save > /etc/iptables/rules.v4 2>/dev/null || true
                log_info "防火墙规则已添加 (iptables)"
            fi
            ;;
    esac
}

# 设置自动更新定时任务
setup_cron_job() {
    log_step "设置自动更新定时任务..."
    
    CRON_FILE="/etc/cron.d/${PROJECT_NAME}"
    
    cat > $CRON_FILE << EOF
# 文件中转站 - 自动检查更新（每天凌晨3点执行）
0 3 * * * root cd ${INSTALL_DIR} && ${INSTALL_DIR}/venv/bin/python scripts/check_update.sh >> ${INSTALL_DIR}/logs/update.log 2>&1
EOF
    
    chmod 644 $CRON_FILE
    
    log_info "自动更新任务已配置 (每天凌晨3点检查)"
}

# 创建必要目录
create_directories() {
    log_step "创建必要目录..."
    
    mkdir -p $INSTALL_DIR/{uploads,logs,backups,.backup}
    chmod -R 755 $INSTALL_DIR/uploads
    
    # 创建日志轮转配置
    LOGROTATE_CONF="/etc/logrotate.d/${PROJECT_NAME}"
    cat > $LOGROTATE_CONF << EOF
${INSTALL_DIR}/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 0644 root root
    size 10M
}
EOF
    
    log_info "目录创建完成"
}

# 初始化数据库
# 初始化数据库
initialize_database() {
    log_step "初始化数据库..."

    cd $INSTALL_DIR/backend

    # 使用虚拟环境中的Python
    source "$INSTALL_DIR/venv/bin/activate"

    # 执行数据库初始化
    python -c "
from app import create_app
app = create_app()
app.app_context().push()
from models import db
db.create_all()
print('Database initialized successfully')
" || {
        log_warn "数据库初始化失败，将在首次启动时自动创建"
    }

    log_info "数据库初始化完成"
}

# 显示部署结果
show_result() {
    log_step "=========================================="
    log_info "部署完成！"
    log_step "=========================================="
    
    echo ""
    echo -e "${GREEN}访问地址: http://$(curl -s ifconfig.me):${PORT}${NC}"
    echo ""
    echo -e "${BLUE}默认管理员账户:${NC}"
    echo "  用户名: admin"
    echo "  密码: Admin@123456"
    echo ""
    echo -e "${YELLOW}重要提示:${NC}"
    echo "  1. 请立即修改默认管理员密码!"
    echo "  2. 建议配置HTTPS证书"
    echo "  3. 定期备份SQLite数据库"
    echo ""
    echo -e "${BLUE}常用命令:${NC}"
    echo "  启动服务:   systemctl start filetransfer"
    echo "  停止服务:   systemctl stop filetransfer"
    echo "  重启服务:   systemctl restart filetransfer"
    echo "  查看日志:   journalctl -u filetransfer -f"
    echo "  更新系统:   ${INSTALL_DIR}/scripts/update.sh"
    echo ""
    echo -e "${BLUE}文件存储位置:${NC}"
    echo "  上传文件:  ${INSTALL_DIR}/uploads/"
    echo "  数据库:     ${INSTALL_DIR}/backend/filetransfer.db"
    echo "  日志文件:   ${INSTALL_DIR}/logs/"
    echo ""
}

# 主函数
main() {
    echo ""
    echo "============================================================"
    echo "           文件中转站 一键部署脚本 v1.0"
    echo "============================================================"
    echo ""
    
    check_root
    detect_os
    check_requirements
    install_base_dependencies
    setup_python_env        # 只检测Python，不创建venv
    clone_repository         # 克隆代码（保留现有venv）
    install_python_dependencies  # 创建venv（如需要）并安装依赖
    build_frontend
    create_directories
    initialize_database
    configure_systemd_service
    configure_nginx
    configure_firewall
    setup_cron_job
    show_result
    
    log_info "所有步骤执行完毕！"
}

# 执行主函数
main "$@"
