#include "frametrail/analysis_job.hpp"
#include "frametrail/preview_session.hpp"
#include <fstream>
#include <iostream>
#include <thread>

namespace {
void require(bool condition,const char* message) {if(!condition)throw std::runtime_error(message);}
template<class F> void fails(F function,const char* message) {
    try{function();}catch(const std::exception&){return;}throw std::runtime_error(message);
}
template<class F> void wait(F function) {
    for(int i=0;i<2000;++i){if(function())return;std::this_thread::sleep_for(std::chrono::milliseconds(5));}
    throw std::runtime_error("Saved analysis timed out");
}
std::string bytes(const std::filesystem::path& path) {
    std::ifstream input(path,std::ios::binary);return {std::istreambuf_iterator<char>(input),{}};
}
std::filesystem::path output_root(const std::filesystem::path& root) {
    auto path=root/("saved-"+std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    std::filesystem::create_directory(path);return path;
}
void storage(const std::filesystem::path& fixtures) {
    const auto root=output_root(fixtures);
    const auto source=root/std::filesystem::path(u8"entrée, 空.mkv"), model=root/"model.onnx";
    std::filesystem::copy_file(fixtures/"variable.mkv",source);
    {std::ofstream out(model);out<<"storage contract model fingerprint";}
    frametrail::MediaInfo media;std::optional<frametrail::Frame> first;
    {frametrail::MediaReader reader(source);media=reader.info();first=reader.read();}
    require(bool(first),"Fixture missing");
    auto config=frametrail::RunConfiguration{source,{model,.55f,.4f},{}};
    config.tracking.line->a={.2,.3};config.tracking.line->b={.8,.7};config.tracking.classes={0,2};
    const auto path=root/std::filesystem::path(u8"résultats 空.frametrail");
    {
        auto store=frametrail::RunStore::create(path,config,media);
        for(std::uint64_t i=0;i<205;++i) {
            auto frame=*first;frame.sequence=i;frame.timestamp=std::chrono::microseconds(i*100000);
            const std::vector<frametrail::CrossingEvent> events{{i+1,17,i,frame.timestamp,0,
                i%2 ? frametrail::CrossingDirection::positive_to_negative : frametrail::CrossingDirection::negative_to_positive,{.5,.5}}};
            store.record_frame(frame,events);store.record_frame(frame,events);
        }
        auto summary=store.summary();require(summary.processed_frames==205 && summary.event_count==205 && summary.forward==103 && summary.reverse==102,
            "Idempotent writes doubled progress or counts");
        require(summary.timestamp_seekable,"Duplicate writes disabled timestamp seeking");
        auto frame=*first;frame.sequence=204;frame.timestamp=std::chrono::microseconds(20400000);
        std::vector<frametrail::CrossingEvent> conflict{{206,18,204,frame.timestamp,0,frametrail::CrossingDirection::negative_to_positive,{.5,.5}},
            {205,999,204,frame.timestamp,0,frametrail::CrossingDirection::negative_to_positive,{.5,.5}}};
        fails([&]{store.record_frame(frame,conflict);},"Conflicting event ID was silently replaced");
        require(store.summary().event_count==205,"Failed transaction partially inserted an event");
        store.finish("completed");fails([&]{store.record_frame(frame,{});},"Completed run changed");
    }
    const auto unchanged=bytes(path);frametrail::RunStore reopened(path);const auto summary=reopened.summary();
    require(summary.id.size()==32 && summary.status=="completed" && summary.configuration.tracking.classes==config.tracking.classes &&
        summary.configuration.detector.confidence==config.detector.confidence && summary.configuration.tracking.line->b.y==.7,
        "Frozen run settings failed round trip");
    const auto one=reopened.events(),two=reopened.events(one.back().event.id),three=reopened.events(two.back().event.id);
    require(one.size()==100 && two.size()==100 && three.size()==5 && two.front().event.id==101 && three.back().event.id==205,
        "Bounded event pagination lost or repeated rows");
    require(!one.front().thumbnail.empty(),"Stored thumbnail was lost");
    fails([&]{reopened.events(0,101);},"Unbounded event page accepted");
    fails([&]{reopened.finish("failed");},"Read-only review changed status");
    const auto csv=root/"events.csv";reopened.export_csv(csv);const auto csv_bytes=bytes(csv);
    require(csv_bytes.find("\",\"completed\",1,0,0,17,0,\"person\",\"negative_to_positive\"")!=std::string::npos,
        "CSV lost quoted source/status or exact source timestamp");
    require(csv_bytes.find("entrée, ")!=std::string::npos,"CSV did not preserve UTF-8 comma-containing source name");
    fails([&]{reopened.export_csv(csv);},"CSV overwrote an existing file");require(bytes(csv)==csv_bytes,"Failed export changed existing CSV");
    fails([&]{reopened.export_csv(root/"missing"/"events.csv");},"Invalid export destination accepted");
    require(bytes(path)==unchanged,"Review/export modified the saved database");
    fails([&]{frametrail::RunStore::create(path,config,media);},"Creating run overwrote existing database");
    std::filesystem::rename(source,root/"moved.mkv");
    require(!reopened.source_available() && reopened.events().size()==100,"Missing source blocked stored results");
    std::filesystem::rename(root/"moved.mkv",source);
    require(reopened.source_available(),"Restored original source was rejected");
    {std::ofstream out(source,std::ios::app);out<<'x';}require(!reopened.source_available(),"Changed source was accepted");
    fails([&]{frametrail::RunStore invalid(fixtures/"variable.mkv");},"Unrelated file accepted as a run");
    std::filesystem::copy_file(fixtures/"variable.mkv",source,std::filesystem::copy_options::overwrite_existing);
    const auto partial=root/"partial.frametrail";
    {auto store=frametrail::RunStore::create(partial,config,media);store.record_frame(*first,{});}
    require(frametrail::RunStore(partial).summary().status=="running","Interrupted run became complete");
    const auto duplicate=root/"duplicate-time.frametrail";
    {auto store=frametrail::RunStore::create(duplicate,config,media);store.record_frame(*first,{});
        first->sequence=1;store.record_frame(*first,{});require(!store.summary().timestamp_seekable,"Repeated timestamps allowed ambiguous seeking");store.finish("cancelled");}
}
void seeking(const std::filesystem::path& root) {
    for(const auto* name:{"variable.mkv","delayed.mkv"}) {
        frametrail::MediaReader reader(root/name);std::vector<frametrail::Frame> frames;
        while(auto frame=reader.read())frames.push_back(std::move(*frame));
        for(const auto index:{7,2,9,0}) {
            auto frame=reader.seek(*frames[index].timestamp);
            require(frame && frame->timestamp==frames[index].timestamp && frame->pixels==frames[index].pixels,"VFR/B-frame event seek changed frame identity");
            if(index<9) {auto next=reader.read();require(next && next->timestamp==frames[index+1].timestamp,"Post-seek playback skipped frame");}
        }
        auto middle=reader.seek(std::chrono::microseconds(350000));
        require(middle && middle->timestamp && middle->timestamp->count()>=350000,"Seek between frame timestamps failed");
        require(!reader.seek(std::chrono::hours(24)),"Beyond-EOF seek produced a false frame");
        frametrail::PreviewSession review;review.start(root/name,{},{},frametrail::ReviewPosition{frames[7].timestamp,7});
        std::optional<frametrail::PreviewFrame> shown;
        wait([&]{shown=review.try_pop();return bool(shown) || review.snapshot().state==frametrail::PreviewState::failed;});
        require(shown && shown->frame.timestamp==frames[7].timestamp && shown->frame.pixels==frames[7].pixels && !shown->detection && !shown->tracking,
            "Review invoked analysis or lost event frame");review.stop();wait([&]{return !review.snapshot().worker_active;});
        review.start(root/name,{},{},frametrail::ReviewPosition{{},7});
        wait([&]{shown=review.try_pop();return bool(shown);});
        require(shown->frame.sequence==7 && shown->frame.pixels==frames[7].pixels,"Missing-time sequence fallback lost event identity");
        fails([&]{review.reconfigure({},{});},"Review enabled inference via settings");review.stop();
    }
    std::stop_source stop;frametrail::MediaReader reader(root/"variable.mkv",stop.get_token());stop.request_stop();
    fails([&]{(void)reader.seek(std::chrono::microseconds(400000));},"Seek ignored cancellation");
}
void analysis(const std::filesystem::path& source,const std::filesystem::path& model) {
    const auto root=output_root(source.parent_path());auto config=frametrail::RunConfiguration{source,{model},{}};
    config.tracking.classes={16};config.tracking.line->a={.1,.75};config.tracking.line->b={.9,.75};
    frametrail::AnalysisJob job;const auto path=root/"native.frametrail";job.start(path,config);
    wait([&]{return !job.progress().active;});require(job.progress().status=="completed","Full native analysis did not finish");
    frametrail::RunStore store(path);const auto s=store.summary();const auto e=store.events();
    require(s.processed_frames==6 && s.event_count==1 && e.front().event.sequence==4 && e.front().event.timestamp->count()==400000 &&
        e.front().event.class_id==16 && s.forward==1,"Saved native pipeline lost crossing frame/timestamp/count");
    const auto broken=root/"failed.frametrail";auto invalid=config;invalid.detector.model=root/"missing.onnx";job.start(broken,invalid);
    wait([&]{return !job.progress().active;});require(job.progress().status=="failed" && !std::filesystem::exists(broken),"Missing model created a successful run");
    job.start(root/"cancelled.frametrail",config);job.cancel();wait([&]{return !job.progress().active;});
    require(job.progress().status=="cancelled","Analysis cancellation did not complete");
    if(std::filesystem::exists(root/"cancelled.frametrail"))require(frametrail::RunStore(root/"cancelled.frametrail").summary().status=="cancelled","Cancelled DB lost partial status");
    const auto partial=root/"partial-cancel.frametrail";job.start(partial,config);
    wait([&]{return job.progress().frames>=1;});job.cancel();wait([&]{return !job.progress().active;});
    require(job.progress().status=="cancelled" && frametrail::RunStore(partial).summary().processed_frames>=1,
        "Cancellation did not preserve committed frames and partial status");
}
}
int main(int argc,char* argv[]) {
    try {
        if(argc==2){storage(argv[1]);seeking(argv[1]);}
        else if(argc==3)analysis(argv[1],argv[2]);else throw std::runtime_error("Expected fixtures, or source/model");
        std::cout<<"Saved-run contracts passed\n";return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
