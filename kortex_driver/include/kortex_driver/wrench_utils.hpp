#ifndef KORTEX_DRIVER__WRENCH_UTILS_HPP_
#define KORTEX_DRIVER__WRENCH_UTILS_HPP_

#include <algorithm>
#include <array>
#include <cmath>

#include "BaseCyclic.pb.h"

namespace kortex_driver
{
inline std::array<double, 6> extractToolExternalWrench(
  const Kinova::Api::BaseCyclic::BaseFeedback & feedback)
{
  return {
    feedback.tool_external_wrench_force_x(), feedback.tool_external_wrench_force_y(),
    feedback.tool_external_wrench_force_z(), feedback.tool_external_wrench_torque_x(),
    feedback.tool_external_wrench_torque_y(), feedback.tool_external_wrench_torque_z()};
}

inline bool conditionWrench(
  const std::array<double, 6> & raw, const std::array<double, 6> & bias,
  double filter_coefficient, double force_deadband, double torque_deadband, double force_limit,
  double torque_limit, double force_stop_threshold, double torque_stop_threshold,
  std::array<double, 6> & output)
{
  auto apply_deadband = [](double value, double deadband)
  {
    if (std::abs(value) <= deadband)
    {
      return 0.0;
    }
    return std::copysign(std::abs(value) - deadband, value);
  };

  filter_coefficient = std::clamp(filter_coefficient, 0.0, 1.0);
  force_deadband = std::abs(force_deadband);
  torque_deadband = std::abs(torque_deadband);
  force_limit = std::abs(force_limit);
  torque_limit = std::abs(torque_limit);

  for (size_t index = 0; index < raw.size(); ++index)
  {
    if (!std::isfinite(raw[index]))
    {
      return false;
    }
    const bool force_axis = index < 3;
    const double stop_threshold =
      force_axis ? std::abs(force_stop_threshold) : std::abs(torque_stop_threshold);
    if (stop_threshold > 0.0 && std::abs(raw[index]) > stop_threshold)
    {
      return false;
    }
    const double deadband = force_axis ? force_deadband : torque_deadband;
    const double limit = force_axis ? force_limit : torque_limit;
    const double conditioned =
      std::clamp(apply_deadband(raw[index] - bias[index], deadband), -limit, limit);
    output[index] += filter_coefficient * (conditioned - output[index]);
  }
  return true;
}
}  // namespace kortex_driver

#endif  // KORTEX_DRIVER__WRENCH_UTILS_HPP_

