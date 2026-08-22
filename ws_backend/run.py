# 완성된 Flask 앱을 가져와 실제 서버로 실행

from app import create_app


app = create_app()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )