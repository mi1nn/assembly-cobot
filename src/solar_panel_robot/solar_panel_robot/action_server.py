# ROS 연결 확인을 위한 Mock data를 보내주는 실험용 노드입니다.
import os
import json
import time

import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.node import Node

from solar_panel_interface.action import ExecuteOperation

from threading import Lock

from rclpy.callback_groups import (
    MutuallyExclusiveCallbackGroup,
    ReentrantCallbackGroup,
)
from rclpy.executors import MultiThreadedExecutor

from solar_panel_interface.srv import (
    StopOperation,
    RecoverRobot,
)

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

mock_reject_operation_id = os.getenv(
    "MOCK_REJECT_OPERATION_ID",
    "",
).strip()

MOCK_REJECT_OPERATION_ID = (
    int(mock_reject_operation_id)
    if mock_reject_operation_id
    else None
)

class ExecuteOperationServer(Node):

    def __init__(self):
        super().__init__("execute_operation_server")

        self._operation_lock = Lock()
        self._active_goal_handle = None
        self._stop_requested = False
        self._robot_stopped = False

        self._action_callback_group = (
            ReentrantCallbackGroup()
        )

        self._stop_callback_group = (
            MutuallyExclusiveCallbackGroup()
        )

        self._action_server = ActionServer(
            self,
            ExecuteOperation,
            "execute_operation",
            execute_callback=self.execute_callback,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback,
            callback_group=(
                self._action_callback_group
            ),
        )

        self._stop_service = self.create_service(
            StopOperation,
            "stop_operation",
            self.stop_operation_callback,
            callback_group=self._stop_callback_group,
        )

        self._recover_service = self.create_service(
            RecoverRobot,
            "recover_robot",
            self.recover_robot_callback,
            callback_group=self._stop_callback_group,
        )

        self.get_logger().info(
            "ExecuteOperation Mock Action Server started"
        )

    def goal_callback(self, goal_request):

        with self._operation_lock:
            robot_stopped = self._robot_stopped

        if robot_stopped:
            self.get_logger().warning(
                "Goal rejected because the Mock "
                "robot requires recovery."
            )
            return GoalResponse.REJECT

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

        if (
            MOCK_REJECT_OPERATION_ID
            and goal_request.operation_id
            == MOCK_REJECT_OPERATION_ID
        ):
            self.get_logger().warning(
                "Mock Goal rejection requested: "
                f"operation_id="
                f"{goal_request.operation_id}"
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

    def stop_operation_callback(
        self,
        request,
        response,
    ):
        with self._operation_lock:
            goal_handle = self._active_goal_handle

            if goal_handle is None:
                response.accepted = False
                response.error_code = (
                    "OPERATION_NOT_ACTIVE"
                )
                response.message = (
                    "No Operation is currently active."
                )
                return response

            active_request = goal_handle.request

            id_matches = (
                request.work_execution_id
                == active_request.work_execution_id
                and request.operation_execution_id
                == active_request.operation_execution_id
                and request.robot_id
                == active_request.robot_id
            )

            if not id_matches:
                response.accepted = False
                response.error_code = (
                    "EXECUTION_MISMATCH"
                )
                response.message = (
                    "Stop request IDs do not match "
                    "the active Operation."
                )
                return response

            self._stop_requested = True
            self._robot_stopped = True

        self.get_logger().warning(
            "Mock robot stop requested: "
            f"work_execution_id="
            f"{request.work_execution_id}, "
            f"operation_execution_id="
            f"{request.operation_execution_id}"
        )

        response.accepted = True
        response.error_code = ""
        response.message = (
            "Mock robot motion stop accepted."
        )

        return response

    def recover_robot_callback(
        self,
        request,
        response,
    ):
        if request.robot_id <= 0:
            response.recovered = False
            response.error_code = (
                "INVALID_ROBOT_ID"
            )
            response.message = (
                "robot_id must be "
                "a positive integer."
            )
            return response

        with self._operation_lock:
            goal_handle = self._active_goal_handle
            if (
                goal_handle is not None
                and goal_handle.is_active
            ):
                response.recovered = False
                response.error_code = (
                    "OPERATION_ACTIVE"
                )
                response.message = (
                    "Robot cannot be recovered "
                    "while an Operation is active."
                )
                return response

            # terminal state인데 참조만 남은 경우 정리
            if goal_handle is not None:
                self._active_goal_handle = None
                self._stop_requested = False

            if not self._robot_stopped:
                response.recovered = True
                response.error_code = ""
                response.message = (
                    "Mock robot is already ready."
                )
                return response

            # 실제 Controller에서는 이 위치에서:
            # - 안전 정지 원인 확인
            # - Robot 오류 상태 해제
            # - Force/Compliance 해제 확인
            # - Servo/운전 가능 상태 확인
            self._robot_stopped = False
            self._stop_requested = False

        self.get_logger().info(
            "Mock robot recovery completed: "
            f"robot_id={request.robot_id}"
        )

        response.recovered = True
        response.error_code = ""
        response.message = (
            "Mock robot recovery completed."
        )

        return response

    def clear_active_goal(
        self,
        goal_handle,
    ) -> None:
        with self._operation_lock:
            if (
                self._active_goal_handle
                is goal_handle
            ):
                self._active_goal_handle = None
                self._stop_requested = False

    def execute_callback(self, goal_handle):
        """Goal이 승인된 후 실제 작업을 수행합니다."""

        request = goal_handle.request
        feedback = ExecuteOperation.Feedback()

        with self._operation_lock:
            self._active_goal_handle = goal_handle
            self._stop_requested = False

        self.get_logger().info(
            f"Executing operation {request.operation_id}"
        )

        # 실제 로봇 동작을 대신하는 Mock 진행 과정
        for progress in range(0, 101, 20):

            with self._operation_lock:
                stop_requested = self._stop_requested

            if (
                goal_handle.is_cancel_requested
                or stop_requested
            ):
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
                result.error_code = "MOCK_OPERATION_FAILURE"
                result.message = "Operation was cancelled"

                self.get_logger().info(
                    f"Operation {request.operation_id} cancelled"
                )

                self.clear_active_goal(goal_handle)

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

                self.clear_active_goal(goal_handle)

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

        self.clear_active_goal(goal_handle)

        return result


def main(args=None):
    rclpy.init(args=args)

    node = ExecuteOperationServer()

    executor = MultiThreadedExecutor(
        num_threads=2
    )
    executor.add_node(node)

    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
