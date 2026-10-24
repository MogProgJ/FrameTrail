#pragma once
#include <QWidget>
#include <functional>

class QLabel;
class QListWidget;
class QPushButton;
class QDragEnterEvent;
class QDropEvent;

// Start page: open or drop media, pick a tool, reopen recent files, see the detector setup.
class HomeWorkspace : public QWidget {
public:
    explicit HomeWorkspace(QWidget* parent=nullptr);
    std::function<void()> open_media, open_analysis;
    std::function<void(const QString&)> open_path;   // media opens in Preview, .frametrail in Analysis
    std::function<void(int section)> navigate;
    std::function<QStringList()> setup;              // detector summary: model, categories, device, confidence
    void refresh();
protected:
    void showEvent(QShowEvent* event) override;
    void dragEnterEvent(QDragEnterEvent* event) override;
    void dropEvent(QDropEvent* event) override;
private:
    QListWidget* recent_{};
    QLabel* recent_empty_{};
    QPushButton* clear_{};
    QLabel *model_{},*details_{};
};
