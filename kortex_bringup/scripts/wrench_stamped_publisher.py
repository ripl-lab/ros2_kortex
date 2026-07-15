#!/usr/bin/env python3

import rclpy
from control_msgs.msg import AdmittanceControllerState
from geometry_msgs.msg import Vector3, Wrench, WrenchStamped
from rclpy.node import Node


class WrenchStampedPublisher(Node):
    def __init__(self):
        super().__init__("wrench_stamped_publisher")
        self.declare_parameter("input_topic", "/admittance_controller/status")
        self.declare_parameter("wrench_topic", "/estimated_wrench")
        self.declare_parameter("frame_id", "base_link")
        self.declare_parameter("publish_rate", 30.0)
        self.declare_parameter("hold_time", 2.0)

        input_topic = self.get_parameter("input_topic").value
        wrench_topic = self.get_parameter("wrench_topic").value
        self.frame_id = self.get_parameter("frame_id").value
        publish_rate = float(self.get_parameter("publish_rate").value)
        self.hold_time = float(self.get_parameter("hold_time").value)

        self.wrench = WrenchStamped().wrench
        self.last_msg_time = self.get_clock().now()

        self.publisher = self.create_publisher(WrenchStamped, wrench_topic, 10)
        self.subscription = self.create_subscription(
            AdmittanceControllerState, input_topic, self.wrench_callback, 10
        )
        self.timer = self.create_timer(
            1.0 / max(publish_rate, 1.0), self.publish_wrench
        )

    def wrench_callback(self, msg):
        self.last_msg_time = self.get_clock().now()
        rotation = msg.ref_trans_base_ft.transform.rotation
        norm = (
            rotation.x * rotation.x
            + rotation.y * rotation.y
            + rotation.z * rotation.z
            + rotation.w * rotation.w
        ) ** 0.5
        if norm < 1e-9:
            self.get_logger().warn("Tool-frame rotation is invalid; skipping wrench sample.")
            return

        x = rotation.x / norm
        y = rotation.y / norm
        z = rotation.z / norm
        w = rotation.w / norm
        # ref_trans_base_ft contains the tool orientation in base_link. Rotate
        # base-frame vectors by its transpose so RViz can draw the same world
        # direction with the arrow anchored at the tool frame.
        rotation_base_tool = (
            (1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - z * w), 2.0 * (x * z + y * w)),
            (2.0 * (x * y + z * w), 1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z - x * w)),
            (2.0 * (x * z - y * w), 2.0 * (y * z + x * w), 1.0 - 2.0 * (x * x + y * y)),
        )

        def base_to_tool(vector):
            values = (vector.x, vector.y, vector.z)
            return Vector3(
                x=sum(rotation_base_tool[row][0] * values[row] for row in range(3)),
                y=sum(rotation_base_tool[row][1] * values[row] for row in range(3)),
                z=sum(rotation_base_tool[row][2] * values[row] for row in range(3)),
            )

        self.wrench = Wrench(
            force=base_to_tool(msg.wrench_base.wrench.force),
            torque=base_to_tool(msg.wrench_base.wrench.torque),
        )
        self.frame_id = (
            msg.ref_trans_base_ft.child_frame_id
            or msg.ft_sensor_frame.data
            or "end_effector_link"
        )

    def publish_wrench(self):
        age = (self.get_clock().now() - self.last_msg_time).nanoseconds * 1e-9
        wrench = self.wrench
        if age > self.hold_time:
            wrench = WrenchStamped().wrench

        msg = WrenchStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id
        msg.wrench = wrench
        self.publisher.publish(msg)


def main():
    rclpy.init()
    node = WrenchStampedPublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
