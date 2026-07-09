#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
REPO_DIR="$(cd -- "${SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd)"
WORKSPACE_DIR="$(cd -- "${REPO_DIR}/../.." >/dev/null 2>&1 && pwd)"

IMAGE_NAME="${IMAGE_NAME:-ros2-kortex-dev}"
CONTAINER_NAME="${CONTAINER_NAME:-ros2-kortex-dev}"
RUN_CLARIUS_SETUP="${RUN_CLARIUS_SETUP:-true}"
BUILD_IMAGE=1
INITIALIZE_WORKSPACE=1

usage() {
  cat <<EOF
Usage: $(basename "$0") [options] [-- command...]

Build and run the ROS 2 Kortex development container.

Options:
  --no-build       Do not build the Docker image before running.
  --no-init        Do not import repos or create .venv in the mounted workspace.
  --image NAME     Docker image name. Default: ${IMAGE_NAME}
  --name NAME      Docker container name. Default: ${CONTAINER_NAME}
  -h, --help       Show this help.

Environment:
  RUN_CLARIUS_SETUP=true|false  Build full image dependencies. Default: true
  LOCAL_UID=1000                User id inside image. Default: current uid
  LOCAL_GID=1000                Group id inside image. Default: current gid

Examples:
  scripts/dev-docker.sh
  scripts/dev-docker.sh --no-build
  scripts/dev-docker.sh --no-build -- colcon build --symlink-install
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-build)
      BUILD_IMAGE=0
      shift
      ;;
    --no-init)
      INITIALIZE_WORKSPACE=0
      shift
      ;;
    --image)
      IMAGE_NAME="$2"
      shift 2
      ;;
    --name)
      CONTAINER_NAME="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    *)
      break
      ;;
  esac
done

LOCAL_UID="${LOCAL_UID:-$(id -u)}"
LOCAL_GID="${LOCAL_GID:-$(id -g)}"

if [[ ! -f "${REPO_DIR}/.devcontainer/Dockerfile" ]]; then
  echo "Could not find ${REPO_DIR}/.devcontainer/Dockerfile" >&2
  exit 1
fi

if [[ "$(basename "${REPO_DIR}")" != "ros2_kortex" || "$(basename "$(dirname "${REPO_DIR}")")" != "src" ]]; then
  echo "Expected this repo at <workspace>/src/ros2_kortex; got ${REPO_DIR}" >&2
  exit 1
fi

if [[ "${BUILD_IMAGE}" -eq 1 ]]; then
  docker build \
    --build-arg "USER_UID=${LOCAL_UID}" \
    --build-arg "USER_GID=${LOCAL_GID}" \
    --build-arg "RUN_CLARIUS_SETUP=${RUN_CLARIUS_SETUP}" \
    -t "${IMAGE_NAME}" \
    -f "${REPO_DIR}/.devcontainer/Dockerfile" \
    "${REPO_DIR}"
fi

DOCKER_ARGS=(
  --rm
  --name "${CONTAINER_NAME}"
  --network=host
  --ipc=host
  --privileged
  -e "COLCON_WS=/workspace/ros2_kortex_ws"
  -e "DISPLAY=${DISPLAY:-}"
  -e "QT_X11_NO_MITSHM=1"
  -e "ROS_DISTRO=humble"
  -e "RMW_IMPLEMENTATION=rmw_fastrtps_cpp"
  -e "VIRTUAL_ENV=/workspace/ros2_kortex_ws/.venv"
  -e "LIBGL_ALWAYS_SOFTWARE=1"
  -e "XDG_RUNTIME_DIR=/tmp/runtime-vscode"
  -v "${WORKSPACE_DIR}:/workspace/ros2_kortex_ws:cached"
  -w "/workspace/ros2_kortex_ws"
)

if [[ -t 0 && -t 1 ]]; then
  DOCKER_ARGS+=(-it)
else
  DOCKER_ARGS+=(-i)
fi

if [[ -d /tmp/.X11-unix ]]; then
  DOCKER_ARGS+=(-v "/tmp/.X11-unix:/tmp/.X11-unix")
fi

if [[ -d "${HOME}/.ssh" ]]; then
  DOCKER_ARGS+=(-v "${HOME}/.ssh:/home/vscode/.ssh:ro")
fi

if [[ $# -gt 0 ]]; then
  EXEC_CMD=$(printf '%q ' "$@")
else
  EXEC_CMD='exec bash'
fi

if [[ "${INITIALIZE_WORKSPACE}" -eq 1 ]]; then
  INIT_CMD='
set -e
source /opt/ros/humble/setup.bash
if [ ! -x /workspace/ros2_kortex_ws/.venv/bin/python3 ]; then
  python3 -m venv --system-site-packages /workspace/ros2_kortex_ws/.venv
  /workspace/ros2_kortex_ws/.venv/bin/python -m pip install --upgrade pip "setuptools<80" wheel
fi
source /workspace/ros2_kortex_ws/.venv/bin/activate
vcs import src --skip-existing --input src/ros2_kortex/ros2_kortex.humble.repos
vcs import src --skip-existing --input src/ros2_kortex/ros2_kortex-not-released.humble.repos
'
else
  INIT_CMD='
set -e
source /opt/ros/humble/setup.bash
if [ -f /workspace/ros2_kortex_ws/.venv/bin/activate ]; then
  source /workspace/ros2_kortex_ws/.venv/bin/activate
fi
'
fi

docker run "${DOCKER_ARGS[@]}" "${IMAGE_NAME}" bash -lc "${INIT_CMD}
${EXEC_CMD}"
