import rclpy
import DR_init
import time


ROBOT_ID = "dsr01"
ROBOT_MODEL = "m0609"

TOOL_NAME = "ToolWeight"
TCP_NAME = "GripperDA_v1"

MANUAL_MODE = 0
AUTO_MODE = 1


DR_init.__dsr__id = ROBOT_ID
DR_init.__dsr__model = ROBOT_MODEL


def main(args=None):
    rclpy.init(args=args)

    node = rclpy.create_node(
        "solar_panel_robot",
        namespace=ROBOT_ID
    )

    DR_init.__dsr__node = node

    try:
        # DSR node 설정 이후 import
        from DSR_ROBOT2 import (
            set_robot_mode,
            set_tool,
            set_tcp,
        )

        from .motion import RobotMotion

        # =========================================================
        # Robot 초기 설정
        # =========================================================

        # 1. Manual Mode
        node.get_logger().info("Manual Mode 전환 시작")

        set_robot_mode(MANUAL_MODE)

        time.sleep(0.5)

        node.get_logger().info("Manual Mode 전환 완료")

        # 2. Tool 설정
        node.get_logger().info(
            f"Tool 설정 시작: {TOOL_NAME}"
        )

        set_tool(TOOL_NAME)

        node.get_logger().info(
            f"Tool 설정 완료: {TOOL_NAME}"
        )

        # 3. TCP 설정
        node.get_logger().info(
            f"TCP 설정 시작: {TCP_NAME}"
        )

        set_tcp(TCP_NAME)

        node.get_logger().info(
            f"TCP 설정 완료: {TCP_NAME}"
        )

        # 4. Auto Mode
        node.get_logger().info("Auto Mode 전환 시작")

        set_robot_mode(AUTO_MODE)

        time.sleep(0.5)

        node.get_logger().info("Auto Mode 전환 완료")

        # =========================================================
        # Motion
        # =========================================================

        motion = RobotMotion()

        node.get_logger().info("전체 작업 시작")

        # 5. Home
        node.get_logger().info("Home 이동 시작")

        motion.move_home()

        node.get_logger().info("Home 이동 완료")

        # 6. Pick
        node.get_logger().info("Pick 시작")

        motion.pick("pick")

        node.get_logger().info("Pick 완료")

        # 7. Place
        node.get_logger().info("Place 시작")

        motion.place("place")

        node.get_logger().info("Place 완료")

        node.get_logger().info("전체 작업 완료")

    except Exception as e:
        node.get_logger().error(
            f"작업 중 오류 발생: {e}"
        )

    finally:
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()