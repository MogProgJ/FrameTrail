#include "saved_run_window.hpp"
#include "preview_window.hpp"
#include <QComboBox>
#include <QApplication>
#include <QFontDatabase>
#include <QLabel>
#include <QMimeData>
#include <QDragEnterEvent>
#include <QDropEvent>
#include <QUrl>
#include <QProgressBar>
#include <QMessageBox>
#include <QTimer>
#include <QListWidget>
#include <QPushButton>
#include <QtTest/QTest>
#include <fstream>
#include <iostream>

namespace {
void require(bool condition,const char* message) {if(!condition)throw std::runtime_error(message);}
template<class F> void wait(F function,const char* stage="Saved review desktop") {
    for(int i=0;i<6000;++i){if(function())return;QTest::qWait(5);}throw std::runtime_error(std::string(stage)+" timed out");
}
std::string bytes(const std::filesystem::path& path) {
    std::ifstream input(path,std::ios::binary);return {std::istreambuf_iterator<char>(input),{}};
}
QString text(const std::filesystem::path& path) {
    const auto value=path.u8string();return QString::fromUtf8(reinterpret_cast<const char*>(value.data()),qsizetype(value.size()));
}
template<class F> void fails(F function,const char* message) {
    try{function();}catch(const std::exception&){return;}throw std::runtime_error(message);
}
void intake(const std::filesystem::path& fixtures,const std::filesystem::path& source,const std::filesystem::path& model) {
    const auto root=fixtures/("intake-ui-"+std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    std::filesystem::create_directory(root);const auto video=root/std::filesystem::path(u8"vidéo, 影.mkv");std::filesystem::copy_file(source,video);
    frametrail::RunConfiguration config{{},{model},{}};
    SavedRunWindow window(config);window.set_review_folder(text(root/"reviews"));window.show();
    auto* analyse=window.findChild<QPushButton*>(QStringLiteral("saveAnalysis"));
    auto* save=window.findChild<QPushButton*>(QStringLiteral("saveRun"));
    auto* list=window.findChild<QListWidget*>(QStringLiteral("savedEvents"));
    auto* status=window.findChild<QLabel*>(QStringLiteral("analysisStatus"));
    require(analyse && !analyse->isEnabled() && !save->isVisible(),"Empty analysis needs player setup or exposes result actions");
    require(window.grab().save(text(root/"analysis-empty.png")),"Empty analysis screenshot failed");
    QMimeData remote;remote.setUrls({QUrl(QStringLiteral("https://example.invalid/video.mp4"))});
    QDragEnterEvent remote_event(QPoint(150,150),Qt::CopyAction,&remote,Qt::LeftButton,Qt::NoModifier);QApplication::sendEvent(&window,&remote_event);
    require(!remote_event.isAccepted(),"Remote drop was accepted");
    QMimeData multiple;multiple.setUrls({QUrl::fromLocalFile(text(video)),QUrl::fromLocalFile(text(video))});
    QDragEnterEvent multiple_event(QPoint(150,150),Qt::CopyAction,&multiple,Qt::LeftButton,Qt::NoModifier);QApplication::sendEvent(&window,&multiple_event);
    require(!multiple_event.isAccepted(),"Multiple drop was accepted");
    QMimeData mime;mime.setUrls({QUrl::fromLocalFile(text(video))});
    QDragEnterEvent drag(QPoint(150,150),Qt::CopyAction,&mime,Qt::LeftButton,Qt::NoModifier);QApplication::sendEvent(&window,&drag);
    require(drag.isAccepted(),"Local video drag was rejected");
    QDropEvent drop(QPointF(150,150),Qt::CopyAction,&mime,Qt::LeftButton,Qt::NoModifier);QApplication::sendEvent(&window,&drop);
    require(drop.isAccepted() && analyse->isEnabled(),"Local Unicode video drop did not prepare analysis");
    analyse->click();require(window.analysing() && !analyse->isEnabled() && window.findChild<QProgressBar*>(QStringLiteral("analysisProgress"))->isVisible(),"Analysis did not enter progress state");
    QDragEnterEvent busy(QPoint(150,150),Qt::CopyAction,&mime,Qt::LeftButton,Qt::NoModifier);QApplication::sendEvent(&window,&busy);require(!busy.isAccepted(),"Busy analysis accepted a replacement drop");
    wait([&]{return !window.analysing() && (save->isEnabled() || window.findChild<QPushButton*>(QStringLiteral("chooseVideo"))->isEnabled());},"Unicode-source analysis finalization");
    require(save->isEnabled(),status->text().toUtf8().constData());
    require(list->count()>0 && status->text().contains(QStringLiteral("completed")),"Appearance results were not presented");
    wait([&]{return window.displayed_timestamp().has_value();},"First reviewed Unicode-source frame");
    // Review mode: verdicts, auto-advance, progress text, export, and restore after reopening (below).
    require(!window.verdict(0) && window.review_summary().contains(QStringLiteral("Not reviewed")),"Fresh analysis already had verdicts");
    window.set_verdict(0,true,true);
    require(window.verdict(0)==std::optional<bool>(true) && list->currentRow()==std::min(1,list->count()-1),"Correct verdict was not stored or did not advance");
    if(list->count()>1){window.set_verdict(1,false);require(window.verdict(1)==std::optional<bool>(false),"Wrong verdict was not stored");}
    require(window.review_summary().contains(QStringLiteral("Reviewed")) || window.review_summary().contains(QStringLiteral("All reviewed")),"Review progress missing");
    window.export_review_csv(text(root/"review.csv"));
    require(bytes(root/"review.csv").find(",correct\r\n")!=std::string::npos,"Review CSV lacks the verdicts");
    require(window.grab().save(text(root/"analysis-results.png")),"Results screenshot failed");
    window.resize(920,620);QTest::qWait(25);require(window.grab().save(text(root/"analysis-compact.png")),"Compact analysis screenshot failed");window.resize(1240,820);
    bool prompt_seen=false;
    QTimer::singleShot(20,[&]{if(auto* message=qobject_cast<QMessageBox*>(QApplication::activeModalWidget())){prompt_seen=true;message->button(QMessageBox::Cancel)->click();}});
    require(!window.select_video(text(video)) && prompt_seen && list->count()>0,"Discard prompt did not preserve unsaved results on Cancel");
    const auto saved=root/"analysis.frametrail",csv=root/"analysis.csv";
    window.save_analysis(text(saved));window.export_analysis_csv(text(csv));
    const auto saved_bytes=bytes(saved),csv_bytes=bytes(csv);
    require(csv_bytes.starts_with("\xef\xbb\xbfObject,Appearance ID") && csv_bytes.find("\r\n")!=std::string::npos,"GUI exported crossing CSV or lost Excel formatting");
    {frametrail::RunStore result(saved);const auto summary=result.summary();require(summary.configuration.kind==frametrail::RunKind::appearances && summary.appearance_count>0 && !summary.configuration.tracking.line,"Saved appearance pipeline retained counting-line dependence");}
    fails([&]{window.save_analysis(text(saved));},"Save replaced an existing result without authorization");
    fails([&]{window.export_analysis_csv(text(csv));},"CSV replaced existing output without authorization");
    fails([&]{window.save_analysis(text(video),true);},"Save overwrote video");
    fails([&]{window.export_analysis_csv(text(model),true);},"Export overwrote model");
    require(bytes(saved)==saved_bytes && bytes(csv)==csv_bytes,"Failed save/export modified existing outputs");
    window.save_analysis(text(saved),true);require(bytes(saved)==saved_bytes,"Confirmed replacement changed results");
    window.close();wait([&]{return !window.isVisible();});
    SavedRunWindow reopened;reopened.set_review_folder(text(root/"reviews"));reopened.show();reopened.open_run(text(saved));
    auto* reopened_list=reopened.findChild<QListWidget*>(QStringLiteral("savedEvents"));require(reopened_list->count()==list->count(),"Reopening lost appearances");
    require(reopened.verdict(0)==std::optional<bool>(true) && (reopened_list->count()<2 || reopened.verdict(1)==std::optional<bool>(false)),"Reopening lost review verdicts");
    fails([&]{reopened.export_analysis_csv(text(saved),true);},"CSV export replaced the working analysis database");
    wait([&]{return reopened.displayed_timestamp().has_value();});
    require(bytes(saved)==saved_bytes,"Review wrote to saved analysis");reopened.close();wait([&]{return !reopened.isVisible();});
    std::filesystem::rename(video,root/"moved.mkv");
    SavedRunWindow missing;missing.show();missing.open_run(text(saved));
    require(!missing.displayed_timestamp() && !missing.findChild<QListWidget*>(QStringLiteral("savedEvents"))->item(0)->icon().isNull(),"Missing video lost stored thumbnail");
    require(missing.findChild<QLabel*>(QStringLiteral("reviewStatus"))->text().contains(QStringLiteral("missing")),"Missing video was not explained");missing.close();wait([&]{return !missing.isVisible();});
    std::filesystem::rename(root/"moved.mkv",video);
    const auto smooth=fixtures/"smooth.mkv";
    if(std::filesystem::exists(smooth)) {
        SavedRunWindow partial(config);partial.show();partial.select_video(text(smooth));partial.analyse_video();
        auto* canvas=static_cast<FrameCanvas*>(partial.findChild<QWidget*>(QStringLiteral("frameCanvas")));
        wait([&]{return !canvas->image().isNull();});partial.findChild<QPushButton*>(QStringLiteral("cancelAnalysis"))->click();
        auto* keep=partial.findChild<QPushButton*>(QStringLiteral("saveRun"));wait([&]{return !partial.analysing() && keep->isEnabled();});
        const auto partial_file=root/"partial.frametrail";partial.save_analysis(text(partial_file));
        require(frametrail::RunStore(partial_file).summary().status=="cancelled" && frametrail::RunStore(partial_file).summary().processed_frames>0,"Cancellation lost partial progress or became complete");
        partial.close();wait([&]{return !partial.isVisible();});
        SavedRunWindow closing(config);closing.show();closing.select_video(text(smooth));closing.analyse_video();
        auto* closing_canvas=static_cast<FrameCanvas*>(closing.findChild<QWidget*>(QStringLiteral("frameCanvas")));
        wait([&]{return !closing_canvas->image().isNull();});
        bool close_prompt=false;QTimer response;response.setInterval(5);
        QObject::connect(&response,&QTimer::timeout,[&]{if(auto* message=qobject_cast<QMessageBox*>(QApplication::activeModalWidget())){close_prompt=true;response.stop();message->button(QMessageBox::Cancel)->click();}});
        response.start();closing.close();wait([&]{return close_prompt;});
        require(closing.isVisible() && closing.findChild<QPushButton*>(QStringLiteral("saveRun"))->isEnabled(),"Closing active analysis discarded partial results without a choice");
        closing.save_analysis(text(root/"closed-partial.frametrail"));closing.close();wait([&]{return !closing.isVisible();});
    }
    SavedRunWindow retry(config);retry.show();retry.select_video(text(fixtures/"invalid.txt"));retry.analyse_video();
    wait([&]{return !retry.analysing() && retry.findChild<QPushButton*>(QStringLiteral("chooseVideo"))->isEnabled();});
    require(!retry.findChild<QPushButton*>(QStringLiteral("saveRun"))->isVisible(),"Invalid input presented a saved result");retry.close();wait([&]{return !retry.isVisible();});
    {   // The frame step is offered and restored from a run's configuration.
        auto stepped=config;stepped.tracking.frame_step=3;SavedRunWindow sampled(stepped);
        auto* step=sampled.findChild<QComboBox*>(QStringLiteral("analysisFrameStep"));
        require(step && step->count()==4 && step->currentData().toInt()==3,"Frame step option missing or not restored");
    }
    std::cout<<"Appearance intake passed; private artifacts: "<<root.string()<<'\n';
}

}
int main(int argc,char* argv[]) {
    QApplication app(argc,argv);
    try {
        require(argc==4 || (argc==5 && std::string_view(argv[4])=="--intake-only"),"Expected fixtures/source/model and optional intake mode");
#ifdef _WIN32
        const auto fonts=qEnvironmentVariable("WINDIR")+QStringLiteral("/Fonts/");
        require(QFontDatabase::addApplicationFont(fonts+QStringLiteral("segoeui.ttf"))>=0,"System font missing");
        app.setFont(QFont(QStringLiteral("Segoe UI"),10));
#endif
        if(argc==5){intake(argv[1],argv[2],argv[3]);return 0;}
        const auto root=std::filesystem::path(argv[1])/("review-ui-"+std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
        std::filesystem::create_directory(root);const auto source=root/"review.mkv",database=root/"review.frametrail";
        std::filesystem::copy_file(argv[2],source);
        frametrail::RunConfiguration config{source,{argv[3]},{}};config.tracking.classes={16};
        config.tracking.line->a={.1,.75};config.tracking.line->b={.9,.75};
        auto first_window=std::make_unique<SavedRunWindow>(config);auto& window=*first_window;
        window.show();window.start_analysis(text(database),config);
        auto* list=window.findChild<QListWidget*>(QStringLiteral("savedEvents"));
        wait([&]{return !window.analysing() && list->count()==1;});
        require(window.findChild<QLabel*>(QStringLiteral("analysisStatus"))->text().contains(QStringLiteral("completed")),"Desktop did not open completed run");
        const auto unchanged=bytes(database);
        QTest::mouseClick(list->viewport(),Qt::LeftButton,{},list->visualItemRect(list->item(0)).center());
        wait([&]{return window.displayed_timestamp()==std::chrono::microseconds(400000);});
        require(static_cast<FrameCanvas*>(window.findChild<QWidget*>(QStringLiteral("frameCanvas")))->image().size()==QSize(1000,1000),"Review displayed thumbnail instead of original source frame");
        auto* play=window.findChild<QPushButton*>(QStringLiteral("reviewPlay"));require(play->isEnabled(),"Review playback unavailable");
        QTest::mouseClick(play,Qt::LeftButton);wait([&]{return window.displayed_timestamp()==std::chrono::microseconds(500000);});
        window.review_event(0);wait([&]{return window.displayed_timestamp()==std::chrono::microseconds(400000);});
        require(window.grab().save(text(root/"saved-review.png")),"Could not render saved review screenshot");
        window.close();wait([&]{return !window.isVisible();});
        first_window.reset();std::filesystem::rename(source,root/"moved.mkv");
        SavedRunWindow reopened;reopened.show();reopened.open_run(text(database));
        auto* events=reopened.findChild<QListWidget*>(QStringLiteral("savedEvents"));require(events->count()==1 && !events->item(0)->icon().isNull(),"Reopen lost event/thumbnail");
        reopened.review_event(0);QTest::qWait(30);
        require(!reopened.displayed_timestamp() && reopened.findChild<QLabel*>(QStringLiteral("reviewStatus"))->text().contains(QStringLiteral("missing")),"Missing source did not produce useful review error");
        require(!static_cast<FrameCanvas*>(reopened.findChild<QWidget*>(QStringLiteral("frameCanvas")))->image().isNull(),"Missing source lost thumbnail");
        std::filesystem::rename(root/"moved.mkv",source);reopened.review_event(0);
        wait([&]{return reopened.displayed_timestamp()==std::chrono::microseconds(400000);});
        require(bytes(database)==unchanged,"Desktop seek/play/reopen modified analysis database");
        reopened.close();wait([&]{return !reopened.isVisible();});
        // 60 FPS must follow presentation time, not the old one-frame/20 ms ceiling.
        const auto smooth=std::filesystem::path(argv[1])/"smooth.mkv",smooth_run=root/"smooth.frametrail";
        {
            frametrail::MediaReader reader(smooth);auto frame=reader.read();auto timing_config=config;timing_config.source=smooth;
            auto saved=frametrail::RunStore::create(smooth_run,timing_config,reader.info());
            const std::vector<frametrail::CrossingEvent> marker{{1,1,frame->sequence,frame->timestamp,0,frametrail::CrossingDirection::negative_to_positive,{.5,.5}}};
            saved.record_frame(*frame,marker);saved.finish("completed");
        }
        SavedRunWindow timing;timing.show();timing.open_run(text(smooth_run));timing.review_event(0);
        wait([&]{return timing.displayed_timestamp()==std::chrono::microseconds(0);});
        auto* timing_play=timing.findChild<QPushButton*>(QStringLiteral("reviewPlay"));timing_play->click();
        QTest::qWait(1000);
        require(timing.displayed_timestamp() && timing.displayed_timestamp()->count()>=900000,"60 FPS review fell behind its presentation clock");
        QTest::qSleep(200);QTest::qWait(120);
        require(timing.displayed_timestamp()->count()>=1200000,"Review did not catch up after a delayed UI tick");
        timing_play->click();const auto paused=timing.displayed_timestamp();QTest::qWait(100);
        require(timing.displayed_timestamp()==paused,"Review pause advanced the source");
        timing.close();wait([&]{return !timing.isVisible();});
        std::cout<<"Desktop saved review passed\n";return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
