from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():

    robot_id_arg = DeclareLaunchArgument(
        "robot_id",
        default_value="1",
        description="Backend/DB robot ID",
    )

    backend_base_url_arg = DeclareLaunchArgument(
        "backend_base_url",
        default_value="http://127.0.0.1:5000",
        description="Backend base URL used by ros2_bridge",
    )

    robot_id = LaunchConfiguration("robot_id")
    backend_base_url = LaunchConfiguration(
        "backend_base_url"
    )

    controller_node = Node(
        package="solar_panel_robot",
        executable="controller",
        output="screen",
        parameters=[
            {
                "robot_id": ParameterValue(
                    robot_id,
                    value_type=int,
                ),
            }
        ],
    )

    ros2_bridge_node = Node(
        package="ros2_bridge",
        executable="bridge_node",
        output="screen",
        additional_env={
            "BACKEND_BASE_URL": backend_base_url,
        },
    )

    return LaunchDescription([
        robot_id_arg,
        backend_base_url_arg,
        controller_node,
        ros2_bridge_node,
    ])