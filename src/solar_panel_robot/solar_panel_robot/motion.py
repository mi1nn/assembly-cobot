from .config_loader import PoseLoader
from .gripper import Gripper

from DSR_ROBOT2 import (
    movej,
    movel,
    movesx,
    posj,
    posx,
    DR_BASE,
    DR_MV_MOD_REL,
)


class RobotMotion:

    def __init__(self):
        self.config = PoseLoader()
        self.velocity = self.config.get_velocity()
        self.acc = self.config.get_acc()
        self.gripper = Gripper()


    # Basic
    def move_home(self):
        pose = self.config.get("home")

        if pose["type"] != "joint":
            raise ValueError(
                "Pose 'home' must be joint type"
            )

        print("[HOME] 이동 시작", flush=True)

        home = posj(pose["position"])
        self.gripper.release()

        movej(
            home,
            vel=self.velocity,
            acc=self.acc
        )

        print("[HOME] 이동 완료", flush=True)


    # Move    
    def make_target_ready(self, pose_name, approach_height):
        pose = self.config.get(pose_name)

        if pose["type"] != "task":
            raise ValueError(
                f"Pose '{pose_name}' must be task type"
            )

        target_position = pose["position"].copy()
        ready_position = pose["position"].copy()

        # BASE 좌표계 Z 방향으로 approach_height 만큼 상승
        ready_position[2] += approach_height

        target = posx(target_position)
        ready = posx(ready_position)

        return target, ready

    def move_z(self, distance):
        # BASE 좌표계 기준 Z축 상대 이동
        # distance > 0 : 상승
        # distance < 0 : 하강

        movel(
            posx(0, 0, distance, 0, 0, 0),
            vel=self.velocity,
            acc=self.acc,
            ref=DR_BASE,
            mod=DR_MV_MOD_REL
        )

    def pick(self, distance=50):

        print(
            f"[PICK] velocity={self.velocity}, "
            f"acc={self.acc}",
            flush=True
        )

        # 1. BASE Z 방향으로 하강
        self.move_z(-distance)

        # 2. Gripper Close
        self.gripper.grasp()

        # 3. BASE Z 방향으로 상승
        self.move_z(distance)

    def place(self, distance=50):
        print(
            f"[PLACE] velocity={self.velocity}, "
            f"acc={self.acc}",
            flush=True
        )

        # 1. BASE Z 방향으로 하강
        self.move_z(-distance)

        # 2. Gripper Open
        self.gripper.release()

        # 3. BASE Z 방향으로 상승
        self.move_z(distance)

    @staticmethod
    def move_arc(start, end, height=100, steps=6):

        points = []

        for i in range(1, steps + 1):

            t = float(i) / steps

            # X, Y는 시작점 -> 끝점 선형 이동
            x = start[0] + (end[0] - start[0]) * t
            y = start[1] + (end[1] - start[1]) * t

            # 기본 Z 선형 이동
            z_linear = start[2] + (end[2] - start[2]) * t

            # 포물선 높이 추가
            z_arc = 4 * height * t * (1 - t)

            z = z_linear + z_arc

            # 자세도 시작 -> 끝으로 서서히 변경
            a = start[3] + (end[3] - start[3]) * t
            b = start[4] + (end[4] - start[4]) * t
            c = start[5] + (end[5] - start[5]) * t

            point = posx(x, y, z, a, b, c)

            points.append(point)

        # 스플라인 곡선 이동
        movesx(
            points,
            v=500,
            a=500,
            ref=DR_BASE
            )

    