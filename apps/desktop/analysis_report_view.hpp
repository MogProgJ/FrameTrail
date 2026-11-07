#pragma once
#include "frametrail/analysis_report.hpp"
#include <QScrollArea>
#include <QWidget>
#include <functional>
#include <optional>

class QLabel;
class QListWidget;
class QTableWidget;
class QVBoxLayout;
class FlowLayout;

// Objects visible over time, stacked by the most frequent types, with scene cuts marked. Click a stretch to review it.
class ActivityChart : public QWidget {
public:
    explicit ActivityChart(QWidget* parent=nullptr);
    void set_report(const frametrail::AnalysisReport* report);
    void set_playhead(std::optional<double> seconds);
    std::function<void(double)> activated; // seconds
    [[nodiscard]] std::vector<int> stacked_types() const {return shown_;}
    QSize sizeHint() const override {return {600,170};}
    QSize minimumSizeHint() const override {return {300,150};}
protected:
    void paintEvent(QPaintEvent*) override;
    void mouseMoveEvent(QMouseEvent* event) override;
    void mousePressEvent(QMouseEvent* event) override;
private:
    [[nodiscard]] QRectF plot() const;
    [[nodiscard]] std::optional<std::size_t> bin_at(QPointF point) const;
    const frametrail::AnalysisReport* report_{};
    std::vector<int> shown_;
    double top_{1};
    std::optional<double> playhead_;
};

// The Report tab: headline numbers, plain-language findings, activity over time, a table per object type,
// the appearances worth a second look, and the run's details.
class AnalysisReportView : public QScrollArea {
public:
    explicit AnalysisReportView(QWidget* parent=nullptr);
    void set_report(std::optional<frametrail::AnalysisReport> report);
    [[nodiscard]] const frametrail::AnalysisReport* report() const {return report_ ? &*report_ : nullptr;}
    void set_playhead(std::optional<double> seconds);
    std::function<void(std::uint64_t)> appearance_activated;
    std::function<void(double)> time_activated;
private:
    std::optional<frametrail::AnalysisReport> report_;
    QWidget* content_{};
    QLabel *empty_{}, *headline_{}, *legend_{}, *details_{}, *concern_note_{};
    QWidget *tiles_{}, *findings_{}, *sections_{};
    FlowLayout* tiles_layout_{};
    QVBoxLayout* findings_layout_{};
    ActivityChart* chart_{};
    QTableWidget* types_{};
    QListWidget* concerns_{};
};
