#include "frametrail/playback_cache.hpp"
#include <array>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace frametrail {
namespace {
constexpr std::array<char,8> magic{'F','T','O','V','L','0','0','1'};
constexpr std::uint64_t max_bytes=256ULL*1024*1024, max_frames=1000000, max_objects=30000;
constexpr auto no_time=std::numeric_limits<std::int64_t>::min();
std::FILE* open_file(const std::filesystem::path& p,bool write) {
    std::FILE* f{};
#ifdef _WIN32
    _wfopen_s(&f,p.c_str(),write ? L"wbx" : L"rb");
#else
    f=std::fopen(p.c_str(),write ? "wbx" : "rb");
#endif
    if(!f)throw std::runtime_error(write ? "Cannot create playback cache; existing files are preserved" : "Cannot read playback cache");
    return f;
}
template<class T>void put(std::FILE* f,T value){if(std::fwrite(&value,sizeof(value),1,f)!=1)throw std::runtime_error("Cannot write playback cache; check free disk space");}
template<class T>T get(std::FILE* f){T value{};if(std::fread(&value,sizeof(value),1,f)!=1)throw std::runtime_error("Playback cache is incomplete");return value;}
void valid(const Detection& d,int width,int height) {
    if(d.class_id<0 || d.class_id>=recognition_classes || !std::isfinite(d.confidence) || d.confidence<0 || d.confidence>1 ||
       !std::isfinite(d.left) || !std::isfinite(d.top) || !std::isfinite(d.right) || !std::isfinite(d.bottom) ||
       d.left<0 || d.top<0 || d.right>width || d.bottom>height || d.right<=d.left || d.bottom<=d.top)
        throw std::runtime_error("Invalid cached detection geometry");
}
}
OverlayCacheWriter::OverlayCacheWriter(const std::filesystem::path& path) {
    file_=open_file(path,true);
    try {for(auto c:magic)put(file_,c);put(file_,std::uint64_t{});}catch(...){std::fclose(file_);file_=nullptr;throw;}
}
OverlayCacheWriter::~OverlayCacheWriter(){if(file_)std::fclose(file_);}
void OverlayCacheWriter::record(const Frame& f,std::span<const Detection> objects) {
    if(finished_)throw std::logic_error("Playback cache is sealed");
    if(f.width<=0 || f.height<=0 || objects.size()>max_objects || frames_>=max_frames ||
       bytes_+32+objects.size()*24>max_bytes)throw std::runtime_error("Video exceeds the 256 MB overlay-cache limit");
    for(const auto& d:objects)valid(d,f.width,f.height);
    put(file_,f.sequence);put(file_,f.timestamp ? f.timestamp->count() : no_time);
    put(file_,std::int32_t(f.width));put(file_,std::int32_t(f.height));put(file_,std::uint64_t(objects.size()));
    for(const auto& d:objects){put(file_,std::int32_t(d.class_id));put(file_,d.confidence);put(file_,d.left);put(file_,d.top);put(file_,d.right);put(file_,d.bottom);}
    ++frames_;bytes_+=32+objects.size()*24;
}
void OverlayCacheWriter::finish() {
    if(finished_)throw std::logic_error("Playback cache is already sealed");
    if(!frames_)throw std::runtime_error("No video frames were prepared");
    if(std::fseek(file_,8,SEEK_SET)!=0)throw std::runtime_error("Cannot seal playback cache");
    put(file_,frames_);
    if(std::fflush(file_)!=0)throw std::runtime_error("Cannot flush playback cache");
    finished_=true;
}
OverlayCacheReader::OverlayCacheReader(const std::filesystem::path& path) {
    if(std::filesystem::file_size(path)>max_bytes)throw std::runtime_error("Playback cache exceeds size limit");
    file_=open_file(path,false);
    try {
        for(auto c:magic)if(get<char>(file_)!=c)throw std::runtime_error("Unknown playback cache format");
        total_=get<std::uint64_t>(file_);
        if(!total_ || total_>max_frames)throw std::runtime_error("Playback cache was not completed");
    }catch(...){std::fclose(file_);file_=nullptr;throw;}
}
OverlayCacheReader::~OverlayCacheReader(){if(file_)std::fclose(file_);}
std::vector<Detection> OverlayCacheReader::read(const Frame& f) {
    if(read_>=total_)throw std::runtime_error("Source has more frames than the prepared cache");
    const auto sequence=get<std::uint64_t>(file_);const auto time=get<std::int64_t>(file_);
    const auto width=get<std::int32_t>(file_),height=get<std::int32_t>(file_);const auto count=get<std::uint64_t>(file_);
    if(sequence!=f.sequence || time!=(f.timestamp ? f.timestamp->count() : no_time) || width!=f.width || height!=f.height)
        throw std::runtime_error("Video no longer matches its prepared overlays");
    if(count>max_objects)throw std::runtime_error("Invalid cached object count");
    std::vector<Detection> out;out.reserve(std::size_t(count));
    for(std::uint64_t i=0;i<count;++i){Detection d;d.class_id=get<std::int32_t>(file_);d.confidence=get<float>(file_);d.left=get<float>(file_);d.top=get<float>(file_);d.right=get<float>(file_);d.bottom=get<float>(file_);valid(d,width,height);out.push_back(d);}
    ++read_;return out;
}
void OverlayCacheReader::verify_end() const {
    if(read_!=total_ || std::fgetc(file_)!=EOF || std::ferror(file_))throw std::runtime_error("Video/cache frame counts differ");
}
PlaybackPreparation::~PlaybackPreparation(){cancel();}
void PlaybackPreparation::cancel(){worker_.request_stop();}
PreparationProgress PlaybackPreparation::progress() const {std::lock_guard lock(mutex_);return progress_;}
void PlaybackPreparation::start(std::filesystem::path source,DetectorOptions options,std::filesystem::path cache) {
    if(progress().active)throw std::logic_error("Preparation already running");
    if(worker_.joinable())worker_.join();
    {std::lock_guard lock(mutex_);progress_={};progress_.active=true;progress_.state="preparing";}
    try {
        worker_=std::jthread([this,source=std::move(source),options=std::move(options),cache=std::move(cache)](std::stop_token stop){
            std::string outcome="completed",error;
            try {
                const auto source_stamp=file_stamp(source),model_stamp=file_stamp(options.model);
                MediaReader reader(source,stop);
                if(stop.stop_requested())throw std::runtime_error("Preparation cancelled before opening detector");
                Detector detector(options);OverlayCacheWriter writer(cache);
                {std::lock_guard lock(mutex_);progress_.source_stamp=source_stamp;progress_.duration=reader.info().duration;progress_.execution=detector.execution_info();}
                auto preview_at=std::chrono::steady_clock::time_point{};
                while(!stop.stop_requested()) {
                    auto frame=reader.read();if(!frame)break;
                    const auto result=detector.detect(*frame,stop);if(stop.stop_requested())break;
                    writer.record(*frame,result.objects);
                    const auto now=std::chrono::steady_clock::now();
                    std::lock_guard lock(mutex_);
                    if(!progress_.frames)progress_.first_timestamp=frame->timestamp;
                    ++progress_.frames;progress_.timestamp=frame->timestamp;progress_.execution=result.execution;
                    if(now-preview_at>=std::chrono::milliseconds(500)) {
                        progress_.preview=std::make_shared<PreparationPreview>(PreparationPreview{std::move(*frame),result.objects});preview_at=now;
                    }
                }
                if(stop.stop_requested())outcome="cancelled";
                else {
                    if(file_stamp(source)!=source_stamp || file_stamp(options.model)!=model_stamp)throw std::runtime_error("Video or model changed during preparation");
                    if(progress().frames<2)throw std::runtime_error("Choose a video with at least two frames");
                    writer.finish();
                }
            }catch(const std::exception& e){outcome=stop.stop_requested()?"cancelled":"failed";error=e.what();}
            std::lock_guard lock(mutex_);progress_.state=outcome;progress_.error=error;progress_.active=false;
        });
    }catch(...){std::lock_guard lock(mutex_);progress_.active=false;progress_.state="failed";throw;}
}
}
