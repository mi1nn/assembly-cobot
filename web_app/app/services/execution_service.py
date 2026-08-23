from datetime import datetime
from uuid import uuid4

from app.extensions import db
from app.models import (
    Operation,
    OperationExecution,
    WorkExecution,
    Robot,
    WorkOrder,
)


def generate_execution_number() -> str:
    date_part = datetime.now().strftime(
        "%Y%m%d"
    )

    unique_part = uuid4().hex[
        :12
    ].upper()

    return (
        f"EX-{date_part}-{unique_part}"
    )


def create_execution_records(
    work_order_id: int,
    operation: Operation,
    robot_id: int,
) -> tuple[
    WorkExecution,
    OperationExecution,
]:
    work_execution = WorkExecution(
        work_order_id=work_order_id,
        robot_id=robot_id,
        execution_number=(
            generate_execution_number()
        ),
        status="PENDING",
    )

    db.session.add(work_execution)

    # INSERT를 먼저 실행해 PK를 발급받는다.
    # 트랜잭션은 아직 commit하지 않는다.
    db.session.flush()

    operation_execution = (
        OperationExecution(
            work_execution_id=(
                work_execution
                .work_execution_id
            ),
            operation_id=(
                operation.operation_id
            ),
            sequence=operation.sequence,
            status="PENDING",
            retry_count=0,
        )
    )

    db.session.add(operation_execution)

    # 두 INSERT를 하나의 트랜잭션으로 확정한다.
    db.session.commit()

    return (
        work_execution,
        operation_execution,
    )

def create_execution_records_for_operations(
    work_order_id: int,
    operations: list[Operation],
    robot_id: int,
) -> tuple[
    WorkExecution,
    list[OperationExecution],
]:
    if not operations:
        raise ValueError(
            "At least one operation is required."
        )
    sorted_operations = sorted(
        operations,
        key=lambda operation: (
            operation.sequence
        ),
    )

    sequences = [
        operation.sequence
        for operation in sorted_operations
    ]

    if len(sequences) != len(set(sequences)):
        raise ValueError(
            "Operation sequences must be unique."
        )

    try:
        work_execution = WorkExecution(
            work_order_id=work_order_id,
            robot_id=robot_id,
            execution_number=(
                generate_execution_number()
            ),
            status="PENDING",
        )

        db.session.add(work_execution)

        db.session.flush()

        operation_executions = [
            OperationExecution(
                work_execution_id=(
                    work_execution
                    .work_execution_id
                ),
                operation_id=(
                    operation.operation_id
                ),
                sequence=operation.sequence,
                status="PENDING",
                retry_count=0,
            )
            for operation in sorted_operations
        ]

        db.session.add_all(
            operation_executions
        )

        db.session.commit()

    except Exception:
        db.session.rollback()
        raise

    return (
        work_execution,
        operation_executions,
    )


def get_work_execution_by_id(
    work_execution_id: int,
) -> WorkExecution | None:
    return db.session.get(
        WorkExecution,
        work_execution_id,
    )


def get_operation_execution_by_id(
    operation_execution_id: int,
) -> OperationExecution | None:
    return db.session.get(
        OperationExecution,
        operation_execution_id,
    )


def get_operation_executions(
    work_execution_id: int,
) -> list[OperationExecution]:
    statement = (
        db.select(OperationExecution)
        .where(
            OperationExecution
            .work_execution_id
            == work_execution_id
        )
        .order_by(
            OperationExecution.sequence.asc()
        )
    )

    return db.session.scalars(
        statement
    ).all()

def get_robot_by_id(
    robot_id: int,
) -> Robot | None:
    return db.session.get(
        Robot,
        robot_id,
    )

def mark_operation_running(
    operation_execution: OperationExecution,
) -> None:
    if operation_execution.status == "RUNNING":
        return

    if operation_execution.status != "PENDING":
        raise ValueError(
            "Only a PENDING operation can "
            "transition to RUNNING."
        )

    operation_execution.status = "RUNNING"

    operation_execution.start_time = (
        datetime.now()
    )

    db.session.commit()

def mark_execution_submission_failed(
    work_execution: WorkExecution,
    operation_execution: OperationExecution,
) -> None:
    current_time = datetime.now()

    work_execution.status = "FAILED"
    work_execution.end_time = current_time

    operation_execution.status = "FAILED"
    operation_execution.end_time = (
        current_time
    )

    db.session.commit()

def mark_execution_completed(
    work_order: WorkOrder,
    work_execution: WorkExecution,
    operation_execution: OperationExecution,
    robot: Robot,
) -> None:
    current_time = datetime.now()

    work_order.status = "COMPLETED"

    work_execution.status = "COMPLETED"
    work_execution.end_time = (
        current_time
    )

    operation_execution.status = (
        "COMPLETED"
    )
    operation_execution.end_time = (
        current_time
    )

    robot.status = "IDLE"

    db.session.commit()

def mark_execution_failed(
    work_order: WorkOrder,
    work_execution: WorkExecution,
    operation_execution: OperationExecution,
    robot: Robot,
) -> None:
    current_time = datetime.now()

    work_order.status = "FAILED"

    work_execution.status = "FAILED"
    work_execution.end_time = (
        current_time
    )

    operation_execution.status = "FAILED"
    operation_execution.end_time = (
        current_time
    )

    robot.status = "IDLE"

    db.session.commit()

def get_next_pending_operation_execution(
    work_execution_id: int,
) -> OperationExecution | None:
    statement = (
        db.select(OperationExecution)
        .where(
            OperationExecution
            .work_execution_id
            == work_execution_id,
            OperationExecution.status
            == "PENDING",
        )
        .order_by(
            OperationExecution.sequence.asc()
        )
        .limit(1)
    )

    return db.session.scalar(
        statement
    )

def mark_operation_completed(
    operation_execution: OperationExecution,
) -> None:
    operation_execution.status = (
        "COMPLETED"
    )

    operation_execution.end_time = (
        datetime.now()
    )

    db.session.commit()

def mark_operation_running(
    operation_execution: OperationExecution,
) -> None:
    operation_execution.status = "RUNNING"

    operation_execution.start_time = (
        datetime.now()
    )

    db.session.commit()

def get_active_work_execution(
    work_order_id: int,
) -> WorkExecution | None:
    statement = (
        db.select(WorkExecution)
        .where(
            WorkExecution.work_order_id
            == work_order_id,
            WorkExecution.status.in_(
                (
                    "PENDING",
                    "RUNNING",
                )
            ),
        )
        .order_by(
            WorkExecution.created_at.desc()
        )
        .limit(1)
    )

    return db.session.scalar(
        statement
    )

def mark_work_execution_running(
    work_order: WorkOrder,
    work_execution: WorkExecution,
    robot: Robot,
) -> None:
    current_time = datetime.now()

    work_order.status = "RUNNING"

    work_execution.status = "RUNNING"
    work_execution.start_time = (
        current_time
    )

    robot.status = "RUNNING"

    db.session.commit()

def mark_work_submission_failed(
    work_execution: WorkExecution,
    operation_executions: list[
        OperationExecution
    ],
) -> None:
    current_time = datetime.now()

    work_execution.status = "FAILED"
    work_execution.end_time = (
        current_time
    )

    for operation_execution in (
        operation_executions
    ):
        if operation_execution.status == "PENDING":
            operation_execution.status = (
                "CANCELLED"
            )
            operation_execution.end_time = (
                current_time
            )

    db.session.commit()
