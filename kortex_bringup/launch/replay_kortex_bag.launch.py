import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, OpaqueFunction, TimerAction
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def _as_bool(value):
    return value.lower() in ("1", "true", "yes", "on")


def _make_bag_player(context):
    bag_path = os.path.abspath(os.path.expanduser(LaunchConfiguration("bag").perform(context)))
    if not os.path.exists(bag_path):
        raise RuntimeError(f"Rosbag path does not exist: {bag_path}")

    command = [
        "ros2",
        "bag",
        "play",
        bag_path,
        "--clock",
        "100",
        "--rate",
        LaunchConfiguration("rate").perform(context),
        "--delay",
        "2.0",
        "--start-offset",
        LaunchConfiguration("start_offset").perform(context),
    ]
    if _as_bool(LaunchConfiguration("loop").perform(context)):
        command.append("--loop")
    if _as_bool(LaunchConfiguration("start_paused").perform(context)):
        command.append("--start-paused")

    return [ExecuteProcess(cmd=command, output="screen")]


def generate_launch_description():
    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2_bag_replay",
        output="screen",
        arguments=[
            "-d",
            PathJoinSubstitution(
                [
                    FindPackageShare("kortex_bringup"),
                    "config",
                    "gen3_admittance_clarius.rviz",
                ]
            ),
        ],
        parameters=[{"use_sim_time": True}],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "bag",
                description="Path to a rosbag directory or metadata.yaml file.",
            ),
            DeclareLaunchArgument("rate", default_value="1.0"),
            DeclareLaunchArgument(
                "start_offset",
                default_value="0.0",
                description="Seconds to skip before replay; use 0.0 for the full bag.",
            ),
            DeclareLaunchArgument("loop", default_value="false"),
            DeclareLaunchArgument("start_paused", default_value="false"),
            rviz,
            TimerAction(period=0.5, actions=[OpaqueFunction(function=_make_bag_player)]),
        ]
    )
