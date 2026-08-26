class PostPickError(Exception):
    pass


class PostPlaceError(Exception):
    pass


class PostPinPickError(Exception):
    pass


class PostPinPlaceError(Exception):
    pass


class PostCycleError(Exception):
    pass


class SolarMotion:
    """DB 최종 계약에 맞춘 Post 1개 설치 Cycle.

    operation.parameter
        DB 전체를 검증하지 않는다. 각 Pick/Place 단계가 실제로 필요한 값만
        실행 시점에 선택적으로 읽는다. 현재 사용하는 키:
            speed, acceleration, pick_distance, place_retreat_distance,
            place_search_limit_z, place_force, place_contact_force,
            place_insert_force, place_stiffness_z, place_search_velocity,
            place_search_acceleration, place_search_timeout

        아래 메타데이터는 DB에 존재해도 Post Motion에서는 사용하지 않는다.
            tcp, ucs, tool, fixture, coordinate_system

    operation.components
        CMP-POST-* : pickup_position / assembly_position
        PIN-*      : pickup_position / assembly_position

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
    POST_PIN_COMPONENT_PREFIX = "PIN-"

    POST_INSERT_DIRECTION = 1      # TOOL +Z
    POST_PIN_INSERT_DIRECTION = 1  # TOOL +X

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

        from DSR_ROBOT2 import movel, posx, wait, DR_BASE, DR_TOOL
        from .robot_motion import RobotMotion

        self.movel = movel
        self.posx = posx
        self.wait = wait
        self.DR_BASE = DR_BASE
        self.DR_TOOL = DR_TOOL

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
                # 최종 본 삽입 Desired Force
                "place_force": self._first_number(
                    parameters, ("place_force", "post_place_force"), 40.0, positive=True
                ),
                # 최초 접촉을 찾기 위한 약한 Desired Force
                "contact_seek_force": self._first_number(
                    parameters, ("place_contact_force", "post_contact_force"), 20.0, positive=True
                ),
                # 최종 삽입 성공 판정은 코드 정책으로 분리한다.
                # place_contact_force는 최초 Contact Seek 용도이며 여기 재사용하지 않는다.
                "final_contact_threshold": self.POST_FINAL_CONTACT_THRESHOLD_N,
                "final_contact_hold_sec": self.POST_FINAL_CONTACT_HOLD_SEC,
                # 각 위치 후보에서 사용하는 Probe Force
                "insert_force": self._first_number(
                    parameters, ("place_insert_force", "post_search_force"), 12.0, positive=True
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

    def _load_pin_place_settings(self, parameters):
        """PIN Place에서 실제로 사용하는 값만 읽는다."""
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
                    parameters, ("place_force", "post_pin_place_force", "post_place_force"), 40.0, positive=True
                ),
                "contact_force": self._first_number(
                    parameters, ("place_contact_force", "post_pin_place_force_threshold", "post_place_force_threshold"), 20.0, positive=True
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

    def _post_pin_assembly_input(self, components):
        return self._assembly_input(
            components, self.POST_PIN_COMPONENT_PREFIX, "POST_PIN"
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
        self.node.get_logger().info("========== POST PICK START ==========")
        self._publish_cycle_event(
            operation_context, phase="POST_PICK", status="STARTED"
        )

        try:
            settings = self._load_pick_settings(parameters)
            component, pickup_pose = self._post_pickup_input(components)

            self.node.get_logger().info(
                f"Post Pick 시작 위치 이동 - {component.get('code')}"
            )
            self.movel(
                pickup_pose,
                vel=settings["speed"],
                acc=settings["acc"],
                ref=self.DR_BASE,
            )
            self.wait(0.5)

            self.motion.pick(
                distance=settings["pick_distance"],
                velocity=settings["speed"],
                acc=settings["acc"],
            )
            self.wait(0.5)

            self.node.get_logger().info("========== POST PICK COMPLETE ==========")
            self._publish_cycle_event(
                operation_context,
                phase="POST_PICK",
                status="COMPLETED",
                detail={"component_code": component.get("code")},
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

            self.node.get_logger().info(
                f"Post Place 시작 위치 이동 - {component.get('code')}"
            )
            self.movel(
                assembly_pose,
                vel=settings["speed"],
                acc=settings["acc"],
                ref=self.DR_BASE,
            )
            self.wait(0.5)

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
    # POST PIN PICK
    # =========================================================

    def pick_post_pin(self, parameters, components, operation_context=None):
        self.node.get_logger().info("========== POST PIN PICK START ==========")
        self._publish_cycle_event(
            operation_context, phase="POST_PIN_PICK", status="STARTED"
        )

        try:
            settings = self._load_pick_settings(parameters)
            componet, pickup_pose = (
                self._post_pin_pickup_input(components)
            )

            
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
            self.wait(0.5)

            self.node.get_logger().info("========== POST PIN PICK COMPLETE ==========")
            self._publish_cycle_event(
                operation_context,
                phase="CHECK",
                status="FAILED",
                error=error_message,
            )
            return False

        except Exception as e:
            self.node.get_logger().error(f"Post Pin Place 실패: {e}")
            self._publish_cycle_event(
                operation_context, phase="POST_PIN_PLACE", status="FAILED", error=e
            )
            self._publish_post_event(
                operation_context,
                phase="CHECK",
                status="FAILED",
                error=e,
            )
            raise


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
                self.node.get_logger().info(
                    f"Post Release 완료 -> BASE +Z {post_retreat}mm 이탈"
                )
                self.motion.move_z(
                    post_retreat,
                    ref=self.DR_BASE,
                    velocity=settings["speed"],
                    acc=settings["acc"],
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