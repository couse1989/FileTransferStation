"""
文件中转站 - 主应用入口
Flask应用工厂模式
"""
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from werkzeug.middleware.proxy_fix import ProxyFix
import os

def create_app(config_class=None):
    """创建Flask应用实例"""
    app = Flask(__name__)
    
    # 处理反向代理（Nginx）传递的真实IP
    # x_for=1: X-Forwarded-For, x_proto=1: X-Forwarded-Proto
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    
    # 加载配置
    if config_class:
        app.config.from_object(config_class)
    else:
        from config import Config
        app.config.from_object(Config)
    
    # 初始化扩展
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    JWTManager(app)
    
    # 确保目录存在
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)
    os.makedirs(app.config.get('LOG_FOLDER', 'logs'), exist_ok=True)
    
    # 初始化数据库
    from models import db
    db.init_app(app)
    
    # 创建数据库表
    with app.app_context():
        db.create_all()
        
        # 创建默认管理员账户（如果不存在）
        from models import User
        try:
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                admin = User(
                    username='admin',
                    is_admin=True,
                    is_active=True
                )
                admin.set_password('Admin@123456')  # 默认密码，首次登录请修改
                db.session.add(admin)
                db.session.commit()
                print("默认管理员账户已创建: admin / Admin@123456")
            else:
                print("管理员账户已存在")
        except Exception as e:
            db.session.rollback()
            print(f"初始化管理员账户时出错: {e}")
            # 继续启动，不阻止应用运行
        
        # 清理过期的验证码
        try:
            from datetime import datetime
            from models import SystemConfig
            cutoff = datetime.utcnow().isoformat()
            SystemConfig.query.filter(
                SystemConfig.key.like('captcha_%'),
                SystemConfig.description < cutoff
            ).delete(synchronize_session=False)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"清理验证码时出错: {e}")
    
    # 注册蓝图
    from routes.auth import auth_bp
    from routes.files import files_bp
    from routes.admin import admin_bp
    from routes.system import system_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(files_bp, url_prefix='/api/files')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(system_bp, url_prefix='/api/system')
    
    # 错误处理
    @app.errorhandler(413)
    def request_entity_too_large(error):
        return {'error': '文件过大，最大允许10GB'}, 413
    
    @app.errorhandler(404)
    def not_found(error):
        return {'error': '接口不存在'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return {'error': '服务器内部错误'}, 500
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=3000, debug=True)
