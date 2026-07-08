# Gen3 translational hand-guiding

This profile uses the Gen3 estimated external tool wrench and the ROS 2
`admittance_controller`. Only tool-frame X, Y, and Z translation are compliant.
The controller captures the measured joint state as its equilibrium when activated.

## Injected-wrench simulation

```bash
ros2 launch kortex_bringup gen3_admittance.launch.py
ros2 run kortex_bringup inject_wrench.py --force 8 0 0 --duration 2
ros2 run kortex_bringup inject_wrench.py --force 0 -8 0 --duration 2
```

The injector publishes `[Fx, Fy, Fz, Tx, Ty, Tz]` to
`/wrench_injector/commands` and publishes zero when it exits. Torque-only input
must not move the arm because rotational compliance is disabled.

RViz also subscribes to `/applied_wrench` in the default robot view using the
built-in Wrench display. The `gen3_admittance.launch.py` file starts
`wrench_stamped_publisher.py` by default, so injected commands appear at
`base_link` as force and torque arrows. Disable this with
`visualize_wrench:=false`.

## Real robot sequence

Start the profile with fake hardware disabled. This starts the trajectory
controller and loads admittance inactive.

```bash
ros2 launch kortex_bringup gen3_admittance.launch.py \
  use_fake_hardware:=false fake_sensor_commands:=false robot_ip:=192.168.1.10
```

Move to a central, nonsingular pose using the trajectory controller. With the
workspace clear and the emergency stop within reach, switch controllers:

```bash
ros2 control switch_controllers \
  --deactivate joint_trajectory_controller \
  --activate admittance_controller \
  --strict
```

To leave hand-guiding and hold the measured position, switch back:

```bash
ros2 control switch_controllers \
  --deactivate admittance_controller \
  --activate joint_trajectory_controller \
  --strict
```

Validate one translation axis at a time. Do not enable rotational axes until
the wrench sign, tool frame, bias, and payload behavior have been confirmed.

## Tuning

The initial profile is deliberately stiff and overdamped. Tune the admittance
mass, damping ratio, and stiffness in `ros2_controllers_admittance.yaml`.
Wrench filtering, bias, deadbands, clamps, stop thresholds, feedback timeout,
joint slew rate, and joint-limit margin are hardware parameters in the Gen3
`ros2_control` Xacro. Bias signs follow the Kortex tool-frame wrench fields.
