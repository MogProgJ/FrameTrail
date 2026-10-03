#pragma once

#include "frametrail/preview_session.hpp"
#include <QImage>
#include <QMainWindow>
#include <QTimer>
#include <chrono>
#include <functional>

class QLabel;
class QPushButton;
class QCheckBox;
class QDoubleSpinBox;
class QComboBox;

class FrameCanvas : public QWidget {
public:
    explicit FrameCanvas(QWidget* parent = nullptr);
    void set_image(QImage image, std::vector<frametrail::Detection> objects = {},
        std::vector<frametrail::TrackedObject> tracks = {}, std::optional<frametrail::CountingLine> line = {});
    void begin_line_selection();
    void cancel_line_selection(bool notify = true);
    void set_empty_text(QString text) {empty_text_=std::move(text);update();}
    std::function<void(frametrail::CountingLine)> line_selected;
    std::function<void()> line_cancelled;
    [[nodiscard]] const QImage& image() const { return image_; }
    [[nodiscard]] const auto& detections() const { return objects_; }
    [[nodiscard]] const auto& tracks() const { return tracks_; }
    [[nodiscard]] const auto& counting_line() const { return line_; }
protected:
    void paintEvent(QPaintEvent*) override;
    void mousePressEvent(QMouseEvent*) override;
private:
    QRect image_rect() const;
    QImage image_;
    std::vector<frametrail::Detection> objects_;
    std::vector<frametrail::TrackedObject> tracks_;
    std::optional<frametrail::CountingLine> line_;
    bool selecting_line_{};
    QString empty_text_{QStringLiteral("Open an image or video to begin")};
    std::optional<frametrail::Point> first_point_;
};

class PreviewWindow : public QMainWindow {
public:
    explicit PreviewWindow(const QString& model_path = {});
    void open_file(const QString& path);
    [[nodiscard]] std::optional<std::uint64_t> displayed_sequence() const { return displayed_sequence_; }
    [[nodiscard]] std::optional<std::chrono::microseconds> displayed_timestamp() const {
        return displayed_frame_ ? displayed_frame_->timestamp : std::nullopt;
    }
    [[nodiscard]] const QImage& preview_image() const { return canvas_->image(); }
    [[nodiscard]] bool playing() const { return playing_; }
    [[nodiscard]] const auto& detections() const { return canvas_->detections(); }
    [[nodiscard]] const auto& tracks() const { return canvas_->tracks(); }
protected:
    void closeEvent(QCloseEvent* event) override;
private:
    void tick();
    void toggle_playback();
    void stop_playback();
    void display(frametrail::PreviewFrame frame);
    void begin_pending_source();
    void reconfigure_analysis();
    void update_controls();
    std::pair<std::optional<frametrail::DetectorOptions>, std::optional<frametrail::TrackingOptions>> analysis_options();

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
    QCheckBox* track_box_{};
    QComboBox* direction_box_{};
    QComboBox* model_box_{};
    QComboBox* classes_box_{};
    QPushButton* line_button_{};
    QLabel* counts_label_{};
    frametrail::CountingLine counting_line_;
    QString model_path_;
    QString source_;
    QString pending_source_;
    std::optional<frametrail::PreviewFrame> next_;
    std::optional<std::uint64_t> displayed_sequence_;
    std::optional<frametrail::Frame> displayed_frame_;
    std::uint64_t generation_{};
    std::uint64_t analysis_revision_{};
    std::uint64_t first_sequence_{};
    bool updating_{};
    bool resume_after_update_{};
    bool line_editing_{};
    bool resume_after_line_{};
    bool playing_{};
    bool stopped_{true};
    bool closing_{};
    bool clock_started_{};
    std::chrono::steady_clock::time_point playback_start_;
    std::chrono::steady_clock::time_point pause_start_;
    std::chrono::microseconds first_timestamp_{};
};
