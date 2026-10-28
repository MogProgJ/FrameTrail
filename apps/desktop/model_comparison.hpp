#pragma once
#include <QDateTime>
#include <QString>
#include <map>
#include <utility>
#include <vector>

class QTableWidget;
class QWidget;

// Compares models on one video through their review files (review mode writes <run id>.json per analysis).
// The share marked correct measures false alarms on the reviewed appearances; the number found shows how much
// each model sees. Their product estimates the correct appearances a model finds in the whole video.
struct ReviewedRun {
    QString run_id, video, model;
    double confidence{};
    qint64 appearances{};
    int reviewed{}, correct{};
    std::map<QString,std::pair<int,int>> objects; // Object type -> (reviewed, correct).
    QDateTime saved;
    [[nodiscard]] double correct_share() const { return reviewed ? double(correct)/reviewed : 0; }
};
// The newest review per model for `video` (a file name), models in name order. Runs without verdicts are skipped.
std::vector<ReviewedRun> reviewed_runs(const QString& folder,const QString& video);
QTableWidget* comparison_table(const std::vector<ReviewedRun>& runs,QWidget* parent=nullptr);
void show_model_comparison(QWidget* parent,const QString& folder,const QString& video);
