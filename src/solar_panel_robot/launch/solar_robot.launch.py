from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():

    controller_node = Node(
        package="solar_panel_robot",
        executable="controller",
        name="solar_robot_controller",
        output="screen",
    )

    work_manager_node = Node(
        package="solar_panel_robot",
        executable="ros_bridge",
        name="ros_bridge",
        output="screen",
    )

    return LaunchDescription([
        controller_node,
        work_manager_node,
    ])