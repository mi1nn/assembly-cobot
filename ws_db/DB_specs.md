# 로봇 작업 공정 관리 시스템 - DB 설계 명세 (v5)

> 기반 문서: DB 요구사항
> 설계일 : 2026-08-21
> 목적: Work Order → ROS2 작업 실행 → 결과/로그/센서 데이터까지 관리
> 구조: 13개 테이블, 4개 그룹 (A~D)

---

## 1. DB 설계 고려 항목

- 기준정보와 작업 실행 데이터를 분리한다.
- `Project → Site → Installation Target → Operation → Component` 구조이다.
- `Installation Target`은 특정 Site에서 실제 작업 대상이 되는 설비를 의미한다.
- `Operation`은 `Installation Target`을 구성하는 개별 작업 단계이다.
- `Component`는 `Operation`에 사용되는 부품/자재이며, `operation_id` FK로 소속되고 자재의 현재 위치와 조립 위치를 함께 관리한다.
- 로봇 작업 파라미터(TCP, tool weight, coordinate 등)는 `operation.parameter` JSONB로 관리한다.
- `Work Order`는 `Installation Target`을 기준으로 생성한다.
- `work_order → installation_target → site → project` 경로로 상위 정보를 조회한다.
- ROS2에서 실제 실행된 작업은 `Work Execution → Operation Execution`으로 기록한다.
- TCP, Position, Coordinate System, Fixture, Robot State Log 등은 확장 시 별도 테이블로 분리한다.

---

## 2. 전체 구조

### A. 생산/작업 기준정보

```
project
   └── site
         └── installation_target
                  └── operation
                        └── component
```

### B. 로봇/센서 기준정보

```
robot

sensor
```

### C. 작업

```
installation_target
        └── work_order
               └── work_execution
                      └── operation_execution
                      └── robot_id
```

### D. 로그/측정

```
operation_execution
        ├── work_event
        ├── error_log
        └── force_torque_data
                └── sensor_id
```

### 테이블 목록

| # | 그룹 | 테이블 | 역할 |
|---|---|---|---|
| 1 | A | project | 프로젝트 정보 |
| 2 | A | site | 작업 현장 정보 |
| 3 | A | installation_target | 실제 작업 대상 |
| 4 | A | operation | Installation Target의 개별 작업 단계 |
| 5 | A | component | Operation에 사용되는 부품/자재 |
| 6 | B | robot | 작업 로봇 정보 |
| 7 | B | sensor | 센서 정보 |
| 8 | C | work_order | 작업 지시 |
| 9 | C | work_execution | Work Order 실제 실행 |
| 10 | C | operation_execution | 개별 Operation 실행 |
| 11 | D | work_event | 작업 이벤트 |
| 12 | D | error_log | 작업 오류 |
| 13 | D | force_torque_data | Force/Torque 측정 데이터 |

---

## 3. 그룹 A. 생산/작업 기준정보

### 3.1 project

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `project_id` | BIGSERIAL PK | 프로젝트 ID |
| `code` | VARCHAR(50) UNIQUE | 프로젝트 코드 |
| `name` | VARCHAR(200) | 프로젝트명 |
| `description` | TEXT | 프로젝트 설명 |
| `status` | VARCHAR(30) | ACTIVE / INACTIVE |
| `created_at` | TIMESTAMP | 생성 시각 |
| `updated_at` | TIMESTAMP | 수정 시각 |

### 3.2 site

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `site_id` | BIGSERIAL PK | 현장 ID |
| `project_id` | BIGINT FK → project | 소속 프로젝트 |
| `name` | VARCHAR(200) | 현장명 |
| `address` | VARCHAR(500) | 주소 |
| `region` | VARCHAR(100) | 지역 |
| `contact_person` | VARCHAR(100) | 담당자 |
| `contact_phone` | VARCHAR(30) | 연락처 |
| `created_at` | TIMESTAMP | 생성 시각 |
| `updated_at` | TIMESTAMP | 수정 시각 |

### 3.3 installation_target

특정 Site에서 실제 작업 대상이 되는 설비를 관리한다.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `installation_target_id` | BIGSERIAL PK | 작업 대상 ID |
| `site_id` | BIGINT FK → site | 작업 현장 |
| `target_code` | VARCHAR(50) UNIQUE | 작업 대상 코드 |
| `name` | VARCHAR(200) | 대상명 |
| `type` | VARCHAR(50) | 대상 유형 |
| `specification` | TEXT | 대상 사양 |
| `serial_number` | VARCHAR(100) | 대상 식별 번호 |
| `created_at` | TIMESTAMP | 생성 시각 |
| `updated_at` | TIMESTAMP | 수정 시각 |

### 3.4 operation

Installation Target을 구성하는 개별 작업 단계를 관리한다.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `operation_id` | BIGSERIAL PK | Operation ID |
| `installation_target_id` | BIGINT FK → installation_target | 소속 작업 대상 |
| `code` | VARCHAR(50) | 작업 코드 |
| `name` | VARCHAR(200) | 작업명 |
| `sequence` | INT | 실행 순서 |
| `description` | TEXT | 작업 설명 |
| `is_required` | BOOLEAN | 필수 작업 여부 |
| `estimated_duration_sec` | INT | 예상 작업 시간 |
| `parameter` | JSONB | 로봇 작업 파라미터 |
| `created_at` | TIMESTAMP | 생성 시각 |
| `updated_at` | TIMESTAMP | 수정 시각 |

> `installation_target_id + code` 조합은 UNIQUE 권장

> parameter JSONB 예시:
> ```json
> {
>   "tool": "gripper_01",
>   "tcp": {"x": 0, "y": 0, "z": 150},
>   "position": "panel_pick",
>   "speed": 100,
>   "force": 30,
>   "fixture": "jig_01",
>   "coordinate_system": "BASE"
> }
> ```

### 3.5 component

Operation에 사용되는 부품 및 자재를 관리한다.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `component_id` | BIGSERIAL PK | 부품 ID |
| `operation_id` | BIGINT FK → operation | 소속 Operation |
| `code` | VARCHAR(50) | 부품 코드 |
| `name` | VARCHAR(200) | 부품명 |
| `category` | VARCHAR(100) | 부품 카테고리 |
| `specification` | TEXT | 부품 사양 |
| `quantity` | INT | 필요 수량 |
| `current_position` | JSONB | 자재의 현재 위치 (픽업 좌표) |
| `assembly_position` | JSONB | 조립시킬 목표 위치 |
| `created_at` | TIMESTAMP | 생성 시각 |
| `updated_at` | TIMESTAMP | 수정 시각 |

> `operation_id + code` 조합은 UNIQUE 권장

> current_position / assembly_position JSONB 예시:
> ```json
> {
>   "x": 1200.0, "y": 350.0, "z": 50.0,
>   "orientation": {"rx": 0.0, "ry": 0.0, "rz": 90.0},
>   "frame": "BASE"
> }
> ```

> 역할 구분: `component.current_position` / `assembly_position`은 자재 단위 Pick/Place 좌표를,
> `operation.parameter`는 로봇 작업 파라미터(TCP, tool, speed 등)를 관리한다.

---

## 4. 그룹 B. 로봇/센서 기준정보

### 4.1 robot

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `robot_id` | BIGSERIAL PK | 로봇 ID |
| `robot_code` | VARCHAR(50) UNIQUE | 로봇 코드 |
| `name` | VARCHAR(200) | 로봇명 |
| `manufacturer` | VARCHAR(100) | 제조사 |
| `model` | VARCHAR(100) | 모델명 |
| `serial_number` | VARCHAR(100) | 시리얼 번호 |
| `status` | VARCHAR(30) | IDLE / BUSY / OFFLINE / ERROR |
| `dofs` | INT | 자유도 |
| `payload_kg` | DECIMAL(8,2) | 페이로드 |
| `created_at` | TIMESTAMP | 생성 시각 |
| `updated_at` | TIMESTAMP | 수정 시각 |

### 4.2 sensor

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `sensor_id` | BIGSERIAL PK | 센서 ID |
| `robot_id` | BIGINT FK → robot | 연결 로봇 |
| `sensor_code` | VARCHAR(50) UNIQUE | 센서 코드 |
| `name` | VARCHAR(200) | 센서 명칭 |
| `type` | VARCHAR(50) | FORCE / TORQUE / FORCE_TORQUE |
| `manufacturer` | VARCHAR(100) | 제조사 |
| `model` | VARCHAR(100) | 모델명 |
| `serial_number` | VARCHAR(100) | 시리얼 번호 |
| `force_max_n` | DECIMAL(10,2) | 최대 측정 힘 (N) |
| `torque_max_nm` | DECIMAL(10,2) | 최대 측정 토크 (Nm) |
| `is_active` | BOOLEAN | 활성 여부 |
| `created_at` | TIMESTAMP | 생성 시각 |
| `updated_at` | TIMESTAMP | 수정 시각 |

---

## 5. 그룹 C. 작업

### 5.1 work_order

특정 Installation Target에 대한 작업 지시이다.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `work_order_id` | BIGSERIAL PK | Work Order ID |
| `order_number` | VARCHAR(50) UNIQUE | 작업 지시 번호 |
| `title` | VARCHAR(300) | 작업 제목 |
| `installation_target_id` | BIGINT FK → installation_target | 작업 대상 |
| `priority` | INT | 우선순위 |
| `status` | VARCHAR(30) | CREATED / WAITING / RUNNING / COMPLETED / FAILED |
| `planned_start_date` | TIMESTAMP | 계획 시작 |
| `planned_end_date` | TIMESTAMP | 계획 종료 |
| `remark` | TEXT | 비고 |
| `created_by` | VARCHAR(100) | 생성자 |
| `created_at` | TIMESTAMP | 생성 시각 |
| `updated_at` | TIMESTAMP | 수정 시각 |

> `project_id`, `site_id`는 Work Order에 직접 저장하지 않는다.
> `work_order → installation_target → site → project`를 통해 상위 정보를 조회한다.

### 5.2 work_execution

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `work_execution_id` | BIGSERIAL PK | 실행 ID |
| `work_order_id` | BIGINT FK → work_order | Work Order |
| `robot_id` | BIGINT FK → robot | 실행 로봇 |
| `execution_number` | VARCHAR(50) UNIQUE | 실행 번호 |
| `status` | VARCHAR(30) | PENDING / RUNNING / COMPLETED / FAILED / ABORTED |
| `start_time` | TIMESTAMP | 시작 시간 |
| `end_time` | TIMESTAMP | 종료 시간 |
| `retry_count` | INT | 재시도 횟수 |
| `result_summary` | TEXT | 실행 결과 |
| `remark` | TEXT | 비고 |
| `created_at` | TIMESTAMP | 생성 시각 |
| `updated_at` | TIMESTAMP | 수정 시각 |

### 5.3 operation_execution

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `operation_execution_id` | BIGSERIAL PK | Operation Execution ID |
| `work_execution_id` | BIGINT FK → work_execution | Work Execution |
| `operation_id` | BIGINT FK → operation | 기준 Operation |
| `sequence` | INT | 실제 실행 순서 |
| `status` | VARCHAR(30) | PENDING / RUNNING / SUCCESS / FAILED / SKIPPED |
| `start_time` | TIMESTAMP | 시작 시간 |
| `end_time` | TIMESTAMP | 종료 시간 |
| `error_message` | TEXT | 오류 메시지 |
| `retry_count` | INT | 재시도 횟수 |
| `created_at` | TIMESTAMP | 생성 시각 |

---

## 6. 그룹 D. 로그 및 측정

### 6.1 work_event

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `work_event_id` | BIGSERIAL PK | 이벤트 ID |
| `work_execution_id` | BIGINT FK → work_execution | Work Execution |
| `operation_execution_id` | BIGINT FK → operation_execution | 관련 Operation |
| `event_type` | VARCHAR(50) | 이벤트 유형 |
| `event_message` | TEXT | 이벤트 내용 |
| `severity` | VARCHAR(20) | INFO / WARNING / ERROR / CRITICAL |
| `timestamp` | TIMESTAMP | 발생 시간 |
| `created_at` | TIMESTAMP | 생성 시각 |

### 6.2 error_log

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `error_log_id` | BIGSERIAL PK | 오류 ID |
| `work_execution_id` | BIGINT FK → work_execution | Work Execution |
| `operation_execution_id` | BIGINT FK → operation_execution | 관련 Operation |
| `robot_id` | BIGINT FK → robot | 관련 로봇 |
| `error_code` | VARCHAR(50) | 오류 코드 |
| `error_type` | VARCHAR(50) | 오류 유형 |
| `error_message` | TEXT | 오류 내용 |
| `severity` | VARCHAR(20) | LOW / MEDIUM / HIGH / CRITICAL |
| `is_resolved` | BOOLEAN | 해결 여부 |
| `resolved_at` | TIMESTAMP | 해결 시간 |
| `resolved_by` | VARCHAR(100) | 해결자 |
| `timestamp` | TIMESTAMP | 발생 시간 |
| `created_at` | TIMESTAMP | 생성 시각 |

### 6.3 force_torque_data

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `force_torque_data_id` | BIGSERIAL PK | 측정 데이터 ID |
| `sensor_id` | BIGINT FK → sensor | 센서 |
| `operation_execution_id` | BIGINT FK → operation_execution | 관련 Operation Execution |
| `fx` | DECIMAL(12,6) | X축 힘 (N) |
| `fy` | DECIMAL(12,6) | Y축 힘 (N) |
| `fz` | DECIMAL(12,6) | Z축 힘 (N) |
| `tx` | DECIMAL(12,6) | X축 토크 (Nm) |
| `ty` | DECIMAL(12,6) | Y축 토크 (Nm) |
| `tz` | DECIMAL(12,6) | Z축 토크 (Nm) |
| `magnitude_n` | DECIMAL(12,6) | 힘 크기 (N) |
| `magnitude_nm` | DECIMAL(12,6) | 토크 크기 (Nm) |
| `timestamp` | TIMESTAMP | 측정 시간 |
| `created_at` | TIMESTAMP | 저장 시간 |

---

## 7. 데이터 흐름 예시

```
Project
└── 대륭포스트타워8차 태양광 설치 프로젝트
     │
     └── Site
          └── 대륭포스트타워8차 옥상
               │
               └── Installation Target
                    └── 옥상 태양광 발전 설비 A
                         ├── Operation 1: 판넬 Pick
                         │    └── Component: 태양광 패널 × 20
                         ├── Operation 2: 판넬 Place
                         └── Operation 3: 체결
                              ├── Component: 브라켓 × 40
                              └── Component: 볼트 × 160

실제 실행:
Work Order
└── WO-001 (설치 대상: 옥상 태양광 발전 설비 A)
     └── Work Execution
          ├── Robot: ROBOT-01
          └── Operation Execution
               ├── 판넬 Pick → SUCCESS
               ├── 판넬 Place → SUCCESS
               └── 체결 → SUCCESS
```

---

## 8. 요구사항 매핑

| ID | 요구사항 | 테이블/컬럼 |
|---|---|---|
| DB-FR-01 | Work Order | `work_order` |
| DB-FR-02 | Project | `work_order → installation_target → site → project` |
| DB-FR-03 | Site | `work_order → installation_target → site` |
| DB-FR-04 | Installation Target | `work_order → installation_target` |
| DB-FR-05 | Priority | `work_order.priority` |
| DB-FR-06 | Work Order Status | `work_order.status` |
| DB-FR-07 | Installation Target 기준 Work Order | `work_order.installation_target_id` |
| DB-FR-08 | Installation Target 사양 | `installation_target` |
| DB-FR-09 | Operation 등록 | `operation` |
| DB-FR-10 | Operation | `operation` |
| DB-FR-11 | Operation Sequence | `operation.sequence` |
| DB-FR-12 | Operation Parameter | `operation.parameter` JSONB |
| DB-FR-13 | Assembly Dimension | `operation.parameter` JSONB |
| DB-FR-14 | Component | `component` |
| DB-FR-15 | Robot | `robot` |
| DB-FR-16 | Tool / Gripper | `operation.parameter` JSONB |
| DB-FR-17 | TCP | `operation.parameter` JSONB |
| DB-FR-18 | Fixture | `operation.parameter` JSONB |
| DB-FR-19 | Position | `operation.parameter` JSONB |
| DB-FR-20 | Coordinate System | `operation.parameter` JSONB |
| DB-FR-21 | Work Execution | `work_execution` |
| DB-FR-22 | Operation Execution | `operation_execution` |
| DB-FR-23 | Execution Status | `work_execution.status`, `operation_execution.status` |
| DB-FR-24 | Start/End Time | `work_execution`, `operation_execution` |
| DB-FR-25 | Execution Result | `operation_execution.status` |
| DB-FR-26 | Retry Count | `work_execution.retry_count`, `operation_execution.retry_count` |
| DB-FR-27 | Work Event Log | `work_event` |
| DB-FR-28 | Robot State Log | 확장 시 별도 테이블 추가 |
| DB-FR-29 | Error Log | `error_log` |
| DB-FR-30 | Event Timestamp | 각 로그의 `timestamp` |
| DB-FR-31 | Error Code | `error_log.error_code` |
| DB-FR-32 | Sensor | `sensor` |
| DB-FR-33 | Force/Torque Data | `force_torque_data` |
| DB-FR-34 | Sensor Timestamp | `force_torque_data.timestamp` |
| DB-FR-35 | Execution Link | `force_torque_data.operation_execution_id` |
| DB-FR-36 | Sensor Result | 확장 시 별도 테이블 추가 |
| DB-FR-37 | Recipe Version | 확장 시 별도 관리 |
| DB-FR-38 | Operation 이력 | `operation_execution → work_execution → work_order` |
| DB-FR-39 | 결과/이벤트/오류 연결 | `operation_execution`, `work_event`, `error_log` |
| DB-FR-40 | 측정 데이터 연결 | `force_torque_data → operation_execution` |
| DB-FR-41 | 작업 이력 조회 | `work_order`, `work_execution`, `operation_execution` |
| DB-FR-42 | Component Position | `component.current_position`, `component.assembly_position` |

---

## 9. 확장 계획

MVP 이후 실제 필요성이 확인되면 다음 테이블을 독립적으로 추가한다.

```
tool (robot_id FK)
tcp (tool_id FK)
fixture (robot_id FK)
position (robot_id FK, coordinate_system_id FK)
coordinate_system
robot_state_log (robot_id FK, work_execution_id FK)
sensor_result (sensor_id FK, operation_execution_id FK)
```

초기에는 `operation.parameter` JSONB로 관리하고, 데이터 구조가 복잡해지거나 독립적인 CRUD가 필요해질 경우 별도 Master Table로 분리한다.
