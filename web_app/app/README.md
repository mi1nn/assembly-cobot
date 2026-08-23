# Backend 개발 환경 설정 (venv)

> 검증 환경: Ubuntu 24.04 / Python 3.12 / ROS2 Jazzy / PostgreSQL 16

## 1. 왜 가상환경을 쓰는가

이 프로젝트의 ROS2 Bridge Node는 하나의 프로세스에서 `rclpy`(ROS2)와 `Flask`(HTTP 서버)를 함께 사용한다.

개발 시에는 가상환경에서 하되, 로컬 환경에서 배포하는 것을 목표로 파일 및 코드를 구성한다.

## 2. 개발/검증 시, venv 생성 및 의존성 설치

최초 1회만 실행한다.

```bash
cd web_app/

# Backend용 venv 생성
python3 -m venv .venv

# 의존성 설치 (requirements.txt 참고)
.venv/bin/python -m pip install -r requirements.txt
```

설치되는 항목 (`requirements.txt`):

| 패키지 | 버전 | 용도 |
|---|---|---|
| Flask | 3.1.3 | Backend API + Bridge 내장 HTTP 서버 |
| Flask-SQLAlchemy | 3.1.1 | Query문을 쉽게 다루기 위함 |
| SQLAlchemy | 2.0.51 | ORM (PostgreSQL 접근) |
| python-dotenv | 1.2.2 | `.env` 환경변수 로딩 |
| psycopg2 | 2.9.9 | PostgreSQL 드라이버 |
| requests | 2.31.0 | Flask → Bridge HTTP 호출 |

## 3. 활성화 / 비활성화

```bash
# 활성화
source .venv/bin/activate

# 비활성화
deactivate
```

## 4. 동작 확인

```bash
# Backend 의존성 확인
.venv/bin/python -c "import flask, flask_sqlalchemy, sqlalchemy, dotenv, psycopg2, requests; print('OK')"

# ROS2 연동 확인 (ros2_bridge 개발 시 필요)
source /opt/ros/jazzy/setup.bash
.venv/bin/python -c "import rclpy; print('rclpy OK')"
```

둘 다 `OK`가 출력되면 준비 완료.

## 5. 주의 사항

- **ROS2를 사용하는 노드 실행 전에는 반드시 `source /opt/ros/jazzy/setup.bash`를 먼저 한다.**
  venv는 시스템 패키지를 "볼 수 있게" 해줄 뿐, ROS2 환경 변수(`PYTHONPATH`, `AMENT_PREFIX_PATH` 등)는 sourcing으로만 설정된다.
- venv 안에서 `pip install`한 패키지는 venv에만 설치되며 시스템 Python을 오염시키지 않는다.
- `.venv/`는 git에 커밋되지 않는다 (`.gitignore`에 포함됨).
- 의존성을 추가했으면 `pip freeze > requirements.txt` 대신, 직접 requirements.txt에 `패키지==버전` 한 줄을 추가한다 (시스템 패키지까지 freeze되는 것을 방지).


---

## 6. Step 4 — Flask ↔ PostgreSQL 연결 확인

### 6.1 사전 조건

아래 명령은 프로젝트 루트(`web_app`)에서 실행한다.

```bash
pwd
source .venv/bin/activate
```

`.env`에는 다음 DB 접속정보가 있어야 한다.

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=robot_automation_db
DB_USER=robot_app
DB_PASSWORD=실제_비밀번호
```

실제 비밀번호가 들어 있는 `.env`는 저장소에 커밋하지 않는다.

### 6.2 Python 의존성 확인

```bash
python -c "import flask, flask_sqlalchemy, sqlalchemy, dotenv, psycopg2; print('Backend dependencies OK')"
```

예상 결과:

```text
Backend dependencies OK
```

설치 버전은 다음 명령으로 확인한다.

```bash
python -c "from importlib.metadata import version; names=['Flask','Flask-SQLAlchemy','SQLAlchemy','python-dotenv','psycopg2']; [print(f'{name}=={version(name)}') for name in names]"
```

### 6.3 Config 로딩 확인

DB 비밀번호를 노출하지 않고 SQLAlchemy 접속 URL을 확인한다.

```bash
python -c "from app.config import Config; print(Config.SQLALCHEMY_DATABASE_URI.render_as_string(hide_password=True))"
```

예상 결과:

```text
postgresql+psycopg2://robot_app:***@localhost:5432/robot_automation_db
```

필수 환경변수가 누락되면 `Required environment variable is missing` 오류가 발생해야 한다.

### 6.4 Flask 앱과 SQLAlchemy 초기화 확인

```bash
python -c "from app import create_app; app=create_app(); print(app.name); print(app.config['SQLALCHEMY_TRACK_MODIFICATIONS'])"
```

예상 결과:

```text
app
False
```

등록된 API Route를 확인한다.

```bash
python -c "from app import create_app; app=create_app(); print(app.url_map)"
```

최소한 다음 Route가 보여야 한다.

```text
/api/v1/health
/api/v1/work-orders
/api/v1/work-orders/<int:work_order_id>
```

### 6.5 PostgreSQL 연결 확인

모델을 사용하지 않고 가장 단순한 SQL로 연결을 확인한다.

```bash
python -c "from sqlalchemy import text; from app import create_app; from app.extensions import db; app=create_app(); ctx=app.app_context(); ctx.push(); print(db.session.execute(text('SELECT 1')).scalar_one()); ctx.pop()"
```

예상 결과:

```text
1
```

`app.app_context()`는 DB 세션이 어느 Flask 애플리케이션의 설정을 사용해야 하는지 알려준다.

### 6.6 WorkOrder 모델 조회 확인

```bash
python -c "from app import create_app; from app.extensions import db; from app.models import WorkOrder; app=create_app(); ctx=app.app_context(); ctx.push(); rows=db.session.scalars(db.select(WorkOrder).order_by(WorkOrder.work_order_id)).all(); print([(row.work_order_id, row.order_number, row.installation_id, row.status) for row in rows]); ctx.pop()"
```

Seed가 적용된 DB라면 `WO-20260821-001`이 포함되어야 한다.

```text
[(1, 'WO-20260821-001', 1, 'COMPLETED'), ...]
```

조회 결과가 빈 배열이라면 연결 실패가 아니라 Seed가 적용되지 않은 상태일 수 있다.

### 6.7 DB 스키마와 CHECK 제약조건 확인

애플리케이션 DB 계정으로 접속한다.

```bash
psql \
  -h localhost \
  -p 5432 \
  -U robot_app \
  -d robot_automation_db
```

테이블 목록:

```sql
\dt
```

현재 스키마는 다음 9개 테이블로 구성된다.

```text
installation
operation
robot
sensor
work_order
work_execution
operation_execution
log
sensor_data
```

Work Order 구조와 제약조건:

```sql
\d work_order
```

모든 CHECK 제약조건 확인:

```sql
SELECT
    conrelid::regclass AS table_name,
    conname,
    pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE connamespace = 'public'::regnamespace
  AND contype = 'c'
ORDER BY conrelid::regclass::text, conname;
```

최소한 다음 제약조건이 보여야 한다.

```text
chk_installation_status
chk_robot_status
chk_work_order_status
chk_work_execution_status
chk_operation_execution_status
chk_log_type
chk_log_severity
```

`schema.sql`만 수정한 뒤 기존 DB에 다시 실행하면 `CREATE TABLE IF NOT EXISTS` 때문에 기존 테이블의 CHECK는 변경되지 않는다. 제약조건이 보이지 않으면 DB Reset 또는 별도 Migration이 필요하다.

종료:

```sql
\q
```

### 6.8 Flask 서버 확인

터미널 1:

```bash
source .venv/bin/activate
python run.py
```

터미널 2:

```bash
curl -i http://localhost:5000/api/v1/health
```

예상 상태 코드:

```text
HTTP/1.1 200 OK
```

Work Order 목록 조회:

```bash
curl -s http://localhost:5000/api/v1/work-orders | python -m json.tool
```

응답 형식:

```json
{
    "success": true,
    "data": [],
    "error": null
}
```

### Step 4 완료 기준

- `.env`가 정상적으로 로딩된다.
- Flask-SQLAlchemy가 Config를 사용해 초기화된다.
- `SELECT 1`이 성공한다.
- `WorkOrder` 모델로 실제 DB 데이터를 조회할 수 있다.
- `GET /api/v1/health`가 `200`을 반환한다.
- `GET /api/v1/work-orders`가 DB 데이터를 JSON으로 반환한다.

---

## 7. Step 5 — Work Order CRUD API 확인

현재 구현 범위는 목록 조회, 단일 조회, 생성, 부분 수정이다. 가이드 범위에 DELETE는 포함하지 않는다.

```text
GET    /api/v1/work-orders
GET    /api/v1/work-orders/{id}
POST   /api/v1/work-orders
PATCH  /api/v1/work-orders/{id}
```

아래 테스트는 Flask 서버가 실행 중인 상태에서 진행한다.

### 7.1 목록 조회

```bash
curl -i http://localhost:5000/api/v1/work-orders
```

확인 사항:

- HTTP 상태 코드가 `200`이다.
- `success`가 `true`이다.
- `data`가 배열이다.
- 각 항목에 `work_order_id`, `order_number`, `installation_id`, `status`가 있다.

### 7.2 단일 조회 성공

Seed Work Order 조회:

```bash
curl -i http://localhost:5000/api/v1/work-orders/1
```

예상 상태 코드:

```text
HTTP/1.1 200 OK
```

### 7.3 존재하지 않는 Work Order 조회

```bash
curl -i http://localhost:5000/api/v1/work-orders/999999
```

예상 상태 코드와 오류 코드:

```text
HTTP/1.1 404 NOT FOUND
WORK_ORDER_NOT_FOUND
```

### 7.4 Work Order 생성

테스트마다 중복되지 않는 작업번호를 만든다.

```bash
VERIFY_ORDER_NUMBER="WO-VERIFY-$(date +%Y%m%d%H%M%S)"
echo "$VERIFY_ORDER_NUMBER"
```

생성 요청:

```bash
curl -i \
  -X POST \
  http://localhost:5000/api/v1/work-orders \
  -H "Content-Type: application/json" \
  -d "{
    \"order_number\": \"$VERIFY_ORDER_NUMBER\",
    \"title\": \"Backend API verification\",
    \"installation_id\": 1,
    \"priority\": 3,
    \"remark\": \"Step 5 verification data\",
    \"created_by\": \"backend-test\"
  }"
```

예상 상태 코드:

```text
HTTP/1.1 201 CREATED
```

응답에서 생성된 `work_order_id`를 확인하고 다음 테스트에 사용한다.

```bash
VERIFY_WORK_ORDER_ID=생성된_ID
```

확인 사항:

- 서버가 `work_order_id`를 생성한다.
- `installation_id`가 요청값 `1`이다.
- 초기 상태가 `CREATED`이다.
- `created_at`, `updated_at`이 생성된다.

### 7.5 생성 데이터 재조회

```bash
curl -s \
  "http://localhost:5000/api/v1/work-orders/$VERIFY_WORK_ORDER_ID" \
  | python -m json.tool
```

생성 요청과 같은 `order_number`, `title`, `installation_id`가 반환되어야 한다.

### 7.6 필수 필드 누락 검사

```bash
curl -i \
  -X POST \
  http://localhost:5000/api/v1/work-orders \
  -H "Content-Type: application/json" \
  -d '{"title":"missing fields test"}'
```

예상 결과:

```text
HTTP/1.1 400 BAD REQUEST
MISSING_REQUIRED_FIELDS
```

### 7.7 중복 작업번호 검사

7.4에서 생성한 작업번호를 다시 사용한다.

```bash
curl -i \
  -X POST \
  http://localhost:5000/api/v1/work-orders \
  -H "Content-Type: application/json" \
  -d "{
    \"order_number\": \"$VERIFY_ORDER_NUMBER\",
    \"title\": \"duplicate test\",
    \"installation_id\": 1
  }"
```

예상 결과:

```text
HTTP/1.1 409 CONFLICT
WORK_ORDER_CONFLICT
```

### 7.8 잘못된 Installation 검사

```bash
curl -i \
  -X POST \
  http://localhost:5000/api/v1/work-orders \
  -H "Content-Type: application/json" \
  -d "{
    \"order_number\": \"${VERIFY_ORDER_NUMBER}-INVALID-INSTALLATION\",
    \"title\": \"invalid installation test\",
    \"installation_id\": 999999
  }"
```

PostgreSQL Foreign Key가 요청을 거절해야 한다.

현재 API의 예상 결과:

```text
HTTP/1.1 409 CONFLICT
WORK_ORDER_CONFLICT
```

### 7.9 Work Order 부분 수정

```bash
curl -i \
  -X PATCH \
  "http://localhost:5000/api/v1/work-orders/$VERIFY_WORK_ORDER_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "priority": 1,
    "status": "READY",
    "remark": "PATCH verification complete"
  }'
```

예상 결과:

```text
HTTP/1.1 200 OK
```

응답에서 다음 값이 변경되어야 한다.

```json
{
    "priority": 1,
    "status": "READY",
    "remark": "PATCH verification complete"
}
```

### 7.10 잘못된 상태 수정 검사

```bash
curl -i \
  -X PATCH \
  "http://localhost:5000/api/v1/work-orders/$VERIFY_WORK_ORDER_ID" \
  -H "Content-Type: application/json" \
  -d '{"status":"UNKNOWN"}'
```

예상 결과:

```text
HTTP/1.1 400 BAD REQUEST
INVALID_STATUS
```

허용 상태:

```text
CREATED
READY
RUNNING
COMPLETED
FAILED
CANCELLED
```

### 7.11 변경 불가능한 필드 검사

```bash
curl -i \
  -X PATCH \
  "http://localhost:5000/api/v1/work-orders/$VERIFY_WORK_ORDER_ID" \
  -H "Content-Type: application/json" \
  -d '{"work_order_id":999}'
```

예상 결과:

```text
HTTP/1.1 400 BAD REQUEST
INVALID_UPDATE_FIELDS
```

### 7.12 존재하지 않는 Work Order 수정

```bash
curl -i \
  -X PATCH \
  http://localhost:5000/api/v1/work-orders/999999 \
  -H "Content-Type: application/json" \
  -d '{"status":"READY"}'
```

예상 결과:

```text
HTTP/1.1 404 NOT FOUND
WORK_ORDER_NOT_FOUND
```

### 7.13 DB에서 최종 결과 확인

```bash
psql \
  -h localhost \
  -p 5432 \
  -U robot_app \
  -d robot_automation_db \
  -c "SELECT work_order_id, order_number, installation_id, priority, status, remark FROM work_order WHERE order_number = '$VERIFY_ORDER_NUMBER';"
```

API 응답과 DB 값이 동일해야 한다.

### 7.14 테스트 데이터 정리(선택)

현재 DELETE API가 없으므로 SQL로 이번 검증에서 생성한 데이터만 제거한다.

삭제 대상을 먼저 확인한다.

```bash
psql \
  -h localhost \
  -p 5432 \
  -U robot_app \
  -d robot_automation_db \
  -c "SELECT work_order_id, order_number FROM work_order WHERE order_number = '$VERIFY_ORDER_NUMBER';"
```

확인된 테스트 데이터만 삭제한다.

```bash
psql \
  -h localhost \
  -p 5432 \
  -U robot_app \
  -d robot_automation_db \
  -c "DELETE FROM work_order WHERE order_number = '$VERIFY_ORDER_NUMBER' AND created_by = 'backend-test';"
```

### Step 5 완료 기준

- 목록 조회가 `200`을 반환한다.
- 단일 조회 성공 시 `200`, 존재하지 않으면 `404`를 반환한다.
- 유효한 생성 요청은 `201`과 `CREATED` 상태를 반환한다.
- 필수 필드 누락은 `400`을 반환한다.
- 중복 작업번호와 잘못된 Foreign Key는 `409`를 반환한다.
- 허용된 필드의 부분 수정은 `200`을 반환한다.
- 잘못된 상태나 변경 불가능한 필드는 `400`을 반환한다.
- 생성 및 수정 결과를 DB에서 다시 조회할 수 있다.
