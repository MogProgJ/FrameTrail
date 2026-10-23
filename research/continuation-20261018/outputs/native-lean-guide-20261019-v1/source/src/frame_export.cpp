#include "frametrail/frame_export.hpp"

#include <fstream>
#include <limits>
#include <stdexcept>

namespace frametrail {

void write_ppm(const Frame& frame, const std::filesystem::path& path) {
    if (frame.width <= 0 || frame.height <= 0 ||
        frame.width > std::numeric_limits<int>::max() / 3 ||
        frame.stride < frame.width * 3 ||
        static_cast<std::size_t>(frame.height) >
            std::numeric_limits<std::size_t>::max() / static_cast<std::size_t>(frame.stride) ||
        frame.pixels.size() < static_cast<std::size_t>(frame.stride) * frame.height) {
        throw std::runtime_error("Cannot export an invalid RGB frame");
    }
    std::ofstream output(path, std::ios::binary);
    if (!output) {
        throw std::runtime_error("Cannot open preview output file");
    }
    output << "P6\n" << frame.width << ' ' << frame.height << "\n255\n";
    for (int row = 0; row < frame.height; ++row) {
        const auto offset = static_cast<std::size_t>(row) * frame.stride;
        output.write(reinterpret_cast<const char*>(frame.pixels.data() + offset),
            static_cast<std::streamsize>(frame.width) * 3);
    }
    output.close();
    if (!output) {
        throw std::runtime_error("Failed to write preview output file");
    }
}

} // namespace frametrail
