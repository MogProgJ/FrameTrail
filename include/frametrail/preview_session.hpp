#pragma once

#include "frametrail/media_reader.hpp"
#include "frametrail/detector.hpp"
#include "frametrail/tracker.hpp"
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
    std::uint64_t analysis_revision{};
};

struct PreviewFrame {
    std::uint64_t generation{};
    Frame frame;
    std::optional<DetectionResult> detection;
    std::optional<TrackingResult> tracking;
    std::uint64_t analysis_revision{};
};

struct ReviewPosition {
    std::optional<std::chrono::microseconds> timestamp;
    std::uint64_t source_sequence{}; // Fallback if timestamps/seeking are unavailable.
};

// Main-thread controller with a single decoding worker and bounded handoff.
// UI code polls; the worker never touches Qt or invokes application callbacks.
class PreviewSession {
public:
    static constexpr std::size_t capacity = 2;
    ~PreviewSession();
    // review: open one saved frame exactly (no analysis). start_at: begin playback at the first frame
    // at or after this time, with detection and tracking as usual (a timeline jump).
    void start(const std::filesystem::path& source, std::optional<DetectorOptions> detection = {},
        std::optional<TrackingOptions> tracking = {}, std::optional<ReviewPosition> review = {},
        std::optional<std::chrono::microseconds> start_at = {});
    // Keep decoder position; re-analyse retained frames and the bounded queue.
    std::uint64_t reconfigure(std::optional<DetectorOptions> detection,
        std::optional<TrackingOptions> tracking, std::vector<Frame> retained = {});
    void stop();
    void release(); // After stop completes, join and release the retained file handle.
    [[nodiscard]] PreviewSnapshot snapshot() const;
    [[nodiscard]] std::optional<PreviewFrame> try_pop();

private:
    void launch_worker();
    void retain_frame(Frame frame); // mutex_ held; ordered and de-duplicated.
    mutable std::mutex mutex_;
    std::condition_variable_any available_;
    std::deque<PreviewFrame> frames_;
    PreviewSnapshot status_;
    std::filesystem::path source_;
    std::optional<DetectorOptions> detection_;
    std::optional<TrackingOptions> tracking_;
    std::optional<ReviewPosition> review_;
    std::optional<std::chrono::microseconds> start_at_;
    std::deque<Frame> pending_frames_;
    std::stop_source source_stop_;
    // Only sequential workers access this; retained at EOF for setting refreshes.
    std::unique_ptr<MediaReader> reader_;
    bool eof_{};
    // Last member: join happens before queue/synchronization objects disappear.
    std::jthread worker_;
};

} // namespace frametrail
