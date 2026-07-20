#!/usr/bin/env python3

"""Interactively check an estimated wrench using a known hanging mass."""

import argparse
import math
import statistics
import sys
import time

import rclpy
from geometry_msgs.msg import WrenchStamped
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.utilities import remove_ros_args


class ForceSampler(Node):
    def __init__(self, topic):
        super().__init__("check_estimated_force")
        self.samples = []
        self.subscription = self.create_subscription(
            WrenchStamped, topic, self._wrench_callback, qos_profile_sensor_data
        )

    def _wrench_callback(self, message):
        force = message.wrench.force
        self.samples.append((force.x, force.y, force.z))

    def sample_for(self, duration):
        self.samples.clear()
        deadline = time.monotonic() + duration
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=min(0.1, max(0.0, deadline - time.monotonic())))
        if not self.samples:
            raise RuntimeError("no wrench messages were received")

        mean = tuple(statistics.fmean(values) for values in zip(*self.samples))
        deviation = tuple(
            statistics.pstdev(values) if len(self.samples) > 1 else 0.0
            for values in zip(*self.samples)
        )
        return mean, deviation, len(self.samples)


def vector_norm(vector):
    return math.sqrt(sum(value * value for value in vector))


def format_vector(vector):
    return "[{: .3f}, {: .3f}, {: .3f}] N".format(*vector)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Compare estimated force change against the weight of a known mass."
    )
    parser.add_argument("mass_kg", type=float, help="applied mass in kilograms")
    parser.add_argument("--topic", default="/estimated_wrench", help="WrenchStamped topic")
    parser.add_argument(
        "--sample-seconds", type=float, default=3.0, help="length of each averaging window"
    )
    parser.add_argument("--gravity", type=float, default=9.80665, help="gravity in m/s^2")
    parser.add_argument(
        "--tolerance-percent",
        type=float,
        default=15.0,
        help="maximum relative error for PASS",
    )
    arguments = parser.parse_args(remove_ros_args(args=sys.argv)[1:])
    if arguments.mass_kg <= 0.0:
        parser.error("mass_kg must be greater than zero")
    if arguments.sample_seconds <= 0.0:
        parser.error("--sample-seconds must be greater than zero")
    if arguments.gravity <= 0.0:
        parser.error("--gravity must be greater than zero")
    if arguments.tolerance_percent < 0.0:
        parser.error("--tolerance-percent cannot be negative")
    return arguments


def main():
    arguments = parse_arguments()
    rclpy.init()
    node = ForceSampler(arguments.topic)

    try:
        print(f"Listening on {arguments.topic}")
        print("Keep the tool unloaded and still.")
        input("Press Enter to sample the idle force... ")
        idle, idle_stddev, idle_count = node.sample_for(arguments.sample_seconds)
        print(
            f"Idle ({idle_count} samples): {format_vector(idle)} "
            f"(component std dev {format_vector(idle_stddev)})"
        )

        input(
            f"Apply the {arguments.mass_kg:g} kg mass, let it settle, "
            "then press Enter to remeasure... "
        )
        loaded, loaded_stddev, loaded_count = node.sample_for(arguments.sample_seconds)

        delta = tuple(loaded[index] - idle[index] for index in range(3))
        measured = vector_norm(delta)
        expected = arguments.mass_kg * arguments.gravity
        error = measured - expected
        error_percent = 100.0 * abs(error) / expected
        passed = error_percent <= arguments.tolerance_percent

        print(f"Loaded ({loaded_count} samples): {format_vector(loaded)}")
        print(f"Loaded component std dev:       {format_vector(loaded_stddev)}")
        print(f"Force change (loaded - idle):   {format_vector(delta)}")
        print(f"Measured force change:          {measured:.3f} N")
        print(f"Expected weight (m * g):        {expected:.3f} N")
        print(f"Signed error:                   {error:+.3f} N")
        print(f"Absolute relative error:        {error_percent:.2f}%")
        print(
            f"Result: {'PASS' if passed else 'FAIL'} "
            f"(tolerance {arguments.tolerance_percent:g}%)"
        )
        return 0 if passed else 1
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.", file=sys.stderr)
        return 130
    except RuntimeError as error:
        print(f"Error: {error} on {arguments.topic}.", file=sys.stderr)
        return 2
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(main())
