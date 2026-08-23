# assembly-cobot

> 두산로보틱스 M0609 협동로봇으로 지상형 태양광 패널 구조물의 조립 공정을 자동화하는 프로젝트

**핵심 공정 순서:** 기둥 설치 → 프레임 설치 → 잠금핀 체결(2단계 삽입) → Frame 좌표계 측정 → 패널 설치

## 1. 시스템 개요

- **F/T 센서 기반 힘 제어 삽입** — Lock Pin 1차 삽입(설정 깊이) 후 재파지/가압으로 최종 삽입, 저항 과다 시 후퇴
- **실측 기반 좌표계 생성** — Frame 기준점(P1/P2/P3) 실측으로 Frame Coordinate System 생성
- **측정 좌표계 기준 후속 동작** — 생성된 Frame Coordinate 기준으로 Panel 위치·자세 제어

```
현장관리자 ↔ Dashboard(HTML/JS) ↔ Flask Backend ↔ PostgreSQL
                                       │ HTTP/REST
                                       ▼
                                  ROS2 Bridge (별도 프로세스)
                                       │ ROS2 Action
                                       ▼
                              Controller ↔ M0609 Robot + Gripper + F/T Sensor
```

자세한 구성도와 각 컴포넌트 간 연결 상태는 `docs/architecture/시스템_구성도_및_작업순서_v2.md`를 참조하세요.

## 2. 운영체제 환경

- **OS:** Ubuntu 24.04
- **ROS Version:** ROS2 Jazzy
- **로봇 프로그래밍:** DART Platform, DART Studio, DRL (Doosan Robot Language, Python 기반)
- **로봇:** Doosan M0609 (그리퍼 + 내장 F/T 센서)
- **Backend:** Python / Flask, SQLAlchemy, PostgreSQL
- **Language:** Python (typing.Protocol / mypy)

## 3. 저장소 구성

이 저장소는 ROS2 colcon 워크스페이스(`src/`)와 Flask 백엔드(`ws_backend/`)로 구성됩니다.

```
assembly-cobot/
├── src/                      # ROS2 colcon 워크스페이스
│   ├── solar_panel_interface # Action/Msg 인터페이스 정의
│   ├── solar_panel_robot     # 로봇 Controller 노드
│   └── ros2_bridge           # Flask Backend ↔ ROS2 Action HTTP 브릿지
├── ws_backend/                # Flask Backend + PostgreSQL 스키마 + 정적 프론트엔드
└── docs/                      # 요구사항 문서 및 아키텍처 문서
```

### src/solar_panel_interface (ament_cmake)

작업 관리 노드 ↔ Controller 간 통신 인터페이스 (IF-14~16 대응)

- `action/ExecuteOperation.action` — Work Order ID / Operation ID / Parameter 전달, 진행 상태 피드백, 완료/실패 + Error Code 반환
- `msg/Parameter.msg` — Recipe/Operation Parameter (key/value)

### src/solar_panel_robot (ament_python)

| 파일 | 역할 |
|---|---|
| `controller_node.py` | 실제 로봇 Controller 노드 (`namespace="dsr01"`, ExecuteOperation Action Server) |
| `action_server.py` | 실제 장비 없이 통신을 검증하기 위한 Mock Action Server |
| `robot_controller.py` / `robot_motion.py` / `solar_motion.py` | 로봇 모션(Pick/Place 등) |
| `force_control.py` | F/T 센서 기반 힘 제어 삽입 로직 |
| `config_loader.py` | Recipe/Parameter 설정 로딩 |
| `ros_bridge_node.py` | Controller를 직접 호출하는 Action Client (현재 Backend와는 분리되어 있음) |
| `config/poses.yaml` | 위치/자세 설정값 |
| `launch/solar_robot.launch.py` | `controller` + `ros_bridge` 노드 실행 |

> `action_server.py`는 아직 `setup.py`의 `console_scripts`에 등록되어 있지 않아 `ros2 run solar_panel_robot action_server`로 바로 실행할 수 없습니다. 실행하려면 `setup.py`에 entry point를 추가해야 합니다.

### src/ros2_bridge (ament_python)

Flask Backend의 HTTP 요청을 큐에 쌓았다가 ROS2 Action Goal로 변환해 Controller에 전달하는 브릿지 노드입니다. 노드 자체에 Flask HTTP 서버(포트 8001)를 내장합니다.

- `GET /health`, `GET /status`, `POST /jobs` — Backend가 호출하는 API
- Action 완료 시 Backend의 `POST /api/v1/executions/action-result`로 결과를 콜백

### ws_backend (Flask Backend)

| 위치 | 역할 |
|---|---|
| `app/routes`, `app/services`, `app/models` | Work Order / Operation / 실행 이력(Work Execution, Operation Execution) API |
| `database/schema.sql` | PostgreSQL 스키마 (9개 테이블) |
| `frontend/` | 정적 HTML/CSS/JS 대시보드 |
| `docs/TIL.md` | 단계별(Step) 구현 기록 |

## 4. 의존성

- ROS2 Jazzy (`rclpy`)
- Python 3 (`setuptools`, `pytest` for test)
- Flask, Flask-SQLAlchemy, SQLAlchemy, python-dotenv, psycopg2, requests (`ws_backend/requirements.txt`)
- PostgreSQL 16 (로컬 설치)

## 5. 빌드 및 실행

### ROS2 워크스페이스

```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash

# 로봇 Controller (실제 장비 연동)
ros2 run solar_panel_robot controller

# ROS2 Bridge (Flask HTTP 서버 내장, 포트 8001)
ros2 run ros2_bridge bridge_node
```

### Flask Backend

```bash
cd ws_backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt

cp .env.example .env   # DB 접속정보, BRIDGE_BASE_URL 등을 채운다

source .venv/bin/activate
python run.py           # http://localhost:5000
```

상세 검증 절차는 `ws_backend/app/README.md`, `ws_backend/database/README.md`를 참조하세요.

## 6. 알려진 미해결 이슈

- `src/ros2_bridge/bridge_node.py`(Backend와 연결된 브릿지)와 `src/solar_panel_robot/ros_bridge_node.py`(Controller를 직접 호출하는 별도 브릿지)가 중복 구현되어 있습니다. 어느 쪽을 canonical bridge로 삼을지 정리가 필요합니다.
- `ws_backend/ros2_ws/`에 `src/ros2_bridge`를 옮기려다 만 것으로 보이는 미완성 스켈레톤(노드 구현 없이 테스트 파일만 존재)이 git에 커밋되지 않은 채 남아 있습니다.
- `/api/v1/executions/action-result` 콜백에는 아직 인증이 없습니다 (`ws_backend/docs/TIL.md` Step 10에 후속 작업으로 명시됨).

## 7. 문서

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
| `docs/architecture/시스템_구성도_및_작업순서_v2.md` | 실제 구현 기준 시스템 구성도 (최신) |
| `docs/architecture/시스템_구성도_및_작업순서.md` | 초기 구상 초안 (참고용, 실제 구현과 다름) |
| `ws_backend/docs/TIL.md` | Backend/ROS2 통합 Step별 구현 기록 |
