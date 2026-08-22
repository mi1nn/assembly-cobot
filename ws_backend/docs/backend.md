# Backend 설계

## 1. 구조

```
[Frontend]
    │
    │ HTTP REST
    ▼
[FastAPI Backend] FLASK 
    │
    ├──────── SQL ────────► [PostgreSQL]
    │
    │ HTTP REST
    ▼
[ROS2 Bridge Node]
    │
    ├── Action ──────────► [ROS2 Control Node]
    │
    ├── Topic ◄────────── [ROS2 Control Node]
    │
    └── Topic ◄────────── [Sensor Node]
```

## 2. 데이터 흐름
```
작업 지시
Frontend
  ↓
Backend
  ↓
DB에서 Work Order/Operation 조회
  ↓
Bridge
  ↓
ROS2 Control
  ↓
로봇 작업 실행
  ↓
Feedback / Event / Error / Sensor
  ↓
Bridge
  ↓
Backend
  ↓
DB 저장
  ↓
Frontend Dashboard
```
---

# 파트 별 역할
## 1. Backend
- Work Order API
- Execution API
- Operation API
- Event/Error API
- Sensor Data API
- DB CRUD
- Bridge와 통신

## 2. Ros2 Bridge
- Backend 요청 수신
- ROS2 Action Client
- ROS2 Topic Subscriber
- ROS2 Service Client
- ROS2 결과 수신
- Backend로 결과 전달

## 3. ROS2 Control
- Action Server
- Robot control
- Operation execution
- Feedback
- Event
- Error

---
# 구현 순서

## 1. 인터페이스 설계

### 공통 규약
- URL Prefix: `/api/v1`
- 응답 포맷 통일

```json
// 성공
{ "success": true, "data": {}, "error": null }

// 실패
{ "success": false, "data": null, "error": { "code": "NOT_FOUND", "message": "..." } }
```

| 상태 코드 | 의미 |
| --- | --- |
| 200 | 조회/요청 성공 |
| 201 | 생성 성공 |
| 400 | 잘못된 요청 |
| 404 | 리소스 없음 |
| 409 | 상태 충돌 (이미 실행 중 등) |
| 503 | Bridge 통신 불가 |

### 도메인 모델 (초안)
- `resource`: 로봇/스테이션 등 작업 자원
- `work_order`: 작업 지시. `created → ready → in_progress → completed | failed | canceled`
- `work_execution`: work_order의 실행 인스턴스 (1 work_order : N work_execution). `pending → running → completed | failed | canceled`
- `operation`: work_order를 구성하는 세부 작업 단위
- `work_event` / `error_log`
- `sensor`

#### Frontend용 API

**Resource**

| CRUD | HTTP | URI | 비고 |
| --- | --- | --- | --- |
| 리소스 목록 조회 | GET | /resources | |
| 리소스 생성 | POST | /resources | |
| 리소스 수정 | PUT | /resources/:id | |
| 리소스 삭제 | DELETE | /resources/:id | |

**Work Order**

| 기능 | HTTP | URI | 비고 |
| --- | --- | --- | --- |
| 작업 지시 목록 조회 | GET | /work-orders | `?status=` 필터 |
| 작업 지시 조회 | GET | /work-orders/:id | operations 포함 |
| 작업 지시 생성 | POST | /work-orders | operations 리스트 포함 |
| 작업 지시 수정 | PUT | /work-orders/:id | 실행 전에만 허용 |
| 작업 지시 삭제 | DELETE | /work-orders/:id | 실행 전에만 허용 |
| 작업 시작 | POST | /work-orders/:id/start | work_execution 생성 + Bridge 실행 요청 |
| 작업 취소 | POST | /work-orders/:id/cancel | |

**Execution**

| 기능 | HTTP | URI | 비고 |
| --- | --- | --- | --- |
| 실행 목록 조회 | GET | /executions | `?work_order_id=` |
| 실행 상세 조회 | GET | /executions/:id | 현재 상태/진행률 포함 |
| 실행 중단 | POST | /executions/:id/cancel | Bridge에 취소 전파 |
| 실행별 이벤트 조회 | GET | /executions/:id/events | |

**Operation**

| 기능 | HTTP | URI | 비고 |
| --- | --- | --- | --- |
| 오퍼레이션 목록 조회 | GET | /work-orders/:id/operations | |
| 오퍼레이션 조회 | GET | /operations/:id | 최근 실행 결과 포함 |

**Event / Error**

| 기능 | HTTP | URI | 비고 |
| --- | --- | --- | --- |
| 이벤트 목록 조회 | GET | /events | `?level=&type=&from=&to=` |
| 에러 목록 조회 | GET | /errors | |

**Sensor**

| 기능 | HTTP | URI | 비고 |
| --- | --- | --- | --- |
| 센서 데이터 조회 | GET | /sensor-data | `?resource_id=&type=&from=&to=` |
| 최신값 조회 | GET | /sensor-data/latest | 대시보드 폴링용 |

### Backend <-> Bridge

Bridge를 HTTP 서버로 구현 (예: `:8001`). Backend → Bridge는 명령, Bridge → Backend는 결과 보고(콜백).

**Backend → Bridge (명령)**

| 기능 | HTTP | URI | 비고 |
| --- | --- | --- | --- |
| 헬스 체크 | GET | /health | Bridge/ROS2 연결 상태 |
| 로봇 상태 조회 | GET | /status | |
| 작업 실행 요청 | POST | /executions/:id/start | ROS2 Action Goal로 변환 |
| 작업 취소 | POST | /executions/:id/cancel | Action cancel |

실행 요청 예시:

```json
POST /executions/123/start
{
  "execution_id": 123,
  "work_order_id": 45,
  "operations": [
    { "seq": 1, "operation_id": 901, "type": "move", "params": { "target": [0.4, 0.1, 0.3] } },
    { "seq": 2, "operation_id": 902, "type": "grip", "params": { "force": 20 } }
  ]
}
```

응답: `202 Accepted` — 비동기 실행이므로 수락 여부만 즉시 반환, 결과는 콜백으로 보고

**Bridge → Backend (결과 보고)**

| 기능 | HTTP | URI | 비고 |
| --- | --- | --- | --- |
| 실행 상태 보고 | POST | /callbacks/executions/:id/status | running/completed/failed/canceled |
| 오퍼레이션 결과 보고 | POST | /callbacks/operations/:id/result | operation 단위 완료 기록 |
| 이벤트/에러 보고 | POST | /callbacks/events | |
| 센서 데이터 전송 | POST | /callbacks/sensor-data | 배치 전송 권장 |

상태 보고 예시:

```json
{
  "execution_id": 123,
  "status": "completed",
  "current_seq": 2,
  "progress": 1.0,
  "error_code": null,
  "message": null,
  "timestamp": "2026-08-21T10:00:00Z"
}
```

**비고**
- Bridge는 HTTP 수신 → ROS2 Action Goal 변환, Action feedback → Backend 콜백 변환 담당
- Action 인터페이스(예: `ExecuteOperations.action`)는 3단계에서 확정
- 콜백 실패 시 재시도 정책, 센서 스트리밍(WebSocket 전환)은 추후 검토

## 2. Backend <-> DB

### FastAPI로 DB에 접근, CRUD
- Work Order 조회
- Work Order 상태 변경
- Work Execution 생성
- Operation 조회
- Execution 상태 변경

### 성공 기준

`GET /work-orders/1` -> DB의 실제 `Work Order` 반환 -> POST /work-orders/1/start -> `work_execution` 생성

## 3. ROS2 bridge <-> control

### Action 인터페이스 확정 필요

## 4. Backend <-> ROS2 bridge 연결
전체 작업 흐름 완성

## 5. Event/Error log 관리

## 6. Sensor data 관리

## 7. Frontend 연결