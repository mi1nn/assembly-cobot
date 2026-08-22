# Flask 애플리케이션을 조립하는 역할

from flask import Flask

from app.config import Config
from app.extensions import db
from app.routes.health import health_bp
from app.routes.work_orders import work_orders_bp


def create_app():
    # Flask app 생성
    app = Flask(__name__)

    # 설정 적용
    app.config.from_object(Config)
    
    # DB 확장 초기화
    db.init_app(app)
    
    # Blueprint 등록
    app.register_blueprint(health_bp)
    app.register_blueprint(work_orders_bp)

    # 오류 처리기 등록

    
    return app