#!/usr/bin/env python3

"""Compute point-to-triangle error metrics for an aligned cloud and CAD mesh."""

import argparse
import csv
import json
from pathlib import Path

import numpy as np


def parse_arguments():
    parser = argparse.ArgumentParser(
        description=(
            "Compute distances from each point in an aligned point cloud to the "
            "nearest triangle of a CAD mesh. Coordinates and results use the input units."
        )
    )
    parser.add_argument("cloud", type=Path, help="Aligned measured cloud (for example, PLY).")
    parser.add_argument("mesh", type=Path, help="Triangulated CAD mesh (STL, OBJ, or PLY).")
    parser.add_argument(
        "--icp-aligned",
        action="store_true",
        required=True,
        help=(
            "Required confirmation that CLOUD is the transformed point cloud "
            "exported after ICP alignment to MESH in CloudCompare."
        ),
    )
    parser.add_argument(
        "--tolerances",
        type=float,
        nargs="+",
        default=[0.5, 1.0, 2.0],
        metavar="VALUE",
        help="Absolute-error tolerances in input units (default: 0.5 1.0 2.0).",
    )
    parser.add_argument(
        "--max-error",
        type=float,
        help="Exclude larger absolute distances from summary statistics.",
    )
    parser.add_argument(
        "--signed",
        action="store_true",
        help="Compute signed distance; meaningful only for a watertight mesh.",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path("point_errors.csv"),
        help="Per-point CSV output (default: point_errors.csv).",
    )
    parser.add_argument(
        "--summary-json",
        type=Path,
        help="Optionally write all summary metrics as JSON.",
    )
    return parser.parse_args()


def validate_arguments(arguments):
    if not arguments.cloud.is_file():
        raise SystemExit(f"Point-cloud file does not exist: {arguments.cloud}")
    if not arguments.mesh.is_file():
        raise SystemExit(f"CAD mesh file does not exist: {arguments.mesh}")
    if any(value < 0 for value in arguments.tolerances):
        raise SystemExit("Tolerances must be non-negative.")
    if arguments.max_error is not None and arguments.max_error <= 0:
        raise SystemExit("--max-error must be greater than zero.")


def load_geometry(cloud_path, mesh_path):
    cloud = o3d.io.read_point_cloud(
        str(cloud_path), remove_nan_points=True, remove_infinite_points=True
    )
    points = np.asarray(cloud.points, dtype=np.float32)
    if points.size == 0:
        raise SystemExit(f"No valid points were read from {cloud_path}")

    mesh = o3d.io.read_triangle_mesh(str(mesh_path))
    if len(mesh.vertices) == 0 or len(mesh.triangles) == 0:
        raise SystemExit(
            f"No triangle mesh was read from {mesh_path}; export the CAD as STL, OBJ, "
            "or triangulated PLY."
        )
    return points, mesh


def compute_distances(points, mesh, signed):
    tensor_mesh = o3d.t.geometry.TriangleMesh.from_legacy(mesh)
    scene = o3d.t.geometry.RaycastingScene()
    scene.add_triangles(tensor_mesh)
    queries = o3d.core.Tensor(points, dtype=o3d.core.Dtype.Float32)
    if signed:
        return scene.compute_signed_distance(queries).numpy().reshape(-1)
    return scene.compute_distance(queries).numpy().reshape(-1)


def summarize(distances, included, tolerances, signed):
    selected = distances[included].astype(np.float64)
    absolute = np.abs(selected)
    metrics = {
        "input_points": int(distances.size),
        "points_used": int(selected.size),
        "points_excluded": int(distances.size - selected.size),
        "mean_absolute_error": float(np.mean(absolute)),
        "rmse": float(np.sqrt(np.mean(np.square(absolute)))),
        "absolute_error_stddev": float(np.std(absolute)),
        "median_absolute_error": float(np.median(absolute)),
        "p95_absolute_error": float(np.percentile(absolute, 95)),
        "p99_absolute_error": float(np.percentile(absolute, 99)),
        "maximum_absolute_error": float(np.max(absolute)),
        "within_tolerance_percent": {
            str(value): float(100.0 * np.mean(absolute <= value))
            for value in tolerances
        },
    }
    if signed:
        metrics["mean_signed_error"] = float(np.mean(selected))
        metrics["signed_error_stddev"] = float(np.std(selected))
    return metrics


def print_summary(metrics):
    labels = (
        ("Input points", "input_points"),
        ("Points used", "points_used"),
        ("Points excluded", "points_excluded"),
        ("Mean absolute error", "mean_absolute_error"),
        ("RMSE", "rmse"),
        ("Absolute-error std. dev.", "absolute_error_stddev"),
        ("Median absolute error", "median_absolute_error"),
        ("95th percentile error", "p95_absolute_error"),
        ("99th percentile error", "p99_absolute_error"),
        ("Maximum absolute error", "maximum_absolute_error"),
        ("Mean signed error", "mean_signed_error"),
        ("Signed-error std. dev.", "signed_error_stddev"),
    )
    for label, key in labels:
        if key in metrics:
            value = metrics[key]
            rendered = str(value) if isinstance(value, int) else f"{value:.6f}"
            print(f"{label + ':':29} {rendered}")
    for tolerance, percentage in metrics["within_tolerance_percent"].items():
        print(f"{'Within +/-' + tolerance + ':':29} {percentage:.2f}%")


def write_csv(path, points, distances, included):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        writer.writerow(("x", "y", "z", "distance", "absolute_error", "included"))
        for point, distance, keep in zip(points, distances, included):
            writer.writerow((*map(float, point), float(distance), abs(float(distance)), int(keep)))


def main():
    arguments = parse_arguments()
    validate_arguments(arguments)

    global o3d
    try:
        import open3d as o3d
    except ImportError as error:
        raise SystemExit(
            "Open3D is required. Rebuild the ros2-kortex development container "
            "using the Software Setup instructions in src/ros2_kortex/README.md."
        ) from error

    points, mesh = load_geometry(arguments.cloud, arguments.mesh)
    distances = compute_distances(points, mesh, arguments.signed)
    included = np.isfinite(distances)
    if arguments.max_error is not None:
        included &= np.abs(distances) <= arguments.max_error
    if not np.any(included):
        raise SystemExit("No valid distances remain after filtering.")

    metrics = summarize(distances, included, arguments.tolerances, arguments.signed)
    metrics["icp_alignment_confirmed"] = True
    print_summary(metrics)
    write_csv(arguments.csv, points, distances, included)
    print(f"Per-point results: {arguments.csv}")

    if arguments.summary_json:
        arguments.summary_json.parent.mkdir(parents=True, exist_ok=True)
        arguments.summary_json.write_text(
            json.dumps(metrics, indent=2) + "\n", encoding="utf-8"
        )
        print(f"Summary results:   {arguments.summary_json}")


if __name__ == "__main__":
    main()
