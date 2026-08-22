from app import create_app
from app.services.work_order_service import get_work_orders


app = create_app()

with app.app_context():
    work_orders = get_work_orders()

    for work_order in work_orders:
        print(
            work_order.work_order_id,
            work_order.order_number,
            work_order.status,
        )
