from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    mode = LaunchConfiguration("mode")
    host = LaunchConfiguration("host")
    port = LaunchConfiguration("port")
    robot_id = LaunchConfiguration("robot_id")
    backend_base_url = LaunchConfiguration("backend_base_url")
    project_root = LaunchConfiguration("project_root")
    start_web = LaunchConfiguration("start_web")

    arguments = [
        DeclareLaunchArgument("mode", default_value="virtual", description="Doosan operation mode"),
        DeclareLaunchArgument("host", default_value="127.0.0.1", description="Doosan controller IP"),
        DeclareLaunchArgument("port", default_value="12345", description="Doosan controller port"),
        DeclareLaunchArgument("robot_id", default_value="1", description="Backend/DB robot ID"),
        DeclareLaunchArgument("backend_base_url", default_value="http://127.0.0.1:5000"),
        DeclareLaunchArgument("project_root", description="Absolute assembly-cobot repository path"),
        DeclareLaunchArgument("start_web", default_value="true", description="Start Flask web app"),
    ]

    doosan_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare("m0609_rg2_bringup"),
                "launch",
                "bringup.launch.py",
            ])
        ),
        launch_arguments={"mode": mode, "host": host, "port": port}.items(),
    )

    web_app = ExecuteProcess(
        cmd=[
            PathJoinSubstitution([project_root, "web_app", ".venv", "bin", "python"]),
            PathJoinSubstitution([project_root, "web_app", "run.py"]),
        ],
        cwd=PathJoinSubstitution([project_root, "web_app"]),
        output="screen",
        condition=IfCondition(start_web),
    )

    bridge = Node(
        package="ros2_bridge",
        executable="bridge_node",
        name="ros2_bridge",
        output="screen",
        additional_env={"BACKEND_BASE_URL": backend_base_url},
    )

    controller = Node(
        package="solar_panel_robot",
        executable="controller",
        name="solar_panel_controller",
        output="screen",
        parameters=[{"robot_id": ParameterValue(robot_id, value_type=int)}],
    )

    return LaunchDescription(arguments + [
        doosan_bringup,
        web_app,
        TimerAction(period=2.0, actions=[bridge]),
        TimerAction(period=5.0, actions=[controller]),
    ])
