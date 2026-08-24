from sqlalchemy import func

from app.extensions import db

class Robot(db.Model):
    __tablename__ = "robot"

    robot_id = db.Column(
        db.BigInteger,
        primary_key=True,
    )

    robot_code = db.Column(
        db.String(50),
        nullable=False,
        unique=True,
    )

    name = db.Column(
        db.String(200),
        nullable=False,
    )

    manufacturer = db.Column(
        db.String(100),
    )

    model = db.Column(
        db.String(100),
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="IDLE",
    )

    dofs = db.Column(
        db.Integer,
    )

    payload_kg = db.Column(
        db.Numeric(8, 2),
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
            "robot_id": self.robot_id,
            "robot_code": self.robot_code,
            "name": self.name,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "status": self.status,
            "dofs": self.dofs,
            "payload_kg": (
                float(self.payload_kg)
                if self.payload_kg is not None
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
