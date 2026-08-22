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

Step 5에서 앞으로 구현할 내용:

- `GET /api/v1/work-orders/{id}`: 단일 조회
- `POST /api/v1/work-orders`: 생성
- `PATCH /api/v1/work-orders/{id}`: 수정
- 요청값 검증과 공통 예외 처리
