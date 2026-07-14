import os
import math
import tempfile
import xml.etree.ElementTree as ET

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


def load_and_apply_prefix(
    yaml_path,
    prefix,
    robot_description,
    substitutions=None,
    force_test_fixture=False,
    force_test_response=True,
    force_test_axis="x",
):
    with open(yaml_path) as f:
        text = f.read()
    text = text.replace("${prefix}", prefix)
    for key, value in (substitutions or {}).items():
        text = text.replace("${" + key + "}", value)
    data = yaml.safe_load(text)
    admittance_node = f"{prefix}/admittance_controller" if prefix else "/admittance_controller"
    if admittance_node in data:
        params = data[admittance_node]["ros__parameters"]
        params["robot_description"] = robot_description
        if force_test_fixture:
            # Isolate the observable world-X load in the upright test pose. The
            # estimator still runs when all axes are disabled; response mode
            # then passes Fx into a bounded, stiffer admittance axis.
            selected_axes = [False] * 6
            selected_axes[{"x": 0, "y": 1, "z": 2}[force_test_axis]] = force_test_response
            params["admittance"]["selected_axes"] = selected_axes
            params["admittance"]["stiffness"] = [100.0, 100.0, 100.0, 0.0, 0.0, 0.0]
            params["admittance"]["joint_damping"] = 10.0
            params["joint_effort_wrench_estimator"]["damping"] = 0.001
            params["control"]["frame"]["id"] = f"{prefix}base_link"
    with tempfile.NamedTemporaryFile(
        mode="w", prefix="kortex_mujoco_controllers_", suffix=".yaml", delete=False
    ) as out:
        yaml.dump(data, out, default_flow_style=False)
        return out.name


def create_force_test_fixture(axis_name, signed_force):
    axis_vectors = {
        "x": (1.0, 0.0, 0.0),
        "y": (0.0, 1.0, 0.0),
        "z": (0.0, 0.0, 1.0),
    }
    if axis_name not in axis_vectors:
        raise RuntimeError("force_test_axis must be one of: x, y, z")
    if not math.isfinite(signed_force) or signed_force == 0.0:
        raise RuntimeError("force_test_force must be a finite, non-zero value in newtons")

    sign = 1.0 if signed_force > 0.0 else -1.0
    direction = tuple(sign * value for value in axis_vectors[axis_name])
    tool_center = (0.26700235, -0.02488211, 0.84396201)
    body_position = tuple(
        center - 0.049 * component for center, component in zip(tool_center, direction)
    )
    plate_size = {
        "x": "0.01 0.08 0.08",
        "y": "0.08 0.01 0.08",
        "z": "0.08 0.08 0.01",
    }[axis_name]

    # Compensate gravity projected onto the slide so the constant motor force
    # produces the requested settled contact load on every axis.
    plunger_mass = 0.2
    gravity_generalized_force = plunger_mass * -9.81 * direction[2]
    actuator_force = abs(signed_force) - gravity_generalized_force

    root = ET.Element("mujoco", {"model": "Gen3 force estimator test fixture"})
    worldbody = ET.SubElement(root, "worldbody")
    body = ET.SubElement(
        worldbody,
        "body",
        {
            "name": "force_test_plunger",
            "pos": " ".join(f"{value:.8g}" for value in body_position),
        },
    )
    ET.SubElement(
        body,
        "joint",
        {
            "name": "force_test_slide",
            "type": "slide",
            "axis": " ".join(f"{value:.8g}" for value in direction),
            "limited": "true",
            "range": "-0.02 0.20",
            "damping": "10.0",
        },
    )
    ET.SubElement(
        body,
        "geom",
        {
            "name": "force_test_plunger_geom",
            "type": "box",
            "size": plate_size,
            "mass": str(plunger_mass),
            "contype": "2",
            "conaffinity": "2",
            "friction": "1 0.005 0.0001",
            "rgba": "0.85 0.25 0.15 1",
        },
    )
    actuator = ET.SubElement(root, "actuator")
    ET.SubElement(
        actuator,
        "motor",
        {
            "name": "force_test_actuator",
            "joint": "force_test_slide",
            "gear": "1",
        },
    )
    keyframe = ET.SubElement(root, "keyframe")
    ET.SubElement(
        keyframe,
        "key",
        {
            "name": "force_test_initial",
            "qpos": "0 -0.35 0 1.25 0 0.85 0 0",
            "ctrl": f"0 -0.35 0 1.25 0 0.85 0 {actuator_force:.10g}",
        },
    )
    ET.indent(root, space="  ")
    with tempfile.NamedTemporaryFile(
        mode="wb", prefix="kortex_force_test_", suffix=".xml", delete=False
    ) as output:
        ET.ElementTree(root).write(output, encoding="utf-8", xml_declaration=True)
        return output.name


def launch_setup(context, *args, **kwargs):
    prefix = LaunchConfiguration("prefix")
    robot_name = LaunchConfiguration("robot_name")
    launch_gui = LaunchConfiguration("launch_gui")
    realtime_factor = LaunchConfiguration("realtime_factor")
    simulation_frequency = LaunchConfiguration("simulation_frequency")
    initial_positions_file = LaunchConfiguration("initial_positions_file")
    force_test_fixture = LaunchConfiguration("force_test_fixture")
    force_test_response = LaunchConfiguration("force_test_response")
    force_test_axis = LaunchConfiguration("force_test_axis")
    force_test_force = LaunchConfiguration("force_test_force")
    payload_cog_x = LaunchConfiguration("payload_cog_x")
    payload_cog_y = LaunchConfiguration("payload_cog_y")
    payload_cog_z = LaunchConfiguration("payload_cog_z")
    payload_weight = LaunchConfiguration("payload_weight")

    prefix_str = prefix.perform(context)
    mujoco_model_path = tempfile.mkdtemp(prefix="kortex_mujoco_")
    mujoco_model_file = os.path.join(mujoco_model_path, "main.xml")
    mujoco_mesh_path = os.path.join(mujoco_model_path, "meshes")

    force_test_enabled = force_test_fixture.perform(context).lower() == "true"
    force_axis_str = force_test_axis.perform(context).lower()
    force_value = float(force_test_force.perform(context))
    initial_positions_path = initial_positions_file.perform(context)
    if force_test_enabled:
        initial_positions_path = PathJoinSubstitution(
            [
                FindPackageShare("kortex_description"),
                "config",
                "admittance_initial_positions.yaml",
            ]
        ).perform(context)

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
            "initial_positions_file:=",
            initial_positions_path,
            " ",
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
        force_test_fixture=force_test_enabled,
        force_test_response=force_test_response.perform(context).lower() == "true",
        force_test_axis=force_axis_str,
    )

    input_files = [
        PathJoinSubstitution(
            [FindPackageShare("mujoco_ros2_control"), "mjcf", "scene.xml"]
        ).perform(context)
    ]
    if force_test_enabled:
        input_files.append(create_force_test_fixture(force_axis_str, force_value))

    xacro2mjcf = Node(
        package="mujoco_ros2_control",
        executable="xacro2mjcf.py",
        output="screen",
        parameters=[
            {"robot_descriptions": [robot_description_string]},
            {"input_files": input_files},
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
            DeclareLaunchArgument(
                "initial_positions_file",
                default_value=PathJoinSubstitution(
                    [FindPackageShare("kortex_description"), "config", "initial_positions.yaml"]
                ),
            ),
            DeclareLaunchArgument(
                "force_test_fixture",
                default_value="false",
                description="Enable the physical MuJoCo force-test plunger.",
            ),
            DeclareLaunchArgument(
                "force_test_response",
                default_value="true",
                description="Pass the estimate into admittance; false measures while holding.",
            ),
            DeclareLaunchArgument(
                "force_test_axis",
                default_value="x",
                description="World/base force axis: x, y, or z.",
            ),
            DeclareLaunchArgument(
                "force_test_force",
                default_value="10.0",
                description="Signed physical contact force in newtons.",
            ),
            DeclareLaunchArgument("payload_cog_x", default_value="0.0"),
            DeclareLaunchArgument("payload_cog_y", default_value="0.0"),
            DeclareLaunchArgument("payload_cog_z", default_value="0.0473"),
            # This launch contains the bare arm (no gripper/payload), so a
            # real-robot payload compensation force would be interpreted by
            # admittance as a constant external wrench.
            DeclareLaunchArgument("payload_weight", default_value="0.0"),
            OpaqueFunction(function=launch_setup),
        ]
    )
