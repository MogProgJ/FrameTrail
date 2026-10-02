#pragma once
#include "frametrail/preview_session.hpp"
#include <functional>

namespace frametrail {
class LiveSource {
public:
    virtual ~LiveSource()=default;
    virtual std::optional<Frame> read()=0;
};
struct LiveSnapshot {
    bool active{};
    std::string state{"idle"},error;
    std::uint64_t captured{},processed{},input_drops{},preview_drops{};
    std::size_t queued_input{},queued_results{};
};
struct LiveFrame {
    Frame frame;
    std::optional<DetectionResult> detection;
    std::optional<TrackingResult> tracking;
    std::chrono::steady_clock::time_point arrived;
    double processing_ms{};
};
class LiveSession {
public:
    using SourceFactory=std::function<std::unique_ptr<LiveSource>(std::stop_token)>;
    using Processor=std::function<DetectionResult(const Frame&,std::stop_token)>;
    ~LiveSession();
    void start(CameraInput camera,std::optional<DetectorOptions> detector={},std::optional<TrackingOptions> tracking={});
    // Also permits synthetic sources/processors for overload/lifecycle testing.
    void start_source(SourceFactory source,Processor processor={},std::optional<TrackingOptions> tracking={});
    void stop();
    LiveSnapshot snapshot() const;
    std::optional<LiveFrame> try_pop();
private:
    struct RawFrame {Frame frame;std::chrono::steady_clock::time_point arrived;};
    mutable std::mutex mutex_;
    std::condition_variable_any available_;
    LiveSnapshot status_;
    std::optional<RawFrame> latest_;
    std::optional<LiveFrame> result_;
    bool capture_done_{};
    std::stop_source halt_;
    std::jthread worker_;
};
}
