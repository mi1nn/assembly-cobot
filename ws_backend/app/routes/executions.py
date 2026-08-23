from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import Robot, WorkOrder
from app.services.execution_service import (
    get_operation_execution_by_id,
    get_work_execution_by_id,
    mark_execution_completed,
    mark_execution_failed,
)


executions_bp = Blueprint(
    "executions",
    __name__,
    url_prefix="/api/v1/executions",
)


@executions_bp.post("/action-result")
def receive_action_result():
    request_data = request.get_json(
        silent=True,
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

    id_fields = (
        "work_execution_id",
        "operation_execution_id",
    )

    for field in id_fields:
        value = request_data.get(field)

        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value <= 0
        ):
            return jsonify({
                "success": False,
                "data": None,
                "error": {
                    "code": (
                        f"INVALID_{field.upper()}"
                    ),
                    "message": (
                        f"{field} must be "
                        "a positive integer."
                    ),
                },
            }), 400

    action_success = request_data.get(
        "success"
    )

    if not isinstance(action_success, bool):
        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": "INVALID_SUCCESS",
                "message": (
                    "success must be "
                    "a boolean."
                ),
            },
        }), 400

    work_execution_id = request_data[
        "work_execution_id"
    ]

    operation_execution_id = request_data[
        "operation_execution_id"
    ]

    work_execution = (
        get_work_execution_by_id(
            work_execution_id
        )
    )

    if work_execution is None:
        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": (
                    "WORK_EXECUTION_NOT_FOUND"
                ),
                "message": (
                    f"Work execution "
                    f"{work_execution_id} "
                    "was not found."
                ),
            },
        }), 404

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
                    f"Operation execution "
                    f"{operation_execution_id} "
                    "was not found."
                ),
            },
        }), 404

    if (
        operation_execution.work_execution_id
        != work_execution.work_execution_id
    ):
        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": "EXECUTION_MISMATCH",
                "message": (
                    "The operation execution "
                    "does not belong to the "
                    "work execution."
                ),
            },
        }), 409

    work_order = db.session.get(
        WorkOrder,
        work_execution.work_order_id,
    )

    robot = db.session.get(
        Robot,
        work_execution.robot_id,
    )

    if work_order is None or robot is None:
        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": (
                    "EXECUTION_REFERENCE_NOT_FOUND"
                ),
                "message": (
                    "The referenced work order "
                    "or robot was not found."
                ),
            },
        }), 409

    expected_status = (
        "COMPLETED"
        if action_success
        else "FAILED"
    )

    if (
        work_execution.status == expected_status
        and operation_execution.status
        == expected_status
    ):
        return jsonify({
            "success": True,
            "data": {
                "already_processed": True,
                "work_execution": (
                    work_execution.to_dict()
                ),
                "operation_execution": (
                    operation_execution.to_dict()
                ),
            },
            "error": None,
        }), 200

    terminal_statuses = {
        "COMPLETED",
        "FAILED",
        "CANCELLED",
    }

    if (
        work_execution.status in terminal_statuses
        or operation_execution.status
        in terminal_statuses
    ):
        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": (
                    "EXECUTION_ALREADY_FINISHED"
                ),
                "message": (
                    "The execution already has "
                    "a terminal status."
                ),
            },
        }), 409

    if action_success:
        mark_execution_completed(
            work_order=work_order,
            work_execution=work_execution,
            operation_execution=(
                operation_execution
            ),
            robot=robot,
        )
    else:
        mark_execution_failed(
            work_order=work_order,
            work_execution=work_execution,
            operation_execution=(
                operation_execution
            ),
            robot=robot,
        )

    return jsonify({
        "success": True,
        "data": {
            "already_processed": False,
            "action_result": {
                "success": action_success,
                "error_code": request_data.get(
                    "error_code",
                    "",
                ),
                "message": request_data.get(
                    "message",
                    "",
                ),
            },
            "work_execution": (
                work_execution.to_dict()
            ),
            "operation_execution": (
                operation_execution.to_dict()
            ),
        },
        "error": None,
    }), 200
