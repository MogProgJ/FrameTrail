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

// Sequential, local-file reader. One reader is used by one thread at a time.
// EOF returns nullopt; failures and cancellation throw std::runtime_error.
class MediaReader {
public:
    explicit MediaReader(const std::filesystem::path& path, std::stop_token stop = {});
    ~MediaReader();
    MediaReader(const MediaReader&) = delete;
    MediaReader& operator=(const MediaReader&) = delete;
    MediaReader(MediaReader&&) noexcept;
    MediaReader& operator=(MediaReader&&) noexcept;

    [[nodiscard]] const MediaInfo& info() const;
    [[nodiscard]] std::optional<Frame> read();

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace frametrail
