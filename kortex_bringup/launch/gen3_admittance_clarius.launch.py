"""Launch Gen3 admittance control and the Clarius segmentation pipeline together."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    robot_ip = LaunchConfiguration("robot_ip")
    use_fake_hardware = LaunchConfiguration("use_fake_hardware")
    fake_sensor_commands = LaunchConfiguration("fake_sensor_commands")
    force_test_response = LaunchConfiguration("force_test_response")
    admittance_mode = LaunchConfiguration("admittance_mode")
    vision = LaunchConfiguration("vision")
    launch_rviz = LaunchConfiguration("launch_rviz")
    start_clarius = LaunchConfiguration("start_clarius")
    clarius_config_file = LaunchConfiguration("clarius_config_file")

    admittance_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare("kortex_bringup"), "launch", "gen3_admittance.launch.py"]
            )
        ),
        launch_arguments={
            "robot_ip": robot_ip,
            "use_fake_hardware": use_fake_hardware,
            "fake_sensor_commands": fake_sensor_commands,
            "force_test_response": force_test_response,
            "admittance_mode": admittance_mode,
            "vision": vision,
            "include_clarius": "true",
            "gripper": "",
            "visualize_wrench": "true",
            # The wrapper owns the single RViz process used for robot, wrench, and images.
            "launch_rviz": "false",
        }.items(),
    )

    clarius_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare("clarius_ros"), "launch", "clarius_segmentation.launch.py"]
            )
        ),
        launch_arguments={
            "config_file": clarius_config_file,
            "launch_rviz": "false",
        }.items(),
        condition=IfCondition(start_clarius),
    )

    combined_rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="gen3_clarius_rviz",
        output="screen",
        arguments=[
            "-d",
            PathJoinSubstitution(
                [FindPackageShare("kortex_bringup"), "config", "gen3_admittance_clarius.rviz"]
            ),
        ],
        condition=IfCondition(launch_rviz),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("robot_ip", default_value="192.168.1.10"),
            DeclareLaunchArgument("use_fake_hardware", default_value="false"),
            DeclareLaunchArgument("fake_sensor_commands", default_value="true"),
            DeclareLaunchArgument("force_test_response", default_value="false"),
            DeclareLaunchArgument("admittance_mode", default_value="move_and_stay"),
            DeclareLaunchArgument("vision", default_value="true"),
            DeclareLaunchArgument("launch_rviz", default_value="true"),
            DeclareLaunchArgument(
                "start_clarius",
                default_value="true",
                description="Start the probe Wi-Fi interface and segmentation pipeline",
            ),
            DeclareLaunchArgument(
                "clarius_config_file",
                default_value=PathJoinSubstitution(
                    [FindPackageShare("clarius_ros"), "config", "clarius.yaml"]
                ),
                description="Clarius interface parameter file",
            ),
            combined_rviz,
            admittance_launch,
            clarius_launch,
        ]
    )
