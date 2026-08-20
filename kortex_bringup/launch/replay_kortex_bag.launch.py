import os

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    LogInfo,
    OpaqueFunction,
    RegisterEventHandler,
    TimerAction,
)
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def _as_bool(value):
    return value.lower() in ("1", "true", "yes", "on")


def _make_bag_player(context):
    bag_path = os.path.abspath(os.path.expanduser(LaunchConfiguration("bag").perform(context)))
    if not os.path.exists(bag_path):
        raise RuntimeError(f"Rosbag path does not exist: {bag_path}")

    rate = LaunchConfiguration("rate").perform(context)
    start_offset = LaunchConfiguration("start_offset").perform(context)
    ultrasound_delay = float(LaunchConfiguration("ultrasound_delay").perform(context))
    if ultrasound_delay < 0.0:
        raise RuntimeError("ultrasound_delay must be non-negative")

    common_options = [
        "--rate",
        rate,
        "--start-offset",
        start_offset,
    ]
    if _as_bool(LaunchConfiguration("loop").perform(context)):
        common_options.append("--loop")

    if ultrasound_delay > 0.0:
        robot_command = [
            "ros2",
            "bag",
            "play",
            bag_path,
            "--clock",
            "100",
            *common_options,
            "--disable-keyboard-controls",
            "--remap",
            "__node:=robot_bag_player",
            "--topics",
            "/robot_description",
            "/tf_static",
            "/joint_states",
            "/tf",
        ]
        ultrasound_command = [
            "ros2",
            "bag",
            "play",
            bag_path,
            *common_options,
            "--disable-keyboard-controls",
            "--remap",
            "__node:=ultrasound_bag_player",
            "--topics",
            "/clarius/image_raw",
        ]
        robot_player = ExecuteProcess(cmd=robot_command, output="screen")
        ultrasound_player = ExecuteProcess(cmd=ultrasound_command, output="screen")
        return [
            robot_player,
            RegisterEventHandler(
                OnProcessExit(
                    target_action=robot_player,
                    on_exit=[LogInfo(msg="Robot motion replay ended.")],
                )
            ),
            TimerAction(
                period=ultrasound_delay,
                actions=[ultrasound_player],
            ),
            RegisterEventHandler(
                OnProcessExit(
                    target_action=ultrasound_player,
                    on_exit=[LogInfo(msg="Raw ultrasound image replay ended.")],
                )
            ),
        ]

    command = [
        "ros2",
        "bag",
        "play",
        bag_path,
        "--clock",
        "100",
        "--rate",
        rate,
        "--delay",
        "2.0",
        "--start-offset",
        start_offset,
        # Some bags contain clouds with the Clarius device-relative timestamp.
        # Keep them off the regenerated topic so RViz only sees the cloud that
        # is stamped against the bag clock and can be transformed with robot TF.
        "--remap",
        "/prediction_pointcloud:=/recorded/prediction_pointcloud",
        "__node:=replay_bag_player",
    ]
    if _as_bool(LaunchConfiguration("loop").perform(context)):
        command.append("--loop")
    if _as_bool(LaunchConfiguration("start_paused").perform(context)):
        command.append("--start-paused")

    combined_player = ExecuteProcess(cmd=command, output="screen")
    return [
        combined_player,
        RegisterEventHandler(
            OnProcessExit(
                target_action=combined_player,
                on_exit=[LogInfo(msg="Robot motion and raw ultrasound replay ended.")],
            )
        ),
    ]


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
                    "kortex_bag_replay.rviz",
                ]
            ),
        ],
        parameters=[{"use_sim_time": True}],
    )

    segmentation = Node(
        package="multi_label_segmentation_ros",
        executable="segmentation_node",
        output="screen",
        condition=IfCondition(LaunchConfiguration("start_segmentation")),
        parameters=[
            LaunchConfiguration("clarius_config_file"),
            {
                "use_sim_time": True,
                # Keep the generated overlay separate from the copy recorded in
                # the bag while regenerating /prediction_pointcloud.
                "prediction_topic": "/replay/segmentation_image",
            },
        ],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "bag",
                description="Path to a rosbag directory or metadata.yaml file.",
            ),
            DeclareLaunchArgument("rate", default_value="1.0"),
            DeclareLaunchArgument(
                "start_segmentation",
                default_value="true",
                description="Run segmentation and regenerate the accumulated point cloud.",
            ),
            DeclareLaunchArgument(
                "ultrasound_delay",
                default_value="0.0",
                description=(
                    "Wall-time seconds to play robot motion before starting raw "
                    "ultrasound. Zero preserves synchronized replay."
                ),
            ),
            DeclareLaunchArgument(
                "clarius_config_file",
                default_value=PathJoinSubstitution(
                    [FindPackageShare("clarius_ros"), "config", "clarius.yaml"]
                ),
                description="Parameters for regenerating ultrasound segmentation and cloud.",
            ),
            DeclareLaunchArgument(
                "start_offset",
                default_value="0.0",
                description="Seconds to skip before replay; use 0.0 for the full bag.",
            ),
            DeclareLaunchArgument("loop", default_value="false"),
            DeclareLaunchArgument("start_paused", default_value="false"),
            rviz,
            segmentation,
            # Allow the neural-network checkpoint to load before image playback.
            TimerAction(period=3.0, actions=[OpaqueFunction(function=_make_bag_player)]),
        ]
    )
