#include "frametrail/detector.hpp"
#include "frametrail/preview_session.hpp"
#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <thread>
#ifdef _WIN32
#define NOMINMAX
#include <Windows.h>
#include <psapi.h>
#endif
using namespace std::chrono_literals;
namespace {
void require(bool value,const char* message) { if (!value) throw std::runtime_error(message); }
template<class F> void fails(F f) {
    try { f(); } catch (const std::exception&) { return; }
    throw std::runtime_error("Expected operation to fail");
}
template<class F> void wait_for(F f) {
    const auto deadline=std::chrono::steady_clock::now()+15s;
    while (!f()) {
        require(std::chrono::steady_clock::now()<deadline,"Detection worker timed out");
        std::this_thread::sleep_for(5ms);
    }
}
void contract() {
    // A padded RGB red/blue row: verify BGR planes, uint8 range, row stride, and padding.
    frametrail::Frame frame{0,{},2,1,8,{255,0,0, 0,0,255, 77,77}};
    const auto input=frametrail::yolox::preprocess(frame);
    constexpr int plane=416*416;
    require(input.resized_width==416 && input.resized_height==208 && input.ratio==208,"Letterbox geometry wrong");
    require(input.tensor[0]==0 && input.tensor[plane]==0 && input.tensor[2*plane]==255,"BGR/range contract wrong");
    require(input.tensor[415]==255 && input.tensor[2*plane+415]==0,"Resize edge wrong");
    require(input.tensor[208*416]==114 && input.tensor[3*plane-1]==114,"Padding is not bottom/right 114");
    require(input.tensor[207]>120 && input.tensor[207]<130,"Bilinear midpoint wrong");
    fails([]{frametrail::yolox::preprocess({});});
    std::vector<float> output(3549*85,0);
    // Two coincident person boxes, plus a different class: class-aware NMS keeps two.
    auto proposal=[&](int row,int cls,float score) {
        float* p=output.data()+row*85;
        p[0]=10.f-row; p[1]=10.f; p[2]=std::log(4.f); p[3]=std::log(6.f);
        p[4]=1.f; p[5+cls]=score;
    };
    proposal(0,0,.9f); proposal(1,0,.8f); proposal(2,2,.85f);
    auto objects=frametrail::yolox::postprocess(output,.5,832,416,.35f,.45f);
    require(objects.size()==2 && objects[0].class_id==0 && objects[1].class_id==2,"NMS/class scores wrong");
    require(std::abs(objects[0].left-128)<.01f && std::abs(objects[0].bottom-208)<.01f,"Original-frame mapping wrong");
    require(frametrail::class_name(0)=="person" && frametrail::class_name(79)=="toothbrush","COCO labels wrong");
    output[0]=std::numeric_limits<float>::quiet_NaN();
    objects=frametrail::yolox::postprocess(output,.5,832,416,.35f,.45f);
    require(objects.size()==2,"Malformed row poisoned valid detections");
    fails([&]{frametrail::yolox::postprocess({},1,10,10,.3f,.4f);});
    fails([&]{frametrail::yolox::postprocess(output,1,10,10,0,.4f);});
}
void inference(const std::filesystem::path& model,const std::filesystem::path& fixtures) {
    frametrail::Detector detector({model});
    frametrail::MediaReader image(fixtures/"still.png");
    auto frame=image.read();
    auto result=detector.detect(*frame);
    require(result.objects.empty(),"Solid red fixture unexpectedly has confident objects");
    require(result.elapsed_ms>0,"Missing detection timing");
    std::stop_source cancelled;
    cancelled.request_stop();
    fails([&]{detector.detect(*frame,cancelled.get_token());});
    fails([&]{frametrail::Detector bad({fixtures/"invalid.txt"});});
    frametrail::PreviewSession session;
    session.start(fixtures/"delayed.mkv",frametrail::DetectorOptions{model});
    const auto generation=session.snapshot().generation;
    std::uint64_t sequence=0;
    wait_for([&] {
        while (auto decoded=session.try_pop()) {
            require(decoded->generation==generation && decoded->frame.sequence==sequence++,"Detection/frame identity diverged");
            require(decoded->detection.has_value(),"Frame missing detection result");
        }
        const auto state=session.snapshot();
        require(state.state!=frametrail::PreviewState::failed,"Worker detection failed");
        return !state.worker_active && state.queued_frames==0;
    });
    require(sequence==10,"Analysis dropped frames");
    session.start(fixtures/"delayed.mkv",frametrail::DetectorOptions{model});
    wait_for([&]{return session.snapshot().queued_frames==2;});
    session.stop();
    wait_for([&]{return !session.snapshot().worker_active;});
    require(!session.try_pop(),"Cancelled analysis retained results");
    session.start(fixtures/"delayed.mkv",frametrail::DetectorOptions{model});
    wait_for([&]{return session.snapshot().state==frametrail::PreviewState::decoding;});
    session.stop();
    wait_for([&]{return !session.snapshot().worker_active;});
    require(session.snapshot().state==frametrail::PreviewState::cancelled,"Active inference cancellation failed");
}
void sample(const std::filesystem::path& model,const std::filesystem::path& sample_path) {
    frametrail::Detector detector({model});
    frametrail::MediaReader reader(sample_path);
    auto frame=reader.read();
    require(frame.has_value(),"No sample frame");
    auto result=detector.detect(*frame);
    bool dog=false,bicycle=false;
    for (const auto& object:result.objects) {
        dog|=object.class_id==16; bicycle|=object.class_id==1;
        require(object.left>=0 && object.right<=frame->width && object.top>=0 && object.bottom<=frame->height,"Box outside image");
        std::cout << frametrail::class_name(object.class_id) << ' ' << object.confidence << " box "
            << object.left << ',' << object.top << ',' << object.right << ',' << object.bottom << '\n';
    }
    require(dog && bicycle,"Reference photo must contain dog and bicycle detections");
    double total=0;
    for (int i=0;i<10;++i) total+=detector.detect(*frame).elapsed_ms;
    std::cout << "Warm CPU detection mean: " << total/10 << " ms/frame (10 runs, YOLOX-Nano 416, four threads)\n";
#ifdef _WIN32
    PROCESS_MEMORY_COUNTERS memory{};
    memory.cb=sizeof(memory);
    if (GetProcessMemoryInfo(GetCurrentProcess(),&memory,sizeof(memory)))
        std::cout << "Process peak working set: " << double(memory.PeakWorkingSetSize)/(1024*1024) << " MiB\n";
#endif
}
}
int main(int argc,char* argv[]) {
    try {
        if (argc==1) contract();
        else if (argc==4 && std::string_view(argv[1])=="--inference") inference(argv[2],argv[3]);
        else if (argc==4 && std::string_view(argv[1])=="--sample") sample(argv[2],argv[3]);
        else throw std::runtime_error("Unexpected test arguments");
        std::cout << "Detection checks passed\n";
        return 0;
    } catch(const std::exception& error) { std::cerr << error.what() << '\n'; return 1; }
}
