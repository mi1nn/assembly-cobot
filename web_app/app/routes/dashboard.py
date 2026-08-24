from flask import Blueprint, jsonify

from app.services.dashboard_service import (
    get_dashboard_data,
)

dashboard_bp = Blueprint(
    "dashboard",
    __name__,
    url_prefix="/api/v1/dashboard",
)

@dashboard_bp.get("")
def get_dashboard():
    return jsonify({
        "success": True,
        "data": get_dashboard_data(),
        "error": None,
    }), 200
