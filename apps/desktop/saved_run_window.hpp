#pragma once
#include "frametrail/analysis_job.hpp"
#include "frametrail/preview_session.hpp"
#include <QMainWindow>
#include <QTemporaryDir>
#include <QTimer>
#include <functional>

class FrameCanvas;
class QLabel;
class QPushButton;
class QListWidget;
class QComboBox;
class QDoubleSpinBox;
class QProgressBar;
class QToolButton;
class QDragEnterEvent;
class QDropEvent;
class AppearanceTimeline;
class FlowLayout;

class SavedRunWindow : public QMainWindow {
public:
    explicit SavedRunWindow(std::optional<frametrail::RunConfiguration> configuration = {});
    bool select_video(const QString& video);
    void analyse_video();
    void save_analysis(const QString& output, bool replace = false);
    void export_analysis_csv(const QString& output, bool replace = false);
    void start_analysis(const QString& database, frametrail::RunConfiguration configuration);
    void open_run(const QString& database);
    void review_event(int row);
    std::optional<std::chrono::microseconds> displayed_timestamp() const { return displayed_timestamp_; }
    bool analysing() const { return job_.progress().active; }
    bool has_video() const { return !selected_video_.isEmpty() || store_.has_value(); }
    std::function<void(bool)> workspace_close_decision;
    void suspend_playback();
protected:
    void closeEvent(QCloseEvent* event) override;
    void dragEnterEvent(QDragEnterEvent* event) override;
    void dropEvent(QDropEvent* event) override;
private:
    void tick();
    void load_page(std::uint64_t after);
    void load_overview();                       // Chips per object type and the timeline chart.
    void select_appearance(std::uint64_t id);
    void show_error(const std::exception& error);
    void toggle_playback();
    void update_controls();
    bool confirm_discard();
    bool choose_save();
    QTemporaryDir scratch_; // Removed only after the workers and readers are destroyed.
    frametrail::AnalysisJob job_;
    frametrail::PreviewSession review_;
    std::optional<frametrail::RunConfiguration> configuration_;
    std::optional<frametrail::RunStore> store_;
    std::optional<frametrail::RunSummary> summary_;
    std::vector<frametrail::StoredEvent> page_; // Read-only compatibility for older crossing analyses.
    std::vector<frametrail::StoredAppearance> appearances_;
    std::vector<std::uint64_t> cursors_{0};
    std::optional<frametrail::ReviewPosition> pending_review_;
    std::optional<frametrail::PreviewFrame> next_;
    std::optional<std::chrono::microseconds> displayed_timestamp_;
    std::optional<std::uint64_t> preview_sequence_;
    std::optional<frametrail::Detection> review_box_;
    QString database_, selected_video_;
    QTimer timer_;
    FrameCanvas* canvas_{};
    QListWidget* events_{};
    QLabel *status_{}, *source_{}, *review_status_{}, *results_title_{};
    QPushButton *choose_{}, *analyse_{}, *open_{}, *cancel_{}, *save_{}, *export_{}, *previous_{}, *more_{}, *play_{}, *back_{};
    QComboBox* model_{};
    QDoubleSpinBox* confidence_{};
    QToolButton* settings_toggle_{};
    QWidget* settings_panel_{};
    QWidget* results_panel_{};
    QProgressBar* progress_{};
    AppearanceTimeline* timeline_{};
    QWidget* chips_{};
    FlowLayout* chips_layout_{};
    bool closing_{}, awaiting_job_{}, awaiting_frame_{}, playing_{}, clock_started_{}, unsaved_{}, draft_job_{},cancel_requested_{};
    std::chrono::steady_clock::time_point analysis_started_{};
    std::chrono::steady_clock::time_point clock_,paused_;
    std::chrono::microseconds first_timestamp_{};
    std::uint64_t first_sequence_{};
};
