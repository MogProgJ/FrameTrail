#pragma once

#include "frametrail/preview_session.hpp"
#include <QImage>
#include <QMainWindow>
#include <QTimer>
#include <chrono>

class QLabel;
class QPushButton;

class FrameCanvas : public QWidget {
public:
    explicit FrameCanvas(QWidget* parent = nullptr);
    void set_image(QImage image);
    [[nodiscard]] const QImage& image() const { return image_; }
protected:
    void paintEvent(QPaintEvent*) override;
private:
    QImage image_;
};

class PreviewWindow : public QMainWindow {
public:
    PreviewWindow();
    void open_file(const QString& path);
    [[nodiscard]] std::optional<std::uint64_t> displayed_sequence() const { return displayed_sequence_; }
    [[nodiscard]] const QImage& preview_image() const { return canvas_->image(); }
    [[nodiscard]] bool playing() const { return playing_; }
protected:
    void closeEvent(QCloseEvent* event) override;
private:
    void tick();
    void toggle_playback();
    void stop_playback();
    void display(frametrail::PreviewFrame frame);
    void begin_pending_source();

    frametrail::PreviewSession session_;
    QTimer timer_;
    FrameCanvas* canvas_{};
    QLabel* source_label_{};
    QLabel* state_label_{};
    QLabel* details_label_{};
    QPushButton* play_button_{};
    QPushButton* stop_button_{};
    QPushButton* replay_button_{};
    QString source_;
    QString pending_source_;
    std::optional<frametrail::PreviewFrame> next_;
    std::optional<std::uint64_t> displayed_sequence_;
    std::uint64_t generation_{};
    bool playing_{};
    bool stopped_{true};
    bool closing_{};
    bool clock_started_{};
    std::chrono::steady_clock::time_point playback_start_;
    std::chrono::steady_clock::time_point pause_start_;
    std::chrono::microseconds first_timestamp_{};
};
