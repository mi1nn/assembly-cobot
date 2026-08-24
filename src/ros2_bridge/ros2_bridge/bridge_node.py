import json

import os
import requests

from datetime import datetime, timezone
from queue import Empty, Queue
from threading import Lock, Thread
from uuid import uuid4
from types import SimpleNamespace

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
        self._stopped_work_execution_ids = set()

        self.create_timer(
            0.1,
            self.process_job_queue,
        )

        self.get_logger().info(
            "ROS2 Bridge Node started."
        )

    def enqueue_work(
        self,
        work: dict,
    ) -> None:
        for operation in work["operations"]:
            job = {
                "bridge_work_id": (
                    work["bridge_work_id"]
                ),
                "work_order_id": (
                    work["work_order_id"]
                ),
                "work_execution_id": (
                    work["work_execution_id"]
                ),
                "robot_id": work["robot_id"],
                "operation_execution_id": (
                    operation[
                        "operation_execution_id"
                    ]
                ),
                "operation_id": (
                    operation["operation_id"]
                ),
                "sequence": (
                    operation["sequence"]
                ),
                "parameters": (
                    operation["parameters"]
                ),
                "components": (
                    operation["components"]
                ),
                "received_at": (
                    work["received_at"]
                ),
            }

            self.job_queue.put(job)

    def stop_current_work(
        self,
        status: str,
    ) -> dict | None:
        with self._state_lock:
            current_job = (
                dict(self._last_job)
                if self._last_job is not None
                else None
            )

            self._status = status
            self._goal_in_progress = False

            if current_job is not None:
                self._stopped_work_execution_ids.add(
                    current_job[
                        "work_execution_id"
                    ]
                )

        return current_job


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
            work_stopped = (
                job["work_execution_id"]
                in self._stopped_work_execution_ids
            )

        if work_stopped:
            self.get_logger().warning(
                "Skipping queued operation from "
                "a stopped work: "
                "work_execution_id="
                f"{job['work_execution_id']}, "
                "operation_execution_id="
                f"{job['operation_execution_id']}"
            )

            self.job_queue.task_done()
            return

        with self._state_lock:
            self._goal_in_progress = True
            self._status = "SENDING_GOAL"
            self._last_job = job

        self.get_logger().info(
            "Sending Action Goal: "
            f"bridge_work_id={job['bridge_work_id']}, "
            f"work_order_id={job['work_order_id']}, "
            f"operation_id={job['operation_id']}, "
            f"work_execution_id="
            f"{job['work_execution_id']}, "
            f"operation_execution_id="
            f"{job['operation_execution_id']}, "
            f"robot_id={job['robot_id']}"
        )

        goal = ExecuteOperation.Goal()

        goal.work_order_id = int(
            job["work_order_id"]
        )

        goal.work_execution_id = int(
            job["work_execution_id"]
        )

        goal.operation_id = int(
            job["operation_id"]
        )

        goal.operation_execution_id = int(
            job["operation_execution_id"]
        )

        goal.robot_id = int(
            job["robot_id"]
        )

        goal.parameters = (
            self.convert_parameters(
                job["parameters"]
            )
        )

        goal.components = json.dumps(
            job["components"],
            ensure_ascii=False,
            separators=(",", ":"),
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

            current_job = self.stop_current_work(
                "GOAL_SEND_FAILED"
            )

            if current_job is not None:
                try:
                    self.notify_backend_dispatch_failure(
                        job=current_job,
                        error_code="GOAL_SEND_FAILED",
                        message=(
                            "Failed to send the Action Goal.: "
                            f"{error}"
                        ),
                    )

                except Exception as callback_error:
                    self.get_logger().error(
                        "Could not notify Backend of "
                        "Goal send failure: "
                        f"{callback_error}"
                    )

            return

        if not goal_handle.accepted:
            self.get_logger().warning(
                "Action Goal rejected."
            )

            current_job = self.stop_current_work(
                "GOAL_REJECTED"
            )

            if current_job is not None:
                try:
                    self.notify_backend_dispatch_failure(
                        job=current_job,
                        error_code="GOAL_REJECTED",
                        message=(
                            "Controller rejected the "
                            "Action Goal."
                        ),
                    )

                except Exception as callback_error:
                    self.get_logger().error(
                        "Could not notify Backend of "
                        "Goal rejection: "
                        f"{callback_error}"
                    )

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

        status_names = {
            ExecuteOperation.Feedback
            .STATUS_PENDING: "PENDING",
            ExecuteOperation.Feedback
            .STATUS_RUNNING: "RUNNING",
            ExecuteOperation.Feedback
            .STATUS_COMPLETED: "COMPLETED",
            ExecuteOperation.Feedback
            .STATUS_FAILED: "FAILED",
            ExecuteOperation.Feedback
            .STATUS_CANCELLED: "CANCELLED",
        }

        status_name = status_names.get(
            feedback.status,
            "UNKNOWN",
        )

        with self._state_lock:
            current_job = (
                dict(self._last_job)
                if self._last_job is not None
                else None
            )

        if current_job is None:
            self.get_logger().warning(
                "Feedback received without "
                "an active job."
            )
            return

        expected_execution_id = int(
            current_job[
                "operation_execution_id"
            ]
        )

        if (
            feedback.operation_execution_id
            != expected_execution_id
        ):
            self.get_logger().warning(
                "Feedback execution ID mismatch: "
                f"expected={expected_execution_id}, "
                "received="
                f"{feedback.operation_execution_id}"
            )
            return

        self.get_logger().info(
            "Action Feedback: "
            "operation_execution_id="
            f"{feedback.operation_execution_id}, "
            f"status={status_name}, "
            f"message={feedback.message}"
        )

        try:
            self.notify_backend_action_feedback(
                job=current_job,
                feedback=feedback,
            )

        except Exception as error:
            self.get_logger().error(
                "Could not notify Backend of "
                "Action feedback: "
                f"{error}"
            )

        with self._state_lock:
            self._status = status_name

    def result_callback(self, future) -> None:

        try:
            wrapped_result = future.result()
            result = wrapped_result.result
        except Exception as error:
            self.get_logger().error(
                "Failed to receive Action result: "
                f"{error}"
            )

            current_job = self.stop_current_work(
                "RESULT_FAILED"
            )

            if current_job is not None:
                try:
                    self.notify_backend_dispatch_failure(
                        job=current_job,
                        error_code=(
                            "RESULT_RECEIVE_FAILED"
                        ),
                        message=(
                            "Failed to receive the "
                            "Action Result: "
                            f"{error}"
                        ),
                    )

                except Exception as callback_error:
                    self.get_logger().error(
                        "Could not notify Backend of "
                        "Result receive failure: "
                        f"{callback_error}"
                    )

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

        if not result.success:
            with self._state_lock:
                self._stopped_work_execution_ids.add(
                    job["work_execution_id"]
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

            self.stop_current_work(
                "CALLBACK_FAILED"
            )

            with self._state_lock:
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

    def notify_backend_action_feedback(
        self,
        job: dict,
        feedback,
    ) -> dict:
        callback_url = (
            f"{BACKEND_BASE_URL}"
            "/api/v1/executions/action-feedback"
        )

        request_data = {
            "work_execution_id": (
                job["work_execution_id"]
            ),
            "operation_execution_id": (
                feedback.operation_execution_id
            ),
            "status": int(
                feedback.status
            ),
            "message": feedback.message,
        }

        response = requests.post(
            callback_url,
            json=request_data,
            timeout=BACKEND_CALLBACK_TIMEOUT,
        )

        if response.status_code != 200:
            raise RuntimeError(
                "Backend feedback callback "
                "failed with "
                f"HTTP {response.status_code}: "
                f"{response.text}"
            )

        try:
            response_data = response.json()

        except ValueError as error:
            raise RuntimeError(
                "Backend feedback callback "
                "returned invalid JSON."
            ) from error

        if not response_data.get("success"):
            raise RuntimeError(
                "Backend rejected the "
                "Action feedback callback."
            )

        return response_data

    def notify_backend_dispatch_failure(
        self,
        job: dict,
        error_code: str,
        message: str,
    ) -> dict:
        failure_result = SimpleNamespace(
            success=False,
            error_code=error_code,
            message=message,
        )

        return self.notify_backend_action_result(
            job=job,
            result=failure_result,
        )

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

        validation_error = (
            validate_work_command(
                request_data
            )
        )

        if validation_error is not None:
            error_code, error_message = (
                validation_error
            )

            return jsonify({
                "success": False,
                "data": None,
                "error": {
                    "code": error_code,
                    "message": error_message,
                },
            }), 400

        sorted_operations = sorted(
            request_data["operations"],
            key=lambda operation: (
                operation["sequence"]
            ),
        )

        work = {
            "bridge_work_id": str(
                uuid4()
            ),
            "work_order_id": (
                request_data[
                    "work_order_id"
                ]
            ),
            "work_execution_id": (
                request_data[
                    "work_execution_id"
                ]
            ),
            "robot_id": request_data[
                "robot_id"
            ],
            "operations": [
                dict(operation)
                for operation
                in sorted_operations
            ],
            "received_at": datetime.now(
                timezone.utc,
            ).isoformat(),
        }

        node.enqueue_work(work)

        return jsonify({
            "success": True,
            "data": {
                "accepted": True,
                "bridge_work_id": (
                    work["bridge_work_id"]
                ),
                "work_execution_id": (
                    work[
                        "work_execution_id"
                    ]
                ),
                "total_operations": len(
                    work["operations"]
                ),
            },
            "error": None,
        }), 202

    return http_app

def validate_operation_item(
    operation: object,
    index: int,
) -> tuple[str, str] | None:
    if not isinstance(operation, dict):
        return (
            "INVALID_OPERATION",
            (
                f"operations[{index}] must be "
                "a JSON object."
            ),
        )

    required_fields = (
        "operation_execution_id",
        "operation_id",
        "sequence",
        "parameters",
        "components",
    )

    missing_fields = [
        field
        for field in required_fields
        if operation.get(field) is None
    ]

    if missing_fields:
        return (
            "MISSING_OPERATION_FIELDS",
            (
                f"operations[{index}] is missing: "
                + ", ".join(missing_fields)
            ),
        )

    integer_fields = (
        "operation_execution_id",
        "operation_id",
        "sequence",
    )

    for field in integer_fields:
        if not is_positive_integer(
            operation[field]
        ):
            return (
                f"INVALID_{field.upper()}",
                (
                    f"operations[{index}].{field} "
                    "must be a positive integer."
                ),
            )

    if not isinstance(
        operation["parameters"],
        dict,
    ):
        return (
            "INVALID_PARAMETERS",
            (
                f"operations[{index}].parameters "
                "must be a JSON object."
            ),
        )

    if not isinstance(
        operation["components"],
        list,
    ):
        return (
            "INVALID_COMPONENTS",
            (
                f"operations[{index}].components "
                "must be a JSON array."
            ),
        )

    return None

def validate_work_command(
    command: object,
) -> tuple[str, str] | None:
    if not isinstance(command, dict):
        return (
            "INVALID_JSON",
            "A JSON request body is required.",
        )

    required_fields = (
        "work_order_id",
        "work_execution_id",
        "robot_id",
        "operations",
    )

    missing_fields = [
        field
        for field in required_fields
        if command.get(field) is None
    ]

    if missing_fields:
        return (
            "MISSING_REQUIRED_FIELDS",
            (
                "Missing required fields: "
                + ", ".join(missing_fields)
            ),
        )

    id_fields = (
        "work_order_id",
        "work_execution_id",
        "robot_id",
    )

    for field in id_fields:
        if not is_positive_integer(
            command[field]
        ):
            return (
                f"INVALID_{field.upper()}",
                (
                    f"{field} must be "
                    "a positive integer."
                ),
            )

    operations = command["operations"]

    if (
        not isinstance(operations, list)
        or not operations
    ):
        return (
            "INVALID_OPERATIONS",
            (
                "operations must be a "
                "non-empty JSON array."
            ),
        )

    sequences = set()
    operation_execution_ids = set()

    for index, operation in enumerate(
        operations
    ):
        validation_error = (
            validate_operation_item(
                operation,
                index,
            )
        )

        if validation_error is not None:
            return validation_error

        sequence = operation["sequence"]

        if sequence in sequences:
            return (
                "DUPLICATE_SEQUENCE",
                (
                    "Operation sequence values "
                    "must be unique."
                ),
            )

        sequences.add(sequence)

        operation_execution_id = (
            operation[
                "operation_execution_id"
            ]
        )

        if (
            operation_execution_id
            in operation_execution_ids
        ):
            return (
                (
                    "DUPLICATE_OPERATION_"
                    "EXECUTION_ID"
                ),
                (
                    "operation_execution_id "
                    "values must be unique."
                ),
            )

        operation_execution_ids.add(
            operation_execution_id
        )

    return None

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
