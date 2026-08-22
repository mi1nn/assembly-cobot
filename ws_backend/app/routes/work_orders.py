# API 발행

from flask import Blueprint, jsonify
from app.services.work_order_service import get_work_orders

work_orders_bp = Blueprint(
    "work_orders",
    __name__,
    url_prefix="/api/v1/work-orders",
)


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
