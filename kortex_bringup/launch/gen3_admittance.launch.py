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
    vision = LaunchConfiguration("vision")
    launch_rviz = LaunchConfiguration("launch_rviz")
    visualize_wrench = LaunchConfiguration("visualize_wrench")
    gripper = LaunchConfiguration("gripper")
    gripper_joint_name = LaunchConfiguration("gripper_joint_name")
    use_internal_bus_gripper_comm = LaunchConfiguration("use_internal_bus_gripper_comm")
    payload_cog_x = LaunchConfiguration("payload_cog_x")
    payload_cog_y = LaunchConfiguration("payload_cog_y")
    payload_cog_z = LaunchConfiguration("payload_cog_z")
    payload_weight = LaunchConfiguration("payload_weight")
    force_test_response = LaunchConfiguration("force_test_response")
    admittance_mode = LaunchConfiguration("admittance_mode")
    admittance_damping = LaunchConfiguration("admittance_damping")
    admittance_stiffness = LaunchConfiguration("admittance_stiffness")
    nullspace_stiffness = LaunchConfiguration("nullspace_stiffness")
    spring_nullspace_stiffness = LaunchConfiguration("spring_nullspace_stiffness")
    move_and_stay_force_deadband = LaunchConfiguration("move_and_stay_force_deadband")
    move_and_stay_torque_deadband = LaunchConfiguration("move_and_stay_torque_deadband")
    move_and_stay_settle_time = LaunchConfiguration("move_and_stay_settle_time")
    include_clarius = LaunchConfiguration("include_clarius")
    initial_positions_file = LaunchConfiguration("initial_positions_file")
    feedback_timeout = LaunchConfiguration("feedback_timeout")
    wrench_filter_coefficient = LaunchConfiguration("wrench_filter_coefficient")
    wrench_force_deadband = LaunchConfiguration("wrench_force_deadband")
    wrench_torque_deadband = LaunchConfiguration("wrench_torque_deadband")
    controller_payload_weight = PythonExpression(
        [
            "'0.0' if '",
            use_fake_hardware,
            "' == 'true' else '",
            payload_weight,
            "'",
        ]
    )
    measurement_only = PythonExpression(
        [
            "'",
            use_fake_hardware,
            "' == 'false' and '",
            force_test_response,
            "' == 'false'",
        ]
    )
    primary_controller = PythonExpression(
        [
            "'twist_controller' if ",
            measurement_only,
            " else 'admittance_controller'",
        ]
    )
    wrench_injector_controller = PythonExpression(
        [
            "'wrench_injector' if '",
            use_fake_hardware,
            "' == 'true' else ''",
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
            "vision": vision,
            "use_fake_hardware": use_fake_hardware,
            "fake_sensor_commands": fake_sensor_commands,
            "controllers_file": "ros2_controllers_admittance.yaml",
            "robot_controller": primary_controller,
            "robot_pos_controller": "joint_trajectory_controller",
            "wrench_injector": wrench_injector_controller,
            "tool_wrench_broadcaster": "",
            "gripper": gripper,
            "gripper_joint_name": gripper_joint_name,
            "use_internal_bus_gripper_comm": use_internal_bus_gripper_comm,
            "payload_cog_x": payload_cog_x,
            "payload_cog_y": payload_cog_y,
            "payload_cog_z": payload_cog_z,
            "payload_weight": controller_payload_weight,
            "force_test_response": force_test_response,
            "admittance_mode": admittance_mode,
            "admittance_damping": admittance_damping,
            "admittance_stiffness": admittance_stiffness,
            "nullspace_stiffness": nullspace_stiffness,
            "spring_nullspace_stiffness": spring_nullspace_stiffness,
            "move_and_stay_force_deadband": move_and_stay_force_deadband,
            "move_and_stay_torque_deadband": move_and_stay_torque_deadband,
            "move_and_stay_settle_time": move_and_stay_settle_time,
            "include_clarius": include_clarius,
            "feedback_timeout": feedback_timeout,
            "wrench_filter_coefficient": wrench_filter_coefficient,
            "wrench_force_deadband": wrench_force_deadband,
            "wrench_torque_deadband": wrench_torque_deadband,
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
                "input_topic": "/admittance_controller/status",
                "wrench_topic": "/estimated_wrench",
                "frame_id": "base_link",
            }
        ],
        condition=IfCondition(visualize_wrench),
    )

    measurement_estimator_spawner = Node(
        package="controller_manager",
        executable="spawner",
        name="spawner_measurement_admittance_controller",
        arguments=["admittance_controller", "-c", "/controller_manager"],
        condition=IfCondition(measurement_only),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("robot_ip", default_value="192.168.1.10"),
            DeclareLaunchArgument(
                "vision",
                default_value="true",
                description="Display and model the installed Gen3 vision module.",
            ),
            DeclareLaunchArgument("use_fake_hardware", default_value="true"),
            DeclareLaunchArgument("fake_sensor_commands", default_value="true"),
            DeclareLaunchArgument("launch_rviz", default_value="true"),
            DeclareLaunchArgument("visualize_wrench", default_value="true"),
            DeclareLaunchArgument(
                "gripper",
                default_value="",
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
                default_value="0.0",
                description="Payload center of gravity Z in end_effector_link.",
            ),
            DeclareLaunchArgument(
                "payload_weight",
                default_value="0.0",
                description=(
                    "Additional unmodeled payload force in newtons for wrench compensation. "
                    "The selected gripper inertia is already included in the URDF."
                ),
            ),
            DeclareLaunchArgument(
                "include_clarius",
                default_value="false",
                description="Attach the Clarius probe model to the wrist mount.",
            ),
            DeclareLaunchArgument(
                "feedback_timeout",
                default_value="0.5",
                description="Maximum seconds since the last successful Kortex cyclic feedback refresh.",
            ),
            DeclareLaunchArgument(
                "wrench_filter_coefficient",
                default_value="0.01",
                description="Low-pass filter coefficient for Kortex estimated external wrench.",
            ),
            DeclareLaunchArgument(
                "wrench_force_deadband",
                default_value="0.0",
                description="Disabled here; contact release is handled once in admittance.",
            ),
            DeclareLaunchArgument(
                "wrench_torque_deadband",
                default_value="0.0",
                description="Disabled here; contact release is handled once in admittance.",
            ),
            DeclareLaunchArgument(
                "force_test_response",
                default_value="false",
                description=(
                    "Enable motion from estimated force. False keeps all admittance axes "
                    "disabled while joint-torque wrench estimation remains active."
                ),
            ),
            DeclareLaunchArgument(
                "admittance_mode",
                default_value="move_and_stay",
                description=(
                    "'move_and_stay' forces zero Cartesian stiffness and enables pose latching; "
                    "'spring' disables pose latching and applies admittance_stiffness."
                ),
            ),
            DeclareLaunchArgument(
                "admittance_damping",
                default_value="80.0, 80.0, 80.0, 1.0, 1.0, 1.0",
                description="Explicit Cartesian damping used by move-and-stay mode.",
            ),
            DeclareLaunchArgument(
                "admittance_stiffness",
                default_value="200.0, 200.0, 200.0, 20.0, 20.0, 20.0",
                # default_value="10.0, 10.0, 10.0, 1.0, 1.0, 1.0",
                description="Spring-mode Cartesian stiffness [x,y,z,rx,ry,rz].",
            ),
            DeclareLaunchArgument(
                "nullspace_stiffness",
                default_value="1.0",
                description="Nullspace stiffness used by move-and-stay mode.",
            ),
            DeclareLaunchArgument(
                "spring_nullspace_stiffness",
                default_value="4.0",
                description="Nullspace posture stiffness used by spring mode.",
            ),
            DeclareLaunchArgument(
                "move_and_stay_force_deadband", default_value="2.0, 2.0, 2.0"
            ),
            DeclareLaunchArgument(
                "move_and_stay_torque_deadband", default_value="0.40, 0.40, 0.65"
            ),
            DeclareLaunchArgument("move_and_stay_settle_time", default_value="0.02"),
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
            measurement_estimator_spawner,
            wrench_stamped_publisher,
        ]
    )
