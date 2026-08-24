from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB

from app.extensions import db


class SystemLog(db.Model):
    __tablename__ = "log"

    log_id = db.Column(
        db.BigInteger,
        primary_key=True,
    )

    work_execution_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "work_execution.work_execution_id"
        ),
        nullable=True,
    )

    operation_execution_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "operation_execution.operation_execution_id"
        ),
        nullable=True,
    )

    robot_id = db.Column(
        db.BigInteger,
        db.ForeignKey("robot.robot_id"),
        nullable=True,
    )

    log_type = db.Column(
        db.String(50),
        nullable=False,
    )

    code = db.Column(
        db.String(50),
        nullable=True,
    )

    severity = db.Column(
        db.String(20),
        nullable=False,
        default="INFO",
    )

    message = db.Column(
        db.Text,
        nullable=False,
    )

    detail = db.Column(
        JSONB,
        nullable=True,
    )

    timestamp = db.Column(
        db.DateTime,
        nullable=False,
        server_default=func.now(),
    )

    def to_dict(self) -> dict:
        return {
            "log_id": self.log_id,
            "work_execution_id": (
                self.work_execution_id
            ),
            "operation_execution_id": (
                self.operation_execution_id
            ),
            "robot_id": self.robot_id,
            "log_type": self.log_type,
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "detail": self.detail,
            "timestamp": (
                self.timestamp.isoformat()
                if self.timestamp
                else None
            ),
        }
