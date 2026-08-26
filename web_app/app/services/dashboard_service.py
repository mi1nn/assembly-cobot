from sqlalchemy import func

from app.extensions import db
from app.models import WorkExecution
from app.services.robot_service import (
    get_active_execution_for_robot,
    get_robots,
)

def get_work_execution_summary() -> dict:
    statement = db.select(
        func.count().filter(
            WorkExecution.status == "COMPLETED"
        ),
        func.count().filter(
            WorkExecution.status == "FAILED"
        ),
        func.count().filter(
            WorkExecution.status == "CANCELLED"
        ),
    )

    row = db.session.execute(
        statement
    ).one()

    completed = int(row[0] or 0)
    failed = int(row[1] or 0)
    cancelled = int(row[2] or 0)

    terminal_total = (
        completed
        + failed
        + cancelled
    )

    success_rate = (
        round(
            completed
            / terminal_total
            * 100,
            1,
        )
        if terminal_total > 0
        else 0.0
    )

    return {
        "completed": completed,
        "failed": failed,
        "cancelled": cancelled,
        "terminal_total": terminal_total,
        "success_rate": success_rate,
    }


def get_dashboard_data() -> dict:
    robot_data = []

    for robot in get_robots():
        active_execution = (
            get_active_execution_for_robot(
                robot.robot_id
            )
        )

        item = robot.to_dict()

        item["work_execution_id"] = (
            active_execution.work_execution_id
            if active_execution
            else None
        )

        item["work_order_id"] = (
            active_execution.work_order_id
            if active_execution
            else None
        )

        robot_data.append(item)

    return {
        "robots": robot_data,
        "work_execution_summary": (
            get_work_execution_summary()
        ),
    }
