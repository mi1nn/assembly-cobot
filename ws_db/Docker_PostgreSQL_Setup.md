# Docker PostgreSQL 설정 및 DB 구축 가이드

> 프로젝트: 로봇 작업 공정 관리 시스템
> 작성일: 2026-08-20
> 참조: DB_DDL.sql, DB_스펙.md

---

## 1. 사전 준비

### Docker 설치 확인

```bash
docker --version
docker compose version
```

### 프로젝트 파일 구조

```
DB_DDL.sql          # DDL 스크립트
DB_스펙.md          # 테이블 명세
docker-compose.yml  # Docker Compose 설정 (선택)
```

---

## 2. PostgreSQL 컨테이너 실행

### 2.1 docker run 명령어

```bash
docker run -d \
  --name robot-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres123 \
  -e POSTGRES_DB=robot_workorder_db \
  -p 5432:5432 \
  -v robot_pgdata:/var/lib/postgresql/data \
  postgres:15
```

| 옵션 | 설명 |
|---|---|
| `-d` | 백그라운드 실행 |
| `--name` | 컨테이너 이름 |
| `-e` | 환경변수 (사용자/비밀번호/DB명) |
| `-p 5432:5432` | 포트 바인딩 (호스트:컨테이너) |
| `-v` | 데이터 볼륨 영구 저장 |
| `postgres:15` | 이미지 버전 |

### 2.2 docker-compose.yml 사용

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:15
    container_name: robot-postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres123
      POSTGRES_DB: robot_workorder_db
    ports:
      - "5432:5432"
    volumes:
      - robot_pgdata:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  robot_pgdata:
```

실행:

```bash
docker compose up -d
```

---

## 3. DDL 스크립트 실행

### 3.1 파일 복사 후 실행

```bash
# 호스트에서 컨테이너로 파일 복사
docker cp /home/shbong/Downloads/DB_DDL.sql robot-postgres:/tmp/DB_DDL.sql

# psql로 DDL 실행
docker exec -it robot-postgres psql -U postgres -d robot_workorder_db -f /tmp/DB_DDL.sql
```

### 3.2 stdin으로 직접 전달

```bash
cat /home/shbong/Downloads/DB_DDL.sql | \
  docker exec -i robot-postgres psql -U postgres -d robot_workorder_db
```

### 3.3 psql 세션 진입 후 실행

```bash
# 컨테이너 접속
docker exec -it robot-postgres psql -U postgres -d robot_workorder_db

# psql 내에서 실행
\i /tmp/DB_DDL.sql
```

### 3.4 psql 별도 컨테이너 사용

이미 PostgreSQL 서버가 실행 중이라면 psql 클라이언트만 사용:

```bash
docker run -it --rm \
  --network host \
  postgres:15 psql -h localhost -U postgres -d robot_workorder_db
```

---

## 4. 연결 정보

| 항목 | 값 |
|---|---|
| 호스트 | localhost |
| 포트 | 5432 |
| 사용자 | postgres |
| 비밀번호 | postgres123 |
| DB명 | robot_workorder_db |

---

## 5. 접속 확인

### 5.1 psql 접속 테스트

```bash
docker exec -it robot-postgres psql -U postgres -d robot_workorder_db
```

```sql
-- 버전 확인
SELECT version();

-- 테이블 목록 확인 (23개 예상)
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```

### 5.2 테이블별 레코드 수 확인

```sql
SELECT
  relname AS table_name,
  n_live_tup AS row_count
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC;
```

---

## 6. 외부 GUI 도구 연결

DBeaver, pgAdmin 등에서 연결:

| 항목 | 값 |
|---|---|
| 호스트 | localhost (또는 127.0.0.1) |
| 포트 | 5432 |
| 데이터베이스 | robot_workorder_db |
| 사용자 | postgres |
| 비밀번호 | postgres123 |

---

## 7. 실행 취소 (테이블 삭제)

```sql
DROP TABLE IF EXISTS
  force_torque_data, sensor,
  error_log, robot_state_log, work_event_log,
  operation_execution, work_execution,
  work_order, position, fixture, tcp, tool,
  coordinate_system, robot,
  component, assembly_dimension, operation_parameter, operation,
  recipe, product, installation_target, site, project
CASCADE;

DROP FUNCTION IF EXISTS update_timestamp();
```

---

## 8. 컨테이너 관리 명령어

```bash
# 컨테이너 상태 확인
docker ps

# 컨테이너 시작
docker start robot-postgres

# 컨테이너 중지
docker stop robot-postgres

# 컨테이너 삭제
docker rm -f robot-postgres

# 로그 확인
docker logs robot-postgres

# 볼륨 삭제 (데이터 유의)
docker volume rm robot_pgdata
```

---

## 9. 트러블슈팅

| 문제 | 해결 |
|---|---|
| `port already in use` | `docker ps`로 기존 컨테이너 확인 후 중지, 또는 포트 변경 `-p 5433:5432` |
| `password authentication failed` | `POSTGRES_PASSWORD` 환경변수 일치 확인 |
| `database "robot_workorder_db" does not exist` | `docker run` 시 `POSTGRES_DB` 옵션 확인 |
| `permission denied` | 컨테이너 실행 사용자 확인: `whoami` |
