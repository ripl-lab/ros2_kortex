FROM ros:humble-ros-base-jammy

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=${USER_UID}
ARG RUN_CLARIUS_SETUP=true

ENV DEBIAN_FRONTEND=noninteractive
ENV ROS_DISTRO=humble
ENV COLCON_WS=/workspace/ros2_kortex_ws
ENV RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
ENV VIRTUAL_ENV=/workspace/ros2_kortex_ws/.venv
ENV PATH=/workspace/ros2_kortex_ws/.venv/bin:${PATH}

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash-completion \
    build-essential \
    cmake \
    git \
    iputils-ping \
    less \
    openssh-client \
    python3-argcomplete \
    python3-colcon-common-extensions \
    python3-pip \
    python3-rosdep \
    python3-vcstool \
    python3-venv \
    ros-humble-moveit \
    ros-humble-rmw-cyclonedds-cpp \
    ros-humble-ros2bag \
    ros-humble-rviz2 \
    ros-humble-xacro \
    sudo \
    vim \
    && rm -rf /var/lib/apt/lists/*

RUN if ! getent group ${USER_GID} >/dev/null; then groupadd --gid ${USER_GID} ${USERNAME}; fi \
    && useradd --uid ${USER_UID} --gid ${USER_GID} -m ${USERNAME} -s /bin/bash \
    && echo "${USERNAME} ALL=(root) NOPASSWD:ALL" >/etc/sudoers.d/${USERNAME} \
    && chmod 0440 /etc/sudoers.d/${USERNAME}

RUN rosdep init || true

WORKDIR ${COLCON_WS}
COPY . ${COLCON_WS}/src/ros2_kortex

RUN python3 -m venv --system-site-packages ${COLCON_WS}/.venv \
    && ${COLCON_WS}/.venv/bin/python -m pip install --upgrade pip 'setuptools<80' wheel \
    && (rosdep update --rosdistro ${ROS_DISTRO} || true) \
    && if [ "${RUN_CLARIUS_SETUP}" = "true" ]; then \
      . /opt/ros/${ROS_DISTRO}/setup.sh \
      && vcs import src --skip-existing --input src/ros2_kortex/ros2_kortex.${ROS_DISTRO}.repos \
      && vcs import src --skip-existing --input src/ros2_kortex/ros2_kortex-not-released.${ROS_DISTRO}.repos \
      && apt-get update \
      && rosdep install --ignore-src --from-paths src -y -r \
      && colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release --executor sequential \
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
