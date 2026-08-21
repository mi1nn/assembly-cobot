# Backend 개발 환경 설정 (venv)

> 검증 환경: Ubuntu 24.04 / Python 3.12 / ROS2 Jazzy / PostgreSQL 16 (Docker)

## 1. 왜 `--system-site-packages`를 쓰는가

이 프로젝트의 ROS2 Bridge Node는 하나의 프로세스에서 `rclpy`(ROS2)와 `Flask`(HTTP 서버)를 함께 사용한다.

- 일반 venv는 시스템 site-packages를 격리하므로 `/opt/ros/jazzy`의 `rclpy` 등을 import할 수 없다.
- `--system-site-packages` 옵션으로 venv를 만들면 시스템 패키지(rclpy 등)를 그대로 보면서,
  프로젝트 전용 패키지(SQLAlchemy 등)는 venv 안에 격리되어 설치된다.

## 2. venv 생성 및 의존성 설치

최초 1회만 실행한다.

```bash
cd ws_backend/backend

# ROS2 패키지를 볼 수 있는 venv 생성
python3 -m venv --system-site-packages .venv

# 의존성 설치 (requirements.txt 참고)
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

설치되는 항목 (`requirements.txt`):

| 패키지 | 버전 | 용도 |
|---|---|---|
| Flask | 3.1.3 | Backend API + Bridge 내장 HTTP 서버 |
| SQLAlchemy | 2.0.52 | ORM (PostgreSQL 접근) |
| psycopg2 | 2.9.9 | PostgreSQL 드라이버 |
| requests | 2.31.0 | Flask → Bridge HTTP 호출 |

## 3. 활성화 / 비활성화

```bash
# 활성화
source .venv/bin/activate

# 비활성화
deactivate
```

활성화 없이 바로 실행하는 방법:

```bash
.venv/bin/python run.py
```

## 4. 동작 확인

```bash
# Backend 의존성 확인
.venv/bin/python -c "import flask, sqlalchemy, psycopg2, requests; print('OK')"

# ROS2 연동 확인 (ros2_bridge 개발 시 필요)
source /opt/ros/jazzy/setup.bash
.venv/bin/python -c "import rclpy; print('rclpy OK')"
```

둘 다 `OK`가 출력되면 준비 완료.

## 5. 주의 사항

- **ROS2를 사용하는 노드 실행 전에는 반드시 `source /opt/ros/jazzy/setup.bash`를 먼저 한다.**
  venv는 시스템 패키지를 "볼 수 있게" 해줄 뿐, ROS2 환경 변수(`PYTHONPATH`, `AMENT_PREFIX_PATH` 등)는 sourcing으로만 설정된다.
- venv 안에서 `pip install`한 패키지는 venv에만 설치되며 시스템 Python을 오염시키지 않는다.
- `.venv/`는 git에 커밋되지 않는다 (`.gitignore`에 포함됨).
- 의존성을 추가했으면 `pip freeze > requirements.txt` 대신, 직접 requirements.txt에
  `패키지==버전` 한 줄을 추가한다 (시스템 패키지까지 freeze되는 것을 방지).

## 6. PostgreSQL (Docker)

Backend가 접속하는 DB는 Docker 컨테이너로 실행한다. 자세한 내용은
`ws_db/Docker_PostgreSQL_Setup.md` 참고.

```bash
# 실행 상태 확인
docker ps | grep robot-postgres

# 중지 상태면 시작
docker start robot-postgres
```

연결 정보: `postgresql://postgres:postgres123@localhost:5432/robot_workorder_db`
