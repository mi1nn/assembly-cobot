import time

import rclpy
import DR_init

from dsr_msgs2.srv import MoveStop

from .config_loader import PoseLoader
from .force_control import ForceController

from DSR_ROBOT2 import (
    movej,
    movel,
    amovel,
    movesx,
    check_motion,
    get_current_posx,
    get_tool_force,
    posj,
    posx,
    set_digital_output,
    wait,
    DR_BASE,
    DR_TOOL,
    DR_MV_MOD_ABS,
    DR_MV_MOD_REL,
    DR_SSTOP,
)


OFF = 0
ON = 1


class RobotMotion:
    """
    로봇의 기본 이동과 단순 그리퍼 제어를 담당
    """

    def __init__(self):

        self.config = PoseLoader()

        # Force Controller
        self.force = ForceController()

        # DSR ROS2 node
        # 클래스 내부에서 DR_init.__dsr__node를 직접 쓰면
        # Python name mangling으로 _RobotMotion__dsr__node가 되므로
        # getattr()로 가져와 보관한다.
        self.dsr_node = getattr(
            DR_init,
            "__dsr__node",
        )

        # MoveStop service client
        # 현재 DSR_ROBOT2 환경의 service prefix:
        # /dsr01/dsr_controller2/...
        self.stop_client = self.dsr_node.create_client(
            MoveStop,
            "dsr_controller2/motion/move_stop",
        )

        # Robot motion settings
        self.velocity = self.config.get_velocity()
        self.acc = self.config.get_acc()

        # Gripper settings
        self.grasp_port = self.config.get_grasp_port()
        self.release_port = self.config.get_release_port()
        self.gripper_wait_time = (
            self.config.get_gripper_wait_time()
        )

    # =========================================================
    # Motion Stop
    # =========================================================

    def stop_motion(
        self,
        mode=DR_SSTOP,
        timeout=2.0,
    ):
        """
        진행 중인 Robot Motion을 MoveStop ROS2 service로 정지한다.

        mode:
            DR_SSTOP 등 Doosan stop mode

        timeout:
            service 대기 및 응답 최대 시간(sec)
        """

        print(
            f"[MOTION STOP] 요청 mode={mode}",
            flush=True,
        )

        if not self.stop_client.wait_for_service(
            timeout_sec=timeout
        ):
            raise RuntimeError(
                "MoveStop service를 찾을 수 없습니다: "
                "/dsr01/dsr_controller2/motion/move_stop"
            )

        request = MoveStop.Request()
        request.stop_mode = int(mode)

        future = self.stop_client.call_async(
            request
        )

        rclpy.spin_until_future_complete(
            self.dsr_node,
            future,
            timeout_sec=timeout,
        )

        if not future.done():
            raise RuntimeError(
                "MoveStop service 응답 Timeout"
            )

        try:
            result = future.result()

        except Exception as e:
            raise RuntimeError(
                f"MoveStop service 호출 실패: {e}"
            ) from e

        if result is None:
            raise RuntimeError(
                "MoveStop service 응답이 없습니다."
            )

        if not result.success:
            raise RuntimeError(
                "Robot Motion 정지 실패"
            )

        print(
            "[MOTION STOP] 완료",
            flush=True,
        )

        return True

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

        wait(
            self.gripper_wait_time
        )

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

        wait(
            self.gripper_wait_time
        )

    # =========================================================
    # Basic motion
    # =========================================================

    def move_home(self):

        pose = self.config.get(
            "home"
        )

        if pose["type"] != "joint":
            raise ValueError(
                "Pose 'home' must be joint type"
            )

        print(
            "[HOME] 이동 시작",
            flush=True,
        )

        home = posj(
            pose["position"]
        )

        movej(
            home,
            vel=self.velocity,
            acc=self.acc,
        )

        print(
            "[HOME] 이동 완료",
            flush=True,
        )

    def make_target_ready(
        self,
        pose_name,
        approach_height,
    ):

        pose = self.config.get(
            pose_name
        )

        if pose["type"] != "task":
            raise ValueError(
                f"Pose '{pose_name}' "
                f"must be task type"
            )

        target_position = (
            pose["position"].copy()
        )

        ready_position = (
            pose["position"].copy()
        )

        ready_position[2] += (
            approach_height
        )

        target = posx(
            target_position
        )

        ready = posx(
            ready_position
        )

        return target, ready

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
        start -> end 사이에 포물선 형태의
        중간점을 생성한 뒤 movesx()로 spline 이동한다.

        start, end:
            [x, y, z, rx, ry, rz]

        height:
            궤적의 최대 추가 높이(mm)

        steps:
            생성할 spline point 개수
        """

        if steps < 2:
            raise ValueError(
                "steps must be 2 or greater"
            )

        if (
            len(start) != 6
            or len(end) != 6
        ):
            raise ValueError(
                "start and end must "
                "contain 6 values"
            )

        points = []

        for i in range(
            1,
            steps + 1,
        ):

            t = (
                float(i)
                / steps
            )

            x = (
                start[0]
                + (
                    end[0]
                    - start[0]
                )
                * t
            )

            y = (
                start[1]
                + (
                    end[1]
                    - start[1]
                )
                * t
            )

            z_linear = (
                start[2]
                + (
                    end[2]
                    - start[2]
                )
                * t
            )

            z_arc = (
                4
                * height
                * t
                * (1 - t)
            )

            z = (
                z_linear
                + z_arc
            )

            rx = (
                start[3]
                + (
                    end[3]
                    - start[3]
                )
                * t
            )

            ry = (
                start[4]
                + (
                    end[4]
                    - start[4]
                )
                * t
            )

            rz = (
                start[5]
                + (
                    end[5]
                    - start[5]
                )
                * t
            )

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
            f"height={height}, "
            f"steps={steps}",
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
            f"[PICK] "
            f"velocity={velocity}, "
            f"acc={acc}, "
            f"distance={distance}",
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
        distance=50,
        search_limit_z=0.0,
        force=40.0,
        contact_force=20.0,
        insert_force=12.0,
        stiffness_z=500.0,
        search_velocity=10.0,
        search_acc=20.0,
        search_timeout=None,
        insert_timeout=3.0,
    ):
        """
        Force 기반 Place

        동작 순서

        1. 현재 Base 기준 TCP 위치 확인
        2. 비접촉 상태의 TOOL Fz를 baseline으로 저장
        3. 현재 X/Y/Rx/Ry/Rz 유지
           Base Z=search_limit_z까지 amovel 하강
        4. TOOL Z Force로 최초 접촉 확인
        5. 1단계 Force 값 터미널 1회 출력
        6. Soft Stop
        7. Compliance Control ON
        8. TOOL -Z 방향 Desired Force 적용
        9. 압입 Force 확인
        10. 2단계 Force 값 터미널 1회 출력
        11. Force / Compliance OFF
        12. Gripper를 닫은 상태로 Post Check 단계에 제어권 반환

        주의:
            Gripper Release와 BASE +Z 이탈은 이 함수에서 수행하지 않는다.
            상위 SolarMotion.install_post()에서 Frame Check 성공 후 수행한다.

        distance:
            Post Check 성공 후 사용할 권장 이탈 거리(mm).
            이 함수 내부에서는 상승하지 않고 값을 반환한다.

        search_limit_z:
            접촉이 없을 경우 허용할
            Base 기준 최저 Z 좌표(mm)

        force:
            접촉 이후 TOOL -Z 방향으로
            가할 Desired Force(N)

        contact_force:
            최초 접촉으로 판단할
            TOOL Z축 Force(N)

        insert_force:
            압입이 진행됐다고 판단할
            TOOL Z축 Force(N)

        stiffness_z:
            TOOL Z축 Compliance stiffness

        search_velocity:
            접촉 탐색 하강 속도(mm/s)

        search_acc:
            접촉 탐색 하강 가속도(mm/s^2)

        search_timeout:
            접촉 탐색 최대 시간(sec)
            None이면 이동거리와 속도로 자동 계산

        insert_timeout:
            Force Control 이후
            insert_force 도달 최대 시간(sec)
        """

        print(
            f"[PLACE] 시작 "
            f"search_limit_z={search_limit_z}mm, "
            f"contact_force={contact_force}N, "
            f"desired_force={force}N, "
            f"insert_force={insert_force}N",
            flush=True,
        )

        contact_detected = False
        search_motion_started = False
        force_control_started = False

        try:

            # =================================================
            # 1. 현재 Base 기준 TCP 위치 확인
            # =================================================

            current_pose, _ = get_current_posx(
                DR_BASE
            )

            current_z = float(
                current_pose[2]
            )

            print(
                f"[PLACE] 현재 TCP "
                f"Base Z={current_z:.2f}mm",
                flush=True,
            )

            if current_z <= search_limit_z:

                raise RuntimeError(
                    "[PLACE] 현재 TCP Z가 "
                    "탐색 한계 이하입니다. "
                    f"current_z={current_z:.2f}, "
                    f"search_limit_z={search_limit_z:.2f}"
                )

            # =================================================
            # 2. 비접촉 상태의 TOOL Fz를 baseline으로 저장
            # =================================================

            print(
                "[PLACE] Force baseline 측정",
                flush=True,
            )

            # 이전 모션의 진동이 가라앉도록 대기
            wait(1.0)

            baseline_force = get_tool_force(
                DR_TOOL
            )

            baseline_fz = float(
                baseline_force[2]
            )

            print(
                f"[PLACE] baseline Fz="
                f"{baseline_fz:.2f}N",
                flush=True,
            )

            # =================================================
            # 3. Base Z=search_limit_z까지
            #    비동기 절대좌표 하강
            # =================================================

            search_target = posx(
                current_pose[0],
                current_pose[1],
                search_limit_z,
                current_pose[3],
                current_pose[4],
                current_pose[5],
            )

            print(
                f"[PLACE] 접촉 탐색 시작 "
                f"Base Z "
                f"{current_z:.2f} -> "
                f"{search_limit_z:.2f}mm "
                f"(vel={search_velocity}, "
                f"acc={search_acc})",
                flush=True,
            )

            amovel(
                search_target,
                vel=search_velocity,
                acc=search_acc,
                ref=DR_BASE,
                mod=DR_MV_MOD_ABS,
            )

            search_motion_started = True

            # 비동기 모션 시작 후 상태 반영 대기
            wait(0.02)

            start_time = time.monotonic()

            # =================================================
            # 접촉 탐색 Timeout 계산
            # =================================================

            if search_timeout is None:

                if search_velocity <= 0:

                    raise ValueError(
                        "search_velocity must be greater than 0"
                    )

                search_distance = (
                    current_z
                    - search_limit_z
                )

                calculated_timeout = (
                    search_distance
                    / search_velocity
                    + 5.0
                )

            else:

                calculated_timeout = (
                    search_timeout
                )

            print(
                f"[PLACE] 접촉 탐색 Timeout="
                f"{calculated_timeout:.2f}s",
                flush=True,
            )

            # =================================================
            # 4. 1단계
            #    amovel 중 최초 접촉 Force 확인
            # =================================================

            while True:

                stage1_force = get_tool_force(
                    DR_TOOL
                )

                current_fz = float(
                    stage1_force[2]
                )

                delta_fz = abs(
                    current_fz
                    - baseline_fz
                )

                contact = (
                    delta_fz
                    >= contact_force
                )

                # -------------------------------------------------
                # 접촉 Force 변화량 도달
                # -------------------------------------------------

                if contact:

                    contact_detected = True

                    print(
                        "",
                        flush=True,
                    )

                    print(
                        "========================================",
                        flush=True,
                    )

                    print(
                        "[PLACE][1단계] 최초 접촉 감지",
                        flush=True,
                    )

                    print(
                        f"[PLACE][1단계] 기준: "
                        f"|ΔF_tool_z| >= "
                        f"{contact_force:.2f}N",
                        flush=True,
                    )

                    print(
                        f"[PLACE][1단계] "
                        f"baseline Fz={baseline_fz:.2f}N, "
                        f"current Fz={current_fz:.2f}N, "
                        f"delta Fz={delta_fz:.2f}N",
                        flush=True,
                    )

                    print(
                        f"[PLACE][1단계] Force "
                        f"Fx={stage1_force[0]:.2f}N, "
                        f"Fy={stage1_force[1]:.2f}N, "
                        f"Fz={stage1_force[2]:.2f}N",
                        flush=True,
                    )

                    print(
                        f"[PLACE][1단계] Moment "
                        f"Mx={stage1_force[3]:.2f}Nm, "
                        f"My={stage1_force[4]:.2f}Nm, "
                        f"Mz={stage1_force[5]:.2f}Nm",
                        flush=True,
                    )

                    print(
                        "========================================",
                        flush=True,
                    )

                    print(
                        "",
                        flush=True,
                    )

                    break

                # -------------------------------------------------
                # Z=search_limit_z까지 갔는데 접촉 없음
                # -------------------------------------------------

                motion_state = check_motion()

                if motion_state == 0:

                    raise RuntimeError(
                        "[PLACE] 접촉 감지 실패: "
                        f"Base Z={search_limit_z}mm까지 "
                        "이동했지만 접촉이 "
                        "감지되지 않았습니다."
                    )

                # -------------------------------------------------
                # Timeout
                # -------------------------------------------------

                elapsed = (
                    time.monotonic()
                    - start_time
                )

                if elapsed >= calculated_timeout:

                    raise RuntimeError(
                        "[PLACE] 접촉 탐색 Timeout: "
                        f"{calculated_timeout:.2f}초 동안 "
                        "접촉이 감지되지 않았습니다."
                    )

                wait(0.02)

            # =================================================
            # 5. 최초 접촉 -> amovel Soft Stop
            # =================================================

            if contact_detected:

                print(
                    "[PLACE] 1단계 접촉 감지 "
                    "-> Soft Stop",
                    flush=True,
                )

                self.stop_motion(
                    DR_SSTOP
                )

                stop_wait_start = (
                    time.monotonic()
                )

                # 실제 모션이 완전히 멈출 때까지 대기
                while check_motion() != 0:

                    if (
                        time.monotonic()
                        - stop_wait_start
                    ) >= 2.0:

                        raise RuntimeError(
                            "[PLACE] 정지 실패: "
                            "Soft Stop 후에도 "
                            "모션이 종료되지 않았습니다."
                        )

                    wait(0.01)

                search_motion_started = False

                # 접촉 당시 정지 위치 확인
                stopped_pose, _ = get_current_posx(
                    DR_BASE
                )

                print(
                    f"[PLACE] 접촉 후 정지 위치 "
                    f"Base Z="
                    f"{float(stopped_pose[2]):.2f}mm",
                    flush=True,
                )

            # =================================================
            # 6. Compliance Control ON
            # =================================================

            print(
                "[PLACE] Compliance ON "
                "(reference=TOOL)",
                flush=True,
            )

            self.force.compliance_on(
                stiffness={
                    "z": stiffness_z,
                },
                reference="tool",
            )

            # Compliance 상태가 안정된 뒤 Desired Force 적용
            wait(0.5)

            # =================================================
            # 7. TOOL -Z Desired Force 적용
            # =================================================

            print(
                f"[PLACE] TOOL -Z "
                f"Desired Force "
                f"{force:.2f}N 적용",
                flush=True,
            )

            self.force.force_on(
                forces={
                    "z": -force,
                },
                mode="relative",
                reference="tool",
            )

            force_control_started = True

            # =================================================
            # 8. 2단계
            #    압입 Force 도달 확인
            # =================================================

            print(
                f"[PLACE] 2단계 압입 확인 시작 "
                f"|F_tool_z| >= "
                f"{insert_force:.2f}N",
                flush=True,
            )

            insert_start = (
                time.monotonic()
            )

            while True:

                inserted = self.force.check(
                    axis="z",
                    min_force=insert_force,
                    reference="tool",
                )

                # -------------------------------------------------
                # 압입 Force 도달
                # -------------------------------------------------

                if inserted:

                    # 2단계 조건이 만족된 바로 이 시점의
                    # TOOL 기준 실제 Force를 1회 읽음
                    stage2_force = get_tool_force(
                        DR_TOOL
                    )

                    print(
                        "",
                        flush=True,
                    )

                    print(
                        "========================================",
                        flush=True,
                    )

                    print(
                        "[PLACE][2단계] 압입 Force 도달",
                        flush=True,
                    )

                    print(
                        f"[PLACE][2단계] 기준: "
                        f"|F_tool_z| >= "
                        f"{insert_force:.2f}N",
                        flush=True,
                    )

                    print(
                        f"[PLACE][2단계] Force "
                        f"Fx={stage2_force[0]:.2f}N, "
                        f"Fy={stage2_force[1]:.2f}N, "
                        f"Fz={stage2_force[2]:.2f}N",
                        flush=True,
                    )

                    print(
                        f"[PLACE][2단계] Moment "
                        f"Mx={stage2_force[3]:.2f}Nm, "
                        f"My={stage2_force[4]:.2f}Nm, "
                        f"Mz={stage2_force[5]:.2f}Nm",
                        flush=True,
                    )

                    print(
                        "========================================",
                        flush=True,
                    )

                    print(
                        "",
                        flush=True,
                    )

                    break

                # -------------------------------------------------
                # 압입 Timeout
                # -------------------------------------------------

                elapsed = (
                    time.monotonic()
                    - insert_start
                )

                if elapsed >= insert_timeout:

                    # 실패 시점 Force도 디버깅을 위해 1회 출력
                    timeout_force = get_tool_force(
                        DR_TOOL
                    )

                    print(
                        f"[PLACE][2단계][TIMEOUT] "
                        f"Fx={timeout_force[0]:.2f}N, "
                        f"Fy={timeout_force[1]:.2f}N, "
                        f"Fz={timeout_force[2]:.2f}N",
                        flush=True,
                    )

                    raise RuntimeError(
                        "[PLACE] 압입 실패: "
                        f"{insert_timeout}초 동안 "
                        f"{insert_force}N에 "
                        "도달하지 못했습니다."
                    )

                wait(0.02)

        finally:

            # =================================================
            # 예외 발생 시 비동기 탐색 모션 정지
            # =================================================

            if (
                search_motion_started
                and check_motion() != 0
            ):

                print(
                    "[PLACE] 예외 처리: "
                    "진행 중 탐색 모션 정지",
                    flush=True,
                )

                self.stop_motion(
                    DR_SSTOP
                )

                stop_wait_start = (
                    time.monotonic()
                )

                while check_motion() != 0:

                    if (
                        time.monotonic()
                        - stop_wait_start
                    ) >= 2.0:

                        break

                    wait(0.01)

            # =================================================
            # 10. Force / Compliance OFF
            # =================================================

            if force_control_started:

                print(
                    "[PLACE] Force Control 종료",
                    flush=True,
                )

            self.force.all_off()


        # =====================================================
        # Place Force 단계 완료
        #
        # Frame Check가 끝날 때까지 Gripper는 닫힌 상태를 유지한다.
        # Gripper Release와 BASE +Z 이탈은 SolarMotion.install_post()
        # 에서 Frame Check 성공 후 수행한다.
        # =====================================================

        print(
            "[PLACE] 2단계 Force 압입 완료 - Gripper 유지",
            flush=True,
        )

        print(
            "[PLACE] Post Check 단계 대기",
            flush=True,
        )

        return float(distance)

    def check_force_move(
        self,
        distance=50.0,
        force_threshold=50.0,
        velocity=10.0,
        acc=20.0,
        label="POST CHECK",
    ):
        """
        TOOL Z 방향으로 최대 distance만큼 비동기 이동하면서
        실제 TOOL Z축 Force 절대값을 검사한다.

        distance:
            TOOL Z 방향 최대 탐색 거리(mm)
            +값이면 TOOL +Z
            -값이면 TOOL -Z

        force_threshold:
            성공으로 판단할 실제 TOOL Z축 Force 절대값(N)

        label:
            터미널 로그 구분용 이름.
            예: "POST CHECK", "PIN INSERT"

        return:
            True  -> 이동 중 |F_tool_z| >= force_threshold 감지
            False -> 최대 거리까지 이동했지만 threshold 미감지

        성공/실패 모두 시작 위치로 자동 복귀하지 않는다.
        실패 시 최대 이동 위치에서 그대로 정지한다.
        """

        prefix = f"[{label}]"

        print(
            f"{prefix} 시작 "
            f"distance={distance}mm, "
            f"threshold={force_threshold}N",
            flush=True,
        )

        motion_started = False

        try:
            # =====================================================
            # 1. 이동 시작 전 Force 확인
            # =====================================================

            start_force = get_tool_force(
                DR_TOOL
            )

            print(
                f"{prefix} 시작 Force "
                f"Fz={float(start_force[2]):.2f}N",
                flush=True,
            )

            # =====================================================
            # 2. TOOL Z 방향 비동기 이동
            # =====================================================

            print(
                f"{prefix} TOOL Z 방향 "
                f"{distance}mm 탐색 시작",
                flush=True,
            )

            amovel(
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
                ref=DR_TOOL,
                mod=DR_MV_MOD_REL,
            )

            motion_started = True
            wait(0.02)

            # =====================================================
            # 3. 이동 중 실제 TOOL Fz 확인
            # =====================================================

            while True:
                force_value = get_tool_force(
                    DR_TOOL
                )

                current_fz = float(
                    force_value[2]
                )

                abs_fz = abs(
                    current_fz
                )

                # -------------------------------------------------
                # Force threshold 도달 -> 즉시 정지 + 성공
                # -------------------------------------------------

                if abs_fz >= force_threshold:
                    print(
                        "",
                        flush=True,
                    )

                    print(
                        "========================================",
                        flush=True,
                    )

                    print(
                        f"{prefix} SUCCESS - Force threshold 감지",
                        flush=True,
                    )

                    print(
                        f"{prefix} 기준: "
                        f"|F_tool_z| >= {force_threshold:.2f}N",
                        flush=True,
                    )

                    print(
                        f"{prefix} 현재: "
                        f"Fz={current_fz:.2f}N, "
                        f"|Fz|={abs_fz:.2f}N",
                        flush=True,
                    )

                    print(
                        f"{prefix} Force "
                        f"Fx={force_value[0]:.2f}N, "
                        f"Fy={force_value[1]:.2f}N, "
                        f"Fz={force_value[2]:.2f}N",
                        flush=True,
                    )

                    print(
                        f"{prefix} Moment "
                        f"Mx={force_value[3]:.2f}Nm, "
                        f"My={force_value[4]:.2f}Nm, "
                        f"Mz={force_value[5]:.2f}Nm",
                        flush=True,
                    )

                    print(
                        "========================================",
                        flush=True,
                    )

                    # threshold 감지 순간 즉시 정지
                    self.stop_motion(
                        DR_SSTOP
                    )

                    stop_wait_start = time.monotonic()

                    while check_motion() != 0:
                        if (
                            time.monotonic()
                            - stop_wait_start
                        ) >= 2.0:
                            raise RuntimeError(
                                f"{label} 정지 실패"
                            )

                        wait(0.01)

                    motion_started = False

                    print(
                        f"{prefix} 감지 위치에서 정지 유지",
                        flush=True,
                    )

                    return True

                # -------------------------------------------------
                # 최대 거리 이동 완료 -> 현재 위치 유지 + 실패
                # -------------------------------------------------

                if check_motion() == 0:
                    motion_started = False

                    final_force = get_tool_force(
                        DR_TOOL
                    )

                    final_fz = float(
                        final_force[2]
                    )

                    final_abs_fz = abs(
                        final_fz
                    )

                    print(
                        "",
                        flush=True,
                    )

                    print(
                        "========================================",
                        flush=True,
                    )

                    print(
                        f"{prefix}[ERROR] Force threshold 미감지",
                        flush=True,
                    )

                    print(
                        f"{prefix}[ERROR] "
                        f"{distance}mm 이동하는 동안 "
                        f"|F_tool_z| >= {force_threshold:.2f}N "
                        "조건을 만족하지 못했습니다.",
                        flush=True,
                    )

                    print(
                        f"{prefix}[ERROR] 최종 Force: "
                        f"Fz={final_fz:.2f}N, "
                        f"|Fz|={final_abs_fz:.2f}N",
                        flush=True,
                    )

                    print(
                        f"{prefix}[ERROR] 현재 위치에서 작업을 중단합니다.",
                        flush=True,
                    )

                    print(
                        "========================================",
                        flush=True,
                    )

                    return False

                wait(0.02)

        finally:
            # =====================================================
            # 예외 발생 시 진행 중인 비동기 모션만 정지
            # 위치 복귀는 하지 않는다.
            # =====================================================

            if (
                motion_started
                and check_motion() != 0
            ):
                print(
                    f"{prefix}[ERROR] 예외 발생 - 진행 중 모션 정지",
                    flush=True,
                )

                self.stop_motion(
                    DR_SSTOP
                )

                stop_wait_start = time.monotonic()

                while check_motion() != 0:
                    if (
                        time.monotonic()
                        - stop_wait_start
                    ) >= 2.0:
                        break

                    wait(0.01)