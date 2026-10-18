#include "recovered_random.hpp"
#include <algorithm>
#include <cmath>
#include <cstring>
using namespace dungeonraid;

extern "C" void dr_random_set_seed(RandomState* state, std::uint32_t seed,
                                    std::uint32_t stream) {
    // SetRandSeed, VA 0x1b6c0. Unsigned comparison rejects negative enum bits.
    if (stream == 6) for (auto& value : state->seeds) value = seed;
    else if (stream < 6) state->seeds[stream] = seed;
}
extern "C" std::uint32_t dr_random_get_seed(const RandomState* state,
                                             std::uint32_t stream) {
    // GetRandSeed, VA 0x1b724.
    return stream < 6 ? state->seeds[stream] : 0;
}
extern "C" void dr_random_flush(RandomState* state) {
    // FlushRandSeeds, VA 0x1b6ec. Multiplication wraps modulo 2^32.
    for (auto& value : state->seeds) value *= 16807u;
}
extern "C" float dr_random_unit(std::uint32_t* seed) {
    // RandUnitF, VA 0x1b76c. This is NOT modulo 2^31-1 Park-Miller.
    *seed *= 16807u;
    const std::uint32_t bits = (*seed >> 10) | 0x40000000u;
    float value;
    std::memcpy(&value, &bits, sizeof(value));
    value -= 2.0f;
    // Original Clamp is called with [0,1]; this construction is finite [0,1).
    return std::min(1.0f, std::max(0.0f, value));
}
extern "C" std::int32_t dr_random_int(RandomState* state, std::int32_t a,
                                       std::int32_t b, std::uint32_t stream) {
    // RandI, VA 0x1bca0. Preserve float32 conversion and operation order.
    const float unit = dr_random_unit(&state->seeds[stream]);
    const auto low = std::min(a, b), high = std::max(a, b);
    const auto width = static_cast<std::int32_t>(static_cast<std::int64_t>(high) - low + 1);
    const float scaled = static_cast<float>(width) * unit;
    const float shifted = scaled + static_cast<float>(low);
    return static_cast<std::int32_t>(std::floor(shifted));
}
extern "C" float dr_random_float(RandomState* state,float a,float b,std::uint32_t stream) {
    const float unit=dr_random_unit(&state->seeds[stream]);
    return (b-a)*unit+a;
}
