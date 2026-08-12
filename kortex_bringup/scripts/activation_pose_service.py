#!/usr/bin/env python3

import math
import threading

import rclpy
from control_msgs.action import FollowJointTrajectory
from control_msgs.msg import JointTolerance
from controller_manager_msgs.srv import SwitchController
from rclpy.action import ActionClient
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_srvs.srv import Trigger
from trajectory_msgs.msg import JointTrajectoryPoint


def kinova_degrees_to_ros_radians(angle_degrees):
    """Map Kinova's [0, 360] degree convention to the nearest ROS angle."""
    radians = math.radians(float(angle_degrees))
    normalized = (radians + math.pi) % (2.0 * math.pi) - math.pi
    # Preserve positive 180 degrees as +pi when no current joint state is
    # available. This avoids the common +pi -> -pi full-turn interpolation.
    if math.isclose(normalized, -math.pi, abs_tol=1e-12) and angle_degrees > 0:
        return math.pi
    return normalized


def nearest_equivalent_angle(target, current):
    """Return target + 2*pi*k on the branch closest to current."""
    turns = math.floor((current - target) / (2.0 * math.pi) + 0.5)
    return target + turns * 2.0 * math.pi


class ActivationPoseService(Node):
    def __init__(self):
        super().__init__("activation_pose_service")
        self.callback_group = ReentrantCallbackGroup()
        self.declare_parameter("joint_names", [f"joint_{index}" for index in range(1, 8)])
        self.declare_parameter(
            "continuous_joint_names", ["joint_1", "joint_3", "joint_5", "joint_7"]
        )
        self.declare_parameter(
            "activation_pose_degrees", [0.0, 30.0, 180.0, 260.0, 0.0, 310.0, 0.0]
        )
        self.declare_parameter("trajectory_duration", 15.0)
        self.declare_parameter("handoff_hold_duration", 1.0)
        self.declare_parameter("goal_tolerance_degrees", 0.5)
        self.declare_parameter("goal_time_tolerance", 5.0)
        self.declare_parameter("auto_move", True)
        self.declare_parameter("auto_move_delay", 2.0)
        self.declare_parameter("service_timeout", 30.0)
        self.declare_parameter("trajectory_controller", "joint_trajectory_controller")
        self.declare_parameter("restore_controller", "admittance_controller")
        self.declare_parameter("restore_state_only_admittance", False)

        controller = self.get_parameter("trajectory_controller").value
        self.switch_client = self.create_client(
            SwitchController,
            "/controller_manager/switch_controller",
            callback_group=self.callback_group,
        )
        self.trajectory_client = ActionClient(
            self,
            FollowJointTrajectory,
            f"/{controller}/follow_joint_trajectory",
            callback_group=self.callback_group,
        )
        self.service = self.create_service(
            Trigger,
            "/move_to_activation_pose",
            self.handle_move_request,
            callback_group=self.callback_group,
        )
        self.motion_lock = threading.Lock()
        self.joint_state_lock = threading.Lock()
        self.current_positions = {}
        self.joint_state_event = threading.Event()
        self.joint_state_subscription = self.create_subscription(
            JointState,
            "/joint_states",
            self.handle_joint_state,
            10,
            callback_group=self.callback_group,
        )
        self.auto_timer = None
        if self.get_parameter("auto_move").value:
            delay = max(0.1, float(self.get_parameter("auto_move_delay").value))
            self.auto_timer = self.create_timer(
                delay, self.handle_auto_move, callback_group=self.callback_group
            )

        self.get_logger().info(
            "activation pose service ready at /move_to_activation_pose"
        )

    def handle_joint_state(self, message):
        with self.joint_state_lock:
            self.current_positions.update(zip(message.name, message.position))
            if self.current_positions:
                self.joint_state_event.set()

    def wait_for_future(self, future, timeout):
        completed = threading.Event()
        future.add_done_callback(lambda _: completed.set())
        if not completed.wait(timeout):
            raise TimeoutError("operation timed out")
        exception = future.exception()
        if exception is not None:
            raise exception
        return future.result()

    def switch_controllers(self, activate, deactivate):
        timeout = float(self.get_parameter("service_timeout").value)
        if not self.switch_client.wait_for_service(timeout_sec=timeout):
            raise RuntimeError("controller-manager switch service is unavailable")
        request = SwitchController.Request()
        request.activate_controllers = list(activate)
        request.deactivate_controllers = list(deactivate)
        request.strictness = SwitchController.Request.BEST_EFFORT
        request.activate_asap = True
        request.timeout.sec = int(timeout)
        response = self.wait_for_future(
            self.switch_client.call_async(request), timeout + 1.0
        )
        if not response.ok:
            raise RuntimeError(
                f"failed to switch controllers; activate={activate}, deactivate={deactivate}"
            )

    def execute_activation_pose(self):
        joint_names = list(self.get_parameter("joint_names").value)
        continuous_joints = set(
            self.get_parameter("continuous_joint_names").value
        )
        angles = list(self.get_parameter("activation_pose_degrees").value)
        if len(joint_names) != 7 or len(angles) != 7:
            raise ValueError("joint_names and activation_pose_degrees must contain 7 values")

        timeout = float(self.get_parameter("service_timeout").value)
        if not self.joint_state_event.wait(timeout=min(timeout, 5.0)):
            raise RuntimeError("no joint state received; refusing to move")
        with self.joint_state_lock:
            current_positions = dict(self.current_positions)
        missing_joints = [name for name in joint_names if name not in current_positions]
        if missing_joints:
            raise RuntimeError(
                f"joint state is missing {', '.join(missing_joints)}; refusing to move"
            )

        trajectory_controller = self.get_parameter("trajectory_controller").value
        restore_controller = self.get_parameter("restore_controller").value
        restore_controllers = [restore_controller]
        if (
            self.get_parameter("restore_state_only_admittance").value
            and "admittance_controller" not in restore_controllers
        ):
            restore_controllers.append("admittance_controller")

        motion_controllers = ["admittance_controller", "twist_controller"]
        self.switch_controllers([trajectory_controller], motion_controllers)
        try:
            if not self.trajectory_client.wait_for_server(timeout_sec=timeout):
                raise RuntimeError("joint trajectory action server is unavailable")

            duration = max(0.1, float(self.get_parameter("trajectory_duration").value))
            hold_duration = max(
                0.1, float(self.get_parameter("handoff_hold_duration").value)
            )
            start_point = JointTrajectoryPoint()
            start_point.positions = [current_positions[name] for name in joint_names]
            start_point.velocities = [0.0] * len(joint_names)
            start_point.accelerations = [0.0] * len(joint_names)
            start_point.time_from_start.sec = int(hold_duration)
            start_point.time_from_start.nanosec = int(
                (hold_duration - int(hold_duration)) * 1e9
            )

            goal_point = JointTrajectoryPoint()
            goal_point.positions = []
            for joint_name, angle in zip(joint_names, angles):
                target = kinova_degrees_to_ros_radians(angle)
                if joint_name in continuous_joints:
                    target = nearest_equivalent_angle(
                        target, current_positions[joint_name]
                    )
                goal_point.positions.append(target)
            goal_point.velocities = [0.0] * len(joint_names)
            goal_point.accelerations = [0.0] * len(joint_names)
            total_duration = hold_duration + duration
            goal_point.time_from_start.sec = int(total_duration)
            goal_point.time_from_start.nanosec = int(
                (total_duration - int(total_duration)) * 1e9
            )

            goal = FollowJointTrajectory.Goal()
            goal.trajectory.joint_names = joint_names
            goal.trajectory.points = [start_point, goal_point]
            goal_tolerance = math.radians(
                max(0.01, float(self.get_parameter("goal_tolerance_degrees").value))
            )
            goal.goal_tolerance = [
                JointTolerance(name=name, position=goal_tolerance)
                for name in joint_names
            ]
            goal_time_tolerance = max(
                0.0, float(self.get_parameter("goal_time_tolerance").value)
            )
            goal.goal_time_tolerance.sec = int(goal_time_tolerance)
            goal.goal_time_tolerance.nanosec = int(
                (goal_time_tolerance - int(goal_time_tolerance)) * 1e9
            )
            goal_handle = self.wait_for_future(
                self.trajectory_client.send_goal_async(goal), timeout
            )
            if not goal_handle.accepted:
                raise RuntimeError("activation-pose trajectory was rejected")
            result = self.wait_for_future(
                goal_handle.get_result_async(), total_duration + timeout
            ).result
            if result.error_code != FollowJointTrajectory.Result.SUCCESSFUL:
                raise RuntimeError(
                    f"activation-pose trajectory failed: {result.error_string} "
                    f"(code {result.error_code})"
                )

            # Do not trust action completion alone: verify the latest measured
            # joint positions before handing command interfaces back.
            with self.joint_state_lock:
                final_positions = dict(self.current_positions)
            errors = {}
            for name, target in zip(joint_names, goal_point.positions):
                actual = final_positions.get(name)
                if actual is None:
                    errors[name] = float("inf")
                    continue
                if name in continuous_joints:
                    target = nearest_equivalent_angle(target, actual)
                errors[name] = abs(target - actual)
            outside_tolerance = {
                name: math.degrees(error)
                for name, error in errors.items()
                if error > goal_tolerance
            }
            if outside_tolerance:
                details = ", ".join(
                    f"{name}={error:.3f} deg"
                    for name, error in outside_tolerance.items()
                )
                raise RuntimeError(
                    f"activation pose measured error exceeds tolerance: {details}"
                )
            self.get_logger().info(
                "activation pose measured errors (deg): "
                + ", ".join(
                    f"{name}={math.degrees(error):.3f}"
                    for name, error in errors.items()
                )
            )
        finally:
            self.switch_controllers(restore_controllers, [trajectory_controller])

    def run_motion(self):
        if not self.motion_lock.acquire(blocking=False):
            return False, "activation-pose motion is already running"
        try:
            self.execute_activation_pose()
            return True, "robot reached the activation pose"
        except Exception as exc:  # Report failures through Trigger and launch logs.
            self.get_logger().error(f"activation pose failed: {exc}")
            return False, str(exc)
        finally:
            self.motion_lock.release()

    def handle_move_request(self, _request, response):
        response.success, response.message = self.run_motion()
        return response

    def handle_auto_move(self):
        if self.auto_timer is not None:
            self.auto_timer.cancel()
        success, message = self.run_motion()
        log = self.get_logger().info if success else self.get_logger().error
        log(f"automatic activation pose: {message}")


def main():
    rclpy.init()
    node = ActivationPoseService()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
