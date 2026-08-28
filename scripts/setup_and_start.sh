#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ROS_DISTRO_NAME="${ROS_DISTRO:-jazzy}"
ROS_SETUP="/opt/ros/$ROS_DISTRO_NAME/setup.bash"
DSR_WS="${DSR_WS:-$HOME/ws_cobot_pjt/ws_dsr}"
DSR_SETUP="$DSR_WS/install/setup.bash"
RUNTIME_DIR="$PROJECT_ROOT/.runtime"
MODE="${COBOT_MODE:-virtual}"
ROBOT_HOST="${COBOT_HOST:-127.0.0.1}"
ROBOT_PORT="${COBOT_PORT:-12345}"
RUN_SETUP=true

usage() {
    echo "Usage: $0 [--mode virtual|real] [--host IP] [--port PORT] [--skip-setup]"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --mode) MODE="${2:?--mode requires a value}"; shift 2 ;;
        --host) ROBOT_HOST="${2:?--host requires a value}"; shift 2 ;;
        --port) ROBOT_PORT="${2:?--port requires a value}"; shift 2 ;;
        --skip-setup) RUN_SETUP=false; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Error: unknown option: $1" >&2; usage; exit 1 ;;
    esac
done

if [[ "$MODE" != "virtual" && "$MODE" != "real" ]]; then
    echo "Error: --mode must be virtual or real." >&2
    exit 1
fi

for setup_file in "$ROS_SETUP" "$DSR_SETUP"; do
    if [[ ! -f "$setup_file" ]]; then
        echo "Error: ROS setup file not found: $setup_file" >&2
        exit 1
    fi
done

if [[ "$RUN_SETUP" == true ]]; then
    "$SCRIPT_DIR/demo_setup.sh"
fi

# 기반 워크스페이스를 먼저 source하고 프로젝트를 빌드한다.
# shellcheck disable=SC1090
source "$ROS_SETUP"
# shellcheck disable=SC1090
source "$DSR_SETUP"

cd "$PROJECT_ROOT"
colcon --log-base "$RUNTIME_DIR/log" build \
    --build-base "$RUNTIME_DIR/build" \
    --install-base "$RUNTIME_DIR/install"
# shellcheck disable=SC1091
source "$RUNTIME_DIR/install/setup.bash"

echo "=== Assembly Cobot system start ==="
echo "mode=$MODE host=$ROBOT_HOST port=$ROBOT_PORT"
echo "Stop all launched processes with Ctrl+C."

exec ros2 launch solar_panel_robot solar_robot.launch.py \
    project_root:="$PROJECT_ROOT" \
    mode:="$MODE" \
    host:="$ROBOT_HOST" \
    port:="$ROBOT_PORT"
