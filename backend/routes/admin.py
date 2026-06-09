"""
管理员路由
用户管理、文件管理、日志查看、系统统计
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import os
import json as json_module
from models import db, User, File, LoginLog, OperationLog

admin_bp = Blueprint('admin', __name__)

def check_admin():
    """检查管理员权限，返回 (is_admin, error_response)"""
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id)
    
    if not user or not user.is_admin:
        return False, jsonify({'error': '需要管理员权限'}), 403
    return True, user, None


# ==================== 用户管理 ====================

@admin_bp.route('/users', methods=['GET'])
@jwt_required()
def list_users():
    """获取用户列表（管理员）"""
    is_admin, result, error = check_admin()
    if not is_admin:
        return error
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '').strip()
    
    query = User.query
    
    if search:
        query = query.filter(User.username.ilike(f'%{search}%'))
    
    query = query.order_by(User.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    users_data = []
    for user in pagination.items:
        file_count = File.query.filter_by(uploaded_by=user.id).count()
        total_size = db.session.query(db.func.sum(File.file_size)).filter_by(uploaded_by=user.id).scalar() or 0
        
        user_dict = user.to_dict()
        user_dict['file_count'] = file_count
        user_dict['total_size'] = total_size
        user_dict['total_size_display'] = _format_size(total_size)
        users_data.append(user_dict)
    
    return jsonify({
        'users': users_data,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    }), 200


@admin_bp.route('/users', methods=['POST'])
@jwt_required()
def create_user():
    """创建用户（管理员）"""
    is_admin, admin_user, error = check_admin()
    if not is_admin:
        return error
    
    data = request.get_json()
    
    username = data.get('username', '').strip()
    password = data.get('password')
    is_admin_flag = data.get('is_admin', False)
    
    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400
    
    if len(username) < 3 or len(username) > 20:
        return jsonify({'error': '用户名长度必须在3-20个字符之间'}), 400
    
    if len(password) < 6:
        return jsonify({'error': '密码长度不能小于6位'}), 400
    
    if User.query.filter_by(username=username).first():
        return jsonify({'error': '用户名已存在'}), 409
    
    user = User(
        username=username,
        is_admin=is_admin_flag,
        is_active=True
    )
    user.set_password(password)
    
    db.session.add(user)
    db.session.commit()
    
    log = OperationLog(
        user_id=admin_user.id,
        username=admin_user.username,
        operation_type='create_user',
        target_type='user',
        target_id=user.id,
        details=json_module.dumps({'username': username, 'is_admin': is_admin_flag}),
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({
        'message': f'用户 {username} 创建成功',
        'user': user.to_dict()
    }), 201


@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    """编辑用户（管理员）"""
    is_admin, admin_user, error = check_admin()
    if not is_admin:
        return error
    
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    if 'is_active' in data:
        user.is_active = bool(data['is_active'])
    
    if 'is_admin' in data:
        user.is_admin = bool(data['is_admin'])
    
    if 'username' in data:
        new_username = data['username'].strip()
        if len(new_username) < 3 or len(new_username) > 20:
            return jsonify({'error': '用户名长度必须在3-20个字符之间'}), 400
        
        existing = User.query.filter_by(username=new_username).first()
        if existing and existing.id != user_id:
            return jsonify({'error': '用户名已存在'}), 409
        
        user.username = new_username
    
    db.session.commit()
    
    log = OperationLog(
        user_id=admin_user.id,
        username=admin_user.username,
        operation_type='update_user',
        target_type='user',
        target_id=user_id,
        details=json_module.dumps(data),
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({
        'message': '用户信息更新成功',
        'user': user.to_dict()
    }), 200


@admin_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@jwt_required()
def reset_password(user_id):
    """重置用户密码（管理员）"""
    is_admin, admin_user, error = check_admin()
    if not is_admin:
        return error
    
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    new_password = data.get('password')
    
    if not new_password or len(new_password) < 6:
        return jsonify({'error': '新密码长度不能小于6位'}), 400
    
    user.set_password(new_password)
    db.session.commit()
    
    log = OperationLog(
        user_id=admin_user.id,
        username=admin_user.username,
        operation_type='reset_password',
        target_type='user',
        target_id=user_id,
        details=json_module.dumps({'target_username': user.username}),
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({'message': f'用户 {user.username} 的密码已重置'}), 200


@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    """删除用户（管理员）"""
    is_admin, admin_user, error = check_admin()
    if not is_admin:
        return error
    
    user = User.query.get_or_404(user_id)
    
    if user_id == admin_user.id:
        return jsonify({'error': '不能删除自己的账户'}), 400
    
    file_count = File.query.filter_by(uploaded_by=user_id).count()
    if file_count > 0:
        return jsonify({'error': f'该用户还有 {file_count} 个文件，请先处理文件'}), 400
    
    username = user.username
    db.session.delete(user)
    db.session.commit()
    
    log = OperationLog(
        user_id=admin_user.id,
        username=admin_user.username,
        operation_type='delete_user',
        target_type='user',
        target_id=user_id,
        details=json_module.dumps({'username': username}),
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({'message': f'用户 {username} 已删除'}), 200


# ==================== 文件管理 ====================

@admin_bp.route('/files', methods=['GET'])
@jwt_required()
def list_all_files():
    """获取所有文件列表（管理员）"""
    is_admin, admin_user, error = check_admin()
    if not is_admin:
        return error
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '')
    uploader_id = request.args.get('uploader_id')
    
    query = File.query
    
    if search:
        query = query.filter(File.original_name.ilike(f'%{search}%'))
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    if uploader_id:
        query = query.filter_by(uploaded_by=int(uploader_id))
    
    query = query.order_by(File.uploaded_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    files_data = []
    for file_item in pagination.items:
        file_dict = file_item.to_dict(include_code=True)
        uploader = db.session.get(User, file_item.uploaded_by)
        file_dict['uploader_name'] = uploader.username if uploader else '未知'
        files_data.append(file_dict)
    
    return jsonify({
        'files': files_data,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    }), 200


@admin_bp.route('/files/<int:file_id>', methods=['DELETE'])
@jwt_required()
def admin_delete_file(file_id):
    """强制删除文件（管理员）"""
    is_admin, admin_user, error = check_admin()
    if not is_admin:
        return error
    
    file_record = File.query.get_or_404(file_id)
    
    # 删除物理文件
    if file_record.storage_path and os.path.exists(file_record.storage_path):
        try:
            os.remove(file_record.storage_path)
        except Exception as e:
            print(f"删除物理文件失败: {e}")
    
    filename = file_record.original_name
    db.session.delete(file_record)
    db.session.commit()
    
    log = OperationLog(
        user_id=admin_user.id,
        username=admin_user.username,
        operation_type='admin_delete_file',
        target_type='file',
        target_id=file_id,
        details=json_module.dumps({'filename': filename}),
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({'message': f'文件 {filename} 已被管理员删除'}), 200


# ==================== 日志管理 ====================

@admin_bp.route('/logs/login', methods=['GET'])
@jwt_required()
def get_login_logs():
    """获取登录日志（管理员）"""
    is_admin, admin_user, error = check_admin()
    if not is_admin:
        return error
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    username = request.args.get('username', '').strip()
    success = request.args.get('success')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = LoginLog.query
    
    if username:
        query = query.filter(LoginLog.username.ilike(f'%{username}%'))
    
    if success is not None:
        query = query.filter_by(success=success.lower() == 'true')
    
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(LoginLog.login_time >= start)
        except ValueError:
            pass
    
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(LoginLog.login_time < end)
        except ValueError:
            pass
    
    query = query.order_by(LoginLog.login_time.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    logs_data = [log.to_dict() for log in pagination.items]
    
    return jsonify({
        'logs': logs_data,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    }), 200


@admin_bp.route('/logs/operation', methods=['GET'])
@jwt_required()
def get_operation_logs():
    """获取操作日志（管理员）"""
    is_admin, admin_user, error = check_admin()
    if not is_admin:
        return error
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    operation_type = request.args.get('operation_type', '').strip()
    username = request.args.get('username', '').strip()
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = OperationLog.query
    
    if operation_type:
        query = query.filter(OperationLog.operation_type.ilike(f'%{operation_type}%'))
    
    if username:
        query = query.filter(OperationLog.username.ilike(f'%{username}%'))
    
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(OperationLog.created_at >= start)
        except ValueError:
            pass
    
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(OperationLog.created_at < end)
        except ValueError:
            pass
    
    query = query.order_by(OperationLog.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    logs_data = [log.to_dict() for log in pagination.items]
    
    return jsonify({
        'logs': logs_data,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    }), 200


# ==================== 系统统计 ====================

@admin_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_system_stats():
    """获取系统统计信息（管理员）"""
    is_admin, admin_user, error = check_admin()
    if not is_admin:
        return error
    
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    stats = {
        'total_users': User.query.count(),
        'active_users': User.query.filter_by(is_active=True).count(),
        'admin_users': User.query.filter_by(is_admin=True).count(),
        
        'total_files': File.query.count(),
        'active_files': File.query.filter_by(status='active').count(),
        'expired_files': File.query.filter_by(status='expired').count(),
        'deleted_files': File.query.filter_by(status='deleted').count(),
        'total_storage_used': db.session.query(db.func.sum(File.file_size)).filter(File.status.in_(['active', 'expired'])).scalar() or 0,
        
        'today_uploads': File.query.filter(File.uploaded_at >= today).count(),
        'today_downloads': OperationLog.query.filter(
            OperationLog.operation_type == 'download',
            OperationLog.created_at >= today
        ).count(),
        'today_logins': LoginLog.query.filter(
            LoginLog.success == True,
            LoginLog.login_time >= today
        ).count(),
        'today_failed_logins': LoginLog.query.filter(
            LoginLog.success == False,
            LoginLog.login_time >= today
        ).count(),
        
        'storage_info': _get_storage_info()
    }
    
    stats['total_storage_used_display'] = _format_size(stats['total_storage_used'])
    
    return jsonify(stats), 200


@admin_bp.route('/cleanup', methods=['POST'])
@jwt_required()
def cleanup_expired_files():
    """手动清理过期文件（管理员）"""
    is_admin, admin_user, error = check_admin()
    if not is_admin:
        return error
    
    now = datetime.utcnow()
    
    expired_files = File.query.filter(
        File.status == 'active',
        File.expires_at != None,
        File.expires_at < now
    ).all()
    
    cleaned_count = 0
    freed_space = 0
    
    for file_record in expired_files:
        if file_record.storage_path and os.path.exists(file_record.storage_path):
            try:
                size = os.path.getsize(file_record.storage_path)
                os.remove(file_record.storage_path)
                freed_space += size
            except Exception as e:
                print(f"删除物理文件失败: {e}")
        
        file_record.status = 'expired'
        cleaned_count += 1
    
    db.session.commit()
    
    log = OperationLog(
        user_id=admin_user.id,
        username=admin_user.username,
        operation_type='manual_cleanup',
        target_type='system',
        details=json_module.dumps({
            'cleaned_count': cleaned_count,
            'freed_space': freed_space
        }),
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({
        'message': '清理完成',
        'cleaned_count': cleaned_count,
        'freed_space': _format_size(freed_space)
    }), 200


# ==================== 辅助函数 ====================

def _format_size(size):
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"


def _get_storage_info():
    """获取存储目录使用情况"""
    from config import Config
    
    upload_folder = Config.UPLOAD_FOLDER
    info = {
        'upload_folder': upload_folder,
        'exists': os.path.exists(upload_folder)
    }
    
    if info['exists']:
        try:
            total = sum(
                os.path.getsize(os.path.join(dirpath, filename))
                for dirpath, dirnames, filenames in os.walk(upload_folder)
                for filename in filenames
            )
            info['used_bytes'] = total
            info['used_display'] = _format_size(total)
        except Exception as e:
            info['error'] = str(e)
    
    return info
