#include "preview_window.hpp"
#include <QApplication>
#include <QTimer>
#include <QComboBox>

int main(int argc, char* argv[]) {
    QApplication app(argc, argv);
    app.setApplicationName(QStringLiteral("FrameTrail"));
    PreviewWindow window;
    auto arguments = app.arguments();
    if(arguments.removeAll(QStringLiteral("--rf-experimental"))) {
        window.findChild<QComboBox*>(QStringLiteral("modelSelection"))->setCurrentIndex(5);
        window.findChild<QComboBox*>(QStringLiteral("backendSelection"))->setCurrentIndex(1);
        window.setWindowTitle(QStringLiteral("FrameTrail · RF trained 7758628 · experimental"));
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
    return app.exec();
}
