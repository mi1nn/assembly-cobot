from datetime import datetime

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from app.services.log_service import (
    create_system_log,
    get_system_logs,
)


LOG_TYPES = {
    "EVENT",
    "ERROR",
    "SYSTEM",
    "ROBOT",
}

LOG_SEVERITIES = {
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
}


logs_bp = Blueprint(
    "logs",
    __name__,
    url_prefix="/api/v1/logs",
)


def parse_optional_id(value):
    if value is None:
        return None

    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None

    if parsed <= 0:
        return None

    return parsed


@logs_bp.get("")
def list_logs():
    limit = request.args.get(
        "limit",
        default=100,
        type=int,
    )

    limit = max(
        1,
        min(limit, 500),
    )

    logs = get_system_logs(
        work_execution_id=parse_optional_id(
            request.args.get(
                "work_execution_id"
            )
        ),
        operation_execution_id=parse_optional_id(
            request.args.get(
                "operation_execution_id"
            )
        ),
        robot_id=parse_optional_id(
            request.args.get("robot_id")
        ),
        limit=limit,
    )

    return jsonify({
        "success": True,
        "data": [
            item.to_dict()
            for item in logs
        ],
        "error": None,
    }), 200


@logs_bp.post("")
def add_log():
    request_data = request.get_json(
        silent=True
    )

    if not isinstance(request_data, dict):
        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": "INVALID_JSON",
                "message": (
                    "A JSON request body "
                    "is required."
                ),
            },
        }), 400

    log_type = request_data.get("log_type")
    severity = request_data.get("severity")
    message = request_data.get("message")

    if log_type not in LOG_TYPES:
        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": "INVALID_LOG_TYPE",
                "message": "Invalid log_type.",
            },
        }), 400

    if severity not in LOG_SEVERITIES:
        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": "INVALID_SEVERITY",
                "message": "Invalid severity.",
            },
        }), 400

    if (
        not isinstance(message, str)
        or not message.strip()
    ):
        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": "INVALID_MESSAGE",
                "message": (
                    "message must be "
                    "a non-empty string."
                ),
            },
        }), 400

    timestamp = None
    timestamp_value = request_data.get(
        "timestamp"
    )

    if timestamp_value is not None:
        try:
            timestamp = datetime.fromisoformat(
                timestamp_value.replace(
                    "Z",
                    "+00:00",
                )
            ).replace(tzinfo=None)
        except (AttributeError, ValueError):
            return jsonify({
                "success": False,
                "data": None,
                "error": {
                    "code": "INVALID_TIMESTAMP",
                    "message": (
                        "timestamp must be "
                        "ISO 8601 format."
                    ),
                },
            }), 400

    try:
        system_log = create_system_log(
            log_type=log_type,
            severity=severity,
            message=message.strip(),
            work_execution_id=(
                parse_optional_id(
                    request_data.get(
                        "work_execution_id"
                    )
                )
            ),
            operation_execution_id=(
                parse_optional_id(
                    request_data.get(
                        "operation_execution_id"
                    )
                )
            ),
            robot_id=parse_optional_id(
                request_data.get("robot_id")
            ),
            code=request_data.get("code"),
            detail=request_data.get("detail"),
            timestamp=timestamp,
        )

    except IntegrityError:
        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": "INVALID_LOG_REFERENCE",
                "message": (
                    "A referenced execution "
                    "or robot does not exist."
                ),
            },
        }), 409

    return jsonify({
        "success": True,
        "data": system_log.to_dict(),
        "error": None,
    }), 201
