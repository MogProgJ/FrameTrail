#pragma once
#include "frametrail/analysis_job.hpp"
#include "frametrail/preview_session.hpp"
#include <QMainWindow>
#include <QTimer>

class FrameCanvas;
class QLabel;
class QPushButton;
class QListWidget;
class EventTimeline;

class SavedRunWindow : public QMainWindow {
public:
    explicit SavedRunWindow(std::optional<frametrail::RunConfiguration> configuration = {});
    void start_analysis(const QString& database, frametrail::RunConfiguration configuration);
    void open_run(const QString& database);
    void review_event(int row);
    std::optional<std::chrono::microseconds> displayed_timestamp() const { return displayed_timestamp_; }
    bool analysing() const { return job_.progress().active; }
protected:
    void closeEvent(QCloseEvent* event) override;
private:
    void tick();
    void load_page(std::uint64_t after);
    void show_error(const std::exception& error);
    void toggle_playback();
    frametrail::AnalysisJob job_;
    frametrail::PreviewSession review_;
    std::optional<frametrail::RunConfiguration> configuration_;
    std::optional<frametrail::RunStore> store_;
    std::optional<frametrail::RunSummary> summary_;
    std::vector<frametrail::StoredEvent> page_;
    std::vector<std::uint64_t> cursors_{0};
    std::optional<frametrail::ReviewPosition> pending_review_;
    std::optional<frametrail::PreviewFrame> next_;
    std::optional<std::chrono::microseconds> displayed_timestamp_;
    QString database_;
    QTimer timer_;
    FrameCanvas* canvas_{};
    EventTimeline* timeline_{};
    QListWidget* events_{};
    QLabel* status_{};
    QLabel* source_{};
    QLabel* settings_{};
    QLabel* review_status_{};
    QPushButton* analyse_{};
    QPushButton* open_{};
    QPushButton* cancel_{};
    QPushButton* export_{};
    QPushButton* previous_{};
    QPushButton* more_{};
    QPushButton* play_{};
    bool closing_{}, awaiting_job_{}, awaiting_frame_{}, playing_{}, clock_started_{};
    std::chrono::steady_clock::time_point clock_,paused_;
    std::chrono::microseconds first_timestamp_{};
    std::uint64_t first_sequence_{};
};
