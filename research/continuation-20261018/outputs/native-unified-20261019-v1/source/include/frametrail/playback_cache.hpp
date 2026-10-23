#pragma once
#include "frametrail/run_store.hpp"
#include <cstdio>
#include <mutex>
#include <thread>

namespace frametrail {
// Session-local overlays only: never retain decoded pixels or modify the source.
class OverlayCacheWriter {
public:
    explicit OverlayCacheWriter(const std::filesystem::path& path);
    ~OverlayCacheWriter();
    void record(const Frame& frame, std::span<const Detection> detections);
    void finish();
private:
    std::FILE* file_{};
    std::uint64_t frames_{}, bytes_{16};
    bool finished_{};
};
class OverlayCacheReader {
public:
    explicit OverlayCacheReader(const std::filesystem::path& path);
    ~OverlayCacheReader();
    std::vector<Detection> read(const Frame& frame);
    void verify_end() const;
    std::uint64_t frames() const { return total_; }
private:
    std::FILE* file_{};
    std::uint64_t total_{}, read_{};
};
struct PreparationPreview { Frame frame; std::vector<Detection> detections; };
struct PreparationProgress {
    bool active{};
    std::string state{"idle"}, error;
    std::uint64_t frames{};
    std::optional<std::chrono::microseconds> timestamp, duration, first_timestamp;
    std::shared_ptr<const PreparationPreview> preview; // One throttled preview, no Qt access.
    ExecutionInfo execution;
    FileStamp source_stamp;
};
class PlaybackPreparation {
public:
    ~PlaybackPreparation();
    void start(std::filesystem::path source, DetectorOptions options, std::filesystem::path cache);
    void cancel();
    PreparationProgress progress() const;
private:
    mutable std::mutex mutex_;
    PreparationProgress progress_;
    std::jthread worker_;
};
}
