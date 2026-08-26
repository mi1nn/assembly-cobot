from flask import Blueprint, jsonify, request

from app.services.execution_service import (
    get_operation_execution_by_id,
)
from app.services.sensor_data_service import (
    get_sensor_data_for_operation,
)

sensor_data_bp = Blueprint(
    "sensor_data",
    __name__,
    url_prefix="/api/v1/sensor-data",
)


@sensor_data_bp.get("")
def list_sensor_data():
    operation_execution_id = request.args.get(
        "operation_execution_id",
        type=int,
    )

    if (
        operation_execution_id is None
        or operation_execution_id <= 0
    ):
        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": (
                    "INVALID_OPERATION_EXECUTION_ID"
                ),
                "message": (
                    "operation_execution_id must "
                    "be a positive integer."
                ),
            },
        }), 400

    operation_execution = (
        get_operation_execution_by_id(
            operation_execution_id
        )
    )

    if operation_execution is None:
        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": (
                    "OPERATION_EXECUTION_NOT_FOUND"
                ),
                "message": (
                    "The Operation Execution "
                    "was not found."
                ),
            },
        }), 404

    limit = request.args.get(
        "limit",
        default=1000,
        type=int,
    )

    if limit is None or not 1 <= limit <= 5000:
        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": "INVALID_LIMIT",
                "message": (
                    "limit must be between "
                    "1 and 5000."
                ),
            },
        }), 400

    data_type = request.args.get(
        "data_type",
        default="FORCE_TORQUE",
        type=str,
    ).strip()

    if not data_type:
        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": "INVALID_DATA_TYPE",
                "message": (
                    "data_type must not "
                    "be empty."
                ),
            },
        }), 400

    sensor_data = (
        get_sensor_data_for_operation(
            operation_execution_id,
            data_type=data_type,
            limit=limit,
        )
    )

    return jsonify({
        "success": True,
        "data": {
            "operation_execution": (
                operation_execution.to_dict()
            ),
            "data_type": data_type,
            "sample_count": len(sensor_data),
            "samples": [
                item.to_dict()
                for item in sensor_data
            ],
        },
        "error": None,
    }), 200
