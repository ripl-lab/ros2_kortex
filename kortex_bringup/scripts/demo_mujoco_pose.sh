#!/usr/bin/env bash
set -euo pipefail

pose="${1:-home}"
case "$pose" in
  home)
    positions="$(ros2 pkg prefix kortex_description)/share/kortex_description/config/home_initial_positions.yaml"
    ;;
  zero)
    positions="$(ros2 pkg prefix kortex_description)/share/kortex_description/config/initial_positions.yaml"
    ;;
  *)
    echo "usage: demo_mujoco_pose.sh [home|zero]" >&2
    exit 2
    ;;
esac

exec ros2 launch kortex_bringup gen3_mujoco_admittance.launch.py \
  launch_gui:=true visualize_wrench:=true force_test_fixture:=false \
  initial_pose:="$pose" initial_positions_file:="$positions" gripper:=none
