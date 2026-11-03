#pragma once
#include <cstdint>
#include <vector>
// The original's pictures as the shell app imports them from the player's IPA (T081): Xcode stored them as "CgBI"
// PNGs (raw deflate without zlib's wrapper, BGRA with premultiplied alpha), which no ordinary PNG reader takes.
// decode_ios_png gives the straight-alpha RGBA rows the Mac version's assets/original/*.png hold, byte for byte
// (each colour c * 255 / alpha, rounded down; frontend/tools/make_shell_data.py's check and the import compare them).
namespace drfront {
struct IosPicture {
    std::uint32_t width=0, height=0;
    std::vector<std::uint8_t> rgba;   // empty when the file is not an 8-bit RGBA CgBI PNG
};
IosPicture decode_ios_png(const std::uint8_t* data,std::size_t size);
}
