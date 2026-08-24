from app.extensions import db
from app.models import (
    Installation,
    Operation,
    WorkOrder,
)

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

# SELECT * FROM work_order WHERE work_order_id = 1;
def get_work_order_by_id(work_order_id: int,) -> WorkOrder | None:
    return db.session.get(WorkOrder, work_order_id)

# order_number 기준으로 가져올 것인지에 따라 함수 추가


# Work Order 생성 함수(INSERT)
def create_work_order(
    order_number: str,
    title: str,
    installation_id: int,
    priority: int = 3,
    remark: str | None = None,
    created_by: str | None = None,
) -> WorkOrder:
    # WorkOrder 객체 생성
    work_order = WorkOrder(
        order_number=order_number,
        title=title,
        installation_id=installation_id,
        priority=priority,
        status="CREATED",
        remark=remark,
        created_by=created_by,
    )
    # DB에 INSERT
    db.session.add(work_order)
    db.session.commit()

    return work_order

def update_work_order(
    work_order_id: int,
    update_data: dict,
) -> WorkOrder | None:
    work_order = db.session.get(
        WorkOrder,
        work_order_id,
    )

    if work_order is None:
        return None

    for field, value in update_data.items():
        # 객체의 속성을 이름으로 변경
        setattr(work_order, field, value)

    db.session.commit()

    return work_order

def validate_ready_requirements(
    work_order: WorkOrder,
) -> str | None:
    installation = db.session.get(
        Installation,
        work_order.installation_id,
    )

    if installation is None:
        return "INSTALLATION_NOT_FOUND"

    if installation.status != "ACTIVE":
        return "INSTALLATION_NOT_ACTIVE"

    operation_exists = db.session.scalar(
        db.select(
            db.exists().where(
                Operation.installation_id
                == work_order.installation_id
            )
        )
    )

    if not operation_exists:
        return "NO_OPERATIONS"

    return None
