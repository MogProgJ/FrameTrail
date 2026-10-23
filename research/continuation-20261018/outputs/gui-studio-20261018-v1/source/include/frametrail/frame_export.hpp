#pragma once

#include "frametrail/frame.hpp"
#include <filesystem>

namespace frametrail {

// A deliberately simple, lossless RGB export for validating decoded pixels.
void write_ppm(const Frame& frame, const std::filesystem::path& path);

} // namespace frametrail
