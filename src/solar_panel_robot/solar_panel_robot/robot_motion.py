import time

from .config_loader import PoseLoader
from .force_control import ForceController

from DSR_ROBOT2 import (
    movej,
    movel,
    amovel,
    movesx,
    stop,
    check_motion,
    posj,
    posx,
    set_digital_output,
    wait,
    DR_BASE,
    DR_TOOL,
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
    ):

        movel(
            posx(
                0,
                0,
                distance,
                0,
                0,
                0,
            ),
            vel=self.velocity,
            acc=self.acc,
            ref=DR_BASE,
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
    ):

        print(
            f"[PICK] "
            f"velocity={self.velocity}, "
            f"acc={self.acc}, "
            f"distance={distance}",
            flush=True,
        )

        # 하강
        self.move_z(
            -distance
        )

        # 파지
        self.grasp()

        # 상승
        self.move_z(
            distance
        )

        print(
            "[PICK] 완료",
            flush=True,
        )


    def place(
        self,
        distance=50,
        force=15.0,
        contact_force=10.0,
        stiffness_z=500.0,
        timeout=5.0,
        search_velocity=10.0,
        search_acc=20.0,
        force_hold_time=1.0,
    ):
        """
        Force 기반 Place

        동작 순서
        1. TOOL -Z 방향으로 저속 비동기 하강(amovel)
        2. 하강 중 TOOL Z축 Force를 계속 확인
        3. contact_force 이상 감지 시 Soft Stop
        4. Compliance Control ON
        5. TOOL -Z 방향 Desired Force 적용
        6. force_hold_time 동안 압입
        7. Gripper Release
        8. Force / Compliance OFF
        9. BASE +Z 방향으로 상승

        distance:
            접촉 탐색 최대 하강 거리(mm) 및
            Place 완료 후 상승 거리(mm)

        force:
            접촉 이후 TOOL -Z 방향으로 가할
            Desired Force(N)

        contact_force:
            접촉으로 판단할 TOOL Z축 Force(N)

        stiffness_z:
            Z축 Compliance stiffness

        timeout:
            접촉 탐색 최대 시간(sec)

        search_velocity:
            접촉 탐색 하강 속도(mm/s)

        search_acc:
            접촉 탐색 하강 가속도(mm/s^2)

        force_hold_time:
            Force Control로 눌러 끼우는 시간(sec)
        """

        print(
            f"[PLACE] 시작 "
            f"search_distance={distance}mm, "
            f"contact_force={contact_force}N, "
            f"insert_force={force}N",
            flush=True,
        )

        contact_detected = False
        search_motion_started = False
        force_control_started = False

        try:

            # -----------------------------------------
            # 1. TOOL -Z 방향 접촉 탐색 시작
            # -----------------------------------------

            print(
                f"[PLACE] 접촉 탐색 시작 "
                f"TOOL -Z {distance}mm "
                f"(vel={search_velocity}, "
                f"acc={search_acc})",
                flush=True,
            )

            amovel(
                posx(
                    0,
                    0,
                    -distance,
                    0,
                    0,
                    0,
                ),
                vel=search_velocity,
                acc=search_acc,
                ref=DR_TOOL,
                mod=DR_MV_MOD_REL,
            )

            search_motion_started = True

            start_time = time.monotonic()


            # -----------------------------------------
            # 2. 이동 중 TOOL Z축 Force 지속 확인
            # -----------------------------------------

            while True:

                contact = self.force.check(
                    axis="z",
                    min_force=contact_force,
                    reference="tool",
                )

                if contact:

                    contact_detected = True

                    print(
                        f"[PLACE] 접촉 감지 "
                        f"|F_tool_z| >= "
                        f"{contact_force}N",
                        flush=True,
                    )

                    break


                # 목표 거리까지 갔는데 접촉이 없으면 실패
                motion_state = check_motion()

                if motion_state == 0:

                    raise RuntimeError(
                        "Place 접촉 감지 실패: "
                        f"TOOL -Z {distance}mm까지 "
                        "이동했지만 접촉이 감지되지 않았습니다."
                    )


                # Timeout 확인
                elapsed = (
                    time.monotonic()
                    - start_time
                )

                if elapsed >= timeout:

                    raise RuntimeError(
                        "Place 접촉 감지 실패: "
                        f"{timeout}초 동안 "
                        "접촉이 감지되지 않았습니다."
                    )

                wait(0.02)


            # -----------------------------------------
            # 3. 접촉 순간 진행 중 모션 정지
            # -----------------------------------------

            if contact_detected:

                print(
                    "[PLACE] 접촉 감지 -> Soft Stop",
                    flush=True,
                )

                stop(DR_SSTOP)

                # 실제 모션이 완전히 멈출 때까지 대기
                stop_wait_start = time.monotonic()

                while check_motion() != 0:

                    if (
                        time.monotonic()
                        - stop_wait_start
                    ) >= 2.0:

                        raise RuntimeError(
                            "Place 정지 실패: "
                            "Soft Stop 후에도 "
                            "모션이 종료되지 않았습니다."
                        )

                    wait(0.01)

                search_motion_started = False


            # -----------------------------------------
            # 4. Compliance Control ON
            # -----------------------------------------

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

            wait(0.2)


            # -----------------------------------------
            # 5. TOOL -Z 방향 Force 적용
            # -----------------------------------------

            print(
                f"[PLACE] TOOL -Z Force "
                f"{force}N 적용",
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


            # -----------------------------------------
            # 6. 일정 시간 Force로 압입
            # -----------------------------------------

            print(
                f"[PLACE] 압입 유지 "
                f"{force_hold_time}초",
                flush=True,
            )

            wait(force_hold_time)


            # -----------------------------------------
            # 7. 물체 놓기
            # -----------------------------------------

            print(
                "[PLACE] Gripper Release",
                flush=True,
            )

            self.release()

            wait(0.5)


        finally:

            # 접촉 탐색 중 예외가 발생했다면
            # 진행 중인 비동기 모션부터 정지
            if (
                search_motion_started
                and check_motion() != 0
            ):

                print(
                    "[PLACE] 예외 처리: "
                    "진행 중 모션 정지",
                    flush=True,
                )

                stop(DR_SSTOP)

                stop_wait_start = time.monotonic()

                while check_motion() != 0:

                    if (
                        time.monotonic()
                        - stop_wait_start
                    ) >= 2.0:
                        break

                    wait(0.01)


            # -----------------------------------------
            # 8. Force / Compliance OFF
            # -----------------------------------------

            if force_control_started:

                print(
                    "[PLACE] "
                    "Force Control 종료",
                    flush=True,
                )

            self.force.all_off()


        # ---------------------------------------------
        # 9. 위로 상승
        # ---------------------------------------------

        print(
            f"[PLACE] "
            f"BASE +Z 상승 {distance}mm",
            flush=True,
        )

        self.move_z(
            distance
        )

        print(
            "[PLACE] 완료",
            flush=True,
        )
