from .config_loader import PoseLoader

from DSR_ROBOT2 import (
    movej,
    movel,
    movesx,
    posj,
    posx,
    set_digital_output,
    wait,
    DR_BASE,
    DR_MV_MOD_REL,
)

OFF = 0
ON = 1


class RobotMotion:
    """
    로봇의 기본 이동과 단순 그리퍼 제어를 담당
    """

    def __init__(self):
        self.config = PoseLoader()

        # Robot motion settings
        self.velocity = self.config.get_velocity()
        self.acc = self.config.get_acc()

        # Gripper settings
        self.grasp_port = self.config.get_grasp_port()
        self.release_port = self.config.get_release_port()
        self.gripper_wait_time = self.config.get_gripper_wait_time()


    # Gripper

    def grasp(self):
        print("[GRIPPER] Grasp", flush=True)

        set_digital_output(self.release_port, OFF)
        set_digital_output(self.grasp_port, ON)

        wait(self.gripper_wait_time)

    def release(self):
        print("[GRIPPER] Release", flush=True)

        set_digital_output(self.grasp_port, OFF)
        set_digital_output(self.release_port, ON)

        wait(self.gripper_wait_time)


    # Basic motion

    def move_home(self):
        pose = self.config.get("home")

        if pose["type"] != "joint":
            raise ValueError("Pose 'home' must be joint type")

        print("[HOME] 이동 시작", flush=True)

        home = posj(pose["position"])

        movej(
            home,
            vel=self.velocity,
            acc=self.acc,
        )

        print("[HOME] 이동 완료", flush=True)

    def make_target_ready(self, pose_name, approach_height):
        pose = self.config.get(pose_name)

        if pose["type"] != "task":
            raise ValueError(f"Pose '{pose_name}' must be task type")

        target_position = pose["position"].copy()
        ready_position = pose["position"].copy()

        ready_position[2] += approach_height

        target = posx(target_position)
        ready = posx(ready_position)

        return target, ready

    def move_z(self, distance):
        movel(
            posx(0, 0, distance, 0, 0, 0),
            vel=self.velocity,
            acc=self.acc,
            ref=DR_BASE,
            mod=DR_MV_MOD_REL,
        )

    def move_arc(self, start, end, height=100, steps=6):
            """
            start -> end 사이에 포물선 형태의 중간점을 생성한 뒤
            movesx()로 spline 이동한다.

            start, end:
                [x, y, z, rx, ry, rz]

            height:
                궤적의 최대 추가 높이(mm)

            steps:
                생성할 spline point 개수
            """
            if steps < 2:
                raise ValueError("steps must be 2 or greater")

            if len(start) != 6 or len(end) != 6:
                raise ValueError("start and end must contain 6 values")

            points = []

            for i in range(1, steps + 1):
                t = float(i) / steps

                x = start[0] + (end[0] - start[0]) * t
                y = start[1] + (end[1] - start[1]) * t

                z_linear = start[2] + (end[2] - start[2]) * t
                z_arc = 4 * height * t * (1 - t)
                z = z_linear + z_arc

                rx = start[3] + (end[3] - start[3]) * t
                ry = start[4] + (end[4] - start[4]) * t
                rz = start[5] + (end[5] - start[5]) * t

                points.append(posx(x, y, z, rx, ry, rz))

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

            print("[ARC] spline 이동 완료", flush=True)


    # Pick & Place

    def pick(self, distance=50):
        print(
            f"[PICK] velocity={self.velocity}, "
            f"acc={self.acc}, distance={distance}",
            flush=True,
        )

        self.move_z(-distance)
        self.grasp()
        self.move_z(distance)

        print("[PICK] 완료", flush=True)

    def place(self, distance=50):
        print(
            f"[PLACE] velocity={self.velocity}, "
            f"acc={self.acc}, distance={distance}",
            flush=True,
        )

        self.move_z(-distance)
        self.release()
        self.move_z(distance)

        print("[PLACE] 완료", flush=True)