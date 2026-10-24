#include "home_workspace.hpp"
#include "recent_files.hpp"
#include "studio_controls.hpp"
#include <QDir>
#include <QDragEnterEvent>
#include <QDropEvent>
#include <QFileInfo>
#include <QFrame>
#include <QGridLayout>
#include <QLabel>
#include <QListWidget>
#include <QMimeData>
#include <QPushButton>
#include <QScrollArea>
#include <QUrl>
#include <QVBoxLayout>

namespace {
QString dropped(const QMimeData* data) {
    if(!data->hasUrls() || data->urls().size()!=1 || !data->urls()[0].isLocalFile())return {};
    const QFileInfo file(data->urls()[0].toLocalFile());
    return file.isFile() ? file.absoluteFilePath() : QString{};
}
QString when(const QDateTime& time) {
    const auto days=time.date().daysTo(QDate::currentDate());
    if(days==0)return QStringLiteral("Today %1").arg(time.time().toString(QStringLiteral("HH:mm")));
    if(days==1)return QStringLiteral("Yesterday");
    return time.date().toString(days<300 ? QStringLiteral("d MMM") : QStringLiteral("d MMM yyyy"));
}
QString kind(const QString& path) {
    const auto suffix=QFileInfo(path).suffix().toLower();
    if(suffix==QStringLiteral("frametrail"))return QStringLiteral("document");
    for(const char* image:{"png","jpg","jpeg","bmp","ppm"})if(suffix==QLatin1StringView(image))return QStringLiteral("image");
    return QStringLiteral("video");
}
QPixmap tile(const QString& icon,const QColor& color,int size=40) {
    QPixmap pixmap(QSize(size,size)*2);pixmap.setDevicePixelRatio(2);pixmap.fill(Qt::transparent);
    QPainter painter(&pixmap);painter.setRenderHint(QPainter::Antialiasing);
    auto fill=color;fill.setAlpha(38);painter.setPen(Qt::NoPen);painter.setBrush(fill);painter.drawRoundedRect(QRectF(0,0,size,size),10,10);
    const int glyph=size/2;painter.drawPixmap(QPointF((size-glyph)/2.,(size-glyph)/2.),fluent_pixmap(icon,color,glyph));
    return pixmap;
}
QLabel* label(const QString& text,const char* role=nullptr,bool wrap=false) {
    auto* out=new QLabel(text);if(role)out->setProperty("role",role);out->setWordWrap(wrap);out->setTextFormat(Qt::PlainText);
    out->setAttribute(Qt::WA_TransparentForMouseEvents);return out;
}
}

HomeWorkspace::HomeWorkspace(QWidget* parent):QWidget(parent) {
    setObjectName(QStringLiteral("homeWorkspace"));setAcceptDrops(true);
    auto* outer=new QVBoxLayout(this);outer->setContentsMargins(0,0,0,0);
    auto* scroll=new QScrollArea;scroll->setWidgetResizable(true);scroll->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);outer->addWidget(scroll);
    auto* page=new QWidget;scroll->setWidget(page);
    auto* centre=new QHBoxLayout(page);centre->setContentsMargins(32,28,32,28);
    auto* content=new QWidget;content->setMaximumWidth(1160);centre->addWidget(content);
    auto* layout=new QVBoxLayout(content);layout->setContentsMargins(0,0,0,0);layout->setSpacing(18);

    auto* title=new QLabel(QStringLiteral("What would you like to look at?"));title->setObjectName(QStringLiteral("display"));layout->addWidget(title);
    layout->addWidget(label(QStringLiteral("Detect, track and count objects in videos, photos and your webcam. Everything runs on this PC."),"muted",true));

    // Drop zone with the two ways in.
    auto* drop=new QFrame;drop->setObjectName(QStringLiteral("dropZone"));drop->setMinimumHeight(176);
    auto* drop_layout=new QVBoxLayout(drop);drop_layout->setContentsMargins(24,26,24,24);drop_layout->setSpacing(6);drop_layout->setAlignment(Qt::AlignCenter);
    auto* drop_icon=new QLabel;drop_icon->setPixmap(tile(QStringLiteral("upload"),ft::ui::accent(),52));drop_icon->setAlignment(Qt::AlignCenter);drop_layout->addWidget(drop_icon);
    auto* drop_title=label(QStringLiteral("Drop a video or photo here"));drop_title->setObjectName(QStringLiteral("cardTitle"));drop_title->setAlignment(Qt::AlignCenter);drop_layout->addWidget(drop_title);
    auto* formats=label(QStringLiteral("MP4 · MOV · MKV · AVI · WebM · JPG · PNG, or a saved .frametrail analysis"),"caption");formats->setAlignment(Qt::AlignCenter);drop_layout->addWidget(formats);
    auto* buttons=new QHBoxLayout;buttons->setSpacing(10);buttons->addStretch();
    auto* open=new QPushButton(QStringLiteral("Open media"));open->setObjectName(QStringLiteral("homeOpen"));open->setProperty("role","primary");studio_button(open,QStringLiteral("open"));buttons->addWidget(open);
    auto* reopen=new QPushButton(QStringLiteral("Open saved analysis"));reopen->setObjectName(QStringLiteral("homeOpenAnalysis"));studio_button(reopen,QStringLiteral("history"));buttons->addWidget(reopen);
    buttons->addStretch();drop_layout->addSpacing(8);drop_layout->addLayout(buttons);layout->addWidget(drop);
    connect(open,&QPushButton::clicked,this,[this]{if(open_media)open_media();});
    connect(reopen,&QPushButton::clicked,this,[this]{if(open_analysis)open_analysis();});

    // Tools.
    auto* tools_title=new QLabel(QStringLiteral("Tools"));tools_title->setProperty("role","section");layout->addWidget(tools_title);
    auto* tools=new QGridLayout;tools->setSpacing(12);
    struct Tool {int section; const char* icon; const char* name; const char* text; const char* key;};
    const Tool list[]={
        {0,"preview","Watch with detection","Play a video or photo and see objects as they appear. Draw a line to count crossings.","Ctrl+1"},
        {1,"analysis","Find every appearance","Scan a whole video once, then jump to each object, save the result or export a table.","Ctrl+2"},
        {2,"playback","Smooth playback","Prepare detections first, then watch without stutter on slower PCs.","Ctrl+3"},
        {3,"camera","Live camera","Detect, track and count from a webcam. Nothing is recorded.","Ctrl+4"}};
    int column=0;
    for(const auto& tool:list) {
        auto* card=new QPushButton;card->setObjectName(QStringLiteral("tool%1").arg(tool.section));card->setProperty("role","card");card->setCursor(Qt::PointingHandCursor);
        card->setMinimumHeight(150);card->setSizePolicy(QSizePolicy::Expanding,QSizePolicy::Fixed);
        auto* card_layout=new QVBoxLayout(card);card_layout->setContentsMargins(18,18,18,16);card_layout->setSpacing(6);
        auto* icon=new QLabel;icon->setPixmap(tile(QString::fromLatin1(tool.icon),ft::ui::category_color(tool.section*3)));icon->setAttribute(Qt::WA_TransparentForMouseEvents);card_layout->addWidget(icon);
        card_layout->addSpacing(4);
        auto* name=label(QString::fromLatin1(tool.name));name->setObjectName(QStringLiteral("cardTitle"));card_layout->addWidget(name);
        card_layout->addWidget(label(QString::fromLatin1(tool.text),"muted",true),1);
        card_layout->addWidget(label(QString::fromLatin1(tool.key),"caption"));
        const int section=tool.section;connect(card,&QPushButton::clicked,this,[this,section]{if(navigate)navigate(section);});
        tools->addWidget(card,0,column++,Qt::AlignTop);
    }
    layout->addLayout(tools);

    // Recent files and the detector setup.
    auto* lower=new QHBoxLayout;lower->setSpacing(12);
    auto* recent_card=new QFrame;recent_card->setObjectName(QStringLiteral("card"));
    auto* recent_layout=new QVBoxLayout(recent_card);recent_layout->setContentsMargins(16,14,16,12);recent_layout->setSpacing(6);
    auto* recent_head=new QHBoxLayout;auto* recent_title=new QLabel(QStringLiteral("Recent"));recent_title->setProperty("role","section");recent_head->addWidget(recent_title);recent_head->addStretch();
    clear_=new QPushButton(QStringLiteral("Clear"));clear_->setProperty("role","subtle");clear_->setObjectName(QStringLiteral("clearRecent"));recent_head->addWidget(clear_);recent_layout->addLayout(recent_head);
    recent_=new QListWidget;recent_->setObjectName(QStringLiteral("recentFiles"));recent_->setIconSize(QSize(36,36));recent_->setMinimumHeight(200);recent_->setAcceptDrops(false);recent_layout->addWidget(recent_,1);
    recent_empty_=label(QStringLiteral("Videos, photos and analyses you open will appear here."),"muted",true);recent_layout->addWidget(recent_empty_);
    lower->addWidget(recent_card,2);
    connect(recent_,&QListWidget::itemActivated,this,[this](QListWidgetItem* item){if(open_path)open_path(item->data(Qt::UserRole).toString());});
    connect(recent_,&QListWidget::itemClicked,this,[this](QListWidgetItem* item){if(open_path)open_path(item->data(Qt::UserRole).toString());});
    connect(clear_,&QPushButton::clicked,this,[this]{clear_recent_files();refresh();});

    auto* setup_card=new QFrame;setup_card->setObjectName(QStringLiteral("card"));
    auto* setup_layout=new QVBoxLayout(setup_card);setup_layout->setContentsMargins(16,14,16,16);setup_layout->setSpacing(8);
    auto* setup_title=new QLabel(QStringLiteral("Detector"));setup_title->setProperty("role","section");setup_layout->addWidget(setup_title);
    auto* setup_icon=new QLabel;setup_icon->setPixmap(tile(QStringLiteral("brand"),ft::ui::accent()));setup_layout->addWidget(setup_icon);
    model_=label(QString(),nullptr,true);model_->setObjectName(QStringLiteral("cardTitle"));setup_layout->addWidget(model_);
    details_=label(QString(),"muted",true);setup_layout->addWidget(details_);setup_layout->addStretch();
    auto* change=new QPushButton(QStringLiteral("Change detection settings"));change->setObjectName(QStringLiteral("homeSettings"));studio_button(change,QStringLiteral("settings"));setup_layout->addWidget(change);
    connect(change,&QPushButton::clicked,this,[this]{if(navigate)navigate(0);});
    auto* privacy=new QHBoxLayout;privacy->setSpacing(8);auto* shield=new QLabel;shield->setPixmap(fluent_pixmap(QStringLiteral("local"),ft::ui::success,16));privacy->addWidget(shield,0,Qt::AlignTop);
    privacy->addWidget(label(QStringLiteral("Private: files and results never leave this PC."),"caption",true),1);setup_layout->addLayout(privacy);
    lower->addWidget(setup_card,1);
    layout->addLayout(lower);layout->addStretch();
}
void HomeWorkspace::refresh() {
    recent_->clear();
    for(const auto& file:recent_files()) {
        const QFileInfo info(file.path);
        auto* item=new QListWidgetItem(QIcon(tile(kind(file.path),info.exists() ? ft::ui::text_secondary : ft::ui::text_disabled,36)),
            QStringLiteral("%1\n%2  ·  %3").arg(info.fileName(),info.exists() ? when(file.opened) : QStringLiteral("missing"),QDir::toNativeSeparators(info.absolutePath())),recent_);
        item->setData(Qt::UserRole,file.path);item->setToolTip(QDir::toNativeSeparators(file.path));item->setSizeHint(QSize(0,60));
        if(!info.exists())item->setFlags(item->flags()&~Qt::ItemIsEnabled);
    }
    recent_->setVisible(recent_->count()>0);recent_empty_->setVisible(recent_->count()==0);clear_->setVisible(recent_->count()>0);
    const auto lines=setup ? setup() : QStringList{};
    model_->setText(lines.value(0));details_->setText(lines.mid(1).join(QLatin1Char('\n')));
}
void HomeWorkspace::showEvent(QShowEvent* event) {QWidget::showEvent(event);refresh();}
void HomeWorkspace::dragEnterEvent(QDragEnterEvent* event) {if(!dropped(event->mimeData()).isEmpty())event->acceptProposedAction();}
void HomeWorkspace::dropEvent(QDropEvent* event) {
    const auto path=dropped(event->mimeData());
    if(!path.isEmpty() && open_path){event->acceptProposedAction();open_path(path);}
}
