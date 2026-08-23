from sqlalchemy import func

from app.extensions import db

class OperationExecution(db.Model):
    __tablename__ = "operation_execution"

    operation_execution_id = db.Column(
        db.BigInteger,
        primary_key=True,
    )

    work_execution_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "work_execution.work_execution_id"
        ),
        nullable=False,
    )

    operation_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "operation.operation_id"
        ),
        nullable=False,
    )

    sequence = db.Column(
        db.Integer,
        nullable=False,
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="PENDING",
    )

    start_time = db.Column(
        db.DateTime,
    )

    end_time = db.Column(
        db.DateTime,
    )

    retry_count = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=func.now(),
    )

    def to_dict(self) -> dict:
        return {
            "operation_execution_id": (
                self.operation_execution_id
            ),
            "work_execution_id": (
                self.work_execution_id
            ),
            "operation_id": self.operation_id,
            "sequence": self.sequence,
            "status": self.status,
            "start_time": (
                self.start_time.isoformat()
                if self.start_time
                else None
            ),
            "end_time": (
                self.end_time.isoformat()
                if self.end_time
                else None
            ),
            "retry_count": self.retry_count,
            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),
        }
