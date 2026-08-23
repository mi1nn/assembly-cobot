# ROS 연결 확인을 위한 Mock data를 보내주는 실험용 노드입니다.

import time

import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.node import Node

from solar_panel_interface.action import ExecuteOperation


class ExecuteOperationServer(Node):

    def __init__(self):
        super().__init__("execute_operation_server")

        self._action_server = ActionServer(
            self,
            ExecuteOperation,
            "execute_operation",
            execute_callback=self.execute_callback,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback,
        )

        self.get_logger().info(
            "ExecuteOperation Mock Action Server started"
        )

    def goal_callback(self, goal_request):
        """새로운 작업 요청을 받을 때 실행됩니다."""

        self.get_logger().info(
            "Goal received: "
            f"work_order_id={goal_request.work_order_id}, "
            f"operation_id={goal_request.operation_id}"
        )

        for parameter in goal_request.parameters:
            self.get_logger().info(
                f"parameter: {parameter.key}={parameter.value}"
            )

        return GoalResponse.ACCEPT

    def cancel_callback(self, goal_handle):
        """Action Client가 취소를 요청할 때 실행됩니다."""

        self.get_logger().info("Cancel request received")

        return CancelResponse.ACCEPT

    def execute_callback(self, goal_handle):
        """Goal이 승인된 후 실제 작업을 수행합니다."""

        request = goal_handle.request
        feedback = ExecuteOperation.Feedback()

        self.get_logger().info(
            f"Executing operation {request.operation_id}"
        )

        # 실제 로봇 동작을 대신하는 Mock 진행 과정
        for progress in range(0, 101, 20):

            if goal_handle.is_cancel_requested:
                goal_handle.canceled()

                result = ExecuteOperation.Result()
                result.success = False
                result.error_code = "CANCELED"
                result.message = "Operation was canceled"

                self.get_logger().info(
                    f"Operation {request.operation_id} canceled"
                )

                return result

            feedback.current_operation = request.operation_id
            feedback.status = "RUNNING"
            feedback.progress = float(progress)

            goal_handle.publish_feedback(feedback)

            self.get_logger().info(
                f"Operation {request.operation_id}: {progress}%"
            )

            time.sleep(1.0)

        goal_handle.succeed()

        result = ExecuteOperation.Result()
        result.success = True
        result.error_code = ""
        result.message = "Operation completed successfully"

        self.get_logger().info(
            f"Operation {request.operation_id} completed"
        )

        return result


def main(args=None):
    rclpy.init(args=args)

    node = ExecuteOperationServer()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
