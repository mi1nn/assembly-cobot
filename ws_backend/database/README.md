# PostgreSQL Database Setup

## 1. 개요

본 디렉토리는 로봇 자동화 공정 시스템에서 사용하는 PostgreSQL 데이터베이스의 구축, 초기화 및 재현을 관리한다.

현재 스키마는 설치 정보를 `installation`으로, 작업 대상물을 `operation.components` JSONB로, 이벤트와 오류를 `log`로 통합한 9개 테이블 구조다.

`setup_db.sh`를 실행하면 다음 작업을 수행한다.

```text
PostgreSQL 설치 확인
        ↓
PostgreSQL 서비스 실행
        ↓
DB User 확인 / 생성
        ↓
Database 확인 / 생성
        ↓
schema.sql 적용
        ↓
grant.sql 적용
        ↓
선택적으로 seed.sql 적용
```

대상 환경:

* Ubuntu 24.04
* PostgreSQL 16
* Bash

---

## 2. 디렉토리 구조

```text
database/
├── setup_db.sh
├── reset_db.sh
├── schema.sql
├── grant.sql
├── seed.sql
├── .env
├── .env.example
└── README.md
```

| 파일 | 역할 |
| -------------- | --------------------------------- |
| `setup_db.sh`  | PostgreSQL 및 DB 초기 구축 |
| `reset_db.sh`  | 개발 DB 삭제 후 재구축 |
| `schema.sql`   | Table, Index, Trigger 등 Schema 정의 |
| `grant.sql`    | 애플리케이션 DB User 권한 설정 |
| `seed.sql`     | 개발 및 테스트용 초기 데이터 |
| `.env`         | 실제 DB 설정 |
| `.env.example` | 환경변수 예시 |

---

## 3. 환경변수 설정

`.env.example` 항목을 바탕으로 `.env` 파일을 생성한다.

```bash
cp .env.example .env
```

---

## 4. DB 구축

최초 실행 시 실행 권한을 부여한다.

```bash
chmod +x database/setup_db.sh
chmod +x database/reset_db.sh
```

기본 DB 구축:
```bash
./database/setup_db.sh
```

이 경우 다음 작업만 수행한다.

```text
PostgreSQL
→ DB User
→ Database
→ Schema
→ Grant
```

기존 PostgreSQL, User, Database, Table, Index 등이 존재하면 중복 생성하지 않는다.

`CREATE TABLE IF NOT EXISTS`는 기존 테이블의 컬럼을 변경하지 않으므로, 이전 버전 스키마에서 v6로 전환할 때는 마이그레이션이나 Database Reset이 필요하다.

---

## 5. Seed Data 포함 구축

개발 및 테스트 데이터를 함께 적용하려면:

```bash
./database/setup_db.sh --seed
```

실행 순서:

```text
PostgreSQL
→ DB User
→ Database
→ schema.sql
→ grant.sql
→ seed.sql
```

기본 `setup_db.sh` 실행에서는 seed 데이터를 적용하지 않는다.

---

## 6. Database Reset

개발 중 DB를 완전히 초기화하려면:

```bash
./database/reset_db.sh
```

`reset_db.sh`는 다음 작업을 수행한다.

```text
기존 DB 연결 종료
        ↓
Database 삭제
        ↓
setup_db.sh 실행
        ↓
Database 재생성
        ↓
Schema / Grant 적용
```

DB User는 삭제하지 않는다.

> Reset 실행 시 기존 Database의 모든 데이터가 삭제된다.

---

## 7. 설치 결과 확인

### DB User 확인

```bash
sudo -u postgres psql -c "\du"
```

### Database 확인

```bash
sudo -u postgres psql -c "\l"
```

### 애플리케이션 계정으로 접속

```bash
psql \
  -h localhost \
  -p 5432 \
  -U robot_app \
  -d robot_automation_db
```

Table 확인:

```sql
\dt
```

주요 Table 구조 확인:

```sql
\d installation
\d operation
\d robot
\d sensor
\d work_order
\d work_execution
\d operation_execution
\d log
\d sensor_data
```

종료:

```sql
\q
```

---

## 8. 재현성 검사

### 8.1 반복 실행 검사

다음 명령을 연속으로 실행한다.

```bash
./database/setup_db.sh
./database/setup_db.sh
```

두 번째 실행에서도 오류 없이 완료되어야 한다.

정상적인 경우 기존 객체는 다음과 같이 처리된다.

```text
PostgreSQL already installed.
Database user already exists.
Database already exists.
relation ... already exists, skipping
```

`ERROR` 없이 다음 메시지까지 출력되면 성공이다.

```text
=== PostgreSQL setup complete ===
```

---

### 8.2 Reset 재현 검사

```bash
./database/reset_db.sh
```

Reset 후 다음 항목을 확인한다.

```bash
sudo -u postgres psql -c "\l"
```

```bash
psql \
  -h localhost \
  -U robot_app \
  -d robot_automation_db \
  -c "\dt"
```

Database와 전체 Table이 다시 생성되어야 한다.

---

### 8.3 Seed 적용 검사

Database를 초기화한 뒤 Seed Data를 적용하려면:

```bash
./database/reset_db.sh
./database/setup_db.sh --seed
```

빈 Database에 바로 적용하려면:

```bash
./database/setup_db.sh --seed
```

실행 후 seed 데이터가 정상적으로 생성되었는지 확인한다.

예:

```sql
SELECT COUNT(*) FROM installation;
SELECT COUNT(*) FROM operation;
SELECT COUNT(*) FROM log;
SELECT COUNT(*) FROM sensor_data;
```

`seed.sql`은 고정 PK를 사용하므로 빈 Database에서 1회 적용한다. 다시 적용하려면 Database를 Reset하거나 기존 Seed Data를 먼저 정리해야 한다.

---

## 9. Schema 재실행 정책

`setup_db.sh` 반복 실행을 위해 `schema.sql`은 중복 실행 가능하도록 작성한다.

Table:

```sql
CREATE TABLE IF NOT EXISTS ...
```

Index:

```sql
CREATE INDEX IF NOT EXISTS ...
```

Trigger는 PostgreSQL에서 일반적인 `CREATE TRIGGER IF NOT EXISTS`를 지원하지 않으므로 다음 방식으로 관리한다.

```sql
DROP TRIGGER IF EXISTS trigger_name ON table_name;

CREATE TRIGGER trigger_name
...
```

이를 통해 동일한 v6 스키마에 `schema.sql`을 반복 적용해도 중복 객체로 인해 Setup이 실패하지 않도록 한다. 스키마 버전 간 변경은 자동으로 마이그레이션하지 않는다.

---

## 10. 현재 DB 배포 정책

현재 DB에는 다음 User가 존재한다.
```text
postgres
└── PostgreSQL 관리자

robot_app
└── Flask Backend용 DB User
```

Flask Backend에서는 `postgres` 계정을 사용하지 않고 `robot_app`으로 접속한다.

향후 Backend 연결 구조:

```text
Flask Backend
      ↓
SQLAlchemy
      ↓
robot_app
      ↓
PostgreSQL
```

DB 초기 구축 완료 후 다음 단계에서는 SQLAlchemy Model을 작성하여 기존 PostgreSQL Table과 Backend를 연동한다.
