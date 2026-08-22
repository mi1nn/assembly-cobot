import rclpy
from rclpy.node import Node

from std_msgs.msg import String

import DR_init


ROBOT_ID = "dsr01"
ROBOT_MODEL = "m0609"


class SolarPanelNode(Node):

    def __init__(self):

        super().__init__(
            "solar_panel_robot",
            namespace=ROBOT_ID
        )

        self.robot = None
        self.solar = None

        # ==========================================
        # 현재 상태
        # ==========================================

        self.current_status = "STARTING"


        # ==========================================
        # Status Publisher
        # 실제 Topic: /dsr01/status
        # ==========================================

        self.status_publisher = self.create_publisher(
            String,
            "status",
            10
        )


        # ==========================================
        # 현재 상태를 1초마다 Publish
        # ==========================================

        self.status_timer = self.create_timer(
            1.0,
            self.publish_current_status
        )


        self.get_logger().info(
            "Solar Panel Robot Node 생성 완료"
        )

        self.set_status("STARTING")


    # ==============================================
    # 상태 변경
    # ==============================================

    def set_status(self, status):

        self.current_status = status

        self.get_logger().info(
            f"[STATUS] {status}"
        )

        # 상태 변경 즉시 한 번 Publish
        self.publish_current_status()


    # ==============================================
    # 현재 상태 Publish
    # ==============================================

    def publish_current_status(self):

        msg = String()

        msg.data = self.current_status

        self.status_publisher.publish(msg)


    # ==============================================
    # Robot / Motion 준비
    # ==============================================

    def setup_components(self):

        from .robot_controller import RobotController
        from .solar_motion import SolarMotion


        # ==========================================
        # Robot 초기화 시작
        # ==========================================

        self.set_status(
            "INITIALIZING"
        )


        # ==========================================
        # Robot Controller 생성
        # ==========================================

        self.robot = RobotController(
            self
        )


        # ==========================================
        # Manual
        # Tool
        # TCP
        # Auto
        # ==========================================

        self.robot.initialize()


        # ==========================================
        # Solar Motion 생성
        # ==========================================

        self.solar = SolarMotion(
            self
        )


        self.get_logger().info(
            "Robot 및 Solar Motion 준비 완료"
        )


        # ==========================================
        # 작업 준비 완료
        # ==========================================

        self.set_status(
            "READY"
        )


    # ==============================================
    # Solar Motion 실행
    # ==============================================

    def run_solar_motion(self):

        # SolarMotion 준비 확인
        if self.solar is None:

            raise RuntimeError(
                "SolarMotion이 준비되지 않았습니다."
            )


        try:

            # ======================================
            # 작업 시작
            # ======================================

            self.set_status(
                "RUNNING"
            )


            # ======================================
            # 실제 작업
            # ======================================

            self.solar.run()


            # ======================================
            # 작업 정상 완료
            # ======================================

            self.set_status(
                "READY"
            )


        except Exception:

            # ======================================
            # 작업 오류
            # ======================================

            self.set_status(
                "ERROR"
            )

            # main()까지 오류 전달
            raise


def main(args=None):

    # ==============================================
    # ROS2 초기화
    # ==============================================

    rclpy.init(args=args)


    # ==============================================
    # Doosan 기본 설정
    # ==============================================

    DR_init.__dsr__id = ROBOT_ID
    DR_init.__dsr__model = ROBOT_MODEL


    # ==============================================
    # Node 생성
    # ==============================================

    node = SolarPanelNode()


    # ==============================================
    # Doosan Node 등록
    # ==============================================

    DR_init.__dsr__node = node


    try:

        # ==========================================
        # Robot 초기화
        # ==========================================

        node.setup_components()


        # ==========================================
        # 현재 테스트용
        #
        # 추후에는 ROS Action/Service가
        # 이 함수를 호출하게 만들 예정
        # ==========================================

        node.run_solar_motion()


        # ==========================================
        # ROS 통신 대기
        # ==========================================

        rclpy.spin(
            node
        )


    except KeyboardInterrupt:

        node.get_logger().info(
            "사용자에 의해 종료되었습니다."
        )


    except Exception as e:

        node.get_logger().error(
            f"프로그램 오류: {e}"
        )

        node.set_status(
            "ERROR"
        )


    finally:

        node.destroy_node()

        if rclpy.ok():

            rclpy.shutdown()


if __name__ == "__main__":
    main()