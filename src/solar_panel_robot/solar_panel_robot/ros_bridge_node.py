import rclpy

from rclpy.node import Node
from rclpy.action import ActionClient

from solar_panel_interface.action import ExecuteOperation


class ROSBridgeNode(Node):

    def __init__(self):
        super().__init__("ros_bridge")

        # =====================================================
        # Action Client
        # ROS Bridge -> M0609 Controller
        # =====================================================

        self.action_client = ActionClient(
            self,
            ExecuteOperation,
            "/dsr01/execute_operation",
        )

        self.current_work_order_id = None
        self.current_operation_id = None

        self.goal_handle = None

        # 현재 Controller가 작업 중인지 여부
        self.is_running = False

        self.get_logger().info(
            "ROS Bridge Node ready"
        )


    def execute_operation(
        self,
        work_order_id,
        operation_id,
        parameters=None,
    ):

        if self.is_running:

            self.get_logger().warning(
                "현재 실행 중인 Operation이 있습니다."
            )

            return

        if parameters is None:
            parameters = []

        self.current_work_order_id = work_order_id
        self.current_operation_id = operation_id

        self.get_logger().info(
            f"Operation 실행 준비 "
            f"work_order={work_order_id}, "
            f"operation={operation_id}"
        )

        self.send_goal(
            work_order_id,
            operation_id,
            parameters,
        )


    # =========================================================
    # IF-14
    # ROS Bridge -> Controller
    #
    # string work_order_id
    # string operation_id
    # Parameter[] parameters
    # =========================================================

    def send_goal(
        self,
        work_order_id,
        operation_id,
        parameters,
    ):

        # Controller Action Server 확인
        self.get_logger().info(
            "Controller Action Server 연결 확인 중..."
        )

        if not self.action_client.wait_for_server(
            timeout_sec=5.0
        ):

            self.get_logger().error(
                "Controller Action Server를 찾을 수 없습니다."
            )

            self.reset_operation()

            return

        # Goal 생성
        goal_msg = ExecuteOperation.Goal()

        goal_msg.work_order_id = work_order_id
        goal_msg.operation_id = operation_id
        goal_msg.parameters = parameters

        self.get_logger().info(
            f"[IF-14] Goal 전송 "
            f"work_order={work_order_id}, "
            f"operation={operation_id}"
        )

        self.is_running = True

        # 비동기로 Goal 전송
        send_goal_future = (
            self.action_client.send_goal_async(
                goal_msg,
                feedback_callback=self.feedback_callback,
            )
        )

        send_goal_future.add_done_callback(
            self.goal_response_callback
        )


    # =========================================================
    # Goal 수락 여부 확인
    # =========================================================

    def goal_response_callback(
        self,
        future,
    ):

        try:

            goal_handle = future.result()

        except Exception as e:

            self.get_logger().error(
                f"Goal 전송 중 오류: {e}"
            )

            self.reset_operation()

            return

        if not goal_handle.accepted:

            self.get_logger().error(
                f"Controller가 Goal을 거부했습니다. "
                f"operation={self.current_operation_id}"
            )

            self.reset_operation()

            return

        self.goal_handle = goal_handle

        self.get_logger().info(
            f"Controller가 Goal을 수락했습니다. "
            f"operation={self.current_operation_id}"
        )

        # Result 대기
        result_future = (
            goal_handle.get_result_async()
        )

        result_future.add_done_callback(
            self.result_callback
        )


    # =========================================================
    # IF-15
    # Controller -> ROS Bridge Feedback
    #
    # string current_operation
    # string status
    # float32 progress
    # =========================================================

    def feedback_callback(
        self,
        feedback_msg,
    ):

        feedback = feedback_msg.feedback

        current_operation = (
            feedback.current_operation
        )

        status = feedback.status
        progress = feedback.progress

        self.get_logger().info(
            f"[IF-15] "
            f"operation={current_operation}, "
            f"status={status}, "
            f"progress={progress:.1f}%"
        )

        # =====================================================
        # 추후 DB 연결 시
        #
        # self.db.update_operation_progress(
        #     self.current_work_order_id,
        #     current_operation,
        #     status,
        #     progress,
        # )
        #
        # 형태로 추가
        # =====================================================


    # =========================================================
    # IF-16
    # Controller -> ROS Bridge Result
    #
    # bool success
    # string error_code
    # string message
    # =========================================================

    def result_callback(
        self,
        future,
    ):

        try:

            wrapped_result = future.result()
            result = wrapped_result.result

        except Exception as e:

            self.get_logger().error(
                f"Result 수신 중 오류: {e}"
            )

            self.reset_operation()

            return

        if result.success:

            self.get_logger().info(
                f"[IF-16] Operation 완료 "
                f"operation={self.current_operation_id}, "
                f"message={result.message}"
            )

            # ================================================
            # 추후 DB 연결
            #
            # self.db.update_operation_result(
            #     self.current_work_order_id,
            #     self.current_operation_id,
            #     status="DONE",
            #     error_code="",
            #     message=result.message,
            # )
            # ================================================

        else:

            self.get_logger().error(
                f"[IF-16] Operation 실패 "
                f"operation={self.current_operation_id}, "
                f"error_code={result.error_code}, "
                f"message={result.message}"
            )

            # ================================================
            # 추후 DB 연결
            #
            # self.db.update_operation_result(
            #     self.current_work_order_id,
            #     self.current_operation_id,
            #     status="ERROR",
            #     error_code=result.error_code,
            #     message=result.message,
            # )
            # ================================================

        self.reset_operation()


    # =========================================================
    # 현재 작업 정보 초기화
    # =========================================================

    def reset_operation(self):

        self.current_work_order_id = None
        self.current_operation_id = None

        self.goal_handle = None
        self.is_running = False


    # =========================================================
    # Action Cancel
    # =========================================================

    def cancel_current_operation(self):

        if self.goal_handle is None:

            self.get_logger().warning(
                "취소할 Operation이 없습니다."
            )

            return

        self.get_logger().info(
            f"Operation 취소 요청 "
            f"operation={self.current_operation_id}"
        )

        cancel_future = (
            self.goal_handle.cancel_goal_async()
        )

        cancel_future.add_done_callback(
            self.cancel_callback
        )


    # =========================================================
    # Cancel 결과
    # =========================================================

    def cancel_callback(
        self,
        future,
    ):

        try:

            cancel_response = future.result()

        except Exception as e:

            self.get_logger().error(
                f"Operation 취소 중 오류: {e}"
            )

            return

        if len(cancel_response.goals_canceling) > 0:

            self.get_logger().info(
                "Operation 취소 요청이 수락되었습니다."
            )

        else:

            self.get_logger().warning(
                "Operation 취소 요청이 거부되었습니다."
            )


def main(args=None):

    rclpy.init(args=args)

    node = ROSBridgeNode()

    try:

        rclpy.spin(node)

    except KeyboardInterrupt:

        pass

    finally:

        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()