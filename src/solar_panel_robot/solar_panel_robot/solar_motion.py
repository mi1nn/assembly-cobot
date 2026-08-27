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

class PanelPickError(Exception):
    pass


class PanelPlaceError(Exception):
    pass


class PostCycleError(Exception):
    pass


class PostUnitCycleError(Exception):
    pass


class FrameSnapfitACycleError(Exception):
    pass


class PanelCycleError(Exception):
    pass


class SolarMotion:
    """DB Operation을 실제 로봇 Pick/Place 조립 동작으로 변환한다."""

    POST_COMPONENT_PREFIX = "CMP-POST-"
    PIN_COMPONENT_PREFIX = "PIN-A-"
    SNAPFIT_COMPONENT_PREFIX = "SNAPFIT-A-"
    FRAME_COMPONENT_PREFIX = "CMP-FRAME-"
    PANEL_COMPONENT_PREFIX = "CMP-PANEL-"


    FRAME_MOVEC_VIA = (
        -46.4,
        472.47,
        343.52,
        95.74,
        179.17,
        9.5,
    )


    SNAPFIT_TRANSFER_POSE = (
        382.99,
        -117.23,
        304.27,
        156.18,
        177.92,
        63.5,
    )


    PANEL_MOVE_VIA = (
        389.65,
        -329.83,
        402.33,
        153.5,
        -176.71,
        161.71,
    )


    PANEL_INSPECTION_READY_POSE = (
        367.86,
        82.67,
        280.74,
        90.39,
        179.98,
        90.75,
    )


    FRAME_PLACE_FORCE_AXIS = "z"
    FRAME_PLACE_FORCE_DIRECTION = -1
    FRAME_PLACE_FORCE_REFERENCE = "base"


    POST_INSERT_DIRECTION = 1


    PIN_INSERT_AXIS = "x"
    PIN_INSERT_DIRECTION = 1
    PIN_INSERT_REFERENCE = "tool"


    SNAPFIT_INSERT_AXIS = "z"
    SNAPFIT_INSERT_DIRECTION = 1
    SNAPFIT_INSERT_REFERENCE = "tool"


    CONTACT_THRESHOLD_N = 5.0
    CONTACT_POLL_INTERVAL = 0.02
    CONTACT_ARM_DELAY = 0.15
    CONTACT_DEFAULT_MAX_TRAVEL_MM = 150.0


    POST_FINAL_CONTACT_THRESHOLD_N = 20.0
    POST_FINAL_CONTACT_HOLD_SEC = 0.50


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
            movejx,
            mwait,
            move_periodic,
            posx,
            wait,
            DR_BASE,
            DR_TOOL,
            DR_MV_MOD_REL,
        )
        from .robot_motion import RobotMotion

        self.movel = movel
        self.movec = movec
        self.movejx = movejx
        self.mwait = mwait
        self.move_periodic = move_periodic
        self.posx = posx
        self.wait = wait
        self.DR_BASE = DR_BASE
        self.DR_TOOL = DR_TOOL
        self.DR_MV_MOD_REL = DR_MV_MOD_REL

        self.motion = RobotMotion()
        self.force = self.motion.force


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
        """키가 없거나 null이면 default를 반환한다."""
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
        """여러 DB 키 중 처음 존재하는 숫자를 사용한다."""
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
        """POST 접촉 탐색/정렬/삽입 설정."""
        settings = self._load_travel_settings(parameters)
        settings.update(
            {
                "retreat_distance": self._first_number(
                    parameters,
                    ("place_retreat_distance", "post_place_retreat_distance"),
                    50.0,
                    nonnegative=True,
                ),

                "place_force": self._first_number(
                    parameters, ("post_place_force",), 40.0, positive=True
                ),

                "contact_seek_force": self._first_number(
                    parameters, ("post_contact_force",), 20.0, positive=True
                ),


                "final_contact_threshold": self.POST_FINAL_CONTACT_THRESHOLD_N,
                "final_contact_hold_sec": self.POST_FINAL_CONTACT_HOLD_SEC,

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
        """SNAPFIT-A-* Pick 설정. snap_fit/snapfit 키를 모두 호환한다."""
        settings = self._load_travel_settings(parameters)
        settings["snapfit_pick_distance"] = self._first_number(
            parameters,
            (
                "snap_fit_pick_distance",
                "snapfit_pick_distance",
                "post_pin_pick_distance",
                "pick_distance",
            ),
            50.0,
            positive=True,
        )
        settings["snapfit_arc_height"] = self._first_number(
            parameters,
            ("snapfit_arc_height",),
            100.0,
            nonnegative=True,
        )
        settings["snapfit_arc_steps"] = self._first_number(
            parameters,
            ("snapfit_arc_steps",),
            6.0,
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
        """FRAME(CMP-FRAME-*) Pick/Place 이동/Force/Periodic 설정."""
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


        settings["place_force"] = self._first_number(
            parameters,
            ("frame_place_force",),
            30.0,
            positive=True,
        )


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

        settings["periodic_x_amplitude"] = self._first_number(
            parameters,
            ("frame_periodic_x_amplitude",),
            6.0,
            nonnegative=True,
        )
        settings["periodic_y_amplitude"] = self._first_number(
            parameters,
            ("frame_periodic_y_amplitude",),
            75.0,
            nonnegative=True,
        )
        settings["periodic_period"] = self._first_number(
            parameters,
            ("frame_periodic_period",),
            2.0,
            positive=True,
        )
        settings["periodic_atime"] = self._first_number(
            parameters,
            ("frame_periodic_atime",),
            5.0,
            nonnegative=True,
        )
        settings["periodic_repeat"] = self._first_number(
            parameters,
            ("frame_periodic_repeat",),
            2.0,
            positive=True,
        )

        return settings

    def _load_snapfit_place_settings(self, parameters):
        """SNAPFIT-A-* Place 설정."""
        settings = self._load_travel_settings(parameters)
        settings.update(
            {
                "place_distance": self._first_number(
                    parameters,
                    (
                        "snap_fit_place_distance",
                        "snapfit_place_distance",
                        "place_distance",
                        "snap_fit_place_retreat_distance",
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

    def _load_panel_pick_settings(self, parameters):
        """PANEL Pick 이동/파지 설정을 읽는다."""
        settings = self._load_travel_settings(parameters)
        settings.update({
            "pick_distance": self._first_number(
                parameters,
                ("panel_pick_distance", "pick_distance"),
                100.0,
                positive=True,
            ),
            "pick_speed": self._first_number(
                parameters,
                ("panel_pick_speed",),
                30.0,
                positive=True,
            ),
            "pick_acc": self._first_number(
                parameters,
                ("panel_pick_acceleration",),
                50.0,
                positive=True,
            ),
            "grasp_wait": self._first_number(
                parameters,
                ("panel_grasp_wait",),
                1.0,
                nonnegative=True,
            ),
            "movejx_solution": int(self._first_number(
                parameters, ("panel_movejx_solution", "movejx_solution"), 2.0,
                nonnegative=True,
            )),
        })
        return settings

    def _load_panel_place_settings(self, parameters):
        """PANEL Place의 안전 접근/복귀와 저속 배치 설정."""
        settings = self._load_travel_settings(parameters)
        settings.update({
            "place_distance": self._first_number(
                parameters,
                ("panel_place_distance", "place_retreat_distance"),
                100.0,
                nonnegative=True,
            ),
            "place_speed": self._first_number(
                parameters, ("panel_place_speed",), 30.0, positive=True
            ),
            "place_acc": self._first_number(
                parameters, ("panel_place_acceleration",), 50.0, positive=True
            ),
            "release_wait": self._first_number(
                parameters, ("panel_release_wait",), 1.0, nonnegative=True
            ),
            "release_retreat_distance": self._first_number(
                parameters, ("panel_release_retreat_distance",), 50.0, positive=True
            ),
            "periodic_x_amplitude": self._first_number(
                parameters, ("panel_periodic_x_amplitude",), 5.0, nonnegative=True
            ),
            "periodic_y_amplitude": self._first_number(
                parameters, ("panel_periodic_y_amplitude",), 0.0, nonnegative=True
            ),
            "periodic_z_amplitude": self._first_number(
                parameters, ("panel_periodic_z_amplitude",), 0.0, nonnegative=True
            ),
            "periodic_period": self._first_number(
                parameters, ("panel_periodic_period",), 2.0, positive=True
            ),
            "periodic_atime": self._first_number(
                parameters, ("panel_periodic_atime",), 0.5, nonnegative=True
            ),
            "periodic_repeat": self._first_number(
                parameters, ("panel_periodic_repeat",), 1.0, positive=True
            ),
        })
        return settings

    def _panel_place_input(self, components):
        component, assembly_pose = self._assembly_input(
            components, self.PANEL_COMPONENT_PREFIX, "PANEL"
        )
        if "assembly_release_position" not in component: # 뺄것1
            raise ValueError(
                f"PANEL({component.get('code')}) assembly_release_position 누락"
            )
        release_pose = self._position_to_posx(
            component["assembly_release_position"],
            "PANEL.assembly_release_position",
        )
        side_positions = component.get("assembly_side_positions")
        if not isinstance(side_positions, list) or len(side_positions) != 2:
            raise ValueError(
                "PANEL.assembly_side_positions는 좌우 검사 좌표 2개를 가진 list여야 합니다."
            )
        side_poses = [
            self._position_to_posx(
                position, f"PANEL.assembly_side_positions[{index}]"
            )
            for index, position in enumerate(side_positions)
        ]
        return component, assembly_pose, release_pose, side_poses


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

    def _panel_pickup_input(self, components):
        return self._pickup_input(
            components, self.PANEL_COMPONENT_PREFIX, "PANEL"
        )


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


    def pick_post(self, parameters, components, operation_context=None):
        """POST를 정확한 pickup_position에서 파지한다."""
        self.node.get_logger().info("========== POST PICK START ==========")
        self._publish_cycle_event(
            operation_context, phase="POST_PICK", status="STARTED"
        )

        try:
            settings = self._load_pick_settings(parameters)
            component, pickup_pose = self._post_pickup_input(components)

            pick_distance = settings["pick_distance"]


            safe_pick_pose = self.posx([
                float(pickup_pose[0]),
                float(pickup_pose[1]),
                float(pickup_pose[2]) + pick_distance,
                float(pickup_pose[3]),
                float(pickup_pose[4]),
                float(pickup_pose[5]),
            ])


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


            self.node.get_logger().info("POST Gripper Close")
            self.motion.grasp()
            self.wait(0.2)


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


            candidate_safe_pose, safe_solution_space = self.motion.get_current_pose(
                ref=self.DR_BASE
            )


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


            safe_place_pose = self.posx([
                float(assembly_pose[0]),
                float(assembly_pose[1]),
                float(assembly_pose[2]) + place_distance,
                float(assembly_pose[3]),
                float(assembly_pose[4]),
                float(assembly_pose[5]),
            ])


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
                    f"{direct_insert_threshold:.3f}mm "
                    "-> 이미 정상 진입으로 판단, 25-point Search SKIP"
                )
            else:
                self.node.get_logger().info(
                    f"BASE Z={current_base_z:.3f}mm >= "
                    f"{direct_insert_threshold:.3f}mm "
                    "-> 25-point Alignment Search 실행"
                )


                _, best = self._search_post_alignment(
                    settings, origin_pose=contact_pose, direction=direction
                )


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


    def pick_pin(self, parameters, components, operation_context=None):
        """PIN-A-*를 지정된 pickup_position에서 집는다."""
        self.node.get_logger().info("========== PIN PICK START ==========")
        self._publish_cycle_event(
            operation_context, phase="PIN_PICK", status="STARTED"
        )

        try:
            settings = self._load_pin_pick_settings(parameters)
            component, pickup_pose = self._pin_pickup_input(components)

            pick_distance = settings["pick_distance"]


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


            self.node.get_logger().info("PIN Gripper Close")
            self.motion.grasp()
            self.wait(0.2)


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
        """PIN-A-*를 TOOL +X 방향으로 두 번 밀어 넣는다."""
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
                f"delta_threshold={settings['contact_force']:.2f}N, "
                "push_count=2"
            )


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


            self.node.get_logger().info(
                "PIN 1차 반력 감지 완료 -> Gripper Release"
            )
            self.motion.release()
            self.wait(0.5)


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


            self.node.get_logger().info(
                "PIN 2차 Push 준비 -> Gripper Close"
            )
            self.motion.grasp()
            self.wait(0.5)


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
                    "first_force": 20.0,
                    "first_threshold": 10.0,
                    "second_force": 50.0,
                    "second_threshold": 40.0,
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


    def pick_panel(self, parameters, components, operation_context=None):
        """태양광 패널 Pick 동작."""
        self.node.get_logger().info("========== PANEL PICK START ==========")
        self._publish_cycle_event(
            operation_context, phase="PANEL_PICK", status="STARTED"
        )

        try:
            settings = self._load_panel_pick_settings(parameters)
            component, pickup_pose = self._panel_pickup_input(components)

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
                for value in self.PANEL_MOVE_VIA
            ])


            self.node.get_logger().info(
                "PANEL Pick 1차 MOVEL - 현재 위치 -> 경유점 - "
                f"via={list(self.PANEL_MOVE_VIA)}"
            )
            first_move_result = self.movel(
                via_pose,
                vel=settings["speed"],
                acc=settings["acc"],
                radius=30.0,
                ref=self.DR_BASE,
            )
            if (
                isinstance(first_move_result, (int, float))
                and first_move_result < 0
            ):
                raise RuntimeError(
                    "PANEL 경유점 MOVEL 실행 실패: "
                    f"result={first_move_result}"
                )


            self.node.get_logger().info(
                "PANEL 정확한 Pick 위치 이동 - "
                f"BASE Z -{pick_distance:.1f}mm"
            )
            self.movel(
                pickup_pose,
                vel=settings["speed"],
                acc=settings["acc"],
                ref=self.DR_BASE,
            )
            self.wait(0.2)


            self.node.get_logger().info("PANEL Gripper Close")
            self.motion.grasp()
            self.wait(0.2)


            self.node.get_logger().info(
                "PANEL Pick 완료 -> 안전 접근점 복귀 - "
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
                "========== PANEL PICK COMPLETE =========="
            )
            self._publish_cycle_event(
                operation_context,
                phase="PANEL_PICK",
                status="COMPLETED",
                detail={
                    "component_code": component.get("code"),
                    "motion": "MOVEL_X2_BLEND",
                    "movel_via": list(self.PANEL_MOVE_VIA),
                    "blend_radius_mm": 20.0,
                    "pick_distance": pick_distance,
                    "safe_reference": "BASE_Z",
                },
            )
            return True

        except Exception as e:
            self.node.get_logger().error(f"PANEL Pick 실패: {e}")
            self._publish_cycle_event(
                operation_context,
                phase="PANEL_PICK",
                status="FAILED",
                error=e,
            )
            raise PanelPickError(str(e)) from e

    def place_panel(self, parameters, components, operation_context=None):
            """PANEL 배치 후 TOOL -Z로 이탈하고 양쪽 지점에서 위치를 검사한다."""
            self.node.get_logger().info("========== PANEL PLACE START ==========")
            self._publish_cycle_event(
                operation_context, phase="PANEL_PLACE", status="STARTED"
            )

            try:
                settings = self._load_panel_place_settings(parameters)
                component, assembly_pose, release_pose, side_poses = (
                    self._panel_place_input(components)
                )
                
                # 1-1. 현재 TCP 위치 -> Panel 전용 경유점
                self.node.get_logger().info(
                    "PANEL PLACE 1차 MOVEL - 현재 위치 -> 경유점 - "
                    f"via={list(self.PANEL_MOVE_VIA)}"
                )
                # 방향 회전1
                self.movel(
                    self.posx([0.0, 0.0, 0.0, 0.0, 0.0, -90.0]),
                    vel=settings["speed"],
                    acc=settings["acc"],
                    ref=self.DR_TOOL,
                    mod=self.DR_MV_MOD_REL,
                )
                self.mwait()
                rotated_pose, _ = self.motion.get_current_pose(ref=self.DR_BASE)

                via_pose = self.posx([
                    float(self.PANEL_MOVE_VIA[0]),
                    float(self.PANEL_MOVE_VIA[1]),
                    float(self.PANEL_MOVE_VIA[2]),
                    float(self.PANEL_MOVE_VIA[3]),
                    float(self.PANEL_MOVE_VIA[4]),
                    float(rotated_pose[5]),
                ])

                first_move_result = self.movel(
                    via_pose,
                    vel=settings["speed"],
                    acc=settings["acc"],
                    ref=self.DR_BASE,
                )
                if (
                    isinstance(first_move_result, (int, float))
                    and first_move_result < 0
                ):
                    raise RuntimeError(
                        "PANEL 경유점 MOVEL 실행 실패: "
                        f"result={first_move_result}"
                    )
                # 방향 회전2
                self.movel(
                    self.posx([0.0, 0.0, 0.0, 0.0, 0.0, -90.0]),
                    vel=settings["speed"],
                    acc=settings["acc"],
                    ref=self.DR_TOOL,
                    mod=self.DR_MV_MOD_REL,
                )
                self.mwait()
                rotated_pose, _ = self.motion.get_current_pose(ref=self.DR_BASE)

                # 1-2. Panel 전용 경유점 -> Panel place 지점
                self.node.get_logger().info(
                    "PANEL Pick 2차 MOVEL - 경유점 -> Assembly Position - "
                    f"assembly_position={[float(assembly_pose[i]) for i in range(6)]}, "
                )
                second_move_result = self.movel(
                    assembly_pose,
                    vel=settings["speed"],
                    acc=settings["acc"],
                    ref=self.DR_BASE,
                )
                if (
                    isinstance(second_move_result, (int, float))
                    and second_move_result < 0
                ):
                    raise RuntimeError(
                        "PANEL Safe Pick MOVEL 실행 실패: "
                        f"result={second_move_result}"
                    )
                self.wait(0.5)


                self.movel(
                    self.posx([-100.0, 0.0, -40.0, 0.0, -30.0, 0.0]),
                    vel=settings["place_speed"],
                    acc=settings["place_acc"],
                    ref=self.DR_BASE,
                    mod=self.DR_MV_MOD_REL,
                )
                self.mwait()
                self.motion.release()
                self.wait(settings["release_wait"])


                retreat_distance = settings["release_retreat_distance"]
                self.movel(
                    self.posx([0.0, 0.0, -retreat_distance, 0.0, 0.0, 0.0]),
                    vel=settings["place_speed"],
                    acc=settings["place_acc"],
                    ref=self.DR_TOOL,
                    mod=self.DR_MV_MOD_REL,
                )
                self.mwait()
                self.wait(0.5)


                inspection_ready_pose = self.posx([
                    float(value) for value in self.PANEL_INSPECTION_READY_POSE
                ])
                self.movel(
                    inspection_ready_pose,
                    vel=settings["speed"],
                    acc=settings["acc"],
                    ref=self.DR_BASE,
                )
                self.mwait()


                periodic_amp = [
                    0.0,
                    settings["periodic_y_amplitude"],
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                ]
                side_approach_distance = settings["place_distance"]
                for side_index, side_pose in enumerate(side_poses, start=1):
                    side_safe_pose = self.posx([
                        float(side_pose[0]),
                        float(side_pose[1]),
                        float(side_pose[2]) + side_approach_distance,
                        float(side_pose[3]),
                        float(side_pose[4]),
                        float(side_pose[5]),
                    ])
                    self.node.get_logger().info(
                        f"PANEL Side 검사 {side_index}/2 안전점 이동 - "
                        f"BASE Z +{side_approach_distance:.1f}mm"
                    )
                    self.movel(
                        side_safe_pose,
                        vel=settings["speed"],
                        acc=settings["acc"],
                        ref=self.DR_BASE,
                    )
                    self.mwait()
                    self.movel(
                        side_pose,
                        vel=settings["place_speed"],
                        acc=settings["place_acc"],
                        ref=self.DR_BASE,
                    )
                    self.mwait()
                    periodic_result = self.move_periodic(
                        amp=periodic_amp,
                        period=settings["periodic_period"],
                        atime=settings["periodic_atime"],
                        repeat=settings["periodic_repeat"],
                        ref=self.DR_TOOL,
                    )
                    if periodic_result != 0:
                        raise RuntimeError(
                            f"PANEL Side {side_index} Periodic 검사 실패: "
                            f"result={periodic_result}"
                        )
                    self.mwait()
                    self.movel(
                        side_safe_pose,
                        vel=settings["place_speed"],
                        acc=settings["place_acc"],
                        ref=self.DR_BASE,
                    )
                    self.mwait()

                self._publish_cycle_event(
                    operation_context,
                    phase="PANEL_PLACE",
                    status="COMPLETED",
                    detail={
                        "component_code": component.get("code"),
                        "motion": "MOVEC_TO_ASSEMBLY",
                        "movec_via": list(self.PANEL_MOVE_VIA),
                        "release_retreat_reference": "TOOL",
                        "release_retreat_axis": "TOOL_Z",
                        "release_retreat_direction": -1,
                        "release_retreat_distance": retreat_distance,
                        "inspection_ready_pose": list(
                            self.PANEL_INSPECTION_READY_POSE
                        ),
                        "side_approach_distance": side_approach_distance,
                        "side_check_count": len(side_poses),
                        "periodic_reference": "TOOL",
                        "periodic_amplitude": periodic_amp,
                    },
                )
                self.node.get_logger().info(
                    "========== PANEL PLACE COMPLETE =========="
                )
                return True

            except Exception as e:
                self.node.get_logger().error(f"PANEL Place 실패: {e}")
                self._publish_cycle_event(
                    operation_context, phase="PANEL_PLACE", status="FAILED", error=e
                )
                raise PanelPlaceError(str(e)) from e


    def pick_frame(self, parameters, components, operation_context=None):
        """FRAME을 공통 경유점 기반 movec()로 접근해 정확한 위치에서 파지한다."""
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
                float(value) for value in self.FRAME_MOVEC_VIA
            ])

            self.node.get_logger().info(
                f"FRAME Pick 준비 -> Home 이동 - {component.get('code')}"
            )
            self.motion.move_home()
            self.wait(0.5)

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

            self.node.get_logger().info("FRAME Gripper Close")
            self.motion.grasp()
            self.wait(0.2)

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
                operation_context, phase="FRAME_PICK", status="FAILED", error=e
            )
            raise FramePickError(str(e)) from e


    def place_frame(self, parameters, components, operation_context=None):
        """FRAME을 movec()로 접근한 뒤 Force Place하고 Periodic 후 이탈한다."""
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


            self.node.get_logger().info(
                "FRAME Force Place 완료 -> Gripper Release"
            )
            self.motion.release()
            self.wait(0.2)


            x_periodic_amp = [
                settings["periodic_x_amplitude"],
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
            ]
            y_periodic_amp = [
                0.0,
                settings["periodic_y_amplitude"],
                0.0,
                0.0,
                0.0,
                0.0,
            ]
            periodic_period = settings["periodic_period"]
            sequence_repeat = int(settings["periodic_repeat"])

            if sequence_repeat < 1:
                raise ValueError("frame_periodic_repeat는 1 이상이어야 합니다.")

            self.node.get_logger().info(
                "========== FRAME TOOL X -> Y PERIODIC START =========="
            )
            self.node.get_logger().info(
                "FRAME Periodic 순차 설정 - "
                f"x_amp={x_periodic_amp}, y_amp={y_periodic_amp}, "
                f"period={periodic_period:.2f}s, "
                f"atime={settings['periodic_atime']:.2f}s, "
                f"sequence_repeat={sequence_repeat}, ref=TOOL"
            )

            for sequence_index in range(sequence_repeat):
                current_sequence = sequence_index + 1
                self.node.get_logger().info(
                    f"FRAME Periodic sequence "
                    f"{current_sequence}/{sequence_repeat} - TOOL X START"
                )
                x_result = self.move_periodic(
                    amp=x_periodic_amp,
                    period=periodic_period,
                    atime=settings["periodic_atime"],
                    repeat=1.0,
                    ref=self.DR_TOOL,
                )
                if x_result != 0:
                    raise RuntimeError(
                        "FRAME TOOL X Periodic 이동 실패 - "
                        f"sequence={current_sequence}, result={x_result}"
                    )
                self.wait(0.2)

                self.node.get_logger().info(
                    f"FRAME Periodic sequence "
                    f"{current_sequence}/{sequence_repeat} - TOOL Y START"
                )
                y_result = self.move_periodic(
                    amp=y_periodic_amp,
                    period=periodic_period,
                    atime=settings["periodic_atime"],
                    repeat=1.0,
                    ref=self.DR_TOOL,
                )
                if y_result != 0:
                    raise RuntimeError(
                        "FRAME TOOL Y Periodic 이동 실패 - "
                        f"sequence={current_sequence}, result={y_result}"
                    )
                self.wait(0.2)

            self.node.get_logger().info(
                "FRAME TOOL X -> Y Periodic 순차 반복 완료"
            )


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
                    "periodic_reference": "TOOL",
                    "periodic_x_amplitude": x_periodic_amp,
                    "periodic_y_amplitude": y_periodic_amp,
                    "periodic_period_sec": periodic_period,
                    "periodic_atime_sec": settings["periodic_atime"],
                    "periodic_sequence_repeat": sequence_repeat,
                    "periodic_axis_repeat": 1,
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


    def pick_snapfit(self, parameters, components, operation_context=None):
        """안전 접근 후 SNAPFIT을 파지하고 공통 전송 기준점까지 Arc 이동한다."""
        self.node.get_logger().info("========== SNAPFIT PICK START ==========")
        self._publish_cycle_event(
            operation_context, phase="SNAPFIT_PICK", status="STARTED"
        )

        try:
            settings = self._load_snapfit_pick_settings(parameters)
            component, pickup_pose = self._snapfit_pickup_input(components)
            pick_distance = settings["snapfit_pick_distance"]
            arc_steps = int(settings["snapfit_arc_steps"])
            if arc_steps < 2:
                raise ValueError("snapfit_arc_steps는 2 이상이어야 합니다.")

            safe_pick_pose = self.posx([
                float(pickup_pose[0]),
                float(pickup_pose[1]),
                float(pickup_pose[2]) + pick_distance,
                float(pickup_pose[3]),
                float(pickup_pose[4]),
                float(pickup_pose[5]),
            ])


            self.node.get_logger().info(
                "SNAPFIT Pick 안전 접근 MOVEL - "
                f"distance=BASE +Z {pick_distance:.1f}mm, "
                f"target={list(safe_pick_pose)}"
            )
            safe_result = self.movel(
                safe_pick_pose,
                vel=settings["speed"],
                acc=settings["acc"],
                ref=self.DR_BASE,
            )
            if safe_result != 0:
                raise RuntimeError(
                    "SNAPFIT Pick 안전 접근 MOVEL 실패 - "
                    f"result={safe_result}, target={list(safe_pick_pose)}"
                )
            self.mwait()
            self.wait(0.2)


            self.node.get_logger().info(
                "SNAPFIT 정확한 Pick 위치 MOVEL - "
                f"target={list(pickup_pose)}"
            )
            pickup_result = self.movel(
                pickup_pose,
                vel=settings["speed"],
                acc=settings["acc"],
                ref=self.DR_BASE,
            )
            if pickup_result != 0:
                raise RuntimeError(
                    "SNAPFIT Pick 위치 MOVEL 실패 - "
                    f"result={pickup_result}, target={list(pickup_pose)}"
                )
            self.mwait()
            self.wait(0.2)


            self.node.get_logger().info("SNAPFIT Gripper Close")
            self.motion.grasp()
            self.wait(0.2)

            safe_result = self.movel(
                safe_pick_pose,
                vel=settings["speed"],
                acc=settings["acc"],
                ref=self.DR_BASE,
            )


            arc_start_pose, solution_space = self.motion.get_current_pose(
                ref=self.DR_BASE
            )
            transfer_pose = list(self.SNAPFIT_TRANSFER_POSE)
            self.node.get_logger().info(
                "SNAPFIT Grasp 완료 -> 공통 기준점 ARC - "
                f"start={arc_start_pose}, end={transfer_pose}, "
                f"height={settings['snapfit_arc_height']:.1f}mm, "
                f"steps={arc_steps}, speed={settings['speed']:.1f}, "
                f"acc={settings['acc']:.1f}, solution_space={solution_space}"
            )
            self.motion.move_arc(
                arc_start_pose,
                transfer_pose,
                height=settings["snapfit_arc_height"],
                steps=arc_steps,
                velocity=settings["speed"],
                acc=settings["acc"],
            )
            self.mwait()
            self.wait(0.2)

            self.node.get_logger().info(
                "========== SNAPFIT PICK COMPLETE =========="
            )
            self._publish_cycle_event(
                operation_context,
                phase="SNAPFIT_PICK",
                status="COMPLETED",
                detail={
                    "component_code": component.get("code"),
                    "snapfit_pick_distance": pick_distance,
                    "safe_reference": "BASE_Z",
                    "arc_start": arc_start_pose,
                    "arc_target": transfer_pose,
                    "arc_height_mm": settings["snapfit_arc_height"],
                    "arc_steps": arc_steps,
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
        """SNAPFIT을 TOOL +Z 방향으로 2단계 Force 삽입한다."""
        self.node.get_logger().info("========== SNAPFIT PLACE START ==========")
        self._publish_cycle_event(
            operation_context, phase="SNAPFIT_PLACE", status="STARTED"
        )

        try:
            settings = self._load_snapfit_place_settings(parameters)
            component, assembly_pose = self._snapfit_assembly_input(components)

            place_distance = settings["place_distance"]


            safe_place_pose = self.posx([
                float(assembly_pose[0]),
                float(assembly_pose[1]),
                float(assembly_pose[2]) + place_distance,
                float(assembly_pose[3]),
                float(assembly_pose[4]),
                float(assembly_pose[5]),
            ])

            self.node.get_logger().info(
                "SNAPFIT Place 설정 - "
                f"component={component.get('code')}, "
                f"force_axis=TOOL +Z, "
                f"place_distance={place_distance:.1f}mm, "
                f"assembly_target={list(assembly_pose)}, "
                f"safe_target={list(safe_place_pose)}, "
                f"force={settings['place_force']:.2f}N, "
                f"threshold={settings['contact_force']:.2f}N"
            )


            self.node.get_logger().info(
                "SNAPFIT Place 안전 접근 - "
                f"assembly_position 기준 BASE +Z {place_distance:.1f}mm"
            )
            self.movel(
                safe_place_pose,
                vel=settings["speed"],
                acc=settings["acc"],
                ref=self.DR_BASE,
            )
            self.mwait()
            self.wait(0.2)


            self.node.get_logger().info(
                "SNAPFIT 1차 Force 준비 -> assembly_position 이동"
            )
            self.movel(
                assembly_pose,
                vel=settings["speed"],
                acc=settings["acc"],
                ref=self.DR_BASE,
            )
            self.mwait()
            self.wait(0.2)


            self.node.get_logger().info(
                "========== SNAPFIT PLACE 1ST FORCE START =========="
            )
            first_result = self.motion.place(
                axis=self.SNAPFIT_INSERT_AXIS,
                direction=self.SNAPFIT_INSERT_DIRECTION,
                force=20.0,
                threshold=10.0,
                timeout=settings["timeout"],
                stiffness={
                    self.SNAPFIT_INSERT_AXIS: settings["stiffness"]
                },
                reference=self.SNAPFIT_INSERT_REFERENCE,
            )
            if not first_result:
                raise RuntimeError(
                    "SNAPFIT 1차 TOOL +Z Force Place가 성공을 반환하지 않았습니다."
                )

            self.wait(0.2)


            self.node.get_logger().info(
                "SNAPFIT 1차 Force 완료 -> Gripper Release"
            )
            self.motion.release()
            self.wait(0.5)


            self.node.get_logger().info(
                "SNAPFIT 1차 삽입 완료 -> BASE +Z 안전 접근점 복귀"
            )
            self.movel(
                safe_place_pose,
                vel=settings["speed"],
                acc=settings["acc"],
                ref=self.DR_BASE,
            )
            self.mwait()
            self.wait(0.2)


            self.node.get_logger().info(
                "SNAPFIT 2차 Push 준비 -> Gripper Close"
            )
            self.motion.grasp()
            self.wait(0.5)


            self.node.get_logger().info(
                "SNAPFIT 2차 Force 준비 -> assembly_position 재접근"
            )
            self.movel(
                assembly_pose,
                vel=settings["speed"],
                acc=settings["acc"],
                ref=self.DR_BASE,
            )
            self.mwait()
            self.wait(0.2)


            self.node.get_logger().info(
                "========== SNAPFIT PLACE 2ND FORCE START =========="
            )
            second_result = self.motion.place(
                axis=self.SNAPFIT_INSERT_AXIS,
                direction=self.SNAPFIT_INSERT_DIRECTION,
                force=10.0,
                threshold=5.0,
                timeout=settings["timeout"],
                stiffness={
                    self.SNAPFIT_INSERT_AXIS: settings["stiffness"]
                },
                reference=self.SNAPFIT_INSERT_REFERENCE,
            )
            if not second_result:
                raise RuntimeError(
                    "SNAPFIT 2차 TOOL +Z Force Place가 성공을 반환하지 않았습니다."
                )

            self.wait(0.2)


            self.node.get_logger().info(
                "SNAPFIT 2차 Force 완료 -> BASE +Z 안전 접근점 복귀"
            )
            self.movel(
                safe_place_pose,
                vel=settings["speed"],
                acc=settings["acc"],
                ref=self.DR_BASE,
            )
            self.mwait()
            self.wait(0.2)

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
                    "safe_reference": "BASE_Z",
                    "push_count": 2,
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


    def install_post_pick_place_cycle(
        self,
        parameters,
        components,
        operation_context=None,
    ):
        """DB operation 1개로 POST Pick + Place 전체 동작을 수행한다."""
        self.node.get_logger().info(
            "========== POST PICK + PLACE UNIT START =========="
        )
        self._publish_cycle_event(
            operation_context,
            phase="POST_PICK_PLACE_UNIT",
            status="STARTED",
        )

        try:
            post_component, _ = self._post_pickup_input(components)
            self._post_assembly_input(components)
            self._load_pick_settings(parameters)
            self._load_post_place_settings(parameters)

            self.node.get_logger().info(
                "POST Unit Preflight 완료 - "
                f"component={post_component.get('code')}"
            )

            result = self.install_post_cycle(
                parameters,
                components,
                operation_context,
            )

            self._publish_cycle_event(
                operation_context,
                phase="POST_PICK_PLACE_UNIT",
                status="COMPLETED",
                detail={
                    "post_component_code": post_component.get("code"),
                },
            )
            return result

        except Exception as e:
            self.node.get_logger().error(
                f"POST Pick + Place Unit 실패: {e}"
            )
            self._publish_cycle_event(
                operation_context,
                phase="POST_PICK_PLACE_UNIT",
                status="FAILED",
                error=e,
            )
            try:
                self.force.all_off()
            except Exception:
                pass
            raise PostUnitCycleError(str(e)) from e

    def install_frame_snapfit_a_cycle(
        self,
        parameters,
        components,
        operation_context=None,
    ):
        """DB operation 1개로 FRAME + SNAPFIT-A 6개 전체 조립을 수행한다."""
        self.node.get_logger().info(
            "========== FRAME + SNAPFIT-A UNIT START =========="
        )
        self._publish_cycle_event(
            operation_context,
            phase="FRAME_SNAPFIT_A_UNIT",
            status="STARTED",
        )

        try:


            frame_component, _ = self._frame_pickup_input(components)
            self._frame_assembly_input(components)

            snapfit_components = []
            for component in components:
                if not isinstance(component, dict):
                    continue
                code = str(component.get("code", "")).strip()
                if code.startswith(self.SNAPFIT_COMPONENT_PREFIX):
                    snapfit_components.append(component)


            snapfit_components.sort(
                key=lambda item: str(item.get("code", "")).strip()
            )

            if len(snapfit_components) != 6:
                raise ValueError(
                    "frameA operation에는 SNAPFIT-A component가 "
                    f"정확히 6개 필요합니다. received={len(snapfit_components)}"
                )

            expected_codes = [
                f"{self.SNAPFIT_COMPONENT_PREFIX}{index:02d}"
                for index in range(1, 7)
            ]
            received_codes = [
                str(component.get("code", "")).strip()
                for component in snapfit_components
            ]
            if received_codes != expected_codes:
                raise ValueError(
                    "SNAPFIT-A component code가 SNAPFIT-A-01~06과 일치해야 합니다. "
                    f"received={received_codes}"
                )


            for component in snapfit_components:
                single_component = [component]
                self._snapfit_pickup_input(single_component)
                self._snapfit_assembly_input(single_component)

            self._load_frame_settings(parameters)
            self._load_snapfit_pick_settings(parameters)
            self._load_snapfit_place_settings(parameters)

            self.node.get_logger().info(
                "FRAME + SNAPFIT-A Unit Preflight 완료 - "
                f"frame={frame_component.get('code')}, "
                f"snapfits={received_codes}"
            )


            self.pick_frame(parameters, components, operation_context)
            self.place_frame(parameters, components, operation_context)

            self.node.get_logger().info(
                "FRAME 완료 -> SNAPFIT-A 작업 전 Home 이동"
            )
            self.motion.move_home()
            self.wait(0.5)


            for index, snapfit_component in enumerate(
                snapfit_components, start=1
            ):
                snapfit_code = str(
                    snapfit_component.get("code", "")
                ).strip()

                self.node.get_logger().info(
                    "========== SNAPFIT-A UNIT "
                    f"{index}/6 START : {snapfit_code} =========="
                )


                self.force.all_off()
                self.motion.release()
                self.wait(0.2)


                single_component = [snapfit_component]

                self.pick_snapfit(
                    parameters,
                    single_component,
                    operation_context,
                )
                self.place_snapfit(
                    parameters,
                    single_component,
                    operation_context,
                )

                self.force.all_off()
                self.motion.release()
                self.wait(0.2)

                self.node.get_logger().info(
                    "SNAPFIT-A "
                    f"{index}/6 COMPLETE : {snapfit_code}"
                )


                self.motion.move_home()
                self.wait(0.5)


            self.node.get_logger().info(
                "========== FRAME + SNAPFIT-A UNIT COMPLETE =========="
            )
            self._publish_cycle_event(
                operation_context,
                phase="FRAME_SNAPFIT_A_UNIT",
                status="COMPLETED",
                detail={
                    "frame_component_code": frame_component.get("code"),
                    "snapfit_component_codes": received_codes,
                    "snapfit_count": len(snapfit_components),
                },
            )
            return True

        except Exception as e:
            self.node.get_logger().error(
                f"FRAME + SNAPFIT-A Unit 실패: {e}"
            )
            self._publish_cycle_event(
                operation_context,
                phase="FRAME_SNAPFIT_A_UNIT",
                status="FAILED",
                error=e,
            )
            try:
                self.force.all_off()
            except Exception:
                pass
            raise FrameSnapfitACycleError(str(e)) from e

    def install_panel_cycle(
        self,
        parameters,
        components,
        operation_context=None,
    ):
        """DB operation 1개로 PANEL Pick + Place 전체 동작을 수행한다."""
        self.node.get_logger().info(
            "========== PANEL PICK + PLACE UNIT START =========="
        )
        self._publish_cycle_event(
            operation_context,
            phase="PANEL_PICK_PLACE_UNIT",
            status="STARTED",
        )

        try:

            panel_component, _ = self._panel_pickup_input(components)
            self._panel_place_input(components)
            self._load_panel_pick_settings(parameters)
            self._load_panel_place_settings(parameters)

            self.node.get_logger().info(
                "PANEL Unit Preflight 완료 - "
                f"component={panel_component.get('code')}"
            )

            self.pick_panel(parameters, components, operation_context)
            self.place_panel(parameters, components, operation_context)

            self.force.all_off()
            self.node.get_logger().info(
                "PANEL Pick + Place 완료 -> Home 이동"
            )
            self.motion.move_home()
            self.wait(0.5)

            self.node.get_logger().info(
                "========== PANEL PICK + PLACE UNIT COMPLETE =========="
            )
            self._publish_cycle_event(
                operation_context,
                phase="PANEL_PICK_PLACE_UNIT",
                status="COMPLETED",
                detail={
                    "panel_component_code": panel_component.get("code"),
                },
            )
            return True

        except Exception as e:
            self.node.get_logger().error(
                f"PANEL Pick + Place Unit 실패: {e}"
            )
            self._publish_cycle_event(
                operation_context,
                phase="PANEL_PICK_PLACE_UNIT",
                status="FAILED",
                error=e,
            )
            try:
                self.force.all_off()
            except Exception:
                pass
            raise PanelCycleError(str(e)) from e


    def install_post_cycle(self, parameters, components, operation_context=None):
        self.node.get_logger().info("========== POST CYCLE START ==========")
        self._publish_cycle_event(
            operation_context, phase="POST_CYCLE", status="STARTED"
        )

        try:


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