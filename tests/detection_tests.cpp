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
    // Open Images nesting: a parent box on the same object as a child box is hidden; other overlaps stay.
    require(frametrail::is_ancestor(106,16) && frametrail::is_ancestor(585,2) && !frametrail::is_ancestor(16,106) &&
        !frametrail::is_ancestor(2,0),"Open Images class hierarchy wrong");
    const frametrail::Detection dog{16,.6f,10,10,50,50},animal{106,.9f,11,10,50,51},far_animal{106,.8f,200,200,240,240},
        person{0,.9f,10,10,50,50};
    const auto hidden=frametrail::hide_parent_duplicates({animal,dog,far_animal,person});
    require(hidden.size()==3 && std::none_of(hidden.begin(),hidden.end(),[](const auto& d){return d.class_id==106 && d.left<100;}),
        "Parent box on a child box was not hidden, or an unrelated box was");
    require(frametrail::parse_model("world-m")==frametrail::DetectorModel::world_m &&
        frametrail::model_class_count(frametrail::DetectorModel::world_s)==100 && frametrail::class_name(80)=="fox" &&
        frametrail::class_name(86)=="balloon" && frametrail::class_name(99)=="shopping cart","World vocabulary/profile mapping wrong");
    const auto world=frametrail::yolo_world::preprocess({0,{},2,1,8,{255,0,0,0,0,255,77,77}});
    constexpr int world_plane=640*640;
    require(world.pad_x==0 && world.pad_y==160 && world.resized_height==320,"World centered geometry wrong");
    require(world.tensor[0]==114.f/255.f && world.tensor[160*640]==1 && world.tensor[2*world_plane+160*640]==0,
        "World RGB/range/padding wrong");
    std::vector<float> world_output(104*8400,0);
    auto world_proposal=[&](int row,int cls,float score){
        world_output[row]=320;world_output[8400+row]=320;world_output[16800+row]=80;world_output[25200+row]=160;
        world_output[(4+cls)*8400+row]=score;
    };
    world_proposal(0,80,.9f);world_proposal(1,80,.8f);world_proposal(2,16,.85f);
    const auto world_boxes=frametrail::yolo_world::postprocess(world_output,world,2,1,.35f,.45f);
    require(world_boxes.size()==2 && world_boxes[0].class_id==80 && world_boxes[1].class_id==16 &&
        std::abs(world_boxes[0].left-.875f)<.001f && std::abs(world_boxes[0].top-.25f)<.001f,"World layout/geometry/NMS wrong");
    world_output[0]=std::numeric_limits<float>::quiet_NaN();
    require(frametrail::yolo_world::postprocess(world_output,world,2,1,.35f,.45f).size()==2,"World malformed geometry poisoned other candidates");
    fails([&]{frametrail::yolo_world::postprocess({},world,2,1,.35f,.45f);});
    fails([]{frametrail::yolo_world::preprocess({});});
    const auto oi=frametrail::DetectorModel::openimages;
    const auto mapping=frametrail::model_classes(oi);
    require(mapping.size()==601 && frametrail::model_output_shape(oi)==std::vector<int64_t>({1,605,8400}) &&
        frametrail::model_has_class(oi,80) && frametrail::model_has_class(oi,614),"Open Images vocabulary/shape wrong");
    std::vector<float> oi_output(605*8400,0);
    int row=0;
    // Publisher's Man/Woman/Boy/Girl all map to person before suppression.
    for(std::size_t index=0;index<mapping.size();++index)if(mapping[index]==0) {
        oi_output[row]=320;oi_output[8400+row]=320;oi_output[16800+row]=80;oi_output[25200+row]=160;
        oi_output[(4+index)*8400+row]=.9f-row*.01f;++row;
    }
    require(row>=4 && frametrail::yolo_world::postprocess(oi_output,world,2,1,.35f,.45f,oi).size()==1,
        "Open Images human aliases created duplicate boxes");
    const auto last=std::find(mapping.begin(),mapping.end(),614)-mapping.begin();
    oi_output[(4+last)*8400+20]=.95f;oi_output[20]=320;oi_output[8400+20]=320;
    oi_output[16800+20]=80;oi_output[25200+20]=160;
    const auto oi_boxes=frametrail::yolo_world::postprocess(oi_output,world,2,1,.35f,.45f,oi);
    require(oi_boxes.size()==2 && oi_boxes[0].class_id==614 && oi_boxes[1].class_id==0,
        "Noncontiguous Open Images label mapping wrong");

    // A padded RGB red/blue row: verify BGR planes, uint8 range, row stride, and padding.
    frametrail::Frame frame{0,{},2,1,8,{255,0,0, 0,0,255, 77,77}};
    const auto input=frametrail::yolox::preprocess(frame);
    constexpr int plane=416*416;
    require(input.resized_width==416 && input.resized_height==208 && input.ratio==208,"Letterbox geometry wrong");
    require(input.tensor[0]==0 && input.tensor[plane]==0 && input.tensor[2*plane]==255,"BGR/range contract wrong");
    require(input.tensor[415]==255 && input.tensor[2*plane+415]==0,"Resize edge wrong");
    require(input.tensor[208*416]==114 && input.tensor[3*plane-1]==114,"Padding is not bottom/right 114");
    require(input.tensor[207]>120 && input.tensor[207]<130,"Bilinear midpoint wrong");
    const auto large=frametrail::yolox::preprocess(frame,640);
    require(large.tensor.size()==3*640*640 && large.ratio==320 && large.resized_height==320,"S letterbox geometry wrong");
    require(large.tensor[2*640*640]==255 && large.tensor[320*640]==114,"S color/padding wrong");
    std::vector<float> large_output(8400*85,0);
    // First stride-32 cell follows 6400 stride-8 and 1600 stride-16 cells.
    auto* p=large_output.data()+8000*85;
    p[0]=2; p[1]=3; p[2]=std::log(2.f); p[3]=std::log(4.f); p[4]=.8f;p[5+29]=.75f;
    const auto large_boxes=frametrail::yolox::postprocess(large_output,.5,1280,720,.35f,.45f,640);
    require(large_boxes.size()==1 && large_boxes[0].class_id==29 && std::abs(large_boxes[0].confidence-.6f)<.001f &&
        large_boxes[0].left==64 && large_boxes[0].top==64 && large_boxes[0].right==192 && large_boxes[0].bottom==320,"S grid/scale/class decode wrong");
    fails([&]{frametrail::yolox::postprocess(large_output,.5,1280,720,.35f,.45f);});
    fails([&]{frametrail::yolox::preprocess(frame,512);});
    fails([]{frametrail::parse_model("auto");});
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
void inference(const std::filesystem::path& model,const std::filesystem::path& fixtures,frametrail::DetectorModel variant=frametrail::DetectorModel::nano) {
    frametrail::Detector detector({model,.35f,.45f,variant});
    fails([&]{frametrail::Detector mismatch({model,.35f,.45f,variant==frametrail::DetectorModel::nano ? frametrail::DetectorModel::yolox_s : frametrail::DetectorModel::nano});});
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
    session.start(fixtures/"delayed.mkv",frametrail::DetectorOptions{model,.35f,.45f,variant});
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
    session.start(fixtures/"delayed.mkv",frametrail::DetectorOptions{model,.35f,.45f,variant});
    wait_for([&]{return session.snapshot().queued_frames==2;});
    session.stop();
    wait_for([&]{return !session.snapshot().worker_active;});
    require(!session.try_pop(),"Cancelled analysis retained results");
    session.start(fixtures/"delayed.mkv",frametrail::DetectorOptions{model,.35f,.45f,variant});
    wait_for([&]{return session.snapshot().state==frametrail::PreviewState::decoding;});
    session.stop();
    wait_for([&]{return !session.snapshot().worker_active;});
    require(session.snapshot().state==frametrail::PreviewState::cancelled,"Active inference cancellation failed");
}
void sample(const std::filesystem::path& model,const std::filesystem::path& sample_path,frametrail::DetectorModel variant=frametrail::DetectorModel::nano) {
    frametrail::Detector detector({model,.35f,.45f,variant});
    fails([&]{frametrail::Detector mismatch({model,.35f,.45f,variant==frametrail::DetectorModel::nano ? frametrail::DetectorModel::yolox_s : frametrail::DetectorModel::nano});});
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
    std::cout << "Warm CPU detection mean: " << total/10 << " ms/frame (10 runs, selected model, four threads)\n";
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
        else if(argc==5 && std::string_view(argv[1])=="--inference") inference(argv[2],argv[3],frametrail::parse_model(argv[4]));
        else if(argc==5 && std::string_view(argv[1])=="--sample") sample(argv[2],argv[3],frametrail::parse_model(argv[4]));
        else throw std::runtime_error("Unexpected test arguments");
        std::cout << "Detection checks passed\n";
        return 0;
    } catch(const std::exception& error) { std::cerr << error.what() << '\n'; return 1; }
}
