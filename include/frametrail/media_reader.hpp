#pragma once

#include "frametrail/frame.hpp"

#include <filesystem>
#include <memory>
#include <optional>
#include <stop_token>
#include <string>

namespace frametrail {

struct MediaInfo {
    std::string codec;
    int width{};
    int height{};
    std::optional<std::chrono::microseconds> duration;
};
struct CameraDevice { std::string id, name; };
struct CameraInput {
    std::string device;
    int width{}, height{}, fps{}; // Zero selects the driver's default format.
};
std::vector<CameraDevice> list_cameras();

// Sequential, local-file reader. One reader is used by one thread at a time.
// EOF returns nullopt; failures and cancellation throw std::runtime_error.
class MediaReader {
public:
    explicit MediaReader(const std::filesystem::path& path, std::stop_token stop = {});
    explicit MediaReader(const CameraInput& camera, std::stop_token stop = {});
    ~MediaReader();
    MediaReader(const MediaReader&) = delete;
    MediaReader& operator=(const MediaReader&) = delete;
    MediaReader(MediaReader&&) noexcept;
    MediaReader& operator=(MediaReader&&) noexcept;

    [[nodiscard]] const MediaInfo& info() const;
    [[nodiscard]] std::optional<Frame> read();
    // Seek backward to a keyframe, then decode to the first timestamp >= target.
    // Sequence restarts at zero and is a decode ordinal after seeking, not a
    // global source index. Presentation timestamps retain their source origin.
    [[nodiscard]] std::optional<Frame> seek(std::chrono::microseconds target);

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace frametrail
