import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, OpaqueFunction, TimerAction
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
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
        "--topics",
        "/tf",
        "/tf_static",
        "/clarius/processed_image",
    ]
    if _as_bool(LaunchConfiguration("loop").perform(context)):
        command.append("--loop")
    if _as_bool(LaunchConfiguration("start_paused").perform(context)):
        command.append("--start-paused")

    return [ExecuteProcess(cmd=command, output="screen")]


def generate_launch_description():
    robot_description_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),
            " ",
            PathJoinSubstitution(
                [FindPackageShare("kortex_description"), "robots", "kinova.urdf.xacro"]
            ),
            " robot_ip:=xxx.yyy.zzz.www",
            " name:=kinova",
            " arm:=gen3",
            " dof:=",
            LaunchConfiguration("dof"),
            " gripper:=",
            LaunchConfiguration("gripper"),
            " vision:=",
            LaunchConfiguration("vision"),
        ]
    )

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[
            {"robot_description": robot_description_content},
            {"use_sim_time": True},
        ],
        remappings=[("/joint_states", "/joint_states_not_used_for_replay")],
    )

    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2_bag_replay",
        output="screen",
        arguments=[
            "-d",
            PathJoinSubstitution(
                [FindPackageShare("kortex_bringup"), "config", "kortex_bag_replay.rviz"]
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
            DeclareLaunchArgument("dof", default_value="7", choices=["6", "7"]),
            DeclareLaunchArgument(
                "gripper",
                default_value="",
                choices=["", "robotiq_2f_85", "robotiq_2f_140"],
            ),
            DeclareLaunchArgument("vision", default_value="false"),
            DeclareLaunchArgument("rate", default_value="1.0"),
            DeclareLaunchArgument(
                "start_offset",
                default_value="0.0",
                description="Seconds to skip before replay; use 0.0 for the full bag.",
            ),
            DeclareLaunchArgument("loop", default_value="false"),
            DeclareLaunchArgument("start_paused", default_value="false"),
            robot_state_publisher,
            rviz,
            TimerAction(period=0.5, actions=[OpaqueFunction(function=_make_bag_player)]),
        ]
    )
