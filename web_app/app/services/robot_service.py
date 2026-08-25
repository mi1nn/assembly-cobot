from app.extensions import db
from app.models import Robot, WorkExecution


def get_robots() -> list[Robot]:
    statement = (
        db.select(Robot)
        .order_by(Robot.robot_id.asc())
    )

    return db.session.scalars(
        statement
    ).all()


def get_active_execution_for_robot(
    robot_id: int,
) -> WorkExecution | None:
    statement = (
        db.select(WorkExecution)
        .where(
            WorkExecution.robot_id == robot_id,
            WorkExecution.status.in_({
                "PENDING",
                "RUNNING",
            }),
        )
        .order_by(
            WorkExecution.created_at.desc()
        )
        .limit(1)
    )

    return db.session.scalar(statement)
