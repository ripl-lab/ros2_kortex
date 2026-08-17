"""Launch Gen3 admittance control and the Clarius segmentation pipeline together."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
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
    constrain_eef_orientation = LaunchConfiguration("constrain_eef_orientation")
    constrain_eef_z_motion = LaunchConfiguration("constrain_eef_z_motion")
    admittance_mode = LaunchConfiguration("admittance_mode")
    auto_move_activation_pose = LaunchConfiguration("auto_move_activation_pose")
    vision = LaunchConfiguration("vision")
    launch_rviz = LaunchConfiguration("launch_rviz")
    start_clarius = LaunchConfiguration("start_clarius")
    clarius_config_file = LaunchConfiguration("clarius_config_file")
    start_apriltag_tracking = LaunchConfiguration("start_apriltag_tracking")
    launch_realsense = LaunchConfiguration("launch_realsense")
    launch_calibration = LaunchConfiguration("launch_calibration")
    apriltag_image_topic = LaunchConfiguration("apriltag_image_topic")
    apriltag_camera_info_topic = LaunchConfiguration("apriltag_camera_info_topic")

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
            "constrain_eef_orientation": constrain_eef_orientation,
            "constrain_eef_z_motion": constrain_eef_z_motion,
            "admittance_mode": admittance_mode,
            "auto_move_activation_pose": auto_move_activation_pose,
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

    apriltag_tracking_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [
                    FindPackageShare("clarius_tracking_bringup"),
                    "launch",
                    "apriltag_tracking.launch.py",
                ]
            )
        ),
        launch_arguments={
            # The master already owns the Clarius/segmentation process.
            "launch_clarius": "false",
            "launch_realsense": launch_realsense,
            "launch_calibration": launch_calibration,
            "apriltag_image_topic": apriltag_image_topic,
            "apriltag_camera_info_topic": apriltag_camera_info_topic,
        }.items(),
        condition=IfCondition(start_apriltag_tracking),
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
            DeclareLaunchArgument(
                "constrain_eef_orientation",
                default_value="false",
                description=(
                    "Allow XYZ admittance motion while locking the Clarius tip orientation."
                ),
            ),
            DeclareLaunchArgument(
                "constrain_eef_z_motion",
                default_value="false",
                description="Lock base-frame Z translation while retaining X/Y admittance motion.",
            ),
            DeclareLaunchArgument("admittance_mode", default_value="move_and_stay"),
            DeclareLaunchArgument(
                "auto_move_activation_pose",
                default_value="true",
                description="Move to the activation pose once at launch.",
            ),
            DeclareLaunchArgument("vision", default_value="true"),
            DeclareLaunchArgument("launch_rviz", default_value="true"),
            DeclareLaunchArgument(
                "start_apriltag_tracking",
                default_value="true",
                description="Start RealSense and AprilTag tracking",
            ),
            DeclareLaunchArgument(
                "launch_realsense",
                default_value="true",
                description="Start the RealSense camera for AprilTag tracking",
            ),
            DeclareLaunchArgument(
                "launch_calibration",
                default_value="false",
                description="Start the optional calibrated CameraInfo publisher",
            ),
            DeclareLaunchArgument(
                "apriltag_image_topic",
                default_value="/camera/camera/color/image_raw",
            ),
            DeclareLaunchArgument(
                "apriltag_camera_info_topic",
                default_value="/camera/camera/color/camera_info",
            ),
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
            apriltag_tracking_launch,
        ]
    )
