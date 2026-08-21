import rclpy
import DR_init


ROBOT_ID = "dsr01"
ROBOT_MODEL = "m0609"


DR_init.__dsr__id = ROBOT_ID
DR_init.__dsr__model = ROBOT_MODEL


def main(args=None):
    rclpy.init(args=args)

    node = rclpy.create_node(
        "solar_panel_robot",
        namespace=ROBOT_ID
    )

    # DSR_ROBOT2에서 사용할 ROS2 Node 설정
    DR_init.__dsr__node = node

    try:
        from .motion import RobotMotion

        motion = RobotMotion()

        node.get_logger().info("Pick & Place 작업 시작")

        # Pick
        node.get_logger().info("물체 Pick 시작")
        motion.pick("pick")
        node.get_logger().info("물체 Pick 완료")

        # Place
        node.get_logger().info("물체 Place 시작")
        motion.place("place")
        node.get_logger().info("물체 Place 완료")

        node.get_logger().info("Pick & Place 작업 완료")

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