from app.services.execution_service import (
    create_execution_records_for_operations,
    get_robot_by_id,
    mark_execution_running,
    mark_execution_submission_failed,
)

# API 발행
from app.services.bridge_service import (
    BridgeConnectionError,
    BridgeResponseError,
    submit_bridge_job,
)
from app.services.operation_service import (
    get_operations_for_installation,
)

from flask import Blueprint, jsonify, request
from app.services.work_order_service import (
    get_work_orders,
    get_work_order_by_id,
    create_work_order,
    update_work_order,
)
# 제약조건 오류 처리하기 위한 모듈
from sqlalchemy.exc import IntegrityError
from app.extensions import db

# 변경 가능 항목
UPDATABLE_FIELDS = {
    "title",
    "priority",
    "status",
    "remark",
}
# 작업 상태 항목
WORK_ORDER_STATUSES = {
    "CREATED",
    "READY",
    "RUNNING",
    "COMPLETED",
    "FAILED",
    "CANCELLED",
}


work_orders_bp = Blueprint(
    "work_orders",
    __name__,
    url_prefix="/api/v1/work-orders",
)
# 작업 지시 조회

@work_orders_bp.get("")
def list_work_orders():
    work_orders = get_work_orders()

    return jsonify({
        "success": True,
        "data": [
            work_order.to_dict()
            for work_order in work_orders
        ],
        "error": None,
    }), 200


@work_orders_bp.get("/<int:work_order_id>")
def get_work_order(work_order_id: int):
    work_order = get_work_order_by_id(work_order_id)

    if work_order is None:
        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": "WORK_ORDER_NOT_FOUND",
                "message": (
                    f"Work order {work_order_id} was not found."
                ),
            },
        }), 404

    return jsonify({
        "success": True,
        "data": work_order.to_dict(),
        "error": None,
    }), 200

# 작업 지시 추가
@work_orders_bp.post("")
def add_work_order():
    request_data = request.get_json(silent=True)

    if not isinstance(request_data, dict):
        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": "INVALID_JSON",
                "message": "A JSON request body is required.",
            },
        }), 400

    required_fields = (
          "order_number",
          "title",
          "installation_id",
    )

    missing_fields = [
        field
        for field in required_fields
        if request_data.get(field) in (None, "")
    ]

    if missing_fields:
        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": "MISSING_REQUIRED_FIELDS",
                "message": (
                    "Missing required fields: "
                    + ", ".join(missing_fields)
                ),
            },
        }), 400

    try:
        work_order = create_work_order(
            order_number=request_data["order_number"],
            title=request_data["title"],
            installation_id=request_data[
                "installation_id"
            ],
            priority=request_data.get("priority", 3),
            remark=request_data.get("remark"),
            created_by=request_data.get("created_by"),
        )

    except IntegrityError:
        db.session.rollback()

        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": "WORK_ORDER_CONFLICT",
                "message": (
                    "The order number already exists or the "
                    "installation is invalid."
                ),
            },
        }), 409

    return jsonify({
        "success": True,
        "data": work_order.to_dict(),
        "error": None,
    }), 201

# 작업 지시 수정
@work_orders_bp.patch("/<int:work_order_id>")
def edit_work_order(work_order_id: int):
    request_data = request.get_json(silent=True)

    if not isinstance(request_data, dict):
        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": "INVALID_JSON",
                "message": "A JSON request body is required.",
            },
        }), 400

    if not request_data:
        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": "EMPTY_UPDATE",
                "message": "At least one field is required.",
            },
        }), 400

    # 변경을 허용하지 않은 필드 검사
    invalid_fields = (
            set(request_data)
            - UPDATABLE_FIELDS
        )

    if invalid_fields:
        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": "INVALID_UPDATE_FIELDS",
                "message": (
                    "Fields cannot be updated: "
                    + ", ".join(sorted(invalid_fields))
                ),
            },
        }), 400

    # 각 값의 타입과 범위를 검사
    if "title" in request_data:
            title = request_data["title"]

            if not isinstance(title, str) or not title.strip():
                return jsonify({
                    "success": False,
                    "data": None,
                    "error": {
                        "code": "INVALID_TITLE",
                        "message": (
                            "title must be a non-empty string."
                        ),
                    },
                }), 400

            request_data["title"] = title.strip()

    if "priority" in request_data:
        priority = request_data["priority"]

        if (
            not isinstance(priority, int)
            or isinstance(priority, bool)
            or priority < 1
        ):
            return jsonify({
                "success": False,
                "data": None,
                "error": {
                    "code": "INVALID_PRIORITY",
                    "message": (
                        "priority must be a positive integer."
                    ),
                },
            }), 400

    if "status" in request_data:
        status = request_data["status"]

        if status not in WORK_ORDER_STATUSES:
            return jsonify({
                "success": False,
                "data": None,
                "error": {
                    "code": "INVALID_STATUS",
                    "message": (
                        "status must be one of: "
                        + ", ".join(
                            sorted(WORK_ORDER_STATUSES)
                        )
                    ),
                },
            }), 400

    # 서비스 호출
    work_order = update_work_order(
        work_order_id,
        request_data,
    )

    if work_order is None:
        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": "WORK_ORDER_NOT_FOUND",
                "message": (
                    f"Work order {work_order_id} was not found."
                ),
            },
        }), 404

    return jsonify({
        "success": True,
        "data": work_order.to_dict(),
        "error": None,
    }), 200

@work_orders_bp.post(
    "/<int:work_order_id>/execute"
)
def execute_work_order(work_order_id: int):
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
                    "A JSON request body is required."
                ),
            },
        }), 400

    robot_id = request_data.get(
        "robot_id"
    )

    if (
        not isinstance(robot_id, int)
        or isinstance(robot_id, bool)
        or robot_id <= 0
    ):
        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": "INVALID_ROBOT_ID",
                "message": (
                    "robot_id must be "
                    "a positive integer."
                ),
            },
        }), 400

    work_order = get_work_order_by_id(
        work_order_id
    )

    if work_order is None:
        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": "WORK_ORDER_NOT_FOUND",
                "message": (
                    f"Work order {work_order_id} "
                    "was not found."
                ),
            },
        }), 404

    if work_order.status != "READY":
        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": "WORK_ORDER_NOT_READY",
                "message": (
                    "Only READY work orders "
                    "can be executed."
                ),
            },
        }), 409

    robot = get_robot_by_id(
        robot_id
    )

    if robot is None:
        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": "ROBOT_NOT_FOUND",
                "message": (
                    f"Robot {robot_id} "
                    "was not found."
                ),
            },
        }), 404

    if robot.status != "IDLE":
        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": "ROBOT_NOT_AVAILABLE",
                "message": (
                    "Only IDLE robots "
                    "can execute a job."
                ),
            },
        }), 409

    operations = (
        get_operations_for_installation(
            work_order.installation_id
        )
    )

    if not operations:
        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": "NO_OPERATIONS",
                "message": (
                    "No operations are configured "
                    "for this work order's "
                    "installation."
                ),
            },
        }), 409


    try:
        (
            work_execution,
            operation_executions,
        ) = create_execution_records_for_operations(
            work_order_id=work_order_id,
            operations=operations,
            robot_id=robot_id,
        )

    except IntegrityError:
        db.session.rollback()

        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": "EXECUTION_CONFLICT",
                "message": (
                    "Could not create "
                    "execution records."
                ),
            },
        }), 409

    operation = operations[0]

    operation_execution = (
        operation_executions[0]
    )

    try:
        bridge_data = submit_bridge_job(
            work_order_id=work_order_id,
            operation_id=(
                operation.operation_id
            ),
            work_execution_id=(
                work_execution.work_execution_id
            ),
            operation_execution_id=(
                operation_execution
                .operation_execution_id
            ),
            robot_id=robot_id,
            parameters=operation.parameter,
        )

    except BridgeConnectionError as error:
        mark_execution_submission_failed(
            work_execution,
            operation_execution,
        )

        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": "BRIDGE_UNAVAILABLE",
                "message": str(error),
            },
        }), 503

    except BridgeResponseError as error:
        mark_execution_submission_failed(
            work_execution,
            operation_execution,
        )

        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": "BRIDGE_JOB_REJECTED",
                "message": str(error),
            },
        }), 502

    mark_execution_running(
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
            "work_order_id": work_order_id,
            "work_execution": (
                work_execution.to_dict()
            ),
            "first_operation": (
                operation.to_dict()
            ),
            "operation_executions": [
                item.to_dict()
                for item
                in operation_executions
            ],
            "total_operations": len(
                operation_executions
            ),
            "bridge": bridge_data,
        },
        "error": None,
    }), 202
