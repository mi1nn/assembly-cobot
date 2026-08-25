from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB

from app.extensions import db


class SensorData(db.Model):
    __tablename__ = "sensor_data"

    sensor_data_id = db.Column(
        db.BigInteger,
        primary_key=True,
    )

    sensor_id = db.Column(
        db.BigInteger,
        db.ForeignKey("sensor.sensor_id"),
        nullable=False,
    )

    operation_execution_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "operation_execution"
            ".operation_execution_id"
        ),
        nullable=False,
    )

    data_type = db.Column(
        db.String(50),
        nullable=False,
    )

    data = db.Column(
        JSONB,
        nullable=False,
    )

    timestamp = db.Column(
        db.DateTime,
        nullable=False,
        server_default=func.now(),
    )

    def to_dict(self) -> dict:
        return {
            "sensor_data_id": (
                self.sensor_data_id
            ),
            "sensor_id": self.sensor_id,
            "operation_execution_id": (
                self.operation_execution_id
            ),
            "data_type": self.data_type,
            "data": self.data,
            "timestamp": (
                self.timestamp.isoformat()
                if self.timestamp
                else None
            ),
        }
