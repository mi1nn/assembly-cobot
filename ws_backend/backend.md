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

### Backend API

| CRUD | HTTP | URI |
| --- | --- | --- |
| 작업 리소스 조회 | GET | /resources |
| 리소스 생성 | POST | /resources |
| 리소스 전체 수정 | PUT | /resources/:id |
| 특정 리소스 삭제 | DELETE | /resources/:id |

| 전체 작업 지시 조회 | GET | /resources/workorders |
| 특정 작업 지시 조회 | GET | /resources/workorders/:id |
| 작업 리소스 조회 | GET | /resources |

#### Frontend용 API



### Backend <-> Bridge

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