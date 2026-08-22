class SolarMotion:

    def __init__(self, node):

        self.node = node

        # DR_init 설정 이후 실행됨
        from DSR_ROBOT2 import (
            movel,
            posx,
            get_current_posx,
            wait,
            DR_BASE,
        )

        from .motion import RobotMotion
        from .force_control import ForceController
        from .config_loader import PoseLoader


        self.movel = movel
        self.get_current_posx = get_current_posx
        self.wait = wait
        self.DR_BASE = DR_BASE


        # ==========================================
        # 객체 생성
        # ==========================================

        self.config = PoseLoader()

        self.motion = RobotMotion()
        self.force = ForceController()


        # ==========================================
        # 좌표
        # ==========================================

        self.start = posx(
            self.config.get("start")["position"]
        )

        self.a = posx(
            self.config.get("a")["position"]
        )

        self.b = posx(
            self.config.get("b")["position"]
        )

        self.c = posx(
            self.config.get("c")["position"]
        )

        self.d = posx(
            self.config.get("d")["position"]
        )


    # =========================================================
    # 전체 Solar 작업
    # =========================================================

    def run(self):

        try:

            self.node.get_logger().info(
                "========== PIN INSERT START =========="
            )


            # =================================================
            # 0. Home
            # =================================================

            self.node.get_logger().info(
                "0. Home 이동"
            )

            self.motion.move_home()

            self.wait(1.0)


            # =================================================
            # 1. Pick 위치 이동
            # =================================================

            self.node.get_logger().info(
                "1. Pin Pick 대기 위치 이동"
            )

            self.movel(
                self.a,
                vel=self.motion.velocity,
                acc=self.motion.acc,
                ref=self.DR_BASE
            )

            self.wait(0.5)


            # =================================================
            # 2. Pick
            # =================================================

            self.node.get_logger().info(
                "2. Pin Pick 시작"
            )

            self.motion.pick()

            self.node.get_logger().info(
                "2. Pin Pick 완료"
            )

            self.wait(0.5)


            # =================================================
            # 3. Arc 이동
            # =================================================

            self.node.get_logger().info(
                "3. Hole Front Arc 이동 시작"
            )

            self.motion.move_arc(
                self.start,
                self.b,
                height=100,
                steps=6
            )

            self.node.get_logger().info(
                "3. Hole Front Arc 이동 완료"
            )

            self.wait(1.0)


            # =================================================
            # 4. 1차 Force 삽입
            # =================================================

            self.node.get_logger().info(
                "4. 1차 Force 삽입 시작"
            )


            # -------------------------------------------------
            # Compliance ON
            # -------------------------------------------------

            self.force.compliance_on(
                stiffness=(
                    300,
                    8000,
                    8000,
                    800,
                    800,
                    800
                ),
                reference="base"
            )

            self.node.get_logger().info(
                "4. Compliance ON 완료"
            )

            self.wait(1.0)


            # -------------------------------------------------
            # Force ON
            # BASE +X 10N
            # -------------------------------------------------

            self.node.get_logger().info(
                "4. Force ON 시작"
            )

            self.force.force_on(
                desired_force=(
                    40,
                    0,
                    0,
                    0,
                    0,
                    0
                ),
                direction=(
                    1,
                    0,
                    0,
                    0,
                    0,
                    0
                ),
                mode="relative"
            )

            self.node.get_logger().info(
                "4. Force ON 완료"
            )


            # -------------------------------------------------
            # B의 X 좌표 도달 확인
            # -------------------------------------------------

            while True:

                current_pos, _ = (
                    self.get_current_posx(
                        ref=self.DR_BASE
                    )
                )

                current_x = current_pos[0]
                target_x = self.b[0]

                self.node.get_logger().info(
                    f"[1차 삽입] "
                    f"current_x={current_x:.2f}, "
                    f"target_x={target_x:.2f}"
                )

                if current_x >= target_x + 40:

                    self.node.get_logger().info(
                        "1차 삽입 목표 위치 도달"
                    )

                    break

                self.wait(0.05)


            # -------------------------------------------------
            # Force OFF
            # -------------------------------------------------

            self.force.force_off()

            self.wait(0.3)


            # -------------------------------------------------
            # Compliance OFF
            # -------------------------------------------------

            self.force.compliance_off()

            self.wait(0.5)

            self.node.get_logger().info(
                "4. 1차 Force 삽입 완료"
            )


            # =================================================
            # 5. Gripper Release
            # =================================================

            self.node.get_logger().info(
                "5. Gripper Release"
            )

            self.motion.gripper.release()

            self.wait(0.5)


            # =================================================
            # 6. C 위치 이동
            # =================================================

            self.node.get_logger().info(
                "6. 재파지 위치 이동"
            )

            self.movel(
                self.c,
                vel=50,
                acc=100,
                ref=self.DR_BASE
            )

            self.wait(1.0)


            # =================================================
            # 다시 Grasp
            # =================================================

            self.node.get_logger().info(
                "6. Pin Re-Grasp"
            )

            self.motion.gripper.grasp()

            self.wait(0.5)


            # =================================================
            # 7. 최종 Force 삽입
            # =================================================

            self.node.get_logger().info(
                "7. 최종 Force 삽입 시작"
            )


            # -------------------------------------------------
            # Compliance ON
            # -------------------------------------------------

            self.force.compliance_on(
                stiffness=(
                    500,
                    500,
                    500,
                    100,
                    100,
                    100
                ),
                reference="base"
            )

            self.node.get_logger().info(
                "7. Compliance ON 완료"
            )

            self.wait(1.0)


            # -------------------------------------------------
            # Force ON
            # -------------------------------------------------

            self.node.get_logger().info(
                "7. Force ON 시작"
            )

            self.force.force_on(
                desired_force=(
                    40,
                    0,
                    0,
                    0,
                    0,
                    0
                ),
                direction=(
                    1,
                    0,
                    0,
                    0,
                    0,
                    0
                ),
                mode="relative"
            )

            self.node.get_logger().info(
                "7. Force ON 완료"
            )


            # -------------------------------------------------
            # D의 X 좌표 도달 확인
            # -------------------------------------------------

            while True:

                current_pos, _ = (
                    self.get_current_posx(
                        ref=self.DR_BASE
                    )
                )

                current_x = current_pos[0]
                target_x = self.d[0]

                self.node.get_logger().info(
                    f"[최종 삽입] "
                    f"current_x={current_x:.2f}, "
                    f"target_x={target_x:.2f}"
                )

                if current_x >= target_x:

                    self.node.get_logger().info(
                        "최종 삽입 목표 위치 도달"
                    )

                    break

                self.wait(0.05)


            # -------------------------------------------------
            # Force OFF
            # -------------------------------------------------

            self.force.force_off()

            self.wait(0.3)


            # -------------------------------------------------
            # Compliance OFF
            # -------------------------------------------------

            self.force.compliance_off()

            self.wait(0.5)

            self.node.get_logger().info(
                "7. 최종 Force 삽입 완료"
            )


            # =================================================
            # 최종 Release
            # =================================================

            self.node.get_logger().info(
                "최종 Pin Release"
            )

            self.motion.gripper.release()

            self.wait(0.5)


            # =================================================
            # 8. Home 복귀
            # =================================================

            self.node.get_logger().info(
                "8. Home 복귀 시작"
            )

            self.motion.move_home()

            self.node.get_logger().info(
                "8. Home 복귀 완료"
            )


            self.node.get_logger().info(
                "========== PIN INSERT COMPLETE =========="
            )


        # =====================================================
        # 작업 오류
        # =====================================================

        except Exception as e:

            self.node.get_logger().error(
                f"Solar Motion 작업 중 오류: {e}"
            )

            try:

                self.force.all_off()

            except Exception as force_error:

                self.node.get_logger().error(
                    f"Force 해제 중 오류: {force_error}"
                )

            # main까지 오류 전달
            raise