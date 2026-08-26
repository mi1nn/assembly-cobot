class PostPickError(Exception):
    pass


class PostPlaceError(Exception):
    pass


class PinPickError(Exception):
    pass


class PinPlaceError(Exception):
    pass


class SnapfitPickError(Exception):
    pass


class SnapfitPlaceError(Exception):
    pass


class FramePickError(Exception):
    pass


class FramePlaceError(Exception):
    pass


class PostCycleError(Exception):
    pass


class SolarMotion:
    """DB 최종 계약에 맞춘 Post 1개 설치 Cycle.

    operation.parameter
        DB 전체를 검증하지 않는다. 각 Pick/Place 단계가 실제로 필요한 값만
        실행 시점에 선택적으로 읽는다. 현재 사용하는 키:
            speed, acceleration, pick_distance, place_retreat_distance,
            place_search_limit_z, post_place_force, post_contact_force,
            post_insert_force, place_stiffness_z, place_search_velocity,
            place_search_acceleration, place_search_timeout

        아래 메타데이터는 DB에 존재해도 Post Motion에서는 사용하지 않는다.
            tcp, ucs, tool, fixture, coordinate_system

    operation.components
        CMP-POST-*   : pickup_position / assembly_position
        PIN-A-*      : pickup_position / assembly_position
        SNAPFIT-A-*  : pickup_position / assembly_position
        CMP-FRAME-*   : pickup_position / assembly_position

    좌표/안전거리 정책:
        - PIN은 기존 실험 코드를 유지한다.
        - POST/FRAME/SNAPFIT의 pickup_position / assembly_position은 실제 작업 좌표다.
        - pick_distance / place_retreat_distance는 안전 접근/복귀 거리로 사용한다.

    Post place alignment는 코드 내부 정책으로 고정한다.
        - 첫 접촉: TOOL +Z
        - 1차 Contact Seek 완료 후 BASE Z < 182mm이면 이미 정상 진입으로 판단
          -> 25-point Search를 생략하고 현재 위치에서 바로 최종 삽입
        - BASE Z >= 182mm이면 X/Y 5x5 격자 탐색
          X/Y = -0.6, -0.3, 0.0, +0.3, +0.6 mm (총 25개 후보)
        - score = side_force_delta / max(travel_mm, 0.1)
        - score가 가장 작은 유효 후보의 실제 BASE 절대 pose로 복귀 후 최종 삽입
    """

    POST_COMPONENT_PREFIX = "CMP-POST-"
    PIN_COMPONENT_PREFIX = "PIN-A-"
    SNAPFIT_COMPONENT_PREFIX = "SNAPFIT-A-"
    FRAME_COMPONENT_PREFIX = "CMP-FRAME-"

    # FRAME Pick/Place 공통 movec 경유점 (BASE 절대좌표)
    FRAME_MOVEC_VIA = (
        -46.4,
        472.47,
        343.52,
        95.74,
        179.17,
        9.5,
    )

    # FRAME Place: 정확한 assembly_position 도달 후 BASE -Z 방향으로 Force Place.
    FRAME_PLACE_FORCE_AXIS = "z"
    FRAME_PLACE_FORCE_DIRECTION = -1
    FRAME_PLACE_FORCE_REFERENCE = "base"

    # FRAME Release 후 TOOL Z축 기준 Spiral은 place_frame()에서 고정값으로 사용한다.
    # Outward 2.5회 + Inward 2.5회, 최대 반경 50mm, 축방향 이동 0mm.

    POST_INSERT_DIRECTION = 1       # TOOL +Z

    # PIN은 기존 설계를 유지한다.
    PIN_INSERT_AXIS = "x"
    PIN_INSERT_DIRECTION = 1        # TOOL +X
    PIN_INSERT_REFERENCE = "tool"

    # SNAPFIT은 TOOL +Z 방향으로 Force 삽입한다.
    SNAPFIT_INSERT_AXIS = "z"
    SNAPFIT_INSERT_DIRECTION = 1    # TOOL +Z
    SNAPFIT_INSERT_REFERENCE = "tool"

    CONTACT_THRESHOLD_N = 5.0
    CONTACT_POLL_INTERVAL = 0.02
    CONTACT_ARM_DELAY = 0.15
    CONTACT_DEFAULT_MAX_TRAVEL_MM = 150.0

    # 최적 위치 선정 후 POST 본 삽입 완료 조건
    POST_FINAL_CONTACT_THRESHOLD_N = 20.0
    POST_FINAL_CONTACT_HOLD_SEC = 0.50

    # 1차 Contact Seek에서 이 BASE Z 아래까지 이미 내려갔다면
    # 포스트가 정상적으로 구멍에 진입한 것으로 보고 25-point Search를 생략한다.
    DIRECT_INSERT_BASE_Z_THRESHOLD_MM = 190.0

    SEARCH_X_OFFSETS_MM = (-0.6, -0.3, 0.0, 0.3, 0.6)
    SEARCH_Y_OFFSETS_MM = (-0.6, -0.3, 0.0, 0.3, 0.6)
    SEARCH_RETRACT_MM = 3.0
    SEARCH_PROBE_TIME_SEC = 0.30
    SEARCH_PROBE_MAX_TRAVEL_MM = 2.0
    SEARCH_MIN_TRAVEL_MM = 0.30
    SEARCH_POLL_INTERVAL = 0.02

    def __init__(self, node):
        self.node = node

        from DSR_ROBOT2 import (
            movel,
            movec,
            move_spiral,
            posx,
            trans,
            wait,
            DR_BASE,
            DR_TOOL,
            DR_AXIS_Z,
            DR_SPIRAL_OUTWARD,
            DR_SPIRAL_INWARD,
            DR_ROT_FORWARD,
        )
        from .robot_motion import RobotMotion

        self.movel = movel
        self.movec = movec
        self.move_spiral = move_spiral
        self.posx = posx
        self.trans = trans
        self.wait = wait
        self.DR_BASE = DR_BASE
        self.DR_TOOL = DR_TOOL
        self.DR_AXIS_Z = DR_AXIS_Z
        self.DR_SPIRAL_OUTWARD = DR_SPIRAL_OUTWARD
        self.DR_SPIRAL_INWARD = DR_SPIRAL_INWARD
        self.DR_ROT_FORWARD = DR_ROT_FORWARD

        self.motion = RobotMotion()
        self.force = self.motion.force

    # =========================================================
    # DB helpers
    # =========================================================

    def _require_key(self, parameters, key):
        if not isinstance(parameters, dict):
            raise ValueError("parameters는 dict여야 합니다.")
        if key not in parameters:
            raise ValueError(f"Post 동작에 필요한 DB parameter 누락: {key}")
        return parameters[key]

    def _require_number(self, parameters, key):
        value = self._require_key(parameters, key)
        if isinstance(value, bool) or value is None:
            raise ValueError(f"DB parameter {key}는 숫자여야 합니다: {value}")
        try:
            return float(value)
        except (TypeError, ValueError) as e:
            raise ValueError(f"DB parameter {key}는 숫자여야 합니다: {value}") from e

    def _optional_number(self, parameters, key, default=None):
        """키가 없거나 null이면 default를 반환한다.

        최종 DB에 있는 메타데이터/선택 필드 때문에 Post 동작이 실패하지 않도록
        실제로 필요한 선택 파라미터만 느슨하게 읽는다.
        """
        if not isinstance(parameters, dict):
            raise ValueError("parameters는 dict여야 합니다.")
        if key not in parameters or parameters[key] is None:
            return default

        value = parameters[key]
        if isinstance(value, bool):
            raise ValueError(f"DB parameter {key}는 숫자 또는 null이어야 합니다.")
        try:
            return float(value)
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"DB parameter {key}는 숫자 또는 null이어야 합니다: {value}"
            ) from e

    def _first_number(self, parameters, keys, default=None, *, positive=False, nonnegative=False):
        """여러 DB 키 중 처음 존재하는 숫자를 사용한다.

        최종 DB 키를 keys의 첫 번째에 두고, 뒤에는 과도기/구버전 alias를 둔다.
        모든 키가 없으면 default를 사용한다. 따라서 사용하지 않는/아직 이관되지 않은
        DB 필드 때문에 전체 Post Cycle이 중단되지 않는다.
        """
        if not isinstance(parameters, dict):
            raise ValueError("parameters는 dict여야 합니다.")

        used_key = None
        value = default
        for key in keys:
            if key in parameters and parameters[key] is not None:
                used_key = key
                value = parameters[key]
                break

        if value is None:
            return None
        if isinstance(value, bool):
            raise ValueError(f"DB parameter {used_key or keys[0]}는 숫자여야 합니다.")
        try:
            value = float(value)
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"DB parameter {used_key or keys[0]}는 숫자여야 합니다: {value}"
            ) from e

        if positive and value <= 0:
            raise ValueError(f"{used_key or keys[0]}은 0보다 커야 합니다.")
        if nonnegative and value < 0:
            raise ValueError(f"{used_key or keys[0]}은 0 이상이어야 합니다.")
        return value

    def _positive_number(self, parameters, key):
        value = self._require_number(parameters, key)
        if value <= 0:
            raise ValueError(f"{key}은 0보다 커야 합니다.")
        return value

    def _nonnegative_number(self, parameters, key):
        value = self._require_number(parameters, key)
        if value < 0:
            raise ValueError(f"{key}은 0 이상이어야 합니다.")
        return value

    def _load_travel_settings(self, parameters):
        """일반 이동에 필요한 값. 최종 DB 키 우선, 누락 시 안전 기본값."""
        return {
            "speed": self._first_number(parameters, ("speed",), 100.0, positive=True),
            "acc": self._first_number(parameters, ("acceleration",), 200.0, positive=True),
        }

    def _load_pick_settings(self, parameters):
        """POST/PIN Pick에 실제로 필요한 값만 읽는다."""
        settings = self._load_travel_settings(parameters)
        settings["pick_distance"] = self._first_number(
            parameters, ("pick_distance", "post_pick_distance"), 50.0, positive=True
        )
        return settings

    def _load_post_place_settings(self, parameters):
        """POST 접촉 탐색/정렬/삽입 설정.

        최종 DB 이름을 최우선으로 사용한다. 현재 DB가 이관 중이라 해당 키가
        아직 없으면 기존 post_* 키 또는 코드 기본값으로 동작한다.
        """
        settings = self._load_travel_settings(parameters)
        settings.update(
            {
                "retreat_distance": self._first_number(
                    parameters,
                    ("place_retreat_distance", "post_place_retreat_distance"),
                    50.0,
                    nonnegative=True,
                ),
                # POST 최종 본 삽입 Desired Force
                "place_force": self._first_number(
                    parameters, ("post_place_force",), 40.0, positive=True
                ),
                # POST 최초 접촉을 찾기 위한 약한 Desired Force
                "contact_seek_force": self._first_number(
                    parameters, ("post_contact_force",), 20.0, positive=True
                ),
                # 최종 삽입 성공 판정은 코드 정책으로 분리한다.
                # post_contact_force는 최초 Contact Seek 용도이며 여기 재사용하지 않는다.
                "final_contact_threshold": self.POST_FINAL_CONTACT_THRESHOLD_N,
                "final_contact_hold_sec": self.POST_FINAL_CONTACT_HOLD_SEC,
                # POST 각 위치 후보에서 사용하는 Probe/Search Force
                "insert_force": self._first_number(
                    parameters, ("post_insert_force",), 12.0, positive=True
                ),
                "stiffness_z": self._first_number(
                    parameters, ("place_stiffness_z",), 500.0, positive=True
                ),
                "search_velocity": self._first_number(
                    parameters, ("place_search_velocity", "post_search_velocity"), 10.0, positive=True
                ),
                "search_acc": self._first_number(
                    parameters, ("place_search_acceleration",), 20.0, positive=True
                ),
                "direct_insert_base_z_threshold": self._first_number(
                    parameters,
                    ("place_direct_insert_base_z_threshold",),
                    self.DIRECT_INSERT_BASE_Z_THRESHOLD_MM,
                ),
            }
        )

        # 최종 키가 0.0이면 '별도 제한값 없음'으로 해석 -> 코드 안전 한계 150mm.
        search_limit_z_raw = self._first_number(
            parameters,
            ("place_search_limit_z", "post_contact_max_travel"),
            0.0,
            nonnegative=True,
        )
        settings["search_limit_z"] = (
            self.CONTACT_DEFAULT_MAX_TRAVEL_MM
            if search_limit_z_raw == 0.0
            else search_limit_z_raw
        )

        # null/누락이면 시간 제한 없음. legacy timeout이 있으면 호환해서 읽는다.
        settings["search_timeout"] = self._first_number(
            parameters, ("place_search_timeout", "post_contact_timeout"), None, positive=True
        )
        return settings

    def _load_pin_pick_settings(self, parameters):
        """얇은 PIN(PIN-A-*) Pick 설정."""
        settings = self._load_travel_settings(parameters)
        settings["pick_distance"] = self._first_number(
            parameters,
            ("pin_pick_distance", "pick_distance"),
            50.0,
            positive=True,
        )
        return settings

    def _load_snapfit_pick_settings(self, parameters):
        """SNAPFIT-A-* Pick 설정. 기존 POST_PIN용 키도 호환한다."""
        settings = self._load_travel_settings(parameters)
        settings["pick_distance"] = self._first_number(
            parameters,
            ("snapfit_pick_distance", "post_pin_pick_distance", "pick_distance"),
            50.0,
            positive=True,
        )
        return settings

    def _load_pin_place_settings(self, parameters):
        """얇은 PIN(PIN-A-*) Force Place 설정."""
        settings = self._load_travel_settings(parameters)
        settings.update(
            {
                "retreat_distance": self._first_number(
                    parameters,
                    ("pin_place_retreat_distance", "place_retreat_distance"),
                    30.0,
                    nonnegative=True,
                ),
                "place_force": self._first_number(
                    parameters,
                    ("pin_place_force", "place_force"),
                    20.0,
                    positive=True,
                ),
                "contact_force": self._first_number(
                    parameters,
                    ("pin_place_force_threshold", "place_contact_force"),
                    10.0,
                    positive=True,
                ),
                "stiffness": self._first_number(
                    parameters,
                    ("pin_place_stiffness_x",),
                    500.0,
                    positive=True,
                ),
                "timeout": self._first_number(
                    parameters,
                    ("pin_place_timeout",),
                    10.0,
                    positive=True,
                ),
            }
        )
        return settings

    def _load_frame_settings(self, parameters):
        """FRAME(CMP-FRAME-*) Pick/Place 이동/Force/Spiral 설정.

        pickup_position / assembly_position:
            실제 Pick/Place 작업 좌표.

        pick_distance / place_distance:
            실제 작업 좌표에서 BASE +Z 방향으로 떨어진 안전 접근 거리.

        FRAME 이동:
            공통 FRAME_MOVEC_VIA를 경유하는 movec() 사용.

        FRAME Place:
            assembly_position 도달 후 BASE -Z Force Place.
            측정 Force threshold는 frame_place_force_threshold를 사용한다.
            Release 후 TOOL Z축 기준 Spiral을 고정값으로 수행하고
            중심으로 복귀한 뒤 상승한다.
        """
        settings = self._load_travel_settings(parameters)

        settings["pick_distance"] = self._first_number(
            parameters,
            ("frame_pick_distance", "pick_distance"),
            50.0,
            nonnegative=True,
        )

        settings["place_distance"] = self._first_number(
            parameters,
            ("frame_place_distance", "place_distance", "place_retreat_distance"),
            50.0,
            nonnegative=True,
        )

        # FRAME 전용 Desired Force.
        settings["place_force"] = self._first_number(
            parameters,
            ("frame_place_force",),
            30.0,
            positive=True,
        )

        # FRAME에서 측정 Force가 이 값 이상이면 Place 성공으로 판단.
        settings["contact_force"] = self._first_number(
            parameters,
            ("frame_place_force_threshold",),
            10.0,
            positive=True,
        )

        settings["stiffness_z"] = self._first_number(
            parameters,
            ("frame_place_stiffness_z", "place_stiffness_z"),
            500.0,
            positive=True,
        )

        settings["force_timeout"] = self._first_number(
            parameters,
            ("frame_place_timeout",),
            10.0,
            positive=True,
        )

        # Spiral 파라미터는 DB에서 읽지 않는다.
        # place_frame()에서 고정값으로 사용한다.

        return settings

    def _load_snapfit_place_settings(self, parameters):
        """SNAPFIT-A-* Place 설정.

        assembly_position은 실제 Place/Force 시작 좌표다.
        place_distance는 해당 좌표에서 TOOL -Z 방향으로 떨어진 안전 접근 거리다.
        """
        settings = self._load_travel_settings(parameters)
        settings.update(
            {
                "place_distance": self._first_number(
                    parameters,
                    (
                        "snapfit_place_distance",
                        "place_distance",
                        "snapfit_place_retreat_distance",
                        "place_retreat_distance",
                        "post_place_retreat_distance",
                    ),
                    30.0,
                    nonnegative=True,
                ),
                "place_force": self._first_number(
                    parameters,
                    (
                        "snapfit_place_force",
                        "post_pin_place_force",
                        "place_force",
                        "post_place_force",
                    ),
                    40.0,
                    positive=True,
                ),
                "contact_force": self._first_number(
                    parameters,
                    (
                        "snapfit_place_force_threshold",
                        "post_pin_place_force_threshold",
                        "place_contact_force",
                        "post_place_force_threshold",
                    ),
                    20.0,
                    positive=True,
                ),
                "stiffness": self._first_number(
                    parameters,
                    (
                        "snapfit_place_stiffness_z",
                        "snapfit_place_stiffness_x",
                    ),
                    500.0,
                    positive=True,
                ),
                "timeout": self._first_number(
                    parameters,
                    ("snapfit_place_timeout",),
                    10.0,
                    positive=True,
                ),
            }
        )
        return settings

    # =========================================================
    # Components
    # =========================================================

    def _get_component(self, components, prefix, label):
        if not isinstance(components, list):
            raise ValueError("components는 list여야 합니다.")

        for component in components:
            if not isinstance(component, dict):
                continue
            code = str(component.get("code", "")).strip()
            if code.startswith(prefix):
                return component

        raise ValueError(
            f"{label} component를 찾을 수 없습니다. code prefix={prefix}"
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
            raise ValueError(f"{label} 필드 누락: " + ", ".join(missing))

        values = []
        for key in ("x", "y", "z", "A", "B", "C"):
            try:
                values.append(float(position[key]))
            except (TypeError, ValueError) as e:
                raise ValueError(f"{label}.{key}는 숫자여야 합니다.") from e

        return self.posx(values)

    def _pickup_input(self, components, prefix, label):
        """Pick 단계에서는 pickup_position만 요구한다."""
        component = self._get_component(components, prefix, label)
        if "pickup_position" not in component:
            raise ValueError(
                f"{label}({component.get('code')}) pickup_position 누락"
            )
        pickup = self._position_to_posx(
            component["pickup_position"], f"{label}.pickup_position"
        )
        return component, pickup

    def _assembly_input(self, components, prefix, label):
        """Place 단계에서는 assembly_position만 요구한다."""
        component = self._get_component(components, prefix, label)
        if "assembly_position" not in component:
            raise ValueError(
                f"{label}({component.get('code')}) assembly_position 누락"
            )
        assembly = self._position_to_posx(
            component["assembly_position"], f"{label}.assembly_position"
        )
        return component, assembly

    def _post_pickup_input(self, components):
        return self._pickup_input(
            components, self.POST_COMPONENT_PREFIX, "POST"
        )

    def _post_assembly_input(self, components):
        return self._assembly_input(
            components, self.POST_COMPONENT_PREFIX, "POST"
        )

    def _pin_pickup_input(self, components):
        return self._pickup_input(
            components, self.PIN_COMPONENT_PREFIX, "PIN"
        )

    def _pin_assembly_input(self, components):
        return self._assembly_input(
            components, self.PIN_COMPONENT_PREFIX, "PIN"
        )

    def _snapfit_pickup_input(self, components):
        return self._pickup_input(
            components, self.SNAPFIT_COMPONENT_PREFIX, "SNAPFIT"
        )

    def _snapfit_assembly_input(self, components):
        return self._assembly_input(
            components, self.SNAPFIT_COMPONENT_PREFIX, "SNAPFIT"
        )

    def _frame_pickup_input(self, components):
        return self._pickup_input(
            components, self.FRAME_COMPONENT_PREFIX, "FRAME"
        )

    def _frame_assembly_input(self, components):
        return self._assembly_input(
            components, self.FRAME_COMPONENT_PREFIX, "FRAME"
        )

    # =========================================================
    # System event
    # =========================================================

    def _publish_cycle_event(
        self,
        operation_context,
        *,
        phase,
        status,
        error=None,
        detail=None,
    ):
        if not operation_context:
            return

        operation_code = str(operation_context.get("operation_code", "")).strip()
        if not operation_code:
            return

        phase = str(phase).strip().upper()
        status = str(status).strip().upper()
        event_code = f"{phase}_{status}"

        if status == "FAILED":
            severity = getattr(self.node, "SEVERITY_ERROR", 2)
            message = f"[{operation_code}] {phase} failed"
        elif status == "COMPLETED":
            severity = getattr(self.node, "SEVERITY_INFO", 0)
            message = f"[{operation_code}] {phase} completed"
        else:
            severity = getattr(self.node, "SEVERITY_INFO", 0)
            message = f"[{operation_code}] {phase} started"

        detail_data = {
            "operation_code": operation_code,
            "phase": phase,
            "status": status,
        }
        for key in ("work_order_id", "operation_id", "robot_id"):
            value = operation_context.get(key)
            if value is not None:
                detail_data[key] = value
        if isinstance(detail, dict):
            detail_data.update(detail)
        if error is not None:
            detail_data["error"] = str(error)
            message = f"{message}: {error}"

        try:
            self.node.publish_system_event(
                severity,
                event_code,
                message,
                work_execution_id=int(
                    operation_context.get("work_execution_id", 0) or 0
                ),
                operation_execution_id=int(
                    operation_context.get("operation_execution_id", 0) or 0
                ),
                operation_code=operation_code,
                phase=phase,
                status=status,
                detail=detail_data,
            )
        except Exception as log_error:
            self.node.get_logger().warning(
                f"Post Cycle SystemEvent 발행 실패: {log_error}"
            )

    # =========================================================
    # POST PICK
    # =========================================================

    def pick_post(self, parameters, components, operation_context=None):
        """POST를 정확한 pickup_position에서 파지한다.

        pickup_position:
            실제 Gripper Close가 수행되는 정확한 Pick 좌표.

        pick_distance:
            pickup_position에서 BASE +Z 방향으로 떨어진 안전 접근 거리.

        순서:
            Safe Pick
            -> pickup_position
            -> Grasp
            -> Safe Pick 복귀
        """
        self.node.get_logger().info("========== POST PICK START ==========")
        self._publish_cycle_event(
            operation_context, phase="POST_PICK", status="STARTED"
        )

        try:
            settings = self._load_pick_settings(parameters)
            component, pickup_pose = self._post_pickup_input(components)

            pick_distance = settings["pick_distance"]

            # DB pickup_position 자체가 실제 파지 좌표다.
            safe_pick_pose = self.posx([
                float(pickup_pose[0]),
                float(pickup_pose[1]),
                float(pickup_pose[2]) + pick_distance,
                float(pickup_pose[3]),
                float(pickup_pose[4]),
                float(pickup_pose[5]),
            ])

            # 1. Pick 안전 접근점
            self.node.get_logger().info(
                "POST Pick 안전 접근 - "
                f"component={component.get('code')}, "
                f"BASE Z +{pick_distance:.1f}mm"
            )
            self.movel(
                safe_pick_pose,
                vel=settings["speed"],
                acc=settings["acc"],
                ref=self.DR_BASE,
            )
            self.wait(0.5)

            # 2. 정확한 Pick 위치
            self.node.get_logger().info(
                "POST 정확한 Pick 위치 이동"
            )
            self.movel(
                pickup_pose,
                vel=settings["speed"],
                acc=settings["acc"],
                ref=self.DR_BASE,
            )
            self.wait(0.2)

            # 3. 파지
            self.node.get_logger().info("POST Gripper Close")
            self.motion.grasp()
            self.wait(0.2)

            # 4. 동일한 안전 접근점으로 복귀
            self.node.get_logger().info(
                "POST Pick 완료 -> 안전 접근점 복귀"
            )
            self.movel(
                safe_pick_pose,
                vel=settings["speed"],
                acc=settings["acc"],
                ref=self.DR_BASE,
            )
            self.wait(0.5)

            self.node.get_logger().info(
                "========== POST PICK COMPLETE =========="
            )
            self._publish_cycle_event(
                operation_context,
                phase="POST_PICK",
                status="COMPLETED",
                detail={
                    "component_code": component.get("code"),
                    "pick_distance": pick_distance,
                    "safe_reference": "BASE_Z",
                },
            )
            return True

        except Exception as e:
            self.node.get_logger().error(f"Post Pick 실패: {e}")
            self._publish_cycle_event(
                operation_context, phase="POST_PICK", status="FAILED", error=e
            )
            raise PostPickError(str(e)) from e

    # =========================================================
    # POST alignment search
    # =========================================================

    def _search_post_alignment(self, settings, *, origin_pose, direction):
        """접촉 P0 주변에서 TOOL X/Y 후보를 force probe하여 최적점을 선택한다."""
        x_offsets = self.SEARCH_X_OFFSETS_MM
        candidates = []
        for x_offset in x_offsets:
            for y_offset in self.SEARCH_Y_OFFSETS_MM:
                label = f"TOOL_X{x_offset:+g}_Y{y_offset:+g}"
                candidates.append((label, x_offset, y_offset))

        self.node.get_logger().info(
            "========== POST ALIGNMENT SEARCH START =========="
        )
        self.node.get_logger().info(f"Search origin P0={origin_pose}")
        self.node.get_logger().info(
            "Search candidates: TOOL X=-0.6,-0.3,0,+0.3,+0.6mm; "
            "TOOL Y=-0.6,-0.3,0,+0.3,+0.6mm; total=25"
        )

        # 접촉 평면에서 안전 평면으로 3mm 이탈.
        self.motion.move_z(
            -direction * self.SEARCH_RETRACT_MM,
            ref=self.DR_TOOL,
            velocity=settings["search_velocity"],
            acc=settings["search_acc"],
        )
        self.wait(0.2)

        current_x = 0.0
        current_y = 0.0
        best = None
        results = []

        for label, offset_x, offset_y in candidates:
            dx = offset_x - current_x
            dy = offset_y - current_y
            if abs(dx) > 1e-9 or abs(dy) > 1e-9:
                self.motion.move_xy(
                    dx,
                    dy,
                    ref=self.DR_TOOL,
                    velocity=settings["search_velocity"],
                    acc=settings["search_acc"],
                )
                self.wait(0.2)
            current_x = offset_x
            current_y = offset_y

            # 현재 후보의 안전 평면 실제 BASE pose를 먼저 저장한다.
            # Probe/retract 중 누적된 상대 이동 오차가 있더라도 마지막에
            # best 후보의 절대 위치로 정확히 복귀하기 위해 사용한다.
            candidate_safe_pose, safe_solution_space = self.motion.get_current_pose(
                ref=self.DR_BASE
            )

            # 후보의 접촉 평면으로 접근.
            self.motion.move_z(
                direction * self.SEARCH_RETRACT_MM,
                ref=self.DR_TOOL,
                velocity=settings["search_velocity"],
                acc=settings["search_acc"],
            )
            self.wait(0.2)

            candidate_pose, solution_space = self.motion.get_current_pose(
                ref=self.DR_BASE
            )
            self.node.get_logger().info(
                f"[SEARCH] 후보={label}, tool_offset_x={offset_x:.3f}mm, "
                f"tool_offset_y={offset_y:.3f}mm, pose={candidate_pose}, "
                f"solution_space={solution_space}"
            )

            probe = self.motion.probe_force(
                axis="z",
                direction=direction,
                force=settings["insert_force"],
                probe_time=self.SEARCH_PROBE_TIME_SEC,
                max_travel=self.SEARCH_PROBE_MAX_TRAVEL_MM,
                poll_interval=self.SEARCH_POLL_INTERVAL,
                stiffness={"z": settings["stiffness_z"]},
            )

            travel_mm = float(probe["travel_mm"])
            side_force = float(probe["side_force_delta"])
            score = side_force / max(travel_mm, 0.1)
            blocked_by_baseline = bool(probe.get("blocked_by_baseline", False))
            valid = (not blocked_by_baseline) and travel_mm >= self.SEARCH_MIN_TRAVEL_MM

            result = {
                "label": label,
                "pose": list(candidate_pose),
                "safe_pose": list(candidate_safe_pose),
                "offset_x": float(offset_x),
                "offset_y": float(offset_y),
                "travel_mm": travel_mm,
                "side_force_delta": side_force,
                "axis_force_delta": float(probe["axis_force_delta"]),
                "score": float(score),
                "valid": bool(valid),
                "blocked_by_baseline": blocked_by_baseline,
            }
            results.append(result)

            self.node.get_logger().info(
                f"[SEARCH] {label}: travel={travel_mm:.3f}mm, "
                f"side_force_delta={side_force:.3f}N, score={score:.3f}, "
                f"valid={valid}, blocked_by_baseline={blocked_by_baseline}"
            )

            if valid and (best is None or score < best["score"]):
                best = result

            # probe 이동량까지 포함해서 동일 안전 평면으로 복귀.
            restore = self.SEARCH_RETRACT_MM + travel_mm
            self.motion.move_z(
                -direction * restore,
                ref=self.DR_TOOL,
                velocity=settings["search_velocity"],
                acc=settings["search_acc"],
            )
            self.wait(0.2)

        if best is None:
            summary = "; ".join(
                f"{item['label']}:travel={item['travel_mm']:.2f},"
                f"side={item['side_force_delta']:.2f}"
                for item in results
            )
            raise RuntimeError(
                "Post Alignment Search 실패 - "
                f"travel >= {self.SEARCH_MIN_TRAVEL_MM:.2f}mm 후보가 없습니다. "
                f"결과: {summary}"
            )

        self.node.get_logger().info(
            "========== POST ALIGNMENT SEARCH BEST =========="
        )
        self.node.get_logger().info(
            f"best={best['label']}, X={best['offset_x']:.3f}mm, "
            f"Y={best['offset_y']:.3f}mm, travel={best['travel_mm']:.3f}mm, "
            f"side={best['side_force_delta']:.3f}N, score={best['score']:.3f}"
        )

        # 25개 Probe가 모두 끝난 뒤, 마지막 후보의 상대 위치를 기준으로
        # 계산하지 않고 best 후보에서 실제 측정해 저장한 BASE 절대 pose로
        # 명시적으로 복귀한다. 이렇게 해야 Probe/Compliance 과정에서 생긴
        # 누적 위치 오차 때문에 마지막 후보에서 바로 삽입되는 현상을 막을 수 있다.
        self.node.get_logger().info(
            f"[SEARCH] BEST 안전 위치 절대 복귀: {best['safe_pose']}"
        )
        self.motion.move_pose(
            best["safe_pose"],
            ref=self.DR_BASE,
            velocity=settings["search_velocity"],
            acc=settings["search_acc"],
        )
        self.wait(0.2)

        self.node.get_logger().info(
            f"[SEARCH] BEST 접촉 위치 절대 복귀: {best['pose']}"
        )
        self.motion.move_pose(
            best["pose"],
            ref=self.DR_BASE,
            velocity=settings["search_velocity"],
            acc=settings["search_acc"],
        )
        self.wait(0.3)

        best_now_pose, best_now_solution_space = self.motion.get_current_pose(
            ref=self.DR_BASE
        )
        self.node.get_logger().info(
            f"[SEARCH] BEST 복귀 완료 actual_pose={best_now_pose}, "
            f"solution_space={best_now_solution_space}"
        )

        return list(best_now_pose), best

    # =========================================================
    # POST PLACE
    # =========================================================

    def place_post(self, parameters, components, operation_context=None):
        self.node.get_logger().info("========== POST PLACE START ==========")
        self._publish_cycle_event(
            operation_context, phase="POST_PLACE", status="STARTED"
        )

        try:
            settings = self._load_post_place_settings(parameters)
            component, assembly_pose = self._post_assembly_input(components)
            direction = self.POST_INSERT_DIRECTION
            direction_label = "+Z" if direction > 0 else "-Z"

            place_distance = settings["retreat_distance"]

            # DB assembly_position 자체가 실제 Place/Force 시작 좌표다.
            safe_place_pose = self.posx([
                float(assembly_pose[0]),
                float(assembly_pose[1]),
                float(assembly_pose[2]) + place_distance,
                float(assembly_pose[3]),
                float(assembly_pose[4]),
                float(assembly_pose[5]),
            ])

            # 1. Place 안전 접근점
            self.node.get_logger().info(
                "POST Place 안전 접근 - "
                f"component={component.get('code')}, "
                f"BASE Z +{place_distance:.1f}mm"
            )
            self.movel(
                safe_place_pose,
                vel=settings["speed"],
                acc=settings["acc"],
                ref=self.DR_BASE,
            )
            self.wait(0.5)

            # 2. 정확한 Place/Force 시작 위치
            self.node.get_logger().info(
                "POST 정확한 assembly_position 이동"
            )
            self.movel(
                assembly_pose,
                vel=settings["speed"],
                acc=settings["acc"],
                ref=self.DR_BASE,
            )
            self.wait(0.2)

            contact = self.motion.seek_contact(
                axis="z",
                direction=direction,
                force=settings["contact_seek_force"],
                threshold=self.CONTACT_THRESHOLD_N,
                max_travel=settings["search_limit_z"],
                poll_interval=self.CONTACT_POLL_INTERVAL,
                arm_delay=self.CONTACT_ARM_DELAY,
                timeout=settings["search_timeout"],
                stiffness={"z": settings["stiffness_z"]},
            )

            self.wait(0.2)
            contact_pose, solution_space = self.motion.get_current_pose(
                ref=self.DR_BASE
            )
            self.node.get_logger().info(
                "========== POST CONTACT SEEK COMPLETE =========="
            )
            self.node.get_logger().info(
                f"Post Contact P0 pose={contact_pose}, solution_space={solution_space}, "
                f"seek_travel={contact['travel_mm']:.3f}mm, "
                f"contact_delta={contact['axis_force_delta']:.3f}N"
            )

            # 2) 첫 Contact Seek에서 이미 충분히 깊게 진입했는지 BASE Z로 판정.
            #    Z < 182mm이면 25-point Search를 생략하고 현재 위치에서 바로 최종 삽입한다.
            current_base_z = float(contact_pose[2])
            best = None
            direct_insert_threshold = settings[
                "direct_insert_base_z_threshold"
            ]

            search_skipped = (
                current_base_z < direct_insert_threshold
            )

            self.node.get_logger().info(
                "========== POST DIRECT INSERT CHECK =========="
                f"Contact BASE Z={current_base_z:.3f}mm, "
                f"threshold={direct_insert_threshold:.3f}mm, "
                f"search_skipped={search_skipped}"
            )

            if search_skipped:
                self.node.get_logger().info(
                    f"BASE Z={current_base_z:.3f}mm < "
                    f"{self.DIRECT_INSERT_BASE_Z_THRESHOLD_MM:.3f}mm "
                    "-> 이미 정상 진입으로 판단, 25-point Search SKIP"
                )
            else:
                self.node.get_logger().info(
                    f"BASE Z={current_base_z:.3f}mm >= "
                    f"{self.DIRECT_INSERT_BASE_Z_THRESHOLD_MM:.3f}mm "
                    "-> 25-point Alignment Search 실행"
                )

                # TOOL X/Y를 -0.6,-0.3,0,+0.3,+0.6mm 5x5 격자로 탐색.
                _, best = self._search_post_alignment(
                    settings, origin_pose=contact_pose, direction=direction
                )

            # 3) 최종 삽입. Search를 생략한 경우에는 현재 Contact 위치에서,
            #    Search를 실행한 경우에는 best 절대 pose로 복귀한 뒤 실행된다.
            #    place_force는 DB Desired Force를 사용하고, 완료 판정은
            #    코드 정책(Delta Fz 65N 이상 0.5초 연속 유지)으로 사용한다.
            self.node.get_logger().info(
                "Post 본 삽입 Force 시작 - "
                f"desired_force={settings['place_force']:.2f}N, "
                f"delta_threshold={settings['final_contact_threshold']:.2f}N, "
                f"hold={settings['final_contact_hold_sec']:.2f}s, timeout=DISABLED"
            )
            result = self.motion.place(
                axis="z",
                direction=direction,
                force=settings["place_force"],
                threshold=settings["final_contact_threshold"],
                timeout=None,
                hold_time=settings["final_contact_hold_sec"],
                stiffness={"z": settings["stiffness_z"]},
            )
            if not result:
                raise RuntimeError("Post TOOL Z Force Place가 성공을 반환하지 않았습니다.")

            self.wait(0.5)
            self.node.get_logger().info("========== POST PLACE COMPLETE ==========")

            detail = {
                "component_code": component.get("code"),
                "axis": "TOOL_Z",
                "direction": direction,
                "contact_seek_travel_mm": float(contact["travel_mm"]),
                "contact_axis_force_delta": float(contact["axis_force_delta"]),
                "contact_base_z": current_base_z,
                "search_skipped": bool(search_skipped),
                "place_distance": place_distance,
                "safe_reference": "BASE_Z",
            }
            if best is not None:
                detail.update(
                    {
                        "search_best": best["label"],
                        "search_offset_x": best["offset_x"],
                        "search_offset_y": best["offset_y"],
                        "search_score": best["score"],
                    }
                )

            self._publish_cycle_event(
                operation_context,
                phase="POST_PLACE",
                status="COMPLETED",
                detail=detail,
            )
            return settings["retreat_distance"]

        except Exception as e:
            self.node.get_logger().error(f"Post Place 실패: {e}")
            self._publish_cycle_event(
                operation_context, phase="POST_PLACE", status="FAILED", error=e
            )
            raise PostPlaceError(str(e)) from e

    # =========================================================
    # PIN PICK / PLACE
    # =========================================================

    def pick_pin(self, parameters, components, operation_context=None):
        """PIN-A-*를 지정된 pickup_position에서 집는다.

        pickup_position은 PIN 바로 위의 접근 위치로 사용한다.

        동작 순서:
            1. pickup_position보다 BASE Z +30mm 높은 위치로 이동
            2. pickup_position으로 이동
            3. BASE -Z 방향으로 pick_distance만큼 하강
            4. Gripper Close
            5. TOOL -X 방향으로 50mm 이동
            6. BASE +Z 방향으로 pick_distance만큼 상승
        """
        self.node.get_logger().info("========== PIN PICK START ==========")
        self._publish_cycle_event(
            operation_context, phase="PIN_PICK", status="STARTED"
        )

        try:
            settings = self._load_pin_pick_settings(parameters)
            component, pickup_pose = self._pin_pickup_input(components)

            pick_distance = settings["pick_distance"]

            # 1. pickup_position보다 BASE Z +30mm 높은 안전 접근점으로 이동
            pickup_safe_pose = self.posx([
                float(pickup_pose[0]),
                float(pickup_pose[1]),
                float(pickup_pose[2]) + 30.0,
                float(pickup_pose[3]),
                float(pickup_pose[4]),
                float(pickup_pose[5]),
            ])

            self.node.get_logger().info(
                f"PIN Pick 안전 접근 위치 이동 - "
                f"component={component.get('code')}, "
                f"BASE Z +30.0mm"
            )
            self.movel(
                pickup_safe_pose,
                vel=settings["speed"],
                acc=settings["acc"],
                ref=self.DR_BASE,
            )
            self.wait(0.5)

            # 2. DB의 pickup_position으로 이동
            self.node.get_logger().info(
                f"PIN Pick 위치 이동 - "
                f"pick_distance={pick_distance:.1f}mm"
            )
            self.movel(
                pickup_pose,
                vel=settings["speed"],
                acc=settings["acc"],
                ref=self.DR_BASE,
            )
            self.wait(0.5)

            # 3. PIN 위치까지 수직 하강
            self.node.get_logger().info(
                f"PIN Pick 하강 - BASE Z {-pick_distance:.1f}mm"
            )
            self.motion.move_z(
                -pick_distance,
                ref=self.DR_BASE,
                velocity=settings["speed"],
                acc=settings["acc"],
            )
            self.wait(0.2)

            # 4. PIN 파지
            self.node.get_logger().info("PIN Gripper Close")
            self.motion.grasp()
            self.wait(0.2)

            # 4. 파지 후 BASE +X 방향으로 50mm 이동
            self.node.get_logger().info(
                "PIN Pick 파지 후 이동 - TOOL X -50.0mm"
            )
            self.motion.move_x(
                -50.0,
                ref=self.DR_TOOL,
                velocity=settings["speed"],
                acc=settings["acc"],
            )
            self.wait(0.2)

            # 6. Z 방향으로 다시 상승
            self.node.get_logger().info(
                f"PIN Pick 상승 - BASE Z +{pick_distance:.1f}mm"
            )
            self.motion.move_z(
                pick_distance,
                ref=self.DR_BASE,
                velocity=settings["speed"],
                acc=settings["acc"],
            )
            self.wait(0.5)

            self.node.get_logger().info("========== PIN PICK COMPLETE ==========")
            self._publish_cycle_event(
                operation_context,
                phase="PIN_PICK",
                status="COMPLETED",
                detail={
                    "component_code": component.get("code"),
                    "pick_distance": pick_distance,
                },
            )
            return True

        except Exception as e:
            self.node.get_logger().error(f"PIN Pick 실패: {e}")
            self._publish_cycle_event(
                operation_context, phase="PIN_PICK", status="FAILED", error=e
            )
            raise PinPickError(str(e)) from e

    def place_pin(self, parameters, components, operation_context=None):
        """PIN-A-*를 TOOL +X 방향으로 두 번 밀어 넣는다.

        순서:
            place 위치 이동
            -> TOOL +X Force Push #1
            -> 반력 감지
            -> Gripper Release
            -> place 위치 복귀
            -> Gripper Close
            -> TOOL +X Force Push #2
            -> 반력 감지
        """
        self.node.get_logger().info("========== PIN PLACE START ==========")
        self._publish_cycle_event(
            operation_context, phase="PIN_PLACE", status="STARTED"
        )

        try:
            settings = self._load_pin_place_settings(parameters)
            component, assembly_pose = self._pin_assembly_input(components)

            self.node.get_logger().info(
                "PIN Place 설정 - "
                f"component={component.get('code')}, "
                f"reference=TOOL, axis=+X, "
                f"force={settings['place_force']:.2f}N, "
                f"threshold={settings['contact_force']:.2f}N"
            )

            # 1. place 위치
            self.node.get_logger().info(
                f"PIN Place 시작 위치 이동 - {component.get('code')}"
            )
            self.movel(
                assembly_pose,
                vel=settings["speed"],
                acc=settings["acc"],
                ref=self.DR_BASE,
            )
            self.wait(0.5)

            # 2. 1차 TOOL +X Force Push
            self.node.get_logger().info(
                "========== PIN PLACE 1ST PUSH START =========="
            )

            first_result = self.motion.place(
                axis=self.PIN_INSERT_AXIS,
                direction=self.PIN_INSERT_DIRECTION,
                force=settings["place_force"],
                threshold=settings["contact_force"],
                timeout=settings["timeout"],
                stiffness={
                    self.PIN_INSERT_AXIS: settings["stiffness"]
                },
                reference=self.PIN_INSERT_REFERENCE,
            )

            if not first_result:
                raise RuntimeError(
                    "PIN 1차 TOOL +X Force Place가 성공을 반환하지 않았습니다."
                )

            self.wait(0.2)

            # 3. 첫 반력 감지 후 PIN을 놓음
            self.node.get_logger().info(
                "PIN 1차 반력 감지 완료 -> Gripper Release"
            )
            self.motion.release()
            self.wait(0.5)

            # 4. 원래 place 위치로 복귀
            self.node.get_logger().info(
                "PIN 1차 삽입 완료 -> 원래 Place 위치 복귀"
            )
            self.movel(
                assembly_pose,
                vel=settings["speed"],
                acc=settings["acc"],
                ref=self.DR_BASE,
            )
            self.wait(0.5)

            # 5. 빈 Gripper를 닫아 Push 준비
            self.node.get_logger().info(
                "PIN 2차 Push 준비 -> Gripper Close"
            )
            self.motion.grasp()
            self.wait(0.5)

            # 6. 2차 TOOL +X Force Push
            self.node.get_logger().info(
                "========== PIN PLACE 2ND PUSH START =========="
            )

            second_result = self.motion.place(
                axis=self.PIN_INSERT_AXIS,
                direction=self.PIN_INSERT_DIRECTION,
                force=settings["place_force"],
                threshold=settings["contact_force"],
                timeout=settings["timeout"],
                stiffness={
                    self.PIN_INSERT_AXIS: settings["stiffness"]
                },
                reference=self.PIN_INSERT_REFERENCE,
            )

            if not second_result:
                raise RuntimeError(
                    "PIN 2차 TOOL +X Force Place가 성공을 반환하지 않았습니다."
                )

            self.wait(0.5)

            self.node.get_logger().info(
                "========== PIN PLACE COMPLETE =========="
            )
            self._publish_cycle_event(
                operation_context,
                phase="PIN_PLACE",
                status="COMPLETED",
                detail={
                    "component_code": component.get("code"),
                    "reference": "TOOL",
                    "axis": "TOOL_X",
                    "direction": self.PIN_INSERT_DIRECTION,
                    "push_count": 2,
                    "force": settings["place_force"],
                    "threshold": settings["contact_force"],
                },
            )
            return True

        except Exception as e:
            self.node.get_logger().error(f"PIN Place 실패: {e}")
            self._publish_cycle_event(
                operation_context,
                phase="PIN_PLACE",
                status="FAILED",
                error=e,
            )

            try:
                self.force.all_off()
            except Exception:
                pass

            raise PinPlaceError(str(e)) from e


    # =========================================================
    # FRAME PICK / PLACE
    # =========================================================

    def pick_frame(self, parameters, components, operation_context=None):
        """FRAME을 공통 경유점 기반 movec()로 접근해 정확한 위치에서 파지한다.

        pickup_position:
            실제 Gripper Close가 수행되는 정확한 Pick 좌표.

        frame_pick_distance / pick_distance:
            pickup_position에서 BASE +Z 방향으로 떨어진 안전 접근 거리.

        순서:
            Home
            -> movec(FRAME_MOVEC_VIA -> Safe Pick)
            -> movel(pickup_position)
            -> Grasp
            -> movel(Safe Pick)
        """
        self.node.get_logger().info("========== FRAME PICK START ==========")
        self._publish_cycle_event(
            operation_context, phase="FRAME_PICK", status="STARTED"
        )

        try:
            settings = self._load_frame_settings(parameters)
            component, pickup_pose = self._frame_pickup_input(components)

            pick_distance = settings["pick_distance"]

            safe_pick_pose = self.posx([
                float(pickup_pose[0]),
                float(pickup_pose[1]),
                float(pickup_pose[2]) + pick_distance,
                float(pickup_pose[3]),
                float(pickup_pose[4]),
                float(pickup_pose[5]),
            ])

            via_pose = self.posx([
                float(value)
                for value in self.FRAME_MOVEC_VIA
            ])

            # 1. Home
            self.node.get_logger().info(
                f"FRAME Pick 준비 -> Home 이동 - {component.get('code')}"
            )
            self.motion.move_home()
            self.wait(0.5)

            # 2. Home -> 공통 경유점 -> Pick 안전 접근점
            self.node.get_logger().info(
                "FRAME Pick MOVEC 안전 접근 - "
                f"via={list(self.FRAME_MOVEC_VIA)}, "
                f"safe_pick={[float(safe_pick_pose[i]) for i in range(6)]}, "
                f"BASE Z +{pick_distance:.1f}mm"
            )
            self.movec(
                via_pose,
                safe_pick_pose,
                vel=settings["speed"],
                acc=settings["acc"],
                ref=self.DR_BASE,
            )
            self.wait(0.5)

            # 3. 정확한 Pick 위치로 직선 하강
            self.node.get_logger().info(
                "FRAME 정확한 Pick 위치 이동 - "
                f"BASE Z -{pick_distance:.1f}mm"
            )
            self.movel(
                pickup_pose,
                vel=settings["speed"],
                acc=settings["acc"],
                ref=self.DR_BASE,
            )
            self.wait(0.2)

            # 4. Grasp
            self.node.get_logger().info("FRAME Gripper Close")
            self.motion.grasp()
            self.wait(0.2)

            # 5. 같은 Safe Pick으로 복귀
            self.node.get_logger().info(
                "FRAME Pick 완료 -> 안전 접근점 복귀 - "
                f"BASE Z +{pick_distance:.1f}mm"
            )
            self.movel(
                safe_pick_pose,
                vel=settings["speed"],
                acc=settings["acc"],
                ref=self.DR_BASE,
            )
            self.wait(0.5)

            self.node.get_logger().info(
                "========== FRAME PICK COMPLETE =========="
            )
            self._publish_cycle_event(
                operation_context,
                phase="FRAME_PICK",
                status="COMPLETED",
                detail={
                    "component_code": component.get("code"),
                    "motion": "MOVEC",
                    "movec_via": list(self.FRAME_MOVEC_VIA),
                    "pick_distance": pick_distance,
                    "safe_reference": "BASE_Z",
                },
            )
            return True

        except Exception as e:
            self.node.get_logger().error(f"FRAME Pick 실패: {e}")
            self._publish_cycle_event(
                operation_context,
                phase="FRAME_PICK",
                status="FAILED",
                error=e,
            )
            raise FramePickError(str(e)) from e

    def place_frame(self, parameters, components, operation_context=None):
        """FRAME을 movec()로 접근한 뒤 Force Place하고 Spiral 후 이탈한다.

        assembly_position:
            Force Place를 시작하는 정확한 Place 좌표.

        place_retreat_distance:
            assembly_position에서 BASE +Z 방향의 안전 접근/복귀 거리.

        Force:
            BASE -Z 방향.
            frame_place_force       = Desired Force
            frame_place_force_threshold = 측정 Force 성공 threshold (기본 10N)

        Release 후 Spiral:
            TOOL Z축 기준.
            Outward 2.5회 + Inward 2.5회로 총 5회.
            최대 반경 50mm(5cm). 값은 코드에 고정.
            축방향 이동 lmax=0mm.
            따라서 중심으로 복귀한 뒤 Safe Place로 상승한다.

        순서:
            movec(FRAME_MOVEC_VIA -> Safe Place)
            -> movel(assembly_position)
            -> BASE -Z Force Place
            -> Release
            -> TOOL Z Spiral Outward
            -> TOOL Z Spiral Inward
            -> movel(Safe Place)
        """
        self.node.get_logger().info("========== FRAME PLACE START ==========")
        self._publish_cycle_event(
            operation_context, phase="FRAME_PLACE", status="STARTED"
        )

        try:
            settings = self._load_frame_settings(parameters)
            component, assembly_pose = self._frame_assembly_input(components)

            place_distance = settings["place_distance"]

            safe_place_pose = self.posx([
                float(assembly_pose[0]),
                float(assembly_pose[1]),
                float(assembly_pose[2]) + place_distance,
                float(assembly_pose[3]),
                float(assembly_pose[4]),
                float(assembly_pose[5]),
            ])

            via_pose = self.posx([
                float(value)
                for value in self.FRAME_MOVEC_VIA
            ])

            # 1. 현재 Pick 안전점 -> 공통 경유점 -> Place 안전 접근점
            self.node.get_logger().info(
                "FRAME Place MOVEC 안전 접근 - "
                f"via={list(self.FRAME_MOVEC_VIA)}, "
                f"safe_place={[float(safe_place_pose[i]) for i in range(6)]}, "
                f"BASE Z +{place_distance:.1f}mm"
            )
            self.movec(
                via_pose,
                safe_place_pose,
                vel=settings["speed"],
                acc=settings["acc"],
                ref=self.DR_BASE,
            )
            self.wait(0.5)

            # 2. 정확한 assembly_position으로 직선 하강
            self.node.get_logger().info(
                "FRAME 정확한 Place 위치 이동 - "
                f"BASE Z -{place_distance:.1f}mm"
            )
            self.movel(
                assembly_pose,
                vel=settings["speed"],
                acc=settings["acc"],
                ref=self.DR_BASE,
            )
            self.wait(0.2)

            # 3. BASE -Z Force Place
            self.node.get_logger().info(
                "========== FRAME BASE -Z FORCE PLACE START =========="
            )
            self.node.get_logger().info(
                "FRAME Force 설정 - "
                f"desired_force={settings['place_force']:.2f}N, "
                f"measured_threshold={settings['contact_force']:.2f}N, "
                f"stiffness_z={settings['stiffness_z']:.2f}, "
                f"timeout={settings['force_timeout']:.2f}s"
            )

            force_result = self.motion.place(
                axis=self.FRAME_PLACE_FORCE_AXIS,
                direction=self.FRAME_PLACE_FORCE_DIRECTION,
                force=settings["place_force"],
                threshold=settings["contact_force"],
                timeout=settings["force_timeout"],
                stiffness={
                    self.FRAME_PLACE_FORCE_AXIS: settings["stiffness_z"]
                },
                reference=self.FRAME_PLACE_FORCE_REFERENCE,
            )

            if not force_result:
                raise RuntimeError(
                    "FRAME BASE -Z Force Place가 성공을 반환하지 않았습니다."
                )

            self.wait(0.2)

            # 4. Force 종료 후 Frame 놓기
            self.node.get_logger().info(
                "FRAME Force Place 완료 -> Gripper Release"
            )
            self.motion.release()
            self.wait(0.2)

            # 5. TOOL Z축 기준 Spiral.
            # Spiral 전용 파라미터는 DB에서 받지 않고 코드에 고정한다.
            #
            # 총 5회 회전:
            #   Outward 2.5회 + Inward 2.5회
            # 최대 반경:
            #   50mm = 5cm
            # 축방향 이동:
            #   0mm
            self.node.get_logger().info(
                "========== FRAME TOOL Z SPIRAL START =========="
            )
            self.node.get_logger().info(
                "FRAME Spiral 고정 설정 - "
                "outward_rev=2.5, inward_rev=2.5, "
                "rmax=50.0mm, lmax=0.0mm, "
                f"vel={settings['speed']:.1f}, "
                f"acc={settings['acc']:.1f}, "
                "ref=TOOL, axis=Z"
            )

            # 5-1. 중심 -> 최대 반경 50mm
            self.move_spiral(
                rev=2.5,
                rmax=50.0,
                lmax=0.0,
                vel=settings["speed"],
                acc=settings["acc"],
                axis=self.DR_AXIS_Z,
                ref=self.DR_TOOL,
                rad_dir=self.DR_SPIRAL_OUTWARD,
                rot_dir=self.DR_ROT_FORWARD,
            )

            # 5-2. 최대 반경 -> 원래 중심
            self.move_spiral(
                rev=2.5,
                rmax=50.0,
                lmax=0.0,
                vel=settings["speed"],
                acc=settings["acc"],
                axis=self.DR_AXIS_Z,
                ref=self.DR_TOOL,
                rad_dir=self.DR_SPIRAL_INWARD,
                rot_dir=self.DR_ROT_FORWARD,
            )

            self.node.get_logger().info(
                "FRAME TOOL Z Spiral 완료 -> 중심 복귀 완료"
            )
            self.wait(0.2)

            # 6. 동일한 Place 안전 접근점으로 상승
            self.node.get_logger().info(
                "FRAME Place 완료 -> 안전 접근점 복귀 - "
                f"BASE Z +{place_distance:.1f}mm"
            )
            self.movel(
                safe_place_pose,
                vel=settings["speed"],
                acc=settings["acc"],
                ref=self.DR_BASE,
            )
            self.wait(0.5)

            self.node.get_logger().info(
                "========== FRAME PLACE COMPLETE =========="
            )
            self._publish_cycle_event(
                operation_context,
                phase="FRAME_PLACE",
                status="COMPLETED",
                detail={
                    "component_code": component.get("code"),
                    "motion": "MOVEC",
                    "movec_via": list(self.FRAME_MOVEC_VIA),
                    "place_distance": place_distance,
                    "safe_reference": "BASE_Z",
                    "force_reference": "BASE",
                    "force_axis": "BASE_Z",
                    "force_direction": self.FRAME_PLACE_FORCE_DIRECTION,
                    "frame_place_force": settings["place_force"],
                    "frame_place_force_threshold": settings["contact_force"],
                    "spiral_reference": "TOOL",
                    "spiral_axis": "Z",
                    "spiral_total_revolutions": 5.0,
                    "spiral_radius_mm": 50.0,
                    "spiral_lmax_mm": 0.0,
                },
            )
            return True

        except Exception as e:
            self.node.get_logger().error(f"FRAME Place 실패: {e}")
            self._publish_cycle_event(
                operation_context,
                phase="FRAME_PLACE",
                status="FAILED",
                error=e,
            )
            try:
                self.force.all_off()
            except Exception:
                pass
            raise FramePlaceError(str(e)) from e

    # =========================================================
    # SNAPFIT PICK / PLACE
    # =========================================================

    def pick_snapfit(self, parameters, components, operation_context=None):
        """SNAPFIT을 정확한 pickup_position에서 파지한다.

        pickup_position:
            실제 Gripper Close가 수행되는 정확한 Pick 좌표.

        pick_distance:
            pickup_position에서 BASE +Z 방향으로 떨어진 안전 접근 거리.

        순서:
            Safe Pick -> pickup_position -> Grasp -> Safe Pick
        """
        self.node.get_logger().info("========== SNAPFIT PICK START ==========")
        self._publish_cycle_event(
            operation_context, phase="SNAPFIT_PICK", status="STARTED"
        )

        try:
            settings = self._load_snapfit_pick_settings(parameters)
            component, pickup_pose = self._snapfit_pickup_input(components)

            pick_distance = settings["pick_distance"]

            # DB pickup_position 자체가 실제 파지 좌표다.
            safe_pick_pose = self.posx([
                float(pickup_pose[0]),
                float(pickup_pose[1]),
                float(pickup_pose[2]) + pick_distance,
                float(pickup_pose[3]),
                float(pickup_pose[4]),
                float(pickup_pose[5]),
            ])

            # 1. 안전 접근점
            self.node.get_logger().info(
                "SNAPFIT Pick 안전 접근 - "
                f"component={component.get('code')}, "
                f"BASE Z +{pick_distance:.1f}mm"
            )
            self.movel(
                safe_pick_pose,
                vel=settings["speed"],
                acc=settings["acc"],
                ref=self.DR_BASE,
            )
            self.wait(0.5)

            # 2. 실제 Pick 위치
            self.node.get_logger().info(
                "SNAPFIT 정확한 Pick 위치 이동"
            )
            self.movel(
                pickup_pose,
                vel=settings["speed"],
                acc=settings["acc"],
                ref=self.DR_BASE,
            )
            self.wait(0.2)

            # 3. 파지
            self.node.get_logger().info("SNAPFIT Gripper Close")
            self.motion.grasp()
            self.wait(0.2)

            # 4. 동일한 안전 접근점으로 복귀
            self.node.get_logger().info(
                "SNAPFIT Pick 완료 -> 안전 접근점 복귀"
            )
            self.movel(
                safe_pick_pose,
                vel=settings["speed"],
                acc=settings["acc"],
                ref=self.DR_BASE,
            )
            self.wait(0.5)

            self.node.get_logger().info(
                "========== SNAPFIT PICK COMPLETE =========="
            )
            self._publish_cycle_event(
                operation_context,
                phase="SNAPFIT_PICK",
                status="COMPLETED",
                detail={
                    "component_code": component.get("code"),
                    "pick_distance": pick_distance,
                    "safe_reference": "BASE_Z",
                },
            )
            return True

        except Exception as e:
            self.node.get_logger().error(f"SNAPFIT Pick 실패: {e}")
            self._publish_cycle_event(
                operation_context,
                phase="SNAPFIT_PICK",
                status="FAILED",
                error=e,
            )
            raise SnapfitPickError(str(e)) from e

    def place_snapfit(self, parameters, components, operation_context=None):
        """SNAPFIT을 TOOL +Z 방향으로 Force 삽입한다.

        assembly_position:
            실제 Place/Force 삽입을 시작하는 정확한 좌표.

        place_distance:
            assembly_position에서 TOOL -Z 방향으로 떨어진 안전 접근 거리.

        순서:
            Safe Place(TOOL -Z)
            -> assembly_position
            -> TOOL +Z Force Insert
            -> Gripper Release
            -> Safe Place 복귀
        """
        self.node.get_logger().info("========== SNAPFIT PLACE START ==========")
        self._publish_cycle_event(
            operation_context, phase="SNAPFIT_PLACE", status="STARTED"
        )

        try:
            settings = self._load_snapfit_place_settings(parameters)
            component, assembly_pose = self._snapfit_assembly_input(components)

            place_distance = settings["place_distance"]

            # assembly_position은 BASE 절대 좌표다.
            # 안전 접근점은 그 pose에서 TOOL -Z 방향으로 place_distance만큼 이격한다.
            safe_place_pose = self.trans(
                assembly_pose,
                [0.0, 0.0, -place_distance, 0.0, 0.0, 0.0],
                self.DR_TOOL,
            )

            self.node.get_logger().info(
                "SNAPFIT Place 설정 - "
                f"component={component.get('code')}, "
                f"force_axis=TOOL +Z, "
                f"place_distance={place_distance:.1f}mm, "
                f"force={settings['place_force']:.2f}N, "
                f"threshold={settings['contact_force']:.2f}N"
            )

            # 1. TOOL -Z 안전 접근점으로 이동
            self.node.get_logger().info(
                "SNAPFIT Place 안전 접근 - "
                f"assembly_position 기준 TOOL -Z {place_distance:.1f}mm"
            )
            self.movel(
                safe_place_pose,
                vel=settings["speed"],
                acc=settings["acc"],
                ref=self.DR_BASE,
            )
            self.wait(0.5)

            # 2. 실제 Place/Force 시작 좌표로 이동
            self.node.get_logger().info(
                "SNAPFIT 정확한 assembly_position 이동"
            )
            self.movel(
                assembly_pose,
                vel=settings["speed"],
                acc=settings["acc"],
                ref=self.DR_BASE,
            )
            self.wait(0.2)

            # 3. TOOL +Z Force 삽입
            self.node.get_logger().info(
                "========== SNAPFIT TOOL +Z FORCE INSERT START =========="
            )
            result = self.motion.place(
                axis=self.SNAPFIT_INSERT_AXIS,
                direction=self.SNAPFIT_INSERT_DIRECTION,
                force=settings["place_force"],
                threshold=settings["contact_force"],
                timeout=settings["timeout"],
                stiffness={
                    self.SNAPFIT_INSERT_AXIS: settings["stiffness"]
                },
                reference=self.SNAPFIT_INSERT_REFERENCE,
            )
            if not result:
                raise RuntimeError(
                    "SNAPFIT TOOL +Z Force Place가 성공을 반환하지 않았습니다."
                )

            self.wait(0.2)

            # 4. 삽입 완료 후 놓기
            self.node.get_logger().info(
                "SNAPFIT Force 삽입 완료 -> Gripper Release"
            )
            self.motion.release()
            self.wait(0.5)

            # 5. 처음 계산한 동일한 안전 접근점으로 복귀
            if place_distance > 0:
                self.node.get_logger().info(
                    "SNAPFIT Place 완료 -> TOOL -Z 안전 접근점 복귀"
                )
                self.movel(
                    safe_place_pose,
                    vel=settings["speed"],
                    acc=settings["acc"],
                    ref=self.DR_BASE,
                )
                self.wait(0.5)

            self.node.get_logger().info(
                "========== SNAPFIT PLACE COMPLETE =========="
            )
            self._publish_cycle_event(
                operation_context,
                phase="SNAPFIT_PLACE",
                status="COMPLETED",
                detail={
                    "component_code": component.get("code"),
                    "reference": "TOOL",
                    "axis": "TOOL_Z",
                    "direction": self.SNAPFIT_INSERT_DIRECTION,
                    "place_distance": place_distance,
                    "force": settings["place_force"],
                    "threshold": settings["contact_force"],
                },
            )
            return True

        except Exception as e:
            self.node.get_logger().error(f"SNAPFIT Place 실패: {e}")
            self._publish_cycle_event(
                operation_context,
                phase="SNAPFIT_PLACE",
                status="FAILED",
                error=e,
            )
            try:
                self.force.all_off()
            except Exception:
                pass
            raise SnapfitPlaceError(str(e)) from e

    # =========================================================
    # Full Post cycle
    # =========================================================

    def install_post_cycle(self, parameters, components, operation_context=None):
        self.node.get_logger().info("========== POST CYCLE START ==========")
        self._publish_cycle_event(
            operation_context, phase="POST_CYCLE", status="STARTED"
        )

        try:
            # Cycle 자체에서는 release 후 이탈 이동에 필요한 speed/acc만 읽는다.
            # 나머지 DB 값은 각 Pick/Place 단계가 실제로 필요한 시점에만 읽는다.
            settings = self._load_travel_settings(parameters)
            self.node.get_logger().info(
                "Post Cycle DB 선택 로드 - "
                f"speed={settings['speed']:.1f}, acc={settings['acc']:.1f}"
            )

            self.pick_post(parameters, components, operation_context)
            post_retreat = self.place_post(parameters, components, operation_context)

            self.node.get_logger().info("Post Place 완료 -> Robot Motion Stop")
            self.motion.stop_motion()
            self.force.all_off()
            self.wait(0.2)

            self.node.get_logger().info("Robot Motion 정지 완료 -> Gripper Release")
            self.motion.release()
            self.wait(0.5)

            if post_retreat > 0:
                # assembly_position을 실제 Place 좌표로 보고,
                # DB place_retreat_distance만큼 BASE +Z에 있는 동일 Safe Place로 복귀한다.
                _, post_assembly_pose = self._post_assembly_input(components)
                post_safe_place_pose = self.posx([
                    float(post_assembly_pose[0]),
                    float(post_assembly_pose[1]),
                    float(post_assembly_pose[2]) + post_retreat,
                    float(post_assembly_pose[3]),
                    float(post_assembly_pose[4]),
                    float(post_assembly_pose[5]),
                ])

                self.node.get_logger().info(
                    "Post Release 완료 -> 동일한 Place 안전 접근점 복귀 - "
                    f"BASE Z +{post_retreat:.1f}mm"
                )
                self.movel(
                    post_safe_place_pose,
                    vel=settings["speed"],
                    acc=settings["acc"],
                    ref=self.DR_BASE,
                )
                self.wait(0.5)

            self.node.get_logger().info("Post Release 및 안전 이탈 완료 -> Home 이동")
            self.motion.move_home()
            self.wait(0.5)

            self.node.get_logger().info("========== POST CYCLE COMPLETE ==========")
            self._publish_cycle_event(
                operation_context, phase="POST_CYCLE", status="COMPLETED"
            )
            return True

        except Exception as e:
            self.node.get_logger().error(f"Post Cycle 실패: {e}")
            self._publish_cycle_event(
                operation_context, phase="POST_CYCLE", status="FAILED", error=e
            )
            try:
                self.force.all_off()
            except Exception:
                pass
            raise PostCycleError(str(e)) from e

    # =========================================================
    # Direct test
    # =========================================================

    def run(self, parameters, components, operation_context=None):
        try:
            self.node.get_logger().info("========== SOLAR MOTION START ==========")
            self.motion.move_home()
            self.wait(1.0)
            self.install_post_cycle(parameters, components, operation_context)
            self.wait(1.0)
            self.motion.move_home()
            self.node.get_logger().info("========== SOLAR MOTION COMPLETE ==========")
            return True
        except Exception as e:
            self.node.get_logger().error(f"Solar Motion 작업 중 오류: {e}")
            try:
                self.force.all_off()
            except Exception as force_error:
                self.node.get_logger().error(f"Force 해제 중 오류: {force_error}")
            raise