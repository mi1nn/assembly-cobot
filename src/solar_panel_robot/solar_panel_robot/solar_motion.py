# =========================================================
# Frame 작업 예외
# =========================================================

class FramePickError(Exception):
    pass


class FramePlaceError(Exception):
    pass


# =========================================================
# Pin 작업 예외
# =========================================================

class PinPickError(Exception):
    pass


class PinPlaceError(Exception):
    pass


class PinInsertError(Exception):
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
        from .config_loader import PoseLoader

        self.movel = movel
        self.get_current_posx = get_current_posx
        self.wait = wait
        self.DR_BASE = DR_BASE

        self.config = PoseLoader()
        self.motion = RobotMotion()
        self.force = self.motion.force

        # =====================================================
        # 현재 테스트용 좌표
        # 추후 DB에서 전달받는 구조로 변경 예정
        # =====================================================

        # Frame 관련 좌표
        self.frame_pick = posx(
            self.config.get("frame_pick")["position"]
        )

        self.frame_place = posx(
            self.config.get("frame_place")["position"]
        )

        # Pin 관련 좌표
        self.pin_pick = posx(
            self.config.get("pin_pick")["position"]
        )

        self.pin_place = posx(
            self.config.get("pin_place")["position"]
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

            retreat_distance = self.motion.place()

            self.node.get_logger().info(
                "Frame Place Force 단계 완료 - Gripper 유지"
            )

            self.wait(0.5)

            # =====================================================
            # Frame 설치 확인
            # =====================================================

            self.node.get_logger().info(
                "Frame 설치 상태 확인 시작"
            )

            check_result = self.check_frame(
                distance=50.0,
                force_threshold=50.0,
            )

            if not check_result:

                self.node.get_logger().error(
                    "[FRAME INSTALL][ERROR] Frame Check 실패 - "
                    "현재 위치에서 작업을 중단합니다. "
                    "Gripper는 파지 상태를 유지합니다."
                )

                raise FramePlaceError(
                    "Frame 설치 확인 실패"
                )

            self.node.get_logger().info(
                "Frame 설치 확인 성공"
            )

            self.wait(0.5)

            # =====================================================
            # 2단계 확인 완료 후 Gripper Release
            # =====================================================

            self.node.get_logger().info(
                "2단계 확인 완료 -> Gripper Release"
            )

            self.motion.release()

            self.wait(0.5)

            # =====================================================
            # Release 이후 BASE +Z 방향 안전 이탈
            # =====================================================

            self.node.get_logger().info(
                f"Frame Release 완료 -> BASE +Z {retreat_distance}mm 이탈"
            )

            self.motion.move_z(
                retreat_distance,
                ref=self.DR_BASE,
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
    # Frame 설치 확인
    # =========================================================

    def check_frame(
        self,
        distance=50.0,
        force_threshold=50.0,
    ):

        self.node.get_logger().info(
            "========== FRAME CHECK START =========="
        )

        result = self.motion.check_force_move(
            distance=distance,
            force_threshold=force_threshold,
            velocity=10.0,
            acc=20.0,
            label="FRAME CHECK",
        )

        if result:

            self.node.get_logger().info(
                "Frame Check 성공"
            )

            self.node.get_logger().info(
                "========== FRAME CHECK COMPLETE =========="
            )

            return True

        self.node.get_logger().error(
            "Frame Check 실패"
        )

        self.node.get_logger().info(
            "========== FRAME CHECK FAILED =========="
        )

        return False


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
    # Pin Pick
    # =========================================================

    def pick_pin(
        self,
        approach_height=180.0,
    ):

        self.node.get_logger().info(
            "========== PIN PICK START =========="
        )

        try:
            # pin_pick은 실제 파지 위치로 사용한다.
            # 먼저 BASE +Z approach_height 위의 대기 위치로 이동한 뒤
            # RobotMotion.pick()으로 하강 -> 파지 -> 상승한다.
            _, pin_ready = self.motion.make_target_ready(
                "pin_pick",
                approach_height,
            )

            self.node.get_logger().info(
                f"Pin Pick 대기 위치 이동 - target 위 {approach_height}mm"
            )

            self.movel(
                pin_ready,
                vel=self.motion.velocity,
                acc=self.motion.acc,
                ref=self.DR_BASE,
            )

            self.wait(0.5)

            self.node.get_logger().info(
                "Pin Pick 시작"
            )

            self.motion.pick(
                distance=approach_height
            )

            self.node.get_logger().info(
                "Pin Pick 완료"
            )

            self.wait(0.5)

            self.node.get_logger().info(
                "========== PIN PICK COMPLETE =========="
            )

        except Exception as e:
            self.node.get_logger().error(
                f"Pin Pick 실패: {e}"
            )

            raise PinPickError(
                str(e)
            ) from e


    # =========================================================
    # Pin Force Place
    # =========================================================

    def place_pin(self):

        self.node.get_logger().info(
            "========== PIN PLACE START =========="
        )

        try:
            self.node.get_logger().info(
                "Pin Place 대기 위치 이동"
            )

            self.movel(
                self.pin_place,
                vel=self.motion.velocity,
                acc=self.motion.acc,
                ref=self.DR_BASE,
            )

            self.wait(0.5)

            self.node.get_logger().info(
                "Pin Force Place 시작"
            )

            # Frame과 동일한 Force Place 사용
            # 1단계: baseline 대비 |Delta Fz| >= 20N 접촉
            # 압입: Desired Force / insert_force 확인
            # 종료 후에도 Gripper는 닫힌 상태를 유지한다.
            retreat_distance = self.motion.place()

            self.node.get_logger().info(
                "Pin Force Place 완료 - Gripper 유지"
            )

            self.wait(0.5)

            self.node.get_logger().info(
                "========== PIN PLACE COMPLETE =========="
            )

            return retreat_distance

        except Exception as e:
            self.node.get_logger().error(
                f"Pin Place 실패: {e}"
            )

            raise PinPlaceError(
                str(e)
            ) from e


    # =========================================================
    # Pin 최종 삽입
    # =========================================================

    def insert_pin(
        self,
        lift_distance=50.0,
        insert_distance=50.0,
        force_threshold=50.0,
    ):
        """
        Force Place가 끝난 Pin을 최종 삽입한다.

        순서:
            1. Pin Release
            2. BASE +Z로 lift_distance 상승
            3. 빈 Gripper Close
            4. Frame Check와 동일한 방식으로 TOOL Z 방향 이동
            5. 이동 중 실제 |F_tool_z| >= force_threshold이면 즉시 정지/성공
            6. 최대 거리까지 미감지 시 현재 위치에서 ERROR/실패

        현재 frame_place / pin_place 자세와 동일하게
        TOOL +Z가 물리적인 하강 방향이라는 전제로
        insert_distance는 +값을 사용한다.
        """

        self.node.get_logger().info(
            "========== PIN INSERT START =========="
        )

        try:
            # -------------------------------------------------
            # 1. Force Place 후 Pin 내려놓기
            # -------------------------------------------------

            self.node.get_logger().info(
                "Pin Release"
            )

            self.motion.release()
            self.wait(0.5)

            # -------------------------------------------------
            # 2. BASE +Z 50mm 상승
            # -------------------------------------------------

            self.node.get_logger().info(
                f"Pin 상부로 BASE +Z {lift_distance}mm 이동"
            )

            self.motion.move_z(
                lift_distance,
                ref=self.DR_BASE,
            )

            self.wait(0.5)

            # -------------------------------------------------
            # 3. 빈 Gripper Close
            # -------------------------------------------------

            self.node.get_logger().info(
                "Pin 삽입용 Gripper Close"
            )

            self.motion.grasp()
            self.wait(0.5)

            # -------------------------------------------------
            # 4. 아래 방향 이동 + 실제 Force 확인
            # -------------------------------------------------

            self.node.get_logger().info(
                f"Pin 삽입 Force Check 시작 - "
                f"distance={insert_distance}mm, "
                f"threshold={force_threshold}N"
            )

            insert_result = self.motion.check_force_move(
                distance=insert_distance,
                force_threshold=force_threshold,
                velocity=10.0,
                acc=20.0,
                label="PIN INSERT",
            )

            if not insert_result:
                self.node.get_logger().error(
                    "[PIN INSERT][ERROR] Force threshold 미감지 - "
                    "현재 위치에서 작업을 중단합니다."
                )

                raise PinInsertError(
                    "Pin 최종 삽입 확인 실패"
                )

            self.node.get_logger().info(
                "Pin 최종 삽입 성공"
            )

            self.node.get_logger().info(
                "========== PIN INSERT COMPLETE =========="
            )

            return True

        except PinInsertError:
            raise

        except Exception as e:
            self.node.get_logger().error(
                f"Pin Insert 실패: {e}"
            )

            raise PinInsertError(
                str(e)
            ) from e


    # =========================================================
    # 전체 Pin 설치 공정
    # =========================================================

    def install_pin(self):

        self.node.get_logger().info(
            "========== PIN INSTALL START =========="
        )

        try:
            self.pick_pin()
            self.place_pin()
            self.insert_pin(
                lift_distance=50.0,
                insert_distance=50.0,
                force_threshold=50.0,
            )

            self.node.get_logger().info(
                "========== PIN INSTALL COMPLETE =========="
            )

            return True

        except PinPickError as e:
            self.node.get_logger().error(
                f"Pin Install 실패 - PICK 단계: {e}"
            )
            raise

        except PinPlaceError as e:
            self.node.get_logger().error(
                f"Pin Install 실패 - PLACE 단계: {e}"
            )
            raise

        except PinInsertError as e:
            self.node.get_logger().error(
                f"Pin Install 실패 - INSERT 단계: {e}"
            )
            raise

        except Exception as e:
            self.node.get_logger().error(
                f"Pin Install 알 수 없는 오류: {e}"
            )
            raise


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

            self.install_pin()

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