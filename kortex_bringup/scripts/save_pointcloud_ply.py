#!/usr/bin/env python3

"""Save the latest ROS PointCloud2 message as a binary little-endian PLY."""

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from rclpy.utilities import remove_ros_args
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2
from std_srvs.srv import Trigger


POINTCLOUD_QOS = QoSProfile(
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
    reliability=ReliabilityPolicy.BEST_EFFORT,
    durability=DurabilityPolicy.VOLATILE,
)


class PlySaver(Node):
    def __init__(self, topic: str, output_path: Path):
        super().__init__("prediction_pointcloud_ply_saver")
        self.output_path = output_path
        self.latest_points = None
        self.latest_frame = ""
        self.subscription = self.create_subscription(
            PointCloud2, topic, self.pointcloud_callback, POINTCLOUD_QOS
        )
        self.save_service = self.create_service(
            Trigger, "/save_prediction_ply", self.save_callback
        )
        self.get_logger().info(
            f"waiting for {topic}; output={self.output_path}"
        )

    def pointcloud_callback(self, msg: PointCloud2):
        points = point_cloud2.read_points_numpy(
            msg, field_names=("x", "y", "z"), skip_nans=True
        )
        self.latest_points = np.ascontiguousarray(points, dtype="<f4").reshape(-1, 3)
        self.latest_frame = msg.header.frame_id

    def save_callback(self, request, response):
        del request
        try:
            count = self.save()
            response.success = True
            response.message = f"saved {count} points to {self.output_path}"
        except RuntimeError as error:
            response.success = False
            response.message = str(error)
        return response

    def save(self) -> int:
        if self.latest_points is None:
            raise RuntimeError("no point cloud has been received")

        points = self.latest_points.copy()
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.output_path.with_suffix(self.output_path.suffix + ".tmp")
        header = (
            "ply\n"
            "format binary_little_endian 1.0\n"
            f"comment ROS frame_id {self.latest_frame}\n"
            f"element vertex {len(points)}\n"
            "property float x\n"
            "property float y\n"
            "property float z\n"
            "end_header\n"
        ).encode("ascii")
        with temporary_path.open("wb") as ply_file:
            ply_file.write(header)
            ply_file.write(points.tobytes(order="C"))
        os.replace(temporary_path, self.output_path)
        self.get_logger().info(f"saved {len(points)} points to {self.output_path}")
        return len(points)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Save the latest /prediction_pointcloud message as a PLY file."
    )
    parser.add_argument(
        "output",
        nargs="?",
        default="reconstruction.ply",
        help="Output PLY path (default: reconstruction.ply).",
    )
    parser.add_argument(
        "--topic",
        default="/prediction_pointcloud",
        help="PointCloud2 topic (default: /prediction_pointcloud).",
    )
    return parser.parse_args(remove_ros_args(args=sys.argv)[1:])


def main():
    arguments = parse_arguments()
    rclpy.init(args=sys.argv)
    node = PlySaver(arguments.topic, Path(arguments.output).expanduser().resolve())
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        if node.latest_points is not None:
            node.save()
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
