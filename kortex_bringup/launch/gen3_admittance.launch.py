from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    use_fake_hardware = LaunchConfiguration("use_fake_hardware")
    fake_sensor_commands = LaunchConfiguration("fake_sensor_commands")
    robot_ip = LaunchConfiguration("robot_ip")
    launch_rviz = LaunchConfiguration("launch_rviz")
    visualize_wrench = LaunchConfiguration("visualize_wrench")
    gripper = LaunchConfiguration("gripper")
    gripper_joint_name = LaunchConfiguration("gripper_joint_name")
    use_internal_bus_gripper_comm = LaunchConfiguration("use_internal_bus_gripper_comm")
    payload_cog_x = LaunchConfiguration("payload_cog_x")
    payload_cog_y = LaunchConfiguration("payload_cog_y")
    payload_cog_z = LaunchConfiguration("payload_cog_z")
    payload_weight = LaunchConfiguration("payload_weight")
    include_clarius = LaunchConfiguration("include_clarius")
    initial_positions_file = LaunchConfiguration("initial_positions_file")
    controller_payload_weight = PythonExpression(
        [
            "'0.0' if '",
            use_fake_hardware,
            "' == 'true' else '",
            payload_weight,
            "'",
        ]
    )

    gen3_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare("kortex_bringup"), "launch", "gen3.launch.py"]
            )
        ),
        launch_arguments={
            "robot_ip": robot_ip,
            "use_fake_hardware": use_fake_hardware,
            "fake_sensor_commands": fake_sensor_commands,
            "controllers_file": "ros2_controllers_admittance.yaml",
            "robot_controller": PythonExpression(
                [
                    "'admittance_controller' if '",
                    use_fake_hardware,
                    "' == 'true' else 'joint_trajectory_controller'",
                ]
            ),
            "robot_pos_controller": PythonExpression(
                [
                    "'joint_trajectory_controller' if '",
                    use_fake_hardware,
                    "' == 'true' else 'admittance_controller'",
                ]
            ),
            "wrench_injector": "wrench_injector",
            "gripper": gripper,
            "gripper_joint_name": gripper_joint_name,
            "use_internal_bus_gripper_comm": use_internal_bus_gripper_comm,
            "payload_cog_x": payload_cog_x,
            "payload_cog_y": payload_cog_y,
            "payload_cog_z": payload_cog_z,
            "payload_weight": controller_payload_weight,
            "include_clarius": include_clarius,
            "initial_positions_file": initial_positions_file,
            "launch_rviz": launch_rviz,
        }.items(),
    )

    wrench_stamped_publisher = Node(
        package="kortex_bringup",
        executable="wrench_stamped_publisher.py",
        name="wrench_stamped_publisher",
        output="screen",
        parameters=[
            {
                "input_topic": "/wrench_injector/commands",
                "wrench_topic": "/applied_wrench",
                "frame_id": "base_link",
            }
        ],
        condition=IfCondition(visualize_wrench),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("robot_ip", default_value="192.168.1.10"),
            DeclareLaunchArgument("use_fake_hardware", default_value="true"),
            DeclareLaunchArgument("fake_sensor_commands", default_value="true"),
            DeclareLaunchArgument("launch_rviz", default_value="true"),
            DeclareLaunchArgument("visualize_wrench", default_value="true"),
            DeclareLaunchArgument(
                "gripper",
                default_value="robotiq_2f_85",
                choices=["", "robotiq_2f_85", "robotiq_2f_140"],
                description="Optional gripper attached to the Gen3.",
            ),
            DeclareLaunchArgument(
                "gripper_joint_name",
                default_value="robotiq_85_left_knuckle_joint",
                description="Commanded gripper joint name.",
            ),
            DeclareLaunchArgument(
                "use_internal_bus_gripper_comm",
                default_value="true",
                description="Use Kinova internal bus gripper communication on real hardware.",
            ),
            DeclareLaunchArgument(
                "payload_cog_x",
                default_value="0.0",
                description="Payload center of gravity X in end_effector_link.",
            ),
            DeclareLaunchArgument(
                "payload_cog_y",
                default_value="0.0",
                description="Payload center of gravity Y in end_effector_link.",
            ),
            DeclareLaunchArgument(
                "payload_cog_z",
                default_value="0.08",
                description="Payload center of gravity Z in end_effector_link.",
            ),
            DeclareLaunchArgument(
                "payload_weight",
                default_value="9.1",
                description="Payload weight in newtons for admittance gravity compensation.",
            ),
            DeclareLaunchArgument(
                "include_clarius",
                default_value="false",
                description="Attach the Clarius probe model to the wrist mount.",
            ),
            DeclareLaunchArgument(
                "initial_positions_file",
                default_value=PathJoinSubstitution(
                    [
                        FindPackageShare("kortex_description"),
                        "config",
                        "admittance_initial_positions.yaml",
                    ]
                ),
                description=(
                    "YAML file used to initialize fake hardware joint positions. "
                    "Real hardware uses measured joint positions instead."
                ),
            ),
            gen3_launch,
            wrench_stamped_publisher,
        ]
    )
