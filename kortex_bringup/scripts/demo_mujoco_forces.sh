#!/usr/bin/env bash
set -euo pipefail

mode="${1:-sequence}"
force="${2:-10.0}"
duration="${3:-2.0}"
start_delay="${4:-5.0}"

run_axis() {
  local axis="$1"
  local stiffness="$2"
  local run_seconds="$3"
  timeout --signal=INT --kill-after=5 "${run_seconds}s" \
    ros2 launch kortex_bringup gen3_mujoco_admittance.launch.py \
      launch_gui:=true visualize_wrench:=true \
      force_test_fixture:=true force_test_response:=true \
      force_test_axis:="$axis" force_test_force:="$force" \
      force_test_duration:="$duration" force_test_start_delay:="$start_delay" \
      force_test_stiffness:="$stiffness" || test "$?" -eq 124 \
      gripper:=none 
}

case "$mode" in
  sequence)
    # 100 N/m restores the original pose. Each axis receives its own clean
    # MuJoCo run only after the previous load has ended and the arm has settled.
    run_seconds="$(python3 -c "print(float('$start_delay') + float('$duration') + 8.0)")"
    for axis in x y z; do
      echo "MuJoCo force demo: ${force} N on world ${axis}"
      run_axis "$axis" 100.0 "$run_seconds"
    done
    ;;
  stay)
    axis="${5:-x}"
    echo "MuJoCo zero-spring demo: ${force} N on world ${axis}"
    # With stiffness zero the displaced pose is intentionally retained, so no
    # subsequent axis is commanded automatically.
    run_axis "$axis" 0.0 86400
    ;;
  *)
    echo "usage: demo_mujoco_forces.sh [sequence|stay] [force_N] [duration_s] [delay_s] [stay_axis]" >&2
    exit 2
    ;;
esac
