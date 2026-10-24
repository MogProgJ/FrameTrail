#include "workspace_chrome.hpp"
#include "studio_controls.hpp"
#include <QMainWindow>
#include <QFrame>
#include <QLabel>
#include <QPushButton>
#include <QScrollArea>
#include <QShortcut>
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
#include <stdexcept>

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
    if(!workspace || !header || !video || !scroll || !inspector || !options || !root || !video_column || !playback || !branding ||
       !title || !subtitle || !source || !open)throw std::runtime_error("Workspace layout contract missing");

    // Navigation pane: brand, sections, guide and the local-processing status.
    auto* rail=new QFrame;rail->setObjectName(QStringLiteral("workspaceRail"));rail->setFixedWidth(212);
    auto* nav=new QVBoxLayout(rail);nav->setContentsMargins(10,14,10,14);nav->setSpacing(4);
    auto* brand=new QHBoxLayout;brand->setContentsMargins(6,0,0,14);brand->setSpacing(8);brand->addWidget(brand_mark(22));
    auto* name=new QLabel(QStringLiteral("FrameTrail"));name->setObjectName(QStringLiteral("brandName"));brand->addWidget(name);brand->addStretch();nav->addLayout(brand);
    auto* group=new QButtonGroup(window);group->setExclusive(true);
    const auto add_nav=[&](QPushButton* button,const QString& label,const QString& icon,const QString& hint){
        button->setText(label);button->setToolTip(hint);button->setProperty("role","navigation");button->setCheckable(true);
        button->setSizePolicy(QSizePolicy::Expanding,QSizePolicy::Fixed);studio_button(button,icon);new NavIndicator(button);
        group->addButton(button,group->buttons().size());nav->addWidget(button);
    };
    auto* current=new QPushButton;current->setObjectName(QStringLiteral("previewWorkspace"));
    add_nav(current,QStringLiteral("Preview"),QStringLiteral("preview"),QStringLiteral("Watch a video or image with live detection · Ctrl+1"));current->setChecked(true);
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
    auto* divider=new QFrame;divider->setObjectName(QStringLiteral("divider"));nav->addSpacing(6);nav->addWidget(divider);nav->addSpacing(6);
    auto* status=new QHBoxLayout;status->setContentsMargins(10,2,4,0);status->setSpacing(8);
    auto* shield=new QLabel;shield->setPixmap(fluent_pixmap(QStringLiteral("local"),ft::ui::text_tertiary,16));status->addWidget(shield,0,Qt::AlignTop);
    auto* activity=new QLabel(QStringLiteral("All work stays local"));activity->setObjectName(QStringLiteral("workspaceActivity"));
    activity->setTextFormat(Qt::PlainText);activity->setWordWrap(true);activity->setToolTip(QStringLiteral("Video, images and results never leave this PC"));
    status->addWidget(activity,1);nav->addLayout(status);

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
    heading->addWidget(toggle);heading->addWidget(open);
    auto* splitter=new QSplitter(Qt::Horizontal);splitter->setObjectName(QStringLiteral("workspaceSplitter"));splitter->setHandleWidth(12);splitter->setChildrenCollapsible(false);
    workspace->removeWidget(video);workspace->removeWidget(scroll);splitter->addWidget(video);splitter->addWidget(scroll);
    splitter->setStretchFactor(0,1);splitter->setStretchFactor(1,0);splitter->setSizes({860,300});
    auto* preview=new QWidget;auto* preview_layout=new QVBoxLayout(preview);preview_layout->setContentsMargins(24,18,24,18);preview_layout->setSpacing(14);
    preview_layout->addLayout(heading);preview_layout->addWidget(splitter,1);
    auto* pages=new QStackedWidget;pages->setObjectName(QStringLiteral("workspacePages"));pages->addWidget(preview);
    auto* body=new QHBoxLayout;body->setContentsMargins(0,0,0,0);body->setSpacing(0);body->addWidget(rail);body->addWidget(pages,1);
    root->addLayout(body,1);delete workspace;

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
    options->insertWidget(0,tabs,1);options->setContentsMargins(16,10,16,16);options->setSpacing(8);
    QObject::connect(toggle,&QPushButton::toggled,scroll,&QWidget::setVisible);
    auto* shortcut=new QShortcut(QKeySequence(QStringLiteral("Ctrl+I")),window);QObject::connect(shortcut,&QShortcut::activated,window,[toggle,pages]{if(pages->currentIndex()==0)toggle->toggle();});
    for(const auto& pair:{std::pair{"play","play"},std::pair{"stop","stop"},std::pair{"replay","replay"},std::pair{"drawLine","line"}})studio_button(window->findChild<QPushButton*>(QString::fromLatin1(pair.first)),QString::fromLatin1(pair.second));
    for(const char* object:{"play","stop","replay"})window->findChild<QPushButton*>(QString::fromLatin1(object))->setProperty("role","subtle");
    // Transport: wrap the existing playback layout without replacing its controls or signals.
    video_column->removeItem(playback);auto* bar=new QFrame;bar->setObjectName(QStringLiteral("transportBar"));bar->setLayout(playback);playback->setContentsMargins(8,6,12,6);playback->setSpacing(6);
    video_column->insertWidget(1,bar);video_column->setSpacing(10);
    window->resize(1400,900);
}
