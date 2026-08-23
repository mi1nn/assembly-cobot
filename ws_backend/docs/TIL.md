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

---

## Step 9. ROS2 Action으로 Bridge와 Robot 연결

### Step 9의 목표

Step 8까지는 Flask Backend가 Bridge의 HTTP Queue에 작업을 접수하는 것까지만 구현했다. Step 9에서는 Queue에서 꺼낸 작업을 ROS2 Action Goal로 변환하고 Robot 제어 노드로 보내는 흐름을 구현했다.

```text
사용자 요청
→ Flask Backend
→ Bridge HTTP API
→ Bridge Queue
→ ROS2 Action Client
→ Robot Action Server
→ Feedback / Result
```

ROS2 패키지는 하나의 workspace에서 관리할 수 있도록 다음 위치로 정리했다.

```text
assembly-cobot/
├── src/
│   ├── ros2_bridge/
│   ├── solar_panel_interface/
│   └── solar_panel_robot/
└── ws_backend/
```

따라서 workspace를 여러 번 source하고 각각 빌드할 필요 없이 `assembly-cobot`에서 한 번에 빌드할 수 있다.

```bash
cd ~/workspace/assembly-cobot
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
```

### ROS2 Action을 사용한 이유

로봇 작업은 요청 직후 끝나는 일반 함수 호출이 아니다. 수 초 이상 실행되며 진행률, 성공/실패 결과, 취소 기능이 필요하다.

```text
Goal     실행할 작업 요청
Feedback 실행 중 반복해서 전달되는 진행 상태
Result   작업 종료 후 한 번 전달되는 최종 결과
```

Service는 요청과 응답이 한 번씩 오가는 짧은 작업에 적합하고, Action은 진행 상태가 필요한 장시간 작업에 적합하다.

### ExecuteOperation Action 인터페이스

기존 `solar_panel_interface/action/ExecuteOperation.action`을 사용했다.

```text
string work_order_id
string operation_id
solar_panel_interface/Parameter[] parameters
---
bool success
string error_code
string message
---
string current_operation
string status
float32 progress
```

첫 번째 구역은 Goal, 두 번째 구역은 Result, 세 번째 구역은 Feedback이다. DB의 ID는 정수지만 Action 메시지에서는 문자열이므로 Bridge에서 변환한다.

```python
goal.work_order_id = str(job["work_order_id"])
goal.operation_id = str(job["operation_id"])
```

### Mock Action Server 구현

실제 로봇 제어 코드를 바로 연결하면 테스트 과정에서 장비가 움직일 수 있으므로 `solar_panel_robot`에 Mock Action Server를 별도로 구현했다.

```text
main 노드          실제 로봇 제어용
action_server 노드 Action 통신 검증용 Mock Server
```

Mock Server는 Goal을 승인한 후 진행률을 `0, 20, 40, 60, 80, 100` 순서로 Feedback에 담아 발행하고, 마지막에 성공 Result를 반환한다.

```python
feedback.current_operation = request.operation_id
feedback.status = "RUNNING"
feedback.progress = float(progress)
goal_handle.publish_feedback(feedback)
```

작업 성공 처리는 다음 두 부분으로 구성된다.

```python
goal_handle.succeed()

result = ExecuteOperation.Result()
result.success = True
result.error_code = ""
result.message = "Operation completed successfully"
```

`goal_handle.succeed()`는 ROS2 Action 자체의 종료 상태를 성공으로 변경하고, `result.success`는 애플리케이션에서 정의한 작업 결과를 나타낸다.

### asyncio 오류와 처리

처음에는 실행 콜백을 `async def`로 만들고 `await asyncio.sleep(1.0)`을 사용했다. 그러나 현재 rclpy executor에서 일반 Python asyncio event loop가 실행되고 있지 않아 다음 오류가 발생했다.

```text
RuntimeError: no running event loop
```

Mock Server에서는 실행 콜백을 동기 함수로 바꾸고 `time.sleep()`을 사용해 해결했다.

```python
def execute_callback(self, goal_handle):
    time.sleep(1.0)
```

이 방식은 기본 Goal과 Feedback 테스트에는 충분하지만 sleep 중 executor thread를 점유한다. 실제 서버에서 취소 요청이나 여러 콜백을 동시에 처리하려면 `MultiThreadedExecutor`와 callback group을 검토해야 한다.

### Bridge Action Client 구현

Bridge Node에 `ActionClient`를 생성했다.

```python
self.action_client = ActionClient(
    self,
    ExecuteOperation,
    "execute_operation",
)
```

Action 이름인 `execute_operation`은 Client와 Server에서 같아야 한다.

Bridge timer는 주기적으로 Queue를 확인한다. Action Server가 준비되지 않았으면 작업을 꺼내지 않고 `ACTION_SERVER_UNAVAILABLE` 상태로 대기한다. Server가 준비되면 작업 하나를 꺼내 Goal을 비동기로 전송한다.

```python
send_goal_future = self.action_client.send_goal_async(
    goal,
    feedback_callback=self.feedback_callback,
)
send_goal_future.add_done_callback(
    self.goal_response_callback
)
```

Future와 done callback을 사용하므로 결과를 기다리는 동안 프로그램 전체가 멈추지 않는다.

### Action Client 콜백 흐름

```text
send_goal_async()
→ goal_response_callback()
→ feedback_callback() 반복
→ result_callback()
```

`goal_response_callback()`에서는 Server가 Goal을 승인했는지 확인한다. 승인되면 Result Future를 등록한다.

```python
if not goal_handle.accepted:
    # GOAL_REJECTED 처리

result_future = goal_handle.get_result_async()
result_future.add_done_callback(self.result_callback)
```

`feedback_callback()`은 실행 중 여러 번 호출되며 현재 상태와 진행률을 Bridge 상태에 반영한다.

```python
self._status = feedback.status
self._last_job["progress"] = feedback.progress
```

`result_callback()`은 최종 결과에 따라 상태를 변경한다.

```text
result.success == true  → COMPLETED
result.success == false → FAILED
```

### Queue의 순차 실행 제어

Bridge에는 `_goal_in_progress` 변수를 추가했다. Goal 실행 중에는 다음 작업을 Queue에서 꺼내지 않고, Result를 받은 뒤 다음 작업을 처리한다.

```text
Operation 10 실행 중
Operation 11 Queue 대기
Operation 12 Queue 대기
→ 10 완료 후 11 실행
→ 11 완료 후 12 실행
```

공유 상태인 `_status`, `_last_job`, `_goal_in_progress`는 Flask HTTP thread와 ROS2 executor가 함께 접근하므로 Lock으로 보호한다.

### Bridge 직접 통합 테스트

Mock Action Server와 Bridge를 실행하고 Bridge에 직접 작업을 접수했다.

```bash
ros2 run solar_panel_robot action_server
ros2 run ros2_bridge bridge_node

curl -X POST \
  http://127.0.0.1:8001/jobs \
  -H "Content-Type: application/json" \
  -d '{"work_order_id":1,"operation_id":10}'
```

다음 항목을 확인했다.

- HTTP `202 Accepted`와 `bridge_job_id` 반환
- Action Server의 Goal 수신 및 승인
- Bridge가 0%부터 100%까지 Feedback 수신
- Action Server가 성공 Result 반환
- Bridge `/status`가 `COMPLETED`로 변경
- 요청을 연속 전송했을 때 Queue 순서대로 실행

### Flask Backend 전체 통합 테스트

최종적으로 Bridge에 직접 요청하지 않고 기존 Backend 실행 API를 사용했다.

```text
POST /api/v1/work-orders/{work_order_id}/execute
```

```bash
curl -X POST \
  http://127.0.0.1:5000/api/v1/work-orders/1/execute \
  -H "Content-Type: application/json" \
  -d '{"operation_id":10}'
```

전체 처리 순서는 다음과 같다.

```text
1. Work Order 존재 확인
2. Work Order 상태가 READY인지 확인
3. Operation 존재 확인
4. Work Order와 Operation의 installation_id 일치 확인
5. Flask Backend가 Bridge /jobs 호출
6. Bridge가 Queue에 작업 저장
7. Bridge Action Client가 Goal 전송
8. Mock Action Server가 Feedback과 Result 반환
```

Backend의 `202 Accepted`는 실제 로봇 작업 완료가 아니라 Bridge가 실행 요청을 접수했다는 의미다.

### Step 9 완료 내용

- ROS2 패키지를 하나의 workspace로 정리
- 기존 ExecuteOperation Action 인터페이스 확인
- 실제 장비 없이 테스트할 Mock Action Server 구현
- Goal, Feedback, Result 통신 확인
- Bridge에 ROS2 Action Client 구현
- Bridge Queue의 작업을 Action Goal로 변환
- Action Server 미실행 상태 처리
- Goal 승인, Feedback, 성공/실패 Result 처리
- `_goal_in_progress`를 이용한 작업 순차 실행
- Flask Backend부터 Mock Robot까지 전체 경로 통합 테스트

### 현재 제한사항과 다음 단계

현재 Action 결과는 Bridge 메모리에만 저장되며 Backend DB에는 반영되지 않는다. Bridge 프로세스가 종료되면 `/status`의 실행 정보도 사라진다. 또한 Operation의 `parameter` JSONB 값은 아직 Action의 `Parameter[]`로 전달하지 않는다.

---

## Step 10. ROS2 Action 실행 이력을 DB에 반영

### Step 10의 목표

Step 9에서는 Action 결과가 Bridge 메모리에만 남았다. Step 10에서는 실행 요청부터 Action 완료까지의 상태를 PostgreSQL에 기록하도록 확장했다.

```text
실행 요청
→ DB 실행 이력 PENDING
→ Bridge 접수
→ DB 상태 RUNNING
→ ROS2 Action 실행
→ Bridge가 Backend callback 호출
→ DB 상태 COMPLETED 또는 FAILED
```

### 실행 이력 모델

기존 DB의 `robot`, `work_execution`, `operation_execution` 테이블을 SQLAlchemy 모델로 작성하고 `app/models/__init__.py`에 등록했다.

```text
WorkOrder
└── WorkExecution
    └── OperationExecution
```

- `WorkExecution`: Work Order가 특정 Robot에서 실행된 이력
- `OperationExecution`: Work Execution 안에서 개별 Operation이 실행된 이력
- `Robot`: 실행 주체와 현재 가용 상태

Foreign Key가 참조하는 테이블도 SQLAlchemy metadata에 등록되어야 한다. 예를 들어 `work_execution.robot_id`가 `robot.robot_id`를 참조하므로 `Robot` 모델을 import하지 않으면 flush 과정에서 `NoReferencedTableError`가 발생할 수 있다.

### flush와 commit

실행 이력을 만들 때 WorkExecution을 먼저 flush하여 PK를 발급받고, 그 값을 OperationExecution의 Foreign Key로 사용했다.

```python
db.session.add(work_execution)
db.session.flush()

operation_execution = OperationExecution(
    work_execution_id=work_execution.work_execution_id,
    operation_id=operation.operation_id,
)

db.session.add(operation_execution)
db.session.commit()
```

`flush()`는 SQL을 DB로 보내 PK를 발급받지만 트랜잭션을 확정하지 않는다. 마지막 `commit()`이 두 레코드를 함께 확정한다.

실행 번호는 날짜와 UUID 일부를 조합해 생성했다.

```text
EX-20260823-A1B2C3D4E5F6
```

### 실행 요청과 상태 전이

Backend 실행 요청에 `robot_id`를 추가했다.

```json
{
  "operation_id": 1,
  "robot_id": 1
}
```

Backend는 Work Order가 `READY`인지, Operation이 같은 Installation 소속인지, Robot이 `IDLE`인지 검사한다. 검증 후 실행 이력을 먼저 `PENDING`으로 생성한다.

```text
WorkOrder          READY
Robot              IDLE
WorkExecution      PENDING
OperationExecution PENDING
```

Bridge가 요청을 접수하면 다음 상태로 변경한다.

```text
WorkOrder          RUNNING
Robot              RUNNING
WorkExecution      RUNNING
OperationExecution RUNNING
```

Bridge 접수가 실패하면 두 실행 이력을 `FAILED`로 남긴다. 실제 로봇은 시작하지 않았으므로 Work Order는 `READY`, Robot은 `IDLE`을 유지한다.

### 실행 이력 식별자 전달

Action 결과가 어느 DB 레코드에 해당하는지 알 수 있도록 Backend가 Bridge에 다음 값을 전달한다.

```json
{
  "work_order_id": 2,
  "operation_id": 1,
  "work_execution_id": 3,
  "operation_execution_id": 10,
  "robot_id": 1
}
```

Bridge는 모든 ID가 양의 정수인지 검사하고 job Queue에 저장한다. ROS2 Action 인터페이스에 없는 실행 이력 ID는 Bridge가 보관했다가 결과 callback에 사용한다.

### Backend Action 결과 callback

Backend에 다음 API를 추가했다.

```text
POST /api/v1/executions/action-result
```

```json
{
  "work_execution_id": 3,
  "operation_execution_id": 10,
  "success": true,
  "error_code": "",
  "message": "Operation completed successfully"
}
```

Callback API는 ID와 success 형식, 두 실행 이력의 소속 관계, WorkOrder와 Robot 참조, 기존 종료 상태를 검사한다.

같은 성공 결과가 재전송되면 오류 대신 `already_processed: true`를 반환한다. 네트워크 재시도로 같은 요청이 여러 번 도착해도 결과가 같도록 만든 멱등 처리다.

### Action 결과에 따른 DB 변경

Action 성공:

```text
WorkOrder          COMPLETED
Robot              IDLE
WorkExecution      COMPLETED
OperationExecution COMPLETED
```

Action 실패:

```text
WorkOrder          FAILED
Robot              IDLE
WorkExecution      FAILED
OperationExecution FAILED
```

`start_time`은 RUNNING 전환 시점, `end_time`은 COMPLETED 또는 FAILED 전환 시점에 기록한다.

### Bridge에서 Backend 자동 callback

Bridge의 `result_callback()`이 Action Result를 받은 뒤 Backend API를 자동 호출한다.

```text
ROS2 Action Result
→ Bridge result_callback()
→ POST /api/v1/executions/action-result
→ Backend DB 상태 변경
```

Backend 주소는 환경변수로 변경할 수 있고 기본값은 로컬 개발 서버다.

```python
BACKEND_BASE_URL = os.getenv(
    "BACKEND_BASE_URL",
    "http://127.0.0.1:5000",
)
```

Callback 성공 시 Bridge job에 `backend_notified: true`를 기록한다. 실패하면 `CALLBACK_FAILED` 상태와 오류 내용을 메모리에 남긴다.

현재는 callback 자동 재시도와 인증이 없다. 배포 전에는 재시도 Queue, timeout 정책, 공유 토큰 또는 내부 네트워크 인증이 필요하다.

### Operation parameter 전달

Operation의 `parameter` JSONB를 Backend에서 ROS2 Action Server까지 전달하도록 확장했다.

```text
PostgreSQL JSONB
→ Flask JSON
→ Bridge job
→ ROS2 Parameter[]
→ Action Server
```

`Parameter.msg`의 `value`는 문자열이므로 문자열이 아닌 값은 JSON 문자열로 직렬화한다.

```python
if isinstance(value, str):
    parameter.value = value
else:
    parameter.value = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
    )
```

```text
"gripper_post"        → gripper_post
80                    → 80
true                  → true
{"x":0,"y":0,"z":150} → {"x":0,"y":0,"z":150}
```

Mock Action Server 로그에서 tool, speed, force, tcp 등의 DB 설정이 Action Goal까지 전달되는 것을 확인했다.

### Step 10 완료 내용

- Robot, WorkExecution, OperationExecution 모델 구현
- WorkExecution과 OperationExecution을 하나의 트랜잭션으로 생성
- Robot 존재 여부와 IDLE 상태 검증
- 실행 접수 전 PENDING 이력 생성
- Bridge 접수 후 관련 상태를 RUNNING으로 변경
- Bridge 요청에 실행 이력 ID와 Robot ID 포함
- Backend Action 결과 callback API 구현
- Callback 중복 요청에 대한 멱등 처리
- Action 성공/실패 결과를 DB에 자동 반영
- Robot 상태를 Action 종료 후 IDLE로 복구
- Operation JSONB parameter를 ROS2 Parameter 배열로 변환
- Backend부터 Mock Action Server, callback, DB까지 통합 테스트

### 현재 구조의 한계와 Step 11

현재는 Operation 하나를 실행할 때마다 WorkExecution 하나를 생성하고, Operation 하나가 성공하면 Work Order를 바로 `COMPLETED`로 변경한다.

실제 Work Order 실행 구조는 다음과 같아야 한다.

```text
WorkOrder 1개
└── WorkExecution 1개
    ├── OperationExecution(sequence=1)
    ├── OperationExecution(sequence=2)
    └── OperationExecution(sequence=N)
```

Step 11에서는 Installation의 Operation 전체를 sequence 순서로 조회하고 첫 Operation부터 차례로 Bridge에 전달한다. 마지막 Operation까지 성공했을 때만 Work Order를 `COMPLETED`로 변경한다.
