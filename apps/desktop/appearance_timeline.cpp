#include "appearance_timeline.hpp"
#include "frametrail/detector.hpp"
#include "theme.hpp"
#include <QMouseEvent>
#include <QPainter>
#include <QPainterPath>
#include <QToolTip>
#include <algorithm>
#include <cmath>

namespace {
constexpr int label_width=118, lane_height=22, axis_height=22, padding=12;
QString clock(double seconds) {
    const auto total=std::max<qint64>(0,qint64(std::floor(seconds)));
    return total>=3600 ? QStringLiteral("%1:%2:%3").arg(total/3600).arg(total/60%60,2,10,QChar('0')).arg(total%60,2,10,QChar('0'))
                       : QStringLiteral("%1:%2").arg(total/60).arg(total%60,2,10,QChar('0'));
}
}

AppearanceTimeline::AppearanceTimeline(QWidget* parent):QWidget(parent) {
    setObjectName(QStringLiteral("appearanceTimeline"));setMouseTracking(true);setSizePolicy(QSizePolicy::Expanding,QSizePolicy::Fixed);
}
void AppearanceTimeline::set_spans(std::vector<Span> spans,double duration) {
    spans_=std::move(spans);lanes_.clear();duration_=duration;
    std::stable_sort(spans_.begin(),spans_.end(),[](const Span& a,const Span& b){return a.start<b.start;});
    for(const auto& span:spans_){duration_=std::max(duration_,span.end);if(std::find(lanes_.begin(),lanes_.end(),span.class_id)==lanes_.end())lanes_.push_back(span.class_id);}
    selected_.reset();updateGeometry();update();
}
void AppearanceTimeline::set_playhead(std::optional<double> seconds) {if(playhead_!=seconds){playhead_=seconds;update();}}
void AppearanceTimeline::set_selected(std::optional<std::uint64_t> id) {if(selected_!=id){selected_=id;update();}}
QSize AppearanceTimeline::sizeHint() const {return {600,axis_height+padding*2+std::max<int>(1,int(lanes_.size()))*lane_height};}
QSize AppearanceTimeline::minimumSizeHint() const {return {320,sizeHint().height()};}
QRectF AppearanceTimeline::lanes_rect() const {
    return QRectF(label_width+padding,padding+axis_height,std::max(1,width()-label_width-padding*2),lanes_.size()*double(lane_height));
}
QRectF AppearanceTimeline::bar_rect(const Span& span) const {
    const auto area=lanes_rect();const auto lane=int(std::find(lanes_.begin(),lanes_.end(),span.class_id)-lanes_.begin());
    const double scale=duration_>0 ? area.width()/duration_ : 0;
    const double left=area.left()+span.start*scale,right=std::max(left+4,area.left()+span.end*scale);
    return QRectF(left,area.top()+lane*lane_height+4,right-left,lane_height-8);
}
std::optional<std::size_t> AppearanceTimeline::span_at(QPointF point) const {
    for(std::size_t i=spans_.size();i-->0;)if(bar_rect(spans_[i]).adjusted(-2,-3,2,3).contains(point))return i;
    return std::nullopt;
}
void AppearanceTimeline::paintEvent(QPaintEvent*) {
    QPainter painter(this);painter.setRenderHint(QPainter::Antialiasing);
    QPainterPath card;card.addRoundedRect(QRectF(rect()).adjusted(.5,.5,-.5,-.5),8,8);
    painter.fillPath(card,ft::ui::card);painter.setPen(QPen(ft::ui::stroke,1));painter.drawPath(card);
    auto font=painter.font();font.setPixelSize(12);painter.setFont(font);
    if(spans_.empty()) {
        painter.setPen(ft::ui::text_tertiary);
        painter.drawText(rect(),Qt::AlignCenter,QStringLiteral("The timeline shows when each object type appears."));
        return;
    }
    const auto area=lanes_rect();
    // Time axis: up to six evenly spaced labels.
    painter.setPen(ft::ui::text_tertiary);
    const int ticks=std::clamp(int(area.width()/110),2,6);
    for(int i=0;i<=ticks;++i) {
        const double x=area.left()+area.width()*i/ticks;
        painter.setPen(QPen(QColor("#2e2e2e"),1));painter.drawLine(QPointF(x,area.top()-4),QPointF(x,area.bottom()));
        painter.setPen(ft::ui::text_tertiary);
        const QRectF label(x-40,padding,80,axis_height-6);
        painter.drawText(label,(i==0?Qt::AlignLeft:i==ticks?Qt::AlignRight:Qt::AlignHCenter)|Qt::AlignVCenter,clock(duration_*i/ticks));
    }
    for(std::size_t lane=0;lane<lanes_.size();++lane) {
        const double y=area.top()+lane*lane_height;
        const auto color=ft::ui::category_color(lanes_[lane]);
        painter.setPen(Qt::NoPen);painter.setBrush(color);painter.drawEllipse(QPointF(padding+5,y+lane_height/2.),4,4);
        painter.setPen(ft::ui::text_secondary);
        painter.drawText(QRectF(padding+16,y,label_width-20,lane_height),Qt::AlignLeft|Qt::AlignVCenter,
            painter.fontMetrics().elidedText(QString::fromUtf8(frametrail::class_name(lanes_[lane]).data()),Qt::ElideRight,label_width-20));
        painter.setPen(Qt::NoPen);painter.setBrush(QColor("#2a2a2a"));painter.drawRoundedRect(QRectF(area.left(),y+lane_height/2.-1,area.width(),2),1,1);
    }
    for(const auto& span:spans_) {
        auto color=ft::ui::category_color(span.class_id);
        const auto bar=bar_rect(span);
        painter.setPen(selected_==span.id ? QPen(ft::ui::text,2) : Qt::NoPen);painter.setBrush(color);painter.drawRoundedRect(bar,3,3);
    }
    if(playhead_ && duration_>0) {
        const double x=area.left()+std::clamp(*playhead_/duration_,0.,1.)*area.width();
        painter.setPen(QPen(ft::ui::text,1.5));painter.drawLine(QPointF(x,area.top()-6),QPointF(x,area.bottom()+2));
        painter.setPen(Qt::NoPen);painter.setBrush(ft::ui::text);painter.drawEllipse(QPointF(x,area.top()-6),3,3);
    }
}
void AppearanceTimeline::mousePressEvent(QMouseEvent* event) {
    if(event->button()!=Qt::LeftButton)return;
    if(const auto index=span_at(event->position())){selected_=spans_[*index].id;update();if(activated)activated(spans_[*index].id);}
}
void AppearanceTimeline::mouseMoveEvent(QMouseEvent* event) {
    const auto index=span_at(event->position());
    setCursor(index ? Qt::PointingHandCursor : Qt::ArrowCursor);
    if(index) {
        const auto& span=spans_[*index];
        QToolTip::showText(event->globalPosition().toPoint(),QStringLiteral("%1 · %2 – %3")
            .arg(QString::fromUtf8(frametrail::class_name(span.class_id).data()),clock(span.start),clock(span.end)),this);
    } else QToolTip::hideText();
}

FlowLayout::FlowLayout(QWidget* parent,int spacing):QLayout(parent),gap_(spacing) {setContentsMargins(0,0,0,0);}
FlowLayout::~FlowLayout() {while(auto* item=takeAt(0))delete item;}
void FlowLayout::addItem(QLayoutItem* item) {items_.push_back(item);}
QLayoutItem* FlowLayout::itemAt(int index) const {return index>=0 && index<count() ? items_[std::size_t(index)] : nullptr;}
QLayoutItem* FlowLayout::takeAt(int index) {
    if(index<0 || index>=count())return nullptr;
    auto* item=items_[std::size_t(index)];items_.erase(items_.begin()+index);return item;
}
void FlowLayout::setGeometry(const QRect& rect) {QLayout::setGeometry(rect);arrange(rect,false);}
QSize FlowLayout::minimumSize() const {
    QSize size;for(auto* item:items_)size=size.expandedTo(item->minimumSize());
    return size+QSize(contentsMargins().left()+contentsMargins().right(),contentsMargins().top()+contentsMargins().bottom());
}
int FlowLayout::arrange(const QRect& rect,bool measure) const {
    int x=rect.x(),y=rect.y(),row=0;
    for(auto* item:items_) {
        const auto hint=item->sizeHint();
        if(x+hint.width()>rect.right()+1 && row>0){x=rect.x();y+=row+gap_;row=0;}
        if(!measure)item->setGeometry(QRect(QPoint(x,y),hint));
        x+=hint.width()+gap_;row=std::max(row,hint.height());
    }
    return y+row-rect.y();
}
