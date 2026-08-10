# syntax=docker/dockerfile:1.4

FROM ros:humble-ros-base-jammy

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=${USER_UID}
ARG RUN_CLARIUS_SETUP=true
# Build by default so packages imported below (including clarius_ros) are
# registered in the image's ament index and are available at runtime.
ARG BUILD_WORKSPACE_IN_IMAGE=true
ARG CLARIUS_MODEL_URL=""

ENV DEBIAN_FRONTEND=noninteractive
ENV ROS_DISTRO=humble
ENV COLCON_WS=/workspace/ros2_kortex_ws
ENV RMW_IMPLEMENTATION=rmw_fastrtps_cpp
ENV VIRTUAL_ENV=/workspace/ros2_kortex_ws/.venv
ENV PATH=/workspace/ros2_kortex_ws/.venv/bin:${PATH}

RUN apt-get update && apt-get install -y --no-install-recommends \
    pkg-config \
    bash-completion \
    build-essential \
    cmake \
    curl \
    git \
    git-lfs \
    iputils-ping \
    libcap-dev \
    libegl1 \
    libfontconfig1 \
    libfreetype6 \
    libgbm1 \
    libglx0 \
    libglfw3-dev \
    libice6 \
    libopencv-dev \
    libopengl0 \
    libpcl-dev \
    libsm6 \
    libx11-dev \
    libx11-xcb1 \
    libxkbcommon-x11-0 \
    libxcb-cursor0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-xkb1 \
    less \
    openssh-client \
    python3-argcomplete \
    python3-colcon-common-extensions \
    python3-pip \
    python3-rosdep \
    python3-scipy \
    python3-vcstool \
    python3-venv \
    ros-humble-ackermann-msgs \
    ros-humble-control-toolbox \
    ros-humble-cv-bridge \
    ros-humble-example-interfaces \
    ros-humble-generate-parameter-library \
    ros-humble-moveit \
    ros-humble-pcl-conversions \
    ros-humble-pcl-ros \
    ros-humble-perception-pcl \
    ros-humble-plotjuggler-ros \
    ros-humble-rmw-cyclonedds-cpp \
    ros-humble-ros2bag \
    ros-humble-rviz2 \
    ros-humble-urdfdom-py \
    ros-humble-xacro \
    sudo \
    vim \
    libwayland-bin \
    wayland-protocols \
    xorg-dev \
    libwayland-dev \
    libxkbcommon-dev \
    extra-cmake-modules \
    && rm -rf /var/lib/apt/lists/*

RUN if ! getent group ${USER_GID} >/dev/null; then groupadd --gid ${USER_GID} ${USERNAME}; fi \
    && useradd --uid ${USER_UID} --gid ${USER_GID} -m ${USERNAME} -s /bin/bash \
    && echo "${USERNAME} ALL=(root) NOPASSWD:ALL" >/etc/sudoers.d/${USERNAME} \
    && chmod 0440 /etc/sudoers.d/${USERNAME}

RUN rosdep init || true
RUN git lfs install --system
RUN install -d -m 0700 /root/.ssh \
    && ssh-keyscan -H github.com >>/root/.ssh/known_hosts \
    && chmod 0600 /root/.ssh/known_hosts

WORKDIR ${COLCON_WS}
COPY . ${COLCON_WS}/src/ros2_kortex

# Install runtime Python dependencies globally so they remain visible when COLCON_WS and its
# development virtual environment are bind-mounted over the image paths.
RUN --mount=type=ssh --mount=type=cache,target=/root/.cache/pip \
    python3 -m venv --system-site-packages ${COLCON_WS}/.venv \
    && ${COLCON_WS}/.venv/bin/python -m pip install --upgrade pip 'setuptools<80' wheel \
    && (rosdep update --rosdistro ${ROS_DISTRO} || true) \
    && if [ "${RUN_CLARIUS_SETUP}" = "true" ]; then \
    . /opt/ros/${ROS_DISTRO}/setup.sh \
    && vcs import src --skip-existing --input src/ros2_kortex/ros2_kortex.${ROS_DISTRO}.repos \
    && vcs import src --skip-existing --input src/ros2_kortex/ros2_kortex-not-released.${ROS_DISTRO}.repos \
    && if [ -f src/clarius_interface/dependencies.repos ]; then \
      vcs import src --skip-existing --input src/clarius_interface/dependencies.repos; \
    fi \
    && git -C src/clarius_interface lfs pull \
    && git -C src/multilabel_segmentation lfs pull \
    && sed '/^[[:space:]]*colcon-common-extensions[[:space:]]*$/d' \
      src/clarius_interface/requirement.txt > /tmp/clarius-requirements.txt \
    && printf '%s\n' 'setuptools>=77,<80' 'packaging>=24,<26' > /tmp/python-constraints.txt \
    && /usr/bin/python3 -m pip install --default-timeout=120 --retries 10 \
      --constraint /tmp/python-constraints.txt \
      'setuptools>=77,<80' \
      'packaging>=24,<26' \
      Pillow \
      PySide6 \
      -r /tmp/clarius-requirements.txt \
    && if [ -n "${CLARIUS_MODEL_URL}" ]; then \
      mkdir -p src/multilabel_segmentation/multi_label_segmentation/src/models \
      && curl --fail --location "${CLARIUS_MODEL_URL}" \
        --output src/multilabel_segmentation/multi_label_segmentation/src/models/deeplabv3.pth; \
    else \
      echo "CLARIUS_MODEL_URL is empty; add deeplabv3.pth to the segmentation model directory before use."; \
    fi \
    && apt-get update \
    && rosdep install --ignore-src --from-paths src -y -r \
    && if [ "${BUILD_WORKSPACE_IN_IMAGE}" = "true" ]; then \
      /usr/bin/colcon build --cmake-args \
        -DCMAKE_BUILD_TYPE=Release \
        -DDOWNLOAD_UNITREE_H1_ASSETS=OFF \
        --executor sequential \
      && . install/setup.sh \
      && python3 -c "import clarius_ros.clarius_connect; print('pyclariuscast import OK')"; \
    else \
      echo "Skipping image-internal colcon build; the mounted workspace is built separately."; \
    fi \
    && rm -rf /var/lib/apt/lists/*; \
    fi

RUN printf '%s\n' \
    'source /opt/ros/humble/setup.bash' \
    'if [ -f /workspace/ros2_kortex_ws/install/setup.bash ]; then source /workspace/ros2_kortex_ws/install/setup.bash; fi' \
    'if [ -f /workspace/ros2_kortex_ws/.venv/bin/activate ]; then source /workspace/ros2_kortex_ws/.venv/bin/activate; fi' \
    >/etc/profile.d/ros2_kortex_ws.sh \
    && printf '%s\n' \
    '' \
    'source /opt/ros/humble/setup.bash' \
    'if [ -f /workspace/ros2_kortex_ws/install/setup.bash ]; then source /workspace/ros2_kortex_ws/install/setup.bash; fi' \
    'if [ -f /workspace/ros2_kortex_ws/.venv/bin/activate ]; then source /workspace/ros2_kortex_ws/.venv/bin/activate; fi' \
    >> /home/${USERNAME}/.bashrc \
    && chown -R ${USERNAME}:${USER_GID} /home/${USERNAME} ${COLCON_WS}

USER ${USERNAME}
WORKDIR ${COLCON_WS}
