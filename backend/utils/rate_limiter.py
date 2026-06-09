"""
登录限制器 - 防暴力破解
基于内存实现（生产环境建议使用Redis）
"""
import time
from collections import defaultdict

# 存储登录失败记录 {ip: [(timestamp, username), ...]}
_failed_attempts = defaultdict(list)

# 配置
MAX_ATTEMPTS = 5
LOCKOUT_TIME = 900  # 15分钟（秒）


def record_failed_attempt(ip_address, username=None):
    """记录一次失败的登录尝试"""
    _failed_attempts[ip_address].append({
        'timestamp': time.time(),
        'username': username
    })
    
    # 清理过期的记录
    _cleanup_old_attempts(ip_address)


def is_account_locked(ip_address):
    """
    检查IP是否被锁定
    返回值：
      - False: 未锁定
      - 正数: 当前失败次数（未达到锁定阈值）
      - True: 已锁定
    """
    _cleanup_old_attempts(ip_address)
    
    attempts = _failed_attempts.get(ip_address, [])
    recent_count = len(attempts)
    
    if recent_count >= MAX_ATTEMPTS:
        return True
    
    return recent_count if recent_count > 0 else False


def clear_failed_attempts(ip_address):
    """清除指定IP的失败记录（登录成功后调用）"""
    if ip_address in _failed_attempts:
        del _failed_attempts[ip_address]


def get_remaining_attempts(ip_address):
    """获取剩余尝试次数"""
    attempts = len(_failed_attempts.get(ip_address, []))
    return max(0, MAX_ATTEMPTS - attempts)


def _cleanup_old_attempts(ip_address):
    """清理过期的失败记录"""
    if ip_address not in _failed_attempts:
        return
    
    current_time = time.time()
    
    # 只保留最近 LOCKOUT_TIME 秒内的记录
    _failed_attempts[ip_address] = [
        attempt for attempt in _failed_attempts[ip_address]
        if current_time - attempt['timestamp'] < LOCKOUT_TIME
    ]
    
    # 如果没有记录了，删除该IP的条目
    if not _failed_attempts[ip_address]:
        del _failed_attempts[ip_address]
