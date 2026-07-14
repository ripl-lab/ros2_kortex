#!/usr/bin/env python3

"""Verify that a MuJoCo force-duration test settles after its load is released."""

import argparse
import sys
import time

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState


class ForceStopVerifier(Node):
    def __init__(self, args):
        super().__init__("verify_mujoco_force_stop")
        self.args = args
        self.samples = []
        self.start_sim_time = None
        self.latest_sim_time = None
        self.joint_names = []
        self.create_subscription(JointState, "/joint_states", self._on_joint_state, 10)

    def _on_joint_state(self, message):
        stamp = message.header.stamp
        sim_time = stamp.sec + stamp.nanosec * 1e-9
        if self.start_sim_time is None:
            self.start_sim_time = sim_time
        self.latest_sim_time = sim_time
        observation_start = (
            self.start_sim_time + self.args.start_delay
            + self.args.duration + self.args.settle_time
        )
        if sim_time >= observation_start and message.velocity and message.position:
            self.joint_names = list(message.name)
            self.samples.append((sim_time, list(message.velocity), list(message.position)))

    def result(self):
        if not self.samples:
            return None
        elapsed = self.samples[-1][0] - self.samples[0][0]
        if elapsed < self.args.observation_time:
            return None

        max_velocity = max(abs(value) for _, velocities, _ in self.samples for value in velocities)
        per_joint_velocity = [
            max(abs(sample[1][joint]) for sample in self.samples)
            for joint in range(min(len(sample[1]) for sample in self.samples))
        ]
        joint_count = min(len(sample[2]) for sample in self.samples)
        max_position_range = max(
            max(sample[2][joint] for sample in self.samples)
            - min(sample[2][joint] for sample in self.samples)
            for joint in range(joint_count)
        )
        passed = (
            max_velocity <= self.args.velocity_tolerance
            and max_position_range <= self.args.position_tolerance
        )
        return passed, max_velocity, max_position_range, per_joint_velocity


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=float, required=True)
    parser.add_argument("--start-delay", type=float, default=1.0)
    parser.add_argument("--settle-time", type=float, default=5.0)
    parser.add_argument("--observation-time", type=float, default=1.0)
    parser.add_argument("--velocity-tolerance", type=float, default=0.01)
    parser.add_argument("--position-tolerance", type=float, default=0.002)
    parser.add_argument("--wall-timeout", type=float, default=30.0)
    return parser.parse_args(argv)


def main():
    args = parse_args(sys.argv[1:])
    rclpy.init()
    node = ForceStopVerifier(args)
    deadline = time.monotonic() + args.wall_timeout
    result = None
    while rclpy.ok() and time.monotonic() < deadline and result is None:
        rclpy.spin_once(node, timeout_sec=0.1)
        result = node.result()

    node.destroy_node()
    rclpy.shutdown()
    if result is None:
        print("FAIL: timed out before receiving a complete post-force observation window")
        return 2
    passed, max_velocity, max_position_range, per_joint_velocity = result
    print(
        f"max post-settle joint velocity={max_velocity:.6f} rad/s, "
        f"max position range={max_position_range:.6f} rad"
    )
    print(
        "per-joint max velocity: "
        + ", ".join(
            f"{name}={velocity:.6f}"
            for name, velocity in zip(node.joint_names, per_joint_velocity)
        )
    )
    if not passed:
        print("FAIL: robot did not remain stationary within the requested tolerances")
        return 1
    print("PASS: robot stopped moving after the applied force ended")
    return 0


if __name__ == "__main__":
    sys.exit(main())
