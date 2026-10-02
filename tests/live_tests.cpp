#include "frametrail/live_session.hpp"
#include <atomic>
#include <iostream>

namespace {
void require(bool value,const char* message){if(!value)throw std::runtime_error(message);}
template<class F> void wait(F done){for(int i=0;i<1000;++i){if(done())return;std::this_thread::sleep_for(std::chrono::milliseconds(5));}throw std::runtime_error("Live lifecycle timed out");}
struct State{std::atomic<int> open{},closed{};};
class SyntheticSource final:public frametrail::LiveSource {
    std::shared_ptr<State> state_;std::stop_token stop_;int remaining_;int interval_;
public:
    SyntheticSource(std::shared_ptr<State> state,std::stop_token stop,int frames,int interval):state_(std::move(state)),stop_(stop),remaining_(frames),interval_(interval){++state_->open;}
    ~SyntheticSource(){++state_->closed;}
    std::optional<frametrail::Frame> read() override {
        std::this_thread::sleep_for(std::chrono::milliseconds(interval_));
        if(stop_.stop_requested() || remaining_--==0)return {};
        frametrail::Frame frame;frame.width=64;frame.height=48;frame.stride=192;frame.pixels.resize(9216,50);return frame;
    }
};
}
int main(int argc,char* argv[]) {
    try {
        if(argc==2 && std::string(argv[1])=="--list-cameras") {
            const auto devices=frametrail::list_cameras();for(const auto& device:devices)std::cout<<device.name<<'\n';
            std::cout<<devices.size()<<" camera(s) enumerated; capture was not started\n";return 0;
        }
        if(argc==3 && std::string(argv[1])=="--camera-smoke") {
            const auto devices=frametrail::list_cameras();require(!devices.empty(),"No camera available for hardware smoke check");
            frametrail::LiveSession camera;
            for(int cycle=0;cycle<2;++cycle) {
                camera.start({devices.front().id},frametrail::DetectorOptions{argv[2]},frametrail::TrackingOptions{});
                wait([&]{return camera.snapshot().processed>0 || !camera.snapshot().active;});
                require(camera.snapshot().processed>0,camera.snapshot().error.c_str());
                const auto until=std::chrono::steady_clock::now()+std::chrono::seconds(2);
                int width{},height{};std::uint64_t shown{};
                while(std::chrono::steady_clock::now()<until) {
                    if(auto frame=camera.try_pop()){width=frame->frame.width;height=frame->frame.height;++shown;require(frame->detection && frame->tracking,"Camera lost analysis pairing");}
                    std::this_thread::sleep_for(std::chrono::milliseconds(10));
                }
                const auto s=camera.snapshot();camera.stop();wait([&]{return !camera.snapshot().active;});
                require(shown>0 && camera.snapshot().state=="stopped","Camera did not produce frames and release cleanly");
                std::cout<<"Hardware cycle "<<cycle+1<<": "<<width<<'x'<<height<<", captured "<<s.captured<<", analysed "<<s.processed
                    <<", input skips "<<s.input_drops<<", displayed "<<shown<<"; stopped cleanly\n";
            }
            return 0;
        }
        auto state=std::make_shared<State>();frametrail::LiveSession session;
        const auto factory=[state](std::stop_token stop){return std::make_unique<SyntheticSource>(state,stop,100000,2);};
        const auto slow=[](const frametrail::Frame&,std::stop_token stop) {
            std::mutex mutex;std::condition_variable_any wake;std::unique_lock lock(mutex);
            wake.wait_for(lock,stop,std::chrono::milliseconds(60),[]{return false;});
            return frametrail::DetectionResult{{{0,.9f,10,10,30,35}},60};
        };
        session.start_source(factory,slow,frametrail::TrackingOptions{});
        std::uint64_t last_sequence{};std::optional<std::chrono::microseconds> last_time;
        const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(3);
        std::uint64_t observed{};
        while(std::chrono::steady_clock::now()<deadline) {
            const auto snapshot=session.snapshot();require(snapshot.queued_input<=1 && snapshot.queued_results<=1,"Live queues grew under slow inference");
            if(auto frame=session.try_pop()) {
                require(frame->detection && frame->tracking,"Live frame lost paired analysis");
                require(!observed || frame->frame.sequence>last_sequence,"Live results reversed/repeated source order");
                require(frame->frame.timestamp && (!last_time || *frame->frame.timestamp>*last_time),"Live arrival timing failed");
                require(frame->tracking->negative_to_positive==0 && frame->tracking->positive_to_negative==0,"Stationary object invented crossings while skipping");
                require(std::chrono::steady_clock::now()-frame->arrived<std::chrono::milliseconds(500),"Live backlog accumulated latency");
                last_sequence=frame->frame.sequence;last_time=frame->frame.timestamp;++observed;
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }
        require(observed>10 && session.snapshot().input_drops>0,"Overload did not exercise latest-frame replacement");
        std::this_thread::sleep_for(std::chrono::milliseconds(150));require(session.snapshot().preview_drops>0,"Slow display did not replace stale results");
        session.stop();wait([&]{return !session.snapshot().active;});require(state->open==state->closed,"Stop retained camera source");
        for(int i=0;i<4;++i) {
            session.start_source(factory);wait([&]{return session.snapshot().captured>=2;});session.stop();wait([&]{return !session.snapshot().active;});
            require(session.snapshot().state=="stopped" && state->open==state->closed,"Restart/stop failed to release source");
        }
        session.start_source([state](std::stop_token stop){return std::make_unique<SyntheticSource>(state,stop,3,2);});
        wait([&]{return !session.snapshot().active;});require(session.snapshot().state=="failed" && !session.snapshot().error.empty(),"Disconnection was not reported");
        session.start_source(factory,[](const frametrail::Frame&,std::stop_token)->frametrail::DetectionResult{throw std::runtime_error("Injected inference failure");});
        wait([&]{return !session.snapshot().active;});require(session.snapshot().error=="Injected inference failure" && state->open==state->closed,"Inference failure leaked capture");
        session.start_source([](std::stop_token)->std::unique_ptr<frametrail::LiveSource>{throw std::runtime_error("Camera permission denied");});
        wait([&]{return !session.snapshot().active;});require(session.snapshot().error=="Camera permission denied","Open failure was lost");
        {frametrail::LiveSession closing;closing.start_source(factory,slow);wait([&]{return closing.snapshot().captured>0;});}
        require(state->open==state->closed,"Destruction leaked capture");
        std::cout<<"Live overload, bounded latency, ordering, failure, cancellation and restart passed\n";return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
