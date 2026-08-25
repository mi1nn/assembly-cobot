from app.extensions import db
from app.models import SensorData

def get_sensor_data_for_operation(
    operation_execution_id: int,
    *,
    data_type: str = "FORCE_TORQUE",
    limit: int = 1000,
) -> list[SensorData]:
    statement = (
        db.select(SensorData)
        .where(
            SensorData.operation_execution_id
            == operation_execution_id,
            SensorData.data_type == data_type,
        )
        .order_by(
            SensorData.timestamp.desc(),
            SensorData.sensor_data_id.desc(),
        )
        .limit(limit)
    )

    # 최신 limit개를 조회한 뒤
    # Frontend 그래프용 시간 오름차순으로 반환
    sensor_data = list(
        db.session.scalars(statement).all()
    )

    sensor_data.reverse()

    return sensor_data
