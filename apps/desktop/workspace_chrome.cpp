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
    if(!workspace || !header || !video || !scroll || !inspector || !options || !root || !video_column || !playback)throw std::runtime_error("Workspace layout contract missing");
    root->setContentsMargins(18,14,18,16);root->setSpacing(16);workspace->setSpacing(10);header->setSpacing(10);
    auto* branding=window->findChild<QVBoxLayout*>(QStringLiteral("branding"));branding->setSpacing(3);
    window->findChild<QLabel*>(QStringLiteral("subtitle"))->setText(QStringLiteral("Workspace / Preview"));studio_heading(header);
    auto* activity=new QLabel(QStringLiteral("All work stays local"));activity->setObjectName(QStringLiteral("workspaceActivity"));activity->setProperty("role","badge");activity->setTextFormat(Qt::PlainText);header->addWidget(activity);
    window->findChild<QLabel*>(QStringLiteral("source"))->setText(QStringLiteral("Preview  /  Untitled media"));
    window->findChild<QLabel*>(QStringLiteral("details"))->setText(QStringLiteral("Local processing  \u00b7  Ctrl+O  Open media     Space  Play / pause"));
    auto* rail=new QFrame;rail->setObjectName(QStringLiteral("workspaceRail"));rail->setFixedWidth(164);
    auto* nav=new QVBoxLayout(rail);nav->setContentsMargins(10,18,10,16);nav->setSpacing(5);
    auto* section=new QLabel(QStringLiteral("WORKSPACE"));section->setProperty("role","section");section->setContentsMargins(8,0,0,10);nav->addWidget(section);
    auto* group=new QButtonGroup(window);group->setExclusive(true);
    auto* current=new QPushButton(QStringLiteral("Preview"));current->setObjectName(QStringLiteral("previewWorkspace"));current->setProperty("role","navigation");current->setCheckable(true);current->setChecked(true);studio_button(current,"play");nav->addWidget(current);group->addButton(current,0);
    current->setToolTip(QStringLiteral("Preview media · Ctrl+1"));
    const auto move_action=[&](const char* name,const QString& label,const QString& icon,const QString& hint) {
        auto* button=window->findChild<QPushButton*>(QString::fromLatin1(name));if(!button)throw std::runtime_error(name);header->removeWidget(button);
        button->setText(label);button->setToolTip(hint);button->setProperty("role","navigation");studio_button(button,icon);
        button->setSizePolicy(QSizePolicy::Expanding,QSizePolicy::Fixed);button->setCheckable(true);group->addButton(button,group->buttons().size());nav->addWidget(button);
    };
    move_action("savedAnalysis",QStringLiteral("Analysis"),"analyse",QStringLiteral("Find and review object appearances · Ctrl+2"));
    move_action("smoothPlayback",QStringLiteral("Playback"),"smooth",QStringLiteral("Prepare once for smooth playback · Ctrl+3"));
    move_action("liveCamera",QStringLiteral("Camera"),"camera",QStringLiteral("Camera opens only on Start and stops when leaving · Ctrl+4"));
    nav->addStretch();
    auto* guide=new QPushButton(QStringLiteral("Quick Guide"));guide->setObjectName(QStringLiteral("quickGuide"));guide->setProperty("role","navigation");guide->setCheckable(true);guide->setToolTip(QStringLiteral("Find tasks, shortcuts and object categories · Ctrl+K / F1"));studio_button(guide,"guide");group->addButton(guide,4);nav->addWidget(guide);
    auto* local=new QLabel(QStringLiteral("LOCAL WORKSPACE"));local->setProperty("role","section");local->setContentsMargins(7,14,0,0);nav->addWidget(local);
    auto* note=new QLabel(QStringLiteral("Ctrl+1–4 to switch\nCtrl+K to find a task"));note->setProperty("role","muted");note->setContentsMargins(7,4,0,0);nav->addWidget(note);
    auto* splitter=new QSplitter(Qt::Horizontal);splitter->setObjectName(QStringLiteral("workspaceSplitter"));splitter->setHandleWidth(6);splitter->setChildrenCollapsible(false);
    workspace->removeWidget(video);workspace->removeWidget(scroll);splitter->addWidget(video);splitter->addWidget(scroll);
    splitter->setStretchFactor(0,1);splitter->setStretchFactor(1,0);splitter->setSizes({830,288});workspace->addWidget(rail);
    auto* pages=new QStackedWidget;pages->setObjectName(QStringLiteral("workspacePages"));pages->addWidget(splitter);workspace->addWidget(pages,1);
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
    auto* shortcut=new QShortcut(QKeySequence(QStringLiteral("Ctrl+I")),window);QObject::connect(shortcut,&QShortcut::activated,window,[toggle,pages]{if(pages->currentIndex()==0)toggle->toggle();});
    studio_button(window->findChild<QPushButton*>(QStringLiteral("open")),"open");
    for(const auto& pair:{std::pair{"play","play"},std::pair{"stop","stop"},std::pair{"replay","replay"},std::pair{"drawLine","analyse"}})studio_button(window->findChild<QPushButton*>(QString::fromLatin1(pair.first)),QString::fromLatin1(pair.second));
    // Wrap the existing transport layout without replacing its controls or signals.
    video_column->removeItem(playback);auto* bar=new QFrame;bar->setObjectName(QStringLiteral("transportBar"));bar->setLayout(playback);playback->setContentsMargins(10,9,12,9);playback->setSpacing(8);video_column->insertWidget(2,bar);video_column->setSpacing(9);
    window->resize(1400,900);
}
