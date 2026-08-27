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
from rclpy.callback_groups import (
    MutuallyExclusiveCallbackGroup,
    ReentrantCallbackGroup,
)

from std_msgs.msg import String

from solar_panel_interface.action import ExecuteOperation
from solar_panel_interface.msg import SystemEvent
from solar_panel_interface.srv import (
    StopOperation,
    RecoverRobot,
)

import DR_init


# =============================================================
# Robot 기본 설정
# =============================================================

ROBOT_ID = "dsr01"
ROBOT_MODEL = "m0609"




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

POST_OPERATION_CODES = {
    "post1",
    "post2",
    "post3",
    "post4",
    "post5",
    "post6",
}

# DB operation code와 별개로 직접 Action 테스트에 사용할 수 있는 코드.
SUPPORTED_OPERATION_CODES = POST_OPERATION_CODES | {
    "POST_PICK",
    "POST_PLACE",
<<<<<<< HEAD
    "PIN_PICK",
    "PIN_PLACE",
    "FRAME_PICK",
    "FRAME_PLACE",
    "PANEL_PICK",
    "PANEL_PLACE",
    "SNAPFIT_PICK",
    "SNAPFIT_PLACE",
=======
    "POST_PIN_PICK",
    "POST_PIN_PLACE",
>>>>>>> origin/feature
    "POST_INSTALL",
    "PANEL_PICK",
    "SOLAR_FULL",
}



class SolarPanelControllerNode(Node):

    SEVERITY_INFO = SystemEvent.SEVERITY_INFO
    SEVERITY_WARNING = SystemEvent.SEVERITY_WARNING
    SEVERITY_ERROR = SystemEvent.SEVERITY_ERROR
    SEVERITY_CRITICAL = SystemEvent.SEVERITY_CRITICAL

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
        self._active_goal_handle = None
        self._stop_requested = False
        self._robot_stopped = False

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

        self.service_callback_group = (
            MutuallyExclusiveCallbackGroup()
        )

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

        self.declare_parameter("robot_id", 1)
        self.backend_robot_id = int(
            self.get_parameter("robot_id").value
        )

        self.system_event_publisher = self.create_publisher(
            SystemEvent,
            "/system_event",
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

        # =====================================================
        # Service Server
        #
        # Bridge와 동일한:
        #
        # /execute_operation
        # =====================================================

        self._stop_service = self.create_service(
            StopOperation,
            "/stop_operation",
            self.stop_operation_callback,
            callback_group=self.service_callback_group,
        )

        self._recover_service = self.create_service(
            RecoverRobot,
            "/recover_robot",
            self.recover_robot_callback,
            callback_group=self.service_callback_group,
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


    def publish_system_event(
        self,
        severity,
        code,
        message,
        *,
        work_execution_id=0,
        operation_execution_id=0,
        operation_code="",
        phase="",
        status="",
        detail=None,
    ):
        """
        Controller -> /system_event 공통 이벤트 발행.

        Operation과 무관한 초기화/Bridge 상태 이벤트는
        기존처럼 severity/code/message만 넘겨도 된다.

        Operation 관련 이벤트는 work_execution_id,
        operation_execution_id, operation_code, phase, status를
        함께 전달한다. detail은 JSON object 형태로 보낸다.
        """
        if detail is None:
            detail_data = {}
        elif isinstance(detail, dict):
            detail_data = dict(detail)
        else:
            detail_data = {
                "value": detail,
            }

        operation_code = str(operation_code).strip()
        phase = str(phase).strip().upper()
        status = str(status).strip().upper()

        if operation_code:
            detail_data.setdefault(
                "operation_code",
                operation_code,
            )
        if phase:
            detail_data.setdefault(
                "phase",
                phase,
            )
        if status:
            detail_data.setdefault(
                "status",
                status,
            )

        msg = SystemEvent()
        msg.robot_id = int(self.backend_robot_id)
        msg.work_execution_id = int(
            work_execution_id or 0
        )
        msg.operation_execution_id = int(
            operation_execution_id or 0
        )
        msg.operation_code = operation_code
        msg.phase = phase
        msg.status = status
        msg.severity = int(severity)
        msg.code = str(code)
        msg.message = str(message)
        msg.detail = json.dumps(
            detail_data,
            ensure_ascii=False,
            separators=(",", ":"),
        )

        self.system_event_publisher.publish(msg)

        self.get_logger().info(
            f"[SYSTEM EVENT] "
            f"robot_id={msg.robot_id}, "
            f"work_execution_id={msg.work_execution_id}, "
            f"operation_execution_id="
            f"{msg.operation_execution_id}, "
            f"operation_code={msg.operation_code}, "
            f"phase={msg.phase}, "
            f"status={msg.status}, "
            f"severity={msg.severity}, "
            f"code={msg.code}, "
            f"message={msg.message}"
        )


    # =========================================================
    # Robot / Motion 준비
    # =========================================================

    def setup_components(self):
        from .robot_controller import RobotController
        from .solar_motion import SolarMotion

        self.set_status("INITIALIZING")

        self.robot = RobotController(self)
        self.robot.initialize()

        self.publish_system_event(
            self.SEVERITY_INFO,
            "ROBOT_INITIALIZED",
            "Robot 초기 설정이 완료되었습니다.",
        )

        self.solar = SolarMotion(self)

        try:
            self.get_logger().info("초기 Gripper Open")
            self.solar.motion.release()
        except Exception as e:
            self.get_logger().warning(
                f"초기 Gripper Open 실패 - 계속 진행: {e}"
            )
            self.publish_system_event(
                self.SEVERITY_WARNING,
                "INITIAL_GRIPPER_OPEN_FAILED",
                str(e),
            )

        try:
            self.get_logger().info("초기 Home 이동")
            self.solar.motion.move_home()
        except Exception as e:
            self.get_logger().warning(
                f"초기 Home 이동 실패 - 계속 진행: {e}"
            )
            self.publish_system_event(
                self.SEVERITY_WARNING,
                "INITIAL_HOME_FAILED",
                str(e),
            )

        self.get_logger().info("초기 자세 설정 완료")
        self.get_logger().info("Robot 및 Solar Motion 준비 완료")
        self.set_status("READY")

        self.publish_system_event(
            self.SEVERITY_INFO,
            "ROBOT_READY",
            "Robot controller is ready.",
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
    # DB Operation Code 검증
    #
    # operation_id는 DB 추적용, operation_code는 동작 선택용이다.
    # Backend -> Bridge -> ExecuteOperation.operation_code 경로로
    # DB의 operation.code(postA, postB, ...)를 그대로 전달한다.
    # =========================================================

    def resolve_operation_code(
        self,
        operation_code,
    ):
        operation_code = str(
            operation_code
        ).strip()

        if not operation_code:
            raise ValueError(
                "operation_code가 비어 있습니다."
            )

        if operation_code not in SUPPORTED_OPERATION_CODES:
            raise ValueError(
                "지원하지 않는 operation_code: "
                f"{operation_code}"
            )

        return operation_code


    # =========================================================
    # Action Goal 수락 여부
    # =========================================================

    def goal_callback(
        self,
        goal_request,
    ):

        self.get_logger().info(
            f"[IF-14] Goal 요청 수신 "
            f"work_order_id={goal_request.work_order_id}, "
            f"work_execution_id={goal_request.work_execution_id}, "
            f"operation_id={goal_request.operation_id}, "
            f"operation_code={goal_request.operation_code}, "
            f"operation_execution_id={goal_request.operation_execution_id}, "
            f"robot_id={goal_request.robot_id}"
        )

        if self.solar is None:
            self.get_logger().warning(
                "Controller가 아직 준비되지 않았습니다."
            )
            return GoalResponse.REJECT

        with self.operation_lock:
            robot_stopped = self._robot_stopped

        if robot_stopped:
            self.get_logger().warning(
                "Robot이 정지 상태이므로 복구가 필요합니다."
            )
            return GoalResponse.REJECT

        id_values = (
            goal_request.work_order_id,
            goal_request.work_execution_id,
            goal_request.operation_id,
            goal_request.operation_execution_id,
            goal_request.robot_id,
        )
        if any(value <= 0 for value in id_values):
            self.get_logger().warning(
                "Goal ID는 모두 양수여야 합니다."
            )
            return GoalResponse.REJECT

        try:
            self.parse_components(goal_request.components)
        except ValueError as error:
            self.get_logger().warning(str(error))
            return GoalResponse.REJECT

        if self.current_status == "ERROR":
            self.get_logger().warning(
                "Controller가 ERROR 상태입니다."
            )
            return GoalResponse.REJECT

        if int(goal_request.robot_id) != self.backend_robot_id:
            self.get_logger().warning(
                "Goal robot_id가 Controller robot_id와 다릅니다. "
                f"expected={self.backend_robot_id}, "
                f"received={goal_request.robot_id}"
            )
            return GoalResponse.REJECT

        try:
            self.resolve_operation_code(
                goal_request.operation_code
            )
        except ValueError as e:
            self.get_logger().warning(str(e))
            return GoalResponse.REJECT

        with self.operation_lock:
            if self.operation_running:
                self.get_logger().warning(
                    "현재 다른 Operation이 실행 중입니다."
                )
                return GoalResponse.REJECT

            self.operation_running = True

        self.get_logger().info("Action Goal 수락")
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

        with self.operation_lock:
            if self._active_goal_handle is not goal_handle:
                return CancelResponse.REJECT
            self._stop_requested = True

        try:
            if self.solar is None:
                raise RuntimeError("SolarMotion is not initialized.")
            self.solar.motion.stop_motion()
            self.solar.force.all_off()
        except Exception as error:
            self.get_logger().error(
                f"Action Cancel 중 Robot 정지 실패: {error}"
            )
            self.set_status("ERROR")
            return CancelResponse.REJECT

        with self.operation_lock:
            self._robot_stopped = True

        self.set_status("STOPPED")
        return CancelResponse.ACCEPT


    # =========================================================
    # IF-15 Feedback
    # =========================================================

    def publish_feedback(
        self,
        goal_handle,
        operation_execution_id,
        status,
        message,
    ):

        feedback = ExecuteOperation.Feedback()
        feedback.operation_execution_id = int(
            operation_execution_id
        )
        feedback.status = int(status)
        feedback.message = str(message)

        goal_handle.publish_feedback(feedback)

        self.get_logger().info(
            f"[IF-15] "
            f"operation_execution_id="
            f"{feedback.operation_execution_id}, "
            f"status={feedback.status}, "
            f"message={feedback.message}"
        )

    # =========================================================
    # Stop/Recover Service 실행
    # =========================================================

    def stop_operation_callback(self, request, response):
        with self.operation_lock:
            goal_handle = self._active_goal_handle

            if goal_handle is None or not goal_handle.is_active:
                response.accepted = False
                response.error_code = "OPERATION_NOT_ACTIVE"
                response.message = "No Operation is currently active."
                return response

            active_request = goal_handle.request
            if (
                request.work_execution_id
                != active_request.work_execution_id
                or request.operation_execution_id
                != active_request.operation_execution_id
                or request.robot_id != active_request.robot_id
            ):
                response.accepted = False
                response.error_code = "EXECUTION_MISMATCH"
                response.message = (
                    "Stop request IDs do not match the active Operation."
                )
                return response

            self._stop_requested = True

        try:
            if self.solar is None:
                raise RuntimeError("SolarMotion is not initialized.")
            self.solar.motion.stop_motion()
            self.solar.force.all_off()
        except Exception as error:
            self.set_status("ERROR")
            response.accepted = False
            response.error_code = "ROBOT_STOP_FAILED"
            response.message = str(error)
            return response

        with self.operation_lock:
            self._robot_stopped = True

        self.set_status("STOPPED")
        response.accepted = True
        response.error_code = ""
        response.message = "Robot motion stop accepted."
        return response

    def recover_robot_callback(self, request, response):
        if int(request.robot_id) != self.backend_robot_id:
            response.recovered = False
            response.error_code = "ROBOT_ID_MISMATCH"
            response.message = "robot_id does not match this Controller."
            return response

        with self.operation_lock:
            goal_handle = self._active_goal_handle
            if goal_handle is not None and goal_handle.is_active:
                response.recovered = False
                response.error_code = "OPERATION_ACTIVE"
                response.message = "An Operation is still active."
                return response

        try:
            if self.solar is None:
                raise RuntimeError("SolarMotion is not initialized.")
            self.solar.motion.restore_motion()
        except Exception as error:
            self.set_status("ERROR")
            response.recovered = False
            response.error_code = "ROBOT_RECOVERY_FAILED"
            response.message = str(error)
            return response

        with self.operation_lock:
            self._active_goal_handle = None
            self._stop_requested = False
            self._robot_stopped = False

        self.set_status("READY")
        response.recovered = True
        response.error_code = ""
        response.message = "Robot recovery completed."
        return response

    def complete_cancelled_operation(
        self,
        goal_handle,
        operation_context,
        message,
    ):
        operation_execution_id = operation_context[
            "operation_execution_id"
        ]
        operation_code = operation_context["operation_code"]

        self.publish_feedback(
            goal_handle,
            operation_execution_id,
            ExecuteOperation.Feedback.STATUS_CANCELLED,
            message,
        )

        if goal_handle.is_active:
            goal_handle.canceled()

        result = ExecuteOperation.Result()
        result.success = False
        result.error_code = "CANCELLED"
        result.message = message

        self.publish_system_event(
            self.SEVERITY_WARNING,
            "OPERATION_CANCELLED",
            f"[{operation_code}] {message}",
            work_execution_id=operation_context["work_execution_id"],
            operation_execution_id=operation_execution_id,
            operation_code=operation_code,
            phase="OPERATION",
            status="CANCELLED",
            detail={
                "work_order_id": operation_context["work_order_id"],
                "operation_id": operation_context["operation_id"],
                "success": False,
            },
        )
        self.set_status("STOPPED")
        return result

    # =========================================================
    # 실제 Robot Operation 실행
    # =========================================================

    def execute_operation(
        self,
        operation_code,
        parameters,
        components,
        operation_context,
    ):
        if self.solar is None:
            raise RuntimeError(
                "SolarMotion이 준비되지 않았습니다."
            )

        # DB Post 작업은 현재 포스트 삽입 검증 Cycle로 실행한다.
        # POST PICK -> POST PLACE -> MOTION STOP -> RELEASE
        # -> SAFE RETREAT -> HOME
        if operation_code in POST_OPERATION_CODES:
            return self.solar.install_post_cycle(
                parameters,
                components,
                operation_context=operation_context,
            )

        # 직접 Action 테스트용 세부 동작.
        if operation_code == "POST_PICK":
            return self.solar.pick_post(
                parameters,
                components,
                operation_context=operation_context,
            )

        if operation_code == "POST_PLACE":
            return self.solar.place_post(
                parameters,
                components,
                operation_context=operation_context,
            )

        if operation_code == "POST_PIN_PICK":
            return self.solar.pick_post_pin(
                parameters,
                components,
                operation_context=operation_context,
            )

        if operation_code == "POST_PIN_PLACE":
            return self.solar.place_post_pin(
                parameters,
                components,
                operation_context=operation_context,
            )

        # POST_INSTALL은 직접 테스트용 Post Cycle 별칭으로 유지한다.
        if operation_code == "POST_INSTALL":
            return self.solar.install_post_cycle(
                parameters,
                components,
                operation_context=operation_context,
            )

        # PANEL_PICK은 태양광 패널 Pick 단독 테스트용 Operation Code.
        # PANEL Pick만 수행하고 Place는 실행하지 않는다.
        if operation_code == "PANEL_PICK":
            return self.solar.pick_panel(
                parameters,
                components,
                operation_context=operation_context,
            )

        if operation_code == "SOLAR_FULL":
            return self.solar.run(
                parameters,
                components,
                operation_context=operation_context,
            )

        raise ValueError(
            "지원하지 않는 Operation Code: "
            f"{operation_code}"
        )


    # =========================================================
    # Action 실행
    # =========================================================

    def execute_callback(
        self,
        goal_handle,
    ):

        with self.operation_lock:
            self._active_goal_handle = goal_handle
            self._stop_requested = False

        request = goal_handle.request

        work_order_id = int(request.work_order_id)
        work_execution_id = int(request.work_execution_id)
        operation_id = int(request.operation_id)
        operation_code = self.resolve_operation_code(
            request.operation_code
        )
        operation_execution_id = int(
            request.operation_execution_id
        )
        robot_id = int(request.robot_id)

        parameters = self.parse_parameters(
            request.parameters
        )
        components = self.parse_components(
            request.components
        )

        operation_context = {
            "work_order_id": work_order_id,
            "work_execution_id": work_execution_id,
            "operation_id": operation_id,
            "operation_code": operation_code,
            "operation_execution_id": (
                operation_execution_id
            ),
            "robot_id": robot_id,
        }

        result = ExecuteOperation.Result()

        try:
            self.get_logger().info(
                "========== OPERATION START =========="
            )
            self.get_logger().info(
                f"Work Order ID          : {work_order_id}"
            )
            self.get_logger().info(
                f"Work Execution ID      : {work_execution_id}"
            )
            self.get_logger().info(
                f"DB Operation ID        : {operation_id}"
            )
            self.get_logger().info(
                "Operation Execution ID : "
                f"{operation_execution_id}"
            )
            self.get_logger().info(
                f"Robot ID               : {robot_id}"
            )
            self.get_logger().info(
                f"Robot Operation Code   : {operation_code}"
            )
            self.get_logger().info(
                f"Parameter 개수         : {len(parameters)}"
            )
            self.get_logger().info(
                f"Component 개수         : {len(components)}"
            )

            self.set_status("RUNNING")

            self.publish_system_event(
                self.SEVERITY_INFO,
                "OPERATION_STARTED",
                f"[{operation_code}] Operation started",
                work_execution_id=work_execution_id,
                operation_execution_id=(
                    operation_execution_id
                ),
                operation_code=operation_code,
                phase="OPERATION",
                status="STARTED",
                detail={
                    "work_order_id": work_order_id,
                    "operation_id": operation_id,
                },
            )

            self.publish_feedback(
                goal_handle,
                operation_execution_id,
                ExecuteOperation.Feedback.STATUS_RUNNING,
                f"{operation_code} started",
            )

            with self.operation_lock:
                stop_requested = self._stop_requested

            if goal_handle.is_cancel_requested or stop_requested:
                return self.complete_cancelled_operation(
                    goal_handle,
                    operation_context,
                    "Operation was cancelled before execution.",
                )

            self.execute_operation(
                operation_code,
                parameters,
                components,
                operation_context,
            )

            with self.operation_lock:
                stop_requested = self._stop_requested

            if goal_handle.is_cancel_requested or stop_requested:
                return self.complete_cancelled_operation(
                    goal_handle,
                    operation_context,
                    "Operation was cancelled.",
                )

            self.publish_feedback(
                goal_handle,
                operation_execution_id,
                ExecuteOperation.Feedback.STATUS_COMPLETED,
                f"{operation_code} completed successfully",
            )

            goal_handle.succeed()

            result.success = True
            result.error_code = ""
            result.message = (
                f"{operation_code} completed successfully"
            )

            self.get_logger().info(
                "========== OPERATION COMPLETE =========="
            )

            self.publish_system_event(
                self.SEVERITY_INFO,
                "OPERATION_COMPLETED",
                f"[{operation_code}] "
                "Operation completed successfully",
                work_execution_id=work_execution_id,
                operation_execution_id=(
                    operation_execution_id
                ),
                operation_code=operation_code,
                phase="OPERATION",
                status="COMPLETED",
                detail={
                    "work_order_id": work_order_id,
                    "operation_id": operation_id,
                    "success": True,
                },
            )

            self.set_status("READY")
            return result

        except Exception as e:
            error_message = str(e)

            with self.operation_lock:
                stop_requested = self._stop_requested

            if goal_handle.is_cancel_requested or stop_requested:
                return self.complete_cancelled_operation(
                    goal_handle,
                    operation_context,
                    error_message or "Operation was cancelled.",
                )

            self.get_logger().error(
                f"Operation 실행 오류: {error_message}"
            )

            if self.solar is not None:
                try:
                    self.solar.force.all_off()
                except Exception as force_error:
                    self.get_logger().error(
                        "Force 해제 오류: "
                        f"{force_error}"
                    )

            try:
                self.publish_feedback(
                    goal_handle,
                    operation_execution_id,
                    ExecuteOperation.Feedback.STATUS_FAILED,
                    error_message,
                )
            except Exception as feedback_error:
                self.get_logger().warning(
                    "실패 Feedback 전송 오류: "
                    f"{feedback_error}"
                )

            goal_handle.abort()

            result.success = False
            result.error_code = "OPERATION_FAILED"
            result.message = error_message

            self.publish_system_event(
                self.SEVERITY_ERROR,
                "OPERATION_FAILED",
                f"[{operation_code}] "
                f"Operation failed: {error_message}",
                work_execution_id=work_execution_id,
                operation_execution_id=(
                    operation_execution_id
                ),
                operation_code=operation_code,
                phase="OPERATION",
                status="FAILED",
                detail={
                    "work_order_id": work_order_id,
                    "operation_id": operation_id,
                    "success": False,
                    "error": error_message,
                },
            )

            self.set_status("ERROR")
            return result

        finally:
            with self.operation_lock:
                if self._active_goal_handle is goal_handle:
                    self._active_goal_handle = None
                if not self._robot_stopped:
                    self._stop_requested = False
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

        controller_node.publish_system_event(
            controller_node.SEVERITY_CRITICAL,
            "CONTROLLER_STARTUP_FAILED",
            str(e),
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