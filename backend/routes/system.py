"""
系统管理路由
自动更新、健康检查、版本信息
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import subprocess
import os
import json
from datetime import datetime
from models import db, User, OperationLog

system_bp = Blueprint('system', __name__)


@system_bp.route('/health', methods=['GET'])
def health_check():
    """系统健康检查"""
    from config import Config
    
    status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': _get_current_version(),
        'components': {
            'database': 'ok',
            'storage': 'ok'
        }
    }
    
    # 检查数据库连接
    try:
        db.session.execute(db.text('SELECT 1'))
    except Exception as e:
        status['status'] = 'unhealthy'
        status['components']['database'] = f'error: {str(e)}'
    
    # 检查存储目录
    if not os.path.exists(Config.UPLOAD_FOLDER):
        status['status'] = 'unhealthy'
        status['components']['storage'] = 'not_accessible'
    
    code = 200 if status['status'] == 'healthy' else 503
    return jsonify(status), code


@system_bp.route('/version', methods=['GET'])
def get_version():
    """获取当前版本信息"""
    version_info = {
        'current_version': _get_current_version(),
        'latest_version': None,
        'update_available': False,
        'github_repo': 'couse1989/FileTransferStation',
        'check_time': datetime.utcnow().isoformat()
    }
    
    # 尝试获取最新版本
    try:
        latest = _get_latest_version()
        if latest:
            version_info['latest_version'] = latest
            if _compare_versions(_get_current_version(), latest) < 0:
                version_info['update_available'] = True
    except Exception as e:
        version_info['version_check_error'] = str(e)
    
    return jsonify(version_info), 200


@system_bp.route('/check-update', methods=['POST'])
@jwt_required()
def check_for_update():
    """手动检查更新（需要管理员权限）"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or not user.is_admin:
        return jsonify({'error': '需要管理员权限'}), 403
    
    current = _get_current_version()
    
    try:
        latest = _get_latest_version()
        
        result = {
            'current_version': current,
            'latest_version': latest,
            'update_available': False,
            'message': ''
        }
        
        if not latest:
            result['message'] = '无法从GitHub获取版本信息'
        elif _compare_versions(current, latest) < 0:
            result['update_available'] = True
            result['message'] = f'发现新版本: {latest}'
        else:
            result['message'] = '当前已是最新版本'
        
        # 记录日志
        log = OperationLog(
            user_id=current_user_id,
            username=user.username,
            operation_type='check_update',
            target_type='system',
            details=json.dumps(result),
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'current_version': current,
            'error': f'检查更新失败: {str(e)}'
        }), 500


@system_bp.route('/update', methods=['POST'])
@jwt_required()
def perform_update():
    """执行系统更新（管理员）"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or not user.is_admin:
        return jsonify({'error': '需要管理员权限'}), 403
    
    # 检查是否已经是最新
    current = _get_current_version()
    try:
        latest = _get_latest_version()
        
        if latest and _compare_versions(current, latest) >= 0:
            return jsonify({
                'message': '当前已是最新版本，无需更新',
                'current_version': current,
                'latest_version': latest
            }), 200
    except:
        pass  # 即使检查失败也继续尝试更新
    
    # 执行更新
    project_dir = '/opt/filetransfer'
    
    try:
        # 1. 备份数据库文件（以防万一）
        backup_dir = os.path.join(project_dir, '.backup')
        os.makedirs(backup_dir, exist_ok=True)
        
        import shutil
        db_file = os.path.join(project_dir, 'filetransfer.db')
        if os.path.exists(db_file):
            backup_name = f"filetransfer.db.bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(db_file, os.path.join(backup_dir, backup_name))
        
        # 2. Git拉取更新
        result = subprocess.run(
            ['git', 'pull', 'origin', 'main'],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            return jsonify({
                'error': 'Git拉取失败',
                'details': result.stderr
            }), 500
        
        # 3. 安装新的依赖（如果有变化）
        requirements_file = os.path.join(project_dir, 'requirements.txt')
        if os.path.exists(requirements_file):
            pip_result = subprocess.run(
                ['pip', 'install', '-r', requirements_file],
                capture_output=True,
                text=True,
                timeout=300
            )
            # 依赖安装失败不阻止更新，只记录警告
        
        # 4. 重启服务（通过systemctl）
        restart_result = subprocess.run(
            ['sudo', 'systemctl', 'restart', 'filetransfer'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        new_version = _get_current_version()
        
        # 记录日志
        log = OperationLog(
            user_id=current_user_id,
            username=user.username,
            operation_type='system_update',
            target_type='system',
            details=json.dumps({
                'old_version': current,
                'new_version': new_version,
                'git_output': result.stdout[:500]
            }),
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'message': '系统更新成功，正在重启...',
            'old_version': current,
            'new_version': new_version,
            'git_output': result.stdout[:200] if result.stdout else '无输出'
        }), 200
        
    except subprocess.TimeoutExpired:
        return jsonify({'error': '更新超时，请手动检查'}), 504
    except Exception as e:
        return jsonify({'error': f'更新失败: {str(e)}'}), 500


# ==================== 辅助函数 ====================

def _get_current_version():
    """获取当前版本（从VERSION文件或git tag）"""
    project_dir = '/opt/filetransfer'
    
    # 尝试从VERSION文件读取
    version_file = os.path.join(project_dir, 'VERSION')
    if os.path.exists(version_file):
        with open(version_file, 'r') as f:
            return f.read().strip()
    
    # 尝试从git tag获取
    try:
        result = subprocess.run(
            ['git', 'describe', '--tags', '--always'],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except:
        pass
    
    return 'unknown'


def _get_latest_version():
    """从GitHub获取最新版本"""
    import requests
    
    repo = 'couse1989/FileTransferStation'
    url = f'https://api.github.com/repos/{repo}/releases/latest'
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('tag_name', data.get('name'))
        else:
            # 如果没有releases，尝试从分支获取commit info
            url = f'https://api.github.com/repos/{repo}/commits/main'
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                sha = data.get('sha', '')[:7]
                date = data.get('commit', {}).get('author', {}).get('date', '')[:10]
                return f"{sha} ({date})"
    except Exception as e:
        print(f"获取GitHub版本失败: {e}")
    
    return None


def _compare_versions(v1, v2):
    """
    比较两个版本号
    返回：负数表示v1< v2，0表示相等，正数表示v1>v2
    简单实现，支持 x.y.z 格式和纯日期格式
    """
    def normalize(v):
        # 移除可能的前缀 v
        v = v.lower().replace('v', '')
        
        # 如果是日期格式 (2024-01-15)
        if '-' in v and len(v.split('-')) == 3:
            return tuple(int(x) for x in v.split('-'))
        
        # 标准版本号格式 (1.2.3)
        parts = []
        for part in v.split('.'):
            try:
                parts.append(int(part))
            except ValueError:
                parts.append(0)
        
        # 补齐长度
        while len(parts) < 3:
            parts.append(0)
        
        return tuple(parts)
    
    try:
        n1, n2 = normalize(v1), normalize(v2)
        
        # 长度不同时补齐
        max_len = max(len(n1), len(n2))
        n1 = n1 + (0,) * (max_len - len(n1))
        n2 = n2 + (0,) * (max_len - len(n2))
        
        if n1 < n2:
            return -1
        elif n1 > n2:
            return 1
        else:
            return 0
    except:
        return 0
