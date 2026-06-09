"""
生产环境启动入口
使用Gunicorn运行
"""

# 如果直接运行此文件，则使用Flask开发服务器
if __name__ == '__main__':
    from app import create_app
    
    app = create_app()
    
    # 启动定时任务
    from tasks.scheduler import init_scheduler
    init_scheduler(app)
    
    app.run(host='0.0.0.0', port=3000, debug=False)
