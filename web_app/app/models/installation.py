from sqlalchemy import func

from app.extensions import db


class Installation(db.Model):
    __tablename__ = "installation"

    installation_id = db.Column(
        db.BigInteger,
        primary_key=True,
    )

    project_code = db.Column(
        db.String(50),
        nullable=False,
    )

    project_name = db.Column(
        db.String(200),
        nullable=False,
    )

    site_name = db.Column(
        db.String(200),
        nullable=False,
    )

    target_code = db.Column(
        db.String(50),
        nullable=False,
        unique=True,
    )

    target_name = db.Column(
        db.String(200),
        nullable=False,
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="ACTIVE",
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
