#include "frametrail/live_session.hpp"
#include "frametrail/frame_tracker.hpp"
#include <stdexcept>

namespace frametrail {
namespace {
class CameraSource final:public LiveSource {
    MediaReader reader_;
public:
    CameraSource(const CameraInput& camera,std::stop_token stop):reader_(camera,stop){}
    std::optional<Frame> read() override {return reader_.read();}
};
}
LiveSession::~LiveSession(){stop();}
void LiveSession::stop(){halt_.request_stop();{std::lock_guard lock(mutex_);if(status_.active)status_.state="stopping";}available_.notify_all();}
LiveSnapshot LiveSession::snapshot() const {
    std::lock_guard lock(mutex_);auto status=status_;status.queued_input=latest_ ? 1 : 0;status.queued_results=result_ ? 1 : 0;return status;
}
std::optional<LiveFrame> LiveSession::try_pop(){std::lock_guard lock(mutex_);auto out=std::move(result_);result_.reset();return out;}
void LiveSession::start(CameraInput camera,std::optional<DetectorOptions> detector,std::optional<TrackingOptions> tracking) {
    if(tracking && !detector)throw std::invalid_argument("Live tracking requires detection");
    Processor processor;
    if(detector)processor=[options=*detector,instance=std::shared_ptr<Detector>{}](const Frame& frame,std::stop_token stop) mutable {
        if(!instance)instance=std::make_shared<Detector>(options);
        return instance->detect(frame,stop);
    };
    start_source([camera=std::move(camera)](std::stop_token stop){return std::make_unique<CameraSource>(camera,stop);},std::move(processor),std::move(tracking));
}
void LiveSession::start_source(SourceFactory source,Processor processor,std::optional<TrackingOptions> tracking) {
    if(!source || (tracking && !processor))throw std::invalid_argument("Live source/processor configuration is incomplete");
    if(snapshot().active)throw std::logic_error("Stop the live source before restarting");
    if(worker_.joinable())worker_.join();
    halt_=std::stop_source{};
    {std::lock_guard lock(mutex_);status_={};status_.active=true;status_.state="opening";latest_.reset();result_.reset();capture_done_=false;}
    try {
        worker_=std::jthread([this,source=std::move(source),processor=std::move(processor),tracking=std::move(tracking),halt=halt_]() mutable {
            const auto stop=halt.get_token();
            try {
                std::unique_ptr<FrameTracker> tracker=tracking ? std::make_unique<FrameTracker>(*tracking) : nullptr;
                std::jthread capture([this,source=std::move(source),stop] {
                    try {
                        auto camera=source(stop);if(!camera)throw std::runtime_error("Live source could not open");
                        const auto origin=std::chrono::steady_clock::now();std::uint64_t sequence{};
                        while(!stop.stop_requested()) {
                            auto frame=camera->read();if(!frame)throw std::runtime_error("Camera stream ended; check connection and restart");
                            const auto now=std::chrono::steady_clock::now();
                            frame->sequence=sequence++;frame->timestamp=std::chrono::duration_cast<std::chrono::microseconds>(now-origin);
                            std::lock_guard lock(mutex_);if(stop.stop_requested())break;
                            ++status_.captured;if(latest_)++status_.input_drops;
                            latest_=RawFrame{std::move(*frame),now};status_.state="live";available_.notify_all();
                        }
                    }catch(const std::exception& e){std::lock_guard lock(mutex_);if(!stop.stop_requested())status_.error=e.what();}
                    std::lock_guard lock(mutex_);capture_done_=true;available_.notify_all();
                });
                try {
                    while(!stop.stop_requested()) {
                        std::unique_lock lock(mutex_);
                        if(!available_.wait(lock,stop,[&]{return latest_.has_value() || capture_done_;}))break;
                        if(!latest_)break;
                        auto raw=std::move(*latest_);latest_.reset();lock.unlock();
                        const auto begin=std::chrono::steady_clock::now();LiveFrame result;
                        if(processor)result.detection=processor(raw.frame,stop);
                        if(tracker && !stop.stop_requested())result.tracking=tracker->update(result.detection->objects,raw.frame);
                        result.frame=std::move(raw.frame);result.arrived=raw.arrived;
                        result.processing_ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-begin).count();
                        lock.lock();if(stop.stop_requested())break;
                        ++status_.processed;if(result_)++status_.preview_drops;result_=std::move(result);
                    }
                }catch(const std::exception& e){std::lock_guard lock(mutex_);if(!stop.stop_requested())status_.error=e.what();}
                halt.request_stop();available_.notify_all();capture.join();
            }catch(const std::exception& e){std::lock_guard lock(mutex_);if(!stop.stop_requested())status_.error=e.what();}
            std::lock_guard lock(mutex_);latest_.reset();result_.reset();status_.active=false;
            status_.state=status_.error.empty() ? "stopped" : "failed";
        });
    }catch(...){std::lock_guard lock(mutex_);status_.active=false;status_.state="failed";throw;}
}
}
