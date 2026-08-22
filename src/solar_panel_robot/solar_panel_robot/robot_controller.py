import time


MANUAL_MODE = 0
AUTO_MODE = 1

TOOL_NAME = "ToolWeight"
TCP_NAME = "GripperDA_v1"


class RobotController:

    def __init__(self, node):

        self.node = node

        # 중요:
        # main.py에서 DR_init 설정 완료 후
        # RobotController가 생성되어야 함
        from DSR_ROBOT2 import (
            set_robot_mode,
            set_tool,
            set_tcp,
        )

        self.set_robot_mode = set_robot_mode
        self.set_tool = set_tool
        self.set_tcp = set_tcp


    def initialize(self):

        self.node.get_logger().info(
            "========== ROBOT INITIALIZE START =========="
        )


        # =====================================================
        # Manual Mode
        # =====================================================

        self.node.get_logger().info(
            "Manual Mode 전환 시작"
        )

        self.set_robot_mode(
            MANUAL_MODE
        )

        time.sleep(0.5)

        self.node.get_logger().info(
            "Manual Mode 전환 완료"
        )


        # =====================================================
        # Tool
        # =====================================================

        self.node.get_logger().info(
            f"Tool 설정 시작: {TOOL_NAME}"
        )

        self.set_tool(
            TOOL_NAME
        )

        self.node.get_logger().info(
            f"Tool 설정 완료: {TOOL_NAME}"
        )


        # =====================================================
        # TCP
        # =====================================================

        self.node.get_logger().info(
            f"TCP 설정 시작: {TCP_NAME}"
        )

        self.set_tcp(
            TCP_NAME
        )

        self.node.get_logger().info(
            f"TCP 설정 완료: {TCP_NAME}"
        )


        # =====================================================
        # Auto Mode
        # =====================================================

        self.node.get_logger().info(
            "Auto Mode 전환 시작"
        )

        self.set_robot_mode(
            AUTO_MODE
        )

        time.sleep(0.5)

        self.node.get_logger().info(
            "Auto Mode 전환 완료"
        )


        self.node.get_logger().info(
            "========== ROBOT INITIALIZE COMPLETE =========="
        )