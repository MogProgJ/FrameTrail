#include "workspace_chrome.hpp"
#include "studio_controls.hpp"
#include "timeline_slider.hpp"
#include <QMainWindow>
#include <QFrame>
#include <QLabel>
#include <QPushButton>
#include <QScrollArea>
#include <QShortcut>
#include <QSlider>
#include <QSplitter>
#include <QTabWidget>
#include <QTabBar>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QComboBox>
#include <QStyle>
#include <QPropertyAnimation>
#include <QGraphicsOpacityEffect>
#include <QStackedWidget>
#include <QButtonGroup>
#include <QPainter>
#include <stdexcept>

namespace {
// Paints a navigation rail button: tinted pill behind the icon when selected, label below, busy dot.
class RailPainter final : public QObject {
public:
    explicit RailPainter(QPushButton* button):QObject(button),button_(button) {button->installEventFilter(this);}
protected:
    bool eventFilter(QObject*,QEvent* event) override {
        if(event->type()!=QEvent::Paint)return false;
        QPainter painter(button_);painter.setRenderHint(QPainter::Antialiasing);
        const bool on=button_->isChecked(),hover=button_->underMouse(),enabled=button_->isEnabled();
        const QRectF area=QRectF(button_->rect()).adjusted(2,2,-2,-2);
        if(hover && !on){painter.setPen(Qt::NoPen);painter.setBrush(QColor("#262626"));painter.drawRoundedRect(area,8,8);}
        const QRectF pill(area.center().x()-24,area.top()+4,48,28);
        if(on){auto fill=ft::ui::accent();fill.setAlpha(40);painter.setPen(Qt::NoPen);painter.setBrush(fill);painter.drawRoundedRect(pill,14,14);}
        const auto color=!enabled ? ft::ui::text_disabled : on ? ft::ui::accent() : hover ? ft::ui::text : ft::ui::text_secondary;
        painter.drawPixmap(QPointF(pill.center().x()-10,pill.center().y()-10),fluent_pixmap(button_->property("railIcon").toString(),color,20));
        if(button_->property("busy").toBool()){painter.setPen(QPen(ft::ui::pane,2));painter.setBrush(ft::ui::accent());painter.drawEllipse(QPointF(pill.right()-10,pill.top()+6),4.5,4.5);}
        auto font=button_->font();font.setPixelSize(11);font.setWeight(on ? QFont::DemiBold : QFont::Normal);painter.setFont(font);
        painter.setPen(!enabled ? ft::ui::text_disabled : on ? ft::ui::text : ft::ui::text_secondary);
        painter.drawText(QRectF(area.left(),pill.bottom()+2,area.width(),area.bottom()-pill.bottom()-2),Qt::AlignHCenter|Qt::AlignTop,button_->text());
        return true;
    }
private:
    QPushButton* button_;
};
}

void install_workspace_chrome(QMainWindow* window) {
    auto* workspace=window->findChild<QHBoxLayout*>(QStringLiteral("workspace"));
    auto* header=window->findChild<QHBoxLayout*>(QStringLiteral("header"));
    auto* video=window->findChild<QWidget*>(QStringLiteral("videoPane"));
    auto* scroll=window->findChild<QScrollArea*>(QStringLiteral("settingsScroll"));
    auto* inspector=window->findChild<QFrame*>(QStringLiteral("inspector"));
    auto* options=window->findChild<QVBoxLayout*>(QStringLiteral("inspectorLayout"));
    auto* root=window->findChild<QVBoxLayout*>(QStringLiteral("rootLayout"));
    auto* video_column=window->findChild<QVBoxLayout*>(QStringLiteral("videoColumn"));
    auto* playback=window->findChild<QHBoxLayout*>(QStringLiteral("playback"));
    auto* branding=window->findChild<QVBoxLayout*>(QStringLiteral("branding"));
    auto* title=window->findChild<QLabel*>(QStringLiteral("title"));
    auto* subtitle=window->findChild<QLabel*>(QStringLiteral("subtitle"));
    auto* source=window->findChild<QLabel*>(QStringLiteral("source"));
    auto* open=window->findChild<QPushButton*>(QStringLiteral("open"));
    auto* state=window->findChild<QLabel*>(QStringLiteral("state"));
    auto* details=window->findChild<QLabel*>(QStringLiteral("details"));
    if(!workspace || !header || !video || !scroll || !inspector || !options || !root || !video_column || !playback || !branding ||
       !title || !subtitle || !source || !open || !state || !details)throw std::runtime_error("Workspace layout contract missing");

    // Navigation rail: icon over label, a tinted pill for the current section, a dot while it is busy.
    auto* rail=new QFrame;rail->setObjectName(QStringLiteral("workspaceRail"));rail->setFixedWidth(84);
    auto* nav=new QVBoxLayout(rail);nav->setContentsMargins(8,14,8,12);nav->setSpacing(4);nav->setAlignment(Qt::AlignHCenter|Qt::AlignTop);
    auto* mark=brand_mark(26);mark->setToolTip(QStringLiteral("FrameTrail"));nav->addWidget(mark,0,Qt::AlignHCenter);nav->addSpacing(14);
    auto* group=new QButtonGroup(window);group->setExclusive(true);
    const auto add_nav=[&](QPushButton* button,const QString& label,const QString& icon,const QString& hint){
        button->setText(label);button->setToolTip(hint);button->setProperty("role","rail");button->setProperty("railIcon",icon);button->setCheckable(true);
        button->setFixedSize(68,58);button->setCursor(Qt::PointingHandCursor);button->setFocusPolicy(Qt::NoFocus);
        button->setAttribute(Qt::WA_Hover);new RailPainter(button); // Ctrl+1–4, Ctrl+H and Ctrl+K switch sections from the keyboard.
        group->addButton(button,group->buttons().size());nav->addWidget(button,0,Qt::AlignHCenter);
    };
    auto* home=new QPushButton;home->setObjectName(QStringLiteral("homeWorkspace"));
    add_nav(home,QStringLiteral("Home"),QStringLiteral("home"),QStringLiteral("Start page: open files, recent work, tools · Ctrl+H"));
    auto* current=new QPushButton;current->setObjectName(QStringLiteral("previewWorkspace"));
    add_nav(current,QStringLiteral("Preview"),QStringLiteral("preview"),QStringLiteral("Watch a video or photo with live detection · Ctrl+1"));current->setChecked(true);
    const auto move_action=[&](const char* object,const QString& label,const QString& icon,const QString& hint) {
        auto* button=window->findChild<QPushButton*>(QString::fromLatin1(object));if(!button)throw std::runtime_error(object);
        header->removeWidget(button);add_nav(button,label,icon,hint);
    };
    move_action("savedAnalysis",QStringLiteral("Analysis"),QStringLiteral("analysis"),QStringLiteral("Find every object appearance in a video · Ctrl+2"));
    move_action("smoothPlayback",QStringLiteral("Playback"),QStringLiteral("playback"),QStringLiteral("Prepare detections once, then play smoothly · Ctrl+3"));
    move_action("liveCamera",QStringLiteral("Camera"),QStringLiteral("camera"),QStringLiteral("Live webcam detection; the camera opens only on Start · Ctrl+4"));
    nav->addStretch();
    auto* guide=new QPushButton;guide->setObjectName(QStringLiteral("quickGuide"));
    add_nav(guide,QStringLiteral("Guide"),QStringLiteral("guide"),QStringLiteral("Tasks, shortcuts and object categories · Ctrl+K / F1"));

    // Status bar: privacy / background work on the left, the active detector on the right.
    auto* status_bar=new QFrame;status_bar->setObjectName(QStringLiteral("statusBar"));status_bar->setFixedHeight(30);
    auto* status=new QHBoxLayout(status_bar);status->setContentsMargins(14,0,16,0);status->setSpacing(8);
    auto* shield=new QLabel;shield->setObjectName(QStringLiteral("activityIcon"));shield->setPixmap(fluent_pixmap(QStringLiteral("local"),ft::ui::text_tertiary,14));status->addWidget(shield);
    auto* activity=new QLabel(QStringLiteral("All work stays local"));activity->setObjectName(QStringLiteral("workspaceActivity"));
    activity->setTextFormat(Qt::PlainText);activity->setToolTip(QStringLiteral("Videos, photos and results never leave this PC"));
    status->addWidget(activity,1);
    auto* detector=new QLabel;detector->setObjectName(QStringLiteral("detectorStatus"));detector->setTextFormat(Qt::PlainText);status->addWidget(detector);

    // Preview page: heading (title, file, actions), then video and inspector side by side.
    root->removeItem(header);root->removeItem(workspace);root->setContentsMargins(0,0,0,0);root->setSpacing(0);
    branding->removeWidget(title);branding->removeWidget(subtitle);subtitle->hide();title->setText(QStringLiteral("Preview"));
    video_column->removeWidget(source);source->setText(QStringLiteral("No media open"));
    header->removeWidget(open);open->setText(QStringLiteral("Open media"));open->setProperty("role","primary");studio_button(open,QStringLiteral("open"));
    while(header->count())delete header->takeAt(0); // Only empty layouts and spacers remain.
    delete header;
    auto* heading=new QHBoxLayout;heading->setSpacing(12);heading->addWidget(title);heading->addWidget(source,1,Qt::AlignVCenter);
    auto* toggle=new QPushButton;toggle->setObjectName(QStringLiteral("toggleInspector"));toggle->setCheckable(true);toggle->setChecked(true);
    toggle->setProperty("role","subtle");toggle->setText(QStringLiteral("Settings"));studio_button(toggle,QStringLiteral("inspector"));
    toggle->setToolTip(QStringLiteral("Show or hide detection and tracking settings · Ctrl+I"));
    auto* snapshot=new QPushButton(QStringLiteral("Snapshot"));snapshot->setObjectName(QStringLiteral("snapshot"));snapshot->setProperty("role","subtle");
    studio_button(snapshot,QStringLiteral("image"));snapshot->setToolTip(QStringLiteral("Save this frame with its boxes as a PNG in Pictures\\FrameTrail · Ctrl+S"));snapshot->setEnabled(false);
    heading->addWidget(snapshot);heading->addWidget(toggle);heading->addWidget(open);
    auto* splitter=new QSplitter(Qt::Horizontal);splitter->setObjectName(QStringLiteral("workspaceSplitter"));splitter->setHandleWidth(12);splitter->setChildrenCollapsible(false);
    workspace->removeWidget(video);workspace->removeWidget(scroll);splitter->addWidget(video);splitter->addWidget(scroll);
    splitter->setStretchFactor(0,1);splitter->setStretchFactor(1,0);splitter->setSizes({860,300});
    auto* preview=new QWidget;auto* preview_layout=new QVBoxLayout(preview);preview_layout->setContentsMargins(24,18,24,18);preview_layout->setSpacing(14);
    preview_layout->addLayout(heading);preview_layout->addWidget(splitter,1);
    auto* pages=new QStackedWidget;pages->setObjectName(QStringLiteral("workspacePages"));pages->addWidget(preview);
    auto* body=new QHBoxLayout;body->setContentsMargins(0,0,0,0);body->setSpacing(0);body->addWidget(rail);body->addWidget(pages,1);
    root->addLayout(body,1);root->addWidget(status_bar);delete workspace;

    // Inspector: Detection and Tracking tabs inside one card.
    scroll->setMaximumWidth(380);scroll->setMinimumWidth(268);scroll->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);inspector->setMinimumWidth(0);inspector->setMaximumWidth(QWIDGETSIZE_MAX);
    auto* tabs=new QTabWidget;tabs->setObjectName(QStringLiteral("inspectorTabs"));tabs->setDocumentMode(true);tabs->tabBar()->setDrawBase(false);
    const auto page=[&](const QString& name,const QStringList& names) {
        auto* widget=new QWidget;auto* layout=new QVBoxLayout(widget);layout->setContentsMargins(0,16,0,8);layout->setSpacing(8);
        for(const auto& object:names) {
            auto* control=window->findChild<QWidget*>(object);if(!control)throw std::runtime_error(("Missing inspector control: "+object).toStdString());options->removeWidget(control);layout->addWidget(control);
            if(auto* box=qobject_cast<QComboBox*>(control)) {box->setSizeAdjustPolicy(QComboBox::AdjustToMinimumContentsLengthWithIcon);box->setMinimumContentsLength(12);box->setMinimumWidth(0);box->setSizePolicy(QSizePolicy::Ignored,QSizePolicy::Fixed);}
            if(qobject_cast<QComboBox*>(control) || qobject_cast<QAbstractSpinBox*>(control) || qobject_cast<QPushButton*>(control))layout->addSpacing(6);
        }
        layout->addStretch();tabs->addTab(widget,name);
    };
    for(auto* label:inspector->findChildren<QLabel*>())if(label->text()==QStringLiteral("PROCESSING DEVICE"))label->setObjectName(QStringLiteral("deviceCaption"));
    page(QStringLiteral("Detection"),{"analysisSection","detectObjects","modelLabel","modelSelection","deviceCaption","backendSelection","confidenceLabel","confidence"});
    page(QStringLiteral("Tracking"),{"trackingSection","trackObjects","classesLabel","trackingClasses","directionLabel","crossingDirection","drawLine","lineHint"});
    tabs->findChild<QLabel*>(QStringLiteral("analysisSection"))->setText(QStringLiteral("Object detection"));
    tabs->findChild<QLabel*>(QStringLiteral("trackingSection"))->setText(QStringLiteral("Movement and counting"));
    tabs->findChild<QLabel*>(QStringLiteral("deviceCaption"))->setText(QStringLiteral("Processing device"));
    tabs->findChild<QLabel*>(QStringLiteral("deviceCaption"))->setProperty("role",QVariant());
    for(const char* caption:{"modelLabel","deviceCaption","confidenceLabel","classesLabel","directionLabel"})
        tabs->findChild<QLabel*>(QString::fromLatin1(caption))->setProperty("role","muted");
    tabs->findChild<QLabel*>(QStringLiteral("lineHint"))->setProperty("role","caption");
    window->findChild<QLabel*>(QStringLiteral("crossingsSection"))->setText(QStringLiteral("Session counts"));
    window->findChild<QLabel*>(QStringLiteral("countsHint"))->setProperty("role","caption");
    window->findChild<QLabel*>(QStringLiteral("crossingCounts"))->setText(QStringLiteral("− → +  0      + → −  0"));
    QObject::connect(tabs,&QTabWidget::currentChanged,tabs,[tabs](int index){
        auto* page=tabs->widget(index);auto* effect=new QGraphicsOpacityEffect(page);page->setGraphicsEffect(effect);
        auto* fade=new QPropertyAnimation(effect,"opacity",page);fade->setDuration(140);fade->setStartValue(.65);fade->setEndValue(1.);fade->setEasingCurve(QEasingCurve::OutCubic);
        QObject::connect(fade,&QPropertyAnimation::finished,page,[page]{page->setGraphicsEffect(nullptr);});fade->start(QAbstractAnimation::DeleteWhenStopped);
    });
    options->insertWidget(0,tabs,1);options->setContentsMargins(16,14,16,16);options->setSpacing(8);
    // What the detector sees in the current frame, by object type.
    auto* in_view_title=new QLabel(QStringLiteral("In view"));in_view_title->setProperty("role","section");
    auto* in_view=new QLabel(QStringLiteral("Open media to see detected objects here."));in_view->setObjectName(QStringLiteral("inViewSummary"));
    in_view->setWordWrap(true);in_view->setProperty("role","muted");in_view->setTextFormat(Qt::RichText);in_view->setMinimumHeight(44);
    in_view->setTextInteractionFlags(Qt::LinksAccessibleByMouse);in_view->setOpenExternalLinks(false);
    in_view->setToolTip(QStringLiteral("Click an object type to show only that type; click it again to show all"));
    auto* in_view_divider=new QFrame;in_view_divider->setObjectName(QStringLiteral("divider"));
    options->insertWidget(0,in_view_title);options->insertWidget(1,in_view);options->insertSpacing(2,4);options->insertWidget(3,in_view_divider);
    QObject::connect(toggle,&QPushButton::toggled,scroll,&QWidget::setVisible);
    auto* shortcut=new QShortcut(QKeySequence(QStringLiteral("Ctrl+I")),window);QObject::connect(shortcut,&QShortcut::activated,window,[toggle,pages]{if(pages->currentIndex()==0)toggle->toggle();});
    for(const auto& pair:{std::pair{"play","play"},std::pair{"stop","stop"},std::pair{"replay","replay"},std::pair{"drawLine","line"}})studio_button(window->findChild<QPushButton*>(QString::fromLatin1(pair.first)),QString::fromLatin1(pair.second));
    for(const char* object:{"play","stop","replay"})window->findChild<QPushButton*>(QString::fromLatin1(object))->setProperty("role","subtle");
    // Transport: wrap the existing playback layout without replacing its controls or signals.
    video_column->removeItem(playback);auto* bar=new QFrame;bar->setObjectName(QStringLiteral("transportBar"));bar->setLayout(playback);playback->setContentsMargins(8,6,12,6);playback->setSpacing(6);
    // Timeline: position, seek slider and duration between the buttons and the end of the bar.
    playback->removeWidget(state);for(int i=playback->count();i-->0;)if(playback->itemAt(i)->spacerItem())delete playback->takeAt(i);
    auto* position=new QLabel(QStringLiteral("0:00"));position->setObjectName(QStringLiteral("timePosition"));position->setProperty("role","time");
    auto* timeline=new TimelineSlider;timeline->setObjectName(QStringLiteral("timeline"));timeline->setRange(0,1000);timeline->setEnabled(false);
    timeline->setAccessibleName(QStringLiteral("Video position"));timeline->setToolTip(QStringLiteral("Drag or click to jump. Tracking counts restart after a jump."));
    auto* duration=new QLabel(QStringLiteral("0:00"));duration->setObjectName(QStringLiteral("timeDuration"));duration->setProperty("role","time");
    playback->addSpacing(8);playback->addWidget(position);playback->addWidget(timeline,1);playback->addWidget(duration);
    video_column->insertWidget(1,bar);video_column->setSpacing(10);
    video_column->removeWidget(details);auto* status_row=new QHBoxLayout;status_row->setSpacing(12);
    state->setProperty("role","caption");details->setWordWrap(false);state->setWordWrap(false);
    status_row->addWidget(state);status_row->addStretch();status_row->addWidget(details);video_column->addLayout(status_row);
    window->resize(1400,900);
}
