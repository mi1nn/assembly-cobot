# Backend 구조
처리 과정:
1. routes/work_orders.py
    요청을 받고 get_work_orders() 호출

2. services/work_order_service.py
    조회 쿼리를 만들고 SQLAlchemy를 통해 실행

3. models/work_order.py
    work_order 테이블의 조회 결과를 WorkOrder 객체로 변환

4. services/work_order_service.py
    WorkOrder 객체 목록을 Route에 반환

5. routes/work_orders.py
    객체를 JSON으로 변환하고 HTTP 200 응답

---
## 파일별 역할 요약

| 위치 | 역할 | 알아야 하는 것 |
|---|---|---|
| models/ | DB 테이블 매핑 | SQLAlchemy, PostgreSQL |
| services/ | 업무 규칙과 데이터 처리 | 모델, 트랜잭션, 외부 시스템 |
| routes/ | HTTP API 처리 | Flask, JSON, HTTP 상태 코드 |
| config.py | 환경별 설정 | .env, DB 접속정보 |
| extensions.py | Flask 확장 객체 | DB 객체 |
| app/__init__.py | 앱 조립 | 설정, DB, Blueprint |0
| run.py | 서버 실행 | create_app() |

- Route는 HTTP에 집중
- Service는 업무 처리에 집중
- Model은 DB 구조에 집중

extensions.py와 models/ 차이?
- DB 연결 도구 자체와 DB 테이블의 표현
- extensions.py : DB를 사용하기 위한 공용 도구인 db를 생성
- models/ : 그 db를 사용해서 각 테이블을 Python 클래스로 정의

db는 SQLAlchemy 기능을 제공하는 공용 객체 - db.Model, db.Column, db.String, db.session, db.select() 등 사용 가능

---
## SQLAlchemy 설명
- 데이터베이스와 Python을 함께 사용하는 데 필요한 포괄적인 도구 모음
- 여러 가지 기능 영역을 제공하며, 각 영역은 개별적으로 또는 조합하여 사용할 수 있다.
### 객체 관계형 매퍼(ORM)과 코어(Core)

#### 코어
SQL및 데이터베이스 통합 및 설명 서비스 전반이 포함되어 있다. SQL 표현 언어가 포함되어 있다.
- SQL 표현 언어는 ORM 패키지와는 별개로 독립적인 툴킷으로, 조합 가능한 객체로 표현되는 SQL 표현식을 구성하는 시스템을 제공한다.
- 스키마 중심적인 데이터베이스 관점과 불변성을 기반으로 하는 프로그래밍 방식을 제공한다.

#### ORM
Core를 기반으로 구축되어 데이터베이스 스키마에 매핑된 도메인 객체 모델을 사용하는 방법을 제공한다.
- SQL문은 Core를 사용할 때와 대부분 동일한 방식으로 구성되지만, DML 작업(삽입, 업데이트, 삭제)은 'Unit of Work'라는 패턴을 사용하여 자동화된다.
- Unit of Work 패턴은 변경 가능한 객체의 상태 변화를 INSERT, UPDATE, DELETE 구문으로 변환하고, 해당 객체를 기반으로 호출된다.
- ORM은 Core 방식을 기반으로 도메인 중심적인 데이터베이스 관점과 명시적으로 객체 지향적이며 가변성을 활용하는 프로그래밍 방식을 구축한다. 상태 중심적인 특징을 가지고 있다.

전체적인 사용 방법 자체는 수업에서 배웠던 psycopg2로 exectute 만들고, 하는 방식과 상당히 유사한 느낌이다.
---

## Step 4. Flask ↔ PostgreSQL 연결

### 환경 설정

- 프로젝트 루트에 `.venv`를 만들고 Backend 의존성을 시스템 Python과 분리했다.
- `python-dotenv`로 루트 `.env`의 DB 접속정보를 읽는다.
- `Config` 클래스가 환경변수를 Flask-SQLAlchemy에서 사용하는 `SQLALCHEMY_DATABASE_URI`로 변환한다.
- `URL.create()`를 사용하면 DB 비밀번호에 특수문자가 있어도 안전하게 URL을 구성할 수 있다.
- .env → Config → Flask application config

### Application Factory와 DB 초기화

`app/__init__.py`의 `create_app()`은 Flask 애플리케이션을 생성하고 조립하는 Application Factory이다.

Flask 앱 생성 → Config 적용 → db.init_app(app) → Blueprint 등록 → 완성된 앱 반환

`run.py`는 `create_app()`으로 완성된 앱을 가져와 서버를 실행하는 진입점(`main.py` 같은 역할)

`app/extensions.py`의 `db = SQLAlchemy()`는 모델 정의, 쿼리, 세션 등의 기능을 제공하는 공용 객체이다. 특정 테이블이나 실제 데이터가 아니며, `db.init_app(app)`을 호출하면 Flask 앱의 DB 설정과 연결된다.

### WorkOrder 모델과 조회

`app/models/work_order.py`에서 PostgreSQL의 `work_order` 테이블을 `WorkOrder` 클래스로 매핑했다.

모델은 DB 데이터를 전부 Python 메모리에 복제하는 것이 아니라 테이블명, 컬럼, 타입, PK, FK 같은 구조를 설명하는 설계도이다. 실제 데이터는 쿼리를 실행할 때 필요한 범위만 가져온다.

모델에 전체 컬럼을 매핑해도 쿼리에서는 필요한 데이터만 선택할 수 있다.
일반적으로 CRUD를 사용할 때, 실제 DB와 동일하게 모든 Column, 데이터 타입, Unique, NULL 허용 규칙, default 값 등을 통일해야 한다.

```python
# 조건에 맞는 행만 조회
db.select(WorkOrder).where(WorkOrder.status == "READY")

# 필요한 컬럼만 조회
db.select(
    WorkOrder.work_order_id,
    WorkOrder.order_number,
    WorkOrder.status,
)
```

Step 4 완료 내용:

- `.env`에서 DB 접속정보 로딩
- Flask 앱에 Config 적용
- Flask-SQLAlchemy 초기화
- 기존 `work_order` 테이블 모델 매핑
- PostgreSQL의 실제 Work Order 조회 성공

---

## Step 5. Work Order CRUD API

현재 Step 5는 전체 CRUD 중 **Work Order 목록 조회 API**까지 구현했다.

### Service 계층

`app/services/work_order_service.py`의 `get_work_orders()`에서 조회 쿼리를 만들고 실행한다.

```python
statement = (
    db.select(WorkOrder)
    .order_by(
        WorkOrder.priority.asc(),
        WorkOrder.created_at.desc(),
    )
)

return db.session.scalars(statement).all()
```

Service는 HTTP 요청이나 JSON 응답을 처리하지 않고 업무 규칙과 DB 처리에 집중한다. 반환값은 JSON이 아니라 `WorkOrder` 객체의 리스트이다.

### JSON 변환과 Route

SQLAlchemy의 `WorkOrder` 객체는 `jsonify()`가 직접 직렬화할 수 없으므로 `to_dict()` 메서드를 작성했다.

- 일반 컬럼은 딕셔너리 값으로 변환한다.
- `datetime`은 `isoformat()`을 사용해 문자열로 변환한다.
- 값이 없는 날짜는 `None`, 즉 JSON의 `null`로 변환한다.

`app/routes/work_orders.py`에 다음 API를 구현했다.(GET /api/v1/work-orders)

Route는 Service 결과를 딕셔너리로 변환하고 JSON 응답과 HTTP 상태 코드를 결정한다. Work Order가 없으면 오류가 아니므로 빈 배열과 `200 OK`를 반환한다.

Route는 `app/__init__.py`에서 Blueprint로 등록해야 활성화된다.

```text
GET /api/v1/work-orders
  ↓
Route → Service → Model → PostgreSQL
  ↓
WorkOrder 객체 목록 → to_dict() → JSON + HTTP 200
```

### Step 5 최종 진행 상태

이후 단일 조회, 생성, 부분 수정까지 구현하여 가이드의 Work Order CRUD 범위를 완료했다.

```text
GET    /api/v1/work-orders
GET    /api/v1/work-orders/{id}
POST   /api/v1/work-orders
PATCH  /api/v1/work-orders/{id}
```

DB 구조 변경에 따라 이전의 `installation_target_id`는 `installation_id`로 변경했다. DB, SQLAlchemy 모델, Service 함수 인자, Route 요청 JSON의 필드 이름이 모두 같아야 한다.

---
--- 

## Step 6. HTML/JavaScript Dashboard 연결

### Frontend 파일의 역할

```text
frontend/
├── index.html   화면에 무엇을 표시할지 정의
├── styles.css   화면을 어떻게 표시할지 정의
└── app.js       사용자 동작과 API 호출을 정의
```

### Flask에서 정적 파일 제공

`create_app()`에서 Flask의 정적 파일 위치를 `frontend`로 지정했다.

```python
app = Flask(
    __name__,
    static_folder="../frontend",
    static_url_path="/static",
)
```

두 설정의 차이:

```text
static_folder     서버 파일시스템의 실제 디렉터리
static_url_path   브라우저가 요청하는 URL Prefix
```

따라서 브라우저 요청과 실제 파일이 다음처럼 연결된다.

```text
/static/styles.css → frontend/styles.css
/static/app.js      → frontend/app.js
```

`pages_bp`는 API가 아닌 HTML 페이지 Route를 담당한다.

```python
@pages_bp.get("/")
def index():
    return current_app.send_static_file("index.html")
```

`current_app`은 Application Factory가 만든 현재 Flask 앱을 가리킨다. `pages_bp`도 다른 Blueprint와 마찬가지로 `create_app()`에서 등록해야 활성화된다.

```text
GET /
  ↓
pages.index()
  ↓
frontend/index.html
```

Frontend와 API를 같은 Flask 서버에서 제공했기 때문에 현재 단계에서는 별도 CORS 설정이 필요하지 않다.

### HTML 구조

Dashboard에는 다음 요소를 구성했다.

- Work Order 생성 Form
- Work Order 목록 영역
- 목록 새로고침 버튼
- Robot 상태 표시 영역

JavaScript가 HTML 요소를 찾을 수 있도록 고유한 `id`를 지정했다.

```text
work-order-form    Work Order 생성 Form
work-order-list    Work Order 목록이 들어갈 영역
refresh-button     목록을 다시 조회하는 버튼
robot-status       Robot 상태 표시 영역
form-message       생성 성공/실패 메시지 영역
```

Form 입력의 `name`은 `FormData`와 Backend 요청 JSON의 Key로 사용된다.

```html
<input name="installation_id">
```

```javascript
formData.get("installation_id");
```

### CSS에서 배운 점

- `box-sizing: border-box`는 width 계산에 padding과 border를 포함한다.
- `display: flex`는 제목과 버튼처럼 한 줄에 배치할 요소에 사용한다.
- `display: grid`는 Form과 Work Order 카드 목록처럼 반복적인 레이아웃에 사용한다.
- `data-status` 속성을 이용해 Work Order 상태별 Badge 색상을 지정했다.
- `:disabled`, `:hover`, `:focus`로 버튼과 입력 요소의 상태별 스타일을 표현했다.

예:

```css
.status-badge[data-status="COMPLETED"] {
    background-color: #d1fae5;
    color: #047857;
}
```

### DOMContentLoaded와 이벤트 등록

```javascript
document.addEventListener("DOMContentLoaded", () => {
    // 버튼과 Form 이벤트 등록
    // 최초 Work Order 조회
});
```

`DOMContentLoaded`는 브라우저가 HTML 구조를 모두 만든 뒤 발생한다. HTML 요소가 만들어지기 전에 `getElementById()`를 호출하는 문제를 피할 수 있다.

`"use strict"`는 JavaScript 엄격 모드 지시문이며 파일의 첫 실행문보다 앞에 있어야 한다. 현재 코드에서도 상수 선언보다 위로 배치하는 것이 올바르다.

### Work Order 목록 조회

`loadWorkOrders()`에서 Fetch API로 Backend를 호출했다.

```javascript
const response = await fetch(
    "/api/v1/work-orders",
    {
        method: "GET",
        headers: {
            "Accept": "application/json",
        },
    },
);
```

`fetch()`는 Promise를 반환한다. `async/await`를 사용하면 비동기 요청을 순차 코드처럼 읽기 쉽게 작성할 수 있다.

fetch 요청 → HTTP 응답 대기 → response.json() → success 및 상태 코드 확인 → renderWorkOrders()

HTTP 요청이 성공했는지는 두 가지를 함께 확인했다.

```javascript
if (!response.ok || !responseData.success) {
    throw new Error(...);
}
```

- `response.ok`: HTTP 상태 코드가 200번대인지 확인
- `responseData.success`: Backend 공통 응답의 업무 처리 성공 여부 확인

`try/catch/finally`의 역할:

- try      정상 API 호출과 렌더링
- catch    네트워크/API 오류 처리
- finally  성공 여부와 관계없이 버튼 상태 복구

### DOM으로 Work Order 렌더링

API로 받은 배열을 순회하며 `document.createElement()`로 Work Order 카드를 만들었다.

```text
renderWorkOrders()
  ↓
createWorkOrderCard()
  ↓
createDetail()
```

`replaceChildren()`은 이전 목록이나 로딩 메시지를 제거한다. 데이터가 빈 배열이면 오류가 아니라 "등록된 Work Order가 없습니다"를 표시한다.

DB에서 받은 문자열은 `innerHTML` 대신 `textContent`로 표시했다.

```javascript
title.textContent = workOrder.title;
```

`textContent`는 데이터 안에 HTML이나 JavaScript가 있어도 실행하지 않고 글자로 표시하므로 XSS 위험을 줄인다.

### Work Order 생성

Form의 기본 제출은 페이지를 새로고침하므로 이를 막았다.

```javascript
event.preventDefault();
```

`FormData`로 입력값을 읽고 Backend 요청 객체로 변환했다. HTML의 number 입력도 JavaScript에서는 문자열이므로 `Number()` 변환이 필요하다.

```javascript
const requestData = {
    order_number: formData.get("order_number").trim(),
    installation_id: Number(formData.get("installation_id")),
    priority: Number(formData.get("priority")),
};
```

JavaScript 객체는 `JSON.stringify()`로 JSON 문자열로 변환하여 전송한다.

```javascript
fetch("/api/v1/work-orders", {
    method: "POST",
    headers: {
        "Content-Type": "application/json",
    },
    body: JSON.stringify(requestData),
});
```

생성 성공 시 Form을 초기화하고 `loadWorkOrders()`를 다시 호출하여 새 데이터를 화면에 반영했다.

### Work Order 상태 수정

카드에 상태 Select와 저장 버튼을 만들고 PATCH API와 연결했다.

```javascript
fetch(`/api/v1/work-orders/${workOrderId}`, {
    method: "PATCH",
    headers: {
        "Content-Type": "application/json",
    },
    body: JSON.stringify({status}),
});
```

현재 상태 수정 UI는 CRUD와 API 통신 검증용이다. 최종 시스템에서는 사용자가 모든 상태를 임의로 선택하지 않도록 변경해야 한다.

```text
사용자/관리자: CREATED → READY 또는 CANCELLED
실행 시스템:   READY → RUNNING → COMPLETED 또는 FAILED
```

상태 전이 검증은 Frontend뿐 아니라 Backend Service에서도 수행해야 한다. API는 브라우저 외부에서도 직접 호출할 수 있기 때문이다.

### Step 6 완료 내용

- Flask가 `index.html`, CSS, JavaScript를 제공
- Dashboard에서 Work Order 목록 조회
- 로딩, 빈 목록, 오류 상태 표시
- Dashboard에서 Work Order 생성
- Dashboard에서 Work Order 상태 수정
- 생성·수정 후 목록 자동 갱신

Dashboard 디자인과 최종 상태 변경 UI는 실행 데이터가 확정되는 Step 11 이후 다시 개선할 예정이다.

---

## Step 7. ROS2 Bridge Node 구축

### Bridge의 역할

ROS2 Bridge는 HTTP 기반 Backend와 ROS2 기반 Robot Control 사이에서 인터페이스를 변환한다.

```text
Flask Backend
    ↓ HTTP/REST
ROS2 Bridge
    ↓ ROS2 Action/Topic
Robot Control
```

현재 Step 7에서는 Robot Control Action을 호출하지 않고 다음 기능까지만 구현했다.

- ROS2 Node 실행
- Bridge HTTP 서버 실행
- Bridge 상태 조회
- 작업 요청 형식 검증
- HTTP Thread에서 ROS2 Main Thread로 요청 전달

### ROS2 Node와 Flask HTTP Server 동시 실행

`rclpy.spin(node)`와 `Flask.run()`은 모두 실행 흐름을 계속 점유하는 Blocking 함수다. 같은 Thread에서 순서대로 실행하면 먼저 실행한 함수 때문에 나머지 함수가 시작되지 않는다.

따라서 다음 구조로 분리했다.

```text
Main Thread
└── rclpy.spin(node)

Daemon Thread
└── Flask HTTP Server (:8001)
```

```python
http_thread = Thread(
    target=run_http_server,
    args=(http_app,),
    daemon=True,
)
```

`daemon=True`이면 Main Thread가 종료될 때 HTTP Thread도 함께 종료된다. Flask의 reloader는 별도 프로세스를 만들 수 있으므로 ROS2와 함께 실행할 때는 `use_reloader=False`로 설정했다.

### Queue를 사용한 Thread 간 데이터 전달

Flask Route는 HTTP Thread에서 실행되고 ROS2 Timer Callback은 Main Thread에서 실행된다. 서로 다른 Thread가 공유 데이터를 직접 변경하면 Race Condition이 발생할 수 있다.

`Queue`를 사용하여 HTTP 요청을 ROS2 Thread로 전달했다.

```text
POST /jobs
  ↓ Flask Thread
job_queue.put(job)
  ↓ Thread-safe Queue
ROS2 Timer (0.1초)
  ↓
job_queue.get_nowait()
```

```python
self.create_timer(
    0.1,
    self.process_job_queue,
)
```

Timer는 0.1초마다 Queue를 확인한다. Queue가 비어 있으면 `Empty` 예외를 처리하고 종료하며, 작업이 있으면 Bridge 상태와 마지막 작업을 갱신하고 ROS2 로그를 출력한다.

`task_done()`은 Queue에서 가져온 작업 처리가 끝났음을 표시한다.

### Lock을 사용한 공유 상태 보호

Bridge의 `_status`와 `_last_job`은 Flask Thread와 ROS2 Thread가 함께 접근한다. `Lock`으로 읽기와 쓰기를 보호했다.

```python
with self._state_lock:
    self._status = "JOB_RECEIVED"
    self._last_job = job
```

Lock이 없으면 한 Thread가 값을 변경하는 도중 다른 Thread가 불완전한 상태를 읽을 수 있다.

### Bridge HTTP API

```text
GET  /health  Bridge와 ROS2 Node 생존 확인
GET  /status  Queue와 마지막 작업 상태 조회
POST /jobs    작업 요청 접수
```

`GET /health`는 Bridge 서비스명과 ROS2 Node 이름을 반환한다.

`GET /status`는 다음 정보를 반환한다.

```text
status        현재 Bridge 상태
pending_jobs  Queue에 남아 있는 작업 수
last_job      가장 최근 처리한 작업
```

`POST /jobs`의 요청 형식:

```json
{
  "work_order_id": 1,
  "operation_id": 1
}
```

검증 내용:

- 요청 Body가 JSON 객체인지 확인
- `work_order_id`, `operation_id` 필수값 확인
- ID가 Boolean이 아닌 양의 정수인지 확인

Python에서 `bool`은 `int`의 하위 타입이므로 별도로 제외했다.

```python
return (
    isinstance(value, int)
    and not isinstance(value, bool)
    and value > 0
)
```

### 비동기 접수와 HTTP 202

Bridge는 작업을 Queue에 넣은 직후 Robot 실행 결과를 기다리지 않고 응답한다.

```text
202 Accepted
```

`202`는 작업이 완료됐다는 뜻이 아니라 요청을 접수했다는 뜻이다. 각 요청에는 `uuid4()`로 `bridge_job_id`를 발급하고, UTC 기준 `received_at`을 기록한다.

```python
job = {
    "bridge_job_id": str(uuid4()),
    "received_at": datetime.now(timezone.utc).isoformat(),
}
```

### Backend와 Bridge의 책임 구분

현재 Bridge는 요청 ID가 양의 정수인지 확인하지만 실제 DB에 존재하는지는 확인하지 않는다.

```text
Backend
- Work Order와 Operation 존재 여부 확인
- 현재 상태와 실행 가능 여부 확인
- DB Transaction 관리

Bridge
- HTTP 요청 형식 확인
- ROS2 명령으로 변환
- Action Feedback/Result를 HTTP Callback으로 변환
```

### 실행 및 확인

```bash
source /opt/ros/jazzy/setup.bash
cd ros2_ws
colcon build --symlink-install --packages-select ros2_bridge
source install/setup.bash
ros2 run ros2_bridge bridge_node
```

ROS2 Node 확인:

```bash
ros2 node list
```

HTTP 확인:

```bash
curl http://localhost:8001/health
curl http://localhost:8001/status
curl -X POST http://localhost:8001/jobs \
  -H "Content-Type: application/json" \
  -d '{"work_order_id":1,"operation_id":1}'
```

### Step 7 완료 내용

- `ament_python` 기반 `ros2_bridge` 패키지 생성
- `ros2 run` Entry Point 구성
- `/ros2_bridge` Node 실행
- Flask HTTP 서버를 별도 Daemon Thread로 실행
- `/health`, `/status`, `/jobs` API 구현
- Queue로 HTTP 요청을 ROS2 Main Thread에 전달
- Lock으로 Bridge 공유 상태 보호
- 유효한 작업 요청에 `202 Accepted` 반환
- ROS2 로그에서 수신 작업 확인

현재는 Action Client가 없으므로 `JOB_RECEIVED` 이후 실제 로봇 작업은 실행되지 않는다. 다음 Step 8에서는 Flask Backend가 DB의 Work Order와 Operation을 확인한 뒤 Bridge의 `POST /jobs`를 호출하도록 연결한다.

---

## Step 8. Flask Backend ↔ ROS2 Bridge 연결

### 전체 흐름

Step 8에서는 Flask Backend가 DB의 Work Order와 Operation을 검증한 뒤 ROS2 Bridge에 HTTP 작업 요청을 전달하도록 구현했다.

```text
POST /api/v1/work-orders/{id}/execute
  ↓
Work Order 존재 여부 및 READY 상태 확인
  ↓
Operation이 같은 Installation 소속인지 확인
  ↓
Backend → POST http://127.0.0.1:8001/jobs
  ↓
Bridge Queue에 작업 접수
  ↓
Backend가 202 Accepted 반환
```

아직 ROS2 Action과 Robot Control은 연결하지 않는다. 이번 단계의 목표는 Backend와 Bridge 사이의 HTTP 통신을 완성하는 것이다.

### Bridge 접속 설정

Bridge 주소와 Timeout은 환경마다 달라질 수 있으므로 `.env`에서 관리한다.

```env
BRIDGE_BASE_URL=http://127.0.0.1:8001
BRIDGE_TIMEOUT_SECONDS=3
```

`Config`에서는 URL 끝의 `/`를 제거하여 경로를 붙일 때 `//health` 또는 `//jobs`가 되지 않도록 한다.

```python
BRIDGE_BASE_URL = os.getenv(
    "BRIDGE_BASE_URL",
    "http://127.0.0.1:8001",
).rstrip("/")
```

Timeout을 설정하지 않으면 Bridge가 응답하지 않을 때 Backend 요청도 계속 대기할 수 있다.

---

### Step 8-1. Operation 조회와 Bridge Client

#### Operation 모델

`app/models/operation.py`에서 PostgreSQL의 `operation` 테이블을 SQLAlchemy 모델로 매핑했다.

주요 필드:

```text
operation_id     Operation PK
installation_id 소속 Installation
code/name        Operation 식별 정보
sequence         실행 순서
parameter        로봇 실행 파라미터 JSONB
components       작업 대상 부품 JSONB
```

PostgreSQL의 JSONB 컬럼은 다음 타입으로 매핑했다.

```python
from sqlalchemy.dialects.postgresql import JSONB
```

```python
parameter = db.Column(JSONB)
components = db.Column(JSONB, nullable=False)
```

JSONB를 사용하면 Python에서는 `dict`와 `list` 형태로 작업 파라미터와 부품 데이터를 다룰 수 있다.

현재 `Installation` 모델이 없으므로 SQLAlchemy 모델에는 Foreign Key를 선언하지 않았다. 실제 PostgreSQL Foreign Key는 그대로 유지되며, 추후 `Installation` 모델을 만들면 ORM Foreign Key와 Relationship을 추가한다.

`app/models/__init__.py`에서 `Operation`을 import하여 다른 코드가 다음처럼 사용할 수 있게 했다.

```python
from app.models import Operation
```

#### Operation 소속 검사

`get_operation_for_installation()`은 Operation ID만 조회하지 않고 Installation ID도 함께 검사한다.

```python
statement = db.select(Operation).where(
    Operation.operation_id == operation_id,
    Operation.installation_id == installation_id,
)
```

이 검사가 필요한 이유:

```text
Work Order A의 installation_id = 1
Operation B의 installation_id = 2

Operation B가 DB에 존재하더라도
Work Order A의 작업으로 실행하면 안 됨
```

조회 결과가 정확히 한 건이면 Operation 객체를, 없으면 `None`을 반환한다.

```python
.scalar_one_or_none()
```

#### Bridge Health 확인

`bridge_service.py`는 Backend에서 Bridge HTTP API를 호출하는 역할을 담당한다.

```text
get_bridge_health()   GET  Bridge /health
submit_bridge_job()   POST Bridge /jobs
```

Bridge 관련 오류를 두 종류로 구분했다.

```python
class BridgeConnectionError(RuntimeError):
    pass

class BridgeResponseError(RuntimeError):
    pass
```

```text
BridgeConnectionError
- Bridge 프로세스가 꺼짐
- 연결 거부
- Timeout
- 네트워크 오류

BridgeResponseError
- 예상하지 않은 HTTP 상태
- 잘못된 JSON
- success=false
- data 형식 오류
```

`ConnectionRefusedError`가 발생했을 때 `BridgeConnectionError`로 변환되는 것은 예외 처리가 의도대로 동작한 것이다. Bridge를 별도 프로세스로 실행한 뒤 다시 호출해야 한다.

#### Bridge Job 전송

`submit_bridge_job()`은 Python Dictionary를 Bridge의 `/jobs`로 전송한다.

```python
request_data = {
    "work_order_id": work_order_id,
    "operation_id": operation_id,
}

response = requests.post(
    jobs_url,
    json=request_data,
    timeout=timeout_seconds,
)
```

`requests.post(..., json=request_data)`는 다음을 자동 처리한다.

```text
Python dict → JSON 문자열
Content-Type: application/json 설정
```

Bridge가 작업을 접수하면 HTTP `202`와 `bridge_job_id`를 반환한다. Backend는 HTTP 상태, 공통 `success`, `data` 타입을 모두 검사한다.

```text
HTTP 202
+ success=true
+ data가 dict
= 정상 접수
```

---

### Step 8-2. Work Order Execute API

구현한 API:

```text
POST /api/v1/work-orders/{work_order_id}/execute
```

요청 Body:

```json
{
  "operation_id": 1
}
```

#### 1. 요청 JSON과 ID 검증

요청 Body가 JSON 객체인지 확인하고 `operation_id`가 Boolean이 아닌 양의 정수인지 검사한다.

```python
if (
    not isinstance(operation_id, int)
    or isinstance(operation_id, bool)
    or operation_id <= 0
):
```

실패 시:

```text
400 INVALID_JSON
400 INVALID_OPERATION_ID
```

#### 2. Work Order 존재 여부 확인

```python
work_order = get_work_order_by_id(
    work_order_id
)
```

해당 ID가 없으면 Bridge를 호출하지 않고 종료한다.

```text
404 WORK_ORDER_NOT_FOUND
```

#### 3. 실행 가능 상태 검사

현재는 `READY` 상태의 Work Order만 실행할 수 있다.

```python
if work_order.status != "READY":
```

```text
CREATED   실행 불가
READY     실행 가능
RUNNING   중복 실행 불가
COMPLETED 실행 불가
FAILED    재실행 정책 필요
CANCELLED 실행 불가
```

실행할 수 없는 상태이면 다음을 반환한다.

```text
409 WORK_ORDER_NOT_READY
```

HTTP `409 Conflict`는 요청 형식은 올바르지만 현재 리소스 상태와 충돌한다는 뜻이다.

#### 4. Operation 소속 확인

Work Order의 `installation_id`와 요청 Operation의 소속을 함께 검사한다.

```python
operation = get_operation_for_installation(
    operation_id=operation_id,
    installation_id=work_order.installation_id,
)
```

Operation이 없거나 다른 Installation에 속하면 다음을 반환한다.

```text
404 OPERATION_NOT_FOUND
```

#### 5. Bridge 호출과 오류 변환

검증을 모두 통과한 후에만 Bridge를 호출한다.

```python
bridge_data = submit_bridge_job(
    work_order_id=work_order_id,
    operation_id=operation_id,
)
```

Bridge 오류를 Backend HTTP 응답으로 변환한다.

```text
BridgeConnectionError → 503 BRIDGE_UNAVAILABLE
BridgeResponseError   → 502 BRIDGE_JOB_REJECTED
```

상태 코드 의미:

```text
502 Bad Gateway
Backend가 연결한 Bridge에서 잘못된 응답을 받음

503 Service Unavailable
Bridge에 연결할 수 없어 현재 실행 요청을 처리할 수 없음
```

#### 6. 정상 접수 응답

Bridge가 작업을 Queue에 접수하면 Backend도 `202 Accepted`를 반환한다.

```json
{
  "success": true,
  "data": {
    "work_order_id": 2,
    "operation": {
      "operation_id": 1,
      "installation_id": 1,
      "sequence": 1
    },
    "bridge": {
      "accepted": true,
      "bridge_job_id": "UUID"
    }
  },
  "error": null
}
```

`202`는 Robot 작업 완료가 아니라 Backend와 Bridge가 요청을 검증하고 접수했다는 뜻이다.

### Step 8에서 확인한 실행 순서

터미널 1에서 Bridge 실행:

```bash
source /opt/ros/jazzy/setup.bash
source ros2_ws/install/setup.bash
ros2 run ros2_bridge bridge_node
```

터미널 2에서 Backend 실행:

```bash
source .venv/bin/activate
python run.py
```

READY Work Order에 실행 요청:

```bash
curl -X POST \
  http://localhost:5000/api/v1/work-orders/2/execute \
  -H "Content-Type: application/json" \
  -d '{"operation_id":1}'
```

성공 시 다음 두 곳에서 확인할 수 있다.

```text
Backend 응답: HTTP 202 + bridge_job_id
Bridge 로그:   work_order_id와 operation_id 출력
```

Bridge 상태 확인:

```bash
curl http://127.0.0.1:8001/status
```

### Backend와 Bridge의 검증 범위

```text
Backend
- Work Order가 DB에 존재하는지 확인
- Work Order가 READY인지 확인
- Operation이 DB에 존재하는지 확인
- 같은 Installation 소속인지 확인

Bridge
- work_order_id와 operation_id 형식 확인
- 작업 UUID 발급
- Thread-safe Queue에 작업 저장
- 이후 ROS2 Action Goal로 변환
```

Bridge가 Backend DB를 직접 조회하지 않게 하여 시스템 책임을 분리했다.

### 현재 제한사항

현재는 하나의 실행 요청에 Operation 한 건만 전달한다.

```json
{
  "operation_id": 1
}
```

실제 Work Order에는 여러 Operation이 있으므로 향후에는 sequence 순서로 Operation 목록을 전달하는 구조가 필요하다.

아직 구현하지 않은 항목:

- `work_execution` 생성
- `operation_execution` 생성
- Work Order의 `RUNNING` 변경
- 중복 실행의 트랜잭션 차단
- ROS2 Action Goal 전송
- Action Feedback과 Result 처리
- 성공/실패 결과 DB 기록

Bridge가 요청을 수락해도 현재 Work Order는 `READY`를 유지한다. `202` 응답만으로 실제 Robot 실행이 시작됐다고 판단하면 안 된다.

### Step 8 완료 내용

- Operation SQLAlchemy 모델 구현
- Work Order와 Operation의 Installation 관계 검증
- Backend에서 Bridge Health 확인
- Backend에서 Bridge `/jobs` 호출
- `POST /api/v1/work-orders/{id}/execute` 구현
- READY 상태 검증
- Bridge 연결/응답 오류 구분
- 정상 작업 접수 시 `202 Accepted`와 `bridge_job_id` 반환
- Bridge Queue와 ROS2 로그에서 요청 수신 확인

다음 Step 9에서는 Bridge를 ROS2 Action Client로 만들고 Robot Control Action Server와 연결한다.
