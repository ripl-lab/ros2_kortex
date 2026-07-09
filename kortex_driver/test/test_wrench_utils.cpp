#include <array>
#include <limits>

#include "gtest/gtest.h"
#include "kortex_driver/wrench_utils.hpp"

TEST(WrenchUtils, ExtractsKortexFieldsInSemanticComponentOrder)
{
  Kinova::Api::BaseCyclic::BaseFeedback feedback;
  feedback.set_tool_external_wrench_force_x(1.0F);
  feedback.set_tool_external_wrench_force_y(2.0F);
  feedback.set_tool_external_wrench_force_z(3.0F);
  feedback.set_tool_external_wrench_torque_x(4.0F);
  feedback.set_tool_external_wrench_torque_y(5.0F);
  feedback.set_tool_external_wrench_torque_z(6.0F);

  EXPECT_EQ(kortex_driver::extractToolExternalWrench(feedback), (std::array<double, 6>{1, 2, 3, 4, 5, 6}));
}

TEST(WrenchUtils, AppliesBiasDeadbandFilterAndClamp)
{
  const std::array<double, 6> raw{5.0, -20.0, 100.0, 0.25, -4.0, 20.0};
  const std::array<double, 6> bias{1.0, 0.0, 0.0, 0.1, 0.0, 0.0};
  std::array<double, 6> output{};

  ASSERT_TRUE(kortex_driver::conditionWrench(
    raw, bias, 0.5, 2.0, 0.2, 40.0, 8.0, 0.0, 0.0, output));
  EXPECT_DOUBLE_EQ(output[0], 1.0);
  EXPECT_DOUBLE_EQ(output[1], -9.0);
  EXPECT_DOUBLE_EQ(output[2], 20.0);
  EXPECT_DOUBLE_EQ(output[3], 0.0);
  EXPECT_DOUBLE_EQ(output[4], -1.9);
  EXPECT_DOUBLE_EQ(output[5], 4.0);
}

TEST(WrenchUtils, RejectsNonFiniteAndExcessiveValues)
{
  std::array<double, 6> raw{};
  const std::array<double, 6> bias{};
  std::array<double, 6> output{};
  raw[0] = 81.0;
  EXPECT_FALSE(kortex_driver::conditionWrench(raw, bias, 1.0, 0.0, 0.0, 40.0, 8.0, 80.0, 15.0, output));
  raw[0] = std::numeric_limits<double>::quiet_NaN();
  EXPECT_FALSE(kortex_driver::conditionWrench(raw, bias, 1.0, 0.0, 0.0, 40.0, 8.0, 80.0, 15.0, output));
}

