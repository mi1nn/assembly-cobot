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

    def to_dict(self) -> dict:
        return {
            "installation_id": self.installation_id,
            "project_code": self.project_code,
            "project_name": self.project_name,
            "site_name": self.site_name,
            "target_code": self.target_code,
            "target_name": self.target_name,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
