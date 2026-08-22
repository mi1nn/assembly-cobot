from app.extensions import db


class WorkOrder(db.Model):
    __tablename__ = "work_order"

    work_order_id = db.Column(
        db.BigInteger,
        primary_key=True,
    )

    order_number = db.Column(
        db.String(50),
        nullable=False,
        unique=True,
    )

    title = db.Column(
        db.String(300),
        nullable=False,
    )

    installation_target_id = db.Column(
        db.BigInteger,
        db.ForeignKey("installation_target.installation_target_id"),
        nullable=False,
    )

    priority = db.Column(
        db.Integer,
        nullable=False,
        default=3,
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="CREATED",
    )

    planned_start_date = db.Column(db.DateTime)
    planned_end_date = db.Column(db.DateTime)
    remark = db.Column(db.Text)
    created_by = db.Column(db.String(100))

    created_at = db.Column(
        db.DateTime,
        nullable=False,
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
    )

    # WorkOder 객체를 jsonify() 형태로 변경하기 위해 딕셔너리로 바꾸는 메서드
    def to_dict(self) -> dict:
        return {
            "work_order_id": self.work_order_id,
            "order_number": self.order_number,
            "title": self.title,
            "installation_target_id": self.installation_target_id,
            "priority": self.priority,
            "status": self.status,
            "planned_start_date": (
                self.planned_start_date.isoformat()
                if self.planned_start_date
                else None
            ),
            "planned_end_date": (
                self.planned_end_date.isoformat()
                if self.planned_end_date
                else None
            ),
            "remark": self.remark,
            "created_by": self.created_by,
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
