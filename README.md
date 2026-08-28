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

## 5. 통합 환경 구성 및 실행

프로젝트 루트의 스크립트 하나로 Python 환경, PostgreSQL DB/기준 데이터,
ROS2 빌드, 두산 M0609+RG2 bringup, Web, ROS2 bridge, Controller를 구성하고 실행합니다.

최초 실행 전에 DB 비밀번호를 설정합니다.

```bash
cp web_app/.env.example web_app/.env
# web_app/.env의 DB_PASSWORD 수정

# 가상 로봇: DB 구축 + 데이터 설정 + 빌드 + 전체 실행
./scripts/setup_and_start.sh

# 실제 로봇
./scripts/setup_and_start.sh --mode real --host 192.168.1.100

# 환경/DB 구성 후 빠르게 재실행
./scripts/setup_and_start.sh --skip-setup --mode real --host 192.168.1.100

# 두산 워크스페이스가 기본 경로와 다른 경우
DSR_WS=/absolute/path/to/ws_dsr ./scripts/setup_and_start.sh
```

기본값은 ROS2 Jazzy와 `~/ws_cobot_pjt/ws_dsr`입니다. 모든 프로세스는 하나의
ROS2 launch가 관리하며 실행 터미널에서 `Ctrl+C`로 함께 종료합니다. Web UI는
`http://127.0.0.1:5000`에서 확인합니다. 스크립트의 ROS2 빌드 산출물은 기존
`build/install/log`와 충돌하지 않도록 `.runtime/`에 생성됩니다.

통합 launch만 직접 실행하려면 기반 워크스페이스부터 순서대로 source합니다.

```bash
source /opt/ros/jazzy/setup.bash
source ~/ws_cobot_pjt/ws_dsr/install/setup.bash
source install/setup.bash

ros2 launch solar_panel_robot solar_robot.launch.py \
  project_root:="$PWD" mode:=virtual host:=127.0.0.1 port:=12345
```

최상위 launch는 `FindPackageShare('m0609_rg2_bringup')`과
`IncludeLaunchDescription()`을 사용합니다. 두산 워크스페이스를 source하지
않으면 `Package 'm0609_rg2_bringup' not found` 오류가 발생합니다.

상태 점검은 별도 터미널에서 실행합니다.

```bash
./scripts/demo_check.sh
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
