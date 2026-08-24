# Flask Backend 개발 가이드

## 1. 개요

`web_app/app`은 작업 지시를 관리하고 PostgreSQL 및 ROS2 Bridge를 연결하는 Flask Backend다.

주요 역할은 다음과 같다.

- Work Order 조회, 생성 및 수정
- Work Order 실행 이력과 공정별 실행 이력 생성
- ROS2 Bridge 상태 확인 및 작업 제출
- ROS2 Action 결과 callback 처리
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
   ├── SQLAlchemy ── PostgreSQL :5432
   └── HTTP ──────── ROS2 Bridge :8001
                           │
                           ▼
                     ROS2 Action Server
                           │
                           ▼
                     Robot Controller
```

Flask Backend와 ROS2 Bridge는 서로 다른 프로세스다. Backend는 일반 HTTP 요청과 DB 상태를 관리하고, Bridge는 HTTP 작업을 ROS2 Action으로 변환한다.

작업 결과는 다음 경로로 돌아온다.

```text
ROS2 Action Result
        ↓
ROS2 Bridge
        ↓ POST /api/v1/executions/action-result
Flask Backend
        ↓
PostgreSQL 상태 갱신
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
├── docs/                 # 상세 설계 및 검증 문서
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

현재 SQLAlchemy Model은 `WorkOrder`, `Operation`, `Robot`, `WorkExecution`, `OperationExecution`을 제공한다. 전체 9개 DB Table과 관계는 [Database 구축 가이드](../database/README.md)를 참고한다.

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
curl -s http://localhost:5000/api/v1/work-orders | python -m json.tool
```

---

## 8. API 요약

| Method | Path | 역할 | 주요 성공 코드 |
| --- | --- | --- | --- |
| `GET` | `/` | Frontend 화면 제공 | `200` |
| `GET` | `/api/v1/health` | Backend 상태 확인 | `200` |
| `GET` | `/api/v1/bridge/health` | Backend를 통한 Bridge 상태 확인 | `200` |
| `GET` | `/api/v1/work-orders` | Work Order 목록 조회 | `200` |
| `GET` | `/api/v1/work-orders/{id}` | Work Order 단일 조회 | `200` |
| `POST` | `/api/v1/work-orders` | Work Order 생성 | `201` |
| `PATCH` | `/api/v1/work-orders/{id}` | Work Order 부분 수정 | `200` |
| `POST` | `/api/v1/work-orders/{id}/execute` | Work Order 실행 요청 | `202` |
| `POST` | `/api/v1/executions/action-result` | Bridge의 ROS2 Action 결과 callback | `200` |

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

현재 PATCH API는 허용 상태 집합을 검사하지만 상태 전이 순서 자체를 강제하지는 않는다.

---

## 10. 작업 실행 흐름

Work Order 실행 요청에는 `robot_id`가 필요하다.

```bash
curl -i \
  -X POST \
  http://localhost:5000/api/v1/work-orders/WORK_ORDER_ID/execute \
  -H "Content-Type: application/json" \
  -d '{"robot_id":1}'
```

실행 조건:

- Work Order가 존재하고 상태가 `READY`여야 한다.
- Robot이 존재하고 상태가 `IDLE`이어야 한다.
- Work Order의 `installation_id`에 하나 이상의 Operation이 있어야 한다.
- ROS2 Bridge가 실행 중이며 작업을 받아들여야 한다.

Backend는 하나의 `work_execution`과 모든 공정의 `operation_execution`을 생성한 뒤 첫 Operation을 Bridge에 제출한다. 첫 제출이 성공하면 Work Order, Work Execution, 첫 Operation Execution 및 Robot 상태를 `RUNNING`으로 변경한다.

Bridge가 Action 결과를 callback하면 Backend는 성공 시 다음 PENDING Operation을 제출하고, 남은 Operation이 없으면 전체 실행을 `COMPLETED`로 변경한다. 실패 시 Work Order와 실행을 `FAILED`, Robot을 `IDLE`로 변경한다. 동일한 완료 또는 실패 callback은 이미 처리된 결과로 응답한다.

### 현재 알려진 제한

다음 Operation을 Bridge에 제출하는 callback 경로는 현재 `components` 인자를 전달하지 않아 여러 Operation을 연속 실행할 때 서버 오류가 발생할 수 있다. 첫 Operation 제출과 단일 Operation 실행은 이 문제의 영향을 받지 않는다. 구현이 수정되기 전까지 다중 공정 End-to-End 검증은 완료된 기능으로 간주하지 않는다.

---

## 11. 기본 검증

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

## 12. 문제 해결

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

## 13. Backend 구축 체크리스트

- `web_app`에서 `.venv`를 생성하고 의존성을 설치한다.
- `.env.example`을 `.env`로 복사하고 DB 및 Bridge 설정을 확인한다.
- Database 가이드에 따라 개발 DB와 Seed Data를 구축한다.
- `python run.py`로 Backend를 실행한다.
- Backend health와 Work Order 목록을 확인한다.
- Bridge 작업이 필요하면 ROS2 환경을 source하고 Bridge를 별도로 실행한다.
- 상세 API 검증은 Backend API 검증 가이드 순서대로 수행한다.
