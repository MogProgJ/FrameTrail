#include "frametrail/analysis_job.hpp"
#include "frametrail/preview_session.hpp"
#include <fstream>
#include <sqlite3.h>
#include <algorithm>
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
    auto config=frametrail::RunConfiguration{source,{model,.55f,.4f,frametrail::DetectorModel::yolox_s},{}};
    config.tracking.line->a={.2,.3};config.tracking.line->b={.8,.7};config.tracking.classes={0,2};
    config.tracking.association=frametrail::AssociationPolicy::repair;
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
        summary.configuration.detector.variant==frametrail::DetectorModel::yolox_s && summary.configuration.detector.confidence==config.detector.confidence && summary.configuration.tracking.line->b.y==.7 && summary.configuration.tracking.association==frametrail::AssociationPolicy::repair,
        "Frozen run settings failed round trip");
    const auto one=reopened.events(),two=reopened.events(one.back().event.id),three=reopened.events(two.back().event.id);
    require(one.size()==100 && two.size()==100 && three.size()==5 && two.front().event.id==101 && three.back().event.id==205,
        "Bounded event pagination lost or repeated rows");
    require(!one.front().thumbnail.empty(),"Stored thumbnail was lost");
    fails([&]{reopened.events(0,101);},"Unbounded event page accepted");
    fails([&]{reopened.finish("failed");},"Read-only review changed status");
    fails([&]{reopened.record_execution({"DirectML","1.24.4","Test device",{}});},"Read-only review rewrote execution metadata");
    // Model metadata must survive reopening; legacy Nano-only files stay read-only.
    const auto legacy=root/"legacy.frametrail";
    std::filesystem::copy_file(path,legacy);
    sqlite3* db{};
    const auto legacy_utf8=legacy.u8string();
    require(sqlite3_open(reinterpret_cast<const char*>(legacy_utf8.c_str()),&db)==SQLITE_OK,"Legacy fixture open failed");
    const auto converted=sqlite3_exec(db,"ALTER TABLE run DROP COLUMN model_type; PRAGMA user_version=1;",nullptr,nullptr,nullptr);
    sqlite3_close(db);require(converted==SQLITE_OK,"Legacy fixture conversion failed");
    const auto legacy_before=bytes(legacy);
    {frametrail::RunStore old(legacy);require(old.summary().configuration.detector.variant==frametrail::DetectorModel::nano && old.events().size()==100,"Legacy run compatibility failed");}
    require(bytes(legacy)==legacy_before,"Legacy review rewrote the file");
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
void appearance_storage(const std::filesystem::path& fixtures) {
    const auto root=output_root(fixtures);const auto model=root/"appearance-model.onnx";
    {std::ofstream file(model);file<<"appearance storage fixture";}
    const auto source=fixtures/"variable.mkv";frametrail::MediaReader reader(source);auto frame=*reader.read();
    frametrail::RunConfiguration config{source,{model},{},frametrail::RunKind::appearances};config.tracking.line.reset();config.tracking.classes={0,14};
    const auto path=root/"appearances.frametrail";
    {
        auto saved=frametrail::RunStore::create(path,config,reader.info());
        const frametrail::TrackedObject person{1,{0,.8f,10,5,25,30},false,{}};
        saved.record_frame(frame,{},std::vector{person});saved.record_frame(frame,{},std::vector{person});
        frame.sequence=1;frame.timestamp=std::chrono::microseconds(100000);
        auto weaker=person;weaker.detection.confidence=.6f;
        const frametrail::TrackedObject bird{2,{14,.9f,30,10,40,25},false,{}};
        saved.record_frame(frame,{},std::vector{weaker,bird});
        frame.sequence=2;frame.timestamp=std::chrono::microseconds(500000);
        auto stronger=person;stronger.detection.confidence=.95f;saved.record_frame(frame,{},std::vector{stronger});
        auto info=saved.summary();require(info.appearance_count==2 && info.class_count==2 && info.processed_frames==3 && info.event_count==0,"Appearance summary lost aggregation");
        const auto values=saved.appearances();
        require(values[0].observations==3 && values[0].first_timestamp->count()==0 && values[0].last_timestamp->count()==500000 &&
            values[0].first_detection.confidence==.8f && values[0].peak_confidence==.95f && values[0].first_sequence==0 && values[0].last_sequence==2 && !values[0].thumbnail.empty(),"Appearance interval/confidence/idempotence failed");
        frame.sequence=3;frame.timestamp=std::chrono::microseconds(600000);auto conflict=person;conflict.detection.class_id=14;auto new_bird=bird;new_bird.id=3;
        fails([&]{saved.record_frame(frame,{},std::vector{new_bird,conflict});},"Changed appearance class was accepted");
        require(saved.summary().appearance_count==2 && saved.summary().processed_frames==3,"Failed appearance write was not rolled back");
        saved.finish("completed");
    }
    const auto before=bytes(path);frametrail::RunStore saved(path);const auto info=saved.summary();
    require(info.configuration.kind==frametrail::RunKind::appearances && !info.configuration.tracking.line && saved.appearances(1,1).front().id==2,"Appearance metadata/page round trip failed");
    fails([&]{saved.appearances(0,101);},"Unbounded appearance page accepted");
    const auto csv=root/"appearances.csv";saved.export_appearances_csv(csv);const auto content=bytes(csv);
    require(content.starts_with("\xef\xbb\xbfObject,Appearance ID") && content.find("00:00:00.000,00:00:00.500,0.500,3,95.00")!=std::string::npos && content.find("\r\n")!=std::string::npos,"Readable CSV times/format/confidence failed");
    require(content.find(info.id)!=std::string::npos,"Appearance CSV lost its run namespace");
    fails([&]{saved.export_appearances_csv(csv);},"Appearance CSV replaced existing output");
    require(bytes(path)==before && bytes(csv)==content,"Review/export changed saved results");
    const auto legacy=root/"schema2.frametrail";std::filesystem::copy_file(path,legacy);
    sqlite3* db{};const auto name=legacy.u8string();require(sqlite3_open(reinterpret_cast<const char*>(name.c_str()),&db)==SQLITE_OK,"Schema2 fixture open failed");
    const auto result=sqlite3_exec(db,"ALTER TABLE run DROP COLUMN run_kind; DROP TABLE appearances; PRAGMA user_version=2;",nullptr,nullptr,nullptr);sqlite3_close(db);
    require(result==SQLITE_OK,"Schema2 fixture conversion failed");const auto legacy_before=bytes(legacy);
    {frametrail::RunStore older(legacy);require(older.summary().configuration.kind==frametrail::RunKind::crossings && older.appearances().empty(),"Schema2 compatibility failed");}
    require(bytes(legacy)==legacy_before,"Schema2 review wrote a migration");
    const auto previous=root/"schema3-before-gpu.frametrail";std::filesystem::copy_file(path,previous);
    const auto previous_name=previous.u8string();require(sqlite3_open(reinterpret_cast<const char*>(previous_name.c_str()),&db)==SQLITE_OK,"Previous schema3 fixture open failed");
    const auto removed=sqlite3_exec(db,"ALTER TABLE run DROP COLUMN requested_backend; ALTER TABLE run DROP COLUMN gpu_device; ALTER TABLE run DROP COLUMN execution_backend; ALTER TABLE run DROP COLUMN execution_runtime; ALTER TABLE run DROP COLUMN execution_device; ALTER TABLE run DROP COLUMN execution_fallback; PRAGMA user_version=3;",nullptr,nullptr,nullptr);
    sqlite3_close(db);require(removed==SQLITE_OK,"Previous schema3 fixture conversion failed");
    const auto previous_bytes=bytes(previous);
    {frametrail::RunStore old(previous);require(old.summary().appearance_count==2 && old.summary().execution.runtime.empty(),"0.9 appearance analysis lost compatibility or acquired invented runtime identity");}
    require(bytes(previous)==previous_bytes,"Previous schema3 review rewrote the file");
    const auto missing=root/"unknown-times.frametrail";
    {auto writer=frametrail::RunStore::create(missing,config,reader.info());frame.sequence=0;frame.timestamp.reset();writer.record_frame(frame,{},std::vector{frametrail::TrackedObject{1,{0,.8f,10,5,25,30},true,{}}});writer.finish("cancelled");}
    require(!frametrail::RunStore(missing).summary().timestamp_seekable && !frametrail::RunStore(missing).appearances()[0].first_timestamp,"Unknown timestamp was invented");
}
void expanded_storage(const std::filesystem::path& fixtures,frametrail::DetectorModel variant,int category) {
    const auto root=output_root(fixtures),source=fixtures/"variable.mkv",model=root/"world.onnx";
    {std::ofstream file(model);file<<"world storage fixture";}
    frametrail::MediaReader reader(source);auto frame=*reader.read();
    frametrail::RunConfiguration config{source,{model,.35f,.45f,variant},{},frametrail::RunKind::appearances};
    config.tracking.line.reset();config.tracking.classes={0,category};const auto path=root/"world.frametrail";
    {
        auto store=frametrail::RunStore::create(path,config,reader.info());
        const frametrail::TrackedObject fox{1,{category,.85f,2,3,20,25},false,{}};
        store.record_frame(frame,{},std::vector{fox});store.finish("completed");
    }
    const auto before=bytes(path);frametrail::RunStore store(path);store.export_appearances_csv(root/"world.csv");
    require(store.appearances().front().first_detection.class_id==category &&
        store.summary().configuration.detector.variant==variant &&
        bytes(root/"world.csv").find(std::string(frametrail::class_name(category)))!=std::string::npos && bytes(path)==before,"World save/reopen/CSV vocabulary failed");
    auto legacy=config;legacy.detector.variant=frametrail::DetectorModel::nano;
    fails([&]{frametrail::RunStore::create(root/"invalid.frametrail",legacy,reader.info());},"Legacy model accepted fox categories");
    require(!std::filesystem::exists(root/"invalid.frametrail"),"Invalid model classes created output");
    const auto tampered=root/"tampered.frametrail";std::filesystem::copy_file(path,tampered);
    sqlite3* db{};const auto name=tampered.u8string();require(sqlite3_open(reinterpret_cast<const char*>(name.c_str()),&db)==SQLITE_OK,"Tamper fixture open failed");
    const auto result=sqlite3_exec(db,"UPDATE run SET vocabulary='wrong labels';",nullptr,nullptr,nullptr);sqlite3_close(db);
    require(result==SQLITE_OK,"Tamper fixture write failed");fails([&]{frametrail::RunStore bad(tampered);},"Mismatched stored vocabulary accepted");
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
    auto appearance_config=config;appearance_config.kind=frametrail::RunKind::appearances;appearance_config.tracking.line.reset();
    appearance_config.tracking.classes.clear();for(int id=0;id<80;++id)appearance_config.tracking.classes.push_back(id);
    const auto appearance_file=root/"native-appearances.frametrail";job.start(appearance_file,appearance_config);
    wait([&]{return !job.progress().active;});require(job.progress().status=="completed","Native appearance pipeline failed");
    frametrail::RunStore appearance_store(appearance_file);const auto appearances=appearance_store.appearances();
    require(appearance_store.summary().processed_frames==6 && appearance_store.summary().appearance_count>=3 && appearance_store.summary().class_count>=3 &&
        std::ranges::any_of(appearances,[](const auto& item){return item.first_detection.class_id==16 && item.first_timestamp && item.first_timestamp->count()==0;}),"Appearance pipeline lost dog/categories/timestamp");
    require(job.progress().preview && job.progress().preview->frame.width==1000,"Analysis preview was not published");
    auto blank_config=appearance_config;blank_config.source=source.parent_path()/"blank.mkv";
    const auto empty_file=root/"empty-appearances.frametrail";job.start(empty_file,blank_config);
    wait([&]{return !job.progress().active;});require(job.progress().status=="completed" && frametrail::RunStore(empty_file).summary().appearance_count==0 && frametrail::RunStore(empty_file).summary().processed_frames==10,"Zero-object video was treated as a failure");
    for(const auto* name:{"still.png","audio.wav","invalid.txt"}) {
        auto invalid_input=appearance_config;invalid_input.source=source.parent_path()/name;
        const auto output=root/(std::string(name)+".frametrail");job.start(output,invalid_input);
        wait([&]{return !job.progress().active;});require(job.progress().status=="failed","Invalid/non-video input became a completed appearance analysis");
        if(std::filesystem::exists(output))require(frametrail::RunStore(output).summary().status=="failed","Failed input lost partial status");
    }
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
        if(argc==2){storage(argv[1]);expanded_storage(argv[1],frametrail::DetectorModel::world_m,80);expanded_storage(argv[1],frametrail::DetectorModel::openimages,614);appearance_storage(argv[1]);seeking(argv[1]);}
        else if(argc==3)analysis(argv[1],argv[2]);else throw std::runtime_error("Expected fixtures, or source/model");
        std::cout<<"Saved-run contracts passed\n";return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
