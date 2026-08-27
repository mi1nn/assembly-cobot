from app.models import Installation


def get_active_installations() -> list[Installation]:
    return (
        Installation.query
        .filter(Installation.status == "ACTIVE")
        .order_by(Installation.installation_id.asc())
        .all()
    )
