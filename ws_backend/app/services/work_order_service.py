from app.extensions import db
from app.models import WorkOrder

# SELECT * FROM work_order ORDER BY priority ASC, created_at DESC;
def get_work_orders() -> list[WorkOrder]:
    statement = (
        db.select(WorkOrder)
        .order_by(
            WorkOrder.priority.asc(),
            WorkOrder.created_at.desc(),
        )
    )

    # 쿼리 실행하고 결과를 WorkOrder 객체의 리스트로 반환
    return db.session.scalars(statement).all()
