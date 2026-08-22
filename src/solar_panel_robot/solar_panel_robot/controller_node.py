import threading

import rclpy
from rclpy.node import Node

from rclpy.action import (
    ActionServer,
    GoalResponse,
    CancelResponse,
)

from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup

from std_msgs.msg import String

from solar_panel_interface.action import ExecuteOperation

import DR_init


ROBOT_ID = "dsr01"
ROBOT_MODEL = "m0609"


class SolarPanelControllerNode(Node):

    def __init__(self):

        super().__init__(
            "solar_robot_controller",
            namespace=ROBOT_ID,
        )

        # =====================================================
        # Component
        # =====================================================

        self.robot = None
        self.solar = None

        # =====================================================
        # 현재 상태
        # =====================================================

        self.current_status = "STARTING"

        # Operation 중복 실행 방지
        self.operation_running = False
        self.operation_lock = threading.Lock()

        # =====================================================
        # Callback Group
        #
        # Action 실행 중에도 Timer 등의 Callback을
        # 다른 Thread에서 처리할 수 있도록 설정
        # =====================================================

        self.callback_group = ReentrantCallbackGroup()

        # =====================================================
        # Status Publisher
        #
        # Topic:
        # /dsr01/status
        # =====================================================

        self.status_publisher = self.create_publisher(
            String,
            "status",
            10,
        )

        # =====================================================
        # Status Timer
        #
        # 현재 Controller 상태를 1초마다 Publish
        # =====================================================

        self.status_timer = self.create_timer(
            1.0,
            self.publish_current_status,
            callback_group=self.callback_group,
        )

        # =====================================================
        # ExecuteOperation Action Server
        #
        # Action:
        # /dsr01/execute_operation
        # =====================================================

        self.action_server = ActionServer(
            self,
            ExecuteOperation,
            "execute_operation",
            execute_callback=self.execute_callback,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback,
            callback_group=self.callback_group,
        )

        self.get_logger().info(
            "Solar Panel Controller Node 생성 완료"
        )

        self.set_status("STARTING")


    # =========================================================
    # 상태 변경
    # =========================================================

    def set_status(self, status):

        self.current_status = status

        self.get_logger().info(
            f"[STATUS] {status}"
        )

        # 상태 변경 즉시 Publish
        self.publish_current_status()


    # =========================================================
    # 현재 상태 Publish
    # =========================================================

    def publish_current_status(self):

        msg = String()
        msg.data = self.current_status

        self.status_publisher.publish(msg)


    # =========================================================
    # Robot / Motion 준비
    # =========================================================

    def setup_components(self):

        # DR_init 설정 이후 import
        from .robot_controller import RobotController
        from .solar_motion import SolarMotion

        # =====================================================
        # Robot 초기화 시작
        # =====================================================

        self.set_status(
            "INITIALIZING"
        )

        # =====================================================
        # Robot Controller 생성
        # =====================================================

        self.robot = RobotController(
            self
        )

        # Manual
        # Tool
        # TCP
        # Auto
        self.robot.initialize()

        # =====================================================
        # Solar Motion 생성
        # =====================================================

        self.solar = SolarMotion(
            self
        )

        self.get_logger().info(
            "Robot 및 Solar Motion 준비 완료"
        )

        # =====================================================
        # 작업 준비 완료
        # =====================================================

        self.set_status(
            "READY"
        )


    # =========================================================
    # Action Goal 수락 여부
    # =========================================================

    def goal_callback(self, goal_request):

        self.get_logger().info(
            f"[IF-14] Goal 요청 수신 "
            f"work_order={goal_request.work_order_id}, "
            f"operation={goal_request.operation_id}"
        )

        # =====================================================
        # SolarMotion 준비 확인
        # =====================================================

        if self.solar is None:

            self.get_logger().warning(
                "Controller가 아직 준비되지 않았습니다."
            )

            return GoalResponse.REJECT

        # =====================================================
        # ERROR 상태에서는 새로운 작업 거부
        # =====================================================

        if self.current_status == "ERROR":

            self.get_logger().warning(
                "Controller가 ERROR 상태입니다."
            )

            return GoalResponse.REJECT

        # =====================================================
        # 이미 다른 Operation 실행 중
        # =====================================================

        with self.operation_lock:

            if self.operation_running:

                self.get_logger().warning(
                    "현재 다른 Operation이 실행 중입니다."
                )

                return GoalResponse.REJECT

            # Goal을 수락하는 시점부터 Busy 처리
            self.operation_running = True

        self.get_logger().info(
            "Action Goal 수락"
        )

        return GoalResponse.ACCEPT


    # =========================================================
    # Action Cancel 요청
    # =========================================================

    def cancel_callback(self, goal_handle):

        self.get_logger().warning(
            "Operation Cancel 요청 수신"
        )

        # 현재 SolarMotion은
        # 동작 중 안전하게 정지시키는 기능이 없음.
        #
        # Force Control이나 로봇 이동 중 임의로
        # Cancel하면 위험할 수 있으므로 현재는 거부.
        #
        # 추후 안전 정지 기능 구현 후
        # CancelResponse.ACCEPT로 변경 가능.

        self.get_logger().warning(
            "현재 버전에서는 Operation Cancel을 지원하지 않습니다."
        )

        return CancelResponse.REJECT


    # =========================================================
    # IF-15
    # Controller -> Work Manager
    # Feedback 전송
    # =========================================================

    def publish_feedback(
        self,
        goal_handle,
        operation,
        status,
        progress,
    ):

        feedback = ExecuteOperation.Feedback()

        feedback.current_operation = operation
        feedback.status = status
        feedback.progress = float(progress)

        goal_handle.publish_feedback(
            feedback
        )

        self.get_logger().info(
            f"[IF-15] "
            f"operation={operation}, "
            f"status={status}, "
            f"progress={progress:.1f}%"
        )


    # =========================================================
    # Operation 실행 분기
    # =========================================================

    def execute_operation(
        self,
        operation_id,
        parameters,
    ):

        if self.solar is None:

            raise RuntimeError(
                "SolarMotion이 준비되지 않았습니다."
            )

        # =====================================================
        # Pin Pick
        # =====================================================

        if operation_id == "PIN_PICK":

            self.solar.pick_pin()

        # =====================================================
        # Lock Pin 1차 삽입
        # =====================================================

        elif operation_id == "PIN_INSERT_1":

            self.solar.first_insert_pin()

        # =====================================================
        # Lock Pin 최종 삽입
        # =====================================================

        elif operation_id == "PIN_INSERT_FINAL":

            self.solar.final_insert_pin()

        # =====================================================
        # 전체 Lock Pin 공정
        #
        # pick_pin()
        #     ↓
        # first_insert_pin()
        #     ↓
        # final_insert_pin()
        # =====================================================

        elif operation_id == "PIN_INSERT":

            self.solar.insert_pin()

        # =====================================================
        # 전체 Solar 작업
        #
        # 현재 SolarMotion.run()에 구현된
        # 전체 작업 실행
        # =====================================================

        elif operation_id == "SOLAR_FULL":

            self.solar.run()

        # =====================================================
        # 정의되지 않은 Operation
        # =====================================================

        else:

            raise ValueError(
                f"지원하지 않는 Operation ID: "
                f"{operation_id}"
            )

        # =====================================================
        # Parameter[]
        # =====================================================
        #
        # 현재 단계에서는 parameters를 아직 사용하지 않음.
        #
        # 추후:
        #
        # DB
        #   ↓
        # Work Manager
        #   ↓
        # ExecuteOperation.parameters
        #   ↓
        # Controller
        #   ↓
        # SolarMotion
        #
        # 형태로 연결.
        #
        # 예:
        #
        # velocity
        # acceleration
        # stiffness
        # force
        # insertion_distance
        # pose
        #
        # 등을 parameters에서 읽어서
        # SolarMotion에 전달.


    # =========================================================
    # Action 실행
    #
    # IF-14 Goal
    # IF-15 Feedback
    # IF-16 Result
    # =========================================================

    def execute_callback(self, goal_handle):

        request = goal_handle.request

        work_order_id = request.work_order_id
        operation_id = request.operation_id
        parameters = request.parameters

        self.get_logger().info(
            "========== OPERATION START =========="
        )

        self.get_logger().info(
            f"Work Order ID : {work_order_id}"
        )

        self.get_logger().info(
            f"Operation ID  : {operation_id}"
        )

        self.get_logger().info(
            f"Parameter 개수 : {len(parameters)}"
        )

        result = ExecuteOperation.Result()

        try:

            # =================================================
            # Controller RUNNING
            # =================================================

            self.set_status(
                "RUNNING"
            )

            # =================================================
            # 시작 Feedback
            # =================================================

            self.publish_feedback(
                goal_handle,
                operation_id,
                "RUNNING",
                0.0,
            )

            # =================================================
            # 실제 Operation 실행
            # =================================================

            self.execute_operation(
                operation_id,
                parameters,
            )

            # =================================================
            # 완료 Feedback
            # =================================================

            self.publish_feedback(
                goal_handle,
                operation_id,
                "DONE",
                100.0,
            )

            # =================================================
            # Action 성공
            # =================================================

            goal_handle.succeed()

            result.success = True
            result.error_code = ""
            result.message = (
                f"{operation_id} completed successfully"
            )

            # =================================================
            # 다음 작업 대기
            # =================================================

            self.set_status(
                "READY"
            )

            self.get_logger().info(
                "========== OPERATION COMPLETE =========="
            )

            return result


        except Exception as e:

            # =================================================
            # Operation 오류
            # =================================================

            self.get_logger().error(
                f"Operation 실행 오류: {e}"
            )

            # =================================================
            # Force / Compliance 안전 해제
            # =================================================

            if self.solar is not None:

                try:

                    self.solar.force.all_off()

                except Exception as force_error:

                    self.get_logger().error(
                        f"Force 해제 오류: {force_error}"
                    )

            # =================================================
            # ERROR Feedback
            # =================================================

            try:

                self.publish_feedback(
                    goal_handle,
                    operation_id,
                    "ERROR",
                    0.0,
                )

            except Exception:

                pass

            # =================================================
            # Action 실패
            # =================================================

            goal_handle.abort()

            result.success = False
            result.error_code = "OPERATION_FAILED"
            result.message = str(e)

            self.set_status(
                "ERROR"
            )

            return result


        finally:

            # =================================================
            # Operation 실행 종료
            # =================================================

            with self.operation_lock:

                self.operation_running = False


    # =========================================================
    # Node 종료
    # =========================================================

    def destroy_node(self):

        if self.action_server is not None:

            self.action_server.destroy()

        super().destroy_node()


def main(args=None):

    # =========================================================
    # ROS2 초기화
    # =========================================================

    rclpy.init(
        args=args
    )

    # =========================================================
    # Doosan 기본 설정
    # =========================================================

    DR_init.__dsr__id = ROBOT_ID
    DR_init.__dsr__model = ROBOT_MODEL

    # =========================================================
    # Controller Node 생성
    # =========================================================

    node = SolarPanelControllerNode()

    # =========================================================
    # Doosan Node 등록
    #
    # DSR_ROBOT2 관련 객체 생성 전에 반드시 설정
    # =========================================================

    DR_init.__dsr__node = node

    executor = None

    try:

        # =====================================================
        # Robot / SolarMotion 초기화
        # =====================================================

        node.setup_components()

        # =====================================================
        # MultiThreadedExecutor
        #
        # Robot Operation이 실행 중이어도
        # Status Timer 등 다른 ROS Callback을
        # 처리할 수 있도록 여러 Thread 사용
        # =====================================================

        executor = MultiThreadedExecutor(
            num_threads=2
        )

        executor.add_node(
            node
        )

        node.get_logger().info(
            "Controller Action Server 대기 중"
        )

        executor.spin()


    except KeyboardInterrupt:

        node.get_logger().info(
            "사용자에 의해 종료되었습니다."
        )


    except Exception as e:

        node.get_logger().error(
            f"Controller 프로그램 오류: {e}"
        )

        node.set_status(
            "ERROR"
        )


    finally:

        if executor is not None:

            executor.shutdown()

        node.destroy_node()

        if rclpy.ok():

            rclpy.shutdown()


if __name__ == "__main__":

    main()