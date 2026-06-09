"""
文件管理路由
上传、下载、删除、续期、预览等
"""
from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
import json as json_module
import hashlib
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from models import db, User, File, FileChunk, OperationLog

files_bp = Blueprint('files', __name__)


@files_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_file():
    """上传文件（普通上传，<100MB）"""
    current_user_id = get_jwt_identity()
    
    if 'file' not in request.files:
        return jsonify({'error': '请选择文件'}), 400
    
    file = request.files['file']
    if not file.filename:
        return jsonify({'error': '文件名为空'}), 400
    
    try:
        # 获取上传参数
        access_type = request.form.get('access_type', 'public')
        expiry_hours = int(request.form.get('expiry_hours', 24))
        allowed_users = request.form.get('allowed_users')  # JSON字符串
        
        # 验证参数
        if access_type not in ['public', 'code', 'private']:
            return jsonify({'error': '无效的访问类型'}), 400
        
        if expiry_hours < 1 or expiry_hours > 720:
            return jsonify({'error': '保留时间必须在1-720小时之间'}), 400
        
        # 检查文件大小
        from config import Config
        file.seek(0, 2)  # 移到文件末尾
        file_size = file.tell()
        file.seek(0)  # 重置到开头
        
        if file_size > Config.MAX_CONTENT_LENGTH:
            return jsonify({'error': '文件过大，最大允许10GB'}), 413
        
        # 大文件需要分块上传
        if file_size >= Config.LARGE_FILE_THRESHOLD:
            return jsonify({
                'error': '大文件请使用分块上传接口',
                'need_chunked': True,
                'threshold': Config.LARGE_FILE_THRESHOLD
            }), 413
        
        # 生成随机存储名和路径
        stored_name = File.generate_stored_name()
        original_name = secure_filename(file.filename)
        
        # 创建日期子目录（方便管理）
        date_dir = datetime.now().strftime('%Y/%m/%d')
        storage_dir = os.path.join(Config.UPLOAD_FOLDER, date_dir)
        os.makedirs(storage_dir, exist_ok=True)
        
        storage_path = os.path.join(storage_dir, stored_name)
        
        # 计算MD5
        md5_hash = hashlib.md5()
        while chunk := file.read(8192):
            md5_hash.update(chunk)
        file.seek(0)
        
        # 保存文件
        file.save(storage_path)
        
        # 处理提取码
        extract_code = None
        if access_type == 'code':
            extract_code = File.generate_extract_code()
        
        # 处理允许的用户列表
        allowed_user_ids = None
        if access_type == 'private' and allowed_users:
            try:
                allowed_user_ids = json_module.loads(allowed_users)
                if isinstance(allowed_user_ids, list):
                    allowed_user_ids = json_module.dumps([int(uid) for uid in allowed_user_ids])
            except:
                pass
        
        # 计算过期时间
        expires_at = datetime.utcnow() + timedelta(hours=expiry_hours)
        
        # 创建数据库记录
        user = User.query.get(current_user_id)
        new_file = File(
            original_name=original_name,
            stored_name=stored_name,
            file_size=file_size,
            mime_type=file.content_type or 'application/octet-stream',
            file_hash=md5_hash.hexdigest(),
            storage_path=storage_path,
            access_type=access_type,
            extract_code=extract_code,
            allowed_users=allowed_user_ids,
            uploaded_by=current_user_id,
            expires_at=expires_at,
            status='active'
        )
        
        db.session.add(new_file)
        db.session.commit()
        
        # 记录操作日志
        log = OperationLog(
            user_id=current_user_id,
            username=user.username,
            operation_type='upload',
            target_type='file',
            target_id=new_file.id,
            details=json_module.dumps({
                'filename': original_name,
                'size': file_size,
                'access_type': access_type
            }),
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        result = new_file.to_dict(include_code=True)
        result['message'] = '上传成功'
        
        return jsonify(result), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'上传失败: {str(e)}'}), 500


@files_bp.route('/upload/init', methods=['POST'])
@jwt_required()
def init_chunked_upload():
    """初始化分块上传（大文件，>=100MB）"""
    current_user_id = get_jwt_identity()
    
    data = request.get_json()
    
    filename = data.get('filename')
    file_size = data.get('file_size')
    mime_type = data.get('mime_type', 'application/octet-stream')
    access_type = data.get('access_type', 'public')
    expiry_hours = int(data.get('expiry_hours', 24))
    allowed_users = data.get('allowed_users')
    
    if not all([filename, file_size]):
        return jsonify({'error': '缺少必要参数'}), 400
    
    from config import Config
    
    if file_size > Config.MAX_CONTENT_LENGTH:
        return jsonify({'error': '文件过大，最大允许10GB'}), 413
    
    if file_size < Config.LARGE_FILE_THRESHOLD:
        return jsonify({'error': '小文件请使用普通上传接口'}), 400
    
    # 生成上传ID和存储信息
    upload_id = File.generate_stored_name()
    stored_name = f"{upload_id}_{secure_filename(filename)}"
    
    # 计算分块数量
    chunk_total = (file_size + Config.CHUNK_SIZE - 1) // Config.CHUNK_SIZE
    
    # 创建分块临时目录
    chunks_dir = os.path.join(Config.UPLOAD_FOLDER, '.chunks', upload_id)
    os.makedirs(chunks_dir, exist_ok=True)
    
    # 处理提取码
    extract_code = None
    if access_type == 'code':
        extract_code = File.generate_extract_code()
    
    # 处理允许的用户列表
    allowed_user_ids = None
    if access_type == 'private' and allowed_users:
        try:
            allowed_user_ids = json_module.dumps([int(uid) for uid in allowed_users])
        except:
            pass
    
    # 计算过期时间
    expires_at = datetime.utcnow() + timedelta(hours=expiry_hours)
    
    # 创建数据库记录（状态为 uploading）
    user = User.query.get(current_user_id)
    new_file = File(
        original_name=secure_filename(filename),
        stored_name=stored_name,
        file_size=file_size,
        mime_type=mime_type,
        storage_path='',  # 稍后更新
        access_type=access_type,
        extract_code=extract_code,
        allowed_users=allowed_user_ids,
        uploaded_by=current_user_id,
        uploaded_at=datetime.utcnow(),
        expires_at=expires_at,
        is_chunked=True,
        chunk_total=chunk_total,
        chunk_uploaded=0,
        status='uploading'
    )
    
    db.session.add(new_file)
    db.session.commit()
    
    return jsonify({
        'upload_id': upload_id,
        'file_id': new_file.id,
        'chunk_size': Config.CHUNK_SIZE,
        'chunk_total': chunk_total,
        'message': '分块上传已初始化'
    }), 200


@files_bp.route('/upload/chunk', methods=['POST'])
@jwt_required()
def upload_chunk():
    """上传文件块"""
    current_user_id = get_jwt_identity()
    
    if 'chunk' not in request.files:
        return jsonify({'error': '缺少文件块数据'}), 400
    
    chunk = request.files['chunk']
    upload_id = request.form.get('upload_id')
    chunk_index = int(request.form.get('chunk_index'))
    file_id = int(request.form.get('file_id'))
    
    if not all([upload_id, chunk_index is not None, file_id]):
        return jsonify({'error': '缺少必要参数'}), 400
    
    from config import Config
    
    # 验证文件记录
    file_record = File.query.get(file_id)
    if not file_record or file_record.uploaded_by != current_user_id:
        return jsonify({'error': '文件不存在或无权限'}), 404
    
    # 保存文件块
    chunk_path = os.path.join(Config.UPLOAD_FOLDER, '.chunks', upload_id, f'part_{chunk_index}')
    chunk.save(chunk_path)
    
    # 更新或创建分块记录
    chunk_record = FileChunk.query.filter_by(file_id=file_id, chunk_index=chunk_index).first()
    if not chunk_record:
        chunk_record = FileChunk(
            file_id=file_id,
            chunk_index=chunk_index,
            chunk_path=chunk_path,
            chunk_size=os.path.getsize(chunk_path),
            status='completed'
        )
        db.session.add(chunk_record)
    else:
        chunk_record.chunk_path = chunk_path
        chunk_record.chunk_size = os.path.getsize(chunk_path)
        chunk_record.status='completed'
        db.session.commit()
    
    # 更新已上传块数
    completed_chunks = FileChunk.query.filter_by(file_id=file_id, status='completed').count()
    file_record.chunk_uploaded = completed_chunks
    db.session.commit()
    
    return jsonify({
        'message': '块上传成功',
        'chunk_index': chunk_index,
        'uploaded': completed_chunks,
        'total': file_record.chunk_total
    }), 200


@files_bp.route('/upload/complete', methods=['POST'])
@jwt_required()
def complete_upload():
    """完成分块上传，合并文件块"""
    current_user_id = get_jwt_identity()
    
    data = request.get_json()
    file_id = data.get('file_id')
    upload_id = data.get('upload_id')
    
    if not all([file_id, upload_id]):
        return jsonify({'error': '缺少必要参数'}), 400
    
    from config import Config
    
    # 查找文件记录
    file_record = File.query.get(file_id)
    if not file_record or file_record.uploaded_by != current_user_id:
        return jsonify({'error': '文件不存在或无权限'}), 404
    
    # 检查所有块是否都上传完成
    uploaded_chunks = FileChunk.query.filter_by(file_id=file_id, status='completed').order_by(FileChunk.chunk_index).all()
    
    if len(uploaded_chunks) != file_record.chunk_total:
        return jsonify({
            'error': f'还有 {file_record.chunk_total - len(uploaded_chunks)} 个块未上传',
            'uploaded': len(uploaded_chunks),
            'total': file_record.chunk_total
        }), 400
    
    # 合并文件块
    date_dir = datetime.now().strftime('%Y/%m/%d')
    storage_dir = os.path.join(Config.UPLOAD_FOLDER, date_dir)
    os.makedirs(storage_dir, exist_ok=True)
    
    final_path = os.path.join(storage_dir, file_record.stored_name)
    md5_hash = hashlib.md5()
    
    with open(final_path, 'wb') as final_file:
        for chunk in uploaded_chunks:
            with open(chunk.chunk_path, 'rb') as chunk_file:
                while piece := chunk_file.read(8192):
                    md5_hash.update(piece)
                    final_file.write(piece)
    
    # 更新文件记录
    file_record.storage_path = final_path
    file_record.file_hash = md5_hash.hexdigest()
    file_record.status = 'active'
    db.session.commit()
    
    # 清理临时分块文件
    import shutil
    chunks_dir = os.path.join(Config.UPLOAD_FOLDER, '.chunks', upload_id)
    if os.path.exists(chunks_dir):
        shutil.rmtree(chunks_dir)
    
    # 删除分块记录
    FileChunk.query.filter_by(file_id=file_id).delete()
    db.session.commit()
    
    # 记录操作日志
    user = User.query.get(current_user_id)
    log = OperationLog(
        user_id=current_user_id,
        username=user.username,
        operation_type='upload',
        target_type='file',
        target_id=file_id,
        details=json_module.dumps({
            'filename': file_record.original_name,
            'size': file_record.file_size,
            'access_type': file_record.access_type,
            'chunked': True
        }),
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
    result = file_record.to_dict(include_code=True)
    result['message'] = '上传成功'
    
    return jsonify(result), 201


@files_bp.route('/list', methods=['GET'])
@jwt_required()
def list_files():
    """获取当前用户的文件列表"""
    current_user_id = get_jwt_identity()
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '')
    
    query = File.query.filter_by(uploaded_by=current_user_id)
    
    # 搜索过滤
    if search:
        query = query.filter(File.original_name.ilike(f'%{search}%'))
    
    # 状态过滤
    if status:
        query = query.filter_by(status=status)
    
    # 排序：最新上传在前
    query = query.order_by(File.uploaded_at.desc())
    
    # 分页
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    files_data = []
    for file_item in pagination.items:
        # 检查是否过期
        is_expired = file_item.expires_at and file_item.expires_at < datetime.utcnow()
        file_dict = file_item.to_dict(include_code=True)
        file_dict['is_expired'] = is_expired
        files_data.append(file_dict)
    
    return jsonify({
        'files': files_data,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    }), 200


@files_bp.route('/<int:file_id>', methods=['GET'])
@jwt_required()
def get_file_info(file_id):
    """获取文件详情"""
    current_user_id = get_jwt_identity()
    
    file_record = File.query.get_or_404(file_id)
    
    # 检查权限：只能查看自己的文件
    if file_record.uploaded_by != current_user_id:
        return jsonify({'error': '无权限访问此文件'}), 403
    
    is_expired = file_record.expires_at and file_record.expires_at < datetime.utcnow()
    file_dict = file_record.to_dict(include_code=True)
    file_dict['is_expired'] = is_expired
    
    return jsonify(file_dict), 200


@files_bp.route('/download/<int:file_id>', methods=['GET'])
@jwt_required()
def download_file(file_id):
    """下载文件（需验证权限）"""
    current_user_id = get_jwt_identity()
    
    file_record = File.query.get_or_404(file_id)
    
    # 检查文件是否存在
    if not os.path.exists(file_record.storage_path):
        return jsonify({'error': '文件不存在'}), 404
    
    # 检查是否过期
    if file_record.status == 'expired' or \
       (file_record.expires_at and file_record.expires_at < datetime.utcnow()):
        file_record.status = 'expired'
        db.session.commit()
        return jsonify({'error': '文件已过期'}), 410
    
    # 检查下载权限
    has_access = False
    
    if file_record.access_type == 'public':
        has_access = True
    elif file_record.access_type == 'private':
        # 指定用户模式
        if file_record.allowed_users:
            allowed = json_module.loads(file_record.allowed_users)
            if current_user_id in allowed:
                has_access = True
        # 上传者始终可以下载
        if file_record.uploaded_by == current_user_id:
            has_access = True
    
    if not has_access:
        return jsonify({'error': '无权限下载此文件'}), 403
    
    # 增加下载计数
    file_record.download_count += 1
    db.session.commit()
    
    # 记录操作日志
    user = User.query.get(current_user_id)
    log = OperationLog(
        user_id=current_user_id,
        username=user.username,
        operation_type='download',
        target_type='file',
        target_id=file_id,
        details=json_module.dumps({'filename': file_record.original_name}),
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
    # 发送文件
    return send_file(
        file_record.storage_path,
        as_attachment=True,
        download_name=file_record.original_name
    )


@files_bp.route('/download/public/<int:file_id>', methods=['GET'])
def download_public(file_id):
    """公开下载文件（无需登录，仅限access_type=public的文件）"""
    file_record = db.session.get(File, file_id)
    
    if not file_record:
        return jsonify({'error': '文件不存在'}), 404
    
    # 只有公开文件才能通过此接口下载
    if file_record.access_type != 'public':
        return jsonify({'error': '此文件需要登录才能下载'}), 403
    
    # 检查状态
    if file_record.status in ('expired', 'deleted'):
        return jsonify({'error': '文件已过期或已删除'}), 410
    
    # 检查过期时间
    if file_record.expires_at and file_record.expires_at < datetime.utcnow():
        file_record.status = 'expired'
        db.session.commit()
        return jsonify({'error': '文件已过期'}), 410
    
    # 检查文件是否存在
    if not file_record.storage_path or not os.path.exists(file_record.storage_path):
        return jsonify({'error': '文件不存在'}), 404
    
    # 增加下载计数
    file_record.download_count += 1
    db.session.commit()
    
    # 记录日志
    log = OperationLog(
        user_id=None,
        username='anonymous',
        operation_type='download_public',
        target_type='file',
        target_id=file_record.id,
        details=json_module.dumps({'filename': file_record.original_name}),
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
    return send_file(
        file_record.storage_path,
        as_attachment=True,
        download_name=file_record.original_name
    )


@files_bp.route('/download/code/<extract_code>', methods=['GET'])
def download_by_code(extract_code):
    """通过提取码下载文件（无需登录）"""
    file_record = File.query.filter_by(extract_code=extract_code.upper(), status='active').first()
    
    if not file_record:
        return jsonify({'error': '提取码错误或文件不存在'}), 404
    
    # 检查是否过期
    if file_record.expires_at and file_record.expires_at < datetime.utcnow():
        file_record.status = 'expired'
        db.session.commit()
        return jsonify({'error': '文件已过期'}), 410
    
    # 检查文件是否存在
    if not os.path.exists(file_record.storage_path):
        return jsonify({'error': '文件不存在'}), 404
    
    # 增加下载计数
    file_record.download_count += 1
    db.session.commit()
    
    # 匿名下载也记录日志
    log = OperationLog(
        user_id=None,
        username='anonymous',
        operation_type='download_by_code',
        target_type='file',
        target_id=file_record.id,
        details=json_module.dumps({
            'filename': file_record.original_name,
            'extract_code': extract_code
        }),
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
    return send_file(
        file_record.storage_path,
        as_attachment=True,
        download_name=file_record.original_name
    )


@files_bp.route('/preview/<int:file_id>', methods=['GET'])
@jwt_required()
def preview_file(file_id):
    """预览文件（仅支持图片、文本、PDF）"""
    current_user_id = get_jwt_identity()
    
    file_record = File.query.get_or_404(file_id)
    
    # 权限检查（与下载相同）
    if file_record.uploaded_by != current_user_id:
        return jsonify({'error': '无权预览此文件'}), 403
    
    if file_record.status == 'expired' or \
       (file_record.expires_at and file_record.expires_at < datetime.utcnow()):
        return jsonify({'error': '文件已过期'}), 410
    
    if not os.path.exists(file_record.storage_path):
        return jsonify({'error': '文件不存在'}), 404
    
    # 支持的预览类型
    preview_types = [
        'image/',  # 所有图片格式
        'text/plain',
        'text/markdown',
        'application/json',
        'application/pdf',
        'text/csv',
        'text/html'
    ]
    
    can_preview = any(file_record.mime_type.startswith(t) for t in preview_types)
    
    if not can_preview:
        return jsonify({'error': '该文件类型不支持在线预览'}), 400
    
    return send_file(file_record.storage_path)


@files_bp.route('/renew/<int:file_id>', methods=['POST'])
@jwt_required()
def renew_file(file_id):
    """延长文件保留时间"""
    current_user_id = get_jwt_identity()
    
    data = request.get_json()
    additional_hours = int(data.get('additional_hours', 24))
    
    if additional_hours < 1 or additional_hours > 720:
        return jsonify({'error': '延长时间必须在1-720小时之间'}), 400
    
    file_record = File.query.get_or_404(file_id)
    
    # 只有上传者可以续期
    if file_record.uploaded_by != current_user_id:
        return jsonify({'error': '只有上传者可以续期'}), 403
    
    # 续期
    if file_record.expires_at:
        if file_record.expires_at < datetime.utcnow():
            # 已过期，从现在开始计算
            file_record.expires_at = datetime.utcnow() + timedelta(hours=additional_hours)
            file_record.status = 'active'
        else:
            # 未过期，在原基础上增加
            file_record.expires_at = file_record.expires_at + timedelta(hours=additional_hours)
    else:
        file_record.expires_at = datetime.utcnow() + timedelta(hours=additional_hours)
    
    db.session.commit()
    
    # 记录日志
    user = User.query.get(current_user_id)
    log = OperationLog(
        user_id=current_user_id,
        username=user.username,
        operation_type='renew',
        target_type='file',
        target_id=file_id,
        details=json_module.dumps({
            'filename': file_record.original_name,
            'additional_hours': additional_hours
        }),
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({
        'message': '续期成功',
        'new_expires_at': file_record.expires_at.isoformat(),
        'file': file_record.to_dict()
    }), 200


@files_bp.route('/<int:file_id>', methods=['DELETE'])
@jwt_required()
def delete_file(file_id):
    """删除文件"""
    current_user_id = get_jwt_identity()
    
    file_record = File.query.get_or_404(file_id)
    
    # 只能删除自己的文件
    if file_record.uploaded_by != current_user_id:
        return jsonify({'error': '只能删除自己的文件'}), 403
    
    # 删除物理文件
    if os.path.exists(file_record.storage_path):
        try:
            os.remove(file_record.storage_path)
        except Exception as e:
            print(f"删除物理文件失败: {e}")
    
    # 更新状态
    file_record.status = 'deleted'
    db.session.commit()
    
    # 记录日志
    user = User.query.get(current_user_id)
    log = OperationLog(
        user_id=current_user_id,
        username=user.username,
        operation_type='delete',
        target_type='file',
        target_id=file_id,
        details=json_module.dumps({'filename': file_record.original_name}),
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({'message': '文件已删除'}), 200


@files_bp.route('/batch-download', methods=['POST'])
@jwt_required()
def batch_download():
    """批量下载文件（打包成ZIP）"""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    file_ids = data.get('file_ids', [])
    
    if not file_ids:
        return jsonify({'error': '请选择要下载的文件'}), 400
    
    import zipfile
    import tempfile
    
    # 创建临时ZIP文件
    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    
    try:
        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_id in file_ids:
                file_record = File.query.get(file_id)
                
                if not file_record:
                    continue
                
                # 权限检查
                if file_record.uploaded_by != current_user_id:
                    continue
                
                # 过期检查
                if file_record.status in ['expired', 'deleted']:
                    continue
                if file_record.expires_at and file_record.expires_at < datetime.utcnow():
                    continue
                
                # 文件存在性检查
                if not os.path.exists(file_record.storage_path):
                    continue
                
                # 添加到ZIP
                zipf.write(
                    file_record.storage_path,
                    arcname=file_record.original_name
                )
                
                # 增加下载计数
                file_record.download_count += 1
            
            db.session.commit()
        
        # 记录日志
        user = User.query.get(current_user_id)
        log = OperationLog(
            user_id=current_user_id,
            username=user.username,
            operation_type='batch_download',
            target_type='file',
            details=json_module.dumps({'file_count': len(file_ids)}),
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        return send_file(
            temp_zip.name,
            as_attachment=True,
            download_name=f'batch_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
        )
        
    except Exception as e:
        if os.path.exists(temp_zip.name):
            os.unlink(temp_zip.name)
        return jsonify({'error': f'打包失败: {str(e)}'}), 500
