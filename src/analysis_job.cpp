#include "frametrail/analysis_job.hpp"
#include "frametrail/frame_tracker.hpp"
#include <stdexcept>
#include <array>
#include <algorithm>

namespace frametrail {
AnalysisJob::~AnalysisJob() { cancel(); }
void AnalysisJob::cancel() { worker_.request_stop(); }
AnalysisProgress AnalysisJob::progress() const { std::lock_guard lock(mutex_);return progress_; }
void AnalysisJob::start(const std::filesystem::path& database,RunConfiguration configuration) {
    if(progress().active) throw std::logic_error("An analysis is already running");
    if(worker_.joinable())worker_.join();
    { std::lock_guard lock(mutex_);progress_={};progress_.active=true;progress_.status="opening"; }
    try {
        worker_=std::jthread([this,database,configuration=std::move(configuration)](std::stop_token stop) {
            std::optional<RunStore> store;
            std::string outcome="completed",error;
            try {
                const auto source_stamp=file_stamp(configuration.source),model_stamp=file_stamp(configuration.detector.model);
                MediaReader reader(configuration.source,stop);
                Detector detector(configuration.detector);
                FrameTracker tracker(configuration.tracking);
                if(stop.stop_requested())throw std::runtime_error("Analysis cancelled before creating output");
                store.emplace(RunStore::create(database,configuration,reader.info()));
                store->record_execution(detector.execution_info());
                if(source_stamp!=store->summary().source_stamp || model_stamp!=store->summary().model_stamp)
                    throw std::runtime_error("Source or model changed while opening analysis");
                {std::lock_guard lock(mutex_);progress_.duration=reader.info().duration;progress_.status="running";}
                std::array<bool,80> observed_classes{};
                auto preview_at=std::chrono::steady_clock::time_point{};
                while(!stop.stop_requested()) {
                    auto frame=reader.read();if(!frame)break;
                    const auto detection=detector.detect(*frame,stop);
                    store->record_execution(detection.execution);
                    const auto tracking=tracker.update(detection.objects,*frame);
                    store->record_frame(*frame,tracking.events,
                        configuration.kind==RunKind::appearances ? std::span<const TrackedObject>(tracking.objects) : std::span<const TrackedObject>{});
                    const auto now=std::chrono::steady_clock::now();
                    std::lock_guard lock(mutex_);++progress_.frames;progress_.events+=tracking.events.size();progress_.timestamp=frame->timestamp;
                    if(configuration.kind==RunKind::appearances) for(const auto& object:tracking.objects) {
                        progress_.appearances=std::max(progress_.appearances,object.id);
                        if(!observed_classes[object.detection.class_id]) {observed_classes[object.detection.class_id]=true;++progress_.classes;}
                    }
                    if(now-preview_at>=std::chrono::milliseconds(200)) {
                        progress_.preview=std::make_shared<AnalysisPreview>(AnalysisPreview{std::move(*frame),detection.objects});preview_at=now;
                    }
                }
                if(stop.stop_requested())outcome="cancelled";
                if(outcome=="completed" && configuration.kind==RunKind::appearances && progress().frames<2)
                    throw std::runtime_error("Choose a video with at least two frames; this input is a still image");
                if(outcome=="completed" && progress().frames==0)throw std::runtime_error("No visual frames could be decoded");
                if(file_stamp(configuration.source)!=store->summary().source_stamp ||
                    file_stamp(configuration.detector.model)!=store->summary().model_stamp)
                    throw std::runtime_error("Source or model changed during analysis; results are partial");
            }catch(const std::exception& exception) {
                outcome=stop.stop_requested() ? "cancelled" : "failed";error=exception.what();
            }
            if(store) {
                try {store->finish(outcome,error);}catch(const std::exception& exception) {outcome="failed";error=exception.what();}
            }
            std::lock_guard lock(mutex_);progress_.active=false;progress_.status=outcome;progress_.error=error;
        });
    }catch(...) {
        std::lock_guard lock(mutex_);progress_.active=false;progress_.status="failed";throw;
    }
}
}
