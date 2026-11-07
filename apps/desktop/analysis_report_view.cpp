#include "analysis_report_view.hpp"
#include "appearance_timeline.hpp"
#include "theme.hpp"
#include <QFrame>
#include <QHeaderView>
#include <QLabel>
#include <QListWidget>
#include <QMouseEvent>
#include <QPainter>
#include <QPainterPath>
#include <QScrollBar>
#include <QTableWidget>
#include <QToolTip>
#include <QVBoxLayout>
#include <algorithm>
#include <cmath>

namespace {
QString name(int id) {return QString::fromUtf8(frametrail::class_name(id).data());}
QString clock(double seconds,bool tenths=false) {return QString::fromStdString(frametrail::clock_text(seconds,tenths));}
QString percent(double share) {return QStringLiteral("%1%").arg(std::lround(std::clamp(share,0.,1.)*100));}
QString length(double seconds) {return seconds<60 ? QStringLiteral("%1 s").arg(seconds,0,'f',seconds<10 ? 1:0) : clock(seconds);}
QLabel* section(const QString& text) {auto* label=new QLabel(text);label->setProperty("role","section");return label;}
QLabel* caption(const QString& text) {
    auto* label=new QLabel(text);label->setProperty("role","caption");label->setWordWrap(true);label->setTextFormat(Qt::PlainText);return label;
}
QString dot(int id) {return QStringLiteral("<span style=\"color:%1\">●</span>").arg(ft::ui::category_color(id).name());}
// Sorts by a number kept next to the displayed text.
class SortItem : public QTableWidgetItem {
public:
    SortItem(const QString& text,double key):QTableWidgetItem(text) {setData(Qt::UserRole,key);setTextAlignment(Qt::AlignRight|Qt::AlignVCenter);}
    bool operator<(const QTableWidgetItem& other) const override {return data(Qt::UserRole).toDouble()<other.data(Qt::UserRole).toDouble();}
};
}

ActivityChart::ActivityChart(QWidget* parent):QWidget(parent) {
    setObjectName(QStringLiteral("activityChart"));setMouseTracking(true);setSizePolicy(QSizePolicy::Expanding,QSizePolicy::Fixed);setFixedHeight(170);
}
void ActivityChart::set_report(const frametrail::AnalysisReport* report) {
    report_=report;shown_.clear();top_=1;playhead_.reset();
    if(report_) {
        for(const auto& type:report_->types)if(shown_.size()<5)shown_.push_back(type.class_id);
        for(const auto& bin:report_->activity)top_=std::max({top_,bin.mean_objects,double(bin.most_objects)});
        top_=std::ceil(top_);
    }
    update();
}
void ActivityChart::set_playhead(std::optional<double> seconds) {if(playhead_!=seconds){playhead_=seconds;update();}}
QRectF ActivityChart::plot() const {return QRectF(40,12,std::max(1,width()-52),std::max(1,height()-40));}
std::optional<std::size_t> ActivityChart::bin_at(QPointF point) const {
    if(!report_ || report_->activity.empty())return std::nullopt;
    const auto area=plot();
    if(!area.adjusted(0,-12,0,20).contains(point))return std::nullopt;
    return std::min(report_->activity.size()-1,std::size_t(std::max(0.,(point.x()-area.left())/area.width()*double(report_->activity.size()))));
}
void ActivityChart::paintEvent(QPaintEvent*) {
    QPainter painter(this);painter.setRenderHint(QPainter::Antialiasing);
    QPainterPath card;card.addRoundedRect(QRectF(rect()).adjusted(.5,.5,-.5,-.5),8,8);
    painter.fillPath(card,ft::ui::card);painter.setPen(QPen(ft::ui::stroke,1));painter.drawPath(card);
    auto font=painter.font();font.setPixelSize(11);painter.setFont(font);
    if(!report_ || report_->activity.empty()) {
        painter.setPen(ft::ui::text_tertiary);painter.drawText(rect(),Qt::AlignCenter,QStringLiteral("Activity over time appears after an analysis."));return;
    }
    const auto area=plot();const auto& bins=report_->activity;
    for(int i=0;i<=2;++i) {
        const double y=area.bottom()-area.height()*i/2.;
        painter.setPen(QPen(QColor("#2e2e2e"),1));painter.drawLine(QPointF(area.left(),y),QPointF(area.right(),y));
        painter.setPen(ft::ui::text_tertiary);
        painter.drawText(QRectF(4,y-8,area.left()-10,16),Qt::AlignRight|Qt::AlignVCenter,QString::number(top_*i/2.,'f',top_<4 ? 1:0));
    }
    const double bar=area.width()/double(bins.size());
    for(std::size_t i=0;i<bins.size();++i) {
        const auto& bin=bins[i];double y=area.bottom();double other=bin.mean_objects;const double x=area.left()+double(i)*bar;
        const auto block=[&](double value,const QColor& colour) {
            if(value<=0)return;const double height=area.height()*value/top_;y-=height;
            painter.fillRect(QRectF(x+.5,y,std::max(1.,bar-1),height),colour);
        };
        for(std::size_t k=0;k<shown_.size();++k)for(const auto& [type,value]:bin.by_type)if(type==shown_[k]){block(value,QColor(frametrail::report_series_colours[k]));other-=value;}
        block(std::max(0.,other),QColor("#6b6b6b"));
        if(bin.scene_cut){painter.setPen(QPen(QColor("#ff6b6b"),1,Qt::DashLine));painter.drawLine(QPointF(x,area.top()),QPointF(x,area.bottom()));}
    }
    painter.setPen(ft::ui::text_tertiary);
    const double total=bins.back().end;
    for(int i=0;i<=4;++i) {
        const double x=area.left()+area.width()*i/4.;
        painter.drawText(QRectF(x-40,area.bottom()+4,80,16),(i==0 ? Qt::AlignLeft : i==4 ? Qt::AlignRight : Qt::AlignHCenter)|Qt::AlignVCenter,clock(total*i/4.,report_->tenths));
    }
    if(playhead_ && total>0) {
        const double x=area.left()+std::clamp(*playhead_/total,0.,1.)*area.width();
        painter.setPen(QPen(ft::ui::text,1.5));painter.drawLine(QPointF(x,area.top()-4),QPointF(x,area.bottom()));
    }
}
void ActivityChart::mouseMoveEvent(QMouseEvent* event) {
    const auto index=bin_at(event->position());setCursor(index ? Qt::PointingHandCursor : Qt::ArrowCursor);
    if(!index){QToolTip::hideText();return;}
    const auto& bin=report_->activity[*index];
    QStringList lines{QStringLiteral("%1 – %2").arg(clock(bin.start,report_->tenths),clock(bin.end,report_->tenths)),
        QStringLiteral("%1 visible on average%2").arg(bin.mean_objects,0,'f',1).arg(bin.most_objects ? QStringLiteral(", up to %1").arg(bin.most_objects) : QString{})};
    for(std::size_t i=0;i<std::min<std::size_t>(5,bin.by_type.size());++i)
        lines<<QStringLiteral("%1  %2").arg(name(bin.by_type[i].first)).arg(bin.by_type[i].second,0,'f',1);
    if(bin.scene_cut)lines<<QStringLiteral("Scene cut");
    lines<<QStringLiteral("Click to review this moment");
    QToolTip::showText(event->globalPosition().toPoint(),lines.join(QLatin1Char('\n')),this);
}
void ActivityChart::mousePressEvent(QMouseEvent* event) {
    if(event->button()!=Qt::LeftButton)return;
    if(const auto index=bin_at(event->position());index && activated) {
        const auto& bin=report_->activity[*index];activated((bin.start+bin.end)/2);
    }
}

AnalysisReportView::AnalysisReportView(QWidget* parent):QScrollArea(parent) {
    setObjectName(QStringLiteral("analysisReport"));setWidgetResizable(true);setFrameShape(QFrame::NoFrame);
    content_=new QWidget;auto* layout=new QVBoxLayout(content_);layout->setContentsMargins(2,4,10,16);layout->setSpacing(10);
    empty_=new QLabel(QStringLiteral("The report appears here after a video is analysed for objects."));empty_->setProperty("role","muted");
    empty_->setAlignment(Qt::AlignCenter);empty_->setMinimumHeight(200);layout->addWidget(empty_);
    sections_=new QWidget;auto* body=new QVBoxLayout(sections_);body->setContentsMargins(0,0,0,0);body->setSpacing(10);
    headline_=new QLabel;headline_->setObjectName(QStringLiteral("reportHeadline"));headline_->setProperty("role","muted");headline_->setWordWrap(true);
    headline_->setTextFormat(Qt::PlainText);body->addWidget(headline_);
    tiles_=new QWidget;tiles_layout_=new FlowLayout(tiles_,10);body->addWidget(tiles_);
    body->addWidget(section(QStringLiteral("Findings")));
    findings_=new QFrame;findings_->setObjectName(QStringLiteral("card"));findings_layout_=new QVBoxLayout(findings_);
    findings_layout_->setContentsMargins(14,10,14,12);findings_layout_->setSpacing(6);body->addWidget(findings_);
    body->addWidget(section(QStringLiteral("Activity over time")));
    chart_=new ActivityChart;body->addWidget(chart_);
    legend_=new QLabel;legend_->setTextFormat(Qt::RichText);legend_->setWordWrap(true);legend_->setProperty("role","caption");body->addWidget(legend_);
    chart_->activated=[this](double seconds){if(time_activated)time_activated(seconds);};
    body->addWidget(section(QStringLiteral("Object types")));
    types_=new QTableWidget;types_->setObjectName(QStringLiteral("reportTypes"));
    types_->setEditTriggers(QAbstractItemView::NoEditTriggers);types_->setSelectionBehavior(QAbstractItemView::SelectRows);
    types_->setSelectionMode(QAbstractItemView::SingleSelection);types_->verticalHeader()->hide();types_->verticalHeader()->setDefaultSectionSize(34);
    types_->setVerticalScrollBarPolicy(Qt::ScrollBarAlwaysOff);types_->setHorizontalScrollBarPolicy(Qt::ScrollBarAsNeeded);types_->setWordWrap(false);
    types_->setToolTip(QStringLiteral("Click a row to review that type's first appearance. Click a heading to sort."));
    body->addWidget(types_);
    connect(types_,&QTableWidget::cellClicked,this,[this](int row,int){
        if(auto* item=types_->item(row,0);item && appearance_activated)appearance_activated(item->data(Qt::UserRole+1).toULongLong());
    });
    body->addWidget(section(QStringLiteral("Worth a second look")));
    concern_note_=caption({});body->addWidget(concern_note_);
    concerns_=new QListWidget;concerns_->setObjectName(QStringLiteral("reportConcerns"));concerns_->setVerticalScrollBarPolicy(Qt::ScrollBarAsNeeded);
    concerns_->setToolTip(QStringLiteral("Click to review the appearance; mark it right or wrong there with C or X."));
    body->addWidget(concerns_);
    connect(concerns_,&QListWidget::itemClicked,this,[this](QListWidgetItem* item){
        if(item && appearance_activated)appearance_activated(item->data(Qt::UserRole).toULongLong());
    });
    body->addWidget(section(QStringLiteral("Run details")));
    details_=new QLabel;details_->setObjectName(QStringLiteral("reportDetails"));details_->setTextFormat(Qt::RichText);details_->setWordWrap(true);
    details_->setTextInteractionFlags(Qt::TextSelectableByMouse);body->addWidget(details_);
    body->addWidget(caption(QStringLiteral("An appearance is one tracked object from when it is first seen until it leaves. "
        "\"Worth a second look\" uses simple checks (seen very briefly, low confidence, a changed label, a box covering most of the frame); "
        "they are hints, not verdicts. Confidence is the model's own score, not measured accuracy: mark appearances right or wrong in Review to measure it.")));
    body->addStretch();
    layout->addWidget(sections_);setWidget(content_);
    set_report(std::nullopt);
}
void AnalysisReportView::set_playhead(std::optional<double> seconds) {chart_->set_playhead(seconds);}
void AnalysisReportView::set_report(std::optional<frametrail::AnalysisReport> report) {
    report_=std::move(report);
    empty_->setVisible(!report_);sections_->setVisible(bool(report_));
    while(auto* item=tiles_layout_->takeAt(0)){delete item->widget();delete item;}
    while(auto* item=findings_layout_->takeAt(0)){delete item->widget();delete item;}
    types_->clear();types_->setRowCount(0);concerns_->clear();chart_->set_report(nullptr);
    if(!report_)return;
    const auto& r=*report_;const auto& s=r.summary;
    headline_->setText(QStringLiteral("%1 · %2 · confidence %3 · %4 on %5")
        .arg(QString::fromStdString(r.video_name),clock(r.duration,r.tenths),percent(s.configuration.detector.confidence),
             QString::fromUtf8(frametrail::detector_name(s.configuration.detector).c_str()),
             QString::fromStdString(s.execution.provider.empty() ? std::string("CPU") : s.execution.provider)));
    std::uint64_t appearances=0;for(const auto& type:r.types)appearances+=type.appearances;
    const auto tile=[this](const QString& value,const QString& label,const QString& tip,bool warn=false) {
        auto* card=new QFrame;card->setObjectName(QStringLiteral("card"));card->setToolTip(tip);card->setMinimumWidth(132);
        auto* box=new QVBoxLayout(card);box->setContentsMargins(14,10,14,10);box->setSpacing(0);
        auto* number=new QLabel(value);number->setStyleSheet(QStringLiteral("font-size:24px;font-weight:600;%1").arg(warn ? QStringLiteral("color:#fce100;") : QString{}));
        box->addWidget(number);auto* text=new QLabel(label);text->setProperty("role","caption");box->addWidget(text);
        tiles_layout_->addWidget(card);
    };
    tile(QString::number(appearances),QStringLiteral("appearances"),QStringLiteral("Tracked objects, each counted from when it appears until it leaves"));
    tile(QString::number(r.types.size()),QStringLiteral("object types"),QStringLiteral("Different kinds of object found"));
    tile(QString::number(r.most_objects),QStringLiteral("most at once"),QStringLiteral("Most objects visible in one frame, at %1").arg(clock(r.most_objects_time,r.tenths)));
    tile(QString::number(r.mean_objects,'f',1),QStringLiteral("visible on average"),QStringLiteral("Average number of tracked objects visible"));
    tile(percent(r.share_with_objects),QStringLiteral("time with objects"),QStringLiteral("Share of the analysed video in which something is visible"));
    tile(QString::number(r.concerns.size()),QStringLiteral("worth a second look"),QStringLiteral("Appearances that are brief, uncertain, relabelled or unusually large"),!r.concerns.empty());
    if(r.frame_details) {
        tile(QStringLiteral("%1 ms").arg(r.detect_ms_mean,0,'f',0),QStringLiteral("per frame"),QStringLiteral("Average detection time; slowest %1 ms").arg(r.detect_ms_max,0,'f',0));
        tile(QString::number(r.scene_cuts.size()),QStringLiteral("scene cuts"),QStringLiteral("Points where the picture changes completely; tracks restart there"));
    }
    for(const auto& line:r.findings) {
        auto* label=new QLabel(QStringLiteral("•  ")+QString::fromStdString(line));label->setWordWrap(true);label->setTextFormat(Qt::PlainText);
        label->setTextInteractionFlags(Qt::TextSelectableByMouse);findings_layout_->addWidget(label);
    }
    chart_->set_report(&*report_);
    QStringList legend;const auto& stacked=chart_->stacked_types();
    for(std::size_t k=0;k<stacked.size();++k)
        legend<<QStringLiteral("<span style=\"color:%1\">●</span> ").arg(QLatin1String(frametrail::report_series_colours[k]))+name(stacked[k]).toHtmlEscaped();
    legend<<QStringLiteral("<span style=\"color:#6b6b6b\">●</span> other");
    if(!r.scene_cuts.empty())legend<<QStringLiteral("<span style=\"color:#ff6b6b\">┆</span> scene cut");
    legend_->setText(legend.join(QStringLiteral("&nbsp;&nbsp;&nbsp;"))+QStringLiteral("<br>Average number of objects visible in each stretch%1. Click a stretch to review it.")
        .arg(r.frame_details ? QString{} : QStringLiteral(", estimated from appearance times")));

    QStringList headers{QStringLiteral("Object"),QStringLiteral("Appearances"),QStringLiteral("On screen"),QStringLiteral("Most at once"),QStringLiteral("First seen"),
        QStringLiteral("Last seen"),QStringLiteral("Longest"),QStringLiteral("Avg conf."),QStringLiteral("Peak conf.")};
    if(r.appearance_details)headers<<QStringLiteral("Movement");
    headers<<QStringLiteral("Doubtful");
    types_->setColumnCount(int(headers.size()));types_->setHorizontalHeaderLabels(headers);
    types_->horizontalHeaderItem(2)->setToolTip(QStringLiteral("Share of the analysed video in which at least one is visible"));
    if(r.appearance_details)types_->horizontalHeaderItem(9)->setToolTip(QStringLiteral("Average distance each appearance travelled, in frame widths (0 = stood still)"));
    types_->setSortingEnabled(false);types_->setRowCount(int(r.types.size()));
    const double covered=std::max(r.covered,1e-9);
    for(int row=0;row<int(r.types.size());++row) {
        const auto& t=r.types[std::size_t(row)];int column=0;
        auto* object=new QTableWidgetItem(name(t.class_id));
        object->setData(Qt::UserRole+1,QVariant::fromValue<qulonglong>(t.first_id));
        object->setToolTip(QStringLiteral("Click to review the first %1").arg(name(t.class_id)));
        QPixmap swatch(10,10);swatch.fill(Qt::transparent);{QPainter p(&swatch);p.setRenderHint(QPainter::Antialiasing);p.setPen(Qt::NoPen);p.setBrush(ft::ui::category_color(t.class_id));p.drawEllipse(1,1,8,8);}
        object->setIcon(QIcon(swatch));types_->setItem(row,column++,object);
        types_->setItem(row,column++,new SortItem(QString::number(t.appearances),double(t.appearances)));
        types_->setItem(row,column++,new SortItem(percent(t.present_seconds/covered)+QStringLiteral("  ·  ")+length(t.present_seconds),t.present_seconds));
        types_->setItem(row,column++,new SortItem(QString::number(t.most_at_once),double(t.most_at_once)));
        types_->setItem(row,column++,new SortItem(clock(t.first_seen,r.tenths),t.first_seen));
        types_->setItem(row,column++,new SortItem(clock(t.last_seen,r.tenths),t.last_seen));
        types_->setItem(row,column++,new SortItem(length(t.longest_seconds),t.longest_seconds));
        types_->setItem(row,column++,new SortItem(percent(t.mean_confidence),t.mean_confidence));
        types_->setItem(row,column++,new SortItem(percent(t.peak_confidence),t.peak_confidence));
        if(r.appearance_details)types_->setItem(row,column++,new SortItem(QString::number(t.mean_path,'f',2),t.mean_path));
        auto* doubtful=new SortItem(t.concerns ? QStringLiteral("%1 of %2").arg(t.concerns).arg(t.appearances) : QStringLiteral("–"),double(t.concerns));
        if(t.concerns)doubtful->setForeground(ft::ui::caution);
        types_->setItem(row,column++,doubtful);
    }
    types_->setSortingEnabled(true);types_->sortByColumn(1,Qt::DescendingOrder);
    types_->resizeColumnsToContents();types_->horizontalHeader()->setStretchLastSection(true);
    types_->setFixedHeight(types_->horizontalHeader()->sizeHint().height()+34*std::max(1,int(r.types.size()))+6+
        (types_->horizontalScrollBar()->isVisible() ? types_->horizontalScrollBar()->height() : 10));

    concern_note_->setText(r.concerns.empty() ? QStringLiteral("Nothing stood out: every appearance passed the checks.")
        : QStringLiteral("%1 appearances, strongest hints first. Click one to review it.").arg(r.concerns.size()));
    const std::size_t limit=500;
    for(std::size_t i=0;i<std::min(limit,r.concerns.size());++i) {
        const auto& c=r.concerns[i];
        auto* item=new QListWidgetItem(QStringLiteral("%1   %2 #%3\n%4").arg(clock(c.start,r.tenths),name(c.class_id)).arg(c.appearance).arg(QString::fromStdString(c.reasons)),concerns_);
        item->setData(Qt::UserRole,QVariant::fromValue<qulonglong>(c.appearance));
        QPixmap swatch(12,12);swatch.fill(Qt::transparent);{QPainter p(&swatch);p.setRenderHint(QPainter::Antialiasing);p.setPen(Qt::NoPen);p.setBrush(ft::ui::category_color(c.class_id));p.drawEllipse(1,1,10,10);}
        item->setIcon(QIcon(swatch));
    }
    if(r.concerns.size()>limit)new QListWidgetItem(QStringLiteral("… and %1 more in the exported report").arg(r.concerns.size()-limit),concerns_);
    concerns_->setVisible(!r.concerns.empty());
    concerns_->setFixedHeight(std::clamp(int(std::min(limit,r.concerns.size()))*58+8,60,420));

    const auto row=[](const QString& label,const QString& value){
        return QStringLiteral("<tr><td style=\"color:#969696;padding:2px 18px 2px 0\">%1</td><td>%2</td></tr>").arg(label,value.toHtmlEscaped());};
    QString table=QStringLiteral("<table>");
    const auto source=s.configuration.source.u8string();
    table+=row(QStringLiteral("Video"),QString::fromUtf8(reinterpret_cast<const char*>(source.data()),qsizetype(source.size())));
    table+=row(QStringLiteral("Resolution"),QStringLiteral("%1 × %2 · %3").arg(s.media.width).arg(s.media.height).arg(QString::fromStdString(s.media.codec)));
    table+=row(QStringLiteral("Duration"),clock(r.duration,r.tenths)+(r.covered+r.frame_interval<r.duration ? QStringLiteral(" (analysed %1)").arg(clock(r.covered,r.tenths)) : QString{}));
    table+=row(QStringLiteral("Frames"),QStringLiteral("%1 analysed%2 · about %3 frames per second")
        .arg(r.analysed_frames).arg(s.configuration.tracking.frame_step>1 ? QStringLiteral(", every %1 frames").arg(s.configuration.tracking.frame_step) : QString{})
        .arg(1/std::max(r.frame_interval,1e-9),0,'f',1));
    const auto model_file=s.configuration.detector.model.filename().u8string();
    table+=row(QStringLiteral("Model"),QStringLiteral("%1 · %2").arg(QString::fromUtf8(frametrail::detector_name(s.configuration.detector).c_str()),
        QString::fromUtf8(reinterpret_cast<const char*>(model_file.data()),qsizetype(model_file.size()))));
    table+=row(QStringLiteral("Confidence threshold"),percent(s.configuration.detector.confidence));
    table+=row(QStringLiteral("Device"),QString::fromStdString(s.execution.provider+(s.execution.device.empty() ? "" : " · "+s.execution.device)+
        (s.execution.fallback.empty() ? "" : " · fallback: "+s.execution.fallback)));
    if(r.frame_details)table+=row(QStringLiteral("Detection time"),QStringLiteral("%1 ms average · %2 ms for 95% of frames · %3 ms slowest")
        .arg(r.detect_ms_mean,0,'f',1).arg(r.detect_ms_p95,0,'f',1).arg(r.detect_ms_max,0,'f',1));
    table+=row(QStringLiteral("Status"),QString::fromStdString(s.status+(s.error.empty() ? "" : " · "+s.error)));
    table+=row(QStringLiteral("Analysed"),QString::fromStdString(s.created));
    table+=row(QStringLiteral("Run ID"),QString::fromStdString(s.id));
    details_->setText(table+QStringLiteral("</table>"));
    verticalScrollBar()->setValue(0);
}
