#pragma once
#include "frametrail/playback_cache.hpp"
#include "frametrail/preview_session.hpp"
#include <QMainWindow>
#include <QTemporaryDir>
#include <QTimer>

class FrameCanvas;
class QLabel;
class QPushButton;
class QProgressBar;
class CachedPlaybackWindow : public QMainWindow {
public:
    CachedPlaybackWindow(const QString& source,frametrail::DetectorOptions options);
    bool prepared() const { return preparation_.progress().state=="completed"; }
    bool preparing() const { return preparation_.progress().active; }
    bool playing() const { return playing_; }
    std::optional<std::uint64_t> displayed_sequence() const {return displayed_sequence_;}
    std::optional<std::chrono::microseconds> displayed_timestamp() const {return displayed_timestamp_;}
    std::uint64_t prepared_frames() const {return preparation_.progress().frames;}
    const std::vector<frametrail::Detection>& detections() const;
protected:
    void closeEvent(QCloseEvent*) override;
private:
    void tick();
    void replay();
    void fail(const std::exception& error);
    QTemporaryDir scratch_; // Removed after both workers and cache reader close.
    frametrail::PlaybackPreparation preparation_;
    frametrail::PreviewSession decoder_;
    std::unique_ptr<frametrail::OverlayCacheReader> overlays_;
    std::filesystem::path source_,cache_;
    std::optional<frametrail::PreviewFrame> next_;
    FrameCanvas* canvas_{};
    QLabel* status_{};
    QProgressBar* progress_{};
    QPushButton *play_{},*replay_{},*cancel_{};
    QTimer timer_;
    bool ready_{},playing_{},closing_{},restart_{},clock_started_{},preparation_done_{};
    std::chrono::steady_clock::time_point clock_,paused_;
    std::chrono::microseconds first_timestamp_{};
    std::uint64_t first_sequence_{};
    std::optional<std::uint64_t> displayed_sequence_;
    std::optional<std::chrono::microseconds> displayed_timestamp_;
};
