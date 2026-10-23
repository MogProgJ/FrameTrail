#include "cached_playback_window.hpp"
#include "playback_workspace.hpp"
#include "preview_window.hpp"
#include <QComboBox>
#include <QDoubleSpinBox>
#include <QPointer>
#include <QApplication>
#include <QLabel>
#include <QFontDatabase>
#include <QPushButton>
#include <QtTest/QTest>
#include <fstream>
#include <iostream>
#include <cmath>

namespace {
void require(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
template<class F>void wait(F f,int seconds=120){for(int i=0;i<seconds*200;++i){if(f())return;QTest::qWait(5);}throw std::runtime_error("Cached playback timed out");}
template<class F>void rejects(F f,const char* message){bool rejected=false;try{f();}catch(const std::exception&){rejected=true;}require(rejected,message);}
QString text(const std::filesystem::path& p){return QString::fromStdWString(p.wstring());}
void contracts(const std::filesystem::path& out){
    frametrail::Frame a;a.sequence=0;a.width=64;a.height=48;a.timestamp=std::chrono::microseconds(1234);
    auto b=a;b.sequence=1;b.timestamp.reset();
    const std::vector<frametrail::Detection> objects{{15,.73f,1,2,30,40},{16,.91f,4,5,50,44}};
    const auto path=out/"roundtrip.ftcache";
    {frametrail::OverlayCacheWriter w(path);w.record(a,objects);w.record(b,{});w.finish();rejects([&]{w.record(b,{});},"Sealed cache accepted writes");}
    rejects([&]{frametrail::OverlayCacheWriter w(path);},"Existing cache overwritten");
    {frametrail::OverlayCacheReader r(path);auto d=r.read(a);require(d.size()==2 && d[0].class_id==15 && d[0].confidence==objects[0].confidence && d[1].bottom==44,"Detection roundtrip changed");require(r.read(b).empty(),"Empty detection frame lost");r.verify_end();}
    {frametrail::OverlayCacheReader r(path);auto wrong=a;wrong.sequence=9;rejects([&]{r.read(wrong);},"Wrong frame sequence accepted");}
    {frametrail::OverlayCacheReader r(path);auto wrong=a;wrong.timestamp=std::chrono::microseconds(2);rejects([&]{r.read(wrong);},"Wrong frame timestamp accepted");}
    {frametrail::OverlayCacheReader r(path);r.read(a);rejects([&]{r.verify_end();},"Truncated source accepted");}
    const auto partial=out/"partial.ftcache";{frametrail::OverlayCacheWriter w(partial);w.record(a,objects);}
    rejects([&]{frametrail::OverlayCacheReader r(partial);},"Unsealed partial cache accepted");
    const auto bad=out/"bad-count.ftcache";std::filesystem::copy_file(path,bad);
    {std::fstream f(bad,std::ios::binary|std::ios::in|std::ios::out);f.seekp(40);const std::uint64_t count=999999999;f.write(reinterpret_cast<const char*>(&count),sizeof(count));}
    {frametrail::OverlayCacheReader r(bad);rejects([&]{r.read(a);},"Unbounded object count accepted");}
    std::cout<<"Cache format, exact frame identity, empty frames, exclusive output and partial/corrupt rejection passed\n";
}
}
int main(int argc,char** argv){
    QApplication app(argc,argv);
    QFontDatabase::addApplicationFont(qEnvironmentVariable("WINDIR")+QStringLiteral("/Fonts/segoeui.ttf"));app.setFont(QFont(QStringLiteral("Segoe UI"),10));
    try{
        if(argc<4)throw std::runtime_error("Need model, video, fresh output folder, optional rf");
        const std::filesystem::path model=argv[1],video=argv[2],out=argv[3];
        require(std::filesystem::create_directories(out),"Test output already exists");contracts(out);
        if(argc>4 && std::string_view(argv[4])=="integration") {
            PreviewWindow parent;parent.show();
            auto* models=parent.findChild<QComboBox*>(QStringLiteral("modelSelection"));models->setItemData(5,text(model));models->setCurrentIndex(5);
            parent.findChild<QComboBox*>(QStringLiteral("backendSelection"))->setCurrentIndex(1);
            parent.findChild<QDoubleSpinBox*>()->setValue(.70);parent.open_file(text(video));
            wait([&]{return parent.displayed_sequence().has_value();});
            auto* button=parent.findChild<QPushButton*>(QStringLiteral("smoothPlayback"));require(button && button->isEnabled(),"Smooth playback entry missing");button->click();
            require(!parent.playing(),"Original preview kept running alongside preparation");
            auto* workspace=parent.playback_workspace();require(workspace,"Playback section missing");
            workspace->findChild<QPushButton*>(QStringLiteral("preparePlayback"))->click();
            wait([&]{return workspace->cache()!=nullptr;});auto* child=workspace->cache();
            require(!child->isWindow(),"Playback escaped the shared window");
            wait([&]{return !child->preparing();});
            if(!child->prepared())throw std::runtime_error(child->findChild<QLabel*>(QStringLiteral("cacheStatus"))->text().toStdString());
            wait([&]{return child->displayed_sequence().has_value();});
            require(child->playing(),"Integrated cache did not play");
            parent.findChild<QPushButton*>(QStringLiteral("previewWorkspace"))->click();button->click();require(workspace->cache()==child,"Navigation duplicated preparation");
            require(parent.grab().save(text(out/"integrated-smooth-playback.png")),"Integration screenshot failed");
            parent.close();wait([&]{return !parent.isVisible();});require(workspace->shutdown_complete(),"Shared workspace closed before cache stopped");
            std::ofstream result(out/"result.json");result<<"{\"status\":\"passed\",\"main_window_to_embedded_playback\":true,\"parent_paused\":true,\"navigation_reuses_cache\":true,\"all_workers_stopped_on_close\":true}\n";
            std::cout<<"Shared-window RF/GPU playback, cache retention and shutdown passed\n";return 0;
        }
        const bool rf=argc>4 && std::string_view(argv[4])=="rf";
        const bool balanced=argc>4 && std::string_view(argv[4])=="balanced";
        frametrail::DetectorOptions options{model,argc>5?std::stof(argv[5]):.70f,.45f,balanced?frametrail::DetectorModel::rf_balanced7805570:(rf?frametrail::DetectorModel::rf_scale7758628:frametrail::DetectorModel::nano),rf?frametrail::DetectorBackend::directml:frametrail::DetectorBackend::cpu};
        {
            frametrail::PlaybackPreparation cancelled;cancelled.start(video,options,out/"cancelled.ftcache");cancelled.cancel();
            wait([&]{return !cancelled.progress().active;});require(cancelled.progress().state=="cancelled","Cancellation failed");
        }
        // Only this copied model is renamed; installed models are never modified.
        const auto copy=out/"test-model.onnx";std::filesystem::copy_file(model,copy);options.model=copy;
        const auto prep_start=std::chrono::steady_clock::now();
        CachedPlaybackWindow window(text(video),options);window.show();
        wait([&]{return !window.preparing();});
        if(!window.prepared()){QTest::qWait(30);throw std::runtime_error(window.findChild<QLabel*>(QStringLiteral("cacheStatus"))->text().toStdString());}
        const auto prep_seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-prep_start).count();
        wait([&]{return window.displayed_sequence().has_value();});
        require(window.prepared_frames()>1,"Too few prepared frames");
        const auto* play=window.findChild<QPushButton*>(QStringLiteral("cachePlay"));require(play && play->isEnabled(),"Prepared playback controls disabled");
        auto first=window.displayed_sequence();auto first_time=window.displayed_timestamp();auto previous=first;
        const auto start=std::chrono::steady_clock::now();
        std::ofstream data(out/"presentation.csv");data<<"sequence,source_us,wall_ms\n";data<<*first<<','<<first_time->count()<<",0\n";
        while(window.playing()){
            QTest::qWait(1);const auto ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
            if(ms>60000)throw std::runtime_error("Playback exceeded 60 seconds");
            if(window.displayed_sequence()!=previous){previous=window.displayed_sequence();data<<*previous<<','<<window.displayed_timestamp()->count()<<','<<ms<<'\n';}
        }
        require(window.displayed_sequence().value()+1==window.prepared_frames(),"Playback failed before final source frame");
        require(window.findChild<QLabel*>(QStringLiteral("cacheStatus"))->text().startsWith(QStringLiteral("Finished")),"Playback ended with error");
        std::filesystem::rename(copy,out/"model-unavailable.onnx");
        window.findChild<QPushButton*>(QStringLiteral("cacheReplay"))->click();
        wait([&]{return window.displayed_sequence().has_value() && *window.displayed_sequence()==0;});
        window.findChild<QPushButton*>(QStringLiteral("cachePlay"))->click();
        const auto paused=window.displayed_sequence();QTest::qWait(150);require(window.displayed_sequence()==paused,"Pause advanced frame");
        // Exact overlay parity with original inference on frame zero.
        frametrail::MediaReader reader(video);const auto frame=reader.read();auto original=options;original.model=model;frametrail::Detector detector(original);const auto expected=detector.detect(*frame);
        const auto& actual=window.detections();require(actual.size()==expected.objects.size(),"Cached object count differs from fresh inference");
        for(std::size_t i=0;i<actual.size();++i){const auto& a=actual[i];const auto& e=expected.objects[i];require(a.class_id==e.class_id && std::abs(a.confidence-e.confidence)<.0001f && std::abs(a.left-e.left)<.01f && std::abs(a.bottom-e.bottom)<.01f,"Cached overlays differ from inference");}
        require(window.grab().save(text(out/"smooth-playback.png")),"Screenshot failed");
        window.close();wait([&]{return !window.isVisible();});
        std::ofstream result(out/"result.json");result<<"{\"status\":\"passed\",\"preparation_seconds\":"<<prep_seconds<<",\"prepared_frames\":"<<window.prepared_frames()<<",\"cached_overlay_parity\":true,\"replay_without_model\":true,\"pause\":true,\"backend\":\""<<(rf?"DirectML":"CPU")<<"\"}\n";
        std::cout<<"Prepared playback, pause, replay without model, exact overlays and closing passed\n";return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
