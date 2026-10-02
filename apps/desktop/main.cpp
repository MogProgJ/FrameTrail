#include "preview_window.hpp"
#include <QApplication>

int main(int argc, char* argv[]) {
    QApplication app(argc, argv);
    app.setApplicationName(QStringLiteral("FrameTrail"));
    PreviewWindow window;
    window.show();
    const auto arguments = app.arguments();
    if (arguments.size() > 1) window.open_file(arguments[1]);
    return app.exec();
}
