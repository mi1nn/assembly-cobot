# PostgreSQL 로컬 개발 DB 구축 가이드

## 1. 목적과 지원 범위

이 디렉토리는 로봇 자동화 공정 시스템에서 사용하는 PostgreSQL 데이터베이스의 구축, 초기화 및 재현 파일을 관리한다.

이 문서는 개인 로컬 개발 환경을 구성하거나 신규 팀원이 동일한 개발 DB를 재현하는 절차를 설명한다. 운영 DB 배포, 원격 DB 관리, 백업 및 복구는 현재 범위에 포함하지 않는다.

지원 환경:

- Ubuntu 24.04
- PostgreSQL 16
- Bash
- `sudo`와 `systemctl`을 사용할 수 있는 로컬 개발 환경

현재 스크립트는 로컬 PostgreSQL을 전제로 한다. Docker PostgreSQL, 원격 PostgreSQL, WSL 및 macOS에서는 동작을 보장하지 않는다. 특히 `reset_db.sh`는 로컬 PostgreSQL의 Database를 삭제하므로 개발 환경에서만 사용한다.

---

## 2. 스키마 구조 요약

현재 DB는 기준정보, 작업 실행, 로그 및 센서 데이터를 관리하는 9개 Table로 구성된다.

```text
installation
├── operation
└── work_order
    └── work_execution ─── robot
        ├── operation_execution ─── operation
        │   ├── log
        │   └── sensor_data ─── sensor
        └── log

robot
└── sensor
```

| 구분 | Table | 주요 내용 |
| --- | --- | --- |
| 설치 기준정보 | `installation` | 프로젝트, 현장, 설치 대상 정보 |
| 공정 기준정보 | `operation` | 설치 대상별 공정 순서, 파라미터, 작업 부품 |
| 장비 기준정보 | `robot` | 로봇 식별 정보, 모델, 상태 및 사양 |
| 센서 기준정보 | `sensor` | 로봇에 연결된 센서와 측정 한계 |
| 작업 지시 | `work_order` | 설치 대상에 대한 작업 지시, 일정, 우선순위 및 상태 |
| 작업 실행 | `work_execution` | 작업 지시를 특정 로봇이 수행한 실행 이력 |
| 공정 실행 | `operation_execution` | 작업 실행에 포함된 개별 공정의 상태와 재시도 이력 |
| 통합 로그 | `log` | 작업·공정·로봇의 이벤트, 오류 및 시스템 로그 |
| 센서 데이터 | `sensor_data` | 공정 실행 중 수집한 센서 측정 데이터 |

핵심 관계는 다음과 같다.

- 하나의 `installation`에는 여러 `operation`과 `work_order`가 속한다.
- 하나의 `work_order`는 여러 번 실행될 수 있으며 각 실행은 `work_execution`으로 기록한다.
- 하나의 `work_execution`은 공정별 `operation_execution`으로 세분화된다.
- `robot`에는 여러 `sensor`가 연결될 수 있다.
- 실행 중 발생한 이벤트와 오류는 `log`, 측정값은 `sensor_data`에 저장한다.

유연한 공정 설정과 측정값은 JSONB로 저장한다.

- `operation.parameter`: Tool, TCP, 속도, 힘, 좌표계 등 공정 실행 파라미터
- `operation.components`: 공정에 필요한 부품, 수량, Pick 및 조립 위치
- `log.detail`: 오류 원인, 해결 여부 등 로그별 상세 정보
- `sensor_data.data`: Force/Torque 등 센서 종류별 측정값

상세 컬럼, 제약조건, Index 및 Trigger 정의는 `schema.sql`을 기준으로 한다.

### 실행 상태

| 대상 | 허용 상태 |
| --- | --- |
| `installation` | `ACTIVE`, `INACTIVE`, `MAINTENANCE`, `ARCHIVED` |
| `robot` | `IDLE`, `RUNNING`, `ERROR`, `OFFLINE`, `MAINTENANCE` |
| `work_order` | `CREATED`, `READY`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED` |
| `work_execution` | `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED` |
| `operation_execution` | `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED` |

Backend는 강제 정지가 접수되면 Robot을 `ERROR`로 전환하고, Action Result에 따라 Work와 Operation Execution의 최종 상태를 확정한다. Robot 복구가 완료되면 `ERROR → IDLE`로 전환한다.

### 화면과 데이터 관계

| 화면 기능 | 주요 Table |
| --- | --- |
| Dashboard 성공률 | 종료 상태의 `work_execution` |
| Dashboard·Work Detail 진행률 | `work_order`, `operation_execution` |
| Robot 상태와 활성 실행 | `robot`, `work_execution` |
| History 실행 선택 | `work_execution`, `operation_execution` |
| 최근·실행별 로그 | `log` |
| 공정 센서 이력 API | `sensor_data`, `sensor`, `operation_execution` |

---

## 3. 디렉토리 구조

```text
web_app/
├── .env                   # 로컬 설정, Git에 커밋하지 않음
├── .env.example           # 환경변수 예시
└── database/
    ├── setup_db.sh        # PostgreSQL 및 DB 초기 구축
    ├── reset_db.sh        # 개발 DB 삭제 후 재구축
    ├── schema.sql         # Table, Index, Trigger 정의
    ├── grant.sql          # 애플리케이션 DB User 권한 설정
    ├── seed.sql           # 개발 및 테스트용 초기 데이터
    └── README.md
```

---

## 4. 사전 준비와 환경변수 설정

이 문서의 모든 명령은 저장소의 `web_app` 디렉토리에서 실행한다.

```bash
cd web_app
cp .env.example .env
```

생성한 `.env`에서 다음 값을 로컬 환경에 맞게 설정한다.

```dotenv
DB_HOST=localhost
DB_PORT=5432
DB_NAME=robot_automation_db
DB_USER=robot_app
DB_PASSWORD=change_me
```

주의사항:

- 현재 구축 및 Reset 스크립트는 `DB_HOST`가 로컬 호스트를 가리키는 환경을 전제로 한다.
- 스크립트는 `.env`를 Bash 설정 파일로 읽으므로 값에 공백이나 특수문자가 있다면 올바르게 따옴표로 감싼다.
- 실제 비밀번호가 들어 있는 `.env`는 공유하거나 Git에 커밋하지 않는다.
- Git에서 실행 권한이 유지되지 않은 경우에만 다음 명령을 실행한다.

```bash
chmod +x database/setup_db.sh database/reset_db.sh
```

---

## 5. DB 구축

Seed Data 없이 Schema만 구축한다.

```bash
./database/setup_db.sh
```

기존 PostgreSQL, User, Database, Table, Index 등이 존재하면 중복 생성을 건너뛴다. 완료되면 다음 메시지가 출력된다.

```text
=== PostgreSQL setup complete ===
```

`CREATE TABLE IF NOT EXISTS`는 기존 테이블의 컬럼을 변경하지 않는다. `schema.sql`이 변경된 경우 현재 개발 단계에서는 필요한 데이터를 백업한 뒤 Database를 Reset하여 다시 구축한다.

---

## 6. Seed Data 포함 구축

최초 개발 환경처럼 예제 데이터가 필요하면 다음 명령을 사용한다.

```bash
./database/setup_db.sh --seed
```

적용 순서는 `schema.sql` → `grant.sql` → `seed.sql`이다. 현재 Seed는 다음과 같은 Dashboard·History·센서 API 확인용 데이터를 제공한다.

- 활성 Installation 1건과 순서가 지정된 Operation 8건
- `IDLE` Robot과 Force/Torque Sensor 각 1건
- 완료된 Work Order와 Work Execution 각 1건
- 완료된 Operation Execution 8건
- 작업·공정 로그 6건
- Force/Torque 측정 Sample 5건

`seed.sql`은 고정 PK를 사용하는 개발 데이터이므로 빈 Database에 한 번만 적용한다. 이미 Seed가 적용된 DB에서 다시 실행하면 duplicate key 오류가 발생할 수 있다.

Seed 마지막에는 이후 Backend가 생성하는 Row의 PK 충돌을 방지하도록 9개 `BIGSERIAL` Sequence를 각 Table의 최대 ID로 보정한다.

---

## 7. 설치 결과 확인

### PostgreSQL 버전과 서비스

```bash
psql --version
systemctl status postgresql --no-pager
```

### DB User와 Database

```bash
sudo -u postgres psql -c "\du"
sudo -u postgres psql -c "\l"
```

### 애플리케이션 계정 접속

```bash
source .env
PGPASSWORD="$DB_PASSWORD" psql \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME"
```

접속 후 9개 Table을 확인한다.

```sql
\dt
\d installation
\d operation
\d robot
\d sensor
\d work_order
\d work_execution
\d operation_execution
\d log
\d sensor_data
\q
```

---

## 8. Database Reset

개발 DB의 모든 데이터를 삭제하고 Schema를 다시 구축한다.

```bash
./database/reset_db.sh
```

실행 전 Database 이름과 삭제 여부를 묻고, `y` 또는 `Y`를 입력한 경우에만 진행한다. DB User는 삭제하지 않는다.

> Reset하면 해당 Database의 모든 데이터가 삭제되며 자동 복구할 수 없다. 필요한 데이터는 먼저 별도로 백업한다.

> `reset_db.sh`는 `.env`의 `DB_HOST`와 `DB_PORT`를 사용해 삭제 대상을 선택하지 않고 로컬 PostgreSQL 관리자 계정으로 Database를 삭제한다. `DB_NAME`을 반드시 확인하고 로컬 개발 환경에서만 실행한다.

`reset_db.sh`는 Database를 삭제한 뒤 내부에서 `setup_db.sh`를 옵션 없이 실행하므로 Schema와 권한만 다시 적용한다. Seed Data까지 다시 적용하려면 다음 두 명령을 순서대로 실행한다. 두 번째 명령은 기존 Schema와 권한을 한 번 더 확인한 뒤 Seed를 적용한다.

```bash
./database/reset_db.sh
./database/setup_db.sh --seed
```

---

## 9. 재현성 확인

### 반복 실행

```bash
./database/setup_db.sh
./database/setup_db.sh
```

두 번째 실행도 `ERROR` 없이 완료되어야 한다. `relation ... already exists, skipping`은 기존 객체를 건너뛰었다는 PostgreSQL 안내다.

### Seed Data 확인

```bash
source .env
PGPASSWORD="$DB_PASSWORD" psql \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  -c "SELECT COUNT(*) FROM installation;" \
  -c "SELECT COUNT(*) FROM operation;" \
  -c "SELECT COUNT(*) FROM log;" \
  -c "SELECT COUNT(*) FROM sensor_data;"
```

예상 결과는 Installation 1건, Operation 8건, Log 6건, Sensor Data 5건이다.

실행 상태와 Sequence를 함께 확인한다.

```bash
source .env
PGPASSWORD="$DB_PASSWORD" psql \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  -c "SELECT status, COUNT(*) FROM work_execution GROUP BY status ORDER BY status;" \
  -c "SELECT status, COUNT(*) FROM operation_execution GROUP BY status ORDER BY status;" \
  -c "SELECT sequencename, last_value FROM pg_sequences WHERE schemaname = 'public' ORDER BY sequencename;"
```

고정 PK를 사용하는 각 Seed Table의 Sequence `last_value`는 해당 Table의 최대 ID 이상이어야 한다.

---

## 10. Schema 재실행 및 변경 정책

동일한 Schema의 반복 적용을 위해 Table과 Index는 `IF NOT EXISTS`를 사용한다. Trigger는 기존 Trigger를 삭제한 뒤 다시 생성한다.

이 방식은 같은 Schema를 반복 적용하기 위한 것이며 스키마 변경을 자동으로 마이그레이션하지 않는다. 현재 개발 단계에서 Schema가 변경되면 변경 내용을 팀에 공유하고, 필요한 데이터를 백업한 후 Reset한다. 운영 데이터가 생기기 전 별도의 migration 도구와 버전 정책을 마련해야 한다.

---

## 11. DB 계정 및 Backend 연결

`setup_db.sh`는 다음 역할로 DB 계정을 구성한다.

```text
postgres
└── PostgreSQL 로컬 관리자

robot_app 또는 DB_USER 값
└── Flask Backend용 DB User
```

연결 구조는 다음과 같다.

```text
Flask Backend
      ↓
SQLAlchemy
      ↓
DB_USER
      ↓
PostgreSQL
```

Flask Backend의 SQLAlchemy Model은 `app/models/`에 있으며 `.env`의 애플리케이션 계정으로 PostgreSQL에 연결한다. Backend에서는 관리자 계정인 `postgres`를 사용하지 않는다.

---

## 12. 문제 해결

### `.env file not found`

현재 위치가 `web_app`인지 확인하고 `.env.example`을 복사한다.

```bash
pwd
cp .env.example .env
```

### `psql: command not found`

`setup_db.sh`가 PostgreSQL 설치를 시도한다. 직접 설치하려면 다음 명령을 실행한 뒤 setup을 다시 수행한다.

```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib
```

### `Peer authentication failed` 또는 `password authentication failed`

`.env`의 접속 설정을 확인한다. 기존 DB User가 이미 존재하면 `setup_db.sh`는 해당 User의 비밀번호를 변경하지 않는다. 기존 User 설정을 확인하거나 개발용 User를 정리한 뒤 다시 구축한다.

### `relation ... already exists`

동일한 Schema를 다시 적용할 때 출력될 수 있다. 마지막에 `=== PostgreSQL setup complete ===`가 출력되고 `ERROR`가 없다면 정상이다.

### Seed 적용 중 duplicate key 오류

Seed가 이미 적용된 DB에는 `seed.sql`을 다시 적용하지 않는다. 필요한 데이터를 백업한 후 Reset하고 Seed를 적용한다.

```bash
./database/reset_db.sh
./database/setup_db.sh --seed
```

---

## 13. 데이터베이스 구축 체크리스트

- Ubuntu 24.04와 `sudo` 사용 가능 여부를 확인한다.
- `web_app`에서 `.env.example`을 `.env`로 복사하고 값을 설정한다.
- `./database/setup_db.sh --seed`를 실행한다.
- 애플리케이션 계정으로 접속하여 9개 Table을 확인한다.
- 주요 Table의 Seed row 수를 확인한다.
- Seed 적용 후 9개 Sequence가 최대 PK 이상으로 보정됐는지 확인한다.
- Flask Backend를 실행하여 DB 연결을 확인한다.
