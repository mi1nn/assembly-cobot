from flask import Blueprint, jsonify

from app.services.bridge_service import (
    BridgeConnectionError,
    BridgeResponseError,
    get_bridge_health,
)


bridge_bp = Blueprint(
    "bridge",
    __name__,
    url_prefix="/api/v1/bridge",
)


@bridge_bp.get("/health")
def bridge_health():
    try:
        bridge_data = get_bridge_health()

    except BridgeConnectionError as error:
        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": "BRIDGE_UNAVAILABLE",
                "message": str(error),
            },
        }), 503

    except BridgeResponseError as error:
        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": "INVALID_BRIDGE_RESPONSE",
                "message": str(error),
            },
        }), 502

    return jsonify({
        "success": True,
        "data": bridge_data,
        "error": None,
    }), 200
