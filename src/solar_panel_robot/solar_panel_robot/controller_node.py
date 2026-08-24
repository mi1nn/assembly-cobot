import json
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


# =============================================================
# Robot 기본 설정
# =============================================================

ROBOT_ID = "dsr01"
ROBOT_MODEL = "m0609"


OPERATION_ID_MAP = {
    "1": "FRAME_PICK",
    "2": "FRAME_PLACE",
    "3": "FRAME_INSTALL",
    "4": "PIN_PICK",
    "5": "PIN_PLACE",
    "6": "PIN_INSERT",
    "7": "PIN_INSTALL",
    "8": "SOLAR_FULL",
}


# =============================================================
# Bridge 기준 Action 이름
#
# ros2_bridge_node.py:
#
# ActionClient(
#     self,
#     ExecuteOperation,
#     "execute_operation",
# )
#
# Bridge Node에는 namespace가 없으므로 실제 Action:
#
# /execute_operation
#
# 따라서 Controller도 절대 이름으로 맞춤.
# =============================================================

ACTION_NAME = "/execute_operation"


# =============================================================
# Controller가 실행 가능한 Operation Code
# =============================================================

SUPPORTED_OPERATION_CODES = {
    "FRAME_PICK",
    "FRAME_PLACE",
    "FRAME_INSTALL",
    "PIN_PICK",
    "PIN_PLACE",
    "PIN_INSERT",
    "PIN_INSTALL",
    "SOLAR_FULL",
}


# =============================================================
# DB Operation ID -> Robot Operation Code
#
# Bridge는 DB의 operation_id를 숫자로 받고,
# Controller에는 문자열로 전달함.
#
# 예:
#
# Backend:
# operation_id = 12
#
# Bridge:
# goal.operation_id = "12"
#
#
# 실제 DB ID가 확정되면 아래에 등록 가능.
#
# 예:
#
# OPERATION_ID_MAP = {
#     "12": "FRAME_PICK",
#     "13": "FRAME_PLACE",
# }
#
#
# 현재는 임의의 DB ID를 만들지 않기 위해 비워둠.
#
# 대신 Backend가 parameters에:
#
# {
#     "operation_code": "FRAME_PICK"
# }
#
# 를 넣으면 이 Mapping 없이도 실행 가능.
# =============================================================

OPERATION_ID_MAP = {}


class SolarPanelControllerNode(Node):

    def __init__(self):

        super().__init__(
            "solar_robot_controller",
            namespace=ROBOT_ID,
        )

        # =====================================================
        # Components
        # =====================================================

        self.robot = None
        self.solar = None

        # =====================================================
        # Controller 상태
        # =====================================================

        self.current_status = "STARTING"

        # Operation 중복 실행 방지
        self.operation_running = False
        self.operation_lock = threading.Lock()

        # =====================================================
        # Callback Groups
        #
        # Action과 Status Timer 분리
        # =====================================================

        self.action_callback_group = ReentrantCallbackGroup()

        self.status_callback_group = ReentrantCallbackGroup()

        # =====================================================
        # Status Publisher
        #
        # Node namespace가 /dsr01 이므로:
        #
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
            callback_group=self.status_callback_group,
        )

        # =====================================================
        # ExecuteOperation Action Server
        #
        # Bridge와 동일한:
        #
        # /execute_operation
        # =====================================================

        self.action_server = ActionServer(
            self,
            ExecuteOperation,
            ACTION_NAME,
            execute_callback=self.execute_callback,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback,
            callback_group=self.action_callback_group,
        )

        self.get_logger().info(
            "Solar Panel Controller Node 생성 완료"
        )

        self.get_logger().info(
            f"ExecuteOperation Action Server: {ACTION_NAME}"
        )

        self.set_status(
            "STARTING"
        )


    # =========================================================
    # 상태 변경
    # =========================================================

    def set_status(
        self,
        status,
    ):

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

        self.status_publisher.publish(
            msg
        )


    # =========================================================
    # Robot / Motion 준비
    # =========================================================

    def setup_components(self):

        # 중요:
        #
        # DR_init.__dsr__node 설정 이후 호출되어야 함.
        #
        # DSR_ROBOT2를 사용하는 모듈은
        # 이 시점 이후 import.

        from .robot_controller import RobotController
        from .solar_motion import SolarMotion

        # =====================================================
        # Robot 초기화
        # =====================================================

        self.set_status(
            "INITIALIZING"
        )

        self.robot = RobotController(
            self
        )

        # Manual
        # Tool
        # TCP
        # Auto
        self.robot.initialize()

        # =====================================================
        # SolarMotion 생성
        # =====================================================

        self.solar = SolarMotion(
            self
        )

        # =====================================================
        # 초기 동작
        #
        # Controller가 READY 상태가 되기 전에:
        # 1. Gripper Open
        # 2. Home 이동
        #
        # 을 수행하여 초기 상태를 일정하게 맞춘다.
        # =====================================================

        self.get_logger().info(
            "초기 Gripper Open"
        )

        self.solar.motion.release()

        self.get_logger().info(
            "초기 Home 이동"
        )

        self.solar.motion.move_home()

        self.get_logger().info(
            "초기 자세 설정 완료"
        )

        self.get_logger().info(
            "Robot 및 Solar Motion 준비 완료"
        )

        self.set_status(
            "READY"
        )


    # =========================================================
    # Bridge Parameter[] -> Python dict
    #
    # Bridge에서는:
    #
    # 문자열:
    #   그대로 Parameter.value
    #
    # 숫자 / list / dict / bool:
    #   json.dumps() 후 Parameter.value
    #
    # 따라서 Controller에서는 가능한 경우
    # json.loads()로 원래 타입 복원.
    # =========================================================

    def parse_parameters(
        self,
        parameters,
    ):

        parsed = {}

        for parameter in parameters:

            key = str(
                parameter.key
            )

            raw_value = parameter.value

            try:

                value = json.loads(
                    raw_value
                )

            except (
                json.JSONDecodeError,
                TypeError,
            ):

                # 일반 문자열
                value = raw_value

            parsed[key] = value

        return parsed


    # =========================================================
    # Bridge components JSON 문자열 -> Python list
    # =========================================================

    def parse_components(
        self,
        components_raw,
    ):

        if components_raw is None:

            return []

        if components_raw == "":

            return []

        try:

            components = json.loads(
                components_raw
            )

        except (
            json.JSONDecodeError,
            TypeError,
        ) as e:

            raise ValueError(
                f"components JSON 파싱 실패: {e}"
            ) from e

        if not isinstance(
            components,
            list,
        ):

            raise ValueError(
                "components는 JSON array여야 합니다."
            )

        return components


    # =========================================================
    # DB Operation ID -> Robot Operation Code 결정
    #
    # 우선순위:
    #
    # 1. operation_id 자체가 FRAME_PICK 등의 Code
    #    -> 기존 CLI 테스트 호환
    #
    # 2. parameters["operation_code"]
    #    -> Bridge/Backend 권장 방식
    #
    # 3. OPERATION_ID_MAP
    #    -> DB ID가 고정된 경우 사용
    # =========================================================

    def resolve_operation_code(
        self,
        operation_id,
        parameters,
    ):

        operation_id = str(
            operation_id
        )

        # -----------------------------------------------------
        # 기존 직접 Action 테스트 호환
        #
        # operation_id="FRAME_PICK"
        # -----------------------------------------------------

        if (
            operation_id
            in SUPPORTED_OPERATION_CODES
        ):

            return operation_id

        # -----------------------------------------------------
        # Bridge Parameters에서 operation_code 확인
        # -----------------------------------------------------

        operation_code = parameters.get(
            "operation_code"
        )

        if operation_code is not None:

            operation_code = str(
                operation_code
            ).strip()

            if (
                operation_code
                in SUPPORTED_OPERATION_CODES
            ):

                return operation_code

            raise ValueError(
                "지원하지 않는 operation_code: "
                f"{operation_code}"
            )

        # -----------------------------------------------------
        # DB Operation ID Mapping
        # -----------------------------------------------------

        mapped_code = OPERATION_ID_MAP.get(
            operation_id
        )

        if mapped_code is not None:

            if (
                mapped_code
                not in SUPPORTED_OPERATION_CODES
            ):

                raise ValueError(
                    "OPERATION_ID_MAP에 잘못된 "
                    f"Operation Code가 있습니다: "
                    f"{mapped_code}"
                )

            return mapped_code

        # -----------------------------------------------------
        # Mapping 불가능
        # -----------------------------------------------------

        raise ValueError(
            "DB operation_id를 Robot Operation으로 "
            f"변환할 수 없습니다. "
            f"operation_id={operation_id}. "
            "Backend parameters에 operation_code를 "
            "전달하거나 OPERATION_ID_MAP을 설정하세요."
        )


    # =========================================================
    # Action Goal 수락 여부
    # =========================================================

    def goal_callback(
        self,
        goal_request,
    ):

        self.get_logger().info(
            f"[IF-14] Goal 요청 수신 "
            f"work_order={goal_request.work_order_id}, "
            f"operation_id={goal_request.operation_id}"
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
        # ERROR 상태에서는 새 작업 거부
        # =====================================================

        if self.current_status == "ERROR":

            self.get_logger().warning(
                "Controller가 ERROR 상태입니다."
            )

            return GoalResponse.REJECT

        # =====================================================
        # Operation 중복 실행 방지
        # =====================================================

        with self.operation_lock:

            if self.operation_running:

                self.get_logger().warning(
                    "현재 다른 Operation이 실행 중입니다."
                )

                return GoalResponse.REJECT

            self.operation_running = True

        self.get_logger().info(
            "Action Goal 수락"
        )

        return GoalResponse.ACCEPT


    # =========================================================
    # Action Cancel
    # =========================================================

    def cancel_callback(
        self,
        goal_handle,
    ):

        self.get_logger().warning(
            "Operation Cancel 요청 수신"
        )

        # 현재 Robot Motion / Force Control을
        # 안전하게 중단시키는 로직이 없으므로 Cancel 거부.

        self.get_logger().warning(
            "현재 버전에서는 Operation Cancel을 지원하지 않습니다."
        )

        return CancelResponse.REJECT


    # =========================================================
    # IF-15 Feedback
    # =========================================================

    def publish_feedback(
        self,
        goal_handle,
        operation,
        status,
        progress,
    ):

        feedback = ExecuteOperation.Feedback()

        feedback.current_operation = str(
            operation
        )

        feedback.status = status

        feedback.progress = float(
            progress
        )

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
    # 실제 Robot Operation 실행
    # =========================================================

    def execute_operation(
        self,
        operation_code,
        parameters,
        components,
    ):

        if self.solar is None:

            raise RuntimeError(
                "SolarMotion이 준비되지 않았습니다."
            )

        # =====================================================
        # Frame Pick
        # =====================================================

        if operation_code == "FRAME_PICK":

            self.solar.pick_frame()

        # =====================================================
        # Frame Place
        # =====================================================

        elif operation_code == "FRAME_PLACE":

            self.solar.place_frame()

        # =====================================================
        # Frame 전체 설치
        # =====================================================

        elif operation_code == "FRAME_INSTALL":

            self.solar.install_frame()

        # =====================================================
        # Pin Pick
        # =====================================================

        elif operation_code == "PIN_PICK":

            self.solar.pick_pin()

        # =====================================================
        # Pin Force Place
        # =====================================================

        elif operation_code == "PIN_PLACE":

            self.solar.place_pin()

        # =====================================================
        # Pin 최종 삽입
        # =====================================================

        elif operation_code == "PIN_INSERT":

            self.solar.insert_pin()

        # =====================================================
        # 전체 Pin 설치
        # =====================================================

        elif operation_code == "PIN_INSTALL":

            self.solar.install_pin()

        # =====================================================
        # 전체 Solar 공정
        # =====================================================

        elif operation_code == "SOLAR_FULL":

            self.solar.run()

        # =====================================================
        # 정의되지 않은 Operation
        # =====================================================

        else:

            raise ValueError(
                "지원하지 않는 Operation Code: "
                f"{operation_code}"
            )

        # =====================================================
        # parameters / components
        #
        # 현재 SolarMotion에서는 아직 직접 사용하지 않음.
        #
        # 이후:
        #
        # pose
        # velocity
        # acceleration
        # force
        # stiffness
        # component
        #
        # 등을 SolarMotion에 전달할 수 있음.
        # =====================================================


    # =========================================================
    # Action 실행
    # =========================================================

    def execute_callback(
        self,
        goal_handle,
    ):

        request = goal_handle.request

        # =====================================================
        # Bridge에서 받은 원본 값
        # =====================================================

        work_order_id = request.work_order_id

        # 이 값은 DB의 Operation ID
        operation_id = request.operation_id

        # Parameter[] -> dict
        parameters = self.parse_parameters(
            request.parameters
        )

        # =====================================================
        # components
        #
        # Bridge 기준 ExecuteOperation.action에
        # components 필드가 존재해야 함.
        # =====================================================

        components_raw = getattr(
            request,
            "components",
            "",
        )

        components = self.parse_components(
            components_raw
        )

        result = ExecuteOperation.Result()

        try:

            # =================================================
            # Robot Operation Code 결정
            # =================================================

            operation_code = (
                self.resolve_operation_code(
                    operation_id,
                    parameters,
                )
            )

            # =================================================
            # 로그
            # =================================================

            self.get_logger().info(
                "========== OPERATION START =========="
            )

            self.get_logger().info(
                f"Work Order ID       : "
                f"{work_order_id}"
            )

            self.get_logger().info(
                f"DB Operation ID     : "
                f"{operation_id}"
            )

            self.get_logger().info(
                f"Robot Operation Code: "
                f"{operation_code}"
            )

            self.get_logger().info(
                f"Parameter 개수      : "
                f"{len(parameters)}"
            )

            self.get_logger().info(
                f"Component 개수      : "
                f"{len(components)}"
            )

            # =================================================
            # RUNNING
            # =================================================

            self.set_status(
                "RUNNING"
            )

            self.publish_feedback(
                goal_handle,
                operation_code,
                "RUNNING",
                0.0,
            )

            # =================================================
            # 실제 Robot 동작
            # =================================================

            self.execute_operation(
                operation_code,
                parameters,
                components,
            )

            # =================================================
            # DONE Feedback
            # =================================================

            self.publish_feedback(
                goal_handle,
                operation_code,
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
                f"{operation_code} "
                "completed successfully"
            )

            self.get_logger().info(
                "========== OPERATION COMPLETE =========="
            )

            # =================================================
            # 다음 작업 대기
            # =================================================

            self.set_status(
                "READY"
            )

            return result


        except Exception as e:

            # =================================================
            # Operation 실패
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
                        "Force 해제 오류: "
                        f"{force_error}"
                    )

            # =================================================
            # ERROR Feedback
            # =================================================

            try:

                self.publish_feedback(
                    goal_handle,
                    str(operation_id),
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

            result.error_code = (
                "OPERATION_FAILED"
            )

            result.message = str(
                e
            )

            self.set_status(
                "ERROR"
            )

            return result


        finally:

            # =================================================
            # 다음 Goal 허용
            # =================================================

            with self.operation_lock:

                self.operation_running = False

            self.get_logger().info(
                "[DEBUG] operation_running = False"
            )


    # =========================================================
    # Node 종료
    # =========================================================

    def destroy_node(self):

        if self.action_server is not None:

            self.action_server.destroy()

        super().destroy_node()


# =============================================================
# MAIN
# =============================================================

def main(args=None):

    # =========================================================
    # ROS2 초기화
    # =========================================================

    rclpy.init(
        args=args
    )

    # =========================================================
    # Doosan 설정
    # =========================================================

    DR_init.__dsr__id = ROBOT_ID
    DR_init.__dsr__model = ROBOT_MODEL

    # =========================================================
    # Controller Node
    #
    # Action Server
    # Status Publisher
    # Status Timer
    # =========================================================

    controller_node = (
        SolarPanelControllerNode()
    )

    # =========================================================
    # DSR_ROBOT2 전용 Node
    #
    # Controller Action/Timer Node와 분리
    # =========================================================

    dsr_node = rclpy.create_node(
        "solar_robot_dsr_client",
        namespace=ROBOT_ID,
    )

    # DSR_ROBOT2에서 사용할 Node
    DR_init.__dsr__node = dsr_node

    executor = None

    try:

        # =====================================================
        # Robot / SolarMotion 초기화
        #
        # DR_init.__dsr__node 설정 이후 실행
        # =====================================================

        controller_node.setup_components()

        # =====================================================
        # Controller Executor
        # =====================================================

        executor = MultiThreadedExecutor(
            num_threads=2
        )

        executor.add_node(
            controller_node
        )

        controller_node.get_logger().info(
            "Controller Action Server 대기 중"
        )

        controller_node.get_logger().info(
            f"Action: {ACTION_NAME}"
        )

        controller_node.get_logger().info(
            "Controller Node / "
            "DSR Client Node 분리 완료"
        )

        executor.spin()


    except KeyboardInterrupt:

        controller_node.get_logger().info(
            "사용자에 의해 종료되었습니다."
        )


    except Exception as e:

        controller_node.get_logger().error(
            f"Controller 프로그램 오류: {e}"
        )

        controller_node.set_status(
            "ERROR"
        )


    finally:

        # =====================================================
        # Executor 종료
        # =====================================================

        if executor is not None:

            executor.shutdown()

        # =====================================================
        # Node 종료
        # =====================================================

        controller_node.destroy_node()

        dsr_node.destroy_node()

        # =====================================================
        # ROS2 종료
        # =====================================================

        if rclpy.ok():

            rclpy.shutdown()


if __name__ == "__main__":

    main()