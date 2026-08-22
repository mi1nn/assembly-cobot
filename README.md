# assembly-cobot

> 두산로보틱스 M0609 협동로봇으로 지상형 태양광 패널 구조물의 조립 공정을 자동화하는 프로젝트

**핵심 공정 순서:** 기둥 설치 → 프레임 설치 → 잠금핀 체결(2단계 삽입) → Frame 좌표계 측정 → 패널 설치

## 1. 시스템 개요

- **F/T 센서 기반 힘 제어 삽입** — Lock Pin 1차 삽입(설정 깊이) 후 재파지/가압으로 최종 삽입, 저항 과다 시 후퇴
- **실측 기반 좌표계 생성** — Frame 기준점(P1/P2/P3) 실측으로 Frame Coordinate System 생성
- **측정 좌표계 기준 후속 동작** — 생성된 Frame Coordinate 기준으로 Panel 위치·자세 제어

```
현장관리자 ↔ UI ↔ ROS2 ↔ M0609 Robot ↔ Controller ↔ Gripper ↔ 조립 대상 구조물
                    ↕
                    DB (Work Order, Recipe, Operation, Parameter, 작업 이력, 오류 로그, 측정 결과)
```

## 2. 운영체제 환경

- **OS:** Ubuntu 24.04
- **ROS Version:** ROS2 Jazzy
- **로봇 프로그래밍:** DART Platform, DART Studio, DRL (Doosan Robot Language, Python 기반)
- **로봇:** Doosan M0609 (그리퍼 + 내장 F/T 센서)
- **Language:** Python (typing.Protocol / mypy)

## 3. 패키지 구성

이 저장소는 두 개의 ROS2 패키지로 구성된 colcon 워크스페이스입니다.

| 패키지 | 타입 | 역할 |
|---|---|---|
| `src/solar_panel_interface` | ament_cmake | Action/Msg 인터페이스 정의 |
| `src/solar_panel_robot` | ament_python | 로봇 제어 노드(DRL 동작 로직) |

### solar_panel_interface

작업 관리 노드 ↔ Controller 간 통신 인터페이스 (IF-14~16 대응)

- `action/ExecuteOperation.action` — Work Order ID / Operation ID / Parameter 전달, 진행 상태 피드백, 완료/실패 + Error Code 반환
- `msg/Parameter.msg` — Recipe/Operation Parameter (key/value)

### solar_panel_robot

| 파일 | 역할 |
|---|---|
| `main.py` | 노드 진입점 (`main` entry point) |
| `motion.py` | 로봇 모션(Pick/Place 등) |
| `force_control.py` | F/T 센서 기반 힘 제어 삽입 로직 |
| `gripper.py` | 그리퍼 제어 |
| `config_loader.py` | Recipe/Parameter 설정 로딩 |
| `config/poses.yaml` | 위치/자세 설정값 |

## 4. 의존성

- ROS2 Jazzy (`rclpy`)
- Python 3 (`setuptools`, `pytest` for test)

## 5. 빌드 및 실행

```bash
# 워크스페이스 빌드
colcon build

# 환경 설정
source install/setup.bash

# 로봇 제어 노드 실행
ros2 run solar_panel_robot main
```

## 6. 문서

상세 요구사항은 `docs/` 디렉토리를 참조하세요 (BR → SYS-FR → FR → TC 추적 체계).

| 문서 | 내용 |
|---|---|
| `docs/01_비즈니스_요구서.md` | 비즈니스 목표(BR), 범위, Actor 구분 |
| `docs/02_시스템_요구서.md` | 시스템 기능/비기능 요구사항(SYS-FR/NFR) |
| `docs/03_기능_요구서.md` | 기능 요구서(FR) Traceability Matrix, 잠금핀 체결 상세 |
| `docs/04_인터페이스_요구사항.md` | 물리/ROS2/DB 인터페이스 계약 |
| `docs/05_테스트_요구사항.md` | 테스트 케이스(TC), 요구사항 추적표 |
| `docs/06_하드웨어_요구사항.md` | 하드웨어 구성, Lock Pin/Bracket/좌표계 측정 구조 설계 |
| `docs/07_db_요구사항.md` | DB 데이터 항목 |
| `docs/08_ops_요구사항.md` | 운영 절차 |
| `docs/09_maint_요구사항.md` | 유지보수 점검 항목 |
| `docs/10_최종_시스템_시나리오md` | 전체 시나리오 |
