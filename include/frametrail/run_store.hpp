#pragma once
#include "frametrail/media_reader.hpp"
#include "frametrail/tracker.hpp"

namespace frametrail {
struct FileStamp {
    std::uint64_t bytes{};
    std::int64_t modified{};
    bool operator==(const FileStamp&) const = default;
};
FileStamp file_stamp(const std::filesystem::path& path);
enum class RunKind { crossings, appearances };
struct RunConfiguration {
    std::filesystem::path source;
    DetectorOptions detector;
    TrackingOptions tracking;
    RunKind kind{RunKind::crossings};
};
struct RunSummary {
    RunConfiguration configuration;
    MediaInfo media;
    FileStamp source_stamp, model_stamp;
    std::string id, created, status, error;
    std::uint64_t processed_frames{}, event_count{}, forward{}, reverse{};
    std::optional<std::chrono::microseconds> last_timestamp;
    bool timestamp_seekable{};
    std::uint64_t appearance_count{}, class_count{};
    ExecutionInfo execution;
};
struct StoredEvent {
    CrossingEvent event;
    std::vector<std::uint8_t> thumbnail; // Small RGB PPM, embedded in the database.
};

struct StoredAppearance {
    std::uint64_t id{}, first_sequence{}, last_sequence{}, observations{};
    std::optional<std::chrono::microseconds> first_timestamp, last_timestamp;
    Detection first_detection; // class_id is the appearance's settled class
    float peak_confidence{};
    std::vector<std::uint8_t> thumbnail;
    // Detail recorded since FrameTrail 0.13; `detailed` is false (and the rest zero) for older analyses.
    bool detailed{};
    int first_class{-1};          // Class when first seen; differs from first_detection.class_id after a relabel
    std::uint64_t class_changes{};
    double confidence_sum{};      // Over all observations: mean = confidence_sum / observations
    Detection last_detection;
    double path{};                // Bottom-centre movement summed over observations, in frame widths/heights
    double max_area{};            // Largest box as a share of the frame
    [[nodiscard]] double mean_confidence() const {return detailed && observations ? confidence_sum/double(observations) : peak_confidence;}
};
// Per analysed frame, recorded since FrameTrail 0.13: detection time, scene cuts and how many tracked objects
// of each type were visible.
struct FrameStats { double detect_ms{}; bool scene_cut{}; };
struct StoredFrame {
    std::uint64_t sequence{};
    std::optional<std::chrono::microseconds> timestamp;
    double detect_ms{};
    bool scene_cut{};
    std::vector<std::pair<int,int>> objects; // class id, visible count
};

// One frozen analysis per file. Read-only review never obtains a writer.
class RunStore {
public:
    static RunStore create(const std::filesystem::path& database, const RunConfiguration& configuration,
        const MediaInfo& media);
    explicit RunStore(const std::filesystem::path& database); // Read-only, existing file.
    ~RunStore();
    RunStore(RunStore&&) noexcept;
    RunStore& operator=(RunStore&&) noexcept;
    RunStore(const RunStore&) = delete;
    RunSummary summary() const;
    std::vector<StoredEvent> events(std::uint64_t after_id = 0, std::size_t limit = 100) const;
    std::vector<StoredAppearance> appearances(std::uint64_t after_id = 0, std::size_t limit = 100) const;
    // Every appearance in id order, without thumbnails (for reports).
    std::vector<StoredAppearance> appearance_details() const;
    // Every analysed frame's statistics in order; empty for analyses made before FrameTrail 0.13.
    std::vector<StoredFrame> frames() const;
    bool has_frame_details() const;
    void export_appearances_csv(const std::filesystem::path& output) const;
    // Events and progress commit together. Repeated identical IDs are ignored;
    // conflicting IDs fail. Memory holds only this frame's events/thumbnail.
    void record_frame(const Frame& frame, std::span<const CrossingEvent> events,
        std::span<const TrackedObject> objects = {}, std::optional<FrameStats> stats = {});
    void finish(std::string_view status, std::string_view error = {});
    void record_execution(const ExecutionInfo& execution);
    void export_csv(const std::filesystem::path& output) const; // Never overwrite.
    bool source_available() const;
private:
    struct Impl;
    explicit RunStore(std::unique_ptr<Impl> impl);
    std::unique_ptr<Impl> impl_;
};
}
