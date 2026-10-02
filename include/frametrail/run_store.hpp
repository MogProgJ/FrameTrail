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
struct RunConfiguration {
    std::filesystem::path source;
    DetectorOptions detector;
    TrackingOptions tracking;
};
struct RunSummary {
    RunConfiguration configuration;
    MediaInfo media;
    FileStamp source_stamp, model_stamp;
    std::string id, created, status, error;
    std::uint64_t processed_frames{}, event_count{}, forward{}, reverse{};
    std::optional<std::chrono::microseconds> last_timestamp;
    bool timestamp_seekable{};
};
struct StoredEvent {
    CrossingEvent event;
    std::vector<std::uint8_t> thumbnail; // Small RGB PPM, embedded in the database.
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
    // Events and progress commit together. Repeated identical IDs are ignored;
    // conflicting IDs fail. Memory holds only this frame's events/thumbnail.
    void record_frame(const Frame& frame, std::span<const CrossingEvent> events);
    void finish(std::string_view status, std::string_view error = {});
    void export_csv(const std::filesystem::path& output) const; // Never overwrite.
    bool source_available() const;
private:
    struct Impl;
    explicit RunStore(std::unique_ptr<Impl> impl);
    std::unique_ptr<Impl> impl_;
};
}
