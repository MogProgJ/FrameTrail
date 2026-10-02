#pragma once

#include "frametrail/detector.hpp"
#include <optional>

namespace frametrail {
struct Point { double x{}, y{}; }; // Normalized frame coordinates [0,1].
enum class CrossingDirection { both, negative_to_positive, positive_to_negative };
std::string_view direction_name(CrossingDirection direction);
struct CountingLine {
    Point a{0.1, 0.5}, b{0.9, 0.5};
    CrossingDirection direction{CrossingDirection::both};
    double deadband{0.015};
    double rearm_distance{0.04};
};
struct TrackingOptions {
    // COCO people and road vehicles; other detections still render without IDs.
    std::vector<int> classes{0, 1, 2, 3, 5, 7};
    std::optional<CountingLine> line{CountingLine{}};
};
struct TrackedObject {
    std::uint64_t id{};
    Detection detection;
    bool confirmed{};
    std::vector<Point> trail; // Last 20 observed bottom-center positions.
};
struct CrossingEvent {
    std::uint64_t id{}, track_id{}, sequence{};
    std::optional<std::chrono::microseconds> timestamp;
    int class_id{};
    CrossingDirection direction{};
    Point position; // Intersection with the finite counting line.
};
struct TrackingResult {
    std::vector<TrackedObject> objects; // Observed now; never predicted-only boxes.
    std::vector<CrossingEvent> events; // This frame only, not an accumulating log.
    std::uint64_t negative_to_positive{}, positive_to_negative{};
    double elapsed_ms{};
};

// One ordered source/run per instance. No Qt, model, pixel, or storage ownership.
class Tracker {
public:
    explicit Tracker(TrackingOptions options = {});
    ~Tracker();
    Tracker(const Tracker&) = delete;
    Tracker& operator=(const Tracker&) = delete;
    TrackingResult update(std::span<const Detection> detections, std::uint64_t sequence,
        std::optional<std::chrono::microseconds> timestamp, int width, int height);
private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};
} // namespace frametrail
