from datetime import datetime, timezone
from queue import Empty, Queue
from threading import Lock, Thread
from uuid import uuid4

from flask import Flask, jsonify, request
import rclpy
from rclpy.node import Node


BRIDGE_HOST = "0.0.0.0"
BRIDGE_PORT = 8001


class Ros2BridgeNode(Node):
    def __init__(self):
        super().__init__("ros2_bridge")

        self.job_queue = Queue()

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
        try:
            job = self.job_queue.get_nowait()
        except Empty:
            return

        with self._state_lock:
            self._status = "JOB_RECEIVED"
            self._last_job = job

        self.get_logger().info(
            "Job received: "
            f"bridge_job_id={job['bridge_job_id']}, "
            f"work_order_id={job['work_order_id']}, "
            f"operation_id={job['operation_id']}"
        )

        # Step 9에서 이 위치에 ROS2 Action Goal 전송을 구현한다.

        self.job_queue.task_done()

    def get_bridge_status(self) -> dict:
        with self._state_lock:
            status = self._status
            last_job = self._last_job

        return {
            "status": status,
            "pending_jobs": self.job_queue.qsize(),
            "last_job": last_job,
        }

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

        work_order_id = request_data[
            "work_order_id"
        ]

        operation_id = request_data[
            "operation_id"
        ]

        if not is_positive_integer(work_order_id):
            return jsonify({
                "success": False,
                "data": None,
                "error": {
                    "code": "INVALID_WORK_ORDER_ID",
                    "message": (
                        "work_order_id must be "
                        "a positive integer."
                    ),
                },
            }), 400

        if not is_positive_integer(operation_id):
            return jsonify({
                "success": False,
                "data": None,
                "error": {
                    "code": "INVALID_OPERATION_ID",
                    "message": (
                        "operation_id must be "
                        "a positive integer."
                    ),
                },
            }), 400

        job = {
            "bridge_job_id": str(uuid4()),
            "work_order_id": work_order_id,
            "operation_id": operation_id,
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
