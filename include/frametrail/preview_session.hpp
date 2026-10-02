#pragma once

#include "frametrail/media_reader.hpp"
#include "frametrail/detector.hpp"
#include <condition_variable>
#include <deque>
#include <mutex>
#include <thread>

namespace frametrail {

enum class PreviewState { idle, opening, decoding, completed, cancelled, failed };

struct PreviewSnapshot {
    PreviewState state{PreviewState::idle};
    std::uint64_t generation{};
    std::uint64_t decoded_frames{};
    std::size_t queued_frames{};
    std::optional<MediaInfo> info;
    std::string error;
    bool worker_active{};
};

struct PreviewFrame {
    std::uint64_t generation{};
    Frame frame;
    std::optional<DetectionResult> detection;
};

// Main-thread controller with a single decoding worker and bounded handoff.
// UI code polls; the worker never touches Qt or invokes application callbacks.
class PreviewSession {
public:
    static constexpr std::size_t capacity = 2;
    ~PreviewSession();
    void start(const std::filesystem::path& source, std::optional<DetectorOptions> detection = {});
    void stop();
    [[nodiscard]] PreviewSnapshot snapshot() const;
    [[nodiscard]] std::optional<PreviewFrame> try_pop();

private:
    mutable std::mutex mutex_;
    std::condition_variable_any available_;
    std::deque<PreviewFrame> frames_;
    PreviewSnapshot status_;
    // Last member: join happens before queue/synchronization objects disappear.
    std::jthread worker_;
};

} // namespace frametrail
