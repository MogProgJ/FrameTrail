#include "preview_window.hpp"
#include "saved_run_window.hpp"
#include <QApplication>
#include <QTimer>
#include <QComboBox>
#include <QFontDatabase>
#include <QLabel>
#include <QDoubleSpinBox>
#include <QListWidget>
#include <QPushButton>
#include <QtTest/QTest>
#include <fstream>
#include <iostream>
namespace {
void require(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
QString text(const std::filesystem::path& p){const auto s=p.u8string();return QString::fromUtf8(reinterpret_cast<const char*>(s.data()),qsizetype(s.size()));}
template<class F>void wait(F f){for(int i=0;i<24000;++i){if(f())return;QTest::qWait(5);}throw std::runtime_error("RF GUI workflow timed out");}
}
int main(int argc,char** argv){
    QApplication app(argc,argv);
    QTimer diagnostic;diagnostic.setInterval(10000);
    QObject::connect(&diagnostic,&QTimer::timeout,[&]{
        for(auto* window:QApplication::topLevelWidgets()) {
            std::cerr<<"TEST_WINDOW "<<window->metaObject()->className()<<" visible="<<window->isVisible()<<" modal="<<window->isModal()<<std::endl;
            for(auto* label:window->findChildren<QLabel*>())if(label->objectName()==QStringLiteral("analysisStatus") || label->objectName()==QStringLiteral("reviewStatus"))std::cerr<<label->objectName().toStdString()<<": "<<label->text().toStdString()<<std::endl;
        }
    });diagnostic.start();
    QTimer::singleShot(60000,&app,[]{std::cerr<<"TEST watchdog exceeded 60s"<<std::endl;std::exit(99);});
    try{
        require(QFontDatabase::addApplicationFont(qEnvironmentVariable("WINDIR")+QStringLiteral("/Fonts/segoeui.ttf"))>=0,"System font missing");
        app.setFont(QFont(QStringLiteral("Segoe UI"),10));

        if(argc==4 && std::string_view(argv[1])=="--benchmark") {
            const std::filesystem::path output=argv[3];std::filesystem::create_directories(output);
            PreviewWindow preview;preview.show();
            preview.findChild<QComboBox*>(QStringLiteral("modelSelection"))->setCurrentIndex(5);
            preview.findChild<QComboBox*>(QStringLiteral("backendSelection"))->setCurrentIndex(1);
            preview.findChild<QDoubleSpinBox*>()->setValue(.65);
            preview.open_file(QString::fromLocal8Bit(argv[2]));
            wait([&]{return preview.displayed_sequence().has_value();});
            bool gpu=false;for(auto* label:preview.findChildren<QLabel*>())if(label->text().contains(QStringLiteral("ms/frame")) && label->text().contains(QStringLiteral("· GPU")))gpu=true;
            require(gpu,"Preview benchmark silently used CPU");
            const auto start=std::chrono::steady_clock::now();
            std::ofstream data(output/"presentation.csv");data<<"sequence,source_us,wall_ms\n";
            auto previous=preview.displayed_sequence();
            data<<*previous<<','<<preview.displayed_timestamp()->count()<<",0\n";
            while(preview.displayed_sequence().value_or(0)<119){
                QTest::qWait(1);
                const auto elapsed=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
                if(elapsed>60000)throw std::runtime_error("Preview benchmark timed out");
                if(preview.displayed_sequence()!=previous){previous=preview.displayed_sequence();data<<*previous<<','<<preview.displayed_timestamp()->count()<<','<<elapsed<<'\n';}
            }
            require(preview.grab().save(text(output/"GPU-preview.png")),"GPU preview screenshot failed");
            preview.close();wait([&]{return !preview.isVisible();});
            std::cout<<"RF GPU preview presentation benchmark passed\n";return 0;
        }
        if(argc!=5 && argc!=6)throw std::runtime_error("Need model, PNG, short video, output directory and optional gpu");
        const bool gpu=argc==6 && std::string_view(argv[5])=="gpu";
        const bool balanced=argc==6 && std::string_view(argv[5])=="balanced";
        const auto variant=balanced ? frametrail::DetectorModel::rf_balanced7805570:frametrail::DetectorModel::rf_scale7758628;
        const std::filesystem::path model=argv[1],image=argv[2],video=argv[3],out=argv[4];std::filesystem::create_directories(out);
        {
            PreviewWindow preview;preview.show();
            auto* selector=preview.findChild<QComboBox*>(QStringLiteral("modelSelection"));
            require(selector && selector->count()==8,"RF not offered in model selector");
            require(selector->currentIndex()==1,"Existing default model changed");
            selector->setCurrentIndex(balanced ? 6:5);
            if(gpu)preview.findChild<QComboBox*>(QStringLiteral("backendSelection"))->setCurrentIndex(1);
            preview.open_file(text(image));
            wait([&]{return preview.displayed_sequence().has_value();});
            require(preview.grab().save(text(out/"rf-preview.png")),"RF preview screenshot failed");
            preview.close();
        }
        frametrail::RunConfiguration config;
        config.detector={model,.35f,.45f,variant,gpu ? frametrail::DetectorBackend::directml:frametrail::DetectorBackend::cpu};config.kind=frametrail::RunKind::appearances;config.tracking.line.reset();
        SavedRunWindow window(config);window.show();
        require(window.select_video(text(video)),"RF video selection failed");
        auto* analyse=window.findChild<QPushButton*>(QStringLiteral("saveAnalysis"));
        auto* save=window.findChild<QPushButton*>(QStringLiteral("saveRun"));
        require(analyse && analyse->isEnabled(),"RF analysis unavailable");analyse->click();
        wait([&]{return !window.analysing() && save->isEnabled();});
        auto* list=window.findChild<QListWidget*>(QStringLiteral("savedEvents"));require(list && list->count()>0,"RF appearances missing");
        require(window.grab().save(text(out/"rf-analysis.png")),"RF result screenshot failed");
        const auto database=out/"rf-local.frametrail";window.save_analysis(text(database));window.export_analysis_csv(text(out/"rf-local.csv"));
        frametrail::RunStore store(database);const auto summary=store.summary();
        require(summary.configuration.detector.variant==variant && summary.status=="completed" && summary.appearance_count>0,"RF saved model identity/status did not round-trip");
        require(summary.execution.provider==(gpu ? "DirectML":"CPU"),"RF saved actual execution provider differs");
        const auto bytes=frametrail::file_stamp(database);
        window.close();
        SavedRunWindow reopened;reopened.open_run(text(database));reopened.show();
        require(reopened.findChild<QListWidget*>(QStringLiteral("savedEvents"))->count()==list->count(),"RF saved review lost appearances");
        require(reopened.grab().save(text(out/"rf-reopened.png")),"RF reopened screenshot failed");
        require(frametrail::file_stamp(database)==bytes,"RF read-only review changed saved analysis");
        reopened.close();std::cout<<"RF GUI preview, analysis, save, CSV and reopen passed\n";return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
