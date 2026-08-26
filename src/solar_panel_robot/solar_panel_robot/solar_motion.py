# =========================================================
# Post 작업 예외
# =========================================================

class PostPickError(Exception):
    pass


class PostPlaceError(Exception):
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

    POST_COMPONENT_PREFIX = "CMP-POST-"

    def __init__(self, node):
        self.node = node

        from DSR_ROBOT2 import (
            movel,
            posx,
            wait,
            DR_BASE,
        )

        from .robot_motion import RobotMotion
        from .config_loader import PoseLoader

        self.movel = movel
        self.posx = posx
        self.wait = wait
        self.DR_BASE = DR_BASE

        self.config = PoseLoader()
        self.motion = RobotMotion()
        self.force = self.motion.force

        # Post 좌표는 DB components에서만 받는다.
        # Pin은 아직 기존 poses.yaml 기반 로직을 유지한다.
        self.pin_pick = posx(
            self.config.get("pin_pick")["position"]
        )
        self.pin_place = posx(
            self.config.get("pin_place")["position"]
        )

    def _require_number(
        self,
        parameters,
        key,
    ):
        if key not in parameters:
            raise ValueError(
                f"DB parameter 누락: {key}"
            )

        value = parameters[key]

        if isinstance(value, bool):
            raise ValueError(
                f"DB parameter {key}는 숫자여야 합니다."
            )

        try:
            return float(value)
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"DB parameter {key}는 숫자여야 합니다: {value}"
            ) from e

    def _optional_number(
        self,
        parameters,
        key,
    ):
        value = parameters.get(key)

        if value is None:
            return None

        if isinstance(value, bool):
            raise ValueError(
                f"DB parameter {key}는 숫자 또는 null이어야 합니다."
            )

        try:
            return float(value)
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"DB parameter {key}는 숫자 또는 null이어야 합니다: {value}"
            ) from e

    def _get_post_component(
        self,
        components,
    ):
        if not isinstance(components, list):
            raise ValueError(
                "components는 list여야 합니다."
            )

        for component in components:
            if not isinstance(component, dict):
                continue

            code = str(
                component.get("code", "")
            )

            if (
                code.startswith(self.POST_COMPONENT_PREFIX)
                and "pickup_position" in component
                and "assembly_position" in component
            ):
                return component

        raise ValueError(
            "Post component를 찾을 수 없습니다. "
            "CMP-POST-* component에 pickup_position과 "
            "assembly_position이 필요합니다."
        )

    def _position_to_posx(
        self,
        position,
        label,
    ):
        if not isinstance(position, dict):
            raise ValueError(
                f"{label}은 JSON object여야 합니다."
            )

        required = (
            "x", "y", "z",
            "A", "B", "C",
        )

        missing = [
            key
            for key in required
            if position.get(key) is None
        ]

        if missing:
            raise ValueError(
                f"{label} 필드 누락: "
                + ", ".join(missing)
            )

        values = []
        for key in ("x", "y", "z", "A", "B", "C"):
            try:
                values.append(float(position[key]))
            except (TypeError, ValueError) as e:
                raise ValueError(
                    f"{label}.{key}는 숫자여야 합니다."
                ) from e

        return self.posx(values)

    def _post_inputs(
        self,
        parameters,
        components,
    ):
        if not isinstance(parameters, dict):
            raise ValueError(
                "parameters는 dict여야 합니다."
            )

        coordinate_system = str(
            parameters.get(
                "coordinate_system",
                "",
            )
        ).upper()

        if coordinate_system != "BASE":
            raise ValueError(
                "현재 Post 동작은 coordinate_system=BASE만 지원합니다."
            )

        component = self._get_post_component(
            components
        )

        pickup_pose = self._position_to_posx(
            component["pickup_position"],
            "pickup_position",
        )

        assembly_pose = self._position_to_posx(
            component["assembly_position"],
            "assembly_position",
        )

        return (
            component,
            pickup_pose,
            assembly_pose,
        )

    # =========================================================
    # Post 단계 DB Log
    # =========================================================

    def _publish_post_event(
        self,
        operation_context,
        *,
        phase,
        status,
        error=None,
        detail=None,
    ):
        """
        Post 세부 단계 이벤트를 /system_event로 발행한다.

        phase:
            PICK / PLACE / CHECK

        status:
            STARTED / COMPLETED / FAILED

        로깅 실패가 실제 Robot Motion 실패로 전파되지 않도록
        이벤트 발행 오류는 warning만 남긴다.
        """
        if not operation_context:
            return

        operation_code = str(
            operation_context.get(
                "operation_code",
                "",
            )
        ).strip()

        if not operation_code:
            return

        phase = str(phase).strip().upper()
        status = str(status).strip().upper()

        event_code = (
            f"POST_{phase}_{status}"
        )

        if status == "FAILED":
            severity = getattr(
                self.node,
                "SEVERITY_ERROR",
                2,
            )
            message = (
                f"[{operation_code}] "
                f"{phase} failed"
            )
        elif status == "COMPLETED":
            severity = getattr(
                self.node,
                "SEVERITY_INFO",
                0,
            )
            message = (
                f"[{operation_code}] "
                f"{phase} completed"
            )
        else:
            severity = getattr(
                self.node,
                "SEVERITY_INFO",
                0,
            )
            message = (
                f"[{operation_code}] "
                f"{phase} started"
            )

        detail_data = {
            "operation_code": operation_code,
            "phase": phase,
            "status": status,
        }

        for key in (
            "work_order_id",
            "operation_id",
            "robot_id",
        ):
            value = operation_context.get(key)
            if value is not None:
                detail_data[key] = value

        if isinstance(detail, dict):
            detail_data.update(detail)

        if error is not None:
            detail_data["error"] = str(error)
            message = (
                f"{message}: {error}"
            )

        try:
            self.node.publish_system_event(
                severity,
                event_code,
                message,
                work_execution_id=int(
                    operation_context.get(
                        "work_execution_id",
                        0,
                    )
                    or 0
                ),
                operation_execution_id=int(
                    operation_context.get(
                        "operation_execution_id",
                        0,
                    )
                    or 0
                ),
                operation_code=operation_code,
                phase=phase,
                status=status,
                detail=detail_data,
            )

        except Exception as log_error:
            self.node.get_logger().warning(
                "Post 단계 SystemEvent 발행 실패: "
                f"{log_error}"
            )


    # =========================================================
    # Post Pick
    # =========================================================

    def pick_post(
        self,
        parameters,
        components,
        operation_context=None,
    ):
        self.node.get_logger().info(
            "========== POST PICK START =========="
        )

        self._publish_post_event(
            operation_context,
            phase="PICK",
            status="STARTED",
        )

        try:
            component, pickup_pose, _ = (
                self._post_inputs(
                    parameters,
                    components,
                )
            )

            speed = self._require_number(
                parameters, "speed"
            )
            acc = self._require_number(
                parameters, "acceleration"
            )
            pick_distance = self._require_number(
                parameters, "pick_distance"
            )

            self.node.get_logger().info(
                f"Post Pick 대기 위치 이동 - "
                f"{component.get('code')}"
            )

            self.movel(
                pickup_pose,
                vel=speed,
                acc=acc,
                ref=self.DR_BASE,
            )

            self.wait(0.5)

            self.motion.pick(
                distance=pick_distance,
                velocity=speed,
                acc=acc,
            )

            self.wait(0.5)

            self.node.get_logger().info(
                "========== POST PICK COMPLETE =========="
            )

            self._publish_post_event(
                operation_context,
                phase="PICK",
                status="COMPLETED",
                detail={
                    "component_code": (
                        component.get("code")
                    ),
                },
            )

            return True

        except Exception as e:
            self.node.get_logger().error(
                f"Post Pick 실패: {e}"
            )

            self._publish_post_event(
                operation_context,
                phase="PICK",
                status="FAILED",
                error=e,
            )

            raise PostPickError(str(e)) from e


    # =========================================================
    # Post Place
    # =========================================================

    def place_post(
        self,
        parameters,
        components,
        operation_context=None,
    ):
        self.node.get_logger().info(
            "========== POST PLACE START =========="
        )

        self._publish_post_event(
            operation_context,
            phase="PLACE",
            status="STARTED",
        )

        try:
            component, _, assembly_pose = (
                self._post_inputs(
                    parameters,
                    components,
                )
            )

            speed = self._require_number(
                parameters, "speed"
            )
            acc = self._require_number(
                parameters, "acceleration"
            )

            self.node.get_logger().info(
                f"Post Place 대기 위치 이동 - "
                f"{component.get('code')}"
            )

            self.movel(
                assembly_pose,
                vel=speed,
                acc=acc,
                ref=self.DR_BASE,
            )

            self.wait(0.5)

            retreat_distance = self.motion.place(
                distance=self._require_number(
                    parameters,
                    "place_retreat_distance",
                ),
                search_limit_z=self._require_number(
                    parameters,
                    "place_search_limit_z",
                ),
                force=self._require_number(
                    parameters,
                    "place_force",
                ),
                contact_force=self._require_number(
                    parameters,
                    "place_contact_force",
                ),
                insert_force=self._require_number(
                    parameters,
                    "place_insert_force",
                ),
                stiffness_z=self._require_number(
                    parameters,
                    "place_stiffness_z",
                ),
                search_velocity=self._require_number(
                    parameters,
                    "place_search_velocity",
                ),
                search_acc=self._require_number(
                    parameters,
                    "place_search_acceleration",
                ),
                search_timeout=self._optional_number(
                    parameters,
                    "place_search_timeout",
                ),
            )

            self.wait(0.5)

            self.node.get_logger().info(
                "Post Place Force 단계 완료 - "
                "Gripper 유지"
            )
            self.node.get_logger().info(
                "========== POST PLACE COMPLETE =========="
            )

            self._publish_post_event(
                operation_context,
                phase="PLACE",
                status="COMPLETED",
                detail={
                    "component_code": (
                        component.get("code")
                    ),
                    "retreat_distance": (
                        float(retreat_distance)
                    ),
                },
            )

            return retreat_distance

        except Exception as e:
            self.node.get_logger().error(
                f"Post Place 실패: {e}"
            )

            self._publish_post_event(
                operation_context,
                phase="PLACE",
                status="FAILED",
                error=e,
            )

            raise PostPlaceError(str(e)) from e


    # =========================================================
    # Post 설치 확인
    # =========================================================

    def check_post(
        self,
        parameters,
        operation_context=None,
    ):
        self.node.get_logger().info(
            "========== POST CHECK START =========="
        )

        self._publish_post_event(
            operation_context,
            phase="CHECK",
            status="STARTED",
        )

        try:
            result = self.motion.check_force_move(
                label="POST CHECK",
            )

            if result:
                self.node.get_logger().info(
                    "========== POST CHECK COMPLETE =========="
                )

                self._publish_post_event(
                    operation_context,
                    phase="CHECK",
                    status="COMPLETED",
                )
                return True

            error_message = (
                "이동 범위 내 Force threshold 미감지"
            )

            self.node.get_logger().error(
                "========== POST CHECK FAILED =========="
            )

            self._publish_post_event(
                operation_context,
                phase="CHECK",
                status="FAILED",
                error=error_message,
            )
            return False

        except Exception as e:
            self.node.get_logger().error(
                f"Post Check 실행 오류: {e}"
            )
            self._publish_post_event(
                operation_context,
                phase="CHECK",
                status="FAILED",
                error=e,
            )
            raise


    # =========================================================
    # 전체 Post 설치 공정
    # =========================================================

    def install_post(
        self,
        parameters,
        components,
        operation_context=None,
    ):
        self.node.get_logger().info(
            "========== POST INSTALL START =========="
        )

        try:
            self.pick_post(
                parameters,
                components,
                operation_context=operation_context,
            )

            retreat_distance = self.place_post(
                parameters,
                components,
                operation_context=operation_context,
            )

            if not self.check_post(
                parameters,
                operation_context=operation_context,
            ):
                raise PostPlaceError(
                    "Post 설치 확인 실패"
                )

            self.node.get_logger().info(
                "Post Check 완료 -> Gripper Release"
            )
            self.motion.release()
            self.wait(0.5)

            speed = self._require_number(
                parameters, "speed"
            )
            acc = self._require_number(
                parameters, "acceleration"
            )

            self.node.get_logger().info(
                f"Post Release 완료 -> "
                f"BASE +Z {retreat_distance}mm 이탈"
            )
            self.motion.move_z(
                retreat_distance,
                ref=self.DR_BASE,
                velocity=speed,
                acc=acc,
            )

            self.wait(0.5)

            self.node.get_logger().info(
                "========== POST INSTALL COMPLETE =========="
            )
            return True

        except PostPickError as e:
            self.node.get_logger().error(
                f"Post Install 실패 - PICK 단계: {e}"
            )
            raise

        except PostPlaceError as e:
            self.node.get_logger().error(
                "Post Install 실패 - "
                f"PLACE/CHECK 단계: {e}"
            )
            raise

        except Exception as e:
            self.node.get_logger().error(
                f"Post Install 알 수 없는 오류: {e}"
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

            # post와 동일한 Force Place 사용
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
            4. post Check와 동일한 방식으로 TOOL Z 방향 이동
            5. 이동 중 실제 |F_tool_z| >= force_threshold이면 즉시 정지/성공
            6. 최대 거리까지 미감지 시 현재 위치에서 ERROR/실패

        현재 post_place / pin_place 자세와 동일하게
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
    # 전체 Solar 작업 - 레거시 직접 테스트용
    # =========================================================

    def run(
        self,
        parameters,
        components,
        operation_context=None,
    ):
        try:
            self.node.get_logger().info(
                "========== SOLAR MOTION START =========="
            )

            self.motion.move_home()
            self.wait(1.0)

            self.install_post(
                parameters,
                components,
                operation_context=operation_context,
            )
            self.wait(1.0)

            self.install_pin()

            self.motion.move_home()

            self.node.get_logger().info(
                "========== SOLAR MOTION COMPLETE =========="
            )

            return True

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

            raise