#!/usr/bin/env python3

"""Generate a box CAD mesh and a noisy partial surface cloud with known errors."""

import argparse
import struct
from pathlib import Path

import numpy as np


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path, default=Path("."), help="Output directory."
    )
    parser.add_argument("--points", type=int, default=20_000, help="Number of cloud points.")
    parser.add_argument(
        "--noise-sigma",
        type=float,
        default=0.2,
        help="Gaussian surface noise standard deviation in model units.",
    )
    parser.add_argument(
        "--offset",
        type=float,
        default=0.0,
        help="Systematic offset normal to the sampled surface.",
    )
    parser.add_argument(
        "--rotation-deg",
        type=float,
        nargs=3,
        default=(10.0, -8.0, 12.0),
        metavar=("RX", "RY", "RZ"),
        help=(
            "XYZ Euler rotation applied to the cloud in degrees "
            "(default: 10 -8 12)."
        ),
    )
    parser.add_argument(
        "--translation",
        type=float,
        nargs=3,
        default=(8.0, -5.0, 4.0),
        metavar=("TX", "TY", "TZ"),
        help="Translation applied after rotation (default: 8 -5 4).",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    return parser.parse_args()


def write_binary_stl(path, vertices, triangles):
    """Write a triangle mesh as binary STL without requiring a geometry library."""
    with path.open("wb") as output:
        output.write(b"Synthetic CAD box".ljust(80, b"\0"))
        output.write(struct.pack("<I", len(triangles)))
        for triangle in triangles:
            corners = vertices[triangle]
            normal = np.cross(corners[1] - corners[0], corners[2] - corners[0])
            length = np.linalg.norm(normal)
            if length:
                normal /= length
            output.write(struct.pack("<12fH", *normal, *corners.reshape(-1), 0))


def write_binary_ply(path, points):
    """Write XYZ points as a binary little-endian PLY."""
    header = (
        "ply\n"
        "format binary_little_endian 1.0\n"
        "comment synthetic partial scan of the CAD top surface\n"
        f"element vertex {len(points)}\n"
        "property float x\n"
        "property float y\n"
        "property float z\n"
        "end_header\n"
    ).encode("ascii")
    with path.open("wb") as output:
        output.write(header)
        output.write(np.asarray(points, dtype="<f4").tobytes(order="C"))


def rigid_transform(rotation_degrees, translation):
    """Return a homogeneous transform using Rz @ Ry @ Rx Euler composition."""
    rx, ry, rz = np.deg2rad(rotation_degrees)
    rotation_x = np.asarray(
        ((1, 0, 0), (0, np.cos(rx), -np.sin(rx)), (0, np.sin(rx), np.cos(rx)))
    )
    rotation_y = np.asarray(
        ((np.cos(ry), 0, np.sin(ry)), (0, 1, 0), (-np.sin(ry), 0, np.cos(ry)))
    )
    rotation_z = np.asarray(
        ((np.cos(rz), -np.sin(rz), 0), (np.sin(rz), np.cos(rz), 0), (0, 0, 1))
    )
    transform = np.eye(4)
    transform[:3, :3] = rotation_z @ rotation_y @ rotation_x
    transform[:3, 3] = translation
    return transform


def main():
    arguments = parse_arguments()
    if arguments.points <= 0:
        raise SystemExit("--points must be greater than zero.")
    if arguments.noise_sigma < 0:
        raise SystemExit("--noise-sigma must be non-negative.")

    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    mesh_path = arguments.output_dir / "test_cad.stl"
    cloud_path = arguments.output_dir / "test_cloud.ply"

    vertices = np.asarray(
        [
            (0, 0, 0), (100, 0, 0), (100, 80, 0), (0, 80, 0),
            (0, 0, 10), (100, 0, 10), (100, 80, 10), (0, 80, 10),
        ],
        dtype=np.float32,
    )
    # Counter-clockwise winding as viewed from outside the box.
    triangles = np.asarray(
        [
            (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7),
        ],
        dtype=np.int32,
    )

    generator = np.random.default_rng(arguments.seed)
    x = generator.uniform(10.0, 90.0, arguments.points)
    y = generator.uniform(10.0, 70.0, arguments.points)
    noise = generator.normal(0.0, arguments.noise_sigma, arguments.points)
    z = 10.0 + arguments.offset + noise

    aligned_points = np.column_stack((x, y, z))
    applied_transform = rigid_transform(
        arguments.rotation_deg, np.asarray(arguments.translation)
    )
    points = (
        aligned_points @ applied_transform[:3, :3].T
        + applied_transform[:3, 3]
    )
    write_binary_stl(mesh_path, vertices, triangles)
    write_binary_ply(cloud_path, points)

    absolute_noise = np.abs(arguments.offset + noise)
    print(f"CAD mesh:    {mesh_path}")
    print(f"Point cloud: {cloud_path}")
    print("The point cloud is intentionally NOT aligned with the CAD.")
    print("Rigid transform applied to the aligned cloud (row-major 4x4):")
    print(np.array2string(applied_transform, precision=9, suppress_small=True))
    print("Ground-truth transform that restores cloud alignment:")
    print(np.array2string(np.linalg.inv(applied_transform), precision=9, suppress_small=True))
    print("Expected metrics after recovering the alignment:")
    print(f"  mean absolute error:   {np.mean(absolute_noise):.6f}")
    print(f"  RMSE:                 {np.sqrt(np.mean(absolute_noise**2)):.6f}")
    print(f"  median absolute error: {np.median(absolute_noise):.6f}")
    print(f"  95th percentile:       {np.percentile(absolute_noise, 95):.6f}")
    print(f"  mean signed error:     {np.mean(arguments.offset + noise):.6f}")


if __name__ == "__main__":
    main()
