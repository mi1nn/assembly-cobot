from .config_loader import PoseLoader
from .gripper import Gripper

from DSR_ROBOT2 import (
    movel,
    posx,
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

        movel(
            ready,
            vel=self.velocity,
            acc=self.acc
        )

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

        movel(
            ready,
            vel=self.velocity,
            acc=self.acc
        )

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