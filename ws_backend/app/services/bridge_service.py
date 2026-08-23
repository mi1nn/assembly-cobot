import requests
from flask import current_app


class BridgeConnectionError(RuntimeError):
    pass


class BridgeResponseError(RuntimeError):
    pass

def get_bridge_health() -> dict:
    bridge_base_url = current_app.config[
        "BRIDGE_BASE_URL"
    ]

    timeout_seconds = current_app.config[
        "BRIDGE_TIMEOUT_SECONDS"
    ]

    health_url = f"{bridge_base_url}/health"

    try:
        response = requests.get(
            health_url,
            timeout=timeout_seconds,
        )
    except requests.RequestException as error:
        raise BridgeConnectionError(
            "Could not connect to ROS2 Bridge."
        ) from error

    if response.status_code != 200:
        raise BridgeResponseError(
            "ROS2 Bridge returned an "
            f"unexpected HTTP status: "
            f"{response.status_code}"
        )

    try:
        response_data = response.json()
    except ValueError as error:
        raise BridgeResponseError(
            "ROS2 Bridge returned invalid JSON."
        ) from error

    if not response_data.get("success"):
        raise BridgeResponseError(
            "ROS2 Bridge health check failed."
        )

    bridge_data = response_data.get("data")

    if not isinstance(bridge_data, dict):
        raise BridgeResponseError(
            "ROS2 Bridge response data is invalid."
        )

    return bridge_data

def submit_bridge_job(
    work_order_id: int,
    operation_id: int,
    work_execution_id: int,
    operation_execution_id: int,
    robot_id: int,
    parameters: dict | None,
) -> dict:
    bridge_base_url = current_app.config[
        "BRIDGE_BASE_URL"
    ]

    timeout_seconds = current_app.config[
        "BRIDGE_TIMEOUT_SECONDS"
    ]

    jobs_url = f"{bridge_base_url}/jobs"

    request_data = {
        "work_order_id": work_order_id,
        "operation_id": operation_id,
        "work_execution_id": (
            work_execution_id
        ),
        "operation_execution_id": (
            operation_execution_id
        ),
        "robot_id": robot_id,
        "parameters": parameters or {},
    }

    try:
        response = requests.post(
            jobs_url,
            json=request_data,
            timeout=timeout_seconds,
        )
    except requests.RequestException as error:
        raise BridgeConnectionError(
            "Could not connect to ROS2 Bridge."
        ) from error

    try:
        response_data = response.json()
    except ValueError as error:
        raise BridgeResponseError(
            "ROS2 Bridge returned invalid JSON."
        ) from error

    if response.status_code != 202:
        bridge_error = response_data.get(
            "error"
        )

        bridge_message = None

        if isinstance(bridge_error, dict):
            bridge_message = bridge_error.get(
                "message"
            )

        raise BridgeResponseError(
            bridge_message
            or (
                "ROS2 Bridge rejected the job "
                f"with HTTP {response.status_code}."
            )
        )

    if not response_data.get("success"):
        raise BridgeResponseError(
            "ROS2 Bridge did not accept the job."
        )

    bridge_data = response_data.get("data")

    if not isinstance(bridge_data, dict):
        raise BridgeResponseError(
            "ROS2 Bridge response data is invalid."
        )

    return bridge_data