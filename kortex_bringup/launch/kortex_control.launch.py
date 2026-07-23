# Copyright (c) 2021 PickNik, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Authors: Marq Rasmussen, Denis Stogl

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    OpaqueFunction,
    RegisterEventHandler,
)
from launch.event_handlers import OnProcessExit
from launch.conditions import IfCondition
from launch.substitutions import (
    Command,
    FindExecutable,
    LaunchConfiguration,
    PathJoinSubstitution,
    PythonExpression,
)
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

import yaml
import os
import tempfile


def load_and_apply_prefix(
    yaml_path,
    prefix,
    robot_description,
    substitutions=None,
    force_test_response=False,
    measurement_only=False,
):
    with open(yaml_path) as f:
        text = f.read()
    # Replace ${prefix} placeholders in the text
    text = text.replace("${prefix}", prefix)
    for key, value in (substitutions or {}).items():
        text = text.replace("${" + key + "}", value)
    data = yaml.safe_load(text)
    admittance_nodes = [
        f"{prefix}/admittance_controller" if prefix else "/admittance_controller",
        f"/{prefix}/admittance_controller" if prefix else "/admittance_controller",
    ]
    for admittance_node in admittance_nodes:
        if admittance_node in data:
            parameters = data[admittance_node]["ros__parameters"]
            parameters["robot_description"] = robot_description
            if measurement_only:
                # Leave the arm in Kinova's single-level firmware gravity hold.  The
                # admittance controller remains active as a state-only wrench estimator.
                parameters["state_only"] = True
            if not force_test_response:
                # Measurement mode is always motionless. In response mode, preserve
                # the explicitly selected axes from the controller YAML.
                parameters["admittance"]["selected_axes"] = [False] * 6
    with tempfile.NamedTemporaryFile(
        mode="w", prefix="kortex_controllers_", suffix=".yaml", delete=False
    ) as out:
        yaml.dump(data, out, default_flow_style=False)
        resolved_path = out.name
    print(f"[DEBUG] Saved resolved YAML to: {resolved_path}")
    return resolved_path


def launch_setup(context, *args, **kwargs):
    # Initialize Arguments
    robot_type = LaunchConfiguration("robot_type")
    robot_ip = LaunchConfiguration("robot_ip")
    dof = LaunchConfiguration("dof")
    vision = LaunchConfiguration("vision")
    # General arguments
    controllers_file = LaunchConfiguration("controllers_file")
    description_package = LaunchConfiguration("description_package")
    description_file = LaunchConfiguration("description_file")
    robot_name = LaunchConfiguration("robot_name")
    prefix = LaunchConfiguration("prefix")
    gripper = LaunchConfiguration("gripper")
    gripper_max_velocity = LaunchConfiguration("gripper_max_velocity")
    gripper_max_force = LaunchConfiguration("gripper_max_force")
    use_fake_hardware = LaunchConfiguration("use_fake_hardware")
    fake_sensor_commands = LaunchConfiguration("fake_sensor_commands")
    robot_traj_controller = LaunchConfiguration("robot_controller")
    robot_pos_controller = LaunchConfiguration("robot_pos_controller")
    robot_hand_controller = LaunchConfiguration("robot_hand_controller")
    fault_controller = LaunchConfiguration("fault_controller")
    wrench_injector = LaunchConfiguration("wrench_injector")
    tool_wrench_broadcaster = LaunchConfiguration("tool_wrench_broadcaster")
    launch_rviz = LaunchConfiguration("launch_rviz")
    use_internal_bus_gripper_comm = LaunchConfiguration("use_internal_bus_gripper_comm")
    initial_positions_file = LaunchConfiguration("initial_positions_file")
    gripper_joint_name = LaunchConfiguration("gripper_joint_name")
    include_clarius = LaunchConfiguration("include_clarius")
    feedback_timeout = LaunchConfiguration("feedback_timeout")
    wrench_filter_coefficient = LaunchConfiguration("wrench_filter_coefficient")
    wrench_force_deadband = LaunchConfiguration("wrench_force_deadband")
    wrench_torque_deadband = LaunchConfiguration("wrench_torque_deadband")
    payload_cog_x = LaunchConfiguration("payload_cog_x")
    payload_cog_y = LaunchConfiguration("payload_cog_y")
    payload_cog_z = LaunchConfiguration("payload_cog_z")
    payload_weight = LaunchConfiguration("payload_weight")
    force_test_response = LaunchConfiguration("force_test_response")
    admittance_damping = LaunchConfiguration("admittance_damping")
    nullspace_stiffness = LaunchConfiguration("nullspace_stiffness")
    move_and_stay_enabled = LaunchConfiguration("move_and_stay_enabled")
    move_and_stay_force_deadband = LaunchConfiguration("move_and_stay_force_deadband")
    move_and_stay_torque_deadband = LaunchConfiguration("move_and_stay_torque_deadband")
    move_and_stay_settle_time = LaunchConfiguration("move_and_stay_settle_time")

    # if we are using fake hardware then we can't use the internal gripper communications of the hardware
    use_fake_hardware_value = use_fake_hardware.perform(context)
    if use_fake_hardware_value == "true":
        use_internal_bus_gripper_comm = "false"

    robot_description_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),
            " ",
            PathJoinSubstitution(
                [FindPackageShare(description_package), "robots", description_file]
            ),
            " ",
            "robot_ip:=",
            robot_ip,
            " ",
            "name:=",
            robot_name,
            " ",
            "arm:=",
            robot_type,
            " ",
            "dof:=",
            dof,
            " ",
            "vision:=",
            vision,
            " ",
            "prefix:=",
            prefix,
            " ",
            "use_fake_hardware:=",
            use_fake_hardware,
            " ",
            "fake_sensor_commands:=",
            fake_sensor_commands,
            " ",
            "gripper:=",
            gripper,
            " ",
            "use_internal_bus_gripper_comm:=",
            use_internal_bus_gripper_comm,
            " ",
            "gripper_max_velocity:=",
            gripper_max_velocity,
            " ",
            "gripper_max_force:=",
            gripper_max_force,
            " ",
            "gripper_joint_name:=",
            gripper_joint_name,
            " ",
            "initial_positions_file:=",
            initial_positions_file,
            " ",
            "include_clarius:=",
            include_clarius,
            " ",
            "feedback_timeout:=",
            feedback_timeout,
            " ",
            "wrench_filter_coefficient:=",
            wrench_filter_coefficient,
            " ",
            "wrench_force_deadband:=",
            wrench_force_deadband,
            " ",
            "wrench_torque_deadband:=",
            wrench_torque_deadband,
            " ",
        ]
    )
    robot_description = {"robot_description": robot_description_content}

    robot_controllers = PathJoinSubstitution(
        [
            FindPackageShare(description_package),
            "arms/" + robot_type.perform(context) + "/" + dof.perform(context) + "dof/config",
            controllers_file,
        ]
    )

    robot_controllers_str = robot_controllers.perform(context)

    rviz_config_file = PathJoinSubstitution(
        [FindPackageShare(description_package), "rviz", "view_robot.rviz"]
    )

    prefix_str = prefix.perform(context)
    remapped_robot_description = (
        "/" + prefix_str + "/robot_description" if prefix_str else "/robot_description"
    )
    control_node = Node(
        package="controller_manager",
        executable="ros2_control_node",
        parameters=[
            robot_description,
            load_and_apply_prefix(
                robot_controllers_str,
                prefix_str,
                robot_description_content.perform(context),
                {
                    "payload_cog_x": payload_cog_x.perform(context),
                    "payload_cog_y": payload_cog_y.perform(context),
                    "payload_cog_z": payload_cog_z.perform(context),
                    "payload_weight": payload_weight.perform(context),
                    "gripper_joint_name": gripper_joint_name.perform(context),
                    "admittance_damping": admittance_damping.perform(context),
                    "nullspace_stiffness": nullspace_stiffness.perform(context),
                    "move_and_stay_enabled": move_and_stay_enabled.perform(context),
                    "move_and_stay_force_deadband": move_and_stay_force_deadband.perform(context),
                    "move_and_stay_torque_deadband": move_and_stay_torque_deadband.perform(context),
                    "move_and_stay_settle_time": move_and_stay_settle_time.perform(context),
                },
                force_test_response=force_test_response.perform(context).lower() == "true",
                measurement_only=(
                    use_fake_hardware.perform(context).lower() == "false"
                    and force_test_response.perform(context).lower() == "false"
                ),
            )
        ],
        namespace=prefix_str,
        remappings=[
            ("~/robot_description", remapped_robot_description),
        ],
        output="both",
    )

    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="both",
        namespace=prefix_str,
        parameters=[robot_description],
    )

    rviz_node = Node(
        package="rviz2",
        condition=IfCondition(launch_rviz),
        executable="rviz2",
        name="rviz2",
        output="log",
        arguments=["-d", rviz_config_file],
    )

    controller_manager_name = (
        "/" + prefix_str + "/controller_manager" if prefix_str else "/controller_manager"
    )
    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "joint_state_broadcaster",
            "--controller-manager",
            controller_manager_name,
        ],
    )

    # Delay rviz start after `joint_state_broadcaster`
    delay_rviz_after_joint_state_broadcaster_spawner = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[rviz_node],
        ),
        condition=IfCondition(launch_rviz),
    )

    robot_traj_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[robot_traj_controller, "-c", controller_manager_name],
    )

    robot_pos_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[robot_pos_controller, "--inactive", "-c", controller_manager_name],
    )

    robot_hand_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[robot_hand_controller, "-c", controller_manager_name],
        condition=IfCondition(PythonExpression(["'", gripper, "' != ''"])),
    )

    # only start the fault controller if we are using hardware
    fault_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[fault_controller, "-c", controller_manager_name],
        condition=IfCondition(use_internal_bus_gripper_comm),
    )
    wrench_injector_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[wrench_injector, "-c", controller_manager_name],
        condition=IfCondition(
            PythonExpression(
                [
                    "'",
                    wrench_injector,
                    "' != '' and '",
                    fake_sensor_commands,
                    "' == 'true'",
                ]
            )
        ),
    )
    tool_wrench_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[tool_wrench_broadcaster, "-c", controller_manager_name],
        condition=IfCondition(PythonExpression(["'", tool_wrench_broadcaster, "' != ''"])),
    )

    nodes_to_start = [
        control_node,
        robot_state_publisher_node,
        joint_state_broadcaster_spawner,
        delay_rviz_after_joint_state_broadcaster_spawner,
        robot_traj_controller_spawner,
        robot_pos_controller_spawner,
        fault_controller_spawner,
        wrench_injector_spawner,
        tool_wrench_broadcaster_spawner,
    ]
    start_robot_hand_controller = gripper.perform(context) != ""
    # Conditionally add robot_hand_controller_spawner
    if start_robot_hand_controller:
        nodes_to_start.append(robot_hand_controller_spawner)

    return nodes_to_start


def generate_launch_description():
    declared_arguments = []
    # Robot specific arguments
    declared_arguments.append(
        DeclareLaunchArgument(
            "robot_type", description="Type/series of robot.", choices=["gen3", "gen3_lite"]
        )
    )
    declared_arguments.append(DeclareLaunchArgument("dof", description="DoF of robot."))
    declared_arguments.append(
        DeclareLaunchArgument(
            "robot_ip", description="IP address by which the robot can be reached."
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "username", description="Robot session username.", default_value="admin"
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "password", description="Robot session password.", default_value="admin"
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "port", description="Robot port for tcp connection.", default_value="10000"
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "port_realtime",
            description="Robot port for udp realtime control.",
            default_value="10001",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "session_inactivity_timeout_ms",
            description="Robot session inactivity timeout in milliseconds.",
            default_value="60000",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "connection_inactivity_timeout_ms",
            description="Robot connection inactivity timeout in milliseconds.",
            default_value="2000",
        )
    )
    # General arguments
    declared_arguments.append(
        DeclareLaunchArgument(
            "controllers_file",
            default_value="ros2_controllers_dual_arm_test.yaml",
            description="YAML file with the controllers configuration.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "description_package",
            default_value="kortex_description",
            description="Description package with robot URDF/XACRO files. Usually the argument \
        is not set, it enables use of a custom description.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "description_file",
            default_value="kinova.urdf.xacro",
            description="URDF/XACRO description file with the robot.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "vision",
            default_value="false",
            description="Use the Gen3 vision-module bracelet model.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "robot_name",
            default_value="arm",
            description="Name of the robot.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "prefix",
            default_value="",
            description="Prefix of the joint names, useful for \
        multi-robot setup. If changed than also joint names in the controllers' configuration \
        have to be updated.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "gripper",
            default_value="",
            description="Name of the gripper attached to the arm",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "use_fake_hardware",
            default_value="false",
            description="Start robot with fake hardware mirroring command to its states.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "fake_sensor_commands",
            default_value="false",
            description="Enable fake command interfaces for sensors used for simple simulations. \
            Used only if 'use_fake_hardware' parameter is true.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "robot_controller",
            default_value="joint_trajectory_controller",
            description="Robot controller to start.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "robot_pos_controller",
            default_value="twist_controller",
            description="Robot controller to start.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "force_test_response",
            default_value="true",
            description="Enable admittance motion from the estimated external wrench.",
        )
    )
    declared_arguments.extend(
        [
            DeclareLaunchArgument(
                "admittance_damping",
                default_value="80.0, 80.0, 80.0, 15.0, 15.0, 15.0",
            ),
            DeclareLaunchArgument("nullspace_stiffness", default_value="1.0"),
            DeclareLaunchArgument("move_and_stay_enabled", default_value="true"),
            DeclareLaunchArgument(
                "move_and_stay_force_deadband", default_value="2.0, 2.0, 2.0"
            ),
            DeclareLaunchArgument(
                "move_and_stay_torque_deadband", default_value="0.2, 0.2, 0.2"
            ),
            DeclareLaunchArgument("move_and_stay_settle_time", default_value="0.05"),
        ]
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "robot_hand_controller",
            default_value="robotiq_gripper_controller",
            description="Robot hand controller to start.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "fault_controller",
            default_value="fault_controller",
            description="Name of the 'fault controller.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "wrench_injector",
            default_value="",
            description="Optional fake sensor command controller to start.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "tool_wrench_broadcaster",
            default_value="",
            description="Optional force-torque sensor broadcaster to start.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "initial_positions_file",
            default_value=PathJoinSubstitution(
                [FindPackageShare("kortex_description"), "config", "initial_positions.yaml"]
            ),
            description="Initial joint positions used by fake hardware.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "payload_cog_x",
            default_value="0.0",
            description="Payload center of gravity X in the gravity compensation frame.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "payload_cog_y",
            default_value="0.0",
            description="Payload center of gravity Y in the gravity compensation frame.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "payload_cog_z",
            default_value="0.08",
            description="Payload center of gravity Z in the gravity compensation frame.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "payload_weight",
            default_value="9.1",
            description="Payload weight in newtons for admittance gravity compensation.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "include_clarius",
            default_value="true",
            description="Attach the Clarius probe model to the Gen3 wrist mount.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "feedback_timeout",
            default_value="0.5",
            description="Maximum seconds since the last successful Kortex cyclic feedback refresh.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "wrench_filter_coefficient",
            default_value="0.05",
            description="Low-pass filter coefficient for Kortex estimated external wrench.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "wrench_force_deadband",
            default_value="0.0",
            description="Disabled here; contact release is handled once in admittance.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "wrench_torque_deadband",
            default_value="0.0",
            description="Disabled here; contact release is handled once in admittance.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument("launch_rviz", default_value="true", description="Launch RViz?")
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "use_internal_bus_gripper_comm",
            default_value="true",
            description="Use internal bus for gripper communication?",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "gripper_max_velocity",
            default_value="100.0",
            description="Max velocity for gripper commands",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "gripper_max_force",
            default_value="100.0",
            description="Max force for gripper commands",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "gripper_joint_name",
            default_value="finger_joint",
            description="Max force for gripper commands",
        )
    )
    return LaunchDescription(declared_arguments + [OpaqueFunction(function=launch_setup)])
