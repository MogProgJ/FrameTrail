#pragma once

#include "frametrail/preview_session.hpp"
#include <QImage>
#include <QMainWindow>
#include <QTimer>
#include <chrono>

class QLabel;
class QPushButton;
class QCheckBox;
class QDoubleSpinBox;

class FrameCanvas : public QWidget {
public:
    explicit FrameCanvas(QWidget* parent = nullptr);
    void set_image(QImage image, std::vector<frametrail::Detection> objects = {});
    [[nodiscard]] const QImage& image() const { return image_; }
    [[nodiscard]] const auto& detections() const { return objects_; }
protected:
    void paintEvent(QPaintEvent*) override;
private:
    QImage image_;
    std::vector<frametrail::Detection> objects_;
};

class PreviewWindow : public QMainWindow {
public:
    explicit PreviewWindow(const QString& model_path = {});
    void open_file(const QString& path);
    [[nodiscard]] std::optional<std::uint64_t> displayed_sequence() const { return displayed_sequence_; }
    [[nodiscard]] const QImage& preview_image() const { return canvas_->image(); }
    [[nodiscard]] bool playing() const { return playing_; }
    [[nodiscard]] const auto& detections() const { return canvas_->detections(); }
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
    QCheckBox* detect_box_{};
    QDoubleSpinBox* confidence_box_{};
    QString model_path_;
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
