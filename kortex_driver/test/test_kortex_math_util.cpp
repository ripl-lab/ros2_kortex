#include <cmath>

#include "gtest/gtest.h"
#include "kortex_driver/kortex_math_util.hpp"

TEST(KortexMathUtil, UnwrapsContinuouslyAcrossPositivePi)
{
  EXPECT_NEAR(
    KortexMathUtil::unwrapRadiansNear(-M_PI + 2e-4, M_PI - 1e-4), M_PI + 2e-4, 1e-12);
}

TEST(KortexMathUtil, UnwrapsContinuouslyAcrossNegativePi)
{
  EXPECT_NEAR(
    KortexMathUtil::unwrapRadiansNear(M_PI - 2e-4, -M_PI + 1e-4), -M_PI - 2e-4, 1e-12);
}

TEST(KortexMathUtil, PreservesNonFiniteInput)
{
  EXPECT_TRUE(std::isnan(KortexMathUtil::unwrapRadiansNear(NAN, 0.0)));
}
