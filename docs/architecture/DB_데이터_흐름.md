# DB 데이터 흐름 구조

> 발표용 자료. PostgreSQL 9개 테이블 각각에 대해
> **① 데이터가 어디서 들어오는가(유입 / INSERT·UPDATE)**,
> **② 어디서 그 테이블의 키(PK/인덱스)를 읽어 사용하는가(유출 / SELECT·JOIN)**
> 를 정리한다.
> 스키마 원본은 `web_app/database/schema.sql`, 모델은 `web_app/app/models/`,
> 접근 로직은 `web_app/app/services/`.

---

## 1. 한눈에 보기

### 1-1. 데이터 유입 경로는 3가지뿐

| # | 유입원 | 방식 | 대상 테이블 |
|---|---|---|---|
| **A** | 사람 · 초기 데이터 | `seed.sql` / Work Order 화면(`POST/PUT`) | `installation`, `operation`, `robot`, `sensor`, `work_order` |
| **B** | 로봇(ROS2) → Bridge → Backend 콜백 | `POST /api/v1/executions/action-feedback`·`action-result`, `POST /api/v1/logs` | `work_execution`, `operation_execution`, `robot`, `log` |
| **C** | Backend 내부 상태 전이 | 실행/정지/복구 라우트가 서비스 함수로 직접 `UPDATE` | `work_order`, `work_execution`, `operation_execution`, `robot`, `log` |

> `updated_at`은 **DB 트리거**(`trg_*_updated` → `update_timestamp()`)가 자동 갱신한다. 애플리케이션이 쓰지 않는다.
> `created_at` / `timestamp` / `start_time` 계열의 기본값은 `DEFAULT NOW()`.

### 1-2. 테이블 분류

```
[ 기준정보 · 거의 읽기 전용 ]          [ 실행 데이터 · 런타임에 계속 쓰임 ]

 installation ──1:N──┬── operation           work_execution ──1:N── operation_execution
                     └── work_order                  │                      │
                                                     │                      ├── log
 robot ──1:N── sensor                                │                      └── sensor_data
                                                     └── log
   ▲                                                 ▲
   │ status만 런타임에 UPDATE                          │ robot: 실행 중 status UPDATE
```

- **기준정보**(`installation`, `operation`, `robot`, `sensor`): 작업 전에 채워지고, 런타임에는 `robot.status`를 빼면 읽기만 한다.
- **실행 데이터**(`work_execution`, `operation_execution`, `log`, `sensor_data`): Work Order 1회 실행마다 새 행이 생기고 상태가 계속 바뀐다.
- `work_order`: 사람이 만들고(`CREATED`), 실행 라이프사이클에 따라 `status`가 `READY→RUNNING→COMPLETED/FAILED/CANCELLED`로 전이.

---

## 2. 전체 데이터 흐름도

```
                      ┌───────────────────────────── 사람(현장 관리자) ───────────────────────────────┐
                      │                                                                           │
   seed.sql ──▶ [installation][operation][robot][sensor]        Work Order 화면(추가/수정/READY)     │
      (초기 1회)         │  기준정보 조회                              │ POST/PUT /api/v1/work-orders  │
                        ▼                                         ▼                               │
                 ┌──────────────────────────── Flask Backend (web_app) ────────────────────────┐  │
                 │                                                                             │  │
   실행 요청 ────▶ │ execute_work_order()                                                        │  │
 POST .../execute│   read : work_order, robot, operation(installation_id, sequence 인덱스)       │  │
                 │   write: work_execution(INSERT), operation_execution(INSERT×N)              │  │
                 │   write: work_order.status=RUNNING, work_execution.status=RUNNING,          │  │
                 │          robot.status=RUNNING                                               │  │
                 │        │                                                                    │  │
                 │        ▼ build_work_command()  ← operation.parameter / operation.components │  │
                 └────────┼────────────────────────────────────────────────────────────────────┘  │
                          │ POST /jobs (HTTP)                                                     │
                          ▼                                                                       │
                 ┌──── ROS2 Bridge ────┐                                                          │
                 │ job_queue (Operation│  ── ExecuteOperation Goal ──▶ Controller ──▶ M0609 로봇   │
                 │  단위, 순서 보장)      │  ◀─ Feedback / Result / /system_event ──                 │
                 └──────────┬──────────┘                                                          │
                            │ 콜백 HTTP                                                            │
                            ▼                                                                     │
                 ┌──────────────────────────── Flask Backend ─────────────────────────────────┐   │
                 │ POST /executions/action-feedback → operation_execution.status=RUNNING      │   │
                 │                                    log(INSERT, EVENT)                      │   │
                 │ POST /executions/action-result   → operation_execution.status=COMPLETED    │   │
                 │       ├ 다음 PENDING 있음 → work_execution 유지(RUNNING)                      │   │
                 │       └ 없음 → work_order/work_execution.status=COMPLETED, robot.status=IDLE│   │
                 │                                    log(INSERT)                             │   │
                 │ POST /logs (from /system_event)  → log(INSERT, ROBOT/SYSTEM)               │   │
                 └──────────┬─────────────────────────────────────────────────────────────────┘   │
                            │ SELECT (인덱스 조회)                                                   │
                            ▼                                                                     │
             Dashboard / History / Robot / Log / Sensor 화면 ◀─────────────────────────────────────┘
```

---

## 3. 테이블별 유입 · 유출 상세

각 항목: **유입** = 이 테이블에 행을 쓰는 주체 / **유출** = 이 테이블의 PK·인덱스를 읽어 쓰는 곳.

### 3-1. `installation` — 설치 기준정보 (PK `installation_id`)

| 구분 | 내용 |
|---|---|
| **유입** | `seed.sql` (초기). 애플리케이션 코드에 INSERT/UPDATE 없음 → **읽기 전용** |
| **유출** | `work_order.installation_id` (FK, 인덱스 `idx_wo_installation`)<br>`operation.installation_id` (FK, 인덱스 `idx_operation_target_seq`)<br>`GET /api/v1/installations` → `get_active_installations()` (`status='ACTIVE'` 필터)<br>Work Order 생성/READY 검증 → `validate_ready_requirements()` (`status`, 하위 operation 존재 확인) |
| **인덱스** | `idx_installation_project_code(project_code)`, `UNIQUE(target_code)` |

### 3-2. `operation` — 공정 기준정보 (PK `operation_id`)

| 구분 | 내용 |
|---|---|
| **유입** | `seed.sql`. 애플리케이션 INSERT 없음 → **읽기 전용** (`parameter`, `components` JSONB 포함) |
| **유출** | `operation_execution.operation_id` (FK, 인덱스 `idx_oe_operation`)<br>`execute_work_order()` → `get_operations_for_installation(installation_id)` : `idx_operation_target_seq(installation_id, sequence)`로 **순서대로** 조회<br>`build_work_command()` : `operation.code / parameter / components`를 그대로 ROS2 Goal payload로 전달<br>`get_work_order_progress()` : `operation.code / name`을 현재 단계 표시에 사용 |
| **인덱스** | `idx_operation_target_seq(installation_id, sequence)`, `UNIQUE(installation_id, code)`, `UNIQUE(installation_id, sequence)` |
| **핵심** | 공정 파라미터(Tool/TCP/속도/힘/좌표계)와 부품·위치는 **여기서 나가서** ROS2 Controller가 소비한다. DB → 로봇 방향 데이터의 원천. |

### 3-3. `robot` — 장비 기준정보 (PK `robot_id`)

| 구분 | 내용 |
|---|---|
| **유입** | 행 생성: `seed.sql`<br>`status` UPDATE (런타임): `mark_work_execution_running`→`RUNNING` / `mark_execution_completed`→`IDLE` / `mark_execution_failed`·`mark_execution_force_stopped`·`mark_robot_stop_requested`→`ERROR` / `mark_robot_recovered`→`IDLE` |
| **유출** | `work_execution.robot_id` (FK, 인덱스 `idx_we_robot`)<br>`log.robot_id` (FK, 인덱스 `idx_log_robot`)<br>`sensor.robot_id` (FK, 인덱스 `idx_sensor_robot`)<br>`execute_work_order()` : 실행 전 `status='IDLE'` 확인<br>`GET /api/v1/robots` → `get_robots()`<br>Dashboard → `get_dashboard_data()` : 로봇별 `status` + 활성 실행 |
| **인덱스** | `UNIQUE(robot_code)` |
| **런타임 파라미터** | Controller launch 인자 `robot_id`(기본 1) = `robot.robot_id`. ROS2 콜백의 `robot_id`가 이 PK와 일치해야 함 |

### 3-4. `sensor` — 센서 기준정보 (PK `sensor_id`)

| 구분 | 내용 |
|---|---|
| **유입** | `seed.sql`. **모델 클래스 없음** (`SensorData.sensor_id` FK로만 참조). 애플리케이션 접근 없음 |
| **유출** | `sensor_data.sensor_id` (FK, 인덱스 `idx_sensor_data_sensor`)<br>`force_max_n` / `torque_max_nm` : 힘 임계값 상한 참조용(설계상) |
| **인덱스** | `idx_sensor_robot(robot_id)` |

### 3-5. `work_order` — 작업 지시 (PK `work_order_id`)

| 구분 | 내용 |
|---|---|
| **유입** | 생성: `POST /api/v1/work-orders` → `create_work_order()` (`status='CREATED'`)<br>수정: `PUT .../<id>` → `update_work_order()` (READY 전환 시 `validate_ready_requirements()` 통과 필요)<br>`status` UPDATE: `mark_work_execution_running`→`RUNNING`, `mark_execution_completed`→`COMPLETED`, `mark_execution_failed`→`FAILED`, `mark_execution_cancelled`·`mark_execution_force_stopped`→`CANCELLED` |
| **유출** | `work_execution.work_order_id` (FK, 인덱스 `idx_we_work_order`)<br>`GET /api/v1/work-orders` → `get_work_orders()` : `idx_wo_priority` / `idx_wo_status` 정렬·필터<br>`GET .../<id>/progress` → `get_work_order_progress()`<br>`execute_work_order()` / `stop_work_order()` : `status` 가드(READY / RUNNING) |
| **인덱스** | `UNIQUE(order_number)`, `idx_wo_installation`, `idx_wo_status`, `idx_wo_priority` |

### 3-6. `work_execution` — 작업 실행 이력 (PK `work_execution_id`)

| 구분 | 내용 |
|---|---|
| **유입** | INSERT: `execute_work_order()` → `create_execution_records_for_operations()` (`status='PENDING'`, `execution_number=EX-YYYYMMDD-xxxx`)<br>UPDATE: `mark_work_execution_running`(`RUNNING`+`start_time`), `mark_execution_completed/failed/cancelled/force_stopped`(종료 상태+`end_time`), `mark_work_submission_failed`(`FAILED`) |
| **유출** | `operation_execution.work_execution_id` (FK, 인덱스 `idx_oe_work_exec`)<br>`log.work_execution_id` (FK, 인덱스 `idx_log_work_exec`)<br>**ROS2 콜백의 매칭 키** : Bridge `_last_job["work_execution_id"]`, `action-feedback`/`action-result` 요청 본문의 `work_execution_id`<br>Dashboard 성공률 → `get_work_execution_summary()` : `idx_we_status`로 종료 상태 집계<br>History → `get_work_executions()`, Robot 활성 실행 → `get_active_execution_for_robot()` : `idx_we_robot` + `status IN (PENDING,RUNNING)` |
| **인덱스** | `UNIQUE(execution_number)`, `idx_we_work_order`, `idx_we_robot`, `idx_we_status` |

### 3-7. `operation_execution` — 공정 실행 (PK `operation_execution_id`)

| 구분 | 내용 |
|---|---|
| **유입** | INSERT: `create_execution_records_for_operations()` — operation 수만큼, `sequence` 부여, `status='PENDING'`<br>UPDATE: `mark_operation_running`(`RUNNING`+`start_time`, feedback 수신 시), `mark_operation_completed`(`COMPLETED`+`end_time`, result 성공 시), `mark_execution_*`(실패/취소 시 해당 + 잔여 PENDING 일괄 `CANCELLED`) |
| **유출** | `log.operation_execution_id` (FK, 인덱스 `idx_log_op_exec`)<br>`sensor_data.operation_execution_id` (FK, 인덱스 `idx_sensor_data_op_exec`)<br>**ROS2 콜백 매칭 키** : Goal의 `operation_execution_id`, feedback/result 본문<br>`get_next_pending_operation_execution()` : `idx_oe_work_exec` + `status='PENDING'` + `sequence ASC` → 다음 단계 판정<br>`get_operation_executions()` : 진행률 계산<br>Sensor 화면 : `operation_execution_id`로 `sensor_data` 조회 |
| **인덱스** | `idx_oe_work_exec(work_execution_id)`, `idx_oe_operation(operation_id)`, `idx_oe_status(status)` |

### 3-8. `log` (모델명 `SystemLog`, `__tablename__='log'`) — 통합 로그 (PK `log_id`)

| 구분 | 내용 |
|---|---|
| **유입** | 모두 `create_system_log()` 경유 INSERT. 호출 지점 2종:<br>① **ROS2 이벤트** : `/system_event` → Bridge `process_system_events()` → `POST /api/v1/logs` → `add_log()` (`log_type='ROBOT'` 또는 Bridge 자체 `'SYSTEM'`)<br>② **Backend 상태 전이** : `receive_action_feedback/result`, `execute/stop_work_order`, `recover_robot`, `robots.recover_robot` 가 직접 호출 (`log_type='EVENT'`/`'ERROR'`)<br>`detail`(JSONB)에 `operation_code / phase / status / error` 등 병합 |
| **유출** | `GET /api/v1/logs` → `list_logs()` → `get_system_logs()` : `work_execution_id` / `operation_execution_id` / `robot_id`로 선택 필터, `idx_log_timestamp`로 최신순 정렬<br>화면: 최근 로그, 실행별 로그, 로봇별 로그 |
| **인덱스** | `idx_log_work_exec`, `idx_log_op_exec`, `idx_log_robot`, `idx_log_type`, `idx_log_code`, `idx_log_timestamp` |
| **FK** | `work_execution_id`, `operation_execution_id`, `robot_id` 모두 **NULLABLE** — 실행과 무관한 시스템 로그 허용 |

### 3-9. `sensor_data` — 센서 측정 데이터 (PK `sensor_data_id`)

| 구분 | 내용 |
|---|---|
| **유입** | `seed.sql`만. **현재 애플리케이션에 INSERT 코드 없음** (`SensorData` 모델은 조회 전용). 로봇 F/T 측정값을 저장하는 콜백은 아직 미구현 |
| **유출** | `GET /api/v1/sensor-data?operation_execution_id=&data_type=` → `get_sensor_data_for_operation()` : `idx_sensor_data_op_exec` + `data_type` 필터, `timestamp` 최신 N개 후 오름차순 반환(그래프용) |
| **인덱스** | `idx_sensor_data_sensor`, `idx_sensor_data_op_exec`, `idx_sensor_data_type`, `idx_sensor_data_timestamp` |

---

## 4. 쓰기 경로 요약 — Work Order 1회 실행 동안 무슨 행이 생기나

| 시점 | 테이블 | 연산 |
|---|---|---|
| Work Order 생성 | `work_order` | INSERT (`CREATED`) |
| READY 전환 | `work_order` | UPDATE `status=READY` (검증: `installation`, `operation` 읽기) |
| **실행 시작** `POST .../execute` | `work_execution` | INSERT (`PENDING`) |
| | `operation_execution` | INSERT × (operation 수), `PENDING` |
| | `work_order` / `work_execution` / `robot` | UPDATE `RUNNING` |
| Operation 시작 (feedback RUNNING) | `operation_execution` | UPDATE `RUNNING` + `start_time` |
| | `log` | INSERT `EVENT / OPERATION_STARTED` |
| 로봇 이벤트 (`/system_event`) | `log` | INSERT `ROBOT` (단계별 다수) |
| Operation 완료 (result 성공) | `operation_execution` | UPDATE `COMPLETED` + `end_time` |
| | `log` | INSERT `EVENT / OPERATION_COMPLETED` |
| 다음 Operation 있음 | — | (`work_execution` 유지, Bridge 큐가 다음 Goal) |
| 마지막 Operation 완료 | `work_order` / `work_execution` | UPDATE `COMPLETED` + `end_time` |
| | `robot` | UPDATE `IDLE` |
| 실패 | `operation_execution` / `work_execution` / `work_order` | UPDATE `FAILED`, `robot` → `ERROR` |
| 강제 정지 `POST .../stop` | `robot` | UPDATE `ERROR` (`mark_robot_stop_requested`) + `log` INSERT `EVENT / WORK_STOP_REQUESTED` |
| 정지 후 result 취소 콜백 도착 | `operation_execution`(활성+잔여 PENDING) / `work_execution` / `work_order` | UPDATE `CANCELLED` (`mark_execution_cancelled`) |
| 로봇 복구 `POST /robots/<id>/recover` | `robot` | UPDATE `ERROR → IDLE`, `log` INSERT `ROBOT` |

> 트랜잭션: 실행 시작의 `work_execution` + `operation_execution×N`은 `flush()`로 PK 발급 후 **한 번에 `commit()`**. 실패 시 `rollback()`.

---

## 5. 읽기 경로 요약 — 화면이 어떤 인덱스로 조회하나

| 화면 / API | 주요 테이블 | 사용 인덱스 · 조건 |
|---|---|---|
| Work Order 목록 | `work_order` | `idx_wo_priority`, `idx_wo_status` (정렬 `priority ASC, created_at DESC`) |
| Work Order 상세 진행률 | `work_order`, `operation_execution`, `operation` | `idx_oe_work_exec`, `idx_operation_target_seq` |
| Dashboard 성공률 | `work_execution` | `idx_we_status` (종료 상태 `COUNT ... FILTER`) |
| Dashboard 로봇 카드 | `robot`, `work_execution` | `idx_we_robot` + `status IN (PENDING,RUNNING)` |
| History 실행 목록 | `work_execution` | `created_at DESC` (+ PK tie-break) |
| History 실행 상세 | `operation_execution` | `idx_oe_work_exec` + `sequence ASC` |
| 로그 조회 | `log` | `idx_log_timestamp` + (`idx_log_work_exec` / `idx_log_op_exec` / `idx_log_robot`) 선택 필터 |
| 센서 그래프 | `sensor_data` | `idx_sensor_data_op_exec` + `data_type` + `timestamp` |
| 설치 대상 선택 | `installation` | `status='ACTIVE'` |
| 다음 Operation 판정 (내부) | `operation_execution` | `idx_oe_work_exec` + `status='PENDING'` + `sequence ASC LIMIT 1` |

---

## 6. FK 의존 그래프 (키가 흐르는 방향)

```
installation_id ──┬─▶ operation.installation_id
                  └─▶ work_order.installation_id

work_order_id ────▶ work_execution.work_order_id
robot_id ─────────┬─▶ work_execution.robot_id
                  ├─▶ log.robot_id
                  └─▶ sensor.robot_id

work_execution_id ─┬─▶ operation_execution.work_execution_id
                   └─▶ log.work_execution_id

operation_id ──────▶ operation_execution.operation_id

operation_execution_id ─┬─▶ log.operation_execution_id
                        └─▶ sensor_data.operation_execution_id

sensor_id ─────────▶ sensor_data.sensor_id
```

- 화살표 오른쪽이 **왼쪽 테이블의 PK를 인덱스로 들고 조회**하는 자식.
- `operation_execution_id`가 가장 말단 조인 키 — 로그·센서 데이터가 전부 여기에 매달린다.

---

## 7. 발표 시 강조 포인트

1. **DB → 로봇 방향**의 유일한 데이터 원천은 `operation.parameter` / `operation.components` (JSONB). 이 값이 `build_work_command()`에서 ROS2 `ExecuteOperation` Goal로 그대로 실려 나간다.
2. **로봇 → DB 방향**은 전부 Bridge 콜백 3개(`action-feedback`, `action-result`, `logs`)로 좁혀진다. 로봇이 DB에 직접 쓰지 않는다(CLAUDE.md 원칙).
3. 실행 상태(`status`)는 4개 테이블(`work_order`, `work_execution`, `operation_execution`, `robot`)에 걸쳐 **동기적으로** 전이하며, 전이 함수는 `execution_service.py`의 `mark_*` 하나로 모여 있다.
4. `updated_at`은 DB 트리거가 담당 — 애플리케이션 코드에서 찾지 말 것.
5. **미구현 / 미사용**:
   - `sensor_data` / `sensor` 쓰기 경로 없음. F/T 실측값 적재 콜백이 추가되면 `operation_execution_id` + `sensor_id`를 키로 INSERT하는 경로가 생긴다.
   - `execution_service.py`의 `create_execution_records()`(단수), `mark_execution_submission_failed()`, `mark_execution_force_stopped()`는 정의만 되어 있고 라우트에서 호출되지 않는다(현재는 복수형 `create_execution_records_for_operations` + `mark_work_submission_failed` + `mark_execution_cancelled` 경로 사용).
