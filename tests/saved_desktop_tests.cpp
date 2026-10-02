#include "saved_run_window.hpp"
#include "preview_window.hpp"
#include <QApplication>
#include <QFontDatabase>
#include <QLabel>
#include <QListWidget>
#include <QPushButton>
#include <QtTest/QTest>
#include <fstream>
#include <iostream>

namespace {
void require(bool condition,const char* message) {if(!condition)throw std::runtime_error(message);}
template<class F> void wait(F function) {
    for(int i=0;i<2000;++i){if(function())return;QTest::qWait(5);}throw std::runtime_error("Saved review desktop timed out");
}
std::string bytes(const std::filesystem::path& path) {
    std::ifstream input(path,std::ios::binary);return {std::istreambuf_iterator<char>(input),{}};
}
QString text(const std::filesystem::path& path) {
    const auto value=path.u8string();return QString::fromUtf8(reinterpret_cast<const char*>(value.data()),qsizetype(value.size()));
}
}
int main(int argc,char* argv[]) {
    QApplication app(argc,argv);
    try {
        require(argc==4,"Expected fixture directory, source and model");
#ifdef _WIN32
        const auto fonts=qEnvironmentVariable("WINDIR")+QStringLiteral("/Fonts/");
        require(QFontDatabase::addApplicationFont(fonts+QStringLiteral("segoeui.ttf"))>=0,"System font missing");
        app.setFont(QFont(QStringLiteral("Segoe UI"),10));
#endif
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
        std::cout<<"Desktop saved review passed\n";return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
