# Flask 애플리케이션을 조립하는 역할

from flask import Flask

from app.config import Config
from app.extensions import db
from app.routes.health import health_bp
from app.routes.work_orders import work_orders_bp
from app.routes.pages import pages_bp
from app.routes.bridge import bridge_bp
from app.routes.executions import executions_bp
from app.routes.logs import logs_bp
from app.routes.robots import robots_bp

def create_app():
    # Flask app 생성
    app = Flask(
        __name__,
        static_folder='../frontend',
        static_url_path='/static',
    )

    # 설정 적용
    app.config.from_object(Config)
    
    # DB 확장 초기화
    db.init_app(app)        
    
    # Blueprint 등록
    app.register_blueprint(pages_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(work_orders_bp)
    app.register_blueprint(bridge_bp)
    app.register_blueprint(executions_bp)
    app.register_blueprint(logs_bp)
    app.register_blueprint(robots_bp)
    
    return app