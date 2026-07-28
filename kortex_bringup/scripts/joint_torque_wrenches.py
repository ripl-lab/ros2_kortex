#!/usr/bin/env python3
import math

import rclpy
from geometry_msgs.msg import TransformStamped, WrenchStamped
from rclpy.node import Node
from sensor_msgs.msg import JointState
from tf2_ros.static_transform_broadcaster import StaticTransformBroadcaster


class JointTorqueWrenches(Node):
    """Publish each measured MuJoCo joint torque as a native ROS wrench."""

    def __init__(self):
        super().__init__("joint_torque_wrenches")
        self.declare_parameter("prefix", "")
        self.declare_parameter("surface_offset", 0.0)
        self.declare_parameter("filter_cutoff_hz", 5.0)
        self.prefix = self.get_parameter("prefix").value
        self.offset = float(self.get_parameter("surface_offset").value)
        self.cutoff = float(self.get_parameter("filter_cutoff_hz").value)
        self.filtered_efforts = {}
        self.last_stamp = None
        self.frames = [
            "shoulder_link", "half_arm_1_link", "half_arm_2_link", "forearm_link",
            "spherical_wrist_1_link", "spherical_wrist_2_link", "bracelet_link",
        ]
        self.wrench_publishers = [
            self.create_publisher(WrenchStamped, f"joint_torque_wrenches/joint_{i}", 10)
            for i in range(1, 8)
        ]
        self.tf_broadcaster = StaticTransformBroadcaster(self)
        self.publish_offset_frames()
        self.create_subscription(JointState, "joint_states", self.on_joint_state, 10)

    def publish_offset_frames(self):
        transforms = []
        stamp = self.get_clock().now().to_msg()
        for index, parent in enumerate(self.frames, start=1):
            transform = TransformStamped()
            transform.header.stamp = stamp
            transform.header.frame_id = f"{self.prefix}{parent}"
            transform.child_frame_id = f"{self.prefix}joint_{index}_torque_wrench"
            transform.transform.translation.x = self.offset
            transform.transform.rotation.w = 1.0
            transforms.append(transform)
        self.tf_broadcaster.sendTransform(transforms)

    def on_joint_state(self, msg):
        efforts = dict(zip(msg.name, msg.effort))
        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        dt = 0.0 if self.last_stamp is None else max(0.0, stamp - self.last_stamp)
        self.last_stamp = stamp
        alpha = 1.0 if dt <= 0.0 or self.cutoff <= 0.0 else 1.0 - math.exp(
            -2.0 * math.pi * self.cutoff * dt
        )
        for index, publisher in enumerate(self.wrench_publishers, start=1):
            torque = efforts.get(f"{self.prefix}joint_{index}")
            if torque is None or not math.isfinite(torque):
                continue
            previous = self.filtered_efforts.get(index, torque)
            torque = previous + alpha * (torque - previous)
            self.filtered_efforts[index] = torque
            wrench = WrenchStamped()
            wrench.header.stamp = msg.header.stamp
            wrench.header.frame_id = f"{self.prefix}joint_{index}_torque_wrench"
            # Every Gen3 revolute joint axis is local +Z. RViz's Wrench display
            # renders this torque with its native torque glyph and scaling.
            wrench.wrench.torque.z = torque
            publisher.publish(wrench)


def main():
    rclpy.init()
    node = JointTorqueWrenches()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
