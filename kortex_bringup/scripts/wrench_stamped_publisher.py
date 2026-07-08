#!/usr/bin/env python3

import rclpy
from geometry_msgs.msg import WrenchStamped
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray


class WrenchStampedPublisher(Node):
    def __init__(self):
        super().__init__("wrench_stamped_publisher")
        self.declare_parameter("input_topic", "/wrench_injector/commands")
        self.declare_parameter("wrench_topic", "/applied_wrench")
        self.declare_parameter("frame_id", "tool_frame")
        self.declare_parameter("publish_rate", 30.0)
        self.declare_parameter("hold_time", 2.0)

        input_topic = self.get_parameter("input_topic").value
        wrench_topic = self.get_parameter("wrench_topic").value
        self.frame_id = self.get_parameter("frame_id").value
        publish_rate = float(self.get_parameter("publish_rate").value)
        self.hold_time = float(self.get_parameter("hold_time").value)

        self.force = [0.0, 0.0, 0.0]
        self.torque = [0.0, 0.0, 0.0]
        self.last_msg_time = self.get_clock().now()

        self.publisher = self.create_publisher(WrenchStamped, wrench_topic, 10)
        self.subscription = self.create_subscription(
            Float64MultiArray, input_topic, self.wrench_callback, 10
        )
        self.timer = self.create_timer(
            1.0 / max(publish_rate, 1.0), self.publish_wrench
        )

    def wrench_callback(self, msg):
        if len(msg.data) != 6:
            self.get_logger().warn("Expected [Fx, Fy, Fz, Tx, Ty, Tz].")
            return
        self.last_msg_time = self.get_clock().now()
        self.force = list(msg.data[:3])
        self.torque = list(msg.data[3:])

    def publish_wrench(self):
        age = (self.get_clock().now() - self.last_msg_time).nanoseconds * 1e-9
        force = self.force
        torque = self.torque
        if age > self.hold_time:
            force = [0.0, 0.0, 0.0]
            torque = [0.0, 0.0, 0.0]

        msg = WrenchStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "end_effector_link"
        msg.wrench.force.x = force[0]
        msg.wrench.force.y = force[1]
        msg.wrench.force.z = force[2]
        msg.wrench.torque.x = torque[0]
        msg.wrench.torque.y = torque[1]
        msg.wrench.torque.z = torque[2]
        self.publisher.publish(msg)


def main():
    rclpy.init()
    node = WrenchStampedPublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
