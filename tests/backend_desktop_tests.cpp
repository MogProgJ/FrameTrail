#include "preview_window.hpp"
#include "saved_run_window.hpp"
#include <QApplication>
#include <QFontDatabase>
#include <QComboBox>
#include <QCheckBox>
#include <QLabel>
#include <QPushButton>
#include <QtTest/QTest>
#include <iostream>

namespace {
void require(bool value,const char* message){if(!value)throw std::runtime_error(message);}
template<class F> void wait(F condition){for(int i=0;i<3000;++i){if(condition())return;QTest::qWait(5);}throw std::runtime_error("GPU desktop check timed out");}
QString text(const std::filesystem::path& path){const auto value=path.u8string();return QString::fromUtf8(reinterpret_cast<const char*>(value.data()),qsizetype(value.size()));}
}
int main(int argc,char** argv) {
    QApplication app(argc,argv);
    try {
        require(argc==4,"Expected fixtures/sample/model");
        QFontDatabase::addApplicationFont(qEnvironmentVariable("WINDIR")+QStringLiteral("/Fonts/segoeui.ttf"));
        app.setFont(QFont(QStringLiteral("Segoe UI"),10));
        const auto root=std::filesystem::path(argv[1])/("gpu-ui-"+std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));std::filesystem::create_directory(root);
        PreviewWindow window(text(argv[3]));window.show();window.open_file(text(argv[2]));
        auto* details=window.findChild<QLabel*>(QStringLiteral("details"));auto* backend=window.findChild<QComboBox*>(QStringLiteral("backendSelection"));
        require(backend && backend->currentIndex()==0,"CPU default or backend selector was lost");
        wait([&]{return window.displayed_sequence().has_value() && !window.playing();});
        const auto sequence=window.displayed_sequence();const auto timestamp=window.displayed_timestamp();const auto size=window.preview_image().size();
        backend->setCurrentIndex(1);wait([&]{return details->text().contains(QStringLiteral("GPU")) && window.findChild<QPushButton*>(QStringLiteral("play"))->isEnabled();});
        require(window.displayed_sequence()==sequence && window.displayed_timestamp()==timestamp && window.preview_image().size()==size && !window.playing(),"GPU switching changed paused source identity/resolution");
        require(details->toolTip().contains(QStringLiteral("DirectML")) && details->toolTip().contains(QStringLiteral("1.24.4")),"GUI hid the actual GPU provider");
        require(window.grab().save(text(root/"player-gpu.png")),"GPU workspace capture failed");
        window.resize(900,600);QTest::qWait(30);require(window.grab().save(text(root/"player-gpu-compact.png")),"Compact GPU workspace capture failed");
        backend->setCurrentIndex(0);wait([&]{return details->text().contains(QStringLiteral("CPU")) && window.findChild<QPushButton*>(QStringLiteral("play"))->isEnabled();});
        require(window.displayed_sequence()==sequence && window.displayed_timestamp()==timestamp,"CPU switching restarted media");
        window.close();wait([&]{return !window.isVisible();});
        frametrail::RunConfiguration config;config.source=std::filesystem::path(argv[1])/"review.mkv";config.detector.model=argv[3];config.detector.backend=frametrail::DetectorBackend::automatic;
        SavedRunWindow analysis(config);analysis.show();analysis.analyse_video();
        auto* save=analysis.findChild<QPushButton*>(QStringLiteral("saveRun"));wait([&]{return !analysis.analysing() && save->isEnabled();});
        analysis.save_analysis(text(root/"analysis.frametrail"));analysis.export_analysis_csv(text(root/"analysis.csv"));
        const auto summary=frametrail::RunStore(root/"analysis.frametrail").summary();
        require(summary.status=="completed" && summary.processed_frames==6 && summary.execution.provider=="DirectML" && summary.appearance_count>=3,"Saved-analysis GPU preference or ordered pipeline was lost");
        wait([&]{return analysis.displayed_timestamp().has_value();});
        require(!analysis.findChild<QComboBox*>(QStringLiteral("backendSelection")),"Saved-analysis layout gained device controls");
        require(analysis.grab().save(text(root/"analysis-gpu.png")),"Saved-analysis capture failed");
        analysis.close();wait([&]{return !analysis.isVisible();});
        std::cout<<"GPU desktop switching, source continuity and unchanged analysis flow passed; captures: "<<root.string()<<'\n';return 0;
    }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
