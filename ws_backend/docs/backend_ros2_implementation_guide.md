# Backend + ROS2 통합 시스템 단계별 구현 가이드

## 0. 목표

현재 프로젝트의 MVP를 다음 구조로 구현한다.

```text
Frontend
HTML / CSS / JavaScript
        │
        │ HTTP / REST
        ▼
Flask Backend
        │
        ├──────────────► PostgreSQL
        │
        │ HTTP / REST
        ▼
ROS2 Bridge Node
        │
        │ ROS2 Action / Topic
        ▼
Robot Control Node
        │
        ▼
Robot
```

### 기술 스택

- Frontend: HTML / CSS / JavaScript
- Backend: Python / Flask
- DB: PostgreSQL
- ORM: SQLAlchemy
- Backend ↔ ROS2 Bridge: HTTP / REST
- ROS2 Bridge: Python / rclpy
- Bridge ↔ Robot Control: ROS2 Action / Topic
- API 테스트: Postman 또는 curl
- 개발 환경: Linux + ROS2

---

# 1. 전체 개발 순서

초보자 기준으로 한 번에 모든 계층을 연결하지 않는다.

```text
Step 1. 개발 환경 구성
    ↓
Step 2. PostgreSQL 구축
    ↓
Step 3. Flask 기본 서버 구축
    ↓
Step 4. Flask ↔ PostgreSQL 연결
    ↓
Step 5. Work Order CRUD API
    ↓
Step 6. HTML/JS Dashboard 연결
    ↓
Step 7. ROS2 Bridge 구축
    ↓
Step 8. Flask ↔ ROS2 Bridge 통신
    ↓
Step 9. ROS2 Action으로 Robot Control 연결
    ↓
Step 10. 실행 상태 / 결과 DB 기록
    ↓
Step 11. Dashboard 상태 조회
    ↓
Step 12. 전체 시나리오 통합 테스트
```

각 단계가 정상 동작한 후 다음 단계로 넘어간다.

---

# 2. Step 1 — 개발 환경 구성

## 목표

각 구성요소를 독립적으로 실행할 수 있는 상태를 만든다.

### 설치 / 확인

- Python
- Flask
- SQLAlchemy
- PostgreSQL
- ROS2
- `rclpy`
- Git

### 권장 디렉토리

```text
project/
├── backend/
├── frontend/
├── ros2_ws/
│   └── src/
├── database/
└── docs/
```

### 완료 기준

- Python 실행 가능
- Flask 실행 가능
- PostgreSQL 접속 가능
- ROS2 workspace 실행 가능
- 기존 `robot_control` Node 실행 가능

---

# 3. Step 2 — PostgreSQL 구축

## 목표

현재 DB 요구사항을 실제 PostgreSQL DB로 구현한다.

주요 데이터 영역:

- Project
- Site
- Installation Target
- Work Order
- Operation
- Component
- Robot
- Work Execution
- Operation Execution
- Work Event
- Error Log
- Sensor / Force-Torque Data

`operation.parameter`는 MVP에서 JSONB로 관리한다.

### 작업

1. PostgreSQL 설치
2. Database 생성
3. User 생성
4. DB schema 생성
5. Table 생성
6. Foreign Key 설정
7. 초기 테스트 데이터 삽입

### 권장 도구

- PostgreSQL
- `psql`
- DBeaver 등의 DB GUI

### 완료 기준

다음 관계를 DB에서 조회할 수 있어야 한다.

```text
Project
  └── Site
       └── Installation Target
            └── Work Order
                 └── Operation
```

그리고 실행 데이터가 연결되어야 한다.

```text
Work Order
    └── Work Execution
          └── Operation Execution
                ├── Event
                ├── Error
                └── Sensor Data
```

---

# 4. Step 3 — Flask 기본 서버 구축

## 목표

가장 단순한 Flask 서버를 먼저 실행한다.

### 구조

```text
backend/
├── app/
│   ├── __init__.py
│   ├── routes/
│   ├── models/
│   ├── services/
│   └── config.py
├── requirements.txt
└── run.py
```

### 먼저 구현할 것

```text
GET /
```

응답:

```json
{
    "message": "Backend is running"
}
```

### 완료 기준

브라우저 또는 curl로 Flask 서버에 접속하여 정상 응답을 확인한다.

---

# 5. Step 4 — Flask ↔ PostgreSQL 연결

## 목표

Flask에서 PostgreSQL 데이터를 읽고 쓸 수 있게 한다.

구조:

```text
Flask Route
    ↓
Service
    ↓
SQLAlchemy
    ↓
PostgreSQL
```

### 먼저 Work Order 하나만 대상으로 테스트한다.

예:

```text
GET /api/work-orders
```

DB에 있는 Work Order를 JSON으로 반환한다.

### 완료 기준

PostgreSQL의 데이터를 Flask API에서 조회할 수 있어야 한다.

---

# 6. Step 5 — Work Order CRUD API

## 목표

웹에서 작업 지시를 관리할 수 있는 기본 API를 만든다.

### API

```text
GET    /api/work-orders
GET    /api/work-orders/{id}
POST   /api/work-orders
PATCH  /api/work-orders/{id}
```

### 예시

```json
POST /api/work-orders

{
    "installation_target_id": 1,
    "priority": 1
}
```

### 상태

MVP에서는 다음 정도로 시작한다.

```text
CREATED
READY
RUNNING
COMPLETED
FAILED
```

### 완료 기준

Postman 또는 curl을 사용하여 Work Order 생성 → 조회 → 수정이 가능해야 한다.

---

# 7. Step 6 — HTML / JavaScript Dashboard 연결

## 목표

React 없이 HTML/CSS/JavaScript로 Backend API를 호출한다.

### 화면

최초에는 하나의 화면만 만든다.

```text
-----------------------------------------
       Robot Automation Dashboard
-----------------------------------------

Work Orders

WO-001   Target-A   READY      [Execute]
WO-002   Target-B   CREATED    [Execute]

-----------------------------------------
Robot Status: IDLE
-----------------------------------------
```

### JavaScript

```text
페이지 로드
    ↓
GET /api/work-orders
    ↓
JSON 수신
    ↓
HTML에 Work Order 표시
```

Execute 버튼:

```text
버튼 클릭
    ↓
POST /api/work-orders/{id}/execute
```

### 완료 기준

브라우저에서 DB의 Work Order를 확인하고 버튼으로 API 요청을 보낼 수 있어야 한다.

---

# 8. Step 7 — ROS2 Bridge Node 구축

## 목표

Backend와 ROS2를 분리하는 Bridge Node를 만든다.

### 구조

```text
ros2_ws/src/
└── ros2_bridge/
    ├── package.xml
    ├── setup.py
    └── ros2_bridge/
        ├── __init__.py
        └── bridge_node.py
```

Bridge는 두 역할을 가진다.

```text
HTTP Server
    ↓
Backend 요청 수신

ROS2 Client
    ↓
Robot Control 호출
```

즉,

```text
Backend
   │ HTTP
   ▼
Bridge
   │ ROS2
   ▼
Robot Control
```

### 완료 기준

Bridge Node가 실행되고 HTTP 요청을 받을 수 있어야 한다.

---

# 9. Step 8 — Flask ↔ ROS2 Bridge 통신

## 목표

Work Order 실행 요청을 실제 ROS2 명령으로 전달한다.

### 전체 흐름

```text
Dashboard
    │
    │ POST /api/work-orders/1/execute
    ▼
Flask
    │
    │ POST /jobs
    ▼
ROS2 Bridge
    │
    │ ROS2 Action Goal
    ▼
Robot Control
```

### Backend 역할

Backend는 작업 정보를 확인한 후 Bridge에 작업 실행을 요청한다.

예:

```json
{
    "work_order_id": 1,
    "operation_id": 10
}
```

### 완료 기준

Flask에서 실행 요청을 보냈을 때 ROS2 Bridge가 해당 요청을 수신하는 것을 확인한다.

---

# 10. Step 9 — ROS2 Action으로 Robot Control 연결

## 목표

Bridge가 Robot Control의 Action Client가 되도록 구현한다.

```text
ROS2 Bridge
    │
    │ Action Client
    ▼
Robot Control
    │
    │ Robot command
    ▼
Robot
```

### 역할

#### Bridge

- Action Server 대기
- Goal 전송
- Feedback 수신
- Result 수신
- 실패 / 취소 처리

#### Robot Control

- Action Server
- 실제 작업 실행
- Feedback 전달
- Result 반환

### 완료 기준

다음 테스트가 가능해야 한다.

```text
Backend
  ↓
Bridge
  ↓
Action Goal
  ↓
Robot Control
  ↓
작업 실행
  ↓
Result
```

---

# 11. Step 10 — 실행 상태와 결과 DB 기록

## 목표

실제 로봇 작업 결과를 DB에 저장한다.

DB 요구사항의 핵심 흐름:

```text
Work Order
    ↓
Work Execution
    ↓
Operation Execution
    ↓
Result
```

예:

```text
RUNNING
    ↓
COMPLETED
```

또는

```text
RUNNING
    ↓
FAILED
```

### 이벤트 기록

작업 중 다음과 같은 이벤트를 기록한다.

```text
WORK_STARTED
OPERATION_STARTED
OPERATION_COMPLETED
OPERATION_FAILED
WORK_COMPLETED
WORK_FAILED
```

### 오류

실패 시:

```json
{
    "error_code": "ROBOT_001",
    "message": "Robot execution failed"
}
```

등을 기록한다.

### 완료 기준

로봇 작업 1회 실행 후 DB에서 실행 이력과 결과를 조회할 수 있어야 한다.

---

# 12. Step 11 — Dashboard 상태 조회

## 목표

웹에서 현재 작업 상태를 확인한다.

최초에는 Polling 방식으로 구현한다.

```text
JavaScript
    │
    │ GET /api/executions/{id}
    │
    ▼
Flask
    │
    ▼
PostgreSQL
```

예:

```text
2초마다 상태 조회

RUNNING
   ↓
RUNNING
   ↓
COMPLETED
```

### 이후 확장

필요하면 WebSocket을 도입한다.

```text
ROS2
 ↓
Bridge
 ↓
WebSocket
 ↓
Browser
```

MVP에서는 WebSocket을 우선 구현하지 않는다.

---

# 13. Step 12 — 전체 통합 시나리오

최종적으로 다음 시나리오가 동작하면 MVP의 핵심 통신 구조가 완성된다.

## 시나리오

### 1. 관리자가 Work Order 생성

```text
Dashboard
   ↓
POST /api/work-orders
   ↓
Flask
   ↓
PostgreSQL
```

### 2. Work Order 조회

```text
Dashboard
   ↓
GET /api/work-orders
   ↓
Flask
   ↓
PostgreSQL
```

### 3. 작업 실행

```text
Dashboard
   ↓
POST /api/work-orders/{id}/execute
   ↓
Flask
   ↓
ROS2 Bridge
   ↓
Robot Control
```

### 4. 로봇 작업 수행

```text
Robot Control
   ↓
Robot
```

### 5. 작업 결과 반환

```text
Robot
   ↓
Robot Control
   ↓
ROS2 Bridge
   ↓
Flask
   ↓
PostgreSQL
```

### 6. Dashboard에서 결과 확인

```text
PostgreSQL
   ↓
Flask API
   ↓
JavaScript
   ↓
Dashboard
```

---

# 14. 구현 우선순위

초보자라면 다음 순서를 지킨다.

### Phase 1 — Backend 기초

- [ ] Flask 서버 실행
- [ ] GET API 구현
- [ ] POST API 구현
- [ ] JSON Request / Response 이해

### Phase 2 — DB

- [ ] PostgreSQL 구축
- [ ] SQLAlchemy 연결
- [ ] Work Order CRUD
- [ ] Operation 조회

### Phase 3 — Frontend

- [ ] HTML Dashboard
- [ ] JavaScript fetch()
- [ ] Work Order 조회
- [ ] Work Order 생성
- [ ] Execute 버튼

### Phase 4 — ROS2

- [ ] ROS2 Bridge Node
- [ ] Bridge HTTP API
- [ ] ROS2 Action Client
- [ ] Robot Control Action Server 연결

### Phase 5 — 통합

- [ ] Work Order 실행
- [ ] Execution 생성
- [ ] Robot 실행
- [ ] Result 저장
- [ ] Error 저장
- [ ] Dashboard 상태 표시

---

# 15. 초기에 하지 않을 것

MVP에서는 다음 기능을 뒤로 미룬다.

- React
- WebSocket
- Redis
- Kafka
- Docker Compose 고도화
- 인증 / OAuth
- 마이크로서비스
- 별도의 Message Broker
- 복잡한 비동기 처리
- 모든 ROS2 데이터를 DB에 저장
- Tool / TCP / Fixture 등을 처음부터 전부 별도 테이블화

특히 Tool / TCP / Fixture / Position / Coordinate System은 현재 DB 설계에서도 `operation.parameter` JSONB로 우선 관리하도록 되어 있으므로 MVP에서 별도 Master Table을 만들지 않는다.

---

# 16. 완료 후 목표 구조

```text
project/
│
├── backend/
│   ├── app/
│   │   ├── routes/
│   │   ├── services/
│   │   ├── models/
│   │   └── config.py
│   └── run.py
│
├── frontend/
│   ├── index.html
│   ├── css/
│   └── js/
│
├── ros2_ws/
│   └── src/
│       ├── ros2_bridge/
│       └── robot_control/
│
├── database/
│   └── migrations/
│
└── docs/
```

핵심 통신 구조:

```text
HTML / JS
    │
    │ REST
    ▼
 Flask Backend
    │
    ├──── SQLAlchemy ──── PostgreSQL
    │
    │ REST
    ▼
 ROS2 Bridge
    │
    │ ROS2 Action / Topic
    ▼
 Robot Control
    │
    ▼
 Robot
```

## 최종 성공 기준

다음 한 문장이 실제 시스템에서 동작하면 된다.

> **관리자가 웹에서 Work Order를 생성하고 실행하면, Flask Backend가 DB에 작업을 기록하고 ROS2 Bridge를 통해 Robot Control에 작업을 전달하며, 로봇 실행 결과가 다시 DB에 기록되고 Dashboard에서 확인된다.**
