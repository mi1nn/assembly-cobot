from datetime import datetime

from app.extensions import db
from app.models import SystemLog


def create_system_log(
    *,
    log_type: str,
    severity: str,
    message: str,
    work_execution_id: int | None = None,
    operation_execution_id: int | None = None,
    robot_id: int | None = None,
    code: str | None = None,
    detail=None,
    timestamp: datetime | None = None,
) -> SystemLog:
    system_log = SystemLog(
        work_execution_id=work_execution_id,
        operation_execution_id=(
            operation_execution_id
        ),
        robot_id=robot_id,
        log_type=log_type,
        code=code,
        severity=severity,
        message=message,
        detail=detail,
    )

    if timestamp is not None:
        system_log.timestamp = timestamp

    db.session.add(system_log)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return system_log


def get_system_logs(
    *,
    work_execution_id: int | None = None,
    operation_execution_id: int | None = None,
    robot_id: int | None = None,
    limit: int = 100,
) -> list[SystemLog]:
    statement = db.select(SystemLog)

    if work_execution_id is not None:
        statement = statement.where(
            SystemLog.work_execution_id
            == work_execution_id
        )

    if operation_execution_id is not None:
        statement = statement.where(
            SystemLog.operation_execution_id
            == operation_execution_id
        )

    if robot_id is not None:
        statement = statement.where(
            SystemLog.robot_id == robot_id
        )

    statement = (
        statement
        .order_by(
            SystemLog.timestamp.desc(),
            SystemLog.log_id.desc(),
        )
        .limit(limit)
    )

    return db.session.scalars(
        statement
    ).all()
