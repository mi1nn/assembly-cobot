# Mock 데이터 구성 명세

> 참조: DB_specs.md (v5), DB_DDL.sql, Mock_data.sql
> 작성일: 2026-08-21
> 시나리오: 대륭 포스트타워 8차 옥상 태양광 발전 시설 A 설치 작업 1회 완료 (2026-08-21 09:00 ~ 11:35)

---

## 1. 데이터 개요

| # | 테이블 | 건수 | 내용 |
|---|---|---|---|
| 1 | project | 1 | 대륭 포스트타워 8차 태양광 발전 시설 도입 |
| 2 | site | 1 | 대륭 포스트타워 8차 옥상 |
| 3 | installation_target | 1 | 태양광 발전 시설 A |
| 4 | operation | 8 | postA~postF, frameA, solarpanelA |
| 5 | component | 18 | 포스트/프레임/패널 + 체결 부품 |
| 6 | robot | 1 | 조립 로봇 1호 (UR10e) |
| 7 | sensor | 1 | F/T 센서 (ATI AXIA80) |
| 8 | work_order | 1 | WO-20260821-001 (COMPLETED) |
| 9 | work_execution | 1 | EX-20260821-001 (COMPLETED) |
| 10 | operation_execution | 8 | Operation별 실행 이력 (전체 SUCCESS) |
| 11 | work_event | 5 | 시작/완료/경고 이벤트 |
| 12 | error_log | 1 | 체결 토크 경고 (해결 완료) |
| 13 | force_torque_data | 5 | 패널 체결 시 F/T 측정 샘플 |

---

## 2. 기준정보 (그룹 A)

### project

| 항목 | 값 |
|---|---|
| code | PRJ-DLPT8 |
| name | 대륭 포스트타워 8차 태양광 발전 시설 도입 |
| status | ACTIVE |

### site

| 항목 | 값 |
|---|---|
| name | 대륭 포스트타워 8차 옥상 |
| address | 서울특별시 중구 을지로 100 대륭포스트타워8차 |
| region | 서울 |
| 담당 | 김태양 / 010-1234-5678 |

### installation_target

| 항목 | 값 |
|---|---|
| target_code | IT-SOLAR-A |
| name | 태양광 발전 시설 A |
| type | 태양광 발전 설비 |
| specification | 옥상형 태양광 발전 시설 (포스트 6 + 프레임 1 + 패널 20) |

---

## 3. Operation 목록

installation_target = 태양광 발전 시설 A, 전체 sequence 1~8

| id | code | name | sequence | 예상 시간(sec) | tool | 비고 |
|---|---|---|---|---|---|---|
| 1 | postA | 포스트 A 설치 | 1 | 600 | gripper_post | 좌측 전단 포스트 |
| 2 | postB | 포스트 B 설치 | 2 | 600 | gripper_post | 중앙 전단 포스트 |
| 3 | postC | 포스트 C 설치 | 3 | 600 | gripper_post | 우측 전단 포스트 |
| 4 | postD | 포스트 D 설치 | 4 | 600 | gripper_post | 좌측 후단 포스트 |
| 5 | postE | 포스트 E 설치 | 5 | 600 | gripper_post | 중앙 후단 포스트 |
| 6 | postF | 포스트 F 설치 | 6 | 600 | gripper_post | 우측 후단 포스트 |
| 7 | frameA | 프레임 A 조립 | 7 | 900 | gripper_frame | 상부 프레임 결합 |
| 8 | solarpanelA | 태양광 패널 A 설치 | 8 | 1200 | suction_cup | 패널 20장 양중 및 체결 |

- `parameter` JSONB에는 tool / tcp / position / speed / force / fixture / coordinate_system 포함
- 포스트 좌표 배치(조립 위치 기준, 단위 mm): A(1000,1000) B(3000,1000) C(5000,1000) / D(1000,4000) E(3000,4000) F(5000,4000)

---

## 4. Component 목록

| id | 소속 Operation | code | name | quantity | 위치 정보 |
|---|---|---|---|---|---|
| 1 | postA | CMP-POST-A | 포스트 A | 1 | 있음 (보관→조립) |
| 2 | postA | CMP-BOLT-M16 | 앵커 볼트 M16 | 4 | 없음 (수동 체결) |
| 3 | postB | CMP-POST-B | 포스트 B | 1 | 있음 |
| 4 | postB | CMP-BOLT-M16 | 앵커 볼트 M16 | 4 | 없음 |
| 5 | postC | CMP-POST-C | 포스트 C | 1 | 있음 |
| 6 | postC | CMP-BOLT-M16 | 앵커 볼트 M16 | 4 | 없음 |
| 7 | postD | CMP-POST-D | 포스트 D | 1 | 있음 |
| 8 | postD | CMP-BOLT-M16 | 앵커 볼트 M16 | 4 | 없음 |
| 9 | postE | CMP-POST-E | 포스트 E | 1 | 있음 |
| 10 | postE | CMP-BOLT-M16 | 앵커 볼트 M16 | 4 | 없음 |
| 11 | postF | CMP-POST-F | 포스트 F | 1 | 있음 |
| 12 | postF | CMP-BOLT-M16 | 앵커 볼트 M16 | 4 | 없음 |
| 13 | frameA | CMP-FRAME-A | 프레임 A | 1 | 있음 |
| 14 | frameA | CMP-BRKT-L | 브라켓 L형 | 8 | 없음 |
| 15 | frameA | CMP-BOLT-M16 | 볼트 M16 | 32 | 없음 |
| 16 | solarpanelA | CMP-PANEL-450W | 태양광 패널 450W | 20 | 있음 (대표 좌표) |
| 17 | solarpanelA | CMP-BRKT-PV | 마운트 브라켓 | 40 | 없음 |
| 18 | solarpanelA | CMP-BOLT-M8 | 볼트 M8 | 160 | 없음 |

- `current_position` / `assembly_position` JSONB 구조: `{"x", "y", "z", "orientation": {"rx","ry","rz"}, "frame"}`
- 수량이 여러 개인 부품(panel 등)은 대표 좌표 1건만 저장
- 볼트/브라켓 등 소형 체결 부품은 위치 NULL (수동 체결 가정)

---

## 5. 로봇/센서 (그룹 B)

### robot

| 항목 | 값 |
|---|---|
| robot_code | RB-01 |
| name | 조립 로봇 1호 |
| 제조사/모델 | Universal Robots / UR10e |
| dofs / payload | 6 / 12.5kg |
| status | IDLE |

### sensor

| 항목 | 값 |
|---|---|
| sensor_code | SNS-FT-01 |
| type | FORCE_TORQUE |
| 제조사/모델 | ATI / AXIA80 |
| 최대 힘/토크 | 500N / 50Nm |
| 연결 로봇 | RB-01 |

---

## 6. 작업 실행 (그룹 C)

### work_order

| 항목 | 값 |
|---|---|
| order_number | WO-20260821-001 |
| title | 태양광 발전 시설 A 설치 작업 |
| priority / status | 1 / COMPLETED |
| 계획 기간 | 2026-08-19 ~ 2026-08-21 |

### work_execution

| 항목 | 값 |
|---|---|
| execution_number | EX-20260821-001 |
| robot | RB-01 |
| status | COMPLETED |
| 실행 시간 | 09:00:00 ~ 11:35:00 |
| result_summary | 8개 Operation 전체 성공 |

### operation_execution (8건, 전체 SUCCESS)

| id | operation | sequence | 시작 | 종료 |
|---|---|---|---|---|
| 1 | postA | 1 | 09:00 | 09:12 |
| 2 | postB | 2 | 09:13 | 09:25 |
| 3 | postC | 3 | 09:26 | 09:38 |
| 4 | postD | 4 | 09:39 | 09:51 |
| 5 | postE | 5 | 09:52 | 10:04 |
| 6 | postF | 6 | 10:05 | 10:17 |
| 7 | frameA | 7 | 10:18 | 10:36 |
| 8 | solarpanelA | 8 | 10:37 | 11:35 |

---

## 7. 로그/측정 (그룹 D)

### work_event (5건)

| id | event_type | severity | 시각 | 내용 |
|---|---|---|---|---|
| 1 | WORK_STARTED | INFO | 09:00 | 작업 실행 시작 |
| 2 | OPERATION_COMPLETED | INFO | 09:12 | postA 설치 완료 |
| 3 | OPERATION_COMPLETED | INFO | 10:36 | frameA 조립 완료 |
| 4 | TORQUE_WARNING | WARNING | 10:52 | 패널 체결 중 토크 상한 근접 |
| 5 | WORK_COMPLETED | INFO | 11:35 | 전체 작업 완료 |

### error_log (1건)

| 항목 | 값 |
|---|---|
| error_code / type | ERR-TORQUE-HIGH / TORQUE_LIMIT |
| 발생 Operation | solarpanelA (oe 8) |
| message | 패널 체결 중 토크 상한 근접 (측정 43.2Nm / 한계 45Nm) |
| severity | HIGH |
| 해결 | is_resolved TRUE, 10:55 김현장 처리 |

### force_torque_data (5건, oe 8 체결 구간 샘플)

| 시각 | fz (N) | magnitude_n | tz (Nm) | 비고 |
|---|---|---|---|---|
| 10:51:58 | 35.2 | 35.29 | 1.20 | 체결 시작 |
| 10:52:05 | 39.8 | 39.87 | 1.60 | 토크 상승 |
| 10:52:12 | 42.6 | 42.65 | 1.90 | 임계 접근 |
| 10:52:19 | 43.2 | 43.25 | 2.10 | 피크 (경고 발생) |
| 10:52:26 | 41.9 | 41.94 | 1.50 | 안정화 |

---

## 8. 실행 방법

```bash
# 컨테이너 실행 후 (Docker_PostgreSQL_Setup.md 참조)
docker cp ws_db/Mock_data.sql robot-postgres:/tmp/Mock_data.sql
docker exec -it robot-postgres psql -U postgres -d robot_workorder_db -f /tmp/Mock_data.sql
```

- 선행 조건: DB_DDL.sql 실행 완료 상태
- 재실행 시: Mock_data.sql 상단의 TRUNCATE 블록 주석 해제 후 실행
