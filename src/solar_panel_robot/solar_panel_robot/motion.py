from .config_loader import PoseLoader
from .gripper import Gripper

from DSR_ROBOT2 import (
    movel,
    movej,
    posx,
    posj,
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

        # BASE 좌표계 Z 방향으로 approach_height 만큼 상승
        ready_position[2] += approach_height

        target = posx(target_position)
        ready = posx(ready_position)

        return target, ready

    def move_home(self):
        pose = self.config.get("home")

        if pose["type"] != "joint":
            raise ValueError(
                "Pose 'home' must be joint type"
            )

        home = posj(pose["position"])

        print("[HOME] home:", home, flush=True)

        # Gripper Open
        print("[HOME] Gripper Open", flush=True)
        self.gripper.release()

        # Home 이동
        print("[HOME] 이동 시작", flush=True)

        movej(
            home,
            vel=self.velocity,
            acc=self.acc
        )

        print("[HOME] 이동 완료", flush=True)

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

        # Pick 위치 위로 이동
        movel(
            ready,
            vel=self.velocity,
            acc=self.acc
        )

        # Pick 위치로 하강
        movel(
            target,
            vel=self.velocity,
            acc=self.acc
        )

        # Gripper Close
        self.gripper.grasp()

        # 다시 상승
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

        # Place 위치 위로 이동
        movel(
            ready,
            vel=self.velocity,
            acc=self.acc
        )

        # Place 위치로 하강
        movel(
            target,
            vel=self.velocity,
            acc=self.acc
        )

        # Gripper Open
        self.gripper.release()

        # 다시 상승
        movel(
            ready,
            vel=self.velocity,
            acc=self.acc
        )