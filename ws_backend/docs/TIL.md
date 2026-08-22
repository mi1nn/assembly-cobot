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
