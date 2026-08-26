import math
import time

from .force_control import ForceController

from DSR_ROBOT2 import (
    movej,
    movel,
    movesx,
    get_tool_force,
    get_current_posx,
    posj,
    posx,
    set_digital_output,
    wait,
    DR_BASE,
    DR_TOOL,
    DR_MV_MOD_REL,
    DR_MV_MOD_ABS,
)


OFF = 0
ON = 1

# =========================================================
# Robot default configuration (YAML/config_loader 제거)
# =========================================================
# 작업별 speed/acc/좌표/Force 값은 SolarMotion이 DB에서 받아 각 함수에 전달한다.
# 아래 값은 로봇 공통 기본값과 초기 Home/Gripper 설정에만 사용한다.
DEFAULT_VELOCITY = 100.0
DEFAULT_ACC = 200.0
HOME_POSITION = [0.0, 0.0, 90.0, 0.0, 90.0, 0.0]
GRASP_PORT = 1
RELEASE_PORT = 2
GRIPPER_WAIT_TIME = 1.0


class RobotMotion:
    """
    로봇의 기본 이동, 그리퍼 제어, Force 기반 Place를 담당한다.
    """

    FORCE_AXIS_INDEX = {
        "x": 0,
        "y": 1,
        "z": 2,
    }

    def __init__(self):
        self.force = ForceController()

        # YAML 대신 robot_motion.py 내부 로봇 기본값 사용.
        # 작업 실행 시에는 DB에서 받은 speed/acc 등이 함수 인자로 전달되어
        # 이 기본값보다 우선한다.
        self.velocity = DEFAULT_VELOCITY
        self.acc = DEFAULT_ACC

        self.grasp_port = GRASP_PORT
        self.release_port = RELEASE_PORT
        self.gripper_wait_time = GRIPPER_WAIT_TIME

    # =========================================================
    # Gripper
    # =========================================================

    def grasp(self):
        print(
            "[GRIPPER] Grasp",
            flush=True,
        )

        set_digital_output(
            self.release_port,
            OFF,
        )
        set_digital_output(
            self.grasp_port,
            ON,
        )

        wait(self.gripper_wait_time)

    def release(self):
        print(
            "[GRIPPER] Release",
            flush=True,
        )

        set_digital_output(
            self.grasp_port,
            OFF,
        )
        set_digital_output(
            self.release_port,
            ON,
        )

        wait(self.gripper_wait_time)

    # =========================================================
    # Basic motion
    # =========================================================

    def move_home(self):
        """robot_motion.py에 고정된 기본 Home 관절 자세로 이동한다."""
        print(
            "[HOME] 이동 시작",
            flush=True,
        )

        home = posj(HOME_POSITION)

        movej(
            home,
            vel=self.velocity,
            acc=self.acc,
        )

        print(
            "[HOME] 이동 완료",
            flush=True,
        )

    def move_z(
        self,
        distance,
        ref=DR_BASE,
        velocity=None,
        acc=None,
    ):
        velocity = (
            self.velocity
            if velocity is None
            else float(velocity)
        )
        acc = (
            self.acc
            if acc is None
            else float(acc)
        )

        movel(
            posx(
                0,
                0,
                distance,
                0,
                0,
                0,
            ),
            vel=velocity,
            acc=acc,
            ref=ref,
            mod=DR_MV_MOD_REL,
        )

    def move_x(
        self,
        distance,
        ref=DR_TOOL,
        velocity=None,
        acc=None,
    ):
        """지정 좌표계의 X축으로 상대 이동한다."""

        velocity = (
            self.velocity
            if velocity is None
            else float(velocity)
        )
        acc = (
            self.acc
            if acc is None
            else float(acc)
        )

        movel(
            posx(
                distance,
                0,
                0,
                0,
                0,
                0,
            ),
            vel=velocity,
            acc=acc,
            ref=ref,
            mod=DR_MV_MOD_REL,
        )

    def move_xy(
        self,
        x,
        y,
        ref=DR_BASE,
        velocity=None,
        acc=None,
    ):
        """지정 좌표계의 X/Y축으로 상대 이동한다."""
        velocity = (
            self.velocity
            if velocity is None
            else float(velocity)
        )
        acc = (
            self.acc
            if acc is None
            else float(acc)
        )

        movel(
            posx(
                float(x),
                float(y),
                0,
                0,
                0,
                0,
            ),
            vel=velocity,
            acc=acc,
            ref=ref,
            mod=DR_MV_MOD_REL,
        )

    def move_pose(
        self,
        pose,
        ref=DR_BASE,
        velocity=None,
        acc=None,
    ):
        """6D 절대 pose로 이동한다. Search best 위치 복귀에 사용한다."""
        if pose is None or len(pose) != 6:
            raise ValueError("pose must contain 6 values")

        velocity = self.velocity if velocity is None else float(velocity)
        acc = self.acc if acc is None else float(acc)

        print(
            "[MOVE POSE ABS] "
            f"ref={'BASE' if ref == DR_BASE else ref}, "
            f"pose={[round(float(v), 3) for v in pose]}",
            flush=True,
        )

        movel(
            posx(*[float(v) for v in pose]),
            vel=velocity,
            acc=acc,
            ref=ref,
            mod=DR_MV_MOD_ABS,
        )

    # =========================================================
    # Arc motion
    # =========================================================

    def move_arc(
        self,
        start,
        end,
        height=100,
        steps=6,
    ):
        """
        start -> end 사이에 포물선 형태의 중간점을 생성하고
        movesx()로 spline 이동한다.
        """

        if steps < 2:
            raise ValueError(
                "steps must be 2 or greater"
            )

        if len(start) != 6 or len(end) != 6:
            raise ValueError(
                "start and end must contain 6 values"
            )

        points = []

        for i in range(1, steps + 1):
            t = float(i) / steps

            x = start[0] + (end[0] - start[0]) * t
            y = start[1] + (end[1] - start[1]) * t

            z_linear = (
                start[2]
                + (end[2] - start[2]) * t
            )
            z_arc = 4 * height * t * (1 - t)
            z = z_linear + z_arc

            rx = start[3] + (end[3] - start[3]) * t
            ry = start[4] + (end[4] - start[4]) * t
            rz = start[5] + (end[5] - start[5]) * t

            points.append(
                posx(
                    x,
                    y,
                    z,
                    rx,
                    ry,
                    rz,
                )
            )

        print(
            f"[ARC] spline 이동 시작: "
            f"height={height}, steps={steps}",
            flush=True,
        )

        movesx(
            points,
            v=self.velocity,
            a=self.acc,
            ref=DR_BASE,
        )

        print(
            "[ARC] spline 이동 완료",
            flush=True,
        )

    # =========================================================
    # Current Pose / Force Probe
    # =========================================================

    def get_current_pose(
        self,
        ref=DR_BASE,
    ):
        """현재 TCP pose를 지정 좌표계 기준으로 반환한다."""
        pose, solution_space = get_current_posx(
            ref=ref
        )

        values = [
            float(pose[i])
            for i in range(6)
        ]

        return values, int(solution_space)

    def seek_contact(
        self,
        axis="z",
        direction=1,
        force=8.0,
        threshold=5.0,
        max_travel=150.0,
        poll_interval=0.02,
        arm_delay=0.15,
        timeout=None,
        stiffness=None,
    ):
        """
        공중의 접근 위치에서 약한 Desired Force를 적용해 실제 접촉점을 찾는다.

        동작:
            1. TOOL 기준 Compliance ON
            2. baseline force / 시작 TCP pose 저장
            3. 지정 TOOL 축으로 Desired Force 적용
            4. 매 poll마다 pose / Fx,Fy,Fz / delta / travel 출력
            5. arm_delay 이후 선택 축 delta force가 threshold 이상이면 접촉
            6. max_travel 초과 시 실패 (시간 제한 없음)
            7. 성공/실패와 무관하게 Force / Compliance OFF

        반환 dict의 contact_pose는 Force가 켜진 상태에서 접촉을 감지한 순간의
        BASE TCP pose다. 상위 로직에서는 Force 해제 후 실제 현재 pose를 다시
        측정해 Search P0로 사용하는 것을 권장한다.
        """
        axis = str(axis).lower()
        direction = int(direction)
        force = float(force)
        threshold = float(threshold)
        max_travel = float(max_travel)
        poll_interval = float(poll_interval)
        arm_delay = float(arm_delay)
        timeout = None if timeout is None else float(timeout)

        if axis not in self.FORCE_AXIS_INDEX:
            raise ValueError(
                f"axis must be one of x, y, z: {axis}"
            )
        if direction not in (-1, 1):
            raise ValueError(
                "direction must be +1 or -1"
            )
        if force <= 0:
            raise ValueError(
                "force must be greater than 0"
            )
        if threshold <= 0:
            raise ValueError(
                "threshold must be greater than 0"
            )
        if max_travel <= 0:
            raise ValueError(
                "max_travel must be greater than 0"
            )
        if poll_interval <= 0:
            raise ValueError(
                "poll_interval must be greater than 0"
            )
        if arm_delay < 0:
            raise ValueError(
                "arm_delay must be >= 0"
            )
        if timeout is not None and timeout <= 0:
            raise ValueError(
                "timeout must be None or greater than 0"
            )

        axis_index = self.FORCE_AXIS_INDEX[axis]
        side_indices = [
            index
            for index in (0, 1, 2)
            if index != axis_index
        ]
        signed_force = direction * force
        direction_label = "+" if direction > 0 else "-"

        print(
            "========================================",
            flush=True,
        )
        print(
            f"[CONTACT SEEK] START axis=TOOL {axis.upper()}, "
            f"direction={direction_label}{axis.upper()}, "
            f"force={force:.2f}N, threshold={threshold:.2f}N, "
            f"max_travel={max_travel:.2f}mm, "
            f"timeout={'DISABLED' if timeout is None else f'{timeout:.2f}s'}",
            flush=True,
        )
        print(
            "========================================",
            flush=True,
        )

        try:
            self.force.compliance_on(
                stiffness=stiffness,
                reference="tool",
            )
            wait(0.15)

            baseline_force = [
                float(value)
                for value in get_tool_force(DR_TOOL)
            ]
            start_pose, solution_space = self.get_current_pose(
                ref=DR_BASE
            )

            print(
                "[CONTACT SEEK] Baseline "
                f"pose=[{', '.join(f'{v:.3f}' for v in start_pose)}] "
                f"solution_space={solution_space} "
                f"force=[Fx={baseline_force[0]:.3f}, "
                f"Fy={baseline_force[1]:.3f}, "
                f"Fz={baseline_force[2]:.3f}]N",
                flush=True,
            )

            self.force.force_on(
                forces={
                    axis: signed_force,
                },
                mode="relative",
                reference="tool",
            )

            start_time = time.monotonic()
            sample_index = 0

            while True:
                wait(poll_interval)
                sample_index += 1

                current_pose, _ = self.get_current_pose(
                    ref=DR_BASE
                )
                current_force = [
                    float(value)
                    for value in get_tool_force(DR_TOOL)
                ]

                elapsed = time.monotonic() - start_time
                travel_mm = math.sqrt(
                    sum(
                        (current_pose[i] - start_pose[i]) ** 2
                        for i in range(3)
                    )
                )
                force_delta = [
                    current_force[i] - baseline_force[i]
                    for i in range(3)
                ]
                axis_force_delta = abs(
                    force_delta[axis_index]
                )
                side_force_delta = math.sqrt(
                    sum(
                        force_delta[i] ** 2
                        for i in side_indices
                    )
                )

                print(
                    f"[CONTACT SAMPLE #{sample_index:04d}] "
                    f"t={elapsed:.3f}s "
                    f"pose=[{', '.join(f'{v:.3f}' for v in current_pose)}] "
                    f"force=[Fx={current_force[0]:.3f}, "
                    f"Fy={current_force[1]:.3f}, "
                    f"Fz={current_force[2]:.3f}]N "
                    f"delta=[dFx={force_delta[0]:+.3f}, "
                    f"dFy={force_delta[1]:+.3f}, "
                    f"dFz={force_delta[2]:+.3f}]N "
                    f"travel={travel_mm:.3f}mm "
                    f"side={side_force_delta:.3f}N "
                    f"axis_delta={axis_force_delta:.3f}N",
                    flush=True,
                )

                if (
                    elapsed >= arm_delay
                    and axis_force_delta >= threshold
                ):
                    result = {
                        "start_pose": list(start_pose),
                        "contact_pose": list(current_pose),
                        "baseline_force": list(baseline_force),
                        "contact_force": list(current_force),
                        "travel_mm": float(travel_mm),
                        "side_force_delta": float(side_force_delta),
                        "axis_force_delta": float(axis_force_delta),
                        "elapsed": float(elapsed),
                    }

                    print(
                        "",
                        flush=True,
                    )
                    print(
                        "========================================",
                        flush=True,
                    )
                    print(
                        "[CONTACT SEEK] CONTACT DETECTED",
                        flush=True,
                    )
                    print(
                        f"[CONTACT SEEK] contact_pose="
                        f"[{', '.join(f'{v:.3f}' for v in current_pose)}]",
                        flush=True,
                    )
                    print(
                        f"[CONTACT SEEK] travel={travel_mm:.3f}mm, "
                        f"axis_delta={axis_force_delta:.3f}N "
                        f">= {threshold:.3f}N, "
                        f"side={side_force_delta:.3f}N",
                        flush=True,
                    )
                    print(
                        "========================================",
                        flush=True,
                    )

                    return result

                if timeout is not None and elapsed >= timeout:
                    raise RuntimeError(
                        "[CONTACT SEEK] Timeout: "
                        f"{timeout:.2f}s, travel={travel_mm:.3f}mm, "
                        f"axis_delta={axis_force_delta:.3f}N"
                    )

                if travel_mm >= max_travel:
                    raise RuntimeError(
                        "[CONTACT SEEK] 최대 이동거리 초과: "
                        f"travel={travel_mm:.3f}mm >= "
                        f"max_travel={max_travel:.3f}mm, "
                        f"axis_delta={axis_force_delta:.3f}N"
                    )


        finally:
            print(
                "[CONTACT SEEK] Force / Compliance 종료",
                flush=True,
            )
            self.force.all_off()

    def probe_force(
        self,
        axis="z",
        direction=1,
        force=8.0,
        probe_time=0.30,
        max_travel=2.0,
        poll_interval=0.02,
        stiffness=None,
    ):
        """
        짧은 Desired Force를 걸어 후보 pose의 삽입 가능성을 측정한다.

        반환값:
            travel_mm:
                probe 시작 TCP 위치 대비 실제 이동 거리(mm)
            side_force_delta:
                Force 시작 전 baseline 대비 횡방향 힘 변화량(N)
            axis_force_delta:
                Force 축의 baseline 대비 힘 변화량(N)

        probe_time 또는 max_travel 중 먼저 도달하는 조건에서 종료하고
        Force / Compliance를 항상 해제한다.
        """
        axis = str(axis).lower()
        direction = int(direction)
        force = float(force)
        probe_time = float(probe_time)
        max_travel = float(max_travel)
        poll_interval = float(poll_interval)

        if axis not in self.FORCE_AXIS_INDEX:
            raise ValueError(
                f"axis must be one of x, y, z: {axis}"
            )
        if direction not in (-1, 1):
            raise ValueError(
                "direction must be +1 or -1"
            )
        if force <= 0:
            raise ValueError(
                "force must be greater than 0"
            )
        if probe_time <= 0:
            raise ValueError(
                "probe_time must be greater than 0"
            )
        if max_travel <= 0:
            raise ValueError(
                "max_travel must be greater than 0"
            )
        if poll_interval <= 0:
            raise ValueError(
                "poll_interval must be greater than 0"
            )

        axis_index = self.FORCE_AXIS_INDEX[axis]
        side_indices = [
            index
            for index in (0, 1, 2)
            if index != axis_index
        ]
        signed_force = direction * force

        result = None

        print(
            f"[PROBE] 시작 axis=TOOL {axis.upper()}, "
            f"direction={direction:+d}, "
            f"force={force:.2f}N, "
            f"probe_time={probe_time:.2f}s, "
            f"max_travel={max_travel:.2f}mm",
            flush=True,
        )

        try:
            self.force.compliance_on(
                stiffness=stiffness,
                reference="tool",
            )
            wait(0.15)

            baseline_force = [
                float(value)
                for value in get_tool_force(DR_TOOL)
            ]
            start_pose, _ = self.get_current_pose(
                ref=DR_BASE
            )

            print(
                "[PROBE] Baseline "
                f"pose=[{', '.join(f'{v:.3f}' for v in start_pose)}] "
                f"force=[Fx={baseline_force[0]:.3f}, "
                f"Fy={baseline_force[1]:.3f}, "
                f"Fz={baseline_force[2]:.3f}]N",
                flush=True,
            )

            # Probe를 걸기 전부터 삽입축 하중이 큰 경우에는
            # 이미 지그/부품에 강하게 걸린 후보로 보고 Desired Force를
            # 추가하지 않는다. set_desired_force()에서 멈추는 상황을 방지한다.
            baseline_axis_force_limit = max(20.0, force * 2.5)
            baseline_axis_force = abs(baseline_force[axis_index])
            if baseline_axis_force >= baseline_axis_force_limit:
                print(
                    f"[PROBE] SKIP - baseline {axis.upper()} force가 이미 큼: "
                    f"{baseline_axis_force:.3f}N >= "
                    f"{baseline_axis_force_limit:.3f}N",
                    flush=True,
                )
                result = {
                    "start_pose": list(start_pose),
                    "end_pose": list(start_pose),
                    "baseline_force": list(baseline_force),
                    "end_force": list(baseline_force),
                    "travel_mm": 0.0,
                    "side_force_delta": 0.0,
                    "axis_force_delta": 0.0,
                    "stopped_by_travel_limit": False,
                    "blocked_by_baseline": True,
                }
                return result

            self.force.force_on(
                forces={
                    axis: signed_force,
                },
                mode="relative",
                reference="tool",
            )

            start_time = time.monotonic()
            stopped_by_travel_limit = False
            end_pose = list(start_pose)
            end_force = list(baseline_force)
            travel_mm = 0.0
            sample_index = 0

            while True:
                wait(poll_interval)
                sample_index += 1

                end_pose, _ = self.get_current_pose(
                    ref=DR_BASE
                )
                end_force = [
                    float(value)
                    for value in get_tool_force(DR_TOOL)
                ]

                travel_mm = math.sqrt(
                    sum(
                        (end_pose[i] - start_pose[i]) ** 2
                        for i in range(3)
                    )
                )

                elapsed = time.monotonic() - start_time
                force_delta = [
                    end_force[i] - baseline_force[i]
                    for i in range(3)
                ]
                sample_side_force_delta = math.sqrt(
                    sum(
                        force_delta[i] ** 2
                        for i in side_indices
                    )
                )
                sample_axis_force_delta = abs(
                    force_delta[axis_index]
                )

                print(
                    f"[PROBE SAMPLE #{sample_index:03d}] "
                    f"t={elapsed:.3f}s "
                    f"pose=[{', '.join(f'{v:.3f}' for v in end_pose)}] "
                    f"force=[Fx={end_force[0]:.3f}, "
                    f"Fy={end_force[1]:.3f}, "
                    f"Fz={end_force[2]:.3f}]N "
                    f"delta=[dFx={force_delta[0]:+.3f}, "
                    f"dFy={force_delta[1]:+.3f}, "
                    f"dFz={force_delta[2]:+.3f}]N "
                    f"travel={travel_mm:.3f}mm "
                    f"side={sample_side_force_delta:.3f}N "
                    f"axis_delta={sample_axis_force_delta:.3f}N",
                    flush=True,
                )

                if travel_mm >= max_travel:
                    stopped_by_travel_limit = True
                    break

                if elapsed >= probe_time:
                    break

            side_force_delta = math.sqrt(
                sum(
                    (
                        end_force[i]
                        - baseline_force[i]
                    ) ** 2
                    for i in side_indices
                )
            )
            axis_force_delta = abs(
                end_force[axis_index]
                - baseline_force[axis_index]
            )

            result = {
                "start_pose": start_pose,
                "end_pose": end_pose,
                "baseline_force": baseline_force,
                "end_force": end_force,
                "travel_mm": float(travel_mm),
                "side_force_delta": float(side_force_delta),
                "axis_force_delta": float(axis_force_delta),
                "stopped_by_travel_limit": bool(
                    stopped_by_travel_limit
                ),
                "blocked_by_baseline": False,
            }

            print(
                f"[PROBE] 결과 travel={travel_mm:.3f}mm, "
                f"side_force_delta={side_force_delta:.3f}N, "
                f"axis_force_delta={axis_force_delta:.3f}N, "
                f"travel_limit={stopped_by_travel_limit}",
                flush=True,
            )

        finally:
            self.force.all_off()

        return result

    # =========================================================
    # Pick & Place
    # =========================================================

    def pick(
        self,
        distance=50,
        velocity=None,
        acc=None,
    ):
        velocity = (
            self.velocity
            if velocity is None
            else float(velocity)
        )
        acc = (
            self.acc
            if acc is None
            else float(acc)
        )

        print(
            f"[PICK] velocity={velocity}, "
            f"acc={acc}, distance={distance}",
            flush=True,
        )

        self.move_z(
            -distance,
            velocity=velocity,
            acc=acc,
        )

        self.grasp()

        self.move_z(
            distance,
            velocity=velocity,
            acc=acc,
        )

        print(
            "[PICK] 완료",
            flush=True,
        )

    def place(
        self,
        axis="z",
        direction=1,
        force=30.0,
        threshold=20.0,
        timeout=10.0,
        hold_time=0.0,
        poll_interval=0.02,
        arm_delay=0.10,
        stiffness=None,
    ):
        """
        TOOL 좌표계 Force 기반 범용 Place 삽입 동작.

        Post 예시:
            axis="z", direction=+1
            -> TOOL +Z 방향 Force 삽입, Delta Fz 감시

        Post Pin 예시:
            axis="x", direction=+1
            -> TOOL +X 방향 Force 삽입, Delta Fx 감시

        get_tool_force(DR_TOOL)로 시작점 대비 힘 변화량을 직접 측정한다.

        axis:
            "x", "y", "z" 중 Force를 적용할 TOOL 축.

        direction:
            +1이면 해당 TOOL 축의 +방향, -1이면 -방향.

        force:
            Desired Force의 크기(N). 양수 값만 입력한다.

        threshold:
            Force 시작점 대비 선택 축 힘 변화량의 절대값(N).
            이 값 이상인 상태가 hold_time 동안 연속 유지되면 완료로 판단한다.

        timeout:
            None이면 시간 제한 없이 threshold 조건을 기다린다.

        hold_time:
            threshold 이상 상태를 연속으로 유지해야 하는 시간(초).
            0이면 기존처럼 즉시 완료한다.
        """

        axis = str(axis).lower()
        direction = int(direction)
        force = float(force)
        threshold = float(threshold)
        timeout = None if timeout is None else float(timeout)
        hold_time = float(hold_time)
        poll_interval = float(poll_interval)
        arm_delay = float(arm_delay)

        if axis not in self.FORCE_AXIS_INDEX:
            raise ValueError(
                f"axis must be one of x, y, z: {axis}"
            )

        if direction not in (-1, 1):
            raise ValueError(
                "direction must be +1 or -1"
            )

        if force <= 0:
            raise ValueError(
                "force must be greater than 0"
            )

        if threshold <= 0:
            raise ValueError(
                "threshold must be greater than 0"
            )

        if timeout is not None and timeout <= 0:
            raise ValueError(
                "timeout must be None or greater than 0"
            )

        if hold_time < 0:
            raise ValueError(
                "hold_time must be >= 0"
            )

        if poll_interval <= 0:
            raise ValueError(
                "poll_interval must be greater than 0"
            )

        if arm_delay < 0:
            raise ValueError(
                "arm_delay must be >= 0"
            )

        axis_index = self.FORCE_AXIS_INDEX[axis]
        axis_label = axis.upper()
        signed_force = direction * force
        direction_label = "+" if direction > 0 else "-"

        print(
            f"[PLACE] 시작 axis=TOOL {axis_label}, "
            f"direction={direction_label}{axis_label}, "
            f"desired_force={force:.2f}N, "
            f"delta_threshold={threshold:.2f}N, "
            f"hold_time={hold_time:.2f}s, "
            f"timeout={'DISABLED' if timeout is None else f'{timeout:.2f}s'}",
            flush=True,
        )

        force_control_started = False

        try:
            # 1. TOOL 기준 Compliance Control
            print(
                "[PLACE] Compliance ON (reference=TOOL)",
                flush=True,
            )

            self.force.compliance_on(
                stiffness=stiffness,
                reference="tool",
            )

            wait(0.2)

            # 2. Force 적용 직전 선택 축의 baseline 저장
            baseline_force = [
                float(value)
                for value in get_tool_force(DR_TOOL)
            ]
            baseline_value = float(
                baseline_force[axis_index]
            )

            print(
                f"[PLACE] Baseline F{axis}={baseline_value:.2f}N "
                f"| force=[Fx={baseline_force[0]:.2f}, "
                f"Fy={baseline_force[1]:.2f}, "
                f"Fz={baseline_force[2]:.2f}]N",
                flush=True,
            )

            # 3. 선택한 TOOL 축에 Desired Force 적용
            print(
                f"[PLACE] TOOL {direction_label}{axis_label} "
                f"Desired Force {force:.2f}N 적용",
                flush=True,
            )

            self.force.force_on(
                forces={
                    axis: signed_force,
                },
                mode="relative",
                reference="tool",
            )

            force_control_started = True
            start_time = time.monotonic()

            if arm_delay > 0:
                wait(arm_delay)

            print(
                f"[PLACE] Delta Force 판정 시작 "
                f"|F{axis} - baseline| >= {threshold:.2f}N",
                flush=True,
            )

            # 본 삽입은 0.1초마다 Force 상태를 출력한다.
            log_interval = 0.10
            next_log_time = 0.0
            sample_index = 0
            threshold_start = None

            # 4. 선택 축의 힘 변화량을 직접 반복 측정
            while True:
                measured_force = [
                    float(value)
                    for value in get_tool_force(DR_TOOL)
                ]
                current_value = float(
                    measured_force[axis_index]
                )
                delta_force = abs(
                    current_value - baseline_value
                )
                elapsed = time.monotonic() - start_time
                sample_index += 1

                if elapsed >= next_log_time:
                    delta_xyz = [
                        measured_force[i] - baseline_force[i]
                        for i in range(3)
                    ]
                    print(
                        f"[PLACE SAMPLE #{sample_index:04d}] "
                        f"t={elapsed:.3f}s "
                        f"force=[Fx={measured_force[0]:.3f}, "
                        f"Fy={measured_force[1]:.3f}, "
                        f"Fz={measured_force[2]:.3f}]N "
                        f"delta=[dFx={delta_xyz[0]:+.3f}, "
                        f"dFy={delta_xyz[1]:+.3f}, "
                        f"dFz={delta_xyz[2]:+.3f}]N "
                        f"axis_delta={delta_force:.3f}N / "
                        f"threshold={threshold:.3f}N",
                        flush=True,
                    )
                    next_log_time += log_interval

                if delta_force >= threshold:
                    if threshold_start is None:
                        threshold_start = time.monotonic()

                    held = time.monotonic() - threshold_start

                    if held >= hold_time:
                        print(
                            "",
                            flush=True,
                        )
                        print(
                            "========================================",
                            flush=True,
                        )
                        print(
                            "[PLACE] COMPLETE - 삽입 Force 유지 조건 만족",
                            flush=True,
                        )
                        print(
                            f"[PLACE] Axis=TOOL {axis_label}",
                            flush=True,
                        )
                        print(
                            f"[PLACE] Baseline F{axis}="
                            f"{baseline_value:.2f}N",
                            flush=True,
                        )
                        print(
                            f"[PLACE] Current F{axis}="
                            f"{current_value:.2f}N",
                            flush=True,
                        )
                        print(
                            f"[PLACE] Delta F{axis}="
                            f"{delta_force:.2f}N "
                            f">= {threshold:.2f}N",
                            flush=True,
                        )
                        print(
                            f"[PLACE] Threshold hold="
                            f"{held:.3f}s >= {hold_time:.3f}s",
                            flush=True,
                        )
                        print(
                            "========================================",
                            flush=True,
                        )

                        return True
                else:
                    # threshold 아래로 떨어지면 연속 유지시간을 처음부터 다시 센다.
                    threshold_start = None

                if timeout is not None and elapsed >= timeout:
                    raise RuntimeError(
                        "[PLACE] Delta Force threshold Timeout: "
                        f"{timeout:.1f}초 동안 "
                        f"|F{axis} - baseline| >= "
                        f"{threshold:.2f}N 조건을 만족하지 "
                        "못했습니다. "
                        f"baseline={baseline_value:.2f}N, "
                        f"current={current_value:.2f}N, "
                        f"delta={delta_force:.2f}N"
                    )

                wait(poll_interval)

        finally:
            if force_control_started:
                print(
                    "[PLACE] Force Control 종료",
                    flush=True,
                )

            # 성공/실패와 관계없이 Force와 Compliance를 반드시 해제한다.
            self.force.all_off()