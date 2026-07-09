#!/usr/bin/env python3

import argparse
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray


def main():
    parser = argparse.ArgumentParser(description="Inject a wrench into Gen3 fake hardware.")
    parser.add_argument("--force", nargs=3, type=float, default=[0.0, 0.0, 0.0])
    parser.add_argument("--torque", nargs=3, type=float, default=[0.0, 0.0, 0.0])
    parser.add_argument("--duration", type=float, default=2.0)
    parser.add_argument("--topic", default="/wrench_injector/commands")
    args = parser.parse_args()

    rclpy.init()
    node = Node("inject_wrench")
    publisher = node.create_publisher(Float64MultiArray, args.topic, 10)
    message = Float64MultiArray(data=args.force + args.torque)
    deadline = time.monotonic() + max(args.duration, 0.1)
    while rclpy.ok() and time.monotonic() < deadline:
        publisher.publish(message)
        rclpy.spin_once(node, timeout_sec=0.02)
        time.sleep(0.03)

    publisher.publish(Float64MultiArray(data=[0.0] * 6))
    rclpy.spin_once(node, timeout_sec=0.1)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()

