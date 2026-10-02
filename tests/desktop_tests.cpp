#include "preview_window.hpp"
#include <QApplication>
#include <QFontDatabase>
#include <QCheckBox>
#include <QLabel>
#include <QPushButton>
#include <QComboBox>
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
            QTest::qWait(30);
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
        wait_for([&] { return window.displayed_sequence().has_value(); });
        QTest::mouseClick(stop, Qt::LeftButton);
        const auto stopped_sequence = window.displayed_sequence();
        QTest::qWait(100);
        require(window.displayed_sequence() == stopped_sequence && !window.playing(), "Stop left presentation active");

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
