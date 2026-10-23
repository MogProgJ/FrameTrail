#pragma once
#include "frametrail/run_store.hpp"
#include <mutex>
#include <thread>

namespace frametrail {
struct AnalysisPreview { Frame frame; std::vector<Detection> detections; };
struct AnalysisProgress {
    bool active{};
    std::string status{"idle"}, error;
    std::uint64_t frames{}, events{};
    std::optional<std::chrono::microseconds> timestamp, duration;
    std::uint64_t appearances{}, classes{};
    std::shared_ptr<const AnalysisPreview> preview; // Capacity one, throttled; no Qt access.
};
// Whole-file analysis, independent of preview speed, seeking, and UI settings.
class AnalysisJob {
public:
    ~AnalysisJob();
    void start(const std::filesystem::path& database, RunConfiguration configuration);
    void cancel();
    AnalysisProgress progress() const;
private:
    mutable std::mutex mutex_;
    AnalysisProgress progress_;
    std::jthread worker_; // Joins before progress/mutex destruction.
};
}
