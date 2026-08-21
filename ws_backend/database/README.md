# PostgreSQL Database Setup

## 1. 개요

본 디렉토리는 로봇 자동화 공정 시스템에서 사용하는 PostgreSQL 데이터베이스의 초기 구축 및 배포를 관리한다.

`setup_db.sh`를 통해 다음 작업을 자동으로 수행한다.

* PostgreSQL 설치 여부 확인
* PostgreSQL 서비스 실행
* 프로젝트용 DB 사용자 생성
* 프로젝트용 Database 생성
* `schema.sql` 적용
* 기존 사용자 및 Database 중복 생성 방지
* 기존 Table 중복 생성 방지

새로운 Ubuntu 환경에서도 동일한 데이터베이스 환경을 쉽게 재현한다.

---

## 2. 개발 환경

* OS: Ubuntu 24.04
* Database: PostgreSQL
* Shell: Bash
* Backend 연동 예정: Flask + SQLAlchemy

---

## 3. 디렉토리 구조

```text
database/
├── setup_db.sh
├── schema.sql
├── seed.sql
├── .env
├── .env.example
└── README.md
```

| 파일             | 설명                                      |
| -------------- | --------------------------------------- |
| `setup_db.sh`  | PostgreSQL 및 프로젝트 DB 초기 구축 스크립트         |
| `schema.sql`   | Table, Constraint, Index 등 DB Schema 정의 |
| `seed.sql`     | 개발 및 테스트용 초기 데이터                        |
| `.env`         | 실제 DB 접속 및 생성 설정                        |
| `.env.example` | 환경변수 작성 예시                              |
| `README.md`    | DB 구축 및 실행 방법                           |

> `.env`에는 비밀번호 등의 설정값이 포함되므로 Git에 포함하지 않는다.

---

## 4. 환경변수 설정

먼저 `.env.example`을 복사한다.

```bash
cp database/.env.example database/.env
```

`.env` 파일에 DB 정보를 설정한다.

```bash
DB_HOST=localhost
DB_PORT=5432

DB_NAME=robot_automation_db
DB_USER=robot_app
DB_PASSWORD=your_password
```

### 환경변수

| 변수 | 설명 |
| ------------- | ---------------- |
| `DB_HOST` | PostgreSQL 서버 주소 |
| `DB_PORT` | PostgreSQL 포트 |
| `DB_NAME` | 프로젝트 Database 이름 |
| `DB_USER` | 애플리케이션용 DB 사용자 |
| `DB_PASSWORD` | DB 사용자 비밀번호 |

---

## 5. 데이터베이스 구축

### 5.1 실행 권한 설정

최초 실행 시 `setup_db.sh`에 실행 권한을 부여한다.

```bash
chmod +x database/setup_db.sh
```

### 5.2 Setup 실행

프로젝트 루트에서 다음 명령을 실행한다.

```bash
./database/setup_db.sh
```

스크립트는 순서대로 다음 작업을 수행한다.

```text
PostgreSQL 설치 확인
        ↓
PostgreSQL 서비스 시작
        ↓
DB User 존재 여부 확인
        ↓
DB User 생성
        ↓
Database 존재 여부 확인
        ↓
Database 생성
        ↓
schema.sql 적용
```

PostgreSQL이 설치되지 않은 환경에서는 다음 패키지를 자동으로 설치한다.

```text
postgresql
postgresql-contrib
```

---

## 6. 중복 실행

`setup_db.sh`는 반복 실행을 고려하여 구성한다.

이미 PostgreSQL이 설치되어 있는 경우 재설치하지 않는다.
```text
PostgreSQL already installed.
```

DB 사용자가 이미 존재하면 다시 생성하지 않는다.
```text
Database user already exists.
```

Database가 이미 존재하면 다시 생성하지 않는다.
```text
Database already exists.
```

`schema.sql`의 Table은 다음 형태로 정의하여 기존 Table의 중복 생성을 방지한다.
```sql
CREATE TABLE IF NOT EXISTS project (
    ...
);
```

따라서 개발 중에도 다음 명령을 다시 실행할 수 있다.
```bash
./database/setup_db.sh
```

---

## 7. 설치 결과 확인

### 7.1 DB 사용자 확인

```bash
sudo -u postgres psql -c "\du"
```
사용자가 존재하는지 확인한다.

---

### 7.2 Database 확인

```bash
sudo -u postgres psql -c "\l"
```
다음 Database가 생성되었는지 확인한다.

Database Owner가 프로젝트용 DB User인지 함께 확인한다.

---

### 7.3 프로젝트 계정으로 접속

실제 Backend에서 사용할 사용자 계정으로 접속한다.
```bash
psql \
  -h localhost \
  -p 5432 \
  -U robot_app \
  -d robot_automation_db
```

비밀번호는 `.env`의 `DB_PASSWORD` 값을 사용한다.

---

### 7.4 Table 확인

PostgreSQL 접속 후 다음 명령을 실행한다.

```sql
\dt
```

생성된 Table 목록을 확인한다.

특정 Table의 Schema를 확인하려면:

```sql
\d work_order
```

또는:

```sql
\d operation
```

을 사용한다.

PostgreSQL 종료:

```sql
\q
```

---

## 8. Schema 관리

DB 구조는 `schema.sql`에서 관리한다.

예:

```sql
CREATE TABLE IF NOT EXISTS project (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL
);
```

---

## 9. 초기 테스트 데이터

개발 및 테스트용 데이터는 `seed.sql`에서 관리한다.

Schema와 테스트 데이터는 역할을 분리한다.
- schema.sql : DB 구조 정의
- seed.sql : 개발/테스트 데이터

초기 MVP에서는 `setup_db.sh`와 `schema.sql` 구축을 우선하며, 테스트 데이터 자동 입력은 필요 시 추가한다.

---

## 10. 오류 처리

`setup_db.sh`는 다음 옵션을 사용한다. 이를 통해 Shell 명령 실행 실패, 정의되지 않은 변수 사용 등의 오류 발생 시 스크립트를 중단한다.

```bash
set -euo pipefail
```

`schema.sql` 실행 과정에서 오류가 발생하면 이후 SQL을 계속 실행하지 않고 즉시 중단한다.
```bash
-v ON_ERROR_STOP=1
```

예:
```text
Table A 생성 성공
        ↓
Table B 생성 실패
        ↓
Setup 중단
```
이를 통해 일부 Table만 생성된 상태에서 Setup이 완료되는 것을 방지한다.

---

## 11. 재현성 확인

DB 구축 스크립트의 재현성은 다음 절차로 확인한다.

### 기존 테스트 DB 제거

```bash
sudo -u postgres dropdb --if-exists robot_automation_db
sudo -u postgres dropuser --if-exists robot_app
```

### Setup 재실행

```bash
./database/setup_db.sh
```

### 생성 확인

```bash
sudo -u postgres psql -c "\du"
sudo -u postgres psql -c "\l"
```

### Table 확인

```bash
psql -h localhost -U robot_app -d robot_automation_db
```

```sql
\dt
```

이후 아무것도 삭제하지 않고 다시 다음 명령을 실행한다.

```bash
./database/setup_db.sh
```

두 번째 실행에서도 오류 없이 완료되면 DB/User/Table 중복 생성 방지가 정상적으로 동작하는 것으로 판단한다.

---

## 12. Backend 연동

향후 Flask Backend에서는 프로젝트용 DB User를 사용하여 PostgreSQL에 접근한다.

통신 구조:

```text
Flask Backend
      │
      │ SQLAlchemy
      ▼
 PostgreSQL
```

접속 문자열은 다음 형태를 사용한다.

```text
postgresql://DB_USER:DB_PASSWORD@DB_HOST:DB_PORT/DB_NAME
```

예:

```text
postgresql://robot_app:password@localhost:5432/robot_automation_db
```

실제 접속 정보는 코드에 직접 작성하지 않고 `.env`를 통해 관리한다.

---

## 13. 현재 범위

현재 DB Setup 단계에서는 다음 항목까지만 자동화한다.

* [x] PostgreSQL 설치 확인
* [x] PostgreSQL 서비스 시작
* [x] DB User 생성
* [x] Database 생성
* [x] Schema 적용
* [x] 중복 실행 대응
* [x] SQL 오류 발생 시 Setup 중단
* [ ] Seed Data 자동 적용
* [ ] DB Reset Script
* [ ] SQLAlchemy Model 연동
* [ ] Alembic / Flask-Migrate 기반 Migration

Migration 및 Backend 연동은 Flask + SQLAlchemy 구현 단계에서 추가한다.
