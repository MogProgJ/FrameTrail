#include "cached_playback_window.hpp"
#include "saved_run_window.hpp"
#include "preview_window.hpp"
#include "processing_feedback.hpp"
#include <QApplication>
#include <QFontDatabase>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QLabel>
#include <QPushButton>
#include <QtTest/QTest>
#include <algorithm>
#include <fstream>
#include <iostream>

namespace {
using Clock=std::chrono::steady_clock;
double ms(Clock::time_point t){return std::chrono::duration<double,std::milli>(Clock::now()-t).count();}
void require(bool ok,const char* text){if(!ok)throw std::runtime_error(text);}
template<class F>void wait(F fn){for(int i=0;i<24000;++i){if(fn())return;QTest::qWait(5);}throw std::runtime_error("Workflow diagnostic timed out");}
QString text(const std::filesystem::path& p){return QString::fromStdWString(p.wstring());}
void capture(QWidget& w,const std::filesystem::path& p){require(w.grab().save(text(p)),"Screenshot failed");}
}
int main(int argc,char** argv){
    QApplication app(argc,argv);
    QFontDatabase::addApplicationFont(qEnvironmentVariable("WINDIR")+QStringLiteral("/Fonts/segoeui.ttf"));
    app.setStyle(QStringLiteral("Fusion"));app.setFont(QFont(QStringLiteral("Segoe UI"),10));
    if(argc<5)return 2;
    const std::filesystem::path video=argv[1],model=argv[2],out=argv[3];std::filesystem::create_directories(out);
    const bool balanced=std::string_view(argv[4])=="balanced";
    const bool fixed=argc>5 && std::string_view(argv[5])=="fixed";
    QJsonObject result;
    try{
        if(fixed){
            using namespace std::chrono;
            const auto unknown=processing_feedback(10,5.,{},{},{});require(!unknown.permille && !unknown.text.contains(QStringLiteral("about")),"Missing duration produced an ETA");
            const auto offset=processing_feedback(11,5.,seconds(100),seconds(105),seconds(10));require(offset.permille==500 && offset.text.contains(QStringLiteral("about 5s left")),"Timestamp origin changed the estimate");
            const auto early=processing_feedback(1,0.,seconds(0),seconds(0),seconds(10));require(!early.text.contains(QStringLiteral("about")),"First frame produced a premature ETA");
            const auto stalled=processing_feedback(10,5.,seconds(0),seconds(0),seconds(10));require(!stalled.text.contains(QStringLiteral("about")),"Stalled timestamps produced an ETA");
            FrameCanvas boxes;boxes.resize(400,300);QImage white(400,300,QImage::Format_RGB888);white.fill(Qt::white);
            boxes.set_image(white,{{15,.9f,20,80,170,250},{16,.8f,200,80,380,250}});boxes.show();
            require(boxes.grab().toImage().pixelColor(280,180)==QColor(Qt::white),"A detection label brush filled another box");boxes.close();
            result["feedback_and_box_contracts"]=true;
        }
        frametrail::DetectorOptions options{model,.65f,.45f,balanced?frametrail::DetectorModel::rf_balanced7805570:frametrail::DetectorModel::yolox_s,frametrail::DetectorBackend::cpu};
        const auto load=Clock::now();
        {frametrail::Detector detector(options);result["model_load_ms"]=ms(load);frametrail::MediaReader media(video);QJsonArray samples;
            for(int i=0;i<5;++i){auto frame=media.read();require(bool(frame),"Profile video too short");const auto d=detector.detect(*frame);samples.append(QJsonObject{{"total_ms",d.elapsed_ms},{"preprocess_ms",d.preprocess_ms},{"inference_ms",d.inference_ms},{"postprocess_ms",d.postprocess_ms}});}result["frame_samples"]=samples;}
        std::vector<double> gaps;auto previous=Clock::now();QTimer heartbeat;heartbeat.setInterval(10);
        QObject::connect(&heartbeat,&QTimer::timeout,[&]{auto now=Clock::now();gaps.push_back(std::chrono::duration<double,std::milli>(now-previous).count());previous=now;});heartbeat.start();
        {
            CachedPlaybackWindow cache(text(video),options);cache.show();
            wait([&]{return cache.prepared_frames()>=(fixed?10:3) || !cache.preparing();});require(cache.preparing(),"Cache finished before cancellation probe");
            if(fixed){auto* canvas=static_cast<FrameCanvas*>(cache.findChild<QWidget*>(QStringLiteral("frameCanvas")));require(!canvas->image().isNull(),"Preparation preview is missing");result["cache_preparation_preview"]=true;}
            capture(cache,out/"01-cache-preparing.png");cache.resize(800,560);QTest::qWait(25);capture(cache,out/"02-cache-compact.png");
            auto* label=cache.findChild<QLabel*>(QStringLiteral("cacheStatus"));
            result["cache_preparing_text"]=label->text();
            const auto start=Clock::now();cache.findChild<QPushButton*>(QStringLiteral("cacheCancel"))->click();
            result["cache_cancel_immediate_text"]=label->text();QTest::qWait(30);result["cache_cancel_after_30ms_text"]=label->text();
            if(fixed && cache.preparing())require(label->text().startsWith(QStringLiteral("Stopping")),"Cancellation feedback was overwritten");
            wait([&]{return !cache.preparing();});result["cache_cancel_ms"]=ms(start);QTest::qWait(20);
            result["cache_cancelled_text"]=label->text();result["cache_partial_frames"]=double(cache.prepared_frames());require(!cache.prepared() && label->text().contains(QStringLiteral("cancelled")),"Cancelled cache became playable");
            capture(cache,out/"03-cache-cancelled.png");cache.close();wait([&]{return !cache.isVisible();});
        }
        const auto partial=out/"partial.frametrail",csv=out/"partial.csv";
        {
            frametrail::RunConfiguration config{video,options,{}};config.kind=frametrail::RunKind::appearances;config.tracking.classes=frametrail::model_classes(options.variant);
            SavedRunWindow analysis(config);analysis.show();analysis.start_analysis(text(out/"working.frametrail"),config);
            auto* canvas=static_cast<FrameCanvas*>(analysis.findChild<QWidget*>(QStringLiteral("frameCanvas")));
            wait([&]{return !canvas->image().isNull() || !analysis.analysing();});require(analysis.analysing(),"Analysis finished before cancellation probe");
            capture(analysis,out/"04-analysis-running.png");auto* status=analysis.findChild<QLabel*>(QStringLiteral("analysisStatus"));
            const auto start=Clock::now();analysis.findChild<QPushButton*>(QStringLiteral("cancelAnalysis"))->click();result["analysis_cancel_immediate_text"]=status->text();
            QTest::qWait(30);result["analysis_cancel_after_30ms_text"]=status->text();
            if(fixed && analysis.analysing())require(status->text().startsWith(QStringLiteral("Stopping")),"Analysis cancellation feedback was overwritten");
            wait([&]{return !analysis.analysing() && analysis.findChild<QPushButton*>(QStringLiteral("saveRun"))->isEnabled();});result["analysis_cancel_ms"]=ms(start);
            analysis.save_analysis(text(partial));analysis.export_analysis_csv(text(csv));capture(analysis,out/"05-analysis-partial.png");analysis.close();wait([&]{return !analysis.isVisible();});
        }
        {frametrail::RunStore store(partial);const auto summary=store.summary();require(summary.status=="cancelled" && summary.processed_frames>0,"Saved partial result lost status or frames");result["partial_status"]=QString::fromStdString(summary.status);result["partial_frames"]=double(summary.processed_frames);result["partial_appearances"]=double(summary.appearance_count);}
        {SavedRunWindow reopened;reopened.show();reopened.open_run(text(partial));QTest::qWait(100);
            if(fixed)require(!reopened.findChild<QLabel*>(QStringLiteral("analysisStatus"))->text().contains(QStringLiteral("terminate")),"Cancellation leaked the runtime termination message");
            capture(reopened,out/"06-analysis-reopened.png");reopened.close();wait([&]{return !reopened.isVisible();});result["partial_reopened"]=true;}
        if(fixed){auto missing=options;missing.model=out/"missing-model.onnx";CachedPlaybackWindow failed(text(video),missing);failed.show();wait([&]{return !failed.preparing();});QTest::qWait(30);
            require(!failed.prepared() && failed.findChild<QLabel*>(QStringLiteral("cacheStatus"))->text().contains(QStringLiteral("failed")),"Missing-model failure was not explained");
            capture(failed,out/"07-cache-failed.png");failed.close();wait([&]{return !failed.isVisible();});result["missing_model_failure"]=true;}
        heartbeat.stop();std::sort(gaps.begin(),gaps.end());require(!gaps.empty(),"No heartbeat observations");result["ui_heartbeat_max_gap_ms"]=gaps.back();result["ui_heartbeat_p95_gap_ms"]=gaps[std::min(gaps.size()-1,gaps.size()*95/100)];result["ui_heartbeat_samples"]=double(gaps.size());result["status"]="passed";
    }catch(const std::exception& e){result["status"]="failed";result["error"]=QString::fromUtf8(e.what());}
    std::ofstream receipt(out/"result.json");receipt<<QJsonDocument(result).toJson().toStdString();std::cout<<QJsonDocument(result).toJson().toStdString();return result["status"]=="passed"?0:1;
}
