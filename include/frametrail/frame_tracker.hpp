#pragma once
#include "frametrail/tracker.hpp"
#include <array>

namespace frametrail {
struct SceneChange {bool changed{};double difference{},histogram_distance{};};
// Conservative visual-discontinuity heuristic. Bounded thumbnail, no model or Qt.
class SceneBoundary {
public:
    SceneChange observe(const Frame& frame);
private:
    std::array<double,32*18*3> previous_{};
    std::array<double,16*3> histogram_{};
    int width_{},height_{};
};
// Ordered pixel-aware composition keeps the association engine independent of pixels.
class FrameTracker {
public:
    explicit FrameTracker(TrackingOptions options={}):tracker_(std::move(options)){}
    TrackingResult update(std::span<const Detection> detections,const Frame& frame);
private:
    Tracker tracker_;
    SceneBoundary boundary_;
    std::optional<std::uint64_t> sequence_;
    std::optional<std::chrono::microseconds> timestamp_;
};
}
