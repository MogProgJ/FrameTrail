#include "preview_window.hpp"
#include <QApplication>
#include <QFontDatabase>
#include <QCheckBox>
#include <QLabel>
#include <QPushButton>
#include <QComboBox>
#include <QDoubleSpinBox>
#include <QtTest/QTest>
#include <iostream>
#include <stdexcept>

namespace {
void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

template<class Predicate>
void wait_for(Predicate predicate) {
    for (int i = 0; i < 500; ++i) {
        if (predicate()) return;
        QTest::qWait(10);
    }
    throw std::runtime_error("Desktop preview timed out");
}
} // namespace

int main(int argc, char* argv[]) {
    QApplication app(argc, argv);
    try {
#ifdef _WIN32
        // The offscreen platform does not discover Windows fonts itself.
        // Use the installed system font for render checks; do not bundle it.
        const auto fonts = qEnvironmentVariable("WINDIR") + QStringLiteral("/Fonts/");
        require(QFontDatabase::addApplicationFont(fonts + QStringLiteral("segoeui.ttf")) >= 0,
            "Could not load the system font for offscreen rendering");
        QFontDatabase::addApplicationFont(fonts + QStringLiteral("seguisb.ttf"));
        app.setFont(QFont(QStringLiteral("Segoe UI"), 10));
#endif
        require(app.arguments().size() == 2 || app.arguments().size() == 3, "Expected fixture directory and optional detection sample");
        const auto root = app.arguments()[1];
        PreviewWindow window;
        window.findChild<QCheckBox*>(QStringLiteral("detectObjects"))->setChecked(false);
        window.show();
        auto* play = window.findChild<QPushButton*>(QStringLiteral("play"));
        auto* stop = window.findChild<QPushButton*>(QStringLiteral("stop"));
        auto* replay = window.findChild<QPushButton*>(QStringLiteral("replay"));
        auto* state = window.findChild<QLabel*>(QStringLiteral("state"));
        require(play && stop && replay && state, "Preview controls are missing");
        // Render an observed track and exercise line selection in an aspect-fit canvas.
        FrameCanvas canvas;
        canvas.resize(800,600); canvas.show();
        QImage image(1000,500,QImage::Format_RGB888); image.fill(QColor("#23354a"));
        const frametrail::Detection object{0,.9f,400,100,500,400};
        canvas.set_image(image,{object},{{7,object,true,{{.43,.7},{.45,.8}}}},frametrail::CountingLine{});
        require(canvas.grab().save(root+QStringLiteral("/desktop-tracking.png")),"Tracking screenshot failed");
        bool selected=false;
        canvas.line_selected=[&](frametrail::CountingLine line) {
            require(std::abs(line.a.x-.25)<.01 && std::abs(line.a.y-.25)<.01 &&
                std::abs(line.b.x-.75)<.01 && std::abs(line.b.y-.75)<.01,"Counting line coordinate transform failed");
            selected=true;
        };
        canvas.begin_line_selection();
        QTest::mouseClick(&canvas,Qt::LeftButton,{},QPoint(100,20)); // Outside the image.
        QTest::mouseClick(&canvas,Qt::LeftButton,{},QPoint(200,200));
        QTest::mouseClick(&canvas,Qt::LeftButton,{},QPoint(202,202)); // Too short.
        require(!selected,"Invalid counting line accepted");
        QTest::mouseClick(&canvas,Qt::LeftButton,{},QPoint(600,400));
        require(selected,"Two-click counting line did not finish");
        canvas.begin_line_selection();selected=false;
        QTest::mouseClick(&canvas,Qt::RightButton,{},QPoint(300,300));
        QTest::mouseClick(&canvas,Qt::LeftButton,{},QPoint(600,400));
        require(!selected,"Cancelled line selection completed");
        canvas.close();
        if (app.arguments().size()==3) {
            auto* detect=window.findChild<QCheckBox*>(QStringLiteral("detectObjects"));
            detect->setChecked(true);
            window.open_file(app.arguments()[2]);
            wait_for([&]{return window.displayed_sequence()==0 && !window.playing();});
            require(window.detections().size()>=2,"Desktop lost model detections");
            require(window.tracks().empty(),"Still image displayed track IDs");
            require(window.preview_image().width()==768 && window.preview_image().height()==576,
                "Detector reduced display resolution to its model input");
            require(window.grab().save(root+QStringLiteral("/desktop-detection.png")),"Detection screenshot failed");
            detect->setChecked(false);
            window.open_file(root+QStringLiteral("/still.png"));
            wait_for([&]{return window.displayed_sequence()==0 && !window.playing();});
            require(window.detections().empty(),"Disabling detection left stale boxes");
            require(window.tracks().empty(),"Disabling detection left stale track IDs");
            require(!window.findChild<QPushButton*>(QStringLiteral("drawLine"))->isEnabled(),"Counting controls enabled without detection");
            detect->setChecked(true);
            window.open_file(root+QStringLiteral("/variable.mkv"));
            wait_for([&]{return window.displayed_sequence().value_or(0)>=2 && window.playing();});
            QTest::mouseClick(stop,Qt::LeftButton);
            const auto position=window.displayed_sequence();
            const auto timestamp=window.displayed_timestamp();
            auto* draw=window.findChild<QPushButton*>(QStringLiteral("drawLine"));
            auto* video_canvas=window.findChild<QWidget*>(QStringLiteral("frameCanvas"));
            auto* track=window.findChild<QCheckBox*>(QStringLiteral("trackObjects"));
            auto* classes=window.findChild<QComboBox*>(QStringLiteral("trackingClasses"));
            auto* direction=window.findChild<QComboBox*>(QStringLiteral("crossingDirection"));
            const auto point=[&](double x,double y) {
                const auto scaled=window.preview_image().size().scaled(video_canvas->size(),Qt::KeepAspectRatio);
                return QPoint((video_canvas->width()-scaled.width())/2+int(x*scaled.width()),
                    (video_canvas->height()-scaled.height())/2+int(y*scaled.height()));
            };
            const auto applied=[&] {
                wait_for([&]{return state->text()==QStringLiteral("Paused") && play->isEnabled();});
                require(window.displayed_sequence()==position && window.displayed_timestamp()==timestamp && !window.playing(),
                    "Settings restarted or advanced paused playback");
            };
            QTest::mouseClick(draw,Qt::LeftButton);
            QTest::mouseClick(video_canvas,Qt::LeftButton,{},point(.2,.4));
            QTest::mouseClick(video_canvas,Qt::LeftButton,{},point(.8,.6));
            applied();
            classes->setCurrentIndex(1);applied();
            direction->setCurrentIndex(1);applied();
            track->setChecked(false);applied();
            require(window.tracks().empty(),"Tracking toggle retained obsolete IDs");
            track->setChecked(true);applied();
            detect->setChecked(false);applied();
            require(window.detections().empty(),"Detection toggle retained obsolete boxes");
            detect->setChecked(true);applied();
            window.findChild<QDoubleSpinBox*>(QStringLiteral("confidence"))->setValue(.45);applied();
            QTest::mouseClick(play,Qt::LeftButton);
            QTest::mouseClick(draw,Qt::LeftButton);
            const auto editing_position=window.displayed_sequence();
            QTest::qWait(120);
            require(!window.playing() && window.displayed_sequence()==editing_position,"Line selection did not freeze the frame");
            QTest::mouseClick(video_canvas,Qt::RightButton,{},point(.5,.5));
            require(window.playing() && window.displayed_sequence()==editing_position,"Cancelling line selection did not resume at held frame");
            QTest::mouseClick(draw,Qt::LeftButton);
            const auto line_position=window.displayed_sequence();
            QTest::mouseClick(video_canvas,Qt::LeftButton,{},point(.2,.6));
            QTest::mouseClick(video_canvas,Qt::LeftButton,{},point(.8,.4));
            wait_for([&]{return window.playing();});
            require(window.displayed_sequence()==line_position,"Applying line restarted playing video");
            track->setChecked(false);track->setChecked(true);direction->setCurrentIndex(2);
            wait_for([&]{return window.playing();});
            require(window.displayed_sequence().value_or(0)>=*line_position,"Rapid settings reset playback");
            window.close();
            wait_for([&]{return !window.isVisible();});
            PreviewWindow missing(root+QStringLiteral("/missing-model.onnx"));
            missing.findChild<QCheckBox*>(QStringLiteral("detectObjects"))->setChecked(true);
            missing.open_file(root+QStringLiteral("/still.png"));
            auto* error=missing.findChild<QLabel*>(QStringLiteral("state"));
            wait_for([&]{return error->text().startsWith(QStringLiteral("Could not read:"));});
            missing.findChild<QCheckBox*>(QStringLiteral("detectObjects"))->setChecked(false);
            wait_for([&]{return missing.displayed_sequence()==0 && !missing.playing();});
            std::cout << "Desktop detection checks passed: overlays, native resolution, toggle, cancellation, missing model recovery\n";
            return 0;
        }

        window.open_file(root + QStringLiteral("/variable.mkv"));
        wait_for([&] { return window.displayed_sequence().has_value(); });
        QTest::mouseClick(play, Qt::LeftButton);
        require(!window.playing(), "Pause did not stop presentation");
        const auto paused_sequence = window.displayed_sequence();
        QTest::qWait(180);
        require(window.displayed_sequence() == paused_sequence, "Frames advanced while paused");
        require(window.grab().save(root + QStringLiteral("/desktop-video.png")), "Video screenshot failed");
        QTest::mouseClick(play, Qt::LeftButton);
        wait_for([&] { return window.displayed_sequence() == 9 && !window.playing(); });
        require(state->text() == QStringLiteral("Finished"), "EOF was not shown");

        QTest::mouseClick(replay, Qt::LeftButton);
        wait_for([&] { return window.displayed_sequence().value_or(0)>=2; });
        QTest::mouseClick(stop, Qt::LeftButton);
        const auto stopped_sequence = window.displayed_sequence();
        QTest::qWait(100);
        require(window.displayed_sequence() == stopped_sequence && !window.playing(), "Stop left presentation active");
        require(play->isEnabled() && play->text()==QStringLiteral("Play"),"Stop disabled resume");
        const auto stopped_timestamp=window.displayed_timestamp();
        window.findChild<QDoubleSpinBox*>(QStringLiteral("confidence"))->setValue(.45);
        wait_for([&]{return play->isEnabled() && state->text()==QStringLiteral("Paused");});
        require(window.displayed_sequence()==stopped_sequence && window.displayed_timestamp()==stopped_timestamp,
            "Paused settings lost the exact source position");
        QTest::mouseClick(play,Qt::LeftButton);
        wait_for([&]{return window.displayed_sequence()>stopped_sequence;});
        require(window.displayed_sequence().value_or(0)>0,"Stop/resume replayed from frame zero");

        window.open_file(root + QStringLiteral("/invalid.txt"));
        wait_for([&] { return state->text().startsWith(QStringLiteral("Could not read:")); });
        window.open_file(root + QStringLiteral("/still.png"));
        wait_for([&] { return window.displayed_sequence() == 0 && !window.playing(); });
        require(window.preview_image().width() == 18 && window.preview_image().height() == 14,
            "Displayed image dimensions are incorrect");
        const auto pixel = window.preview_image().pixelColor(0, 0);
        require(pixel.red() > 240 && pixel.green() < 10, "Displayed pixels are incorrect");
        require(window.grab().save(root + QStringLiteral("/desktop-preview.png")), "Preview screenshot failed");

        // Rapid source replacement must not display an earlier source's frames.
        window.open_file(root + QStringLiteral("/delayed.mkv"));
        QTest::qWait(30);
        window.open_file(root + QStringLiteral("/still.png"));
        wait_for([&] { return window.displayed_sequence() == 0 && !window.playing(); });
        require(window.preview_image().width() == 18, "A stale source frame reached the display");

        window.open_file(root + QStringLiteral("/variable.mkv"));
        QTest::qWait(30);
        window.close();
        wait_for([&] { return !window.isVisible(); });
        std::cout << "Desktop checks passed: render, pause, resume, EOF, replay, stop, errors, replacement, close\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
