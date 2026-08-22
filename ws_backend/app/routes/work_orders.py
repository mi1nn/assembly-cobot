# API 발행

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
          "installation_target_id",
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
            installation_target_id=request_data[
                "installation_target_id"
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
                    "installation target is invalid."
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
