from flask import Blueprint, current_app

pages_bp = Blueprint("pages", __name__)

@pages_bp.get("/")
def index():
    return current_app.send_static_file("index.html")
