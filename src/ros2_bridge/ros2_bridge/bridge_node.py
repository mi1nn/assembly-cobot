import json

import os
import requests

from datetime import datetime, timezone
from queue import Empty, Queue
from threading import Lock, Thread
from uuid import uuid4

from flask import Flask, jsonify, request
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from solar_panel_interface.action import ExecuteOperation
from solar_panel_interface.msg import Parameter

BRIDGE_HOST = "0.0.0.0"
BRIDGE_PORT = 8001

BACKEND_BASE_URL = os.getenv(
    "BACKEND_BASE_URL",
    "http://127.0.0.1:5000",
)
BACKEND_CALLBACK_TIMEOUT = 3.0


class Ros2BridgeNode(Node):
    def __init__(self):
        super().__init__("ros2_bridge")

        self.job_queue = Queue()
        self.action_client = ActionClient(
            self,
            ExecuteOperation,
            "execute_operation",
        )

        self._goal_in_progress = False
        self._state_lock = Lock()
        self._status = "IDLE"
        self._last_job = None

        self.create_timer(
            0.1,
            self.process_job_queue,
        )

        self.get_logger().info(
            "ROS2 Bridge Node started."
        )

    def enqueue_job(self, job: dict) -> None:
        self.job_queue.put(job)

    def process_job_queue(self) -> None:
        with self._state_lock:
            if self._goal_in_progress:
                return

        # Action Server가 준비되지 않았다면 큐에서 작업을 꺼내지 않는다.
        if not self.action_client.server_is_ready():
            with self._state_lock:
                self._status = "ACTION_SERVER_UNAVAILABLE"

            return

        try:
            job = self.job_queue.get_nowait()
        except Empty:
            return

        with self._state_lock:
            self._goal_in_progress = True
            self._status = "SENDING_GOAL"
            self._last_job = job

        self.get_logger().info(
            "Sending Action Goal: "
            f"bridge_job_id={job['bridge_job_id']}, "
            f"work_order_id={job['work_order_id']}, "
            f"operation_id={job['operation_id']}, "
            f"work_execution_id="
            f"{job['work_execution_id']}, "
            f"operation_execution_id="
            f"{job['operation_execution_id']}, "
            f"robot_id={job['robot_id']}"
        )

        goal = ExecuteOperation.Goal()
        goal.work_order_id = str(
            job["work_order_id"]
        )   
        goal.operation_id = str(
            job["operation_id"]
        )
        goal.parameters = (
            self.convert_parameters(
                job["parameters"]
            )
        )

        send_goal_future = (
            self.action_client.send_goal_async(
                goal,
                feedback_callback=(
                    self.feedback_callback
                ),
            )
        )

        send_goal_future.add_done_callback(
            self.goal_response_callback
        )

        self.job_queue.task_done()

    def goal_response_callback(self, future) -> None:
        try:
            goal_handle = future.result()
        except Exception as error:
            self.get_logger().error(
                f"Failed to send Action Goal: {error}"
            )

            with self._state_lock:
                self._status = "GOAL_SEND_FAILED"
                self._goal_in_progress = False

            return

        if not goal_handle.accepted:
            self.get_logger().warning(
                "Action Goal rejected."
            )

            with self._state_lock:
                self._status = "GOAL_REJECTED"
                self._goal_in_progress = False

            return

        self.get_logger().info(
            "Action Goal accepted."
        )

        with self._state_lock:
            self._status = "EXECUTING"

        result_future = goal_handle.get_result_async()

        result_future.add_done_callback(
            self.result_callback
        )

    def feedback_callback(
        self,
        feedback_message,
    ) -> None:
        feedback = feedback_message.feedback

        self.get_logger().info(
            "Action Feedback: "
            f"operation={feedback.current_operation}, "
            f"status={feedback.status}, "
            f"progress={feedback.progress:.1f}%"
        )

        with self._state_lock:
            self._status = feedback.status

            if self._last_job is not None:
                self._last_job["progress"] = (
                    feedback.progress
                )

    def result_callback(self, future) -> None:
        try:
            wrapped_result = future.result()
            result = wrapped_result.result
        except Exception as error:
            self.get_logger().error(
                "Failed to receive Action result: "
                f"{error}"
            )

            with self._state_lock:
                self._status = "RESULT_FAILED"
                self._goal_in_progress = False

            return

        with self._state_lock:
            job = (
                dict(self._last_job)
                if self._last_job is not None
                else None
            )

        if job is None:
            self.get_logger().error(
                "Action result has no matching job."
            )

            with self._state_lock:
                self._status = "CALLBACK_FAILED"
                self._goal_in_progress = False

            return

        final_status = (
            "COMPLETED"
            if result.success
            else "FAILED"
        )

        try:
            self.notify_backend_action_result(
                job=job,
                result=result,
            )
        except Exception as error:
            self.get_logger().error(
                "Could not notify Backend of "
                f"Action result: {error}"
            )

            with self._state_lock:
                self._status = "CALLBACK_FAILED"
                self._goal_in_progress = False

                if self._last_job is not None:
                    self._last_job["result"] = {
                        "success": result.success,
                        "error_code": (
                            result.error_code
                        ),
                        "message": result.message,
                    }

                    self._last_job[
                        "callback_error"
                    ] = str(error)

            return

        if result.success:
            self.get_logger().info(
                "Action completed successfully: "
                f"{result.message}"
            )
        else:
            self.get_logger().error(
                "Action failed: "
                f"error_code={result.error_code}, "
                f"message={result.message}"
            )

        with self._state_lock:
            self._status = final_status
            self._goal_in_progress = False

            if self._last_job is not None:
                self._last_job["result"] = {
                    "success": result.success,
                    "error_code": (
                        result.error_code
                    ),
                    "message": result.message,
                }

                self._last_job[
                    "backend_notified"
                ] = True


    def notify_backend_action_result(
        self,
        job: dict,
        result,
    ) -> dict:
        callback_url = (
            f"{BACKEND_BASE_URL}"
            "/api/v1/executions/action-result"
        )

        request_data = {
            "work_execution_id": (
                job["work_execution_id"]
            ),
            "operation_execution_id": (
                job["operation_execution_id"]
            ),
            "success": result.success,
            "error_code": result.error_code,
            "message": result.message,
        }

        response = requests.post(
            callback_url,
            json=request_data,
            timeout=BACKEND_CALLBACK_TIMEOUT,
        )

        if response.status_code != 200:
            raise RuntimeError(
                "Backend callback failed with "
                f"HTTP {response.status_code}: "
                f"{response.text}"
            )

        try:
            response_data = response.json()
        except ValueError as error:
            raise RuntimeError(
                "Backend callback returned "
                "invalid JSON."
            ) from error

        if not response_data.get("success"):
            raise RuntimeError(
                "Backend rejected the "
                "Action result callback."
            )

        return response_data

    def get_bridge_status(self) -> dict:
        with self._state_lock:
            status = self._status
            last_job = self._last_job

        return {
            "status": status,
            "pending_jobs": self.job_queue.qsize(),
            "last_job": last_job,
        }

    def convert_parameters(
        self,
        parameters: dict,
    ) -> list[Parameter]:
        ros_parameters = []

        for key, value in parameters.items():
            parameter = Parameter()
            parameter.key = str(key)

            if isinstance(value, str):
                parameter.value = value
            else:
                parameter.value = json.dumps(
                    value,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )

            ros_parameters.append(parameter)

        return ros_parameters    

def create_http_app(
    node: Ros2BridgeNode,
) -> Flask:
    http_app = Flask("ros2_bridge_http")

    @http_app.get("/health")
    def health_check():
        return jsonify({
            "success": True,
            "data": {
                "status": "ok",
                "service": "ros2-bridge",
                "ros_node": node.get_name(),
            },
            "error": None,
        }), 200

    @http_app.get("/status")
    def get_status():
        return jsonify({
            "success": True,
            "data": node.get_bridge_status(),
            "error": None,
        }), 200

    @http_app.post("/jobs")
    def create_job():
        request_data = request.get_json(
            silent=True,
        )

        if not isinstance(request_data, dict):
            return jsonify({
                "success": False,
                "data": None,
                "error": {
                    "code": "INVALID_JSON",
                    "message": (
                        "A JSON request body is required."
                    ),
                },
            }), 400

        required_fields = (
            "work_order_id",
            "operation_id",
            "work_execution_id",
            "operation_execution_id",
            "robot_id",
            "parameters",
        )

        missing_fields = [
            field
            for field in required_fields
            if request_data.get(field) is None
        ]

        if missing_fields:
            return jsonify({
                "success": False,
                "data": None,
                "error": {
                    "code": "MISSING_REQUIRED_FIELDS",
                    "message": (
                        "Missing required fields: "
                        + ", ".join(missing_fields)
                    ),
                },
            }), 400

        id_fields = {
            "work_order_id": (
                "INVALID_WORK_ORDER_ID"
            ),
            "operation_id": (
                "INVALID_OPERATION_ID"
            ),
            "work_execution_id": (
                "INVALID_WORK_EXECUTION_ID"
            ),
            "operation_execution_id": (
                "INVALID_OPERATION_EXECUTION_ID"
            ),
            "robot_id": (
                "INVALID_ROBOT_ID"
            ),
        }

        for field, error_code in (
            id_fields.items()
        ):
            value = request_data[field]

            if not is_positive_integer(value):
                return jsonify({
                    "success": False,
                    "data": None,
                    "error": {
                        "code": error_code,
                        "message": (
                            f"{field} must be "
                            "a positive integer."
                        ),
                    },
                }), 400

        parameters = request_data[
            "parameters"
        ]

        if not isinstance(parameters, dict):
            return jsonify({
                "success": False,
                "data": None,
                "error": {
                    "code": "INVALID_PARAMETERS",
                    "message": (
                        "parameters must be "
                        "a JSON object."
                    ),
                },
            }), 400

        job = {
            "bridge_job_id": str(uuid4()),
            "work_order_id": request_data[
                "work_order_id"
            ],
            "operation_id": request_data[
                "operation_id"
            ],
            "work_execution_id": request_data[
                "work_execution_id"
            ],
            "operation_execution_id": (
                request_data[
                    "operation_execution_id"
                ]
            ),
            "robot_id": request_data[
                "robot_id"
            ],
            "parameters": parameters,
            "received_at": datetime.now(
                timezone.utc,
            ).isoformat(),
        }

        node.enqueue_job(job)

        return jsonify({
            "success": True,
            "data": {
                "accepted": True,
                "bridge_job_id": (
                    job["bridge_job_id"]
                ),
            },
            "error": None,
        }), 202

    return http_app

def is_positive_integer(value) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and value > 0
    )

def run_http_server(
    http_app: Flask,
) -> None:
    http_app.run(
        host=BRIDGE_HOST,
        port=BRIDGE_PORT,
        debug=False,
        use_reloader=False,
    )


def main(args=None):
    rclpy.init(args=args)

    node = Ros2BridgeNode()
    http_app = create_http_app(node)

    http_thread = Thread(
        target=run_http_server,
        args=(http_app,),
        daemon=True,
    )

    http_thread.start()

    node.get_logger().info(
        f"Bridge HTTP server listening "
        f"on port {BRIDGE_PORT}."
    )

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info(
            "ROS2 Bridge Node stopping."
        )
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
