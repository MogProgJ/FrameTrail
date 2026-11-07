#pragma once
#include <QLayout>
#include <QWidget>
#include <cstdint>
#include <functional>
#include <optional>
#include <vector>

// One lane per object type across the video's duration; each appearance is a bar.
// Clicking a bar reports its appearance id. The playhead marks the reviewed time.
class AppearanceTimeline : public QWidget {
public:
    struct Span { std::uint64_t id{}; int class_id{}; double start{}, end{}; }; // seconds
    explicit AppearanceTimeline(QWidget* parent=nullptr);
    void set_spans(std::vector<Span> spans,double duration);
    void set_playhead(std::optional<double> seconds);
    void set_selected(std::optional<std::uint64_t> id);
    [[nodiscard]] bool empty() const {return spans_.empty();}
    // The appearance visible at that time that started last, otherwise the next one to start.
    [[nodiscard]] std::optional<std::uint64_t> appearance_at(double seconds) const;
    std::function<void(std::uint64_t)> activated;
    QSize sizeHint() const override;
    QSize minimumSizeHint() const override;
protected:
    void paintEvent(QPaintEvent*) override;
    void mousePressEvent(QMouseEvent* event) override;
    void mouseMoveEvent(QMouseEvent* event) override;
private:
    std::optional<std::size_t> span_at(QPointF point) const;
    QRectF bar_rect(const Span& span) const;
    QRectF lanes_rect() const;
    std::vector<Span> spans_;
    std::vector<int> lanes_; // class ids in order of first appearance
    double duration_{};
    std::optional<double> playhead_;
    std::optional<std::uint64_t> selected_;
};

// Left-to-right layout that wraps onto new rows (chips).
class FlowLayout : public QLayout {
public:
    explicit FlowLayout(QWidget* parent=nullptr,int spacing=6);
    ~FlowLayout() override;
    void addItem(QLayoutItem* item) override;
    int count() const override {return int(items_.size());}
    QLayoutItem* itemAt(int index) const override;
    QLayoutItem* takeAt(int index) override;
    Qt::Orientations expandingDirections() const override {return {};}
    bool hasHeightForWidth() const override {return true;}
    int heightForWidth(int width) const override {return arrange(QRect(0,0,width,0),true);}
    void setGeometry(const QRect& rect) override;
    QSize sizeHint() const override {return minimumSize();}
    QSize minimumSize() const override;
private:
    int arrange(const QRect& rect,bool measure) const;
    std::vector<QLayoutItem*> items_;
    int gap_;
};
