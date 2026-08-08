# ROS 2 KINOVA KORTEX™
> Kinova® KINOVA KORTEX™ is the common software platform behind all of the products in the Gen3 family (Gen3 and Gen3 lite). It unifies the inner workings of the various robots and their related external tools, like the API. <br />
> https://www.kinovarobotics.com/product/gen3-robots

<center><img src="doc/resources/kinova-gen3-7dof-robotiq-2f-85.jpg" alt="Kinova Gen3 7DoF manipulator with Intel RealSense 3D Vision Module and Robotiq 2F-85 2 Finger 85mm Adaptive Gripper" style="width: 50%"/></center>

ROS2 KINOVA KORTEX™ is the official ROS2 package to interact with KINOVA KORTEX™ and its related products. It is built upon the KINOVA KORTEX™ API, documentation for which can be found in the [GitHub Kortex repository](https://github.com/Kinovarobotics/kortex).

## Build status

<table width="100%">
  <tr>
    <th>ROS 2 Distro</th>
    <th>Humble</th>
    <th>Jazzy</th>
    <th>Rolling</th>
  </tr>
  <tr>
    <th>Branch</th>
    <td><a href="https://github.com/Kinovarobotics/ros2_kortex/tree/humble">humble</a></td>
    <td><a href="https://github.com/Kinovarobotics/ros2_kortex/tree/jazzy">jazzy</a></td>
    <td><a href="https://github.com/Kinovarobotics/ros2_kortex/tree/main">main</a></td>
  </tr>
  <tr>
    <th>Build Status</th>
    <td>
      <a href="https://github.com/Kinovarobotics/ros2_kortex/actions/workflows/humble-binary-build.yml">
        <img src="https://github.com/Kinovarobotics/ros2_kortex/actions/workflows/humble-binary-build.yml/badge.svg?event=push&branch=humble" alt="Humble Binary Build"/>
      </a>
      <br/>
      <a href="https://github.com/Kinovarobotics/ros2_kortex/actions/workflows/humble-source-build.yml">
        <img src="https://github.com/Kinovarobotics/ros2_kortex/actions/workflows/humble-source-build.yml/badge.svg?event=push&branch=humble" alt="Humble Source Build"/>
      </a>
    </td>
    <td>
      <a href="https://github.com/Kinovarobotics/ros2_kortex/actions/workflows/jazzy-binary-build.yml">
        <img src="https://github.com/Kinovarobotics/ros2_kortex/actions/workflows/jazzy-binary-build.yml/badge.svg?event=push&branch=jazzy" alt="Jazzy Binary Build"/>
      </a>
      <br/>
      <a href="https://github.com/Kinovarobotics/ros2_kortex/actions/workflows/jazzy-source-build.yml">
        <img src="https://github.com/Kinovarobotics/ros2_kortex/actions/workflows/jazzy-source-build.yml/badge.svg?event=push&branch=jazzy" alt="Jazzy Source Build"/>
      </a>
    </td>
    <td>
      <a href="https://github.com/Kinovarobotics/ros2_kortex/actions/workflows/rolling-binary-build.yml">
        <img src="https://github.com/Kinovarobotics/ros2_kortex/actions/workflows/rolling-binary-build.yml/badge.svg?event=push&branch=main" alt="Rolling Binary Build"/>
      </a>
      <br/>
      <a href="https://github.com/Kinovarobotics/ros2_kortex/actions/workflows/rolling-semi-binary-build.yml">
        <img src="https://github.com/Kinovarobotics/ros2_kortex/actions/workflows/rolling-semi-binary-build.yml/badge.svg?event=push&branch=main" alt="Rolling Semi-Binary Build"/>
      </a>
      <br/>
      <a href="https://github.com/Kinovarobotics/ros2_kortex/actions/workflows/rolling-source-build.yml">
        <img src="https://github.com/Kinovarobotics/ros2_kortex/actions/workflows/rolling-source-build.yml/badge.svg?event=push&branch=main" alt="Rolling Source Build"/>
      </a>
    </td>
  </tr>
  <tr>
    <th>Release Status</th>
    <td>Stable (binary available — may lag behind source)<!-- TODO(moriarty) add build.ros2.org status badge once released --></td>
    <td>Stable (source only)<!-- TODO(moriarty) add build.ros2.org status badge once released --></td>
    <td>Unstable (source only)</td>
  </tr>
</table>


**Note:** There are several CI jobs checking against future upstream changes see [detailed build status](.github/workflows/README.md) for a full list of CI jobs and for more information.

**Note:** Gazebo classic support was kept on the `humble` branch of this repository

---

## Docker development environment

The Docker setup targets ROS 2 Humble on Ubuntu 22.04. Install Docker Engine and make sure your
user can run `docker` before continuing. The repository must be located at
`<workspace>/src/ros2_kortex`; the helper script mounts the complete workspace into the container.

### Build the workspace in Docker

From the `ros2_kortex` repository directory, run:

```bash
./.devcontainer/dev-docker.sh -- \
  colcon build --cmake-args \
    -DCMAKE_BUILD_TYPE=Release \
    -DDOWNLOAD_UNITREE_H1_ASSETS=OFF \
    --executor sequential
```

On the first run, this command:

1. Builds the `ros2-kortex-dev` image from `.devcontainer/Dockerfile`.
2. Imports missing Humble dependencies into the mounted workspace with `vcs`.
3. Creates the workspace Python virtual environment.
4. Builds the mounted workspace, so `build`, `install`, and `log` remain on the host.

The initial image build and dependency import can take several minutes. The sequential colcon
executor avoids excessive memory use.

### Run an interactive container

After the image and workspace have been built, start a shell without rebuilding the image or
reimporting dependencies:

```bash
./.devcontainer/dev-docker.sh --no-build --no-init
```

The container sources ROS 2 Humble, the workspace `install/setup.bash` when present, and the
workspace virtual environment. It uses host networking and mounts the workspace at
`/workspace/ros2_kortex_ws`.

For subsequent source changes, rebuild from inside the container:

```bash
colcon build \
  --cmake-args \
    -DCMAKE_BUILD_TYPE=Release \
    -DDOWNLOAD_UNITREE_H1_ASSETS=OFF \
  --executor sequential
source install/setup.bash
```

Exit the shell with `exit`. The container is removed automatically, while files in the mounted
workspace are preserved.

Useful options include:

```bash
# Use a custom image and container name.
./.devcontainer/dev-docker.sh --image my-kortex-image --name my-kortex-container

# Skip the full Clarius dependency setup while building a lighter development image.
RUN_CLARIUS_SETUP=false ./.devcontainer/dev-docker.sh

# Skip compiling the copied workspace into the image (the helper's bind mount hides it).
BUILD_WORKSPACE_IN_IMAGE=false ./.devcontainer/dev-docker.sh

# Build selected packages in the mounted workspace before opening the shell.
./.devcontainer/dev-docker.sh --build-packages "clarius_ros kortex_bringup"

# Optionally download the private segmentation weights while building.
CLARIUS_MODEL_URL='https://your-authorized-download/deeplabv3.pth' \
  ./.devcontainer/dev-docker.sh

# If an SSH agent is not running, select a host private key explicitly.
HOST_SSH_KEY="$HOME/.ssh/id_ed25519" ./.devcontainer/dev-docker.sh

# Display every supported option.
./.devcontainer/dev-docker.sh --help
```

When `RUN_CLARIUS_SETUP=false` is used, install any missing workspace dependencies inside the
container before building:

```bash
sudo apt-get update
rosdep install --ignore-src --from-paths src -y -r
```

The full image installs Git LFS, imports `clarius_interface` and `multi-label_segmentation`, installs
`clarius_interface/requirement.txt`, Pillow, and PySide6, then builds the ROS workspace. The
segmentation model is not in Git; either provide an authorized `CLARIUS_MODEL_URL` during the image
build or place
`deeplabv3.pth` in `src/multilabel_segmentation/multi_label_segmentation/src/models/` afterward.
Private Git repositories are cloned with BuildKit SSH forwarding. The key remains on the host and
is exposed only to the repository-import build step; it is not copied into the image. The launcher
prefers `SSH_AUTH_SOCK`, then `HOST_SSH_KEY`, then `~/.ssh/id_ed25519` or `~/.ssh/id_rsa`.
The bundled `libcast.so` and `pyclariuscast.so` must match the Clarius App version because Cast does
not provide forward or backward compatibility across App/API releases.
The Dockerfile builds the workspace by default so a standalone image can resolve imported packages
such as `clarius_ros`. `dev-docker.sh` overrides this to false because it bind-mounts the host
workspace over the image workspace, which would hide image-internal build artifacts; its command
examples build the mounted workspace instead. BuildKit also retains the pip download cache across
rebuilt layers.

Use `--build-packages "package_a package_b"` (or the `BUILD_PACKAGES` environment variable) to
build selected packages every time the helper starts. When the value is empty, initialization only
imports missing repositories and prepares the virtual environment; it does not build any packages.

For graphical applications, the script forwards `DISPLAY` and mounts `/tmp/.X11-unix` when it is
available. The host X server may also need to authorize the local container user.

### Minimal MuJoCo build image

For controller and headless MuJoCo development without the full development image, build the core
image from the workspace root:

```bash
cd /path/to/ros2_kortex_ws
docker build \
  -t ros2-kortex-mujoco-core \
  -f src/ros2_kortex/.devcontainer/Dockerfile.mujoco-core \
  src/ros2_kortex
```

Run it with the workspace mounted:

```bash
docker run --rm -it \
  --network host \
  --ipc host \
  -v "$PWD:/workspace/ros2_kortex_ws" \
  -w /workspace/ros2_kortex_ws \
  ros2-kortex-mujoco-core bash
```

Then build and source the required packages in the container:

```bash
source /opt/ros/humble/setup.bash
if [ -f install/setup.bash ]; then source install/setup.bash; fi
colcon build \
  --packages-up-to admittance_controller mujoco_ros2_control kortex_bringup \
  --cmake-args -DDOWNLOAD_UNITREE_H1_ASSETS=OFF \
  --executor sequential
source install/setup.bash
```

### Run MuJoCo with admittance and an applied force

The MuJoCo GUI also draws each measured joint actuator torque at its joint: yellow is positive,
purple is negative, and arrow length is proportional to torque magnitude. Run the requested home
and all-zero pose demonstrations with:

```bash
ros2 run kortex_bringup demo_mujoco_pose.sh home
ros2 run kortex_bringup demo_mujoco_pose.sh zero
```

To view the same measured joint torques in RViz2, launch the MuJoCo demo directly with RViz enabled:

```bash
ros2 launch kortex_bringup gen3_mujoco_admittance.launch.py \
  launch_gui:=true launch_rviz:=true initial_pose:=home force_test_fixture:=false
```

To interactiovely push or pull the robot in the MuJCo window, double-click a
robot link to select it, then hold **Ctrl** and drag with the **right mouse
button**. Ctrl + left-drag applies a rotational perturbation. Release the mouse
button to stop applying the perturbation.

Choose `initial_pose:=home` or `initial_pose:=zero`. The `Measured Joint Torques` group contains
seven native RViz Wrench displays fed by `geometry_msgs/WrenchStamped` topics.

The home pose is `[0, 15, 180, -130, 0, 55, 90]` degrees. Both commands keep the joint-effort
wrench estimator and its blue estimated-force arrow enabled.

To apply 10 N successively on world X, Y, and Z, allowing the arm to return and settle before the
next independently initialized MuJoCo run, use:

```bash
ros2 run kortex_bringup demo_mujoco_forces.sh sequence 10 2 5
```

To demonstrate zero spring stiffness, where the arm retains its displacement after the force is
removed, run (the final argument is the axis):

```bash
ros2 run kortex_bringup demo_mujoco_forces.sh stay 10 2 5 x
```

Stop the zero-spring demonstration with Ctrl-C. It deliberately does not apply a following force,
because stiffness zero removes the automatic return-to-origin condition.

Start the development container and ensure the workspace is built and sourced as described above.
Then launch the seven-DoF Gen3 with the admittance controller and the MuJoCo force-test fixture:

```bash
ros2 launch kortex_bringup gen3_mujoco_admittance.launch.py \
  launch_gui:=true \
  force_test_fixture:=true \
  force_test_axis:=x \
  force_test_force:=10.0 \
  force_test_duration:=2.0 \
  force_test_start_delay:=1.0 \
  force_test_response:=true
```

The fixture creates a physical sliding plunger in MuJoCo and applies the requested signed contact
force to the tool. It does not inject a synthetic wrench directly into the controller. The
controller estimates the wrench with an impulse-momentum observer using `qfrc_actuator`, joint
velocity, and the Pinocchio dynamics model; joint acceleration is not required.

The force controls are:

- `force_test_axis:=x`, `y`, or `z` selects the base/world force axis.
- `force_test_force:=10.0` applies a positive 10 N force; use `-10.0` for the opposite direction.
- `force_test_duration:=2.0` releases the physical load after two seconds of simulation time.
- `force_test_start_delay:=1.0` lets controllers initialize before the timed load begins.
- `force_test_mass:=8.0` sets the virtual translational mass in kilograms.
- `force_test_joint_damping:=10.0` sets admittance inverse-kinematics joint damping.

The controller also bounds the virtual motion with measured-state tracking anti-windup. Its
`admittance.max_cartesian_acceleration`, `max_joint_acceleration`, `max_joint_velocity`,
`max_joint_displacement`, and `max_tracking_error` parameters can be tuned in the controller YAML.
The MuJoCo Gen3 position servos use lower-bandwidth PD gains to avoid high-frequency wrist chatter.
- `force_test_response:=true` enables compliant motion on the selected axis.
- `force_test_response:=false` keeps the robot holding position while the estimator continues to
  measure the applied force.
- `launch_gui:=false` runs the same test headlessly.

For example, run an estimator-only test with a negative Y force:

```bash
ros2 launch kortex_bringup gen3_mujoco_admittance.launch.py \
  launch_gui:=false \
  force_test_fixture:=true \
  force_test_axis:=y \
  force_test_force:=-10.0 \
  force_test_response:=false
```

In another terminal, enter the running development container and inspect the controller state:

```bash
docker exec -it ros2-kortex-dev bash
source /opt/ros/humble/setup.bash
source /workspace/ros2_kortex_ws/install/setup.bash
ros2 topic echo /admittance_controller/status
```

The estimated base-frame force is reported in `wrench_base.wrench.force`. Allow the simulation to
settle before checking it. With the default force fixture, the selected component should be close
to the requested signed force; the acceptance tolerance used for force testing is 0.5 N.

To verify that the robot settles after the timed force is removed, keep the launch running and run
this in another sourced container terminal. Match `--duration` to `force_test_duration`:

```bash
ros2 run kortex_bringup verify_mujoco_force_stop.py \
  --duration 2.0 \
  --start-delay 1.0 \
  --settle-time 5.0 \
  --observation-time 1.0
```

The check passes when every joint remains below 0.01 rad/s and drifts less than 0.002 rad over the
post-settle observation window. Both tolerances can be overridden with command-line options. Run
the same check with both `force_test_response:=false` (estimator-only hold) and
`force_test_response:=true` (compliant response) when validating controller stability.

When `force_test_response:=true`, the controller uses zero Cartesian stiffness with explicit
Cartesian damping and bounded acceleration and velocity. The resulting displacement depends on
the force duration and motion limits rather than a static `force / stiffness` ratio. After the
force is released, move-and-stay mode holds the displaced pose. Tool motion can be observed in the
GUI or from the base-to-tool transform:

```bash
ros2 run tf2_ros tf2_echo base_link end_effector_link
```

To establish the zero-force pose or verify that the estimator is near zero without contact, run
the launch once with the fixture disabled:

```bash
ros2 launch kortex_bringup gen3_mujoco_admittance.launch.py \
  launch_gui:=false \
  force_test_fixture:=false
```

### Measure force from real Gen3 joint torques

The real Gen3 hardware exports cyclic actuator torque readings through each joint's ROS 2
`effort` state interface. Start the joint-effort wrench estimator in measure-only mode with:

```bash
ros2 launch kortex_bringup gen3_admittance.launch.py \
  robot_ip:=192.168.1.10 \
  use_fake_hardware:=false \
  force_test_response:=false
```

The admittance controller starts at the measured joint positions and keeps every response axis
disabled, so the estimate is published without force-driven motion. Inspect it with:

```bash
ros2 topic echo /admittance_controller/status
```

The estimated force is in `wrench_base.wrench.force`. Keep the arm unloaded initially and verify
that the estimate is near zero before applying a known force. Accuracy depends on the URDF inertial
model and the configured payload mass and center of gravity; pass the `payload_weight` and
`payload_cog_*` launch arguments if the attached tool differs from the defaults.

Only after validating both force and torque estimates should six-axis spring compliance be enabled
with `force_test_response:=true`. The real Gen3 spring configuration uses the bounded-joint URDF
limits directly; controller-side soft-limit weighting is disabled, while the hardware driver keeps
its final 0.02 rad position guard.

For free-hand scanning, use move-and-stay mode so the released pose becomes the new hold pose:

```bash
ros2 launch kortex_bringup gen3_admittance.launch.py \
  robot_ip:=192.168.1.10 \
  use_fake_hardware:=false \
  force_test_response:=true \
  admittance_mode:=move_and_stay
```

The real-robot profile filters the 1 kHz joint-effort wrench estimate and uses lower virtual
rotational inertia than translation so an operator can command roll, pitch, and yaw with normal
one-hand moments. Before scanning, hold the arm unloaded and confirm that all six components of
`/admittance_controller/status.wrench_base.wrench` settle near zero. Incorrect payload weight or
center of gravity appears primarily as a persistent torque and can cause unwanted rotation.

To identify the center of mass of an attached rigid payload from static poses, first launch in
measure-only mode with the Clarius model enabled:

```bash
ros2 launch kortex_bringup gen3_admittance.launch.py \
  robot_ip:=192.168.1.10 \
  use_fake_hardware:=false \
  include_clarius:=true \
  force_test_response:=false
```

In another terminal, run the interactive calibration using the measured combined mass:

```bash
ros2 run kortex_bringup estimate_payload_com.py --mass 0.536 --poses 15
```

Before sampling, the script publishes the 15 numbered target orientations to
`/payload_com_calibration/poses`. To inspect them without starting calibration, run:

```bash
ros2 run kortex_bringup estimate_payload_com.py --mass 0.536 --poses 15 --preview-only
```

The RViz arrows share the current `clarius_base_link` position and show the target direction of its
positive Z axis. They are orientation references only: the script does not command robot motion.

At each prompt, move the arm slowly to a substantially different tool orientation, stop, and press
Enter. The script rejects moving samples, robustly fits the CoM in `clarius_base_link`, and fits a
constant offset for each joint so sensor zero error is not confused with payload gravity. Keep the
complete mount, probe, fasteners, and normally supported cable section installed throughout the
calibration. Copy the printed inertial origin into the `clarius_base_link` URDF, rebuild, and restart
the launch. Leave `payload_weight:=0.0` because the 0.536 kg mass is then already represented in the
Pinocchio model. Validate the result on several stationary poses that were not part of the fit.

---

## CLARIUS SETUP

The Clarius description can be used by MoveIt, rosbag replay, and the Gen3 admittance-control
launch. In the admittance launch it is attached through the Kinova wrist mount defined in the
Gen3 description.

To start Gen3 admittance control, the Clarius Wi-Fi interface and segmentation, and one RViz window containing the robot, applied wrench, raw ultrasound, and segmentation image, run:

```bash
ros2 launch kortex_bringup gen3_admittance_clarius.launch.py \
  robot_ip:=192.168.1.10 \
  use_fake_hardware:=false \ force_test_response:=true \
  start_clarius:=true \
  vision:=true \
  launch_rviz:=true \ 
  clarius_config_file:=/workspace/ros2_kortex_ws/src/clarius_interface/clarius_ros/config/clarius.yaml
```

The wrapper always attaches the Clarius model and disables the gripper.

1. Make sure that `colcon`, its extensions, and `vcs` are installed:

    ```bash
    sudo apt install python3-colcon-common-extensions python3-vcstool
    ```

2. Create a new ROS2 workspace:

    ```bash
    export COLCON_WS=~/workspace/ros2_kortex_ws
    mkdir -p $COLCON_WS/src
    ```

3. Pull relevant packages:
   
    ```bash
    cd $COLCON_WS
    git clone -b tz/clarius_scanner --single-branch git@github.com:ripl-lab/ros2_kortex.git src/ros2_kortex
    vcs import src --skip-existing --input src/ros2_kortex/ros2_kortex.$ROS_DISTRO.repos
    vcs import src --skip-existing --input src/ros2_kortex/ros2_kortex-not-released.$ROS_DISTRO.repos
    ```

4. Install MoveIt 2

    ```bash
    sudo apt install ros-humble-moveit 
    ```

5. Install dependencies, compile, and source the workspace:
  - `--executor sequential` is recomended to prevent crashing your laptop

    ```bash
    rosdep install --ignore-src --from-paths src -y -r
    colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release --executor sequential
    ```

6. Source the previously built workspace using the following command:
   
    ```bash
    echo 'source ~/workspace/ros2_kortex_ws/install/setup.bash' >> ~/.bashrc
    ```

7. Launch the bringup to verify 

    ```bash
    ros2 launch kortex_description view_robot.launch.py
    ```

### Admittance control

Enable the mount and probe model with `include_clarius:=true`:

```bash
ros2 launch kortex_bringup gen3_admittance.launch.py \
  robot_ip:=192.168.1.10 \
  use_fake_hardware:=false \
  force_test_response:=false \
  vision:=true \
  include_clarius:=true \
  launch_rviz:=true
```

The resulting fixed-link chain is
`end_effector_link -> kinova_mount_link -> clarius_base_link -> clarius_sensor_frame`.
Start with `force_test_response:=false` while validating the payload model and gravity
compensation.

### MoveIt

- For visualization 

    ```bash
    ros2 launch kinova_gen3_7dof_robotiq_2f_85_moveit_config robot_no_gripper.launch.py \
      robot_ip:=yyy.yyy.yyy.yyy \
      use_fake_hardware:=true
    ```
- For real robot

    ```bash
    ros2 launch kinova_gen3_7dof_robotiq_2f_85_moveit_config robot_no_gripper.launch.py \
      robot_ip:=192.168.1.10
    ```

### Bag Replay

To replay recorded Gen3 transforms together with a Clarius processed image:

```bash
ros2 launch kortex_bringup replay_kortex_bag.launch.py \
  bag:=/absolute/path/to/rosbag
```

The launch uses simulated time and replays `/tf`, `/tf_static`, and
`/clarius/processed_image`. It defaults to a 7-DoF Gen3 without a gripper. Do not run hardware or fake controllers simultaneously because their TF output can compete with the recorded transforms.


---

## Getting started

1. Install ROS 2.

   For this branch, ROS2 Humble has to be installed on Ubuntu 22.04.

   Stable LTS Release: [Install ROS2 Humble](https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debians.html)

   After installing ROS2, source the setup.bash, which will set the `$ROS_DISTRO` environment variable.

2. Install this package from binary
   ```
   sudo apt install ros-$ROS_DISTRO-kortex-bringup
   ```

3. Optional: install MoveIt Configuration and Cyclone DDS

   If you have a 7dof arm:
   ```
   sudo apt install ros-$ROS_DISTRO-kinova-gen3-7dof-robotiq-2f-85-moveit-config
   ```
   If you have a 6dof arm:
   ```
   sudo apt install ros-$ROS_DISTRO-kinova-gen3-6dof-robotiq-2f-85-moveit-config
   ```
   If you plan to use MoveIt, it is recommended to install and use Cyclone DDS.
   ```
   sudo apt install ros-$ROS_DISTRO-rmw-cyclonedds-cpp
   export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
   ```

4. Go to Usage section

## Contributing to this repository or building from source

Note: It is recommended to use a released binary version of this package and apt install it.
If you want the latest version of this repository for testing latest fixes
check out testing with pre-released binaries: https://docs.ros.org/en/rolling/Installation/Testing.html

If the bug fix you need isn't in a released version or If you want to build this repository from source or contribute back to the repository read on.

1. Make sure that `colcon`, its extensions, and `vcs` are installed:
   ```
   sudo apt install python3-colcon-common-extensions python3-vcstool
   ```

2. Create a new ROS2 workspace:
   ```
   export COLCON_WS=~/workspace/ros2_kortex_ws
   mkdir -p $COLCON_WS/src
   ```

3. Pull relevant packages:
   ```
   cd $COLCON_WS
   git clone -b humble --single-branch https://github.com/Kinovarobotics/ros2_kortex.git src/ros2_kortex
   vcs import src --skip-existing --input src/ros2_kortex/ros2_kortex.$ROS_DISTRO.repos
   vcs import src --skip-existing --input src/ros2_kortex/ros2_kortex-not-released.$ROS_DISTRO.repos
   ```

   If you plan on simulating the robot with ignition or gazebo, first install the simulator using the following commands:
  ```
  sudo apt-get update && sudo apt-get install wget
  sudo sh -c 'echo "deb http://packages.osrfoundation.org/gazebo/ubuntu-stable `lsb_release -cs` main" > /etc/apt/sources.list.d/gazebo-stable.list'
  wget http://packages.osrfoundation.org/gazebo.key -O - | sudo apt-key add -
  sudo apt-get update && sudo apt-get install ignition-fortress
  ```
  Then make sure to pull the additional simulation packages. If you're on ROS2 Humble, run:
   ```
   vcs import src --skip-existing --input src/ros2_kortex/simulation.humble.repos
   ```

   otherwise
   ```
   vcs import --skip-existing --input src/ros2_kortex/simulation.repos
   ```

   If you plan on using MoveIt, you must make sure that you have it already [installed](https://moveit.ros.org/install-moveit2/binary/) either from binaries or by building it from source.

   If you plan on simulating the Gen3 7Dof robot mounted on the Husky mobile robot from clearpath, make sure to pull the additional related packages. On ROS2 Humble, run
   ```
   vcs import src --skip-existing --input src/ros2_kortex/clearpath.repos
   ```

4. Install dependencies, compile, and source the workspace:
   ```
   rosdep install --ignore-src --from-paths src -y -r
   colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release
   ```

   By default, colcon will use as much resources as possible to build the ROS2 workspace. This can temporarily freeze or even crash your machine. You can limit the number of threads used to avoid this issue, we found a good tradeoff between build time and resource utilisation by setting it to 3 :
   ```
   colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release --parallel-workers 3
   ```
5. Source the previously built workspace using the following command:
   ```
   echo 'source ~/workspace/ros2_kortex_ws/install/setup.bash' >> ~/.bashrc
   ```

## Simulation Issues

Please note, at this time there are two known issues you with simulation

1. Gazebo + Mimic Joints for the Robotiq Gripper
2. Protobuf version mismatch

# Gazebo and Mimic Joints

A pull request has been made to gz_ros2_control which is how this repository was tested in simulation.
The pull request won't be merged as the fix should be done upstream in gz-sim.
Once a fix is available ros2_robotiq_gripper will be re-released and an update should fix any workarounds.

In the meantime if you need simulation checkout the upstream pull request link:

- Upstream Issue: https://github.com/gazebosim/gz-sim/issues/1684
- Upstream Pull Request: https://github.com/ros-controls/gz_ros2_control/pull/86
- Tracking Issue: https://github.com/PickNikRobotics/ros2_robotiq_gripper/issues/7

# Protobuf

Due to mismatched protobuf version that ships system and used by Gazebo simulator compiling twice may be required.
You will only run into this if you have certain other gazebo related code in your workspace while compiling this repository.
If errors are encounter you must clean your workspace and run colcon build in two steps:

1. build everything except kortex related packages
2. build the packages that where skipped

```
sudo apt install python3-colcon-clean # if you don't have colcon-clean installed already
colcon clean workspace -y
colcon build --packages-skip-regex '.*kortex.*' '.*gen3.*'
colcon build --packages-select-regex '.*kortex.*' '.*gen3.*'
```

## Usage
To launch and view any of the robot's URDF run:

```bash
ros2 launch kortex_description view_robot.launch.py
```

The accepted arguments are:

* `robot_type` : Your robot model. Possible values are either `gen3` or `gen3_lite`, the default is `gen3`.

* `gripper` : Gripper to use. Possible values for the Gen3 are either `robotiq_2f_85` or `robotiq_2f_140`. For the Gen3 Lite, the only option is `gen3_lite_2f`. Default value is an empty string, which will display the arm without a gripper.

* `dof` : Degrees of freedom of the arm. Possible values for the Gen3 are either `6` or `7`. For the Gen3 Lite, the only option is `6`. Default value is `7`.

### Gen 3 Robots

The `gen3.launch.py` launch file is designed to be used for Gen3 arms. The typical use case to bringup and visualize the 7 DoF Kinova Gen3 robot arm (default) with mock hardware on Rviz:

```bash
ros2 launch kortex_bringup gen3.launch.py \
  robot_ip:=yyy.yyy.yyy.yyy \
  use_fake_hardware:=true
```

Alternatively, for a physical robot:

```bash
ros2 launch kortex_bringup gen3.launch.py \
  robot_ip:=192.168.1.10
```
You can specify the following arguments if you wish to change your arm configuration:

* `robot_type`: Your robot model. Default value (and only one) is `gen3`.

* `gripper` : Gripper to use. Possible values for the Gen3 are either `robotiq_2f_85`, `robotiq_2f_140` or `""`. Default is `""`. An empty string will not initialise any gripper.

* `gripper_joint_name` : Name of the controlled joint of the gripper attached to the arm. Default value is `robotiq_85_left_knuckle_joint`.

* `use_internal_bus_gripper_comm` : Use internal bus for gripper communication. Default value is `true`.

* `gripper_max_velocity` : Max velocity for gripper commands. Default value is `100.0`.

* `gripper_max_force` : Max force for gripper commands. Default value is `100.0`.

* `dof` : Degrees of freedom of the arm. Possible values are either `6` or `7`.Default value is `7`.

* `robot_ip` : IP address by which the robot can be reached. No default is specified, this is a required argument. All arms are shipped with address `192.168.1.10`, but if you have reassigned your physical arm's robot IP address, then you will need to assign that ip address.

* `use_fake_hardware` : Start robot with fake hardware mirroring command to its states. Default value is `false`.

* `fake_sensor_commands` : Enable fake command interfaces for sensors used for simple simulations. Used only if 'use_fake_hardware' parameter is true. Default value is `false`.

* `robot_controller` : Robot controller to start. Possible values are `twist_controller` and `joint_trajectory_controller`.Default value is `joint_trajectory_controller`.

* `controllers_file` : Ros 2 control configuration file to use. Default value is `ros2_controllers.yaml`

* `launch_rviz` : Start an Rviz window to visualize the robot. Default value is `true`.

### Gen 3 Lite Robot

The `gen3_lite.launch.py` launch file is designed to be used for Gen3 Lite arms. The typical use case to bringup the robot arm with mock hardware:

```bash
ros2 launch kortex_bringup gen3_lite.launch.py \
  robot_ip:=yyy.yyy.yyy.yyy \
  use_fake_hardware:=true
```
Alternatively, if you wish to use the physical robot:

```bash
ros2 launch kortex_bringup gen3_lite.launch.py \
  robot_ip:=192.168.1.10 \
```

You can specify the following arguments if you wish to change your arm configuration:

* `robot_type`: Your robot model. Default value (and only one) is `gen3_lite`.

* `gripper` : Gripper to use. Default value (and only one) is `gen3_lite_2f`.

* `gripper_joint_name` : Name of the controlled joint of the gripper attached to the arm. Default value (and only one) is `right_finger_bottom_joint`.

* `use_internal_bus_gripper_comm` : Use internal bus for gripper communication. Default value is `true`.

* `gripper_max_velocity` : Max velocity for gripper commands. Default value is `100.0`.

* `gripper_max_force` : Max force for gripper commands. Default value is `100.0`.

* `robot_ip` : IP address by which the robot can be reached. No default is specified, this is a required argument. All arms are shipped with address `192.168.1.10`, but if you have reassigned your physical arm's robot IP address, then you will need to assign that ip address. If you're using an USB to Ethernet interface to connect your robot to your machine instead of USB via RNDIS, the ip address will be `192.168.2.10`.

* `use_fake_hardware` : Start robot with fake hardware mirroring command to its states. Default value is `false`.

* `fake_sensor_commands` : Enable fake command interfaces for sensors used for simple simulations. Used only if 'use_fake_hardware' parameter is true. Default value is `false`.

* `robot_controller` : Robot controller to start. Possible values are `twist_controller` and `joint_trajectory_controller`.Default value is `joint_trajectory_controller`.

* `controllers_file` : Ros 2 control configuration file to use. Default value is `ros2_controllers.yaml`

* `description_file` : URDF/XACRO description file with the robot. Default value is `gen3_lite_gen3_lite_2f.xacro`.

* `launch_rviz` : Start an Rviz window to visualize the robot. Default value is `true`.


## Simulation
The `kortex_sim_control.launch.py` launch file is designed to simulate all of our arm models, you just need to specify your configuration through the arguments. By default, the Gen3 7 dof configuration is used :

```bash
ros2 launch kortex_bringup kortex_sim_control.launch.py \
  use_sim_time:=true \
  launch_rviz:=false
```

* `sim_ignition` : Use Ignition for simulation. Default value is `true`.
* `sim_gazebo` : Use Gazebo Classic for simulation. Default value is `false`.
* `robot_type` : Your robot model. Possible values are either `gen3` or `gen3_lite`.Default is `gen3`.
* `robot_name` : Name you would like your robot to have. Default value is `gen3`.
* `dof` : Degrees of freedom of the arm. Possible values are either `6` or `7`.Default value is `7`.
* `vision` : Use arm mounted realsens. Possible values are either `true` or `false`. Default value is `false`. This option does not generate simulated images, it only loads up the robot's URDF that includes the vision link.
* `robot_controller` : Robot joint controller to start. Default value is `joint_trajectory_controller`.
* `robot_pos_controller` : Robot position controller to start. Default value is `twist_controller`.
* `robot_hand_controller` : Robot gripper controller to start. Default value is `robotiq_gripper_controller`.
* `controllers_file` :  Ros 2 control configuration file to use. Default value is `ros2_controllers.yaml`
* `description_package` : Description package with robot URDF/XACRO files. Default value is `kortex_description`.
* `description_file` : URDF/XACRO description file with the robot. Default value is `kinova.urdf.xacro`.
* `prefix` : Prefix of the joint names, useful for multi-robot setup. If changed, then also joint names in the controllers' configuration have to be updated. Default value is `""` (none).
* `use_sim_time` : Use simulated clock. Default value is `true`.
* `gripper` : Gripper to use. Possible values for the Gen3 are: `robotiq_2f_85`, `robotiq_2f_140`, `""` and `gen3_lite_2f` and the default value is `""` which will not initialise any gripper.

## MoveIt2

#### Virtual Hardware

To generate motion plans and execute them with virtual arm hardware:

1. For a 6 DoF Kinova Gen3 arm, run the following:

```bash
ros2 launch kinova_gen3_6dof_robotiq_2f_85_moveit_config robot.launch.py \
  robot_ip:=yyy.yyy.yyy.yyy \
  use_fake_hardware:=true
```

2. For a 7 DoF Kinova Gen3 arm, run the following:

```bash
ros2 launch kinova_gen3_7dof_robotiq_2f_85_moveit_config robot.launch.py \
  robot_ip:=yyy.yyy.yyy.yyy \
  use_fake_hardware:=true
```

#### Real-Life Hardware

To generate motion plans and execute them with real-life hardware:

1. For a 6 DoF Kinova Gen3 arm with default IP address, run the following:

```bash
ros2 launch kinova_gen3_6dof_robotiq_2f_85_moveit_config robot.launch.py \
  robot_ip:=192.168.1.10
```

2. For a 7 DoF Kinova Gen3 arm with default IP address, run the following:

```bash
ros2 launch kinova_gen3_7dof_robotiq_2f_85_moveit_config robot.launch.py \
  robot_ip:=192.168.1.10
```

3. For a Gen3-Lite arm with default IP address and connected through USB, run the following:

```bash
ros2 launch kinova_gen3_lite_moveit_config robot.launch.py \
  robot_ip:=192.168.2.10
```

#### Simulated Robot

To generate motion plans and execute them in simulation, make sure to first start the simulated robot with the command at the [simulation](#simulation) section, then:

1. For a 6 DoF Kinova Gen3 arm, run the following:
```bash
ros2 launch kinova_gen3_6dof_robotiq_2f_85_moveit_config sim.launch.py \
  use_sim_time:=true
```
2. For a 7 DoF Kinova Gen3 arm, run the following:
```bash
ros2 launch kinova_gen3_7dof_robotiq_2f_85_moveit_config sim.launch.py \
  use_sim_time:=true
```

3. For a Gen3-Lite arm, run the following:
```bash
ros2 launch kinova_gen3_lite_moveit_config sim.launch.py \
  use_sim_time:=true
```

## Commanding the arm (physically and in simulation)
You can command the arm by publishing Joint Trajectory messages directly to the joint trajectory controller with joint positions are in **radians**:

```bash
ros2 topic pub /joint_trajectory_controller/joint_trajectory trajectory_msgs/JointTrajectory "{
  joint_names: [joint_1, joint_2, joint_3, joint_4, joint_5, joint_6, joint_7],
  points: [
    { positions: [0, 0, 0, 0, 0, 0, 0], time_from_start: { sec: 10 } },
  ]
}" -1
```

Depending on your robot type and its DoF, you will need to adapt the `joint_names` and `positions` properties accordingly. For the Gen3 Lite arm, the integrated gripper is considered as a joint, so to command it, it must be included in the `joint_names` array. (`0.0=open`, `1.0=close`):

```bash
ros2 topic pub /joint_trajectory_controller/joint_trajectory trajectory_msgs/JointTrajectory "{
  joint_names: [joint_1, joint_2, joint_3, joint_4, joint_5, joint_6, right_finger_bottom_joint],
  points: [
    { positions: [0, 0, 0, 0, 0, 0, 1], time_from_start: { sec: 10 } },
  ]
}" -1
```

You can also command the arm using Twist messages. Before doing so, you must active the `twist_controller` and deactivate the `joint_trajectory_controller`:
```bash
ros2 service call /controller_manager/switch_controller controller_manager_msgs/srv/SwitchController "{
  activate_controllers: [twist_controller],
  deactivate_controllers: [joint_trajectory_controller],
  strictness: 1,
  activate_asap: true,
}"
```

**Note: the required interface for the `twist_controller` does not currently exist in the gazebo or mock hardware simulation setups. So the `twist_controller` is currently only functional on Kinova hardware.**

Once the `twist_controller` is activated, You can publish Twist messages on the `/twist_controller/commands` topic to command the arm.

For example, you can jog the arm using [Teleop Twist Keyboard](https://index.ros.org/p/teleop_twist_keyboard/github-ros2-teleop_twist_keyboard/) with the following command:

**WARNING: you are responsible for collision checking, including self collisions when in this mode.**

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args --remap /cmd_vel:=/twist_controller/commands
```

If you wish to use the `joint_trajectory_controller` again to command the arm using JointTrajectory messages, run the following:
```bash
ros2 service call /controller_manager/switch_controller controller_manager_msgs/srv/SwitchController "{
  activate_controllers: [joint_trajectory_controller],
  deactivate_controllers: [twist_controller],
  strictness: 1,
  activate_asap: true,
}"
```

#### Robotiq gripper

The Robotiq 2f 85 (or 2f 140) Gripper will be available on the Action topic:

```bash
/robotiq_gripper_controller/gripper_cmd
```

You can test the gripper by calling the Action server with the following command and setting the desired `position` of the gripper (`0.1=open`, `0.7=close`)

```bash
ros2 action send_goal /robotiq_gripper_controller/gripper_cmd control_msgs/action/GripperCommand "{command:{position: 0.0, max_effort: 100.0}}"
```

#### Vision Module

In order to access the Kinova Vision module's depth and color streams for the camera-equipped Gen3 arm models, please refer to the following github repository for detailed instructions: [ros2_kortex_vision](https://github.com/Kinovarobotics/ros2_kortex_vision)


## Contents

The following is a description of the packages included in this repository.

### kortex_description
This package contains the URDF (Unified Robot Description Format), STL and configuration files for the Kortex-compatible robots. For more details, please consult the [README](kortex_description/readme.md) from the package subdirectory.

### kortex_driver
This package implements a ROS node that allows communication between a node and a Kinova Gen3 or Gen3 lite robot. For more details, please consult the [README](kortex_driver/readme.md) from the package subdirectory.

### kortex_moveit_config
This metapackage contains the auto-generated MoveIt! files to use the Kinova Gen3 and Gen3 lite arms with the MoveIt! motion planning framework. For more details, please consult the [README](kortex_moveit_config/readme.md) from the package subdirectory.

# Dual Control (2 Gen3 7DoF or 6DoF)

1. Make sure to connect each robotic arm via an Ethernet connection, and assign each arm to a different IP subnet (for example, one at 192.168.1.10 and the other at 192.168.2.10).

2. Start the dual control launch file using the following command:

```
ros2 launch kortex_bringup gen3_dual.launch.py robot_ip_1:=192.168.1.10 robot_ip_2:=192.168.2.10
```

You can specify the following arguments if you wish to change your arms configurations:

* `robot_ip_1` : IP address by which the first robot can be reached. The default is empty, this is a required argument. All arms are shipped with address `192.168.1.10`by default, but if you have reassigned your physical arm's robot IP address, then you will need to assign that ip address.

* `robot_ip_2` : IP address by which the second robot can be reached. The default is empty, this is a required argument. All arms are shipped with address `192.168.1.10`by default, but if you have reassigned your physical arm's robot IP address, then you will need to assign that ip address.

* `gripper_1` : Gripper to use with the first arm. Possible values for the Gen3 are either `robotiq_2f_85`, `robotiq_2f_140` or `""`. Default is `""`. An empty string will not initialise any gripper.

* `gripper_2` : Gripper to use with the second arm. Possible values for the Gen3 are either `robotiq_2f_85`, `robotiq_2f_140` or `""`. Default is `""`. An empty string will not initialise any gripper.

* `dof_1` : Degrees of freedom of the first arm. Possible values are either `6` or `7`.Default value is `7`.

* `dof_2` : Degrees of freedom of the first arm. Possible values are either `6` or `7`.Default value is `7`.

3. Use the following command to control the first arm's joints positions:

**6DoF**

```
ros2 topic pub /arm_1_/joint_trajectory_controller/joint_trajectory trajectory_msgs/JointTrajectory "{
  joint_names: [arm_1_joint_1, arm_1_joint_2, arm_1_joint_3, arm_1_joint_4, arm_1_joint_5, arm_1_joint_6],
  points: [
    { positions: [0, 0, 0, 0, 0, 0], time_from_start: { sec: 10 } },
  ]
}" -1
```

**7DoF**

```
ros2 topic pub /arm_1_/joint_trajectory_controller/joint_trajectory trajectory_msgs/JointTrajectory "{
  joint_names: [arm_1_joint_1, arm_1_joint_2, arm_1_joint_3, arm_1_joint_4, arm_1_joint_5, arm_1_joint_6, arm_1_joint_7],
  points: [
    { positions: [0, 0, 0, 0, 0, 0, 0], time_from_start: { sec: 10 } },
  ]
}" -1
```

4. Use the following command to control the second arm's joints positions:

**6DoF**

```
ros2 topic pub /arm_2_/joint_trajectory_controller/joint_trajectory trajectory_msgs/JointTrajectory "{
  joint_names: [arm_2_joint_1, arm_2_joint_2, arm_2_joint_3, arm_2_joint_4, arm_2_joint_5, arm_2_joint_6],
  points: [
    { positions: [0, 0, 0, 0, 0, 0], time_from_start: { sec: 10 } },
  ]
}" -1
```

**7DoF**

```
ros2 topic pub /arm_2_/joint_trajectory_controller/joint_trajectory trajectory_msgs/JointTrajectory "{
  joint_names: [arm_2_joint_1, arm_2_joint_2, arm_2_joint_3, arm_2_joint_4, arm_2_joint_5, arm_2_joint_6, arm_2_joint_7],
  points: [
    { positions: [0, 0, 0, 0, 0, 0, 0], time_from_start: { sec: 10 } },
  ]
}" -1
```
