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
    if(!workspace || !header || !video || !scroll || !inspector || !options || !root || !video_column || !playback)throw std::runtime_error("Workspace layout contract missing");
    root->setContentsMargins(18,14,18,16);root->setSpacing(16);workspace->setSpacing(10);header->setSpacing(10);
    auto* branding=window->findChild<QVBoxLayout*>(QStringLiteral("branding"));branding->setSpacing(3);
    window->findChild<QLabel*>(QStringLiteral("subtitle"))->setText(QStringLiteral("Video intelligence"));studio_heading(header);
    window->findChild<QLabel*>(QStringLiteral("source"))->setText(QStringLiteral("Preview  /  Untitled media"));
    window->findChild<QLabel*>(QStringLiteral("details"))->setText(QStringLiteral("Local processing  \u00b7  Ctrl+O  Open media     Space  Play / pause"));
    auto* rail=new QFrame;rail->setObjectName(QStringLiteral("workspaceRail"));rail->setFixedWidth(164);
    auto* nav=new QVBoxLayout(rail);nav->setContentsMargins(10,18,10,16);nav->setSpacing(5);
    auto* section=new QLabel(QStringLiteral("WORKSPACE"));section->setProperty("role","section");section->setContentsMargins(8,0,0,10);nav->addWidget(section);
    auto* current=new QLabel(QStringLiteral("Preview"));current->setObjectName(QStringLiteral("activeWorkspace"));nav->addWidget(current);
    const auto move_action=[&](const char* name,const QString& label,const QString& icon,const QString& hint) {
        auto* button=window->findChild<QPushButton*>(QString::fromLatin1(name));if(!button)throw std::runtime_error(name);header->removeWidget(button);
        button->setText(label);button->setToolTip(hint);button->setProperty("role","navigation");studio_button(button,icon);
        button->setSizePolicy(QSizePolicy::Expanding,QSizePolicy::Fixed);nav->addWidget(button);
    };
    move_action("savedAnalysis",QStringLiteral("Analysis"),"analyse",QStringLiteral("Find object appearances, review moments and save results."));
    move_action("smoothPlayback",QStringLiteral("Playback"),"smooth",QStringLiteral("Prepare detections once for smooth video playback."));
    move_action("liveCamera",QStringLiteral("Camera"),"camera",QStringLiteral("Open camera controls. Capture starts only when you choose Start."));
    nav->addStretch();auto* local=new QLabel(QStringLiteral("LOCAL WORKSPACE"));local->setProperty("role","section");local->setContentsMargins(7,0,0,0);nav->addWidget(local);
    auto* note=new QLabel(QStringLiteral("Your files stay\non this device."));note->setProperty("role","muted");note->setContentsMargins(7,4,0,0);nav->addWidget(note);
    auto* splitter=new QSplitter(Qt::Horizontal);splitter->setObjectName(QStringLiteral("workspaceSplitter"));splitter->setHandleWidth(6);splitter->setChildrenCollapsible(false);
    workspace->removeWidget(video);workspace->removeWidget(scroll);splitter->addWidget(video);splitter->addWidget(scroll);
    splitter->setStretchFactor(0,1);splitter->setStretchFactor(1,0);splitter->setSizes({830,288});workspace->addWidget(rail);workspace->addWidget(splitter,1);
    scroll->setMaximumWidth(390);scroll->setMinimumWidth(276);scroll->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);inspector->setMinimumWidth(0);inspector->setMaximumWidth(QWIDGETSIZE_MAX);
    auto* tabs=new QTabWidget;tabs->setObjectName(QStringLiteral("inspectorTabs"));tabs->setDocumentMode(true);tabs->tabBar()->setDrawBase(false);
    const auto page=[&](const QString& title,const QStringList& names) {
        auto* widget=new QWidget;auto* layout=new QVBoxLayout(widget);layout->setContentsMargins(2,18,2,10);layout->setSpacing(11);
        for(const auto& name:names) {
            auto* control=window->findChild<QWidget*>(name);if(!control)throw std::runtime_error(("Missing inspector control: "+name).toStdString());options->removeWidget(control);layout->addWidget(control);
            if(auto* box=qobject_cast<QComboBox*>(control)) {box->setSizeAdjustPolicy(QComboBox::AdjustToMinimumContentsLengthWithIcon);box->setMinimumContentsLength(12);box->setMinimumWidth(0);box->setSizePolicy(QSizePolicy::Ignored,QSizePolicy::Fixed);}
        }
        layout->addStretch();tabs->addTab(widget,title);
    };
    for(auto* label:inspector->findChildren<QLabel*>())if(label->text()==QStringLiteral("PROCESSING DEVICE"))label->setObjectName(QStringLiteral("deviceCaption"));
    page(QStringLiteral("Detection"),{"analysisSection","detectObjects","modelLabel","modelSelection","deviceCaption","backendSelection","confidenceLabel","confidence"});
    page(QStringLiteral("Tracking"),{"trackingSection","trackObjects","classesLabel","trackingClasses","directionLabel","crossingDirection","drawLine","lineHint"});
    tabs->findChild<QLabel*>(QStringLiteral("analysisSection"))->setText(QStringLiteral("OBJECT RECOGNITION"));
    tabs->findChild<QLabel*>(QStringLiteral("trackingSection"))->setText(QStringLiteral("MOVEMENT & COUNTING"));
    window->findChild<QLabel*>(QStringLiteral("crossingsSection"))->setText(QStringLiteral("SESSION COUNTS"));
    QObject::connect(tabs,&QTabWidget::currentChanged,tabs,[tabs](int index){
        auto* page=tabs->widget(index);auto* effect=new QGraphicsOpacityEffect(page);page->setGraphicsEffect(effect);
        auto* fade=new QPropertyAnimation(effect,"opacity",page);fade->setDuration(140);fade->setStartValue(.65);fade->setEndValue(1.);fade->setEasingCurve(QEasingCurve::OutCubic);
        QObject::connect(fade,&QPropertyAnimation::finished,page,[page]{page->setGraphicsEffect(nullptr);});fade->start(QAbstractAnimation::DeleteWhenStopped);
    });
    options->insertWidget(0,tabs,1);options->setContentsMargins(14,14,14,16);options->setSpacing(10);
    auto* toggle=new QPushButton(QStringLiteral("Inspector"));toggle->setObjectName(QStringLiteral("toggleInspector"));toggle->setCheckable(true);toggle->setChecked(true);studio_button(toggle,"inspector");toggle->setToolTip(QStringLiteral("Toggle inspector \u00b7 Ctrl+I"));
    header->addWidget(toggle);QObject::connect(toggle,&QPushButton::toggled,scroll,&QWidget::setVisible);
    auto* shortcut=new QShortcut(QKeySequence(QStringLiteral("Ctrl+I")),window);QObject::connect(shortcut,&QShortcut::activated,toggle,&QPushButton::toggle);
    studio_button(window->findChild<QPushButton*>(QStringLiteral("open")),"open");
    for(const auto& pair:{std::pair{"play","play"},std::pair{"stop","stop"},std::pair{"replay","replay"},std::pair{"drawLine","analyse"}})studio_button(window->findChild<QPushButton*>(QString::fromLatin1(pair.first)),QString::fromLatin1(pair.second));
    // Wrap the existing transport layout without replacing its controls or signals.
    video_column->removeItem(playback);auto* bar=new QFrame;bar->setObjectName(QStringLiteral("transportBar"));bar->setLayout(playback);playback->setContentsMargins(10,9,12,9);playback->setSpacing(8);video_column->insertWidget(2,bar);video_column->setSpacing(9);
    window->resize(1400,900);
}
