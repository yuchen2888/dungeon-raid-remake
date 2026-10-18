#pragma once
#include <cstdint>

namespace dungeonraid {
struct RandomState { std::uint32_t seeds[6]; };
}

extern "C" {
// SetRandSeed accepts streams 0..5; 6 sets all; other values do nothing.
void dr_random_set_seed(dungeonraid::RandomState*, std::uint32_t, std::uint32_t);
std::uint32_t dr_random_get_seed(const dungeonraid::RandomState*, std::uint32_t);
void dr_random_flush(dungeonraid::RandomState*);
float dr_random_unit(std::uint32_t*);
// Rand(float,float,RandType); endpoints are not sorted. stream < 6.
float dr_random_float(dungeonraid::RandomState*,float,float,std::uint32_t);
// Original valid-stream precondition: stream < 6. Finite representable signed
// range width and floor result required. Compiled with -ffp-contract=off.
// Float rounding is intentionally retained, including any upper-end rounding.
std::int32_t dr_random_int(dungeonraid::RandomState*, std::int32_t,
                           std::int32_t, std::uint32_t);
}
