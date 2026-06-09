"""
数据库模型定义
使用SQLite + SQLAlchemy ORM
"""
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import string

db = SQLAlchemy()

class User(db.Model):
    """用户表"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    last_login_ip = db.Column(db.String(45))
    
    # 关系
    uploaded_files = db.relationship('File', backref='uploader', lazy='dynamic', foreign_keys='File.uploaded_by')
    
    def set_password(self, password):
        """设置密码（bcrypt加密）"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'is_admin': self.is_admin,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class File(db.Model):
    """文件表"""
    __tablename__ = 'files'
    
    id = db.Column(db.Integer, primary_key=True)
    original_name = db.Column(db.String(255), nullable=False)  # 原始文件名
    stored_name = db.Column(db.String(100), unique=True, nullable=False)  # 随机存储名
    file_size = db.Column(db.BigInteger, nullable=False)  # 文件大小(字节)
    mime_type = db.Column(db.String(100))  # MIME类型
    file_hash = db.Column(db.String(64))  # 文件MD5哈希
    
    # 存储路径
    storage_path = db.Column(db.String(512), nullable=False)
    
    # 权限设置
    access_type = db.Column(db.String(20), default='public')  # public, code, private
    extract_code = db.Column(db.String(10))  # 提取码
    allowed_users = db.Column(db.Text)  # 允许的用户ID列表(JSON)
    
    # 时间设置
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    expires_at = db.Column(db.DateTime, index=True)  # 过期时间
    download_count = db.Column(db.Integer, default=0)  # 下载次数
    
    # 分块上传相关
    is_chunked = db.Column(db.Boolean, default=False)  # 是否分块上传
    chunk_total = db.Column(db.Integer, default=0)  # 总块数
    chunk_uploaded = db.Column(db.Integer, default=0)  # 已上传块数
    
    # 状态
    status = db.Column(db.String(20), default='active')  # active, expired, deleted
    
    @staticmethod
    def generate_stored_name():
        """生成随机文件名"""
        return secrets.token_hex(16)
    
    @staticmethod
    def generate_extract_code(length=4):
        """生成提取码"""
        chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
        return ''.join(secrets.choice(chars) for _ in range(length))
    
    def to_dict(self, include_code=False):
        data = {
            'id': self.id,
            'original_name': self.original_name,
            'file_size': self.file_size,
            'file_size_display': self._format_size(self.file_size),
            'mime_type': self.mime_type,
            'access_type': self.access_type,
            'uploaded_by': self.uploaded_by,
            'uploaded_by_name': self.uploader.username if self.uploader else None,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'download_count': self.download_count,
            'status': self.status,
            'is_expired': self.is_expired if hasattr(self, 'is_expired') else False
        }
        
        if include_code and self.extract_code:
            data['extract_code'] = self.extract_code
            
        return data
    
    @staticmethod
    def _format_size(size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"


class FileChunk(db.Model):
    """文件分块表"""
    __tablename__ = 'file_chunks'
    
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey('files.id'), nullable=False, index=True)
    chunk_index = db.Column(db.Integer, nullable=False)  # 块索引
    chunk_path = db.Column(db.String(512), nullable=False)  # 块文件路径
    chunk_size = db.Column(db.Integer, nullable=False)  # 块大小
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='uploading')  # uploading, completed


class LoginLog(db.Model):
    """登录日志表"""
    __tablename__ = 'login_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    username = db.Column(db.String(80), nullable=False)
    ip_address = db.Column(db.String(45), nullable=False, index=True)
    user_agent = db.Column(db.String(500))
    success = db.Column(db.Boolean, default=False, index=True)
    fail_reason = db.Column(db.String(100))  # 失败原因: invalid_password, account_locked, etc.
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent[:100] if self.user_agent else None,
            'success': self.success,
            'fail_reason': self.fail_reason,
            'login_time': self.login_time.isoformat() if self.login_time else None
        }


class OperationLog(db.Model):
    """操作日志表"""
    __tablename__ = 'operation_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    username = db.Column(db.String(80))
    operation_type = db.Column(db.String(50), nullable=False, index=True)  # upload, download, delete, renew, etc.
    target_type = db.Column(db.String(20))  # file, user, system
    target_id = db.Column(db.Integer)
    details = db.Column(db.Text)  # 详细信息JSON
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'operation_type': self.operation_type,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'details': self.details,
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class SystemConfig(db.Model):
    """系统配置表"""
    __tablename__ = 'system_config'
    
    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.Text)
    description = db.Column(db.String(255))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
