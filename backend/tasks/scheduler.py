"""
定时任务调度器
负责：清理过期文件、自动更新检查等
"""
import os
import time
import threading
import logging
from datetime import datetime, timedelta
from models import db, File, OperationLog

logger = logging.getLogger(__name__)


class TaskScheduler:
    """定时任务调度器"""
    
    def __init__(self, app):
        self.app = app
        self.running = False
        self.thread = None
    
    def start(self):
        """启动定时任务"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("定时任务调度器已启动")
    
    def stop(self):
        """停止定时任务"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("定时任务调度器已停止")
    
    def _run_loop(self):
        """主循环"""
        while self.running:
            try:
                with self.app.app_context():
                    # 执行所有定时任务
                    self._cleanup_expired_files()
                    self._check_for_updates()
                    self._cleanup_old_logs()
                
                # 每小时执行一次
                time.sleep(3600)
                
            except Exception as e:
                logger.error(f"定时任务执行出错: {e}")
                time.sleep(60)  # 出错后等待1分钟再试
    
    def _cleanup_expired_files(self):
        """清理过期文件"""
        try:
            now = datetime.utcnow()
            
            expired_files = File.query.filter(
                File.status == 'active',
                File.expires_at != None,
                File.expires_at < now
            ).all()
            
            cleaned_count = 0
            freed_space = 0
            
            for file_record in expired_files:
                # 删除物理文件
                if file_record.storage_path and os.path.exists(file_record.storage_path):
                    try:
                        size = os.path.getsize(file_record.storage_path)
                        os.remove(file_record.storage_path)
                        freed_space += size
                    except Exception as e:
                        logger.warning(f"删除过期文件失败: {file_record.id}, 错误: {e}")
                
                file_record.status = 'expired'
                cleaned_count += 1
            
            if cleaned_count > 0:
                db.session.commit()
                
                # 记录清理日志
                log = OperationLog(
                    user_id=None,
                    username='system',
                    operation_type='auto_cleanup',
                    target_type='system',
                    details=f"清理了{cleaned_count}个过期文件，释放空间{freed_space}字节"
                )
                db.session.add(log)
                db.session.commit()
                
                logger.info(f"自动清理完成: 删除了{cleaned_count}个过期文件")
            
        except Exception as e:
            logger.error(f"清理过期文件失败: {e}")
            db.session.rollback()
    
    def _check_for_updates(self):
        """检查系统更新（每天凌晨3点执行）"""
        now = datetime.utcnow().hour
        
        if now != 3:  # 只在凌晨3点检查
            return
        
        try:
            from routes.system import _get_current_version, _get_latest_version, _compare_versions
            
            current = _get_current_version()
            latest = _get_latest_version()
            
            if latest and _compare_versions(current, latest) < 0:
                logger.info(f"发现新版本: {current} -> {latest}")
                # 这里可以添加通知逻辑（如邮件通知管理员）
        
        except Exception as e:
            logger.error(f"检查更新失败: {e}")
    
    def _cleanup_old_logs(self):
        """清理旧的操作日志（保留30天）"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            deleted_count = OperationLog.query.filter(
                OperationLog.created_at < cutoff_date
            ).delete()
            
            if deleted_count > 0:
                db.session.commit()
                logger.info(f"清理了{deleted_count}条旧操作日志")
        
        except Exception as e:
            logger.error(f"清理日志失败: {e}")
            db.session.rollback()


# 全局调度器实例（由app.py初始化）
scheduler = None


def init_scheduler(app):
    """初始化并启动定时任务调度器"""
    global scheduler
    scheduler = TaskScheduler(app)
    scheduler.start()
    return scheduler
