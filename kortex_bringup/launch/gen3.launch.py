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
# Author: Denis Stogl

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, ThisLaunchFileDir
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # Declare arguments
    declared_arguments = []
    declared_arguments.append(
        DeclareLaunchArgument(
            "robot_type",
            default_value="gen3",
            description="Type/series of robot.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "robot_ip",
            description="IP address by which the robot can be reached.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument("dof", default_value="7", description="DoF of robot.")
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
            description="Second robot controller to load inactive.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "wrench_injector",
            default_value="",
            description="Optional fake wrench command controller to start.",
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
            DeclareLaunchArgument("move_and_stay_settle_time", default_value="0.0"),
        ]
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
        DeclareLaunchArgument(
            "controllers_file",
            default_value="ros2_controllers_parametric.yaml",
            description="Robot controller to start.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "gripper",
            default_value="",
            description="Name of the gripper attached to the arm",
            choices=["", "robotiq_2f_85", "robotiq_2f_140"],
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "gripper_joint_name",
            default_value="robotiq_85_left_knuckle_joint",
            description="Name of the gripper attached to the arm",
        )
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
        DeclareLaunchArgument("launch_rviz", default_value="true", description="Launch RViz?")
    )

    # Initialize Arguments
    robot_type = LaunchConfiguration("robot_type")
    robot_ip = LaunchConfiguration("robot_ip")
    dof = LaunchConfiguration("dof")
    vision = LaunchConfiguration("vision")
    use_fake_hardware = LaunchConfiguration("use_fake_hardware")
    fake_sensor_commands = LaunchConfiguration("fake_sensor_commands")
    robot_controller = LaunchConfiguration("robot_controller")
    robot_pos_controller = LaunchConfiguration("robot_pos_controller")
    wrench_injector = LaunchConfiguration("wrench_injector")
    tool_wrench_broadcaster = LaunchConfiguration("tool_wrench_broadcaster")
    initial_positions_file = LaunchConfiguration("initial_positions_file")
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
    include_clarius = LaunchConfiguration("include_clarius")
    feedback_timeout = LaunchConfiguration("feedback_timeout")
    wrench_filter_coefficient = LaunchConfiguration("wrench_filter_coefficient")
    wrench_force_deadband = LaunchConfiguration("wrench_force_deadband")
    wrench_torque_deadband = LaunchConfiguration("wrench_torque_deadband")
    gripper = LaunchConfiguration("gripper")
    use_internal_bus_gripper_comm = LaunchConfiguration("use_internal_bus_gripper_comm")
    gripper_max_velocity = LaunchConfiguration("gripper_max_velocity")
    gripper_max_force = LaunchConfiguration("gripper_max_force")
    gripper_joint_name = LaunchConfiguration("gripper_joint_name")
    launch_rviz = LaunchConfiguration("launch_rviz")
    controllers_file = LaunchConfiguration("controllers_file")

    base_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([ThisLaunchFileDir(), "/kortex_control.launch.py"]),
        launch_arguments={
            "robot_type": robot_type,
            "robot_ip": robot_ip,
            "dof": dof,
            "vision": vision,
            "use_fake_hardware": use_fake_hardware,
            "fake_sensor_commands": fake_sensor_commands,
            "robot_controller": robot_controller,
            "robot_pos_controller": robot_pos_controller,
            "wrench_injector": wrench_injector,
            "tool_wrench_broadcaster": tool_wrench_broadcaster,
            "initial_positions_file": initial_positions_file,
            "payload_cog_x": payload_cog_x,
            "payload_cog_y": payload_cog_y,
            "payload_cog_z": payload_cog_z,
            "payload_weight": payload_weight,
            "force_test_response": force_test_response,
            "admittance_damping": admittance_damping,
            "nullspace_stiffness": nullspace_stiffness,
            "move_and_stay_enabled": move_and_stay_enabled,
            "move_and_stay_force_deadband": move_and_stay_force_deadband,
            "move_and_stay_torque_deadband": move_and_stay_torque_deadband,
            "move_and_stay_settle_time": move_and_stay_settle_time,
            "include_clarius": include_clarius,
            "feedback_timeout": feedback_timeout,
            "wrench_filter_coefficient": wrench_filter_coefficient,
            "wrench_force_deadband": wrench_force_deadband,
            "wrench_torque_deadband": wrench_torque_deadband,
            "gripper": gripper,
            "use_internal_bus_gripper_comm": use_internal_bus_gripper_comm,
            "gripper_max_velocity": gripper_max_velocity,
            "gripper_max_force": gripper_max_force,
            "gripper_joint_name": gripper_joint_name,
            "launch_rviz": launch_rviz,
            "controllers_file": controllers_file,
            "description_file": "gen3.xacro",
        }.items(),
    )

    return LaunchDescription(declared_arguments + [base_launch])
