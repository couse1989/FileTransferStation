"""
登录限制器 - 防暴力破解
使用数据库存储（支持多worker环境）
"""
from datetime import datetime, timedelta
from models import LoginLog

# 配置
MAX_ATTEMPTS = 5
LOCKOUT_MINUTES = 15  # 15分钟


def record_failed_attempt(ip_address, username=None):
    """记录失败的登录尝试（已通过LoginLog记录，此函数保留兼容）"""
    pass


def is_account_locked(ip_address, username=None):
    """
    检查IP或用户名是否被锁定（基于数据库中的失败登录记录）
    返回:
      - False: 未锁定（失败次数<5）
      - 数字: 当前失败次数（0-4）
      - True: 已锁定（失败次数>=5）
    """
    cutoff_time = datetime.utcnow() - timedelta(minutes=LOCKOUT_MINUTES)
    
    query = LoginLog.query.filter(
        LoginLog.success == False,
        LoginLog.timestamp >= cutoff_time
    )
    
    if username:
        # 检查特定用户名的失败次数
        count = query.filter(LoginLog.username == username).count()
    else:
        # 检查IP的失败次数
        count = query.filter(LoginLog.ip_address == ip_address).count()
    
    if count >= MAX_ATTEMPTS:
        return True
    
    return count if count > 0 else False


def clear_failed_attempts(ip_address):
    """清除失败记录（登录成功时不删除历史日志，仅用于兼容）"""
    pass


def get_remaining_attempts(ip_address):
    """获取剩余尝试次数"""
    cutoff_time = datetime.utcnow() - timedelta(minutes=LOCKOUT_MINUTES)
    
    recent_failures = LoginLog.query.filter(
        LoginLog.ip_address == ip_address,
        LoginLog.success == False,
        LoginLog.timestamp >= cutoff_time
    ).count()
    
    return max(0, MAX_ATTEMPTS - recent_failures)
