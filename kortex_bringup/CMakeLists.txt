cmake_minimum_required(VERSION 3.5)
project(kortex_bringup)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

# Install Python executables
install(PROGRAMS
  scripts/test_huge_joint_space_jump.py
  scripts/inject_wrench.py
  scripts/wrench_stamped_publisher.py
  scripts/verify_mujoco_force_stop.py
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY config launch
  DESTINATION share/${PROJECT_NAME}
)

install(DIRECTORY doc
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
