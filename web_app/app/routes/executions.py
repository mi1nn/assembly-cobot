from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import Robot, WorkOrder

from app.services.log_service import create_system_log
from app.services.execution_service import (
    get_next_pending_operation_execution,
    get_operation_execution_by_id,
    get_work_execution_by_id,
    mark_execution_completed,
    mark_execution_failed,
    mark_execution_cancelled,
    mark_operation_completed,
    mark_operation_running,
)

FEEDBACK_STATUS_NAMES = {
    0: "PENDING",
    1: "RUNNING",
    2: "COMPLETED",
    3: "FAILED",
    4: "CANCELLED",
}

executions_bp = Blueprint(
    "executions",
    __name__,
    url_prefix="/api/v1/executions",
)

@executions_bp.post("/action-feedback")
def receive_action_feedback():
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

    status = request_data.get(
        "status"
    )

    if (
        not isinstance(status, int)
        or isinstance(status, bool)
        or status
        not in FEEDBACK_STATUS_NAMES
    ):
        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": "INVALID_STATUS",
                "message": (
                    "status must be an integer "
                    "between 0 and 4."
                ),
            },
        }), 400

    work_execution = (
        get_work_execution_by_id(
            request_data[
                "work_execution_id"
            ]
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
                    "The work execution "
                    "was not found."
                ),
            },
        }), 404

    operation_execution = (
        get_operation_execution_by_id(
            request_data[
                "operation_execution_id"
            ]
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
                    "The operation execution "
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

    status_name = FEEDBACK_STATUS_NAMES[
        status
    ]

    if status_name == "RUNNING":
        try:
            operation_started = (
                mark_operation_running(
                    operation_execution
                )
            )

        except ValueError as error:
            return jsonify({
                "success": False,
                "data": None,
                "error": {
                    "code": (
                        "INVALID_STATUS_TRANSITION"
                    ),
                    "message": str(error),
                },
            }), 409

        if operation_started:
            create_system_log(
                log_type="EVENT",
                severity="INFO",
                code="OPERATION_STARTED",
                message=(
                    request_data.get("message")
                    or "Operation started."
                ),
                work_execution_id=(
                    work_execution.work_execution_id
                ),
                operation_execution_id=(
                    operation_execution
                    .operation_execution_id
                ),
                robot_id=work_execution.robot_id,
                detail={
                    "feedback_status": status_name,
                },
            )

    return jsonify({
        "success": True,
        "data": {
            "work_execution_id": (
                work_execution
                .work_execution_id
            ),
            "operation_execution": (
                operation_execution.to_dict()
            ),
            "feedback_status": status_name,
            "message": request_data.get(
                "message",
                "",
            ),
            "final_state_pending_result": (
                status_name in {
                    "COMPLETED",
                    "FAILED",
                    "CANCELLED",
                }
            ),
        },
        "error": None,
    }), 200

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

    # 같은 결과 callback이 다시 들어온 경우
    if (
        action_success
        and operation_execution.status
        == "COMPLETED"
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

    result_error_code = (
        request_data.get("error_code") or ""
    )

    action_cancelled = (
        not action_success
        and result_error_code == "CANCELLED"
    )

    if (
        action_cancelled
        and operation_execution.status
        == "CANCELLED"
        and work_execution.status
        == "CANCELLED"
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

    if (
        not action_success
        and not action_cancelled
        and operation_execution.status == "FAILED"
        and work_execution.status == "FAILED"
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

    allowed_result_statuses = (
        {"RUNNING"}
        if action_success
        else {"PENDING", "RUNNING"}
    )

    if (
        operation_execution.status
        not in allowed_result_statuses
    ):
        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": (
                    "INVALID_RESULT_STATE"
                ),
                "message": (
                    "A successful Result requires "
                    "a RUNNING operation. "
                    "A failed Result requires a "
                    "PENDING or RUNNING operation."
                ),
            },
        }), 409


    # 현재 Operation이 취소된 경우
    if action_cancelled:
        mark_execution_cancelled(
            work_order=work_order,
            work_execution=work_execution,
            operation_execution=(
                operation_execution
            ),
            robot=robot,
        )

        create_system_log(
            log_type="EVENT",
            severity="INFO",
            code="OPERATION_CANCELLED",
            message=(
                request_data.get("message")
                or "Operation cancelled."
            ),
            work_execution_id=(
                work_execution.work_execution_id
            ),
            operation_execution_id=(
                operation_execution
                .operation_execution_id
            ),
            robot_id=work_execution.robot_id,
            detail={
                "action_success": False,
                "action_cancelled": True,
            },
        )

        return jsonify({
            "success": True,
            "data": {
                "already_processed": False,
                "workflow_status": "CANCELLED",
                "action_result": {
                    "success": False,
                    "error_code": "CANCELLED",
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

    # 현재 Operation이 실패한 경우
    if not action_success:
        mark_execution_failed(
            work_order=work_order,
            work_execution=work_execution,
            operation_execution=(
                operation_execution
            ),
            robot=robot,
        )

        error_code = (
            request_data.get("error_code")
            or "OPERATION_FAILED"
        )

        create_system_log(
            log_type="ERROR",
            severity="ERROR",
            code=error_code,
            message=(
                request_data.get("message")
                or "Operation failed."
            ),
            work_execution_id=(
                work_execution.work_execution_id
            ),
            operation_execution_id=(
                operation_execution
                .operation_execution_id
            ),
            robot_id=work_execution.robot_id,
            detail={
                "action_success": False,
            },
        )

        return jsonify({
            "success": True,
            "data": {
                "already_processed": False,
                "workflow_status": "FAILED",
                "action_result": {
                    "success": False,
                    "error_code": (
                        request_data.get(
                            "error_code",
                            "",
                        )
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

    # 현재 Operation만 완료 처리한다.
    mark_operation_completed(
        operation_execution
    )

    create_system_log(
        log_type="EVENT",
        severity="INFO",
        code="OPERATION_COMPLETED",
        message=(
            request_data.get("message")
            or "Operation completed."
        ),
        work_execution_id=(
            work_execution.work_execution_id
        ),
        operation_execution_id=(
            operation_execution
            .operation_execution_id
        ),
        robot_id=work_execution.robot_id,
        detail={
            "action_success": True,
        },
    )

    next_operation_execution = (
        get_next_pending_operation_execution(
            work_execution.work_execution_id
        )
    )

    # 다음 Operation이 없으면 전체 작업 완료
    if next_operation_execution is None:
        mark_execution_completed(
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
                "workflow_status": (
                    "COMPLETED"
                ),
                "has_next_operation": False,
                "work_execution": (
                    work_execution.to_dict()
                ),
                "operation_execution": (
                    operation_execution.to_dict()
                ),
            },
            "error": None,
        }), 200

    return jsonify({
        "success": True,
        "data": {
            "already_processed": False,
            "workflow_status": "RUNNING",
            "has_next_operation": True,
            "completed_operation_execution": (
                operation_execution.to_dict()
            ),
            "next_operation_execution": (
                next_operation_execution.to_dict()
            ),
        },
        "error": None,
    }), 200
