# Flask Backend 개발 가이드

## 1. 개요

`web_app/app`은 작업 지시를 관리하고 PostgreSQL 및 ROS2 Bridge를 연결하는 Flask Backend다.

주요 역할은 다음과 같다.

- Work Order 조회, 생성 및 수정
- Work Order 실행 이력과 공정별 실행 이력 생성
- ROS2 Bridge 상태 확인 및 작업 제출
- ROS2 Action Feedback/Result callback과 실행 상태 반영
- Controller 및 Bridge 이벤트 로그 저장과 조회
- `frontend/`의 정적 웹 화면 제공

검증 환경:

- Ubuntu 24.04
- Python 3.12
- PostgreSQL 16
- ROS2 Jazzy

---

## 2. 시스템 연결 구조

```text
Browser
   │ HTTP :5000
   ▼
Flask Backend
   ├── SQLAlchemy ──────────────────── PostgreSQL :5432
   └── HTTP(Work Command DTO) ──────── ROS2 Bridge :8001
                                            │
                                            ▼
                                      ROS2 Action Server
                                            │
                                            ▼
                                        Controller
```

Flask Backend와 ROS2 Bridge는 서로 다른 프로세스다. Backend는 HTTP API와 DB 상태를 관리하고, Bridge는 Work 단위 Command DTO를 받아 `sequence` 순서로 Operation Action Goal 하나씩 전송한다.

작업 결과는 다음 경로로 돌아온다.

```text
ROS2 Action Feedback/Result
        ↓
ROS2 Bridge
        ↓ POST /api/v1/executions/action-feedback|action-result
Flask Backend
        ↓
PostgreSQL 상태 및 Operation 로그 갱신
```

Log에는 작업 중 발생하는 상태 뿐 아니라 Controller, Bridge 준비 상태와 같은 시스템 이벤트도 다음과 같은 경로로 관리한다.

```text
Controller /system_event
        ↓
ROS2 Bridge
        ↓ POST /api/v1/logs
Flask Backend
        ↓
PostgreSQL log 저장
```

---

## 3. 디렉토리 구조

```text
web_app/
├── app/
│   ├── __init__.py       # Flask Application Factory와 Blueprint 등록
│   ├── config.py         # 환경변수 및 Backend 설정
│   ├── extensions.py     # SQLAlchemy 확장 객체
│   ├── models/           # SQLAlchemy Model
│   ├── routes/           # HTTP 요청 검증 및 응답
│   └── services/         # DB 처리와 Bridge 호출
├── frontend/             # Flask가 제공하는 정적 웹 화면
├── database/             # Schema, Seed 및 DB 구축 스크립트
├── .env                  # 로컬 환경변수, Git에 커밋하지 않음
├── .env.example
├── requirements.txt
└── run.py                # 로컬 개발 서버 진입점
```

요청은 일반적으로 다음 순서로 처리된다.

```text
Route → Service → Model/Database
               └→ ROS2 Bridge HTTP API
```

현재 Backend는 `WorkOrder`, `Installation`, `Operation`, `Robot`, `WorkExecution`, `OperationExecution`, `SystemLog` SQLAlchemy Model을 제공한다. 전체 DB Table과 관계는 [Database 구축 가이드](../database/README.md)를 참고한다.

---

## 4. 개발 환경 준비

모든 명령은 `web_app` 디렉토리에서 실행한다.

```bash
cd web_app
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

가상환경 활성화와 비활성화:

```bash
source .venv/bin/activate
deactivate
```

Backend 의존성 확인:

```bash
.venv/bin/python -c "import flask, flask_sqlalchemy, sqlalchemy, dotenv, psycopg2, requests; print('Backend dependencies OK')"
```

ROS2 Bridge를 실행할 터미널에서는 ROS2 환경을 먼저 설정한다.

```bash
source /opt/ros/jazzy/setup.bash
source ../install/setup.bash
```

Backend만 실행하거나 Work Order CRUD API만 확인할 때는 `rclpy`가 필요하지 않다.

---

## 5. 환경변수

최초 한 번 예제 파일을 복사한다.

```bash
cp .env.example .env
```

| 변수 | 필수 여부 | 기본값 | 용도 |
| --- | --- | --- | --- |
| `DB_HOST` | 필수 | 없음 | PostgreSQL 호스트 |
| `DB_PORT` | 필수 | 없음 | PostgreSQL 포트 |
| `DB_NAME` | 필수 | 없음 | Database 이름 |
| `DB_USER` | 필수 | 없음 | Backend 접속 계정 |
| `DB_PASSWORD` | 필수 | 없음 | Backend 접속 비밀번호 |
| `BRIDGE_BASE_URL` | 선택 | `http://127.0.0.1:8001` | ROS2 Bridge HTTP 주소 |
| `BRIDGE_TIMEOUT_SECONDS` | 선택 | `3` | Bridge 요청 제한 시간(초) |

예시:

```dotenv
DB_HOST=localhost
DB_PORT=5432
DB_NAME=robot_automation_db
DB_USER=robot_app
DB_PASSWORD=change_me

BRIDGE_BASE_URL=http://127.0.0.1:8001
BRIDGE_TIMEOUT_SECONDS=3
```

필수 DB 변수가 없으면 애플리케이션 import 단계에서 `Required environment variable is missing` 오류가 발생한다. 실제 비밀번호가 들어 있는 `.env`는 공유하거나 Git에 커밋하지 않는다.

---

## 6. Database 준비

로컬 개발 DB와 Seed Data를 처음 구축하려면 다음 명령을 실행한다.

```bash
./database/setup_db.sh --seed
```

DB 구축, Reset, Schema 및 Seed 정책은 [Database 구축 가이드](../database/README.md)를 기준으로 한다.

Backend에서 DB 연결만 확인하려면 다음 명령을 사용한다.

```bash
.venv/bin/python -c "from sqlalchemy import text; from app import create_app; from app.extensions import db; flask_app=create_app(); ctx=flask_app.app_context(); ctx.push(); print(db.session.execute(text('SELECT 1')).scalar_one()); ctx.pop()"
```

정상 결과는 `1`이다.

---

## 7. Backend 실행

```bash
source .venv/bin/activate
python run.py
```

개발 서버는 `0.0.0.0:5000`에서 실행된다.

- `http://localhost:5000/`: `frontend/index.html`
- `http://localhost:5000/static/...`: Frontend 정적 파일
- `http://localhost:5000/api/v1/...`: Backend API

`run.py`는 `debug=True`인 Flask 개발 서버다. 운영 배포 용도로 사용하지 않는다.

기본 동작 확인:

```bash
curl -i http://localhost:5000/api/v1/health
curl -s \
  http://localhost:5000/api/v1/work-orders \
  | .venv/bin/python -m json.tool
```

---

## 8. API 요약

  Method    Path                               역할                             성공 코드
━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━
  GET       /                                  Frontend 화면 제공               200
────────  ─────────────────────────────────  ───────────────────────────────  ───────────
  GET       /api/v1/health                     Backend 상태 확인                200
────────  ─────────────────────────────────  ───────────────────────────────  ───────────
  GET       /api/v1/bridge/health              Bridge 상태 확인                 200
────────  ─────────────────────────────────  ───────────────────────────────  ───────────
  GET       /api/v1/work-orders                Work Order 목록 조회             200
────────  ─────────────────────────────────  ───────────────────────────────  ───────────
  GET       /api/v1/work-orders/{id}           Work Order 단일 조회             200
────────  ─────────────────────────────────  ───────────────────────────────  ───────────
  GET       /api/v1/work-orders/{id}/          최신 실행 진행 상태 조회         200
            progress
────────  ─────────────────────────────────  ───────────────────────────────  ───────────
  POST      /api/v1/work-orders                Work Order 생성                  201
────────  ─────────────────────────────────  ───────────────────────────────  ───────────
  PATCH     /api/v1/work-orders/{id}           Work Order 수정 및 READY 전환    200
────────  ─────────────────────────────────  ───────────────────────────────  ───────────
  POST      /api/v1/work-orders/{id}/          Work 단위 실행 요청              202
            execute
────────  ─────────────────────────────────  ───────────────────────────────  ───────────
  POST      /api/v1/executions/action-         Action Feedback callback         200
            feedback
────────  ─────────────────────────────────  ───────────────────────────────  ───────────
  POST      /api/v1/executions/action-         Action Result callback           200
            result
────────  ─────────────────────────────────  ───────────────────────────────  ───────────
  GET       /api/v1/logs                       로그 조회                        200
────────  ─────────────────────────────────  ───────────────────────────────  ───────────
  POST      /api/v1/logs                       Controller·Bridge 로그 저장      201

DELETE API는 현재 제공하지 않는다.

### 일반 응답 형식

대부분의 API는 다음 envelope를 사용한다.

```json
{
  "success": true,
  "data": {},
  "error": null
}
```

오류 응답:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "Error description"
  }
}
```

`GET /api/v1/health`는 다음과 같은 별도 형식이다.

```json
{
  "status": "ok",
  "service": "robot-automation-backend"
}
```

상세 요청과 오류 검증 예시는 [Backend API 검증 가이드](../docs/backend_api_test.md)를 참고한다.

---

## 9. Work Order API

### 생성

```bash
curl -i \
  -X POST \
  http://localhost:5000/api/v1/work-orders \
  -H "Content-Type: application/json" \
  -d '{
    "order_number": "WO-LOCAL-001",
    "title": "Local verification",
    "installation_id": 1,
    "priority": 3,
    "created_by": "local-user"
  }'
```

필수 필드는 `order_number`, `title`, `installation_id`다. 생성 상태는 `CREATED`다.

부분 수정이 가능한 필드는 다음과 같다.

- `title`
- `priority`
- `status`
- `remark`

허용되는 Work Order 상태:

```text
CREATED → READY → RUNNING → COMPLETED
                    └─────→ FAILED
CREATED/READY/RUNNING ────→ CANCELLED
```

사용자가 PATCH로 요청할 수 있는 상태 전이는 `CREATED` → `READY` 하나이다. 

실행 이후 RUNNING, COMPLETED, FAILED, CANCELLED 상태는 Backend가 Bridge 접수 결과와 Action Feedback/Result를 기준으로 갱신한다.

현재 사용자가 직접 작업을 취소하는 API는 제공하지 않는다.

---

## 10. 작업 실행 흐름

Work Order 실행 요청에는 robot_id가 필요하다.

curl -i \
  -X POST \
  http://localhost:5000/api/v1/work-orders/WORK_ORDER_ID/execute \
  -H "Content-Type: application/json" \
  -d '{"robot_id":1}'

실행 조건:

- Work Order 상태가 READY여야 한다.
- Robot이 존재하고 상태가 IDLE이어야 한다.
- Installation에 하나 이상의 Operation이 있어야 한다.
- 동일 Work Order에 실행 중인 Work Execution이 없어야 한다.
- ROS2 Bridge가 실행 중이며 Work를 받아들여야 한다.

Backend는 하나의 work_execution과 모든 공정의 operation_execution을 생성한다. Operation
Execution의 초기 상태는 PENDING이다.

Backend는 다음 Work Command DTO를 Bridge에 한 번 전달한다.

```
{
  "work_order_id": 1,
  "work_execution_id": 10,
  "robot_id": 1,
  "operations": [
    {
      "operation_execution_id": 101,
      "operation_id": 1,
      "sequence": 1,
      "parameters": {},
      "components": []
    }
  ]
}
```

Bridge는 operations를 sequence 오름차순으로 정렬하고 한 번에 하나의 Action Goal만 Controller에 보낸다. 현재 Operation이 성공해야 다음 Operation을 실행한다.

```
Backend
    → Work Command DTO
Bridge
    → Operation 1 Action Goal
    → 성공
    → Operation 2 Action Goal
    → 성공
    → ...
```

Bridge 접수가 성공하면 Backend는 다음 상태를 변경한다.

```
Work Order:     READY → RUNNING
Work Execution: PENDING → RUNNING
Robot:          IDLE → RUNNING
```

Operation Execution은 Action Feedback과 Result에 따라 변경한다.

`PENDING → RUNNING → COMPLETED | FAILED | CANCELLED`

상태 추적 기준은 operation_execution_id다. 진행률은 ROS에서 전달하지 않고 Backend가 다음과 같이 계산한다.

`COMPLETED Operation 수 / 전체 Operation 수`

중간 Operation이 실패하거나 취소되면 Bridge는 이후 Operation을 실행하지 않는다. 모든 Operation이 완료되면 Work Order와 Work Execution은 COMPLETED, Robot은 IDLE로 변경된다.

동일한 Feedback 또는 Result callback이 재전송돼도 이미 처리된 상태를 중복 변경하지 않는다.

### 현재 제한

- 사용자가 실행 중인 작업을 취소하는 HTTP API는 아직 제공하지 않는다.
- Bridge Queue와 중복 접수 정보는 메모리에 있으므로 Bridge 재시작 후 복구되지 않는다.
- Backend 자체 오류는 DB 로그에 자동 저장하지 않고 Flask 일반 로그로만 출력한다.
- 실제 Controller Operation handler는 별도 개발 범위다.

———

## 11. 로그 관리

로그는 Operation 내부와 외부를 구분한다.

### Operation 내부 이벤트와 오류

Operation 실행 중 발생하는 상태와 결과는 ROS Action으로만 관리한다.

```
Controller Action Feedback/Result
    → ROS2 Bridge
    → Backend execution callback
    → log 테이블
```

Backend 기록 규칙:

| 상황 | log_type | severity | code |
| --- | --- | --- | --- |
| Operation 시작 | EVENT | INFO | OPERATION_STARTED |
| Operation 완료 | EVENT | INFO | OPERATION_COMPLETED |
| Operation 실패 | ERROR | ERROR | Action Result의 error_code |
|  Operation 취소 | EVENT | INFO | OPERATION_CANCELLED |

같은 Operation 오류를 /system_event Topic으로 다시 보내지 않는다.

### Operation 외부 Controller 이벤트

Controller 상태 변경과 Operation 외부 오류는 /system_event Topic으로 발행한다.

```
uint8 SEVERITY_INFO=0
uint8 SEVERITY_WARNING=1
uint8 SEVERITY_ERROR=2
uint8 SEVERITY_CRITICAL=3

uint64 robot_id
uint8 severity
string code
string message
```

주요 이벤트 코드 예:

- `CONTROLLER_STARTED`
- `CONTROLLER_READY`
- `CONTROLLER_ERROR`
- `SOLAR_MOTION_READY`
- `SOLAR_MOTION_NOT_READY`
- `SOLAR_MOTION_ERROR`
- `SAFETY_STOP_ACTIVATED`
- `SAFETY_STOP_RELEASED`

Bridge는 Topic 메시지를 다음 형태로 Backend에 전달한다.

```
{
  "robot_id": 1,
  "log_type": "ROBOT",
  "severity": "ERROR",
  "code": "SOLAR_MOTION_ERROR",
  "message": "Solar Motion initialization failed."
}
```

### Bridge 자체 이벤트

Bridge 자체 상태와 오류는 Bridge가 직접 /api/v1/logs로 전달한다.

```
log_type = SYSTEM
code = BRIDGE_...
```

현재 Action Server 연결 상태 변경을 다음 코드로 기록한다.

```
BRIDGE_ACTION_SERVER_CONNECTED
BRIDGE_ACTION_SERVER_DISCONNECTED
```

Controller 존재 여부는 /system_event가 아니라 Bridge의 Action Server 연결 상태로 판단한다. Action Goal 수락 여부는 별도 Topic 없이 ROS Action Goal Response를 사용한다.

### 로그 조회

최근 로그 조회:
```
curl \
  'http://localhost:5000/api/v1/logs?limit=100'
```

특정 Work Execution 로그 조회:
```
curl \
  'http://localhost:5000/api/v1/logs?work_execution_id=10&limit=100'
```

특정 Operation Execution 로그 조회:
```
curl \
  'http://localhost:5000/api/v1/logs?operation_execution_id=101&limit=100'
```

지원하는 조회 조건:

- work_execution_id
- operation_execution_id
- robot_id
- limit: 1~500

---

## 12. 기본 검증

등록된 Route 확인:

```bash
.venv/bin/python -c "from app import create_app; flask_app=create_app(); print(flask_app.url_map)"
```

Backend와 DB 확인:

```bash
curl -i http://localhost:5000/api/v1/health
curl -s http://localhost:5000/api/v1/work-orders | python -m json.tool
```

Bridge가 실행 중인 경우:

```bash
curl -i http://localhost:5000/api/v1/bridge/health
```

CRUD, 오류 응답 및 실행 연동을 단계별로 확인하려면 [Backend API 검증 가이드](../docs/backend_api_test.md)를 사용한다.

---

## 13. 문제 해결

### `Required environment variable is missing`

`web_app/.env`가 존재하는지와 필수 DB 변수 다섯 개가 설정됐는지 확인한다.

### PostgreSQL 연결 오류

PostgreSQL 서비스, `.env` 접속정보 및 개발 DB 구축 여부를 확인한다. 자세한 내용은 [Database 구축 가이드](../database/README.md)의 문제 해결 절을 참고한다.

### `Address already in use`

5000 포트를 사용 중인 프로세스를 확인하고 기존 Backend를 종료한 뒤 다시 실행한다.

```bash
ss -ltnp | grep ':5000'
```

Bridge의 8001 포트도 같은 방법으로 확인할 수 있다.

### `BRIDGE_UNAVAILABLE`

ROS2 Bridge가 실행 중인지, `.env`의 `BRIDGE_BASE_URL`이 실제 Bridge 주소와 일치하는지 확인한다.

### Frontend는 열리지만 API가 실패함

`GET /`는 정적 파일만 제공하므로 DB나 Bridge 상태를 보장하지 않는다. `/api/v1/health`, Work Order 목록, Bridge health를 각각 확인한다.

---

## 14. Backend 구축 체크리스트

- `web_app`에서 `.venv`를 생성하고 의존성을 설치한다.
- `.env.example`을 `.env`로 복사하고 DB 및 Bridge 설정을 확인한다.
- Database 가이드에 따라 개발 DB와 Seed Data를 구축한다.
- `python run.py`로 Backend를 실행한다.
- Backend health와 Work Order 목록을 확인한다.
- Bridge 작업이 필요하면 ROS2 환경을 source하고 Bridge를 별도로 실행한다.
- 상세 API 검증은 Backend API 검증 가이드 순서대로 수행한다.
