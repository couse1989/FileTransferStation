"""
WSGI入口 - 供Gunicorn使用
"""
from app import create_app
from tasks.scheduler import init_scheduler

# 创建Flask应用实例
app = create_app()

# 启动定时任务
with app.app_context():
    init_scheduler(app)

if __name__ == "__main__":
    app.run()
