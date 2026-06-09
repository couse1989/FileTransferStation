"""
文件中转站 - 配置文件
"""
import os

class Config:
    # 基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-change-in-production'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-key-change-in-production'
    
    # 数据库配置 (使用SQLite - 使用绝对路径)
    _basedir = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{os.path.join(_basedir, "filetransfer.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 文件存储配置
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or '/opt/filetransfer/uploads'
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024 * 1024  # 10GB
    CHUNK_SIZE = 5 * 1024 * 1024  # 分块大小: 5MB
    
    # 大文件分块上传阈值 (100MB)
    LARGE_FILE_THRESHOLD = 100 * 1024 * 1024
    
    # 文件保留时间（默认24小时，单位：小时）
    DEFAULT_FILE_EXPIRY = 24
    MAX_FILE_EXPIRY = 720  # 最长30天
    
    # JWT Token过期时间
    JWT_ACCESS_TOKEN_EXPIRES = 86400  # 24小时
    JWT_REFRESH_TOKEN_EXPIRES = 604800  # 7天
    
    # 登录安全配置
    LOGIN_ATTEMPT_LIMIT = 5  # 登录失败次数限制
    LOGIN_LOCKOUT_TIME = 900  # 锁定时间15分钟(秒)
    
    # 提取码配置
    EXTRACT_CODE_LENGTH = 4
    EXTRACT_CODE_CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'  # 去掉容易混淆的字符
    
    # 日志配置
    LOG_FOLDER = '/opt/filetransfer/logs'
    LOG_MAX_SIZE = 10 * 1024 * 1024  # 单个日志文件最大10MB
    LOG_BACKUP_COUNT = 5  # 保留5个备份
    
    # GitHub更新配置
    GITHUB_REPO = 'couse1989/FileTransferStation'
    GITHUB_BRANCH = 'main'
    
    # 服务端口
    PORT = int(os.environ.get('PORT', 3000))
    HOST = '0.0.0.0'
