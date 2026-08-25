from flask import Blueprint, jsonify

from app.services.bridge_service import (
    BridgeConnectionError,
    BridgeResponseError,
    recover_bridge_robot,
)
from app.services.execution_service import (
    get_robot_by_id,
    mark_robot_recovered,
)
from app.services.log_service import (
    create_system_log,
)
from app.services.robot_service import (
    get_active_execution_for_robot,
    get_robots,
)


robots_bp = Blueprint(
    "robots",
    __name__,
    url_prefix="/api/v1/robots",
)


@robots_bp.get("")
def list_robots():
    robots = get_robots()

    data = []

    for robot in robots:
        active_execution = (
            get_active_execution_for_robot(
                robot.robot_id
            )
        )

        robot_data = robot.to_dict()

        robot_data["work_execution_id"] = (
            active_execution.work_execution_id
            if active_execution
            else None
        )

        robot_data["work_order_id"] = (
            active_execution.work_order_id
            if active_execution
            else None
        )

        data.append(robot_data)

    return jsonify({
        "success": True,
        "data": data,
        "error": None,
    }), 200


@robots_bp.post("/<int:robot_id>/recover")
def recover_robot(robot_id: int):
    robot = get_robot_by_id(robot_id)

    if robot is None:
        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": "ROBOT_NOT_FOUND",
                "message": (
                    f"Robot {robot_id} "
                    "was not found."
                ),
            },
        }), 404

    if robot.status != "ERROR":
        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": (
                    "ROBOT_RECOVERY_NOT_REQUIRED"
                ),
                "message": (
                    "Only an ERROR Robot "
                    "can be recovered."
                ),
            },
        }), 409

    create_system_log(
        log_type="ROBOT",
        severity="WARNING",
        code="ROBOT_RECOVERY_REQUESTED",
        message=(
            f"Recovery requested for "
            f"Robot {robot_id}."
        ),
        robot_id=robot_id,
    )

    try:
        recovery_result = (
            recover_bridge_robot(robot_id)
        )

    except BridgeConnectionError as error:
        create_system_log(
            log_type="ERROR",
            severity="ERROR",
            code="ROBOT_RECOVERY_FAILED",
            message=str(error),
            robot_id=robot_id,
        )

        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": "BRIDGE_UNAVAILABLE",
                "message": str(error),
            },
        }), 503

    except BridgeResponseError as error:
        create_system_log(
            log_type="ERROR",
            severity="ERROR",
            code="ROBOT_RECOVERY_FAILED",
            message=str(error),
            robot_id=robot_id,
        )

        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": "RECOVERY_REJECTED",
                "message": str(error),
            },
        }), 502

    try:
        mark_robot_recovered(robot)

    except ValueError as error:
        return jsonify({
            "success": False,
            "data": None,
            "error": {
                "code": (
                    "INVALID_ROBOT_TRANSITION"
                ),
                "message": str(error),
            },
        }), 409

    create_system_log(
        log_type="ROBOT",
        severity="INFO",
        code="ROBOT_RECOVERY_COMPLETED",
        message=(
            recovery_result.get("message")
            or (
                f"Robot {robot_id} "
                "recovery completed."
            )
        ),
        robot_id=robot_id,
    )

    return jsonify({
        "success": True,
        "data": {
            "robot": robot.to_dict(),
            "recovery_result": recovery_result,
        },
        "error": None,
    }), 200
