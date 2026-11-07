#pragma once
#include "frametrail/run_store.hpp"
#include <string>
#include <vector>

namespace frametrail {
// A reason to look at an appearance again: likely a false alarm, a partial view or a wrong label.
// Severity 3 is the strongest hint. Heuristics, not verdicts; they are listed in report_html's method notes.
struct Concern {
    enum class Kind { brief, uncertain, relabelled, large };
    Kind kind{};
    int severity{};
    std::string text;
};
std::vector<Concern> appearance_concerns(const StoredAppearance& appearance, float confidence_threshold);

struct ReportConcern {
    std::uint64_t appearance{};
    int class_id{};
    double start{}; // seconds
    int severity{}; // sum of the appearance's concern severities
    std::string reasons;
};
struct ObjectTypeReport {
    int class_id{};
    std::uint64_t appearances{}, observations{}, concerns{};
    double screen_seconds{};  // All appearances' time on screen added up
    double present_seconds{}; // Time at least one of this type is visible
    double first_seen{}, last_seen{};
    double mean_confidence{}, peak_confidence{};
    double longest_seconds{};
    std::uint64_t longest_id{}, first_id{};
    std::uint64_t most_at_once{};
    double most_at_once_time{};
    double mean_path{}; // Movement per appearance in frame sizes (0 when not recorded)
};
struct ActivityBin {
    double start{}, end{};
    double mean_objects{};                     // Average number of tracked objects visible
    std::uint64_t most_objects{};              // Most visible at once (0 when per-frame statistics are missing)
    std::vector<std::pair<int,double>> by_type; // Average visible per type, largest first
    bool scene_cut{};
};
struct AnalysisReport {
    RunSummary summary;
    std::string video_name;
    double duration{};          // Whole video, seconds (0 if unknown)
    bool tenths{};              // Under a minute: times are shown to a tenth of a second
    double covered{};           // Part that was analysed, seconds
    double frame_interval{};    // Seconds between decoded frames (estimate)
    bool frame_details{};       // Per-frame statistics were recorded (FrameTrail 0.13 and later)
    bool appearance_details{};  // Per-appearance mean confidence, movement and label changes were recorded
    bool times_estimated{};     // The video has no usable timestamps; times assume 30 frames per second
    std::uint64_t analysed_frames{};
    double share_with_objects{}; // Share of the analysed time with at least one object visible
    double mean_objects{};
    std::uint64_t most_objects{};
    double most_objects_time{};
    std::vector<std::pair<int,std::uint64_t>> most_objects_mix;
    double detect_ms_mean{}, detect_ms_p95{}, detect_ms_max{};
    std::vector<double> scene_cuts;
    std::uint64_t brief{}, uncertain{}, relabelled{}, large{};
    std::vector<ObjectTypeReport> types; // Most appearances first
    std::vector<ActivityBin> activity;
    std::vector<ReportConcern> concerns; // Strongest first
    std::vector<std::string> findings;   // Plain-language summary sentences
};
// Reads the whole analysis once. Works for every saved appearance analysis; older files lack the
// per-frame and per-appearance detail, which the report then estimates from appearance spans.
AnalysisReport build_report(const RunStore& store, std::size_t bins = 80);
std::string report_html(const AnalysisReport& report);
void write_report_html(const AnalysisReport& report, const std::filesystem::path& output); // Never overwrites
// Distinct colours for the activity chart's five most frequent types (category colours can look alike).
inline constexpr const char* report_series_colours[5]{"#4c9aff","#f5a524","#3ccf91","#e86fd8","#a78bfa"};
std::string clock_text(double seconds,bool tenths=false); // 0:42, 12:05 or 1:02:05; with tenths 0:04.3
}
