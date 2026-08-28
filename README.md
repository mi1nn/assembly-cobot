# assembly-cobot

> 두산로보틱스 M0609 협동로봇으로 지상형 태양광 패널 구조물의 조립 공정을 자동화하고 MES(Work Order·이력 관리)와 연동하는 프로젝트
> **F/T 센서 기반 힘 제어 삽입으로 구현한, 비전 없는 협동로봇 조립 자동화 시스템**

**핵심 공정 순서:** 기둥 설치 → 프레임 설치 → 스냅핏 체결 → 패널 설치

> 기둥–주춧돌의 잠금핀(Lock Pin) 체결은 로봇·작업자 협동 작업으로 **작업자가 수행**합니다 (2026-08 범위 조정).

## 1. 시스템 개요

- **F/T 센서 기반 힘 제어 삽입** — 정해진 깊이까지 1차 삽입 → 재파지 → 축 방향 가압으로 최종 삽입. 저항이 임계값을 넘으면 후퇴하거나(스냅핏 체결) 미세하게 위치를 조정(기둥 삽입)합니다. 임계값은 코드에 두지 않고 DB Recipe/Parameter로 관리합니다.


```
현장관리자 ↔ Dashboard(HTML/JS) ↔ Flask Backend ↔ PostgreSQL
                                       │ HTTP/REST
                                       ▼
                                  ROS2 Bridge (별도 프로세스)
                                       │ ROS2 Action
                                       ▼
                              Controller ↔ M0609 Robot + Gripper + F/T Sensor
```


## 2. 운영체제 환경

- **OS:** Ubuntu 24.04
- **ROS Version:** ROS2 Jazzy
- **로봇 프로그래밍:** DART Platform, DART Studio, DRL (Doosan Robot Language, Python 기반)
- **로봇:** Doosan M0609 (그리퍼 + 내장 F/T 센서)
- **Backend:** Python / Flask, SQLAlchemy, PostgreSQL
- **Language:** Python  

## 3. 🛠️ 사용 장비 목록 (Hardware List)

본 프로젝트에서는 두산로보틱스 M0609 협동로봇과 2지 평행 그리퍼를 이용하여 태양광 패널 구조물의 부품을 파지·이송·삽입하였습니다. 구조물 부품과 고정 지그는 STL 모델을 기반으로 3D 프린팅하여 제작하였습니다.

|    구분    | 장비 및 부품명          |  수량 | 용도                                              |
| :------: | :---------------- | :-: | :---------------------------------------------- |
|   로봇 장비  | 두산로보틱스 M0609 협동로봇 |  1대 | 부품의 파지, 이송, 삽입 및 조립 작업 수행                       |
|   로봇 장비  | 2지 평행 그리퍼         |  1대 | 태양광 패널과 구조물 부품의 파지 및 해제                         |
|   제어 장비  | 로봇 제어기 및 티칭 펜던트   |  1식 | 로봇 동작 제어, 좌표 설정 및 작업 상태 확인                      |
|   제어 장비  | 로봇 제어용 PC         |  1대 | Ubuntu 24.04 및 ROS 2 Jazzy 기반 제어 프로그램과 UI 실행    |
|   제작 장비  | FDM 방식 3D 프린터     |  1대 | 태양광 패널 구조물의 부품 제작                   |
| 조립 보조 장비 | 기둥 및 스냅핀 고정 지그    |  1식 | 기둥과 스냅핀의 위치 및 자세를 일정하게 유지하여 로봇의 안정적인 파지와 조립을 보조 |
|   조립 부품  | Solar Panel       |  1식 | 로봇 조립 작업의 대상이 되는 태양광 패널                         |
|   조립 부품  | Base Stone        |  6개 | 태양광 패널 구조물을 지지하고 고정하는 하부 주춧돌 부품                    |
|   조립 부품  | Short Column      |  3개 | 태양광 패널 프레임을 지지하는 짧은 기둥                          |
|   조립 부품  | Long Column      |  3개 | 태양광 패널 프레임을 지지하는 긴 기둥                          |
|   조립 부품  | Col Frame      |  3개 | 태양광 패널 구조물의 세로 방향 프레임                           |
|   조립 부품  | Row Frame         |  4개 | 태양광 패널 구조물의 가로 방향 프레임                           |
|   체결 부품  | Snap Pin   |  6개 | 기둥과 프레임을 고정하는 체결용 잠금 핀                          |
  
## 4. 패키지 구성

### src/solar_panel_interface (ament_cmake)

작업 관리 노드 ↔ Controller 간 통신 인터페이스 (IF-14~16 대응)

- `action/ExecuteOperation.action` — Work Order ID / Operation ID / Parameter 전달, 진행 상태 피드백(STATUS_PENDING~CANCELLED), 완료/실패 + Error Code 반환
- `msg/Parameter.msg` — Recipe/Operation Parameter (key/value)
- `msg/SystemEvent.msg` — Controller → Bridge 이벤트/오류 알림 (severity·code·phase·status·detail)
- `srv/StopOperation.srv` — 실행 중인 Operation 강제 정지 요청
- `srv/RecoverRobot.srv` — ERROR 상태 로봇 복구 요청

### src/solar_panel_robot (ament_python)

| 파일 | 역할 |
|---|---|
| `controller_node.py` | 실제 로봇 Controller 노드 (`namespace="dsr01"`이지만 Action은 절대 경로 `/execute_operation`으로 등록, ExecuteOperation Action Server) |
| `action_server.py` | 실제 장비 없이 통신을 검증하기 위한 Mock Action Server. `ExecuteOperation` Action 외에 `StopOperation`/`RecoverRobot` Service도 함께 구현 |
| `robot_controller.py` / `robot_motion.py` / `solar_motion.py` | 로봇 모션(Pick/Place 등) |
| `force_control.py` | F/T 센서 기반 힘 제어 삽입 로직 |
| `coordinate_manager.py` | *(폐기 예정)* Frame 좌표계(UCS, P1/P2/P3 기반) 생성 유틸. 2026-08 설계 변경으로 Frame 좌표계 측정 자체를 더 이상 사용하지 않기로 확정 — `solar_motion.py` 공정 흐름 연동 계획 없음 |
| `config_loader.py` | Recipe/Parameter 설정 로딩 |
| `ros_bridge_node.py` | Controller를 직접 호출하는 별도 Action Client (`setup.py` entry_points에 등록되어 있지 않아 실행되지 않는 미사용 코드) |
| `config/poses.yaml` | 위치/자세 설정값 |
| `launch/solar_robot.launch.py` | `controller` 노드 실행 |

> `controller_node.py`의 `resolve_operation_code()`는 DB `operation.code`(`postA`~`postF` 등)를 그대로 검증·실행하도록 구현되어 있어, Action 이름/Operation 코드 체계는 Backend·Bridge와 일치합니다.
> `StopOperation`/`RecoverRobot` Service는 실제 `controller_node.py`(`stop_operation_callback` / `recover_robot_callback`)와 `action_server.py`(Mock) **양쪽에 구현**되어 있습니다. 다만 실물 로봇을 포함한 강제정지/복구 end-to-end 검증은 아직 Mock 기준입니다.
> Goal Cancel은 현재 항상 REJECT이며, 정지는 `StopOperation` Service로 처리합니다.

### src/ros2_bridge (ament_python)

Flask Backend의 HTTP 요청을 큐에 쌓았다가 ROS2 Action Goal/Service 호출로 변환해 Controller에 전달하는 브릿지 노드입니다. 노드 자체에 Flask HTTP 서버(포트 8001)를 내장합니다.

- `POST /jobs` — Work Order 하나의 Operation 전체(`operations` 배열)를 한 번에 받아 sequence 순서대로 큐에 쌓고, 하나씩 Action Goal로 전송
- `POST /works/<id>/stop` — 실행 중인 Work를 `StopOperation` Service로 중지 요청
- `POST /robots/<id>/recover` — ERROR 상태 로봇을 `RecoverRobot` Service로 복구 요청
- `GET /health`, `GET /status` — Backend가 호출하는 상태 조회 API
- Action Feedback을 받을 때마다 Backend의 `POST /api/v1/executions/action-feedback`으로, 완료/실패 시 `POST /api/v1/executions/action-result`로 콜백
- Controller가 publish하는 `/system_event`를 구독해 Backend의 `POST /api/v1/logs`로 전달
- Operation 하나가 실패하면 같은 Work Execution의 나머지 대기 중인 Operation은 큐에서 건너뜀

### web_app (Flask Backend)

프론트엔드·백엔드·DB는 완성 단계로, Work Order/Robot/Dashboard/Log 전 구간이 연동되어 있습니다.

| 위치 | 역할 |
|---|---|
| `app/routes`, `app/services`, `app/models` | Work Order / Operation / 실행 이력(Work Execution, Operation Execution) / Robot / Installation API |
| `app/routes/work_orders.py` | `POST /<id>/execute` — Operation 전체를 한 번에 Bridge에 제출, `GET /<id>/progress` — 진행률 조회, `POST /<id>/stop` — 강제 정지 |
| `app/routes/executions.py` | `POST /action-feedback`, `POST /action-result` — Bridge 콜백 수신, DB 상태 갱신 |
| `app/routes/robots.py` | `GET /` — 로봇 목록 + 현재 실행 중인 Work 정보, `POST /<id>/recover` — ERROR 로봇 복구 |
| `app/routes/dashboard.py` | `GET /` — 대시보드 집계(로봇별 활성 실행, 성공률 등) |
| `app/routes/logs.py` | 시스템 로그 조회/기록 (`/system_event` → Bridge → 여기로 연결됨) |
| `database/schema.sql` | PostgreSQL 스키마 (9개 테이블) |
| `frontend/` | 정적 HTML/CSS/JS 대시보드 — Work Order 생성/조회/실행/강제정지, 로봇 상태/복구, 시스템 로그 UI |

## 5. DB 구조
<p align="center">
  <img src="./img/db.png" alt="system">
</p>

## 6. 의존성

- ROS2 Jazzy (`rclpy`)
- Python 3 (`setuptools`, `pytest` for test)
- Flask, Flask-SQLAlchemy, SQLAlchemy, python-dotenv, psycopg2, requests (`web_app/requirements.txt`)
- PostgreSQL 16 (로컬 설치)

## 7. 빌드 및 실행

프로젝트 루트의 스크립트 하나로 Python 환경, PostgreSQL DB/기준 데이터,
ROS2 빌드, 두산 M0609+RG2 bringup, Web, ROS2 bridge, Controller를 구성하고 실행합니다.

최초 실행 전에 DB 비밀번호를 설정합니다.

### 7.1 PostgreSQL (DB)
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

### 7.2 Flask Backend + Frontend
```bash
cd web_app
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt

source .venv/bin/activate
python run.py                    # http://localhost:5000 (API + Dashboard)
```

브라우저에서 `http://localhost:5000`에 접속하면 Work Order 대시보드가 보입니다. 상세 검증 절차는 `web_app/app/README.md`, `web_app/frontend/README.md`를 참조하세요.

### 7.3 ROS2 워크스페이스 빌드
```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
```
  
### 7.4 M0609 Virtual 로봇 + rviz2
※ Doosan에서 제공하는 ROS2 package는 해당 저장소에 포함되지 않음
```bash
source /opt/ros/jazzy/setup.bash
source ~/ws_cobot_pjt/ws_dsr/install/setup.bash   # Doosan Robotics 패키지 워크스페이스

ros2 launch m0609_rg2_bringup bringup.launch.py \
    mode:=virtual \
    name:=dsr01 \
    model:=m0609 \
    host:=127.0.0.1 \
    port:=12345
```
  
### 7.5 이 프로젝트의 Controller + Bridge
```bash
ros2 launch solar_panel_robot solar_robot.launch.py \
    robot_id:=1 \
    backend_base_url:=http://127.0.0.1:5000
```
  
### 7.6 로봇 조종 (Dashboard → rviz2)

`controller` Action Server(`/dsr01/execute_operation`)와 `ros2_bridge`(Flask HTTP 서버, 포트 8001)가 함께 실행됩니다. `robot_id`는 6.2에서 접속한 DB의 `robot.robot_id`와 일치해야 합니다.

### 7.6 로봇 조종 (Dashboard → rviz2)

## 8. 문서
상세 요구사항은 `docs/` 디렉토리 참고 (BR 6 → SYS-FR 24 → FR 24 → TC 15 추적 체계).  

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
| `docs/10_최종_시스템_시나리오.md` | 전체 조립 시나리오 (단계별) |
| `docs/소스코드_역할_정리.md` | 소스 파일별 역할 요약 |

아키텍처/발표 문서 (`docs/architecture/`):

| 문서 | 내용 | 저장소 |
|---|---|---|
| `시스템_구성도_및_작업순서_v2.md` | 실제 구현 기준 시스템 구성도 (최신) | 포함 |
| `시스템_구성도_및_작업순서.md` | 초기 구상 초안 (참고용, 실제 구현과 다름) | 포함 |
| `파일별_함수_동작순서.md` | 프로세스 기동 순서 + 작업 지시 1건의 함수 단위 흐름 | 로컬 전용 |
| `DB_데이터_흐름.md` | 9개 테이블별 데이터 유입·유출 경로 | 로컬 전용 |
| `기술_발표_스크립트.md` | 발표자료 PDF(01~05) 순서에 맞춘 발표 대본 | 로컬 전용 |

> `docs/architecture/`는 `.gitignore` 대상이라 이후 추가된 문서는 로컬에만 존재합니다(위 표의 "로컬 전용"). 초기 아키텍처 문서 2건은 규칙 추가 전 커밋되어 계속 추적됩니다. `docs/test.md`, `CLAUDE.md`, `graphify-out/`도 `.gitignore` 대상입니다.
