"""
登录限制器 - 防暴力破解
使用数据库存储（支持多worker环境）
"""
import time
from datetime import datetime, timedelta
from models import db, LoginLog

# 配置
MAX_ATTEMPTS = 5
LOCKOUT_TIME = 900  # 15分钟（秒）


def record_failed_attempt(ip_address, username=None):
    """记录失败的登录尝试（已通过LoginLog记录，此函数保留兼容）"""
    pass


def is_account_locked(ip_address):
    """
    检查IP是否被锁定（基于数据库中的失败登录记录）
    返回:
      - False: 未锁定
      - True: 已锁定（失败次数>=5）
      - 正数: 当前失败次数
    """
    cutoff_time = datetime.utcnow() - timedelta(seconds=LOCKOUT_TIME)
    
    recent_failures = LoginLog.query.filter(
        LoginLog.ip_address == ip_address,
        LoginLog.success == False,
        LoginLog.login_time >= cutoff_time
    ).count()
    
    if recent_failures >= MAX_ATTEMPTS:
        return True
    
    return recent_failures if recent_failures > 0 else False


def clear_failed_attempts(ip_address):
    """清除失败记录（通过标记旧记录，登录成功时不删除历史日志）"""
    pass


def get_remaining_attempts(ip_address):
    """获取剩余尝试次数"""
    cutoff_time = datetime.utcnow() - timedelta(seconds=LOCKOUT_TIME)
    
    recent_failures = LoginLog.query.filter(
        LoginLog.ip_address == ip_address,
        LoginLog.success == False,
        LoginLog.login_time >= cutoff_time
    ).count()
    
    return max(0, MAX_ATTEMPTS - recent_failures)
