#!/usr/bin/env python3

"""Estimate a rigid payload CoM from static joint-effort measurements."""

import argparse
import math
import re
import statistics
import sys
import time
import xml.etree.ElementTree as ET

import numpy as np
import pinocchio as pin
import rclpy
from geometry_msgs.msg import Point
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from rclpy.utilities import remove_ros_args
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from visualization_msgs.msg import Marker, MarkerArray


def payload_model_xml(robot_xml, link_name, mass, cog=None):
    root = ET.fromstring(robot_xml)
    link = next((item for item in root.findall("link") if item.get("name") == link_name), None)
    if link is None:
        raise RuntimeError(f"payload link {link_name!r} is absent from robot_description")
    old_inertial = link.find("inertial")
    if old_inertial is not None:
        link.remove(old_inertial)
    if cog is not None:
        inertial = ET.SubElement(link, "inertial")
        ET.SubElement(inertial, "origin", xyz=" ".join(str(value) for value in cog), rpy="0 0 0")
        ET.SubElement(inertial, "mass", value=str(mass))
        # Inertia does not affect static gravity, but a positive matrix keeps URDF parsers happy.
        epsilon = max(mass * 1e-9, 1e-12)
        ET.SubElement(
            inertial,
            "inertia",
            ixx=str(epsilon),
            ixy="0",
            ixz="0",
            iyy=str(epsilon),
            iyz="0",
            izz=str(epsilon),
        )
    return ET.tostring(root, encoding="unicode")


class StaticSampler(Node):
    def __init__(self, joint_topic, description_topic, preview_topic):
        super().__init__("estimate_payload_com")
        self.latest_joint_state = None
        self.robot_description = None
        self.samples = []
        self.collecting = False
        self.create_subscription(JointState, joint_topic, self._on_joint_state, 50)
        description_qos = QoSProfile(depth=1)
        description_qos.reliability = ReliabilityPolicy.RELIABLE
        description_qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
        self.create_subscription(String, description_topic, self._on_description, description_qos)
        preview_qos = QoSProfile(depth=1)
        preview_qos.reliability = ReliabilityPolicy.RELIABLE
        preview_qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
        self.preview_publisher = self.create_publisher(MarkerArray, preview_topic, preview_qos)

    def _on_description(self, message):
        self.robot_description = message.data

    def _on_joint_state(self, message):
        self.latest_joint_state = message
        if self.collecting:
            self.samples.append(message)

    def wait_for_inputs(self, timeout):
        deadline = time.monotonic() + timeout
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
            if self.robot_description and self.latest_joint_state is not None:
                return
        missing = []
        if not self.robot_description:
            missing.append("robot_description")
        if self.latest_joint_state is None:
            missing.append("joint states")
        raise RuntimeError("timed out waiting for " + " and ".join(missing))

    def sample(self, seconds):
        self.samples = []
        self.collecting = True
        deadline = time.monotonic() + seconds
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=min(0.05, deadline - time.monotonic()))
        self.collecting = False
        if not self.samples:
            raise RuntimeError("no joint-state samples received")
        return self.samples

    def publish_pose_preview(self, fixed_frame, origin, rotations):
        message = MarkerArray()
        delete_all = Marker()
        delete_all.action = Marker.DELETEALL
        message.markers.append(delete_all)
        stamp = self.get_clock().now().to_msg()
        for index, rotation in enumerate(rotations):
            direction = rotation[:, 2]
            phase = index / max(1, len(rotations) - 1)
            color = (0.15 + 0.75 * phase, 0.85 - 0.60 * phase, 1.0 - 0.65 * phase)
            arrow = Marker()
            arrow.header.frame_id = fixed_frame
            arrow.header.stamp = stamp
            arrow.ns = "payload_com_pose_axes"
            arrow.id = index
            arrow.type = Marker.ARROW
            arrow.action = Marker.ADD
            arrow.points = [
                Point(x=float(origin[0]), y=float(origin[1]), z=float(origin[2])),
                Point(
                    x=float(origin[0] + 0.20 * direction[0]),
                    y=float(origin[1] + 0.20 * direction[1]),
                    z=float(origin[2] + 0.20 * direction[2]),
                ),
            ]
            arrow.scale.x = 0.008
            arrow.scale.y = 0.018
            arrow.scale.z = 0.025
            arrow.color.r, arrow.color.g, arrow.color.b = color
            arrow.color.a = 0.85
            message.markers.append(arrow)

            label = Marker()
            label.header.frame_id = fixed_frame
            label.header.stamp = stamp
            label.ns = "payload_com_pose_labels"
            label.id = index
            label.type = Marker.TEXT_VIEW_FACING
            label.action = Marker.ADD
            label.pose.position.x = float(origin[0] + 0.23 * direction[0])
            label.pose.position.y = float(origin[1] + 0.23 * direction[1])
            label.pose.position.z = float(origin[2] + 0.23 * direction[2])
            label.pose.orientation.w = 1.0
            label.scale.z = 0.035
            label.color.r = label.color.g = label.color.b = 1.0
            label.color.a = 1.0
            label.text = str(index + 1)
            message.markers.append(label)
        self.preview_publisher.publish(message)


def model_configuration(model, joint_positions):
    q = pin.neutral(model)
    for name, position in joint_positions.items():
        if not model.existJointName(name):
            continue
        joint = model.joints[model.getJointId(name)]
        if joint.nv != 1:
            continue
        if joint.nq == 1:
            q[joint.idx_q] = position
        elif joint.nq == 2:  # Pinocchio representation for an unbounded revolute joint.
            q[joint.idx_q] = math.cos(position)
            q[joint.idx_q + 1] = math.sin(position)
    return q


def gravity_for_joints(model, data, q, joint_names):
    gravity = pin.computeGeneralizedGravity(model, data, q)
    return np.asarray([gravity[model.joints[model.getJointId(name)].idx_v] for name in joint_names])


def averaged_pose(messages, joint_names, effort_sign):
    positions = {name: [] for name in joint_names}
    efforts = {name: [] for name in joint_names}
    velocities = {name: [] for name in joint_names}
    for message in messages:
        index = {name: offset for offset, name in enumerate(message.name)}
        if any(name not in index for name in joint_names):
            continue
        for name in joint_names:
            offset = index[name]
            if offset >= len(message.position) or offset >= len(message.effort):
                break
            positions[name].append(message.position[offset])
            efforts[name].append(effort_sign * message.effort[offset])
            if offset < len(message.velocity):
                velocities[name].append(message.velocity[offset])
    if any(not values for values in positions.values()) or any(not values for values in efforts.values()):
        raise RuntimeError("joint_states does not contain position and effort for every arm joint")
    mean_position = {name: statistics.fmean(values) for name, values in positions.items()}
    mean_effort = np.asarray([statistics.fmean(efforts[name]) for name in joint_names])
    max_velocity = max((abs(value) for values in velocities.values() for value in values), default=0.0)
    effort_stddev = max(
        statistics.pstdev(efforts[name]) if len(efforts[name]) > 1 else 0.0 for name in joint_names
    )
    return mean_position, mean_effort, max_velocity, effort_stddev


def robust_fit(matrix, target, iterations=8):
    weights = np.ones(target.size)
    estimate = np.zeros(matrix.shape[1])
    for _ in range(iterations):
        weighted_matrix = matrix * np.sqrt(weights)[:, None]
        weighted_target = target * np.sqrt(weights)
        estimate = np.linalg.lstsq(weighted_matrix, weighted_target, rcond=None)[0]
        residual = target - matrix @ estimate
        scale = 1.4826 * np.median(np.abs(residual - np.median(residual)))
        if scale < 1e-9:
            break
        threshold = 1.345 * scale
        weights = np.minimum(1.0, threshold / np.maximum(np.abs(residual), 1e-12))
    return estimate, target - matrix @ estimate


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Estimate payload CoM and constant joint-torque offsets from static poses."
    )
    parser.add_argument("--mass", type=float, default=0.536, help="payload mass in kg")
    parser.add_argument("--poses", type=int, default=15, help="number of static poses")
    parser.add_argument("--sample-seconds", type=float, default=3.0)
    parser.add_argument("--payload-link", default="clarius_base_link")
    parser.add_argument("--joint-topic", default="/joint_states")
    parser.add_argument("--description-topic", default="/robot_description")
    parser.add_argument("--preview-topic", default="/payload_com_calibration/poses")
    parser.add_argument("--fixed-frame", default="base_link")
    parser.add_argument(
        "--preview-only",
        action="store_true",
        help="publish the suggested orientations and wait without collecting measurements",
    )
    parser.add_argument("--effort-sign", type=float, default=-1.0)
    parser.add_argument("--max-velocity", type=float, default=0.02, help="rad/s rejection threshold")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument(
        "--joints",
        help="comma-separated arm joint names; by default discovers names ending in joint_1..joint_7",
    )
    arguments = parser.parse_args(remove_ros_args(args=sys.argv)[1:])
    if arguments.mass <= 0 or arguments.poses < 4 or arguments.sample_seconds <= 0:
        parser.error("mass and sample-seconds must be positive, and at least four poses are required")
    return arguments


def main():
    arguments = parse_arguments()
    rclpy.init()
    node = StaticSampler(arguments.joint_topic, arguments.description_topic, arguments.preview_topic)
    try:
        print("Waiting for robot_description and joint states...")
        node.wait_for_inputs(arguments.timeout)
        if arguments.joints:
            joint_names = [name.strip() for name in arguments.joints.split(",") if name.strip()]
        else:
            available = set(node.latest_joint_state.name)
            joint_names = sorted(
                (name for name in available if re.search(r"joint_[1-7]$", name)),
                key=lambda name: int(re.search(r"([1-7])$", name).group(1)),
            )
        if len(joint_names) != 7:
            raise RuntimeError(
                f"expected seven arm joints, discovered {joint_names}; specify them with --joints"
            )

        base_model = pin.buildModelFromXML(
            payload_model_xml(node.robot_description, arguments.payload_link, arguments.mass)
        )
        center_model = pin.buildModelFromXML(
            payload_model_xml(node.robot_description, arguments.payload_link, arguments.mass, (0, 0, 0))
        )
        axis_models = [
            pin.buildModelFromXML(
                payload_model_xml(
                    node.robot_description,
                    arguments.payload_link,
                    arguments.mass,
                    tuple(1.0 if row == column else 0.0 for row in range(3)),
                )
            )
            for column in range(3)
        ]
        models = [base_model, center_model] + axis_models
        data = [pin.Data(model) for model in models]

        preview_positions = {
            name: node.latest_joint_state.position[node.latest_joint_state.name.index(name)]
            for name in joint_names
        }
        preview_q = model_configuration(base_model, preview_positions)
        pin.forwardKinematics(base_model, data[0], preview_q)
        pin.updateFramePlacements(base_model, data[0])
        if not base_model.existFrame(arguments.fixed_frame):
            raise RuntimeError(f"fixed frame {arguments.fixed_frame!r} is absent from robot_description")
        if not base_model.existFrame(arguments.payload_link):
            raise RuntimeError(f"payload frame {arguments.payload_link!r} is absent from robot_description")
        base_placement = data[0].oMf[base_model.getFrameId(arguments.fixed_frame)]
        payload_placement = data[0].oMf[base_model.getFrameId(arguments.payload_link)]
        base_to_payload = base_placement.inverse() * payload_placement
        current_rpy = pin.rpy.matrixToRpy(base_to_payload.rotation)
        preview_rotations = [
            pin.rpy.rpyToMatrix(math.radians(roll), math.radians(pitch), current_rpy[2])
            for roll in (-60.0, 0.0, 60.0)
            for pitch in (-60.0, -30.0, 0.0, 30.0, 60.0)
        ]
        node.publish_pose_preview(
            arguments.fixed_frame, np.asarray(base_to_payload.translation), preview_rotations
        )
        print(
            f"Published {len(preview_rotations)} numbered orientation arrows on "
            f"{arguments.preview_topic}. Each arrow shows the target +Z axis of "
            f"{arguments.payload_link}."
        )
        if arguments.preview_only:
            print("Preview-only mode; press Ctrl+C to exit.")
            while rclpy.ok():
                rclpy.spin_once(node, timeout_sec=0.5)
            return 0
        input("Inspect all targets in RViz, then press Enter to begin calibration... ")

        print(f"Arm joints: {', '.join(joint_names)}")
        print("Admittance response must be disabled. Move through diverse orientations slowly.")
        regressors = []
        targets = []
        accepted = 0
        while accepted < arguments.poses:
            input(f"Pose {accepted + 1}/{arguments.poses}: hold still, then press Enter to sample... ")
            messages = node.sample(arguments.sample_seconds)
            position, measured, max_velocity, effort_stddev = averaged_pose(
                messages, joint_names, arguments.effort_sign
            )
            if max_velocity > arguments.max_velocity:
                print(f"  Rejected: maximum velocity {max_velocity:.4f} rad/s")
                continue
            gravities = [
                gravity_for_joints(model, datum, model_configuration(model, position), joint_names)
                for model, datum in zip(models, data)
            ]
            payload_at_origin = gravities[1] - gravities[0]
            cog_columns = np.column_stack([value - gravities[1] for value in gravities[2:]])
            # A constant offset per joint absorbs sensor zero error without disguising pose-varying gravity.
            bias_columns = np.eye(len(joint_names))
            regressors.append(np.hstack((cog_columns, bias_columns)))
            targets.append(measured - gravities[0] - payload_at_origin)
            accepted += 1
            print(
                f"  Accepted {len(messages)} samples; max velocity {max_velocity:.4f} rad/s, "
                f"max effort stddev {effort_stddev:.3f} Nm"
            )

        matrix = np.vstack(regressors)
        target = np.concatenate(targets)
        if np.linalg.matrix_rank(matrix[:, :3]) < 3:
            raise RuntimeError("poses do not excite all three CoM axes; use more diverse orientations")
        estimate, residual = robust_fit(matrix, target)
        cog = estimate[:3]
        biases = estimate[3:]
        rms = math.sqrt(float(np.mean(residual**2)))
        print("\nEstimated payload parameters")
        print(f"  mass: {arguments.mass:.6f} kg")
        print(f"  CoM in {arguments.payload_link}: {cog[0]:.6f} {cog[1]:.6f} {cog[2]:.6f} m")
        print(f"  equivalent weight: {arguments.mass * 9.80665:.6f} N")
        print(f"  fitted constant joint offsets ({arguments.effort_sign:+g} effort convention):")
        for name, bias in zip(joint_names, biases):
            print(f"    {name}: {bias:+.6f} Nm")
        print(f"  torque residual RMS: {rms:.6f} Nm")
        print("\nURDF inertial values:")
        print(f'  <origin xyz="{cog[0]:.6f} {cog[1]:.6f} {cog[2]:.6f}" rpy="0 0 0"/>')
        print(f'  <mass value="{arguments.mass:.6f}"/>')
        print("Rebuild and restart after updating the payload link. Because this mass is then part of")
        print("the Pinocchio model, leave the additional payload_weight launch argument at 0.0.")
        return 0
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.", file=sys.stderr)
        return 130
    except (RuntimeError, ValueError, ET.ParseError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(main())
