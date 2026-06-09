"""
认证相关路由
登录、登出、Token刷新、验证码
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import random
import string
from models import db, User, LoginLog, OperationLog
from utils.rate_limiter import is_account_locked, record_failed_attempt, clear_failed_attempts

auth_bp = Blueprint('auth', __name__)

# 存储验证码（生产环境应使用Redis）
captcha_store = {}

def generate_captcha_text(length=4):
    """生成验证码文本"""
    chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    return ''.join(random.choices(chars, k=length))

@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': '用户名和密码不能为空'}), 400
    
    username = data['username'].strip()
    password = data['password']
    ip_address = request.remote_addr
    user_agent = request.user_agent.string if request.user_agent else None
    
    # 查找用户
    user = User.query.filter_by(username=username).first()
    
    # 记录登录尝试（无论用户是否存在）
    if not user:
        log = LoginLog(
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            fail_reason='user_not_found'
        )
        db.session.add(log)
        db.session.commit()
        
        # 为了安全，不明确提示用户不存在
        # 检查是否需要验证码（基于IP）
        if is_account_locked(ip_address):
            return jsonify({'error': '需要验证码', 'require_captcha': True}), 403
        
        return jsonify({'error': '用户名或密码错误'}), 401
    
    # 检查账户是否被锁定
    if not user.is_active:
        log = LoginLog(
            user_id=user.id,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            fail_reason='account_disabled'
        )
        db.session.add(log)
        db.session.commit()
        return jsonify({'error': '账户已被禁用，请联系管理员'}), 403
    
    # 检查IP是否被临时锁定
    if is_account_locked(ip_address):
        # 验证验证码
        captcha = data.get('captcha')
        captcha_key = f"{ip_address}_{data.get('captcha_key', '')}"
        
        if not captcha or captcha_store.get(captcha_key) != captcha.upper():
            return jsonify({
                'error': '验证码错误或已过期',
                'require_captcha': True,
                'need_new_captcha': True
            }), 403
        else:
            # 验证码正确，清除该次记录
            del captcha_store[captcha_key]
    
    # 验证密码
    if user.check_password(password):
        # 登录成功
        clear_failed_attempts(ip_address)
        
        # 更新最后登录时间
        user.last_login = datetime.utcnow()
        user.last_login_ip = ip_address
        db.session.commit()
        
        # 记录日志
        log = LoginLog(
            user_id=user.id,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True
        )
        db.session.add(log)
        db.session.commit()
        
        # 生成Token
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)
        
        return jsonify({
            'message': '登录成功',
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user.to_dict()
        }), 200
    else:
        # 登录失败
        record_failed_attempt(ip_address, username)
        
        fail_count = is_account_locked(ip_address)
        need_captcha = fail_count >= 3
        
        log = LoginLog(
            user_id=user.id,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            success=False,
            fail_reason='invalid_password'
        )
        db.session.add(log)
        db.session.commit()
        
        response_data = {
            'error': '用户名或密码错误',
            'require_captcha': need_captcha,
            'remaining_attempts': max(0, 5 - (fail_count if fail_count else 1))
        }
        
        if need_captcha:
            response_data['need_new_captcha'] = True
        
        return jsonify(response_data), 401


@auth_bp.route('/captcha', methods=['GET'])
def get_captcha():
    """获取验证码"""
    from io import BytesIO
    import base64
    from PIL import Image, ImageDraw, ImageFont
    
    ip_address = request.remote_addr
    
    # 生成验证码文本
    text = generate_captcha_text(4)
    key = f"{ip_address}_{random.randint(1000, 9999)}"
    
    # 存储验证码（5分钟有效期）
    captcha_store[key] = text.upper()
    # 清理过期的验证码（简单实现）
    if len(captcha_store) > 1000:
        keys_to_remove = list(captcha_store.keys())[:-500]
        for k in keys_to_remove:
            del captcha_store[k]
    
    # 生成验证码图片
    width, height = 120, 50
    image = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
    except:
        font = ImageFont.load_default()
    
    # 绘制干扰线
    for _ in range(5):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=(random.randint(0, 155), random.randint(0, 155), random.randint(0, 155)))
    
    # 绘制文字
    text_width = draw.textlength(text, font=font)
    x = (width - text_width) / 2
    y = (height - 36) / 2
    
    for i, char in enumerate(text):
        char_color = (random.randint(0, 100), random.randint(0, 100), random.randint(0, 100))
        draw.text((x + i * 25, y), char, fill=char_color, font=font)
    
    # 转换为base64
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return jsonify({
        'captcha_image': f'data:image/png;base64,{img_str}',
        'captcha_key': key
    })


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """刷新Token"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or not user.is_active:
        return jsonify({'error': '用户不存在或已被禁用'}), 401
    
    new_token = create_access_token(identity=current_user_id)
    return jsonify({'access_token': new_token}), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """获取当前用户信息"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    
    return jsonify(user.to_dict()), 200


@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """修改密码"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    data = request.get_json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if not all([old_password, new_password]):
        return jsonify({'error': '旧密码和新密码不能为空'}), 400
    
    if len(new_password) < 6:
        return jsonify({'error': '新密码长度不能小于6位'}), 400
    
    if not user.check_password(old_password):
        return jsonify({'error': '旧密码错误'}), 401
    
    user.set_password(new_password)
    
    # 记录操作日志
    log = OperationLog(
        user_id=current_user_id,
        username=user.username,
        operation_type='change_password',
        target_type='user',
        target_id=current_user_id,
        details='修改密码',
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({'message': '密码修改成功'}), 200


@auth_bp.route('/users', methods=['GET'])
@jwt_required()
def list_active_users():
    """获取活跃用户列表（所有登录用户可用，用于文件分享时选择指定用户）"""
    users = User.query.filter_by(is_active=True).order_by(User.username).all()
    return jsonify({
        'users': [{'id': u.id, 'username': u.username} for u in users]
    }), 200
