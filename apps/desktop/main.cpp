#include "preview_window.hpp"
#include "cached_playback_window.hpp"
#include <QApplication>
#include <QTimer>
#include <QComboBox>
#include <QPushButton>
#include <QFontDatabase>
#include <QStyleHints>

int main(int argc, char* argv[]) {
    QApplication app(argc, argv);
    app.setStyle(QStringLiteral("Fusion"));
    // Windows 11 type face when installed (Windows 10 falls back to Segoe UI); dark title bar and palette.
    const auto family=QFontDatabase::hasFamily(QStringLiteral("Segoe UI Variable Text")) ? QStringLiteral("Segoe UI Variable Text") : QStringLiteral("Segoe UI");
    app.setFont(QFont(family,10));
    app.styleHints()->setColorScheme(Qt::ColorScheme::Dark);
    app.setApplicationName(QStringLiteral("FrameTrail"));
    PreviewWindow window;
    auto arguments = app.arguments();
    const bool smooth_mode=arguments.removeAll(QStringLiteral("--smooth-rf-experimental"))>0;
    if(arguments.removeAll(QStringLiteral("--rf-balanced"))) {
        window.findChild<QComboBox*>(QStringLiteral("modelSelection"))->setCurrentIndex(6);
        window.setWindowTitle(QStringLiteral("FrameTrail · balanced model preview"));
    }
    if(arguments.removeAll(QStringLiteral("--rf-experimental")) || smooth_mode) {
        window.findChild<QComboBox*>(QStringLiteral("modelSelection"))->setCurrentIndex(5);
        window.findChild<QComboBox*>(QStringLiteral("backendSelection"))->setCurrentIndex(1);
        window.setWindowTitle(QStringLiteral("FrameTrail · RF-DETR experimental"));
    }
    window.show();
    if (arguments.size() > 1 && arguments[1] == QStringLiteral("--smoke-test")) {
        if (arguments.size() != 3) return 2;
        // Packaging check: local-file decode, inference and Qt presentation only.
        window.open_file(arguments[2]);
        auto* poll = new QTimer(&window);
        QObject::connect(poll, &QTimer::timeout, &app, [&] {
            if (window.displayed_sequence().has_value()) app.exit(0);
        });
        poll->start(20);
        QTimer::singleShot(10000, &app, [&] { app.exit(1); });
    } else if (arguments.size() > 1) window.open_file(arguments[1]);
    if(smooth_mode){
        auto* prepare=new QTimer(&window);prepare->setInterval(20);
        QObject::connect(prepare,&QTimer::timeout,&window,[&window,prepare]{
            if(!window.displayed_sequence())return;
            prepare->stop();window.findChild<QPushButton*>(QStringLiteral("smoothPlayback"))->click();
            window.findChild<QPushButton*>(QStringLiteral("preparePlayback"))->click();
        });prepare->start();
    }
    return app.exec();
}
