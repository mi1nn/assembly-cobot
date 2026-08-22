# 환경변수(.env)를 읽어 FLASK와 FLASK-SQLAlchemy가 사용할 수 있는 설정으로 변환
# SQLAlchemy 접속 URL을 만드는 설정 클래스 파일

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

def get_required_env(name: str) -> str: 
    value = os.getenv(name)

    if not value:
        raise RuntimeError(f"Required environment variable is missing: {name}")

    return value

class Config:
    # 다음 접속정보를 SLQAlchemy 형식으로 구성
    SQLALCHEMY_DATABASE_URI = URL.create(
        drivername="postgresql+psycopg2",
        username=get_required_env("DB_USER"),
        password=get_required_env("DB_PASSWORD"),
        host=get_required_env("DB_HOST"),
        port=int(get_required_env("DB_PORT")),
        database=get_required_env("DB_NAME"),
    )

    # 불필요한 객체 변경 추적 기능 OFF
    SQLALCHEMY_TRACK_MODIFICATIONS = False

