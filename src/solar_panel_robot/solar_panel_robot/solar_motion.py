# =========================================================
# Frame 작업 예외
# =========================================================

class FramePickError(Exception):
    pass


class FramePlaceError(Exception):
    pass


class SolarMotion:

    def __init__(self, node):

        self.node = node

        from DSR_ROBOT2 import (
            movel,
            posx,
            get_current_posx,
            wait,
            DR_BASE,
        )

        from .robot_motion import RobotMotion
        from .force_control import ForceController
        from .config_loader import PoseLoader

        self.movel = movel
        self.get_current_posx = get_current_posx
        self.wait = wait
        self.DR_BASE = DR_BASE

        self.config = PoseLoader()
        self.motion = RobotMotion()
        self.force = ForceController()

        # =====================================================
        # 현재 테스트용 좌표
        # 추후 DB에서 전달받는 구조로 변경 예정
        # =====================================================

        # Lock Pin 관련 좌표
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

        # Frame 관련 좌표
        self.frame_pick = posx(
            self.config.get("frame_pick")["position"]
        )

        self.frame_place = posx(
            self.config.get("frame_place")["position"]
        )


    # =========================================================
    # Frame Pick
    # =========================================================

    def pick_frame(self):

        self.node.get_logger().info(
            "========== FRAME PICK START =========="
        )

        try:

            self.node.get_logger().info(
                "Frame Pick 대기 위치 이동"
            )

            self.movel(
                self.frame_pick,
                vel=self.motion.velocity,
                acc=self.motion.acc,
                ref=self.DR_BASE,
            )

            self.wait(0.5)

            self.node.get_logger().info(
                "Frame Pick 시작"
            )

            self.motion.pick()

            self.node.get_logger().info(
                "Frame Pick 완료"
            )

            self.wait(0.5)

            self.node.get_logger().info(
                "========== FRAME PICK COMPLETE =========="
            )

        except Exception as e:

            self.node.get_logger().error(
                f"Frame Pick 실패: {e}"
            )

            raise FramePickError(
                str(e)
            ) from e


    # =========================================================
    # Frame Place
    # =========================================================

    def place_frame(self):

        self.node.get_logger().info(
            "========== FRAME PLACE START =========="
        )

        try:

            self.node.get_logger().info(
                "Frame Place 대기 위치 이동"
            )

            self.movel(
                self.frame_place,
                vel=self.motion.velocity,
                acc=self.motion.acc,
                ref=self.DR_BASE,
            )

            self.wait(0.5)

            self.node.get_logger().info(
                "Frame Place 시작"
            )

            self.motion.place()

            self.node.get_logger().info(
                "Frame Place 완료"
            )

            self.wait(0.5)

            self.node.get_logger().info(
                "========== FRAME PLACE COMPLETE =========="
            )

        except Exception as e:

            self.node.get_logger().error(
                f"Frame Place 실패: {e}"
            )

            raise FramePlaceError(
                str(e)
            ) from e


    # =========================================================
    # 전체 Frame 설치 공정
    # =========================================================

    def install_frame(self):

        self.node.get_logger().info(
            "========== FRAME INSTALL START =========="
        )

        try:
            self.pick_frame()
            self.place_frame()

            self.node.get_logger().info(
                "========== FRAME INSTALL COMPLETE =========="
            )

        except FramePickError as e:

            self.node.get_logger().error(
                f"Frame Install 실패 - PICK 단계: {e}"
            )

            # 상위 Controller까지 전달
            raise

        except FramePlaceError as e:

            self.node.get_logger().error(
                f"Frame Install 실패 - PLACE 단계: {e}"
            )
            raise

        except Exception as e:

            self.node.get_logger().error(
                f"Frame Install 알 수 없는 오류: {e}"
            )

            raise


    # =========================================================
    # Lock Pin Pick
    # =========================================================

    def pick_pin(self):

        self.node.get_logger().info(
            "========== PIN PICK START =========="
        )

        self.node.get_logger().info(
            "Pin Pick 대기 위치 이동"
        )

        self.movel(
            self.a,
            vel=self.motion.velocity,
            acc=self.motion.acc,
            ref=self.DR_BASE,
        )

        self.wait(0.5)

        self.node.get_logger().info(
            "Pin Pick 시작"
        )

        self.motion.pick()

        self.node.get_logger().info(
            "Pin Pick 완료"
        )

        self.wait(0.5)

        self.node.get_logger().info(
            "========== PIN PICK COMPLETE =========="
        )


    # =========================================================
    # Lock Pin 1차 삽입
    # =========================================================

    def first_insert_pin(self):

        self.node.get_logger().info(
            "========== FIRST PIN INSERT START =========="
        )

        # -----------------------------------------------------
        # Hole Front까지 Arc 이동
        # -----------------------------------------------------

        self.node.get_logger().info(
            "Hole Front Arc 이동 시작"
        )

        self.motion.move_arc(
            self.start,
            self.b,
            height=100,
            steps=6,
        )

        self.node.get_logger().info(
            "Hole Front Arc 이동 완료"
        )

        self.wait(1.0)

        # -----------------------------------------------------
        # Compliance ON
        # -----------------------------------------------------

        self.node.get_logger().info(
            "1차 삽입 Compliance ON"
        )

        self.force.compliance_on(
            stiffness={
                "x": 300,
                "y": 8000,
                "z": 8000,
                "a": 800,
                "b": 800,
                "c": 800,
            },
            reference="base",
        )

        self.wait(1.0)

        # -----------------------------------------------------
        # Force ON
        # -----------------------------------------------------

        self.node.get_logger().info(
            "1차 삽입 Force ON"
        )

        self.force.force_on(
            forces={
                "x": 40,
            },
            mode="relative",
            reference="base",
        )

        # -----------------------------------------------------
        # 1차 삽입 위치 확인
        # -----------------------------------------------------

        while True:

            current_pos, _ = self.get_current_posx(
                ref=self.DR_BASE
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

        # -----------------------------------------------------
        # Force OFF
        # -----------------------------------------------------

        self.force.force_off()

        self.wait(0.3)

        # -----------------------------------------------------
        # Compliance OFF
        # -----------------------------------------------------

        self.force.compliance_off()

        self.wait(0.5)

        self.node.get_logger().info(
            "========== FIRST PIN INSERT COMPLETE =========="
        )


    # =========================================================
    # Lock Pin 최종 삽입
    # =========================================================

    def final_insert_pin(self):

        self.node.get_logger().info(
            "========== FINAL PIN INSERT START =========="
        )

        # -----------------------------------------------------
        # 기존 파지 해제
        # -----------------------------------------------------

        self.node.get_logger().info(
            "Pin Release"
        )

        self.motion.release()

        self.wait(0.5)

        # -----------------------------------------------------
        # 재파지 위치 이동
        # -----------------------------------------------------

        self.node.get_logger().info(
            "Pin 재파지 위치 이동"
        )

        self.movel(
            self.c,
            vel=50,
            acc=100,
            ref=self.DR_BASE,
        )

        self.wait(1.0)

        # -----------------------------------------------------
        # 다시 파지
        # -----------------------------------------------------

        self.node.get_logger().info(
            "Pin Re-Grasp"
        )

        self.motion.grasp()

        self.wait(0.5)

        # -----------------------------------------------------
        # Compliance ON
        # -----------------------------------------------------

        self.node.get_logger().info(
            "최종 삽입 Compliance ON"
        )

        self.force.compliance_on(
            stiffness={
                "x": 500,
                "y": 500,
                "z": 500,
                "a": 100,
                "b": 100,
                "c": 100,
            },
            reference="base",
        )

        self.wait(1.0)

        # -----------------------------------------------------
        # Force ON
        # -----------------------------------------------------

        self.node.get_logger().info(
            "최종 삽입 Force ON"
        )

        self.force.force_on(
            forces={
                "x": 40,
            },
            mode="relative",
            reference="base",
        )

        # -----------------------------------------------------
        # 최종 삽입 위치 확인
        # -----------------------------------------------------

        while True:

            current_pos, _ = self.get_current_posx(
                ref=self.DR_BASE
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

        # -----------------------------------------------------
        # Force OFF
        # -----------------------------------------------------

        self.force.force_off()

        self.wait(0.3)

        # -----------------------------------------------------
        # Compliance OFF
        # -----------------------------------------------------

        self.force.compliance_off()

        self.wait(0.5)

        # -----------------------------------------------------
        # 최종 Pin Release
        # -----------------------------------------------------

        self.node.get_logger().info(
            "최종 Pin Release"
        )

        self.motion.release()

        self.wait(0.5)

        self.node.get_logger().info(
            "========== FINAL PIN INSERT COMPLETE =========="
        )


    # =========================================================
    # 전체 Lock Pin 삽입 공정
    # =========================================================

    def insert_pin(self):

        self.node.get_logger().info(
            "========== PIN INSERT START =========="
        )

        self.pick_pin()

        self.first_insert_pin()

        self.final_insert_pin()

        self.node.get_logger().info(
            "========== PIN INSERT COMPLETE =========="
        )


    # =========================================================
    # 전체 Solar 작업
    # =========================================================

    def run(self):

        try:

            self.node.get_logger().info(
                "========== SOLAR MOTION START =========="
            )

            # -------------------------------------------------
            # 시작 위치
            # -------------------------------------------------

            self.node.get_logger().info(
                "Home 이동"
            )

            self.motion.move_home()

            self.wait(1.0)

            # -------------------------------------------------
            # Frame 설치
            # -------------------------------------------------

            self.install_frame()

            self.wait(1.0)

            # -------------------------------------------------
            # Lock Pin 삽입
            # -------------------------------------------------

            self.insert_pin()

            # -------------------------------------------------
            # 작업 완료 후 Home 복귀
            # -------------------------------------------------

            self.node.get_logger().info(
                "Home 복귀 시작"
            )

            self.motion.move_home()

            self.node.get_logger().info(
                "Home 복귀 완료"
            )

            self.node.get_logger().info(
                "========== SOLAR MOTION COMPLETE =========="
            )

        except Exception as e:

            self.node.get_logger().error(
                f"Solar Motion 작업 중 오류: {e}"
            )

            # -------------------------------------------------
            # Force / Compliance가 켜진 상태에서
            # 오류가 발생했을 경우 안전하게 해제
            # -------------------------------------------------

            try:

                self.force.all_off()

            except Exception as force_error:

                self.node.get_logger().error(
                    f"Force 해제 중 오류: {force_error}"
                )

            # main.py / Action Server까지 오류 전달
            raise