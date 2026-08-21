import os
import yaml

from ament_index_python.packages import get_package_share_directory


class PoseLoader:

    def __init__(self):
        package_share = get_package_share_directory(
            "solar_panel_robot"
        )

        yaml_path = os.path.join(
            package_share,
            "config",
            "poses.yaml"
        )

        with open(yaml_path, "r") as file:
            data = yaml.safe_load(file)

        self.poses = data["poses"]

    def get(self, name):
        if name not in self.poses:
            raise KeyError(f"Pose '{name}' not found")

        return self.poses[name]