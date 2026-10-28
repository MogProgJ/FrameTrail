#pragma once

#include "frametrail/preview_session.hpp"
#include <QImage>
#include <QMainWindow>
#include <QTimer>
#include <chrono>
#include <functional>

class QDragEnterEvent;
class QDropEvent;
class QLabel;
class QPushButton;
class QCheckBox;
class QDoubleSpinBox;
class QComboBox;
class QPropertyAnimation;
class QStackedWidget;
class QShortcut;
class QPainter;
class SavedRunWindow;
class PlaybackWorkspace;
class LiveWindow;
class GuideWorkspace;
class HomeWorkspace;
class QSlider;

class FrameCanvas : public QWidget {
public:
    explicit FrameCanvas(QWidget* parent = nullptr);
    void set_image(QImage image, std::vector<frametrail::Detection> objects = {},
        std::vector<frametrail::TrackedObject> tracks = {}, std::optional<frametrail::CountingLine> line = {});
    void begin_line_selection();
    void cancel_line_selection(bool notify = true);
    void set_empty_text(QString text) {empty_text_=std::move(text);update();}
    void set_empty_icon(QString icon) {empty_icon_=std::move(icon);update();} // Fluent icon name, see studio_controls.hpp
    void set_temporal_style(bool enabled) {temporal_style_=enabled;update();}
    // Show only one object type; other boxes fade. Empty shows all.
    void set_focus_class(std::optional<int> id) {focus_class_=id;update();}
    [[nodiscard]] std::optional<int> focus_class() const {return focus_class_;}
    void set_ambient(bool enabled) {ambient_=enabled;update();} // Frame colours glow around the picture.
    // The current frame with boxes, labels, trails and counting line, at the frame's own resolution.
    [[nodiscard]] QImage annotated_image() const;
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
    void draw_overlays(QPainter& painter,const QRect& target) const;
    QImage image_;
    QImage glow_; // A few pixels wide; scaled up smoothly it becomes the ambient glow.
    std::optional<int> focus_class_;
    bool ambient_{true};
    std::vector<frametrail::Detection> objects_;
    std::vector<frametrail::TrackedObject> tracks_;
    std::optional<frametrail::CountingLine> line_;
    bool selecting_line_{};
    bool temporal_style_{};
    QString empty_text_{QStringLiteral("Open an image or video to begin")};
    QString empty_icon_{QStringLiteral("preview")};
    std::optional<frametrail::Point> first_point_;
};

class PreviewWindow : public QMainWindow {
public:
    explicit PreviewWindow(const QString& model_path = {});
    void open_file(const QString& path);
    void open_path(const QString& path); // Media opens in Preview, a saved .frametrail analysis in Analysis.
    void show_home();
    [[nodiscard]] std::optional<std::uint64_t> displayed_sequence() const { return displayed_sequence_; }
    [[nodiscard]] std::optional<std::chrono::microseconds> displayed_timestamp() const {
        return displayed_frame_ ? displayed_frame_->timestamp : std::nullopt;
    }
    [[nodiscard]] const QImage& preview_image() const { return canvas_->image(); }
    [[nodiscard]] bool playing() const { return playing_; }
    [[nodiscard]] const auto& detections() const { return canvas_->detections(); }
    [[nodiscard]] const auto& tracks() const { return canvas_->tracks(); }
    SavedRunWindow* analysis_workspace() const{return analysis_workspace_;}
    PlaybackWorkspace* playback_workspace() const{return playback_workspace_;}
    LiveWindow* camera_workspace() const{return camera_workspace_;}
protected:
    void closeEvent(QCloseEvent* event) override;
    void dragEnterEvent(QDragEnterEvent* event) override;
    void dropEvent(QDropEvent* event) override;
private:
    void tick();
    void toggle_playback();
    void stop_playback();
    void display(frametrail::PreviewFrame frame);
    void begin_pending_source();
    void reconfigure_analysis();
    void update_controls();
    void activate_workspace(int section);
    void begin_workspace_shutdown();
    void update_workspace_activity();
    void update_detector_status();
    void update_timeline();
    void seek_to(double fraction);
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
    QComboBox* backend_box_{};
    QPropertyAnimation* source_transition_{};
    QStackedWidget* workspace_pages_{};
    QShortcut* preview_play_shortcut_{};
    SavedRunWindow* analysis_workspace_{};
    PlaybackWorkspace* playback_workspace_{};
    LiveWindow* camera_workspace_{};
    GuideWorkspace* guide_workspace_{};
    HomeWorkspace* home_workspace_{};
    QSlider* timeline_{};
    QLabel *position_label_{},*duration_label_{},*in_view_{};
    std::optional<std::chrono::microseconds> pending_start_;
    std::optional<std::chrono::microseconds> media_start_,media_duration_;
    bool pause_after_seek_{};
    int workspace_section_{};
    bool workspace_close_requested_{},workspace_close_ready_{};
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
    bool finished_{}; // Reached the end: Play starts again from the beginning.
    bool closing_{};
    bool clock_started_{};
    std::chrono::steady_clock::time_point playback_start_;
    std::chrono::steady_clock::time_point pause_start_;
    std::chrono::microseconds first_timestamp_{};
};
