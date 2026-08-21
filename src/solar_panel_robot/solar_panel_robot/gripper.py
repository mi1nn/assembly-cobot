from DSR_ROBOT2 import (
    set_digital_output,
    wait,
)
from .config_loader import PoseLoader

OFF = 0
ON = 1


class Gripper:

    def __init__(self):
        config = PoseLoader()

        self.grasp_port = config.get_grasp_port()
        self.release_port = config.get_release_port()
        self.wait_time = config.get_gripper_wait_time()

    def grasp(self):
        set_digital_output(
            self.release_port,
            OFF
        )

        set_digital_output(
            self.grasp_port,
            ON
        )

        wait(self.wait_time)

    def release(self):
        set_digital_output(
            self.grasp_port,
            OFF
        )

        set_digital_output(
            self.release_port,
            ON
        )

        wait(self.wait_time)
