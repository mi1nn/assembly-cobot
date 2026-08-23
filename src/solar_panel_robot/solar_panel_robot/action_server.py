# ROS 연결 확인을 위한 Mock data를 보내주는 실험용 노드입니다.
import os
import json
import time

import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.node import Node

from solar_panel_interface.action import ExecuteOperation

# 실패 테스트용 변수 설정 - 노드 실행 전 환경변수 설정(실패할 번호 입력)
mock_fail_operation_id = os.getenv(
    "MOCK_FAIL_OPERATION_ID",
    "",
).strip()

MOCK_FAIL_OPERATION_ID = (
    int(mock_fail_operation_id)
    if mock_fail_operation_id
    else None
)

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
        self.get_logger().info(
            "Goal received: "
            f"work_order_id="
            f"{goal_request.work_order_id}, "
            f"work_execution_id="
            f"{goal_request.work_execution_id}, "
            f"operation_id="
            f"{goal_request.operation_id}, "
            f"operation_execution_id="
            f"{goal_request.operation_execution_id}, "
            f"robot_id="
            f"{goal_request.robot_id}"
        )

        id_values = (
            goal_request.work_order_id,
            goal_request.work_execution_id,
            goal_request.operation_id,
            goal_request.operation_execution_id,
            goal_request.robot_id,
        )

        if any(value <= 0 for value in id_values):
            self.get_logger().warning(
                "Goal contains an invalid ID."
            )
            return GoalResponse.REJECT

        for parameter in goal_request.parameters:
            self.get_logger().info(
                "parameter: "
                f"{parameter.key}="
                f"{parameter.value}"
            )

        try:
            components = json.loads(
                goal_request.components
            )

        except (TypeError, ValueError):
            self.get_logger().warning(
                "components is not valid JSON."
            )
            return GoalResponse.REJECT

        if not isinstance(components, list):
            self.get_logger().warning(
                "components must decode "
                "to a list."
            )
            return GoalResponse.REJECT

        self.get_logger().info(
            f"components: {len(components)}개"
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
                feedback.operation_execution_id = (
                    request.operation_execution_id
                )

                feedback.status = (
                    ExecuteOperation.Feedback
                    .STATUS_CANCELLED
                )

                feedback.message = (
                    "Mock operation was cancelled."
                )

                goal_handle.publish_feedback(
                    feedback
                )

                goal_handle.canceled()

                result = ExecuteOperation.Result()
                result.success = False
                result.error_code = "CANCELED"
                result.message = "Operation was canceled"

                self.get_logger().info(
                    f"Operation {request.operation_id} canceled"
                )

                return result

            feedback.operation_execution_id = (
                request.operation_execution_id
            )

            feedback.status = (
                ExecuteOperation.Feedback
                .STATUS_RUNNING
            )

            feedback.message = (
                "Mock operation is running."
            )

            goal_handle.publish_feedback(
                feedback
            )

            self.get_logger().info(
                f"Operation {request.operation_id}: {progress}%"
            )

            if (
                MOCK_FAIL_OPERATION_ID
                and request.operation_id
                == MOCK_FAIL_OPERATION_ID
                and progress >= 60
            ):
                feedback.operation_execution_id = (
                    request.operation_execution_id
                )

                feedback.status = (
                    ExecuteOperation.Feedback
                    .STATUS_FAILED
                )

                feedback.message = (
                    "Mock operation failure."
                )

                goal_handle.publish_feedback(
                    feedback
                )

                goal_handle.abort()

                result = ExecuteOperation.Result()
                result.success = False
                result.error_code = (
                    "MOCK_OPERATION_FAILURE"
                )
                result.message = (
                    "Mock failure requested for "
                    f"operation {request.operation_id}"
                )

                self.get_logger().error(
                    result.message
                )

                return result

            time.sleep(1.0)

        feedback.operation_execution_id = (
            request.operation_execution_id
        )

        feedback.status = (
            ExecuteOperation.Feedback
            .STATUS_COMPLETED
        )

        feedback.message = (
            "Mock operation completed."
        )

        goal_handle.publish_feedback(
            feedback
        )

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
