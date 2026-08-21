# 로봇 작업 공정 관리 시스템 - DB 설계 명세 (v4)

> 기반 문서: DB 요구사항
> 설계일 : 2026-08-21
> 목적: Work Order → ROS2 작업 실행 → 결과/로그/센서 데이터까지 관리
> 구조: 16개 테이블, 4개 그룹 (A~D)

---

## 1. DB 설계 고려 항목
- 기준정보와 작업 실행 데이터를 분리한다.
- `Project → Site → Installation Target → Product → Recipe → Operation`으로 연결되는 구조
- `Product`는 설치되는 제품의 종류/모델(포스트, 거더, 판넬 등)을 의미한다.
- `Installation Target`은 특정 Site에서 실제 작업 대상이 되는 설비를 의미한다.
- `Component`는 작업에 사용되는 부품/자재를 의미한다.
- `Recipe`는 제품을 어떤 절차로 작업할지 정의한다.
- `Operation`은 Recipe를 구성하는 개별 작업 단계이며, 로봇 작업 파라미터(TCP, tool weigth, coordinate 등)는 `parameter` JSONB로 관리한다.
- `Work Order`는 `Installation Target`과 `Recipe`를 기준으로 생성한다.
- `work_order → installation_target → site → project` 경로로 조회한다.
- ROS2에서 실제 실행된 작업은 `Work Execution → Operation Execution`으로 기록한다.
- TCP, Position, Coordinate System, Fixture, Robot State Log 등은 확장 시 별도 테이블로 분리한다.

---

## 2. 전체 구조

### A. 생산/작업 기준정보

```
project
   └── site
         └── installation_target
                └── product
                       │
                       └── recipe
                              ├── operation
                              └── recipe_component
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
---

## 3. 테이블 목록

| # | 그룹 | 테이블 | 역할 |
|---|---|---|---|
| 1 | 기준정보 | project | 프로젝트 정보 |
| 2 | 기준정보 | site | 작업 현장 정보 |
| 3 | 기준정보 | installation_target | 실제 작업 대상 |
| 4 | 기준정보 | product | 설치 제품 Master |
| 5 | 기준정보 | recipe | 제품 작업 기준 |
| 6 | 기준정보 | operation | Recipe의 개별 작업 단계 |
| 7 | 기준정보 | component | 부품/자재 Master |
| 8 | 기준정보 | recipe_component | Recipe-Component 연결 |
| 9 | 로봇/센서 | robot | 작업 로봇 정보 |
| 10 | 로봇/센서 | sensor | 센서 Master |
| 11 | 작업 | work_order | 작업 지시 |
| 12 | 작업 | work_execution | Work Order 실제 실행 |
| 13 | 작업 | operation_execution | 개별 Operation 실행 |
| 14 | 로그 | work_event | 작업 이벤트 |
| 15 | 로그 | error_log | 작업 오류 |
| 16 | 측정 | force_torque_data | Force/Torque 측정 데이터 |

---

## 4. 기준정보

### 4.1 project

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `project_id` | BIGSERIAL PK | 프로젝트 ID |
| `code` | VARCHAR(50) UNIQUE | 프로젝트 코드 |
| `name` | VARCHAR(200) | 프로젝트명 |
| `description` | TEXT | 프로젝트 설명 |
| `status` | VARCHAR(30) | ACTIVE / INACTIVE |
| `created_at` | TIMESTAMP | 생성 시각 |
| `updated_at` | TIMESTAMP | 수정 시각 |

### 4.2 site

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

### 4.3 installation_target

특정 Site에서 실제 작업 대상이 되는 설비를 관리한다.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `installation_target_id` | BIGSERIAL PK | 작업 대상 ID |
| `site_id` | BIGINT FK → site | 작업 현장 |
| `product_id` | BIGINT FK → product | 대상 제품 |
| `target_code` | VARCHAR(50) UNIQUE | 작업 대상 코드 |
| `name` | VARCHAR(200) | 대상명 |
| `type` | VARCHAR(50) | 대상 유형 |
| `specification` | TEXT | 대상 사양 |
| `serial_number` | VARCHAR(100) | 대상 식별 번호 |
| `created_at` | TIMESTAMP | 생성 시각 |
| `updated_at` | TIMESTAMP | 수정 시각 |

### 4.4 product

설치되는 제품의 종류 또는 모델 정보를 관리한다.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `product_id` | BIGSERIAL PK | 제품 ID |
| `code` | VARCHAR(50) UNIQUE | 제품 코드 |
| `name` | VARCHAR(200) | 제품명 (포스트, 거더, 판넬 등) |
| `description` | TEXT | 제품 설명 |
| `category` | VARCHAR(100) | 제품 카테고리 |
| `specification` | JSONB | 제품 사양 |
| `created_at` | TIMESTAMP | 생성 시각 |
| `updated_at` | TIMESTAMP | 수정 시각 |

### 4.5 recipe

특정 Product를 작업하기 위한 기준 공정을 관리한다.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `recipe_id` | BIGSERIAL PK | Recipe ID |
| `product_id` | BIGINT FK → product | 대상 제품 |
| `code` | VARCHAR(50) | Recipe 코드 |
| `name` | VARCHAR(200) | Recipe명 |
| `description` | TEXT | 작업 기준 설명 |
| `is_active` | BOOLEAN | 활성 여부 |
| `created_by` | VARCHAR(100) | 생성자 |
| `created_at` | TIMESTAMP | 생성 시각 |
| `updated_at` | TIMESTAMP | 수정 시각 |

> `product_id + code` 조합은 UNIQUE 권장

### 4.6 operation

Recipe를 구성하는 개별 작업 단계를 관리한다.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `operation_id` | BIGSERIAL PK | Operation ID |
| `recipe_id` | BIGINT FK → recipe | 소속 Recipe |
| `code` | VARCHAR(50) | 작업 코드 |
| `name` | VARCHAR(200) | 작업명 |
| `sequence` | INT | 실행 순서 |
| `description` | TEXT | 작업 설명 |
| `is_required` | BOOLEAN | 필수 작업 여부 |
| `estimated_duration_sec` | INT | 예상 작업 시간 |
| `parameter` | JSONB | 로봇 작업 파라미터 |
| `created_at` | TIMESTAMP | 생성 시각 |
| `updated_at` | TIMESTAMP | 수정 시각 |

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

### 4.7 component

작업에 사용되는 부품 및 자재의 Master 정보를 관리한다.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `component_id` | BIGSERIAL PK | 부품 ID |
| `code` | VARCHAR(50) UNIQUE | 부품 코드 |
| `name` | VARCHAR(200) | 부품명 |
| `category` | VARCHAR(100) | 부품 카테고리 |
| `specification` | TEXT | 부품 사양 |
| `unit` | VARCHAR(30) | 단위 |
| `created_at` | TIMESTAMP | 생성 시각 |
| `updated_at` | TIMESTAMP | 수정 시각 |

### 4.8 recipe_component

Recipe에서 사용하는 Component와 수량을 관리한다.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `recipe_component_id` | BIGSERIAL PK | 연결 ID |
| `recipe_id` | BIGINT FK → recipe | Recipe |
| `component_id` | BIGINT FK → component | Component |
| `quantity` | INT | 필요 수량 |
| `remark` | TEXT | 비고 |
| `created_at` | TIMESTAMP | 생성 시각 |

> `recipe_id + component_id`는 UNIQUE 권장

---

## 5. 로봇/센서

### 5.1 robot

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

### 5.2 sensor

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

## 6. 작업

### 6.1 work_order

특정 Installation Target에 특정 Recipe를 적용하는 작업 지시이다.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `work_order_id` | BIGSERIAL PK | Work Order ID |
| `order_number` | VARCHAR(50) UNIQUE | 작업 지시 번호 |
| `title` | VARCHAR(300) | 작업 제목 |
| `installation_target_id` | BIGINT FK → installation_target | 작업 대상 |
| `recipe_id` | BIGINT FK → recipe | 적용 Recipe |
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

### 6.2 work_execution

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

### 6.3 operation_execution

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `operation_execution_id` | BIGSERIAL PK | Operation Execution ID |
| `work_execution_id` | BIGINT FK → work_execution | Work Execution |
| `operation_id` | BIGINT FK → operation | 기준 Operation |
| `sequence` | INT | 실제 실행 순서 |
| `status` | VARCHAR(30) | PENDING / RUNNING / SUCCESS / FAILED / SKIPPED |
| `start_time` | TIMESTAMP | 시작 시간 |
| `end_time` | TIMESTAMP | 종료 시간 |
| `result` | VARCHAR(30) | SUCCESS / FAIL |
| `error_message` | TEXT | 오류 메시지 |
| `retry_count` | INT | 재시도 횟수 |
| `created_at` | TIMESTAMP | 생성 시각 |

---

## 7. 로그 및 측정

### 7.1 work_event

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

### 7.2 error_log

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

### 7.3 force_torque_data

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

## 8. FK 관계 요약

```
project
  └── site.project_id
        └── installation_target.site_id
              │
              ├── installation_target.product_id ──▶ product
              │
              └── work_order.installation_target_id
                    │
                    └── work_order.recipe_id ──▶ recipe.product_id ──▶ product
                          │
                          ├── recipe → operation
                          │
                          └── recipe → recipe_component → component

work_order
  └── work_execution.work_order_id
        ├── work_execution.robot_id ──▶ robot
        └── operation_execution.work_execution_id
              ├── operation_execution.operation_id ──▶ operation
              ├── work_event.operation_execution_id
              ├── error_log.operation_execution_id
              │     └── error_log.robot_id ──▶ robot
              └── force_torque_data.operation_execution_id
                    └── force_torque_data.sensor_id ──▶ sensor
                          └── sensor.robot_id ──▶ robot
```

---

## 9. 데이터 흐름 예시

```
Project
└── 대륭포스트타워8차 태양광 설치 프로젝트
     │
     └── Site
          └── 대륭포스트타워8차 옥상
               │
               └── Installation Target
                    ├── Product: 포스트
                    │    └── Recipe: 포스트 설치
                    │         ├── Operation 1: 기초 고정
                    │         └── Operation 2: 포스트 삽입
                    │
                    ├── Product: 거더
                    │    └── Recipe: 거더 설치
                    │         ├── Operation 1: 거더 Pick
                    │         └── Operation 2: 거더 Place
                    │
                    └── Product: 판넬
                         └── Recipe: 판넬 설치
                              ├── Operation 1: 판넬 Pick
                              ├── Operation 2: 판넬 Place
                              └── Operation 3: 체결

실제 실행:
Work Order
└── WO-001 (설치 대상: 옥상 태양광 발전 설비 A, Recipe: 판넬 설치)
     └── Work Execution
          ├── Robot: ROBOT-01
          └── Operation Execution
               ├── 판넬 Pick → SUCCESS
               ├── 판넬 Place → SUCCESS
               └── 체결 → SUCCESS
```

Recipe Component:
```
판넬 설치
├── 태양광 패널 × 20
├── 브라켓 × 40
└── 볼트 × 160
```

---

## 10. 요구사항 매핑

| ID | 요구사항 | 테이블/컬럼 |
|---|---|---|
| DB-FR-01 | Work Order | `work_order` |
| DB-FR-02 | Project | `work_order → installation_target → site → project` |
| DB-FR-03 | Site | `work_order → installation_target → site` |
| DB-FR-04 | Installation Target | `work_order → installation_target` |
| DB-FR-05 | Priority | `work_order.priority` |
| DB-FR-06 | Work Order Status | `work_order.status` |
| DB-FR-07 | Recipe | `work_order.recipe_id` |
| DB-FR-08 | Product | `product` |
| DB-FR-09 | Recipe | `recipe` |
| DB-FR-10 | Operation | `operation` |
| DB-FR-11 | Operation Sequence | `operation.sequence` |
| DB-FR-12 | Operation Parameter | `operation.parameter` JSONB |
| DB-FR-13 | Assembly Dimension | `operation.parameter` JSONB |
| DB-FR-14 | Component | `component`, `recipe_component` |
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
| DB-FR-25 | Execution Result | `operation_execution.result` |
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
| DB-FR-37 | Recipe Version | `recipe.version` |
| DB-FR-38 | Operation 이력 | `operation_execution → work_execution → work_order` |
| DB-FR-39 | 결과/이벤트/오류 연결 | `operation_execution`, `work_event`, `error_log` |
| DB-FR-40 | 측정 데이터 연결 | `force_torque_data → operation_execution` |
| DB-FR-41 | 작업 이력 조회 | `work_order`, `work_execution`, `operation_execution` |

---

## 11. 확장 계획

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
