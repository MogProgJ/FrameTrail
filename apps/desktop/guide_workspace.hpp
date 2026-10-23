#pragma once
#include <QWidget>
#include <QString>
#include <QVector>
#include <functional>

class QComboBox;
class QLineEdit;
class QListWidget;
class QLabel;
class QTextBrowser;
class QPushButton;

class GuideWorkspace : public QWidget {
public:
    explicit GuideWorkspace(const QComboBox* models, QWidget* parent=nullptr);
    void focus_search();
    std::function<void(int section, int model_index)> navigate;
private:
    struct Entry {QString title, body, keywords, action; int section{}, model{-1};};
    void filter();
    void show_entry();
    QVector<Entry> tasks_, visible_;
    QVector<bool> installed_;
    QLineEdit* search_{};
    QListWidget* results_{};
    QLabel* title_{};
    QLabel* summary_{};
    QTextBrowser* body_{};
    QPushButton* go_{};
};
