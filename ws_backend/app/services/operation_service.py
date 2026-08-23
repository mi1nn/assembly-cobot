from app.extensions import db
from app.models import Operation


def get_operation_for_installation(
    operation_id: int,
    installation_id: int,
) -> Operation | None:
    statement = db.select(Operation).where(
        Operation.operation_id == operation_id,
        Operation.installation_id == installation_id,
    )

    return db.session.execute(
        statement
    ).scalar_one_or_none()

def get_operations_for_installation(
    installation_id: int,
) -> list[Operation]:
    statement = (
        db.select(Operation)
        .where(
            Operation.installation_id
            == installation_id
        )
        .order_by(
            Operation.sequence.asc()
        )
    )

    return db.session.scalars(
        statement
    ).all()

def get_operation_by_id(
    operation_id: int,
) -> Operation | None:
    return db.session.get(
        Operation,
        operation_id,
    )
