from flask import Flask, redirect, url_for
from flask_login import current_user
from config import Config
from sqlalchemy import func
import os

# 导入数据库和模型
from app.utils.db_manager import db, User, get_config, set_config
# 导入 LoginManager
from app.utils.login_manager import login_manager
# 导入 APScheduler
from app.utils.scheduler import scheduler

# 导入定时任务函数
# [修改说明] 这里导入的函数现在已经不再需要 app 参数了
from app.modules.data_core.komari_api import run_periodic_static_sync, run_periodic_snapshot_sync

def create_app(config_class=Config):
    # 初始化 Flask 应用
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 1. 初始化插件
    db.init_app(app)
    login_manager.init_app(app)
    
    # 配置未登录时的跳转端点
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录以访问此页面'
    login_manager.login_message_category = 'info'

    # 2. 注册蓝图
    register_blueprints(app)
    
    # 3. 根路由处理 (访问 / 时自动调度)
    @app.route('/')
    def root_redirect():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.index'))
        return redirect(url_for('auth.login'))
    
    # 初始化变量，确保它们在外部可用
    snapshot_interval = 5
    static_sync_interval = 60
    
    # 4. 应用上下文初始化 (数据库与默认设置)
    with app.app_context():
        # 创建表结构
        db.create_all()
        
        # 检查并创建默认管理员
        init_admin_user()

        # 初始化应用配置
        init_default_settings()

        # 安全地读取配置
        try:
            snapshot_interval = int(get_config('ACQUISITION_INTERVAL_MINUTES', 5))
            static_sync_interval = int(get_config('STATIC_SYNC_INTERVAL_MINUTES', 60))
        except (ValueError, TypeError) as e:
            print(f"警告: 配置间隔时间读取失败或格式错误，使用默认值。错误: {e}")
            snapshot_interval = 5
            static_sync_interval = 60
            
    # 5. 初始化并启动调度器
    scheduler.init_app(app)
    
    # 将 app 实例显式绑定到 scheduler 对象上
    # 这样在 komari_api.py 中可以通过 scheduler.app 访问上下文，
    # 而不需要将 app 对象作为参数传递（避免了 PostgreSQL 序列化报错）。
    scheduler.app = app 

    # 防止 Debug 模式下调度器启动两次
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        scheduler.start()
        
        # 注册任务 1: 高频快照
        if not scheduler.get_job('periodic_snapshot_sync'):
            scheduler.add_job(
                id='periodic_snapshot_sync',
                func=run_periodic_snapshot_sync,
                trigger='interval',
                minutes=snapshot_interval,
                max_instances=1,
                replace_existing=True, 
                # 清空 args，绝对不能传递 app 对象
                args=[] 
            )
            print(f">>> [Scheduler] 快照同步任务已启动 (每 {snapshot_interval} 分钟)")

        # 注册任务 2: 低频静态信息
        if not scheduler.get_job('periodic_static_sync'):
            scheduler.add_job(
                id='periodic_static_sync',
                func=run_periodic_static_sync,
                trigger='interval',
                minutes=static_sync_interval,
                max_instances=1,
                replace_existing=True,
                # 清空 args
                args=[] 
            )
            print(f">>> [Scheduler] 静态信息同步任务已启动 (每 {static_sync_interval} 分钟)")

    return app

def register_blueprints(app):
    """
    注册所有功能模块的蓝图
    """
    try:
        from app.modules.auth.routes import bp as auth_bp
        from app.modules.dashboard.routes import bp as dashboard_bp
        from app.modules.history.routes import bp as history_bp
        from app.modules.subscription.routes import bp as sub_bp
        from app.modules.settings import settings_bp
        from app.modules.data_core.komari_api import bp as komari_api_bp

        app.register_blueprint(auth_bp)
        app.register_blueprint(dashboard_bp)
        app.register_blueprint(history_bp)
        app.register_blueprint(sub_bp)
        app.register_blueprint(settings_bp, url_prefix='/settings')
        app.register_blueprint(komari_api_bp)
        
    except ImportError as e:
        print(f"!!! 蓝图导入失败: {e}")
        print("请检查各模块 routes.py 是否定义了 'bp = Blueprint(...)'")
        raise e

# --- 辅助函数：保持 create_app 整洁 ---

def init_admin_user():
    """检查并创建默认管理员"""
    user_count = db.session.scalar(db.select(func.count(User.id)))
    if user_count == 0:
        print(">>> 初始化: 创建默认管理员 admin/123456")
        admin = User(username='admin')
        admin.set_password('123456')
        db.session.add(admin)
        db.session.commit()

def init_default_settings():
    """初始化数据库默认配置"""
    default_settings = {
        'KOMARI_BASE_URL': {'value': 'http://127.0.0.1:8888', 'desc': 'API 地址'},
        'RAW_DATA_RETENTION_DAYS': {'value': 30, 'desc': '数据库数据保留天数'},
        'ACQUISITION_INTERVAL_MINUTES': {'value': 5, 'desc': '节点流量同步间隔(分)'},
        'STATIC_SYNC_INTERVAL_MINUTES': {'value': 60, 'desc': '节点列表同步间隔(分)'}
    }
    
    for key, data in default_settings.items():
        if get_config(key) is None:
            set_config(key, data['value'], data['desc'])
