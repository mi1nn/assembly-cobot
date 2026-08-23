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
