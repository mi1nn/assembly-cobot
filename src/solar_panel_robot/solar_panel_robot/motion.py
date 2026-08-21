from .config_loader import PoseLoader
from .gripper import Gripper

from DSR_ROBOT2 import (
    movel,
    movesx,
    posx,
    trans,
    DR_BASE,
)



class RobotMotion:

    def __init__(self):
        self.config = PoseLoader()

        self.velocity = self.config.get_velocity()
        self.acc = self.config.get_acc()

        self.gripper = Gripper()

    def make_target_ready(self, pose_name, approach_height):
        pose = self.config.get(pose_name)

        if pose["type"] != "task":
            raise ValueError(
                f"Pose '{pose_name}' must be task type"
            )

        target_position = pose["position"].copy()
        ready_position = pose["position"].copy()

        ready_position[2] += approach_height

        target = posx(target_position)
        ready = posx(ready_position)

        return target, ready

    def pick(self, pose_name, approach_height=50):
        target, ready = self.make_target_ready(
            pose_name,
            approach_height
        )

        print(
            f"[PICK] velocity={self.velocity}, "
            f"acc={self.acc}",
            flush=True
        )

        print("[PICK] ready :", ready, flush=True)
        print("[PICK] target:", target, flush=True)

        # movel(
        #     ready,
        #     vel=self.velocity,
        #     acc=self.acc
        # ) # pick 장소로 이동

        movel(
            target,
            vel=self.velocity,
            acc=self.acc
        )

        self.gripper.grasp()

        movel(
            ready,
            vel=self.velocity,
            acc=self.acc
        )

    def place(self, pose_name, approach_height=100):
        target, ready = self.make_target_ready(
            pose_name,
            approach_height
        )

        print(
            f"[PLACE] velocity={self.velocity}, "
            f"acc={self.acc}",
            flush=True
        )

        print("[PLACE] ready :", ready, flush=True)
        print("[PLACE] target:", target, flush=True)

        # movel(
        #     ready,
        #     vel=self.velocity,
        #     acc=self.acc
        # ) # place 장소로 이동

        movel(
            target,
            vel=self.velocity,
            acc=self.acc
        )

        self.gripper.release()

        movel(
            ready,
            vel=self.velocity,
            acc=self.acc
        )

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

    