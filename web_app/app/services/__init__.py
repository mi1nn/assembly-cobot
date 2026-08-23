# 실제 업무 로직 처리
# app의 핵심 동작 담당
# - 조회, 생성, 수정 작업
# - 상태 변경 규칙
# - 입력값 검증
# - 여러 모델을 함께 처리하는 트랜잭션
# - ROS2 Bridge 같은 외부 시스템 호출

from app.services.work_order_service import get_work_orders

__all__ = ["get_work_orders"]
