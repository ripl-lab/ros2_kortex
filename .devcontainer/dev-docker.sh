#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
REPO_DIR="$(cd -- "${SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd)"
WORKSPACE_DIR="$(cd -- "${REPO_DIR}/../.." >/dev/null 2>&1 && pwd)"

IMAGE_NAME="${IMAGE_NAME:-ros2-kortex-dev}"
CONTAINER_NAME="${CONTAINER_NAME:-ros2-kortex-dev}"
RUN_CLARIUS_SETUP="${RUN_CLARIUS_SETUP:-true}"
# The helper bind-mounts the host workspace over the image workspace, so its
# build products need to be created on the host instead of duplicated here.
BUILD_WORKSPACE_IN_IMAGE="${BUILD_WORKSPACE_IN_IMAGE:-false}"
CLARIUS_MODEL_URL="${CLARIUS_MODEL_URL:-}"
HOST_SSH_KEY="${HOST_SSH_KEY:-}"
BUILD_PACKAGES="${BUILD_PACKAGES:-}"
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
  --build-packages "PKG ..."
                   Build these packages in the mounted workspace on startup
  -h, --help       Show this help.

Environment:
  RUN_CLARIUS_SETUP=true|false  Build full image dependencies. Default: true
  BUILD_WORKSPACE_IN_IMAGE=true|false
                                Build the copied workspace into the image. Default: false
  CLARIUS_MODEL_URL=URL          Optional deeplabv3.pth download URL
  HOST_SSH_KEY=PATH              Private key used when no SSH agent is running
  BUILD_PACKAGES="PKG ..."       Packages to build on startup. Default: empty
  LOCAL_UID=1000                User id inside image. Default: current uid
  LOCAL_GID=1000                Group id inside image. Default: current gid

Examples:
  scripts/dev-docker.sh
  scripts/dev-docker.sh --no-build
  scripts/dev-docker.sh --build-packages "clarius_ros kortex_bringup"
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
    --build-packages)
      BUILD_PACKAGES="$2"
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
  SSH_BUILD_ARGS=()
  if [[ -n "${SSH_AUTH_SOCK:-}" && -S "${SSH_AUTH_SOCK}" ]]; then
    SSH_BUILD_ARGS+=(--ssh "default=${SSH_AUTH_SOCK}")
  else
    if [[ -z "${HOST_SSH_KEY}" ]]; then
      if [[ -f "${HOME}/.ssh/id_ed25519" ]]; then
        HOST_SSH_KEY="${HOME}/.ssh/id_ed25519"
      elif [[ -f "${HOME}/.ssh/id_rsa" ]]; then
        HOST_SSH_KEY="${HOME}/.ssh/id_rsa"
      fi
    fi
    if [[ -n "${HOST_SSH_KEY}" ]]; then
      if [[ ! -f "${HOST_SSH_KEY}" ]]; then
        echo "HOST_SSH_KEY does not exist: ${HOST_SSH_KEY}" >&2
        exit 1
      fi
      SSH_BUILD_ARGS+=(--ssh "default=${HOST_SSH_KEY}")
    else
      echo "No SSH agent or private key found; private repository imports will fail." >&2
      echo "Start ssh-agent and run ssh-add, or set HOST_SSH_KEY=/path/to/key." >&2
      exit 1
    fi
  fi

  DOCKER_BUILDKIT=1 docker build \
    "${SSH_BUILD_ARGS[@]}" \
    --build-arg "USER_UID=${LOCAL_UID}" \
    --build-arg "USER_GID=${LOCAL_GID}" \
    --build-arg "RUN_CLARIUS_SETUP=${RUN_CLARIUS_SETUP}" \
    --build-arg "BUILD_WORKSPACE_IN_IMAGE=${BUILD_WORKSPACE_IN_IMAGE}" \
    --build-arg "CLARIUS_MODEL_URL=${CLARIUS_MODEL_URL}" \
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
  -e "BUILD_PACKAGES=${BUILD_PACKAGES}"
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

# Forward the active X11 authorization cookie (including GNOME Wayland/Xwayland
# sessions) so GUI applications such as RViz can connect to the host display.
HOST_XAUTHORITY="${XAUTHORITY:-${HOME}/.Xauthority}"
if [[ -f "${HOST_XAUTHORITY}" ]]; then
  DOCKER_ARGS+=(
    -e "XAUTHORITY=/tmp/.docker.xauthority"
    -v "${HOST_XAUTHORITY}:/tmp/.docker.xauthority:ro"
  )
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
vcs import src --skip-existing --input src/clarius_interface/dependencies.repos
sudo apt-get update
sudo rosdep init 2>/dev/null || true
rosdep update --rosdistro humble
rosdep install --ignore-src --from-paths \
  src/clarius_interface src/apriltag src/apriltag_msgs \
  src/apriltag_ros src/realsense-ros -y -r
if [ -n "${BUILD_PACKAGES}" ]; then
  read -r -a selected_packages <<< "${BUILD_PACKAGES}"
  colcon build --packages-up-to "${selected_packages[@]}" --symlink-install
fi
if [ -f /workspace/ros2_kortex_ws/install/setup.bash ]; then
  source /workspace/ros2_kortex_ws/install/setup.bash
fi
'
else
  INIT_CMD='
set -e
source /opt/ros/humble/setup.bash
if [ -f /workspace/ros2_kortex_ws/.venv/bin/activate ]; then
  source /workspace/ros2_kortex_ws/.venv/bin/activate
fi
if [ -f /workspace/ros2_kortex_ws/install/setup.bash ]; then
  source /workspace/ros2_kortex_ws/install/setup.bash
fi
'
fi

docker run "${DOCKER_ARGS[@]}" "${IMAGE_NAME}" bash -lc "${INIT_CMD}
${EXEC_CMD}"
