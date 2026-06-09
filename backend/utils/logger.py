"""
日志工具 - 带轮转功能的日志系统
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

# 日志配置
def setup_logging(app):
    """配置应用日志系统"""
    from config import Config
    
    log_dir = Config.LOG_FOLDER
    os.makedirs(log_dir, exist_ok=True)
    
    # 主应用日志
    app_handler = RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=Config.LOG_MAX_SIZE,
        backupCount=Config.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    # 错误日志（单独记录）
    error_handler = RotatingFileHandler(
        os.path.join(log_dir, 'error.log'),
        maxBytes=Config.LOG_MAX_SIZE,
        backupCount=Config.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s\n%(pathname)s:%(lineno)d'
    ))
    
    # 访问日志（类似nginx access log）
    access_handler = RotatingFileHandler(
        os.path.join(log_dir, 'access.log'),
        maxBytes=Config.LOG_MAX_SIZE,
        backupCount=Config.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    access_handler.setLevel(logging.INFO)
    access_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(message)s'
    ))
    
    # 添加到Flask logger
    app.logger.addHandler(app_handler)
    app.logger.addHandler(error_handler)
    app.logger.setLevel(logging.INFO)
    
    # 返回访问日志logger，供请求钩子使用
    return access_logger = logging.getLogger('access')
    access_logger.addHandler(access_handler)
    return access_logger


class RequestLogger:
    """请求日志记录器"""
    
    def __init__(self, app=None):
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        self.access_logger = setup_logging(app)
        
        @app.before_request
        def before_request():
            from flask import request
            request.start_time = datetime.utcnow()
        
        @app.after_request
        def after_request(response):
            try:
                duration = (datetime.utcnow() - request.start_time).total_seconds()
                
                log_data = {
                    'method': request.method,
                    'path': request.full_path.split('?')[0],
                    'status': response.status_code,
                    'ip': request.remote_addr,
                    'duration_ms': round(duration * 1000, 2),
                    'user_agent': request.user_agent.string[:200] if request.user_agent else None
                }
                
                self.access_logger.info(
                    f"{log_data['ip']} - "
                    f"{log_data['method']} {log_data['path']} "
                    f"- {log_data['status']} - "
                    f"{log_data['duration_ms']}ms"
                )
            except Exception as e:
                app.logger.error(f'记录访问日志失败: {e}')
            
            return response
