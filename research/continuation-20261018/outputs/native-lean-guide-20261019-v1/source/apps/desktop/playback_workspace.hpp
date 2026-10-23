#pragma once
#include "frametrail/detector.hpp"
#include <QWidget>
#include <QTimer>
#include <functional>
class CachedPlaybackWindow;
class QLabel;
class QPushButton;
class QVBoxLayout;
class FrameCanvas;

class PlaybackWorkspace : public QWidget {
public:
    PlaybackWorkspace(QString source,frametrail::DetectorOptions options,QWidget* parent=nullptr);
    std::function<std::pair<QString,frametrail::DetectorOptions>()> preview_selection;
    void select_video(QString source,frametrail::DetectorOptions options);
    CachedPlaybackWindow* cache() const {return cache_;}
    bool preparing() const;
    void suspend_playback();
    void request_shutdown();
    bool shutdown_complete() const;
private:
    void prepare();
    void tick();
    void refresh();
    QString source_;
    frametrail::DetectorOptions options_;
    CachedPlaybackWindow* cache_{};
    QLabel *source_label_{},*settings_label_{};
    FrameCanvas* empty_{};
    QPushButton *choose_{},*prepare_{},*use_preview_{};
    QVBoxLayout* content_{};
    QTimer timer_;
    bool replacing_{},resetting_{},closing_{};
};
