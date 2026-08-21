# 7. DB 요구사항

> 최초 작성: 2026-08-20
> 개정: 2026-08-21 (DB_specs.md v5 / DB_DDL.sql v5 설계 반영)
> 상위 문서: DB_specs.md, DB_DDL.sql

본 시스템은 작업 지시부터 로봇 작업 실행 및 결과 관리까지의 공정 데이터를 통합 관리하기 위한 데이터베이스를 구축한다.

데이터베이스는 다음 정보를 관리할 수 있어야 한다.

- 작업 지시(Work Order)
- Project / Site / Installation Target
- Operation 및 작업 순서
- 작업 Parameter 및 치수
- 구성 부품(Component) 및 수량, 자재 위치 정보
- Robot / Sensor 정보
- Tool / TCP / Fixture / Position / Coordinate System (작업 파라미터로 관리)
- 작업 실행 및 상태
- 작업 이벤트 및 오류
- Force/Torque 센서 데이터
- 작업 결과 및 이력

> **v5 개정 반영 사항**
> - **제외**: Product, Recipe, Recipe Component, Recipe Version → Installation Target / Operation 기반 구조로 대체
> - **변경**: Work Order는 Installation Target 기준 생성, Operation은 Installation Target 직속
> - **신규**: Component의 자재 현재 위치 / 조립 위치 관리 (DB-FR-42)
> - **위임**: Tool / TCP / Fixture / Position / Coordinate System / Robot State Log / Sensor Result는 `operation.parameter`(JSONB)로 관리하며, 확장 시 별도 테이블 분리

---

## 7.1 작업 지시 데이터

| ID | 데이터 | 요구사항 |
| --- | --- | --- |
| DB-FR-01 | Work Order | 시스템은 Work Order의 생성, 조회, 수정 및 상태 관리를 지원해야 한다. |
| DB-FR-02 | Project | Work Order와 Project 정보를 연결하여 관리할 수 있어야 한다. (`work_order → installation_target → site → project` 경로로 조회) |
| DB-FR-03 | Site | Work Order와 작업 현장(Site) 정보를 연결하여 관리할 수 있어야 한다. (상동 경로) |
| DB-FR-04 | Installation Target | Work Order의 설치 대상을 식별하고 관리할 수 있어야 한다. |
| DB-FR-05 | Priority | Work Order의 우선순위를 저장하고 관리할 수 있어야 한다. |
| DB-FR-06 | Work Order Status | 생성, 대기, 실행, 완료, 실패 등의 작업 상태를 관리할 수 있어야 한다. |
| DB-FR-07 | Installation Target 기준 Work Order | Work Order는 Installation Target을 기준으로 생성되고, 해당 설치 대상을 식별할 수 있어야 한다. *(구 Recipe 식별 요구사항 → 제외)* |

---

## 7.2 작업 기준 데이터

| ID | 데이터 | 요구사항 |
| --- | --- | --- |
| DB-FR-08 | Installation Target 사양 | 설치 대상 설비의 유형, 사양, 식별 번호 등 정보를 직접 관리할 수 있어야 한다. *(구 Product Master 요구사항 → 제외)* |
| DB-FR-09 | Operation 등록 | Installation Target별로 작업 단계 집합(Operation)을 등록하고 관리할 수 있어야 한다. *(구 Recipe 요구사항 → Operation으로 대체)* |
| DB-FR-10 | Operation | Installation Target을 구성하는 개별 작업 단계를 관리할 수 있어야 한다. |
| DB-FR-11 | Operation Sequence | Operation의 실행 순서를 관리할 수 있어야 한다. |
| DB-FR-12 | Operation Parameter | 각 Operation에 필요한 작업 조건 및 Parameter를 관리할 수 있어야 한다. |
| DB-FR-13 | Assembly Dimension | 기둥 높이, 설치 간격 등 조립에 필요한 치수를 관리할 수 있어야 한다. |
| DB-FR-14 | Component | Operation에 필요한 구성 부품과 수량을 관리할 수 있어야 한다. |
| DB-FR-42 | Component Position | 부품/자재의 현재 위치(픽업 좌표)와 조립 위치를 관리할 수 있어야 한다. *(v5 신규)* |

---

## 7.3 로봇 작업 데이터

| ID | 데이터 | 요구사항 |
| --- | --- | --- |
| DB-FR-15 | Robot | 작업에 사용되는 로봇 정보를 관리할 수 있어야 한다. |
| DB-FR-16 | Tool / Gripper | 작업에 사용되는 Tool 및 Gripper 정보를 관리할 수 있어야 한다. |
| DB-FR-17 | TCP | 작업에 사용되는 TCP 정보를 관리할 수 있어야 한다. |
| DB-FR-18 | Fixture | 작업 대상 및 부품의 고정 위치 정보를 관리할 수 있어야 한다. |
| DB-FR-19 | Position | Pick, Place, Insertion 등 작업에 필요한 위치 정보를 관리할 수 있어야 한다. |
| DB-FR-20 | Coordinate System | 작업에 사용되는 기준 좌표계 정보를 관리할 수 있어야 한다. |

> DB-FR-16 ~ DB-FR-20은 MVP에서 `operation.parameter`(JSONB)로 관리한다. 데이터 구조가 복잡해지거나 독립적인 CRUD가 필요해질 경우 별도 Master Table로 분리한다. (DB_specs.md 확장 계획 참조)

---

## 7.4 작업 실행 데이터

| ID | 데이터 | 요구사항 |
| --- | --- | --- |
| DB-FR-21 | Work Execution | Work Order의 실제 작업 실행 정보를 생성하고 관리할 수 있어야 한다. |
| DB-FR-22 | Operation Execution | 개별 Operation의 실행 이력을 관리할 수 있어야 한다. |
| DB-FR-23 | Execution Status | 작업 실행 상태를 관리할 수 있어야 한다. |
| DB-FR-24 | Execution Start/End Time | 작업 실행 시작 및 종료 시간을 기록할 수 있어야 한다. |
| DB-FR-25 | Execution Result | 개별 작업의 성공/실패 결과를 기록할 수 있어야 한다. |
| DB-FR-26 | Retry Count | 작업 재시도 횟수를 기록할 수 있어야 한다. |

---

## 7.5 작업 상태 및 이벤트 로그

| ID | 데이터 | 요구사항 |
| --- | --- | --- |
| DB-FR-27 | Work Event Log | 작업 과정에서 발생하는 주요 이벤트를 기록할 수 있어야 한다. |
| DB-FR-28 | Robot State Log | 작업 중 로봇의 주요 상태 변화를 기록할 수 있어야 한다. *(확장 시 robot_state_log 별도 테이블)* |
| DB-FR-29 | Error Log | 작업 중 발생한 오류와 오류 코드를 기록할 수 있어야 한다. |
| DB-FR-30 | Event Timestamp | 이벤트 및 오류 발생 시간을 기록할 수 있어야 한다. |
| DB-FR-31 | Error Code | 오류 유형을 식별할 수 있어야 한다. |

---

## 7.6 Force/Torque 센서 데이터

| ID | 데이터 | 요구사항 |
| --- | --- | --- |
| DB-FR-32 | Sensor | 사용 센서의 식별 정보를 관리할 수 있어야 한다. |
| DB-FR-33 | Force/Torque Data | 작업 중 측정된 힘/토크 데이터를 저장할 수 있어야 한다. |
| DB-FR-34 | Sensor Timestamp | 센서 데이터의 측정 시간을 기록할 수 있어야 한다. |
| DB-FR-35 | Execution Link | 센서 데이터를 해당 Operation Execution과 연결할 수 있어야 한다. |
| DB-FR-36 | Sensor Result | 측정 데이터에 대한 작업 결과 또는 판정 정보를 관리할 수 있어야 한다. *(확장 시 sensor_result 별도 테이블)* |

---

## 7.7 데이터 이력 및 추적성

| ID | 요구사항 |
| --- | --- |
| DB-FR-37 | 시스템은 Work Order에 적용된 작업 기준의 버전을 추적할 수 있어야 한다. *(구 Recipe Version → 확장 시 별도 관리)* |
| DB-FR-38 | 시스템은 각 Operation의 실행 이력을 Work Order와 연결하여 조회할 수 있어야 한다. |
| DB-FR-39 | 시스템은 작업 결과와 발생한 이벤트 및 오류를 해당 Execution과 연결할 수 있어야 한다. |
| DB-FR-40 | 시스템은 측정 결과 및 센서 데이터를 해당 작업 실행과 연결하여 조회할 수 있어야 한다. |
| DB-FR-41 | 시스템은 완료된 작업의 주요 이력을 조회할 수 있어야 한다. |

---

## 7.8 v5 개정 이력

| 구분 | 내용 | 관련 ID |
| --- | --- | --- |
| 제외 | Product Master (installation_target이 직접 작업 대상 정의) | DB-FR-08 |
| 제외 | Recipe / Recipe Component (operation, component로 대체) | DB-FR-07, DB-FR-09 |
| 변경 | Work Order 생성 기준: Recipe → Installation Target | DB-FR-07 |
| 변경 | Operation 소속: Recipe → Installation Target 직속 | DB-FR-09, DB-FR-10 |
| 변경 | Component 소속: Recipe 연결(recipe_component) → Operation 직속(FK) | DB-FR-14 |
| 신규 | Component 자재 현재 위치 / 조립 위치 관리 | DB-FR-42 |
| 위임 | Tool / TCP / Fixture / Position / Coordinate System → `operation.parameter` JSONB (확장 시 테이블 분리) | DB-FR-16~20 |
| 위임 | Robot State Log / Sensor Result → 확장 시 별도 테이블 | DB-FR-28, DB-FR-36 |
| 위임 | Recipe Version → 확장 시 별도 관리 | DB-FR-37 |
