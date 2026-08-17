#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
bag_path="${1:-${script_dir}/rosbag2_2026_08_11-20_40_26}"
if [[ $# -gt 0 ]]; then
  shift
fi

if [[ ! -f "${bag_path}/metadata.yaml" ]]; then
  echo "Rosbag not found: ${bag_path}" >&2
  exit 1
fi

if [[ -f /opt/ros/humble/setup.bash ]]; then
  # ROS setup scripts may reference variables that are unset in a clean shell.
  set +u
  source /opt/ros/humble/setup.bash
  set -u
fi

if [[ -f "${script_dir}/install/setup.bash" &&
      -f "${script_dir}/install/kortex_bringup/share/kortex_bringup/local_setup.bash" ]]; then
  set +u
  source "${script_dir}/install/setup.bash"
  set -u
fi

exec ros2 launch kortex_bringup replay_kortex_bag.launch.py \
  bag:="${bag_path}" \
  "$@"
