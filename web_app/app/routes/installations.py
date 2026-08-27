from flask import Blueprint, jsonify

from app.services.installation_service import get_active_installations


installations_bp = Blueprint(
    "installations", __name__, url_prefix="/api/v1/installations"
)


@installations_bp.get("/active")
def list_active_installations():
    installations = get_active_installations()

    return jsonify({
        "success": True,
        "data": [
            installation.to_dict() for installation in installations
        ],
        "error": None,
    }), 200
