from sqlalchemy import func

from app.extensions import db


class WorkExecution(db.Model):
    __tablename__ = "work_execution"

    work_execution_id = db.Column(
        db.BigInteger,
        primary_key=True,
    )

    work_order_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "work_order.work_order_id"
        ),
        nullable=False,
    )

    robot_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "robot.robot_id"
        ),
        nullable=False,
    )

    execution_number = db.Column(
        db.String(50),
        nullable=False,
        unique=True,
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

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=func.now(),
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=func.now(),
    )

    def to_dict(self) -> dict:
        return {
            "work_execution_id": (
                self.work_execution_id
            ),
            "work_order_id": self.work_order_id,
            "robot_id": self.robot_id,
            "execution_number": (
                self.execution_number
            ),
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
            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),
            "updated_at": (
                self.updated_at.isoformat()
                if self.updated_at
                else None
            ),
        }
