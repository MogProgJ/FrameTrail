#pragma once

#include <chrono>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <vector>

namespace frametrail {

// An independent RGB24 snapshot. No pixels point into decoder-owned memory.
// Run/generation identity will be added with the asynchronous job controller.
struct Frame {
    std::uint64_t sequence{};
    std::optional<std::chrono::microseconds> timestamp;
    int width{};
    int height{};
    int stride{};
    std::vector<std::uint8_t> pixels;
};

} // namespace frametrail
