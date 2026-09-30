## Hardware Setup

### Kinova Gen 3

1. Connect the power cable to the robot and an Ethernet cable to your laptop
2. Replace the Robotiq gripper with Clarius scanner by removing the 4 screws
3. Power up the robot by holding the power button until seeing the green light
4. Wait for around 30 second, then open [Kinova Web Interface](http://192.168.1.10/)
5. Ensure the surround environment for robot is clean and empty
6. In the web interface, run zero pose from the action on the bottom

  ![Run the Kinova zero-pose action](doc/resources/kinova-zero-pose-action.png)

7. Go to robot and set the torque on each joint to be zero

  ![Open the Kinova robot configuration menu](doc/resources/kinova-robot-configuration-menu.png)

  ![Set each Kinova actuator torque offset to zero](doc/resources/kinova-zero-torque-offset.png)

8. Run retract pose from the action on the bottom

  ![Run the Kinova retract pose action](doc/resources/kinova-retract-pose-action.png)

### Clarius

1. Unlock the tablet using `WESTL25!`
2. Open Clarius app
3. Turn on Clarius by pressing the power button
4. Connect Clarius to the tablet
5. Ensure IMU is turned on

### Realsense

1. Connect the RealSense camera to the laptop

## Software Setup

### First Time Used

1. Install Docker Engine following this [instruction](https://docs.docker.com/engine/install/) and ensure the user to run Docker

	```bash
	sudo usermod -aG docker "$USER"
	```

2. Configure the host so Clarius Wi-Fi and robot Ethernet work together.
	- The robot is at `192.168.1.10` over Ethernet and the Clarius probe is at `192.168.1.1` over `DIRECT_CLARIUS`
	- Because both are on the `192.168.1.0/24` subnet, use a host route for each device
	- Follow these steps while Ethernet remains connected
	- Replace the example interface and connection names with the values shown by:

		```bash
		nmcli -f NAME,TYPE,DEVICE connection show --active
		ip -br address
		```

	1. Connect to the Clarius Wi-Fi:

		```bash
		nmcli connection up DIRECT_CLARIUS
		```

	2. Add a route for each device to the correct interface:

		```bash
		sudo ip route replace 192.168.1.1/32 dev wlp0s20f3
		sudo ip route replace 192.168.1.10/32 dev enx68da73a52630
		```

	3. Confirm Clarius traffic uses Wi-Fi:

		```bash
		ip route get 192.168.1.1
		```

	It should contain:

		```text
		dev wlp0s20f3
		```

	4. Confirm robot traffic still uses Ethernet:

	```bash
	ip route get <ROBOT_IP>
	```

	It should contain:

	```text
	dev enx68da73a52630
	```

	Replace `<ROBOT_IP>` with the robot arm’s actual address.

	5. Once confirmed working, make both routes persistent. Replace `"Wired connection 1"` with the Ethernet connection name reported by `nmcli`:

	```bash
	sudo nmcli connection modify DIRECT_CLARIUS ipv4.never-default yes
	sudo nmcli connection modify DIRECT_CLARIUS +ipv4.routes "192.168.1.1/32"
	sudo nmcli connection modify "Wired connection 1" ipv4.never-default yes
	sudo nmcli connection modify "Wired connection 1" +ipv4.routes "192.168.1.10/32"
	sudo nmcli connection up "Wired connection 1"
	sudo nmcli connection up DIRECT_CLARIUS
	```

	6. Verify again:

	```bash
	ip route get 192.168.1.1
	ip route get <ROBOT_IP>
	```

	The development container uses host networking, so it inherits these routes. Do not use this setup if the robot itself also has IP address `192.168.1.1`; duplicate addresses cannot be reliably routed this way.
3. Make sure [SSH key](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent) has been added to the GitHub and the following repos are being shared
	- [clarius_interface](https://github.com/westlab-uwo/clarius_interface)
	- [clarius_description](https://github.com/ripl-lab/clarius_description)
	- [multi-label_segmentation](https://github.com/westlab-uwo/multi-label_segmentation)
4. Run the following command to clone the repo

	```bash
	mkdir -p ~/workspace/clarius_ws/src
	cd ~/workspace/clarius_ws/src
	git clone git@github.com:ripl-lab/ros2_kortex.git
	```

The host workspace is named `clarius_ws`; the Docker helper mounts it at the fixed internal path `/workspace/ros2_kortex_ws`, so commands run inside the container continue to use that internal path.

### Build and Run

1. Build and enter the container. The first build may take approximately 10 minutes.

	```bash
	cd ~/workspace/clarius_ws/src/ros2_kortex
	./.devcontainer/dev-docker.sh -- \
    colcon build --cmake-args \
      -DCMAKE_BUILD_TYPE=Release \
      -DDOWNLOAD_UNITREE_H1_ASSETS=OFF \
      --executor sequential
	```

	To skip rebuilding and initializing an existing environment:

	```bash
	./.devcontainer/dev-docker.sh --no-build --no-init
	```

2. Inside the Docker container, you should see a prompt similar to:

	```bash
	(.venv) clarius@user-Yoga-Pro-9-16IMH9:/workspace/ros2_kortex_ws$
	```

3. Launch the Kinova Gen3, Clarius interface, RealSense camera, AprilTag tracking, admittance controller, and RViz:

	```bash
	ros2 launch kortex_bringup gen3_admittance_clarius.launch.py \
		robot_ip:=192.168.1.10 \
		force_test_response:=true \
		start_clarius:=true \
		start_apriltag_tracking:=true \
		launch_realsense:=true \
		vision:=true \
		launch_rviz:=true \
		auto_move_activation_pose:=true \
		constrain_eef_orientation:=true
	```

3. Keep the emergency stop accessible and observe the automatic movement to the activation pose. Confirm that the path and final scanning pose are safe before approaching the robot.
	- The configured activation pose is: [0, 30, 180, 260, 360, 310, 0] degrees
		- If the pose is unsuitable:
		- Stop using the robot emergency stop if immediate motion is unsafe.
		- Otherwise stop the launch with `Ctrl+C`.
		- Move the robot to a safe configuration.
		- Update activation_pose_degrees in: ` src/ros2_kortex/kortex_bringup/scripts/activation_pose_service.py`
		- Rebuild and source the package:

			```bash
			colcon build --packages-select kortex_bringup --symlink-install
			source install/setup.bash
			```

		- To launch without automatically moving the robot:

			```bash
			ros2 launch kortex_bringup gen3_admittance_clarius.launch.py \
				robot_ip:=192.168.1.10 \
				force_test_response:=true \
				auto_move_activation_pose:=false
			```

		- The activation pose can then be requested manually:

			```bash
			ros2 service call /move_to_activation_pose std_srvs/srv/Trigger "{}"
			```

4. To open another shell in the already-running container:

	```bash
	docker exec -it ros2-kortex-dev bash
	```

### Expected behaviour

1. Initialize the Kinova Gen3, Clarius interface, RealSense camera, AprilTag tracking, admittance controller, and RViz.
2. Automatically switch the host Wi-Fi connection to `DIRECT_CLARIUS`.
3. Read the measured joint positions and move smoothly to the activation scanning pose if needed.
4. Switch from the joint trajectory controller to the admittance controller after reaching the activation pose.
5. Capture the activation-pose orientation as the constrained EEF orientation.
6. Permit force-guided XYZ translation while keeping the scanner orientation fixed.
7. Stop translational movement after the applied force is released and the latch settles.
8. Display the robot, estimated wrench, Clarius image, segmentation result, and RealSense image in one RViz session.
9. When the launch exits normally, attempt to restore the configured Wi-Fi connection.

### Configurable arguments

- Useful launch arguments include:
	- `use_fake_hardware:=false`: Use the real robot. Set it to true for testing without a connected robot.
	- `force_test_response:=true`: Allow the estimated wrench to command admittance motion. When false, wrench estimation remains active but the robot should not respond to it.
	- `auto_move_activation_pose:=true`: Automatically move to the activation pose during launch.
	- `constrain_eef_orientation:=true`: Keep the activation-pose orientation while allowing XYZ admittance motion.
	- `constrain_eef_z_motion:=true`: Lock base-frame Z translation while retaining X/Y admittance motion.
	- `start_clarius:=true`: Start the Clarius connection and segmentation pipeline.
	- `start_apriltag_tracking:=true`: Start the RealSense and AprilTag tracking pipeline.
	- `launch_realsense:=true`: Start the RealSense camera used by AprilTag tracking.
	- `vision:=true`: Include the Kinova vision configuration.
	- `launch_rviz:=true`: Open the combined RViz session.
	- `admittance_mode:=move_and_stay`: Move under applied force, then latch the released position.
	- `start_clarius:=false` and `start_apriltag_tracking:=false`: Useful for testing only the robot and controller.
- For a fake-hardware test:

	```bash
	ros2 launch kortex_bringup gen3_admittance_clarius.launch.py \
		use_fake_hardware:=true \
		force_test_response:=true \
		start_clarius:=false \
		start_apriltag_tracking:=false \
		launch_rviz:=true \
		auto_move_activation_pose:=true \
		constrain_eef_orientation:=true
	```

## Collect Data on the Real Robot

1. Start the real-robot master launch and wait until the robot, Clarius, and RealSense streams are stable.
	- Keep `use_sim_time` disabled for live data.

2. In a second container shell, verify the reconstruction inputs and camera streams:

	```bash
	ros2 topic hz /joint_states
	ros2 topic hz /clarius/image_raw
	ros2 topic hz /camera/camera/color/image_raw
	ros2 topic echo /estimated_wrench --once
	ros2 run tf2_ros tf2_echo base_link clarius_sensor_frame
	```

3. Record the raw ultrasound, robot motion, transforms, wrench, RealSense image, and AprilTag detections:

	```bash
	cd /workspace/ros2_kortex_ws
	mkdir -p bags

	ros2 bag record \
		-o "bags/scan_$(date +%Y%m%d_%H%M%S)" \
		/robot_description \
		/joint_states \
		/tf \
		/tf_static \
		/estimated_wrench \
		/clarius/image_raw \
		/clarius/imu \
		/clarius/imu_pose \
		/camera/camera/color/image_raw \
		/camera/camera/color/camera_info \
		/apriltag/detections
	```

	- `/joint_states`, `/tf`, `/tf_static`, and `/clarius/image_raw` are the source data used to place each ultrasound slice using robot motion.
	- The segmentation image and `/prediction_pointcloud` are derived outputs, so they are regenerated during replay instead of being required in the recording.

4. Press `Ctrl+C` once in the recording terminal after the scan.
	- Wait for rosbag2 to finish writing `metadata.yaml` before stopping the master launch or disconnecting hardware.

5. Check the recording:

	```bash
	ros2 bag info bags/scan_YYYYMMDD_HHMMSS
	```


## Replay a Rosbag and Regenerate the Point Cloud

No real robot, Clarius probe, or RealSense camera is required for replay.

1. Enter the container and run:

	```bash
	cd /workspace/ros2_kortex_ws
	src/ros2_kortex/kortex_bringup/scripts/play_rosbag.sh \
		bags/scan_YYYYMMDD_HHMMSS \
		ultrasound_delay:=0.0 \
		start_segmentation:=true
	```

   This opens RViz, publishes the bag clock, replays the robot state and raw ultrasound, runs segmentation, and regenerates the accumulated `/prediction_pointcloud`.

2. Keep `ultrasound_delay:=0.0` for reconstruction so the original recorded timing is preserved. A positive value intentionally starts ultrasound later and should only be used for timing diagnostics.

3. Optional replay controls include:

	```bash
	# Prepare the RViz view before playback begins.
	src/ros2_kortex/kortex_bringup/scripts/play_rosbag.sh BAG_PATH \
		start_paused:=true

	# Skip the first 5 seconds and replay at half speed.
	src/ros2_kortex/kortex_bringup/scripts/play_rosbag.sh BAG_PATH \
		start_offset:=5.0 rate:=0.5
	```

   With `ultrasound_delay:=0.0`, press the space bar in the rosbag playback terminal to pause or resume the topics. RViz remains interactive while the bag is paused.

## Save the Point Cloud to PLY

1. Start the saver in a separate container shell before replaying the bag:

	```bash
	cd /workspace/ros2_kortex_ws
	ros2 run kortex_bringup save_pointcloud_ply.py \
		/workspace/ros2_kortex_ws/reconstruction.ply
	```

2. Run the replay command with `start_segmentation:=true` in another shell

3. Wait until playback ends and the final accumulated point cloud appears in RViz.

4. Save the most recently received cloud:

	```bash
	ros2 service call /save_prediction_ply std_srvs/srv/Trigger "{}"
	```

   - The response reports the output path and number of points.
   - Pressing `Ctrl+C` in the saver terminal also saves the latest cloud.

5. If the saver only reports that it is waiting for `/prediction_pointcloud`, check that segmentation is running and the topic is active:

	```bash
	ros2 topic hz /prediction_pointcloud
	ros2 topic info /prediction_pointcloud --verbose
	```

6. Clear the accumulated cloud before starting another live scan or replay:

	```bash
	ros2 service call /reset_prediction_pointcloud std_srvs/srv/Empty "{}"
	```
