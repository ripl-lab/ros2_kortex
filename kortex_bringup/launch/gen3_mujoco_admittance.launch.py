import os
import tempfile

import yaml
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    LogInfo,
    OpaqueFunction,
    RegisterEventHandler,
)
from launch.event_handlers import OnProcessExit, OnProcessStart
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def load_and_apply_prefix(yaml_path, prefix, robot_description, substitutions=None):
    with open(yaml_path) as f:
        text = f.read()
    text = text.replace("${prefix}", prefix)
    for key, value in (substitutions or {}).items():
        text = text.replace("${" + key + "}", value)
    data = yaml.safe_load(text)
    admittance_node = f"{prefix}/admittance_controller" if prefix else "/admittance_controller"
    if admittance_node in data:
        data[admittance_node]["ros__parameters"]["robot_description"] = robot_description
    with tempfile.NamedTemporaryFile(
        mode="w", prefix="kortex_mujoco_controllers_", suffix=".yaml", delete=False
    ) as out:
        yaml.dump(data, out, default_flow_style=False)
        return out.name


def launch_setup(context, *args, **kwargs):
    prefix = LaunchConfiguration("prefix")
    robot_name = LaunchConfiguration("robot_name")
    launch_gui = LaunchConfiguration("launch_gui")
    realtime_factor = LaunchConfiguration("realtime_factor")
    simulation_frequency = LaunchConfiguration("simulation_frequency")
    payload_cog_x = LaunchConfiguration("payload_cog_x")
    payload_cog_y = LaunchConfiguration("payload_cog_y")
    payload_cog_z = LaunchConfiguration("payload_cog_z")
    payload_weight = LaunchConfiguration("payload_weight")

    prefix_str = prefix.perform(context)
    mujoco_model_path = tempfile.mkdtemp(prefix="kortex_mujoco_")
    mujoco_model_file = os.path.join(mujoco_model_path, "main.xml")
    mujoco_mesh_path = os.path.join(mujoco_model_path, "meshes")

    robot_description_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),
            " ",
            PathJoinSubstitution(
                [FindPackageShare("kortex_description"), "robots", "kinova.urdf.xacro"]
            ),
            " ",
            "name:=",
            robot_name,
            " ",
            "arm:=gen3 dof:=7 vision:=false gripper:='' ",
            "prefix:=",
            prefix,
            " ",
            "use_fake_hardware:=false sim_mujoco:=true include_clarius:=false "
            "use_internal_bus_gripper_comm:=false ",
        ]
    )
    robot_description_string = robot_description_content.perform(context)
    robot_description = {"robot_description": robot_description_string}

    controllers_file = PathJoinSubstitution(
        [
            FindPackageShare("kortex_description"),
            "arms/gen3/7dof/config/ros2_controllers_admittance_mujoco.yaml",
        ]
    ).perform(context)
    controller_parameters = load_and_apply_prefix(
        controllers_file,
        prefix_str,
        robot_description_string,
        {
            "payload_cog_x": payload_cog_x.perform(context),
            "payload_cog_y": payload_cog_y.perform(context),
            "payload_cog_z": payload_cog_z.perform(context),
            "payload_weight": payload_weight.perform(context),
        },
    )

    xacro2mjcf = Node(
        package="mujoco_ros2_control",
        executable="xacro2mjcf.py",
        output="screen",
        parameters=[
            {"robot_descriptions": [robot_description_string]},
            {
                "input_files": [
                    PathJoinSubstitution(
                        [FindPackageShare("mujoco_ros2_control"), "mjcf", "scene.xml"]
                    ).perform(context)
                ]
            },
            {"output_file": mujoco_model_file},
            {"mujoco_files_path": mujoco_model_path},
        ],
    )

    gen3_mesh_path = PathJoinSubstitution(
        [FindPackageShare("kortex_description"), "arms/gen3/7dof/meshes"]
    ).perform(context)
    gen3_common_mesh_path = PathJoinSubstitution(
        [FindPackageShare("kortex_description"), "arms/gen3/meshes"]
    ).perform(context)
    clarius_mesh_path = PathJoinSubstitution(
        [FindPackageShare("clarius_description"), "meshes"]
    ).perform(context)
    mesh_fixup = ExecuteProcess(
        cmd=[
            "bash",
            "-lc",
            (
                f"sed -i 's/\\.dae/\\.STL/g' '{mujoco_model_path}'/*.xml; "
                "for d in "
                f"'{gen3_mesh_path}' '{gen3_common_mesh_path}' '{clarius_mesh_path}'; do "
                f"find -L \"$d\" -maxdepth 1 -type f -exec ln -sf {{}} '{mujoco_mesh_path}'/ \\;; "
                "done"
            ),
        ],
        output="screen",
    )

    mujoco = Node(
        package="mujoco_ros2_control",
        executable="mujoco_ros2_control",
        output="screen",
        parameters=[
            robot_description,
            controller_parameters,
            {"simulation_frequency": float(simulation_frequency.perform(context))},
            {"realtime_factor": float(realtime_factor.perform(context))},
            {"robot_model_path": mujoco_model_file},
            {"show_gui": launch_gui.perform(context).lower() == "true"},
        ],
        remappings=[("/controller_manager/robot_description", "/robot_description")],
    )

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="both",
        parameters=[robot_description, {"use_sim_time": True}],
    )

    controller_manager_name = (
        "/" + prefix_str + "/controller_manager" if prefix_str else "/controller_manager"
    )
    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager", controller_manager_name],
    )
    admittance_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["admittance_controller", "-c", controller_manager_name],
    )
    joint_trajectory_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_trajectory_controller", "--inactive", "-c", controller_manager_name],
    )

    start_mujoco = RegisterEventHandler(
        OnProcessExit(
            target_action=xacro2mjcf,
            on_exit=[
                LogInfo(msg="Created MuJoCo XML, fixing mesh links..."),
                mesh_fixup,
            ],
        )
    )
    start_mujoco_after_mesh_fixup = RegisterEventHandler(
        OnProcessExit(
            target_action=mesh_fixup,
            on_exit=[LogInfo(msg="Prepared MuJoCo mesh links, starting ros2_control..."), mujoco],
        )
    )
    load_controllers = RegisterEventHandler(
        OnProcessStart(
            target_action=mujoco,
            on_start=[
                joint_state_broadcaster_spawner,
                admittance_controller_spawner,
                joint_trajectory_controller_spawner,
            ],
        )
    )

    return [
        robot_state_publisher,
        xacro2mjcf,
        start_mujoco,
        start_mujoco_after_mesh_fixup,
        load_controllers,
    ]


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("robot_name", default_value="gen3"),
            DeclareLaunchArgument("prefix", default_value=""),
            DeclareLaunchArgument("launch_gui", default_value="true"),
            DeclareLaunchArgument("realtime_factor", default_value="1.0"),
            DeclareLaunchArgument("simulation_frequency", default_value="1000.0"),
            DeclareLaunchArgument("payload_cog_x", default_value="0.0"),
            DeclareLaunchArgument("payload_cog_y", default_value="0.0"),
            DeclareLaunchArgument("payload_cog_z", default_value="0.0473"),
            DeclareLaunchArgument("payload_weight", default_value="0.925"),
            OpaqueFunction(function=launch_setup),
        ]
    )
