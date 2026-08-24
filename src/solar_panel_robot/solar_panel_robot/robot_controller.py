import time
import rclpy
import DR_init

from dsr_msgs2.srv import (
    SetRobotMode,
    SetCurrentTool,
    SetCurrentTcp,
)

MANUAL_MODE = 0
AUTO_MODE = 1

TOOL_NAME = "ToolWeight"
TCP_NAME = "GripperDA_v1"

INIT_TIMEOUT = 3.0
INIT_MAX_RETRIES = 3


class RobotController:

    def __init__(self, node):
        self.node = node
        self.dsr_node = getattr(DR_init, "__dsr__node")

        self.robot_mode_client = self.dsr_node.create_client(
            SetRobotMode,
            "dsr_controller2/system/set_robot_mode",
        )
        self.tool_client = self.dsr_node.create_client(
            SetCurrentTool,
            "dsr_controller2/tool/set_current_tool",
        )
        self.tcp_client = self.dsr_node.create_client(
            SetCurrentTcp,
            "dsr_controller2/tcp/set_current_tcp",
        )

    def _call_with_retry(
        self,
        step_name,
        client,
        request_factory,
        timeout=INIT_TIMEOUT,
        max_retries=INIT_MAX_RETRIES,
        success_delay=0.0,
    ):
        last_error = "알 수 없는 오류"

        for attempt in range(1, max_retries + 1):
            self.node.get_logger().info(
                f"[INITIALIZE][{step_name}][{attempt}/{max_retries}] 시작"
            )

            deadline = time.monotonic() + timeout

            remaining = deadline - time.monotonic()
            if remaining <= 0 or not client.wait_for_service(timeout_sec=remaining):
                last_error = f"{timeout:.1f}초 이내 서비스 연결 실패"
                self.node.get_logger().warning(
                    f"[INITIALIZE][{step_name}][{attempt}/{max_retries}] "
                    f"{last_error}"
                )
                self.node.publish_system_event(
                    self.node.SEVERITY_WARNING,
                    "INITIALIZE_RETRY",
                    f"{step_name} {attempt}/{max_retries}: {last_error}",
                )
                continue

            try:
                request = request_factory()
                future = client.call_async(request)

                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    future.cancel()
                    raise TimeoutError(
                        f"{timeout:.1f}초 이내 응답 없음"
                    )

                rclpy.spin_until_future_complete(
                    self.dsr_node,
                    future,
                    timeout_sec=remaining,
                )

                if not future.done():
                    future.cancel()
                    raise TimeoutError(
                        f"{timeout:.1f}초 이내 응답 없음"
                    )

                result = future.result()

                if result is None:
                    raise RuntimeError("서비스 응답 없음")

                if not result.success:
                    raise RuntimeError("서비스가 success=False 반환")

                self.node.get_logger().info(
                    f"[INITIALIZE][{step_name}] 완료"
                )

                if success_delay > 0:
                    time.sleep(success_delay)

                return True

            except Exception as e:
                last_error = str(e)
                self.node.get_logger().warning(
                    f"[INITIALIZE][{step_name}][{attempt}/{max_retries}] "
                    f"실패: {last_error}"
                )
                self.node.publish_system_event(
                    self.node.SEVERITY_WARNING,
                    "INITIALIZE_RETRY",
                    f"{step_name} {attempt}/{max_retries}: {last_error}",
                )

        message = (
            f"Robot 초기화 실패 - {step_name}: "
            f"{max_retries}회 시도 모두 실패 "
            f"(마지막 오류: {last_error})"
        )

        self.node.get_logger().error(
            f"[INITIALIZE][FATAL] {message}"
        )
        self.node.publish_system_event(
            self.node.SEVERITY_CRITICAL,
            "INITIALIZE_FAILED",
            message,
        )
        raise RuntimeError(message)

    def initialize(self):
        self.node.get_logger().info(
            "========== ROBOT INITIALIZE START =========="
        )

        def manual_request():
            request = SetRobotMode.Request()
            request.robot_mode = MANUAL_MODE
            return request

        self._call_with_retry(
            "Manual Mode",
            self.robot_mode_client,
            manual_request,
            success_delay=0.5,
        )

        def tool_request():
            request = SetCurrentTool.Request()
            request.name = TOOL_NAME
            return request

        self._call_with_retry(
            f"Tool {TOOL_NAME}",
            self.tool_client,
            tool_request,
        )

        def tcp_request():
            request = SetCurrentTcp.Request()
            request.name = TCP_NAME
            return request

        self._call_with_retry(
            f"TCP {TCP_NAME}",
            self.tcp_client,
            tcp_request,
        )

        def auto_request():
            request = SetRobotMode.Request()
            request.robot_mode = AUTO_MODE
            return request

        self._call_with_retry(
            "Auto Mode",
            self.robot_mode_client,
            auto_request,
            success_delay=0.5,
        )

        self.node.get_logger().info(
            "========== ROBOT INITIALIZE COMPLETE =========="
        )