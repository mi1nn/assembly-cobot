# 로봇 작업 공정 관리 시스템 - DB 설계 명세 (MVP)

> 기반 문서: DB 요구사항_봉승현.md
> 목적: Work Order → ROS2 작업 실행 → 결과/로그/센서 데이터까지 관리하기 위한 핵심 기능 위주로 구현한 DB 구조
> 기준: 요구사항을 충족하면서 구현 복잡도를 낮추는 것을 우선

---

## 1. 설계 원칙

- 기준정보와 작업 실행 데이터를 분리한다.
- `Project → Site → Installation Target → Product → Recipe → Operation`의 작업 기준 계층을 유지한다.
- `Product`는 설치되는 제품의 종류/모델을 의미한다.
- `Installation Target`은 특정 Site에서 실제 작업 대상이 되는 대상을 의미한다.
- `Component`는 작업에 사용되는 부품/자재를 의미한다.
- `Recipe`는 제품을 어떤 절차로 작업할지 정의한다.
- `Operation`은 Recipe를 구성하는 개별 작업 단계이다.
- Work Order는 `Installation Target`과 `Recipe`를 기준으로 생성한다.
- ROS2에서 실제 실행된 작업은 `Work Execution → Operation Execution`으로 기록한다.
- 소형 프로젝트 범위를 고려하여 TCP, Position, Coordinate System, Fixture, Sensor Master, Sensor Result 등은 별도 테이블로 분리하지 않는다.
- Operation의 로봇 작업 관련 세부값은 `operation.parameter` JSONB로 관리한다.

---

## 2. 전체 구조

```text
[PROJECT / SITE]

Project
   │
   └── Site
         │
         └── Installation Target
                │
                └── Product
                       │
                       └── Recipe
                              │
                              └── Operation


[RECIPE MATERIAL]

Recipe
   │
   └── Recipe Component
              │
              └── Component


[WORK]

Installation Target
        │
        └── Work Order
               │
               └── Work Execution
                      │
                      └── Operation Execution
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
           Event           Error       Force/Torque Data


[ROBOT]

Robot
   │
   └── Work Execution
```

---

## 3. 테이블 목록

| 그룹 | 테이블 | 역할 |
|---|---|---|
| 기준정보 | `project` | 프로젝트 정보 |
| 기준정보 | `site` | 작업 현장 정보 |
| 기준정보 | `installation_target` | 실제 작업 대상 |
| 기준정보 | `product` | 설치 제품 Master |
| 기준정보 | `recipe` | 제품 작업 기준 |
| 기준정보 | `operation` | Recipe의 개별 작업 단계 |
| 기준정보 | `component` | 부품/자재 Master |
| 기준정보 | `recipe_component` | Recipe와 Component의 연결 및 수량 |
| 로봇 | `robot` | 작업 로봇 정보 |
| 작업 | `work_order` | 작업 지시 |
| 작업 | `work_execution` | Work Order의 실제 실행 |
| 작업 | `operation_execution` | 개별 Operation 실행 |
| 로그 | `work_event` | 작업 이벤트 |
| 로그 | `error_log` | 작업 오류 |
| 측정 | `force_torque_data` | Force/Torque 측정 데이터 |

총 15개 테이블

---

## 4. 기준정보

### 4.1 project

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | BIGSERIAL PK | 프로젝트 ID |
| `code` | VARCHAR(50) UNIQUE | 프로젝트 코드 |
| `name` | VARCHAR(200) | 프로젝트명 |
| `description` | TEXT | 프로젝트 설명 |
| `status` | VARCHAR(30) | ACTIVE / INACTIVE |
| `created_at` | TIMESTAMP | 생성 시각 |
| `updated_at` | TIMESTAMP | 수정 시각 |

### 4.2 site

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | BIGSERIAL PK | 현장 ID |
| `project_id` | BIGINT FK → project | 소속 프로젝트 |
| `name` | VARCHAR(200) | 현장명 |
| `address` | VARCHAR(500) | 주소 |
| `region` | VARCHAR(100) | 지역 |
| `contact_person` | VARCHAR(100) | 담당자 |
| `contact_phone` | VARCHAR(30) | 연락처 |
| `created_at` | TIMESTAMP | 생성 시각 |
| `updated_at` | TIMESTAMP | 수정 시각 |

### 4.3 installation_target

특정 Site에서 실제 작업 대상이 되는 대상을 관리한다.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | BIGSERIAL PK | 작업 대상 ID |
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
| `id` | BIGSERIAL PK | 제품 ID |
| `code` | VARCHAR(50) UNIQUE | 제품 코드 |
| `name` | VARCHAR(200) | 제품명 |
| `description` | TEXT | 제품 설명 |
| `category` | VARCHAR(100) | 제품 카테고리 |
| `specification` | JSONB | 제품 사양 |
| `created_at` | TIMESTAMP | 생성 시각 |
| `updated_at` | TIMESTAMP | 수정 시각 |

### 4.5 recipe

특정 Product를 작업하기 위한 기준 공정을 관리한다.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | BIGSERIAL PK | Recipe ID |
| `product_id` | BIGINT FK → product | 대상 제품 |
| `code` | VARCHAR(50) | Recipe 코드 |
| `name` | VARCHAR(200) | Recipe명 |
| `version` | VARCHAR(20) | Recipe 버전 |
| `description` | TEXT | 작업 기준 설명 |
| `is_active` | BOOLEAN | 활성 여부 |
| `created_by` | VARCHAR(100) | 생성자 |
| `created_at` | TIMESTAMP | 생성 시각 |
| `updated_at` | TIMESTAMP | 수정 시각 |

`product_id + code + version` 조합은 UNIQUE로 관리하는 것을 권장한다.

### 4.6 operation

Recipe를 구성하는 개별 작업 단계를 관리한다.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | BIGSERIAL PK | Operation ID |
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

예:
```json
{
  "tool": "gripper_01",
  "position": "panel_pick",
  "speed": 100,
  "force": 30
}
```

### 4.7 component

작업에 사용되는 부품 및 자재의 Master 정보를 관리한다.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | BIGSERIAL PK | 부품 ID |
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
| `id` | BIGSERIAL PK | 연결 ID |
| `recipe_id` | BIGINT FK → recipe | Recipe |
| `component_id` | BIGINT FK → component | Component |
| `quantity` | INT | 필요 수량 |
| `remark` | TEXT | 비고 |
| `created_at` | TIMESTAMP | 생성 시각 |

`recipe_id + component_id`는 UNIQUE로 관리한다.

---

## 5. 로봇 기준정보

### 5.1 robot

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | BIGSERIAL PK | 로봇 ID |
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

---

## 6. 작업 지시 및 실행

### 6.1 work_order

특정 Installation Target에 특정 Recipe를 적용하는 작업 지시이다.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | BIGSERIAL PK | Work Order ID |
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
| `id` | BIGSERIAL PK | 실행 ID |
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
| `id` | BIGSERIAL PK | Operation Execution ID |
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
| `id` | BIGSERIAL PK | 이벤트 ID |
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
| `id` | BIGSERIAL PK | 오류 ID |
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
| `id` | BIGSERIAL PK | 측정 데이터 ID |
| `operation_execution_id` | BIGINT FK → operation_execution | 관련 Operation Execution |
| `sensor_name` | VARCHAR(100) | 센서 식별명 |
| `fx` | DECIMAL(12,6) | X축 힘 (N) |
| `fy` | DECIMAL(12,6) | Y축 힘 (N) |
| `fz` | DECIMAL(12,6) | Z축 힘 (N) |
| `tx` | DECIMAL(12,6) | X축 토크 (Nm) |
| `ty` | DECIMAL(12,6) | Y축 토크 (Nm) |
| `tz` | DECIMAL(12,6) | Z축 토크 (Nm) |
| `timestamp` | TIMESTAMP | 측정 시간 |
| `created_at` | TIMESTAMP | 저장 시간 |

---

## 8. 전체 FK 관계

```text
project
  │
  └── site
        │
        └── installation_target
              │
              └── product
                    │
                    └── recipe
                          │
                          ├── operation
                          │
                          └── recipe_component
                                │
                                └── component


installation_target
        │
        └── work_order
              │
              └── work_execution
                    │
                    ├── robot
                    │
                    └── operation_execution
                          │
                          ├── operation
                          ├── work_event
                          ├── error_log
                          └── force_torque_data
```

---

## 9. 데이터 흐름 예시

```text
Project
└── 대륭포스트타워8차 태양광 설치 프로젝트
     │
     └── Site
          └── 대륭포스트타워8차 옥상
               │
               └── Installation Target
                    └── 옥상 태양광 발전 설비 A
                         │
                         └── Product
                              └── 태양광 패널 A
                                   │
                                   └── Recipe
                                        └── 태양광 패널 A 설치 v1.0
                                             │
                                             ├── Operation 1: 거더 설치
                                             ├── Operation 2: 패널 Pick
                                             ├── Operation 3: 패널 Place
                                             └── Operation 4: 체결
```

Recipe Component:

```text
거더 × 4
태양광 패널 A × 20
브라켓 × 40
볼트 × 160
```

실제 실행:

```text
Work Order
└── WO-001
     │
     └── Work Execution
          ├── Robot: ROBOT-01
          │
          └── Operation Execution
               ├── 거더 설치 → SUCCESS
               ├── 패널 Pick → SUCCESS
               ├── 패널 Place → SUCCESS
               └── 체결 → SUCCESS
```

---

## 10. 요구사항 매핑

| 요구사항 | 테이블/컬럼 |
|---|---|
| DB-FR-01 Work Order | `work_order` |
| DB-FR-02 Project | `project` |
| DB-FR-03 Site | `site` |
| DB-FR-04 Installation Target | `installation_target` |
| DB-FR-05 Priority | `work_order.priority` |
| DB-FR-06 Work Order Status | `work_order.status` |
| DB-FR-07 Recipe | `work_order.recipe_id` |
| DB-FR-08 Product | `product` |
| DB-FR-09 Recipe | `recipe` |
| DB-FR-10 Operation | `operation` |
| DB-FR-11 Operation Sequence | `operation.sequence` |
| DB-FR-12 Operation Parameter | `operation.parameter` |
| DB-FR-13 Assembly Dimension | `operation.parameter` JSONB |
| DB-FR-14 Component | `component`, `recipe_component` |
| DB-FR-15 Robot | `robot` |
| DB-FR-16 Tool / Gripper | `operation.parameter` JSONB |
| DB-FR-17 TCP | `operation.parameter` JSONB |
| DB-FR-18 Fixture | `operation.parameter` JSONB |
| DB-FR-19 Position | `operation.parameter` JSONB |
| DB-FR-20 Coordinate System | `operation.parameter` JSONB |
| DB-FR-21 Work Execution | `work_execution` |
| DB-FR-22 Operation Execution | `operation_execution` |
| DB-FR-23 Execution Status | `work_execution.status`, `operation_execution.status` |
| DB-FR-24 Start/End Time | `work_execution`, `operation_execution` |
| DB-FR-25 Execution Result | `operation_execution.result` |
| DB-FR-26 Retry Count | `work_execution.retry_count`, `operation_execution.retry_count` |
| DB-FR-27 Work Event Log | `work_event` |
| DB-FR-28 Robot State Log | `work_event` 또는 필요 시 별도 확장 |
| DB-FR-29 Error Log | `error_log` |
| DB-FR-30 Event Timestamp | 각 로그의 `timestamp` |
| DB-FR-31 Error Code | `error_log.error_code` |
| DB-FR-32 Sensor | `force_torque_data.sensor_name` |
| DB-FR-33 Force/Torque Data | `force_torque_data` |
| DB-FR-34 Sensor Timestamp | `force_torque_data.timestamp` |
| DB-FR-35 Execution Link | `force_torque_data.operation_execution_id` |
| DB-FR-36 Sensor Result | 필요 시 `force_torque_data` 또는 별도 확장 |
| DB-FR-37 Recipe Version | `recipe.version` |
| DB-FR-38 Operation 이력 | `operation_execution → work_execution → work_order` |
| DB-FR-39 결과/이벤트/오류 연결 | `operation_execution`, `work_event`, `error_log` |
| DB-FR-40 측정 데이터 연결 | `force_torque_data → operation_execution` |
| DB-FR-41 작업 이력 조회 | `work_order`, `work_execution`, `operation_execution` |

---

## 11. 확장 계획

MVP 이후 실제 필요성이 확인되면 다음 테이블을 독립적으로 추가할 수 있다.

```text
tool
tcp
fixture
position
coordinate_system
sensor
sensor_result
robot_state_log
```

초기에는 `operation.parameter` JSONB로 관리하고, 데이터 구조가 복잡해지거나 독립적인 CRUD가 필요해질 경우 별도 Master Table로 분리한다.

---

## 12. 핵심 설계 요약

```text
Project
= 전체 프로젝트

Site
= 작업 장소

Installation Target
= 해당 장소의 실제 작업 대상

Product
= 설치 제품의 종류/모델

Component
= 작업에 사용하는 부품/자재

Recipe
= 제품을 작업하는 방법

Operation
= Recipe의 개별 작업

Work Order
= 실제 작업 지시

Work Execution
= 작업의 실제 실행

Operation Execution
= 개별 작업의 실제 실행

Event / Error / Force-Torque
= 실행 과정에서 발생한 관측 데이터
```

본 구조를 소형 프로젝트의 MVP 기준 DB 구조로 사용한다.
