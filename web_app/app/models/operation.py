from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB

from app.extensions import db


class Operation(db.Model):
    __tablename__ = "operation"

    operation_id = db.Column(
        db.BigInteger,
        primary_key=True,
    )

    installation_id = db.Column(
        db.BigInteger,
        db.ForeignKey("installation.installation_id"),
        nullable=False,
    )

    code = db.Column(
        db.String(50),
        nullable=False,
    )

    name = db.Column(
        db.String(200),
        nullable=False,
    )

    sequence = db.Column(
        db.Integer,
        nullable=False,
    )

    description = db.Column(
        db.Text,
    )

    is_required = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )

    estimated_duration_sec = db.Column(
        db.Integer,
    )

    parameter = db.Column(
        JSONB,
    )

    components = db.Column(
        JSONB,
        nullable=False,
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
            "operation_id": self.operation_id,
            "installation_id": (
                self.installation_id
            ),
            "code": self.code,
            "name": self.name,
            "sequence": self.sequence,
            "description": self.description,
            "is_required": self.is_required,
            "estimated_duration_sec": (
                self.estimated_duration_sec
            ),
            "parameter": self.parameter,
            "components": self.components,
        }
