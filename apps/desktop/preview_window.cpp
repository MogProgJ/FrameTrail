#include "preview_window.hpp"
#include "guide_workspace.hpp"
#include "model_selection.hpp"
#include "saved_run_window.hpp"
#include "cached_playback_window.hpp"
#include "live_window.hpp"
#include "theme.hpp"
#include "studio_controls.hpp"
#include "workspace_chrome.hpp"
#include "playback_workspace.hpp"
#include "home_workspace.hpp"
#include "recent_files.hpp"
#include <QSlider>
#include "timeline_slider.hpp"
#include <QDir>
#include <QStandardPaths>
#include <QSignalBlocker>
#include <map>
#include <QStackedWidget>
#include <QStyle>
#include <QDragEnterEvent>
#include <QDropEvent>
#include <QMimeData>
#include <QUrl>
#include <QShortcut>
#include <QKeyEvent>
#include <QLineEdit>
#include <QPropertyAnimation>
#include <QGraphicsOpacityEffect>
#include "ui_preview_layout.h"

#include <QCloseEvent>
#include <QCoreApplication>
#include <QCheckBox>
#include <QDoubleSpinBox>
#include <QComboBox>
#include <QMouseEvent>
#include <QFileDialog>
#include <QFileInfo>
#include <QHBoxLayout>
#include <QLabel>
#include <QPainter>
#include <QPainterPath>
#include <QPushButton>
#include <QVBoxLayout>
#include <algorithm>
#include <cmath>

namespace {
std::filesystem::path native_path(const QString& value) {
#ifdef _WIN32
    return std::filesystem::path(value.toStdWString());
#else
    const auto bytes = value.toUtf8();
    return std::filesystem::path(std::u8string(bytes.begin(), bytes.end()));
#endif
}

// Space is play/pause everywhere in Preview. A focused spin box would otherwise take it as typing.
class SpaceForPlayback final : public QObject {
public:
    using QObject::QObject;
protected:
    bool eventFilter(QObject*,QEvent* event) override {
        if(event->type()!=QEvent::ShortcutOverride)return false;
        const auto* key=static_cast<QKeyEvent*>(event);
        return key->key()==Qt::Key_Space && key->modifiers()==Qt::NoModifier;
    }
};

QString timestamp_text(const std::optional<std::chrono::microseconds>& timestamp) {
    if (!timestamp) return QStringLiteral("Unknown time");
    const auto ms = std::max<std::int64_t>(0, timestamp->count() / 1000);
    return QStringLiteral("%1:%2:%3.%4")
        .arg(ms / 3600000, 2, 10, QChar('0'))
        .arg((ms / 60000) % 60, 2, 10, QChar('0'))
        .arg((ms / 1000) % 60, 2, 10, QChar('0'))
        .arg(ms % 1000, 3, 10, QChar('0'));
}
bool still_image(const QString& path) {
    const auto suffix=QFileInfo(path).suffix().toLower();
    return suffix==QStringLiteral("png") || suffix==QStringLiteral("jpg") || suffix==QStringLiteral("jpeg") || suffix==QStringLiteral("bmp") || suffix==QStringLiteral("ppm");
}
QString clock_text(std::chrono::microseconds time) {
    const auto total=std::max<std::int64_t>(0,time.count()/1000000);
    return total>=3600 ? QStringLiteral("%1:%2:%3").arg(total/3600).arg(total/60%60,2,10,QChar('0')).arg(total%60,2,10,QChar('0'))
                       : QStringLiteral("%1:%2").arg(total/60).arg(total%60,2,10,QChar('0'));
}
} // namespace

FrameCanvas::FrameCanvas(QWidget* parent) : QWidget(parent) {
    setMinimumSize(320, 220);
    setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Expanding);
    setObjectName(QStringLiteral("frameCanvas"));
}

void FrameCanvas::set_image(QImage image, std::vector<frametrail::Detection> objects,
    std::vector<frametrail::TrackedObject> tracks, std::optional<frametrail::CountingLine> line) {
    image_ = std::move(image);
    glow_ = image_.isNull() ? QImage{} : image_.scaled(96,54,Qt::IgnoreAspectRatio,Qt::FastTransformation).scaled(24,14,Qt::IgnoreAspectRatio,Qt::SmoothTransformation);
    objects_ = std::move(objects);
    tracks_ = std::move(tracks);
    line_ = std::move(line);
    if (image_.isNull()) { selecting_line_ = false; first_point_.reset(); unsetCursor(); }
    update();
}

QRect FrameCanvas::image_rect() const {
    const auto scaled = image_.size().scaled(size(), Qt::KeepAspectRatio);
    return {(width()-scaled.width())/2,(height()-scaled.height())/2,scaled.width(),scaled.height()};
}
void FrameCanvas::begin_line_selection() {
    if (image_.isNull()) return;
    selecting_line_ = true; first_point_.reset(); setCursor(Qt::CrossCursor); update();
}
void FrameCanvas::cancel_line_selection(bool notify) {
    if (!selecting_line_) return;
    selecting_line_ = false; first_point_.reset(); unsetCursor(); update();
    if (notify && line_cancelled) line_cancelled();
}
void FrameCanvas::mousePressEvent(QMouseEvent* event) {
    if (!selecting_line_ || image_.isNull()) return;
    if (event->button() == Qt::RightButton) {
        cancel_line_selection(); return;
    }
    const auto target = image_rect();
    if (event->button() != Qt::LeftButton || !target.contains(event->position().toPoint())) return;
    frametrail::Point p{(event->position().x()-target.left())/target.width(),
        (event->position().y()-target.top())/target.height()};
    if (!first_point_) { first_point_ = p; update(); return; }
    if (std::hypot(p.x-first_point_->x,p.y-first_point_->y) < 0.05) return;
    auto line = line_.value_or(frametrail::CountingLine{});
    line.a = *first_point_; line.b = p;
    selecting_line_ = false; first_point_.reset(); unsetCursor(); line_ = line; update();
    if (line_selected) line_selected(line);
}

void FrameCanvas::paintEvent(QPaintEvent*) {
    QPainter painter(this);
    painter.setRenderHint(QPainter::Antialiasing);
    QPainterPath surface;surface.addRoundedRect(QRectF(rect()).adjusted(.5,.5,-.5,-.5),8,8);
    painter.fillPath(surface,ft::ui::canvas);painter.setPen(QPen(ft::ui::stroke,1));painter.drawPath(surface);
    painter.setClipPath(surface);
    if (image_.isNull()) {
        const bool preview=empty_text_==QStringLiteral("Open an image or video to begin");
        const auto lines=empty_text_.split('\n');
        const auto title=preview?QStringLiteral("Open a video or image"):lines.first();
        const auto hint=preview?QStringLiteral("Drop a file here, or choose Open media."):lines.mid(1).join('\n');
        const auto center=rect().center();
        if(preview && width()>360 && height()>260) {
            const QRectF zone=QRectF(rect()).adjusted(24,24,-24,-24);
            painter.setPen(QPen(QColor("#3a3a3a"),1.2,Qt::DashLine));painter.setBrush(Qt::NoBrush);painter.drawRoundedRect(zone,8,8);
        }
        const QRectF badge(center.x()-28,center.y()-104,56,56);
        painter.setPen(Qt::NoPen);painter.setBrush(QColor("#232323"));painter.drawRoundedRect(badge,12,12);
        painter.drawPixmap(badge.center()-QPointF(14,14),fluent_pixmap(empty_icon_,ft::ui::accent(),28));
        auto title_font=painter.font();title_font.setPixelSize(width()<540?18:20);title_font.setWeight(QFont::DemiBold);painter.setFont(title_font);painter.setPen(ft::ui::text);
        painter.drawText(QRect(22,center.y()-30,width()-44,32),Qt::AlignHCenter|Qt::AlignTop|Qt::TextWordWrap,title);
        auto hint_font=painter.font();hint_font.setPixelSize(14);hint_font.setWeight(QFont::Normal);painter.setFont(hint_font);painter.setPen(ft::ui::text_secondary);
        painter.drawText(QRect(28,center.y()+8,width()-56,64),Qt::AlignHCenter|Qt::AlignTop|Qt::TextWordWrap,hint);
        if(preview){painter.setPen(ft::ui::text_tertiary);hint_font.setPixelSize(12);painter.setFont(hint_font);painter.drawText(QRect(20,center.y()+60,width()-40,22),Qt::AlignCenter,QStringLiteral("MP4 · MOV · MKV · AVI · WebM · JPG · PNG     Ctrl+O"));}
        return;
    }
    const QRect target = image_rect();
    painter.setRenderHint(QPainter::SmoothPixmapTransform);
    if(ambient_ && !glow_.isNull()) {
        painter.setOpacity(.6);painter.drawImage(QRectF(rect()).adjusted(-40,-40,40,40),glow_);painter.setOpacity(1);
        painter.fillRect(rect(),QColor(17,17,17,150));
    }
    painter.drawImage(target, image_);
    painter.setClipRect(target);
    draw_overlays(painter,target);
    if (selecting_line_) {
        const auto screen=[&](frametrail::Point p){return QPointF(target.left()+p.x*target.width(),target.top()+p.y*target.height());};
        auto font=painter.font();font.setPixelSize(13);font.setWeight(QFont::DemiBold);painter.setFont(font);
        if (first_point_) {
            const QRectF circle(screen(*first_point_).x()-9,screen(*first_point_).y()-9,18,18);painter.setPen(Qt::NoPen);painter.setBrush(ft::ui::line_color);painter.drawEllipse(circle);
            painter.setPen(QColor("#101010"));painter.drawText(circle,Qt::AlignCenter,QStringLiteral("A"));
        }
        const auto text=first_point_ ? QStringLiteral("Click point B   ·   right-click to cancel") : QStringLiteral("Click point A   ·   right-click to cancel");
        font.setWeight(QFont::Normal);painter.setFont(font);
        const auto size=painter.fontMetrics().size(Qt::TextSingleLine,text);
        const QRectF banner(target.left()+12,target.top()+12,size.width()+24,size.height()+12);
        painter.setPen(Qt::NoPen);painter.setBrush(QColor(20,20,20,225));painter.drawRoundedRect(banner,6,6);
        painter.setPen(ft::ui::line_color);painter.drawText(banner,Qt::AlignCenter,text);
    }
}

QImage FrameCanvas::annotated_image() const {
    if(image_.isNull())return {};
    QImage out=image_.convertToFormat(QImage::Format_RGB32);
    QPainter painter(&out);painter.setRenderHint(QPainter::Antialiasing);
    // Draw overlays as they look on a ~1280 px wide view, so lines and labels stay readable on large frames.
    const double scale=std::max(1.,out.width()/1280.);painter.scale(scale,scale);
    draw_overlays(painter,QRect(0,0,int(out.width()/scale),int(out.height()/scale)));
    return out;
}

void FrameCanvas::draw_overlays(QPainter& painter,const QRect& target) const {
    auto label_font=painter.font();label_font.setPixelSize(12);label_font.setWeight(QFont::DemiBold);painter.setFont(label_font);
    const double sx=double(target.width())/image_.width(), sy=double(target.height())/image_.height();
    for (const auto& object:objects_) {
        const frametrail::TrackedObject* matched{};
        for(const auto& track:tracks_)if(track.detection.class_id==object.class_id && track.detection.left==object.left &&
            track.detection.top==object.top && track.detection.right==object.right && track.detection.bottom==object.bottom){matched=&track;break;}
        const bool tentative=temporal_style_ && matched && !matched->confirmed;
        QColor color=temporal_style_ && matched ? (matched->confirmed ? ft::ui::category_color(int(matched->id%97)):QColor("#a6a6a6")):
            ft::ui::category_color(object.class_id);
        if(focus_class_ && object.class_id!=*focus_class_) {
            color.setAlpha(70);painter.setPen(QPen(color,1.5));painter.setBrush(Qt::NoBrush);
            painter.drawRoundedRect(QRectF(target.left()+object.left*sx,target.top()+object.top*sy,(object.right-object.left)*sx,(object.bottom-object.top)*sy),4,4);
            continue;
        }
        const QRectF box(target.left()+object.left*sx, target.top()+object.top*sy,
            (object.right-object.left)*sx, (object.bottom-object.top)*sy);
        auto fill=color;fill.setAlpha(22);
        painter.setPen(QPen(color,2,tentative ? Qt::DashLine:Qt::SolidLine));painter.setBrush(fill);
        painter.drawRoundedRect(box,4,4);
        auto label=QStringLiteral("%1  %2%")
            .arg(QString::fromUtf8(frametrail::class_name(object.class_id).data()))
            .arg(qRound(object.confidence*100));
        if(matched)label += QStringLiteral("  #%1%2").arg(matched->id).arg(matched->confirmed ? QString{} : QStringLiteral("?"));
        const auto text_size=painter.fontMetrics().size(Qt::TextSingleLine,label);
        const QSizeF pill(text_size.width()+12,text_size.height()+4);
        const double label_x=std::clamp(box.left(),double(target.left()),std::max(double(target.left()),double(target.right())-pill.width()));
        const double above=box.top()-pill.height()-3;
        const double label_y=above>=target.top() ? above : std::min(box.top()+3,double(target.bottom())-pill.height());
        const QRectF label_box(QPointF(label_x,label_y),pill);
        painter.setPen(Qt::NoPen);painter.setBrush(color);painter.drawRoundedRect(label_box,4,4);
        painter.setPen(QColor("#101010"));
        painter.drawText(label_box,Qt::AlignCenter,label);
    }
    const auto screen = [&](frametrail::Point p) {
        return QPointF(target.left()+p.x*target.width(),target.top()+p.y*target.height());
    };
    for (const auto& track : tracks_) {
        if(focus_class_ && track.detection.class_id!=*focus_class_)continue;
        auto color=ft::ui::category_color(int(track.id%97));
        for (std::size_t i=1;i<track.trail.size();++i) {
            if(temporal_style_)color.setAlpha(50+int(180*i/(track.trail.size()-1)));
            painter.setPen(QPen(color,2.5,Qt::SolidLine,Qt::RoundCap));painter.drawLine(screen(track.trail[i-1]),screen(track.trail[i]));
        }
    }
    const auto marker=[&](QPointF center,const QString& text){
        const QRectF circle(center.x()-9,center.y()-9,18,18);painter.setPen(Qt::NoPen);painter.setBrush(ft::ui::line_color);painter.drawEllipse(circle);
        painter.setPen(QColor("#101010"));painter.drawText(circle,Qt::AlignCenter,text);
    };
    if (line_) {
        painter.setPen(QPen(ft::ui::line_color,3,Qt::SolidLine,Qt::RoundCap));
        painter.drawLine(screen(line_->a),screen(line_->b));
        const auto dx=line_->b.x-line_->a.x,dy=line_->b.y-line_->a.y;
        const auto norm=std::max(1e-9,std::hypot(dx,dy));
        const frametrail::Point middle{(line_->a.x+line_->b.x)/2,(line_->a.y+line_->b.y)/2};
        marker(screen(line_->a),QStringLiteral("A"));marker(screen(line_->b),QStringLiteral("B"));
        marker(screen({middle.x-dy/norm*0.05,middle.y+dx/norm*0.05}),QStringLiteral("+"));
        marker(screen({middle.x+dy/norm*0.05,middle.y-dx/norm*0.05}),QStringLiteral("−"));
    }
}

PreviewWindow::PreviewWindow(const QString& model_path) {
    model_path_=model_path.isEmpty() ? QCoreApplication::applicationDirPath()+QStringLiteral("/models/yolox_nano.onnx") : model_path;
    Ui::PreviewLayout ui;
    ui.setupUi(this);
    setWindowTitle(QStringLiteral("FrameTrail — Video workspace"));
    setMinimumSize(900, 600);
    install_studio_style();setStyleSheet(frametrail_theme());
    ui.rootLayout->setContentsMargins(24, 22, 24, 22); ui.rootLayout->setSpacing(22);
    ui.header->setStretch(0, 1);
    ui.playback->setStretch(3, 1);
    for (auto* button : {ui.open, ui.liveCamera, ui.savedAnalysis, ui.play, ui.stop, ui.replay}) button->setSizePolicy(QSizePolicy::Maximum, QSizePolicy::Fixed);
    ui.workspace->setStretch(0, 1); ui.videoColumn->setStretch(1, 1);
    ui.inspectorLayout->setContentsMargins(18, 20, 18, 20);
    canvas_ = ui.frameCanvas;canvas_->set_temporal_style(true);source_label_ = ui.source;
    source_label_->setTextFormat(Qt::PlainText);
    source_label_->setMinimumWidth(0); source_label_->setSizePolicy(QSizePolicy::Ignored, QSizePolicy::Preferred);
    auto* source_effect=new QGraphicsOpacityEffect(source_label_);source_label_->setGraphicsEffect(source_effect);source_effect->setOpacity(1.);
    source_transition_=new QPropertyAnimation(source_effect,"opacity",this);source_transition_->setDuration(160);
    source_transition_->setStartValue(.35);source_transition_->setEndValue(1.);source_transition_->setEasingCurve(QEasingCurve::OutCubic);
    state_label_ = ui.state; state_label_->setTextFormat(Qt::PlainText);
    details_label_ = ui.details;
    play_button_ = ui.play; stop_button_ = ui.stop; replay_button_ = ui.replay;
    for (auto* button : {play_button_, stop_button_, replay_button_}) button->setEnabled(false);
    detect_box_ = ui.detectObjects; detect_box_->setChecked(QFileInfo::exists(model_path_));
    confidence_box_ = ui.confidence; track_box_ = ui.trackObjects;
    confidence_box_->setKeyboardTracking(false); // Typed values apply once, on Enter or leaving the box, not per digit.
    {auto* space=new SpaceForPlayback(confidence_box_);confidence_box_->installEventFilter(space);
     if(auto* edit=confidence_box_->findChild<QLineEdit*>())edit->installEventFilter(space);}
    classes_box_ = ui.trackingClasses; direction_box_ = ui.crossingDirection;
    line_button_ = ui.drawLine; counts_label_ = ui.crossingCounts;

    model_box_=model_selector(model_path_,this);
    if(model_path.isEmpty()) {
        if(QFileInfo::exists(model_box_->itemData(1).toString()))model_box_->setCurrentIndex(1);
        model_path_=model_box_->currentData().toString();
    }
    ui.modelLabel->setText(frametrail::is_rf_model(selected_model(model_box_)) ? QStringLiteral("Detection model · experimental RF") : QStringLiteral("Detection model · %1 categories").arg(frametrail::model_category_count(selected_model(model_box_))));
    ui.inspectorLayout->insertWidget(ui.inspectorLayout->indexOf(ui.modelLabel)+1,model_box_);
    auto* backend_label=new QLabel(QStringLiteral("PROCESSING DEVICE"));backend_label->setProperty("role","section");
    backend_box_=backend_selector(this);backend_label->setBuddy(backend_box_);
    const auto backend_index=ui.inspectorLayout->indexOf(model_box_)+1;
    ui.inspectorLayout->insertWidget(backend_index,backend_label);ui.inspectorLayout->insertWidget(backend_index+1,backend_box_);
    detect_box_->setText(QStringLiteral("Detect objects"));
    ui.confidenceLabel->setBuddy(confidence_box_); ui.classesLabel->setBuddy(classes_box_); ui.directionLabel->setBuddy(direction_box_);
    line_button_->setToolTip(QStringLiteral("Click A then B. Right-click cancels. Playback stays at this position."));
    direction_box_->setToolTip(QStringLiteral("Sides refer to the A→B line. For a left-to-right line, + is below."));
    auto* open = ui.open;
    auto* smooth=new QPushButton(QStringLiteral("Playback"));smooth->setObjectName(QStringLiteral("smoothPlayback"));ui.header->addWidget(smooth);
    connect(ui.liveCamera,&QPushButton::clicked,this,[this]{activate_workspace(3);});
    connect(smooth,&QPushButton::clicked,this,[this]{activate_workspace(2);});
    connect(ui.savedAnalysis,&QPushButton::clicked,this,[this]{activate_workspace(1);});
    connect(open, &QPushButton::clicked, this, [this] {
        const auto path = QFileDialog::getOpenFileName(this, QStringLiteral("Open image or video"), {},
            QStringLiteral("Media (*.mp4 *.mkv *.avi *.mov *.webm *.png *.jpg *.jpeg *.bmp *.ppm);;All files (*)"));
        if (!path.isEmpty()) open_file(path);
    });
    connect(play_button_, &QPushButton::clicked, this, [this] { toggle_playback(); });
    connect(stop_button_, &QPushButton::clicked, this, [this] { stop_playback(); });
    connect(replay_button_, &QPushButton::clicked, this, [this] { open_file(source_); });
    connect(detect_box_,&QCheckBox::toggled,this,[this](bool){reconfigure_analysis();});
    connect(model_box_,&QComboBox::currentIndexChanged,this,[this,label=ui.modelLabel]{
        label->setText(frametrail::is_rf_model(selected_model(model_box_)) ? QStringLiteral("Detection model · experimental RF") : QStringLiteral("Detection model · %1 categories").arg(frametrail::model_category_count(selected_model(model_box_))));
        model_path_=model_box_->currentData().toString();
        reconfigure_analysis();
    });
    connect(backend_box_,&QComboBox::currentIndexChanged,this,[this](int){reconfigure_analysis();});
    connect(confidence_box_,&QDoubleSpinBox::valueChanged,this,[this](double){reconfigure_analysis();});
    connect(track_box_,&QCheckBox::toggled,this,[this](bool){reconfigure_analysis();});
    connect(classes_box_,&QComboBox::currentIndexChanged,this,[this](int){reconfigure_analysis();});
    connect(direction_box_,&QComboBox::currentIndexChanged,this,[this](int){reconfigure_analysis();});
    connect(line_button_,&QPushButton::clicked,this,[this] {
        if (!canvas_->image().isNull()) {
            if (!line_editing_) resume_after_line_ = playing_;
            if (playing_) toggle_playback();
            line_editing_ = true;
            canvas_->begin_line_selection();
            state_label_->setText(QStringLiteral("Select line endpoints A and B"));
            update_controls();
        }
    });
    canvas_->line_selected = [this](frametrail::CountingLine line) { counting_line_ = line; reconfigure_analysis(); };
    canvas_->line_cancelled = [this] {
        line_editing_ = false;
        if (resume_after_line_ && !stopped_) toggle_playback();
        else state_label_->setText(QStringLiteral("Paused"));
        update_controls();
    };
    install_workspace_chrome(this);
    details_label_->setText(QStringLiteral("Ctrl+O  open media   ·   Space  play or pause   ·   Ctrl+I  settings"));
    workspace_pages_=findChild<QStackedWidget*>(QStringLiteral("workspacePages"));
    connect(findChild<QPushButton*>(QStringLiteral("previewWorkspace")),&QPushButton::clicked,this,[this]{activate_workspace(0);});
    connect(findChild<QPushButton*>(QStringLiteral("quickGuide")),&QPushButton::clicked,this,[this]{activate_workspace(4);if(guide_workspace_)guide_workspace_->focus_search();});
    connect(findChild<QPushButton*>(QStringLiteral("homeWorkspace")),&QPushButton::clicked,this,[this]{activate_workspace(5);});
    for(const auto& key:{QKeySequence(QStringLiteral("Ctrl+H")),QKeySequence(QStringLiteral("Ctrl+0"))}){auto* shortcut=new QShortcut(key,this);connect(shortcut,&QShortcut::activated,this,[this]{activate_workspace(5);});}
    timeline_=findChild<QSlider*>(QStringLiteral("timeline"));position_label_=findChild<QLabel*>(QStringLiteral("timePosition"));
    duration_label_=findChild<QLabel*>(QStringLiteral("timeDuration"));in_view_=findChild<QLabel*>(QStringLiteral("inViewSummary"));
    connect(timeline_,&QSlider::sliderMoved,this,[this](int value){
        if(media_duration_)position_label_->setText(clock_text(std::chrono::microseconds(std::int64_t(media_duration_->count()*(value/1000.))))); });
    connect(timeline_,&QSlider::sliderReleased,this,[this]{seek_to(timeline_->value()/1000.);});
    connect(in_view_,&QLabel::linkActivated,this,[this](const QString& link){
        const int id=link.toInt();
        canvas_->set_focus_class(canvas_->focus_class()==id ? std::nullopt : std::optional<int>(id));
        if(displayed_frame_)canvas_->update();
    });
    auto* snapshot=findChild<QPushButton*>(QStringLiteral("snapshot"));
    const auto save_snapshot=[this]{
        const auto image=canvas_->annotated_image();if(image.isNull())return;
        const auto folder=QDir(QStandardPaths::writableLocation(QStandardPaths::PicturesLocation)).filePath(QStringLiteral("FrameTrail"));
        const auto offset=displayed_frame_ && displayed_frame_->timestamp && media_start_ ? *displayed_frame_->timestamp-*media_start_ : std::chrono::microseconds{};
        const auto seconds=offset.count()/1000000;
        auto name=QStringLiteral("%1-%2m%3s").arg(QFileInfo(source_).completeBaseName()).arg(seconds/60).arg(seconds%60,2,10,QChar('0'));
        QString path=QDir(folder).filePath(name+QStringLiteral(".png"));
        for(int n=2;QFileInfo::exists(path);++n)path=QDir(folder).filePath(QStringLiteral("%1 (%2).png").arg(name).arg(n));
        if(QDir().mkpath(folder) && image.save(path))show_toast(this,QStringLiteral("Snapshot saved to %1").arg(QDir::toNativeSeparators(path)));
        else show_toast(this,QStringLiteral("Could not save the snapshot in %1").arg(QDir::toNativeSeparators(folder)),QStringLiteral("warning"));
    };
    connect(snapshot,&QPushButton::clicked,this,save_snapshot);
    auto* snapshot_shortcut=new QShortcut(QKeySequence::Save,this);
    connect(snapshot_shortcut,&QShortcut::activated,this,[this,save_snapshot]{if(workspace_section_==0)save_snapshot();});
    for(auto* box:{static_cast<QWidget*>(model_box_),static_cast<QWidget*>(backend_box_)})connect(qobject_cast<QComboBox*>(box),&QComboBox::currentIndexChanged,this,[this]{update_detector_status();});
    connect(confidence_box_,&QDoubleSpinBox::valueChanged,this,[this]{update_detector_status();});
    update_detector_status();
    for(int i=0;i<4;++i){auto* shortcut=new QShortcut(QKeySequence(QStringLiteral("Ctrl+%1").arg(i+1)),this);connect(shortcut,&QShortcut::activated,this,[this,i]{activate_workspace(i);});}
    for(const auto& key:{QKeySequence(QStringLiteral("Ctrl+K")),QKeySequence(Qt::Key_F1)}){auto* shortcut=new QShortcut(key,this);connect(shortcut,&QShortcut::activated,this,[this]{activate_workspace(4);if(guide_workspace_)guide_workspace_->focus_search();});}
    setAcceptDrops(true);
    auto* open_shortcut=new QShortcut(QKeySequence::Open,this);
    connect(open_shortcut,&QShortcut::activated,this,[this,open]{activate_workspace(0);open->click();});
    preview_play_shortcut_=new QShortcut(QKeySequence(Qt::Key_Space),this);
    connect(preview_play_shortcut_,&QShortcut::activated,this,[this]{if(workspace_section_==0 && play_button_->isEnabled())toggle_playback();});
    update_controls();
    connect(&timer_, &QTimer::timeout, this, [this] { tick(); });
    timer_.setObjectName(QStringLiteral("previewPoll"));timer_.start(100);
}

void PreviewWindow::activate_workspace(int section) {
    if(workspace_close_requested_ || section<0 || section>5)return;
    const bool switching=section!=workspace_section_;
    if(section!=workspace_section_){
        if(workspace_section_==0 && (updating_ ? resume_after_update_ : playing_))toggle_playback();
        if(workspace_section_==1 && analysis_workspace_)analysis_workspace_->suspend_playback();
        if(workspace_section_==2 && playback_workspace_)playback_workspace_->suspend_playback();
        if(workspace_section_==3 && camera_workspace_)camera_workspace_->request_stop();
    }
    QWidget* page=workspace_pages_->widget(0);
    const auto options=[this]{return frametrail::DetectorOptions{native_path(model_path_),float(confidence_box_->value()),.45f,selected_model(model_box_),selected_backend(backend_box_)};};
    const auto embed=[this](QMainWindow* window){
        window->setParent(workspace_pages_,Qt::Widget);window->setMinimumSize(0,0);auto* layout=window->centralWidget()->layout();layout->setContentsMargins(24,18,24,18);
        if(auto* heading=layout->itemAt(0)->layout();heading && heading->count())if(auto* mark=qobject_cast<QLabel*>(heading->itemAt(0)->widget());mark && !mark->pixmap().isNull())mark->hide();
        workspace_pages_->addWidget(window);
    };
    if(section==1){
        if(!analysis_workspace_){
            frametrail::RunConfiguration configuration;configuration.source=source_.isEmpty()?std::filesystem::path{}:native_path(source_);configuration.detector=options();configuration.kind=frametrail::RunKind::appearances;configuration.tracking.line.reset();
            analysis_workspace_=new SavedRunWindow(std::move(configuration));embed(analysis_workspace_);
            analysis_workspace_->workspace_close_decision=[this](bool accepted){
                if(!workspace_close_requested_)return;
                if(accepted)begin_workspace_shutdown();
                else{workspace_close_requested_=false;findChild<QWidget*>(QStringLiteral("workspaceRail"))->setEnabled(true);activate_workspace(1);}
            };
        }
        else if(!analysis_workspace_->analysing() && !analysis_workspace_->has_video() && !source_.isEmpty() && !still_image(source_))
            analysis_workspace_->select_video(source_); // Open once: Analysis picks up the video from Preview.
        page=analysis_workspace_;
    }else if(section==2){
        if(!playback_workspace_){
            playback_workspace_=new PlaybackWorkspace(source_,options(),workspace_pages_);workspace_pages_->addWidget(playback_workspace_);
            playback_workspace_->preview_selection=[this]{return std::pair{source_,frametrail::DetectorOptions{native_path(model_path_),float(confidence_box_->value()),.45f,selected_model(model_box_),selected_backend(backend_box_)}};};
        }
        else if(playback_workspace_->source().isEmpty() && !source_.isEmpty() && !still_image(source_))
            playback_workspace_->select_video(source_,options());
        page=playback_workspace_;
    }else if(section==3){
        if(!camera_workspace_){camera_workspace_=new LiveWindow(model_box_->itemData(0).toString(),selected_model(model_box_),selected_backend(backend_box_));embed(camera_workspace_);}
        page=camera_workspace_;
    }else if(section==4){
        if(!guide_workspace_){
            guide_workspace_=new GuideWorkspace(model_box_,workspace_pages_);workspace_pages_->addWidget(guide_workspace_);
            guide_workspace_->navigate=[this](int target,int model){
                if(model>=0 && model<model_box_->count() && QFileInfo::exists(model_box_->itemData(model).toString()))model_box_->setCurrentIndex(model);
                activate_workspace(target);
            };
        }
        page=guide_workspace_;
    }else if(section==5){
        if(!home_workspace_){
            home_workspace_=new HomeWorkspace(workspace_pages_);workspace_pages_->addWidget(home_workspace_);
            home_workspace_->open_media=[this]{activate_workspace(0);findChild<QPushButton*>(QStringLiteral("open"))->click();};
            home_workspace_->open_analysis=[this]{activate_workspace(1);if(auto* button=analysis_workspace_->findChild<QPushButton*>(QStringLiteral("openRun")))button->click();};
            home_workspace_->open_path=[this](const QString& path){open_path(path);};
            home_workspace_->navigate=[this](int target){activate_workspace(target);};
            home_workspace_->setup=[this]{
                const auto model=selected_model(model_box_);
                return QStringList{QString::fromUtf8(frametrail::model_name(model).data()),
                    QStringLiteral("%1 object categories").arg(frametrail::model_category_count(model)),
                    QStringLiteral("Runs on %1 · confidence %2%").arg(selected_backend(backend_box_)==frametrail::DetectorBackend::cpu ? QStringLiteral("the CPU") : QStringLiteral("the GPU when available")).arg(qRound(confidence_box_->value()*100))};
            };
        }
        page=home_workspace_;
    }
    workspace_section_=section;workspace_pages_->setCurrentWidget(page);page->show();if(switching)fade_in(page);
    const QStringList labels{QStringLiteral("Preview"),QStringLiteral("Analysis"),QStringLiteral("Playback"),QStringLiteral("Camera"),QStringLiteral("Guide"),QStringLiteral("Home")};
    const QStringList buttons{QStringLiteral("previewWorkspace"),QStringLiteral("savedAnalysis"),QStringLiteral("smoothPlayback"),QStringLiteral("liveCamera"),QStringLiteral("quickGuide"),QStringLiteral("homeWorkspace")};
    findChild<QPushButton*>(buttons[section])->setChecked(true);
    findChild<QLabel*>(QStringLiteral("subtitle"))->setText(QStringLiteral("Workspace / %1").arg(labels[section]));
    findChild<QPushButton*>(QStringLiteral("open"))->setVisible(section==0);findChild<QPushButton*>(QStringLiteral("toggleInspector"))->setVisible(section==0);
    if(preview_play_shortcut_)preview_play_shortcut_->setEnabled(section==0);
    setAcceptDrops(section==0);update_workspace_activity();
}
void PreviewWindow::begin_workspace_shutdown(){
    closing_=true;timer_.setInterval(10);pending_source_.clear();session_.stop();
    if(playback_workspace_)playback_workspace_->request_shutdown();
    if(camera_workspace_)camera_workspace_->request_stop();
    state_label_->setText(QStringLiteral("Closing workspace…"));
}
void PreviewWindow::update_workspace_activity(){
    QStringList activity;
    if(analysis_workspace_ && analysis_workspace_->analysing())activity<<QStringLiteral("Analysis running");
    if(playback_workspace_ && playback_workspace_->preparing())activity<<QStringLiteral("Playback preparing");
    if(camera_workspace_ && camera_workspace_->active())activity<<(workspace_section_==3?QStringLiteral("Camera on"):QStringLiteral("Camera stopping"));
    auto* badge=findChild<QLabel*>(QStringLiteral("workspaceActivity"));const bool busy=!activity.isEmpty();
    const auto text=busy?activity.join(QStringLiteral(" · ")):QStringLiteral("All work stays local");
    const std::pair<const char*,bool> rail[]={{"savedAnalysis",analysis_workspace_ && analysis_workspace_->analysing()},
        {"smoothPlayback",playback_workspace_ && playback_workspace_->preparing()},{"liveCamera",camera_workspace_ && camera_workspace_->active()}};
    for(const auto& [name,active]:rail)if(auto* button=findChild<QPushButton*>(QString::fromLatin1(name));button && button->property("busy").toBool()!=active){button->setProperty("busy",active);button->update();}
    if(badge->text()!=text)badge->setText(text);
    if(badge->property("busy").toBool()!=busy){badge->setProperty("busy",busy);badge->style()->unpolish(badge);badge->style()->polish(badge);}
}

void PreviewWindow::show_home(){activate_workspace(5);}
void PreviewWindow::open_path(const QString& path) {
    if(path.isEmpty())return;
    if(QFileInfo(path).suffix().compare(QStringLiteral("frametrail"),Qt::CaseInsensitive)==0) {
        activate_workspace(1);
        try{analysis_workspace_->open_run(path);remember_file(path);}catch(const std::exception&){}
        return;
    }
    open_file(path);
}
void PreviewWindow::update_detector_status() {
    if(auto* label=findChild<QLabel*>(QStringLiteral("detectorStatus")))
        label->setText(QStringLiteral("%1  ·  %2  ·  %3%").arg(QString::fromUtf8(frametrail::model_name(selected_model(model_box_)).data()),
            selected_backend(backend_box_)==frametrail::DetectorBackend::cpu ? QStringLiteral("CPU") : QStringLiteral("GPU / auto")).arg(qRound(confidence_box_->value()*100)));
}
void PreviewWindow::update_timeline() {
    const bool known=media_start_ && media_duration_ && media_duration_->count()>0;
    timeline_->setEnabled(known && !line_editing_ && !updating_ && pending_source_.isEmpty() && !closing_);
    duration_label_->setText(known ? clock_text(*media_duration_) : QStringLiteral("0:00"));
    if(!known || timeline_->isSliderDown())return;
    const auto position=displayed_frame_ && displayed_frame_->timestamp ? *displayed_frame_->timestamp-*media_start_ : std::chrono::microseconds{};
    position_label_->setText(clock_text(position));
    QSignalBlocker block(timeline_);timeline_->setValue(int(std::clamp(1000.*double(position.count())/double(media_duration_->count()),0.,1000.)));
}
void PreviewWindow::seek_to(double fraction) {
    if(source_.isEmpty() || closing_ || !pending_source_.isEmpty() || line_editing_ || !media_start_ || !media_duration_)return;
    const auto offset=std::chrono::microseconds(std::int64_t(std::clamp(fraction,0.,1.)*double(media_duration_->count())));
    pause_after_seek_=!playing_;
    pending_start_=*media_start_+offset;
    pending_source_=source_;timer_.setInterval(10);session_.stop();next_.reset();
    updating_=false;line_editing_=false;stopped_=true;playing_=false;finished_=false;
    state_label_->setText(QStringLiteral("Jumping to %1…").arg(clock_text(offset)));
    counts_label_->setText(QStringLiteral("Counts restart after a jump"));
    update_controls();
}

void PreviewWindow::open_file(const QString& path) {
    if (path.isEmpty() || closing_ || workspace_close_requested_) return;
    activate_workspace(0);
    remember_file(path);
    pending_source_ = path;pending_start_.reset();pause_after_seek_=false;media_start_.reset();media_duration_.reset();
    static_cast<TimelineSlider*>(timeline_)->reset_activity();canvas_->set_focus_class(std::nullopt);
    timer_.setInterval(10);
    session_.stop();
    next_.reset();
    displayed_sequence_.reset();
    displayed_frame_.reset();
    updating_ = false; line_editing_ = false;
    canvas_->set_image({});
    stopped_ = true;
    finished_ = false;
    playing_ = false;
    play_button_->setEnabled(false);
    stop_button_->setEnabled(false);
    replay_button_->setEnabled(false);
    state_label_->setText(QStringLiteral("Opening…"));
    source_label_->setText(QFileInfo(path).fileName());
    source_label_->setToolTip(path);source_transition_->stop();source_transition_->start();
    details_label_->setText(QStringLiteral("Reading media…"));
    counts_label_->setText(QStringLiteral("− → +  0      + → −  0"));
}

std::pair<std::optional<frametrail::DetectorOptions>,std::optional<frametrail::TrackingOptions>> PreviewWindow::analysis_options() {
    std::optional<frametrail::DetectorOptions> detection;
    if (detect_box_->isChecked()) detection=frametrail::DetectorOptions{
        native_path(model_path_),float(confidence_box_->value()),0.45f,selected_model(model_box_),selected_backend(backend_box_)};
    std::optional<frametrail::TrackingOptions> tracking;
    if (detection && track_box_->isChecked()) {
        tracking = frametrail::TrackingOptions{};
        if (classes_box_->currentIndex() == 1) tracking->classes = {0};
        if (classes_box_->currentIndex() == 2) tracking->classes = {1,2,3,5,7};
        counting_line_.direction = direction_box_->currentIndex() == 1 ? frametrail::CrossingDirection::negative_to_positive :
            direction_box_->currentIndex() == 2 ? frametrail::CrossingDirection::positive_to_negative : frametrail::CrossingDirection::both;
        tracking->line = counting_line_;
    }
    return {std::move(detection),std::move(tracking)};
}

void PreviewWindow::update_controls() {
    // While settings apply, Play/Pause stays usable and changes what happens once they are applied.
    const bool ready = !stopped_ && !line_editing_ && pending_source_.isEmpty();
    const bool will_play = updating_ ? resume_after_update_ : playing_;
    play_button_->setEnabled(ready || (finished_ && pending_source_.isEmpty() && !closing_));
    stop_button_->setEnabled(ready && will_play);
    replay_button_->setEnabled(!source_.isEmpty() && pending_source_.isEmpty() && !closing_);
    play_button_->setText(will_play ? QStringLiteral("Pause") : QStringLiteral("Play"));
    if(play_button_->property("showsPause").toBool()!=will_play){play_button_->setProperty("showsPause",will_play);studio_button(play_button_,will_play ? QStringLiteral("pause") : QStringLiteral("play"));}
    const bool tracking = detect_box_->isChecked() && track_box_->isChecked();
    track_box_->setEnabled(detect_box_->isChecked());
    classes_box_->setEnabled(tracking); direction_box_->setEnabled(tracking);
    line_button_->setEnabled(tracking && displayed_frame_.has_value() && !updating_);
    timer_.setInterval(playing_ || updating_ || !pending_source_.isEmpty() || closing_ ? 10:100);
    if(timeline_)update_timeline();
    if(auto* snapshot=findChild<QPushButton*>(QStringLiteral("snapshot")))snapshot->setEnabled(!canvas_->image().isNull());
}

void PreviewWindow::reconfigure_analysis() {
    if (closing_) return;
    if (source_.isEmpty() || !pending_source_.isEmpty()) { update_controls(); return; }
    const bool resume = updating_ ? resume_after_update_ : line_editing_ ? resume_after_line_ : playing_;
    if (playing_) toggle_playback();
    canvas_->cancel_line_selection(false);
    line_editing_ = false;
    resume_after_update_ = resume;
    std::vector<frametrail::Frame> retained;
    if (displayed_frame_) retained.push_back(*displayed_frame_);
    if (next_) { retained.push_back(std::move(next_->frame)); next_.reset(); }
    try {
        auto [detection,tracking] = analysis_options();
        analysis_revision_ = session_.reconfigure(std::move(detection),std::move(tracking),std::move(retained));
        updating_ = true; stopped_ = false; playing_ = false;
        canvas_->set_image(canvas_->image()); // Keep pixels, clear obsolete overlays.
        counts_label_->setText(QStringLiteral("Counts reset at this position — applying settings…"));
        state_label_->setText(QStringLiteral("Applying settings…"));
    } catch (const std::exception& error) {
        updating_ = false; stopped_ = true; playing_ = false;
        state_label_->setText(QStringLiteral("Could not apply settings: ")+QString::fromUtf8(error.what()));
    }
    update_controls();
}

void PreviewWindow::begin_pending_source() {
    source_ = pending_source_;
    pending_source_.clear();
    finished_ = false;
    try {
        auto [detection,tracking] = analysis_options();
        session_.start(native_path(source_),std::move(detection),std::move(tracking),std::nullopt,std::exchange(pending_start_,std::nullopt));
        generation_ = session_.snapshot().generation;
        analysis_revision_ = session_.snapshot().analysis_revision;
        playing_ = true;
        stopped_ = false;
        clock_started_ = false;
        update_controls();
    } catch (const std::exception& error) {
        state_label_->setText(QStringLiteral("Could not open: ") + QString::fromUtf8(error.what()));
        replay_button_->setEnabled(true);
    }
}

void PreviewWindow::toggle_playback() {
    if (finished_ && pending_source_.isEmpty() && !closing_) { open_file(source_); return; }
    if (stopped_ || line_editing_ || !pending_source_.isEmpty()) return;
    if (updating_) {
        resume_after_update_ = !resume_after_update_;
        update_controls();
        state_label_->setText(resume_after_update_ ? QStringLiteral("Applying settings… then playing") : QStringLiteral("Applying settings… then paused"));
        return;
    }
    const auto now = std::chrono::steady_clock::now();
    playing_ = !playing_;
    if (!playing_) pause_start_ = now;
    else if (clock_started_) playback_start_ += now - pause_start_;
    update_controls();
    state_label_->setText(playing_ ? QStringLiteral("Playing") : QStringLiteral("Paused"));
}

void PreviewWindow::stop_playback() {
    if (updating_ ? resume_after_update_ : playing_) toggle_playback();
    state_label_->setText(QStringLiteral("Stopped — press Play to continue"));
}

void PreviewWindow::display(frametrail::PreviewFrame wrapped) {
    if (wrapped.generation != generation_ || wrapped.analysis_revision != analysis_revision_) return;
    const auto& frame = wrapped.frame;
    const QImage borrowed(frame.pixels.data(), frame.width, frame.height, frame.stride, QImage::Format_RGB888);
    canvas_->set_image(borrowed.copy(),wrapped.detection ? wrapped.detection->objects : std::vector<frametrail::Detection>{},
        wrapped.tracking ? wrapped.tracking->objects : std::vector<frametrail::TrackedObject>{},
        wrapped.tracking ? std::optional<frametrail::CountingLine>(counting_line_) : std::nullopt);
    displayed_sequence_ = frame.sequence;
    const auto info = session_.snapshot().info;
    if(!media_start_)media_start_=frame.timestamp.value_or(std::chrono::microseconds{});
    if(info && info->duration && info->duration->count()>0)media_duration_=info->duration;
    if(!wrapped.detection)in_view_->setText(detect_box_->isChecked() ? QStringLiteral("Waiting for the detector…") : QStringLiteral("Detection is off."));
    else if(wrapped.detection->objects.empty())in_view_->setText(QStringLiteral("Nothing detected in this frame."));
    else {
        std::map<int,int> counts;for(const auto& object:wrapped.detection->objects)++counts[object.class_id];
        std::vector<std::pair<int,int>> ordered(counts.begin(),counts.end());
        std::stable_sort(ordered.begin(),ordered.end(),[](const auto& a,const auto& b){return a.second>b.second;});
        const auto focus=canvas_->focus_class();
        QStringList parts;
        for(const auto& [id,count]:ordered) {
            const bool dimmed=focus && *focus!=id;
            parts<<QStringLiteral("<a href=\"%5\" style=\"text-decoration:none\"><span style=\"color:%1\">&#9679;</span>&nbsp;<span style=\"color:%2\">%3</span>&nbsp;<b style=\"color:%2\">%4</b></a>")
                .arg(ft::ui::category_color(id).name(),(dimmed ? ft::ui::text_disabled : ft::ui::text).name(),QString::fromUtf8(frametrail::class_name(id).data()).toHtmlEscaped()).arg(count).arg(id);
        }
        auto html=parts.join(QStringLiteral("&nbsp;&nbsp;&nbsp; "));
        if(focus)html+=QStringLiteral("<br><span style=\"color:%1;font-size:12px\">Showing only %2 · click it again to show all</span>")
            .arg(ft::ui::text_tertiary.name(),QString::fromUtf8(frametrail::class_name(*focus).data()).toHtmlEscaped());
        in_view_->setText(html);
        if(media_duration_ && media_start_ && frame.timestamp && media_duration_->count()>0)
            static_cast<TimelineSlider*>(timeline_)->add_activity(double((*frame.timestamp-*media_start_).count())/double(media_duration_->count()),
                int(wrapped.detection->objects.size()),ordered.front().first);
    }
    details_label_->setText(QStringLiteral("%1×%2  ·  %3")
        .arg(frame.width).arg(frame.height)
        .arg(info ? QString::fromStdString(info->codec) : QStringLiteral("unknown codec")));
    details_label_->setToolTip(QStringLiteral("Frame %1 at %2").arg(frame.sequence).arg(timestamp_text(frame.timestamp)));
    if (wrapped.detection) details_label_->setText(details_label_->text()+QStringLiteral("  ·  %1 objects  ·  %2 ms per frame")
        .arg(wrapped.detection->objects.size()).arg(wrapped.detection->elapsed_ms,0,'f',1));
    if (wrapped.tracking) {
        counts_label_->setText(QStringLiteral("− → +  %1      + → −  %2\n%3 tracked now")
            .arg(wrapped.tracking->negative_to_positive).arg(wrapped.tracking->positive_to_negative)
            .arg(wrapped.tracking->objects.size()));
        counts_label_->setToolTip(QStringLiteral("Tracking rules took %1 ms for this frame").arg(wrapped.tracking->elapsed_ms,0,'f',2));
    } else counts_label_->setText(QStringLiteral("− → +  0      + → −  0"));
    if(wrapped.detection) {
        const auto& execution=wrapped.detection->execution;
        details_label_->setText(details_label_->text()+QStringLiteral(" on %1").arg(execution.provider=="DirectML" ? QStringLiteral("GPU"):QStringLiteral("CPU")));
        details_label_->setToolTip(QString::fromStdString(execution.provider+" / ONNX Runtime "+execution.runtime+" / "+execution.device+
            (execution.fallback.empty() ? "": "\nCPU fallback: "+execution.fallback)));
    }
    displayed_frame_ = std::move(wrapped.frame);
    state_label_->setText(playing_ ? QStringLiteral("Playing") : QStringLiteral("Paused"));
    update_controls();
    if(pause_after_seek_ && playing_){pause_after_seek_=false;toggle_playback();}
}

void PreviewWindow::tick() {
    update_workspace_activity();
    auto status = session_.snapshot();
    if (closing_) {
        if (!status.worker_active && (!playback_workspace_ || playback_workspace_->shutdown_complete()) && (!camera_workspace_ || !camera_workspace_->active())){workspace_close_ready_=true;close();}
        return;
    }
    if (!pending_source_.isEmpty()) {
        if (!status.worker_active) begin_pending_source();
        return;
    }
    if (stopped_) return;
    if (status.state==frametrail::PreviewState::opening) {
        state_label_->setText(detect_box_->isChecked() ? QStringLiteral("Loading model…") : QStringLiteral("Opening…"));
    }
    if (status.state == frametrail::PreviewState::failed) {
        next_.reset();
        stopped_ = true;
        playing_ = false;
        updating_ = false;
        update_controls();
        state_label_->setText(QStringLiteral("Could not read: ") + QString::fromStdString(status.error));
        return;
    }
    if (updating_) {
        auto refreshed = session_.try_pop();
        if (refreshed && refreshed->generation == generation_ && refreshed->analysis_revision == analysis_revision_) {
            display(std::move(*refreshed));
            updating_ = false;
            playing_ = resume_after_update_;
            const auto now = std::chrono::steady_clock::now();
            first_timestamp_ = displayed_frame_->timestamp.value_or(std::chrono::microseconds{});
            first_sequence_ = displayed_frame_->sequence;
            playback_start_ = now; pause_start_ = now; clock_started_ = true;
            state_label_->setText(playing_ ? QStringLiteral("Playing") : QStringLiteral("Paused"));
            update_controls();
        }
        return;
    }
    if (!playing_) return;
    if (!next_) next_ = session_.try_pop();
    if (next_) {
        const auto now = std::chrono::steady_clock::now();
        if (!clock_started_) {
            first_timestamp_ = next_->frame.timestamp.value_or(std::chrono::microseconds{});
            first_sequence_ = next_->frame.sequence;
            playback_start_ = now;
            clock_started_ = true;
        }
        const auto timestamp = next_->frame.timestamp.value_or(
            first_timestamp_ + std::chrono::microseconds((next_->frame.sequence-first_sequence_) * 33333));
        if (now - playback_start_ >= timestamp - first_timestamp_) {
            display(std::move(*next_));
            next_.reset();
        }
    } else if (!status.worker_active && status.queued_frames == 0) {
        playing_ = false;
        stopped_ = true;
        finished_ = displayed_sequence_.has_value();
        update_controls();
        state_label_->setText(displayed_sequence_ ? QStringLiteral("Finished") : QStringLiteral("No frames decoded"));
    }
}

void PreviewWindow::closeEvent(QCloseEvent* event) {
    if(workspace_close_ready_){event->accept();return;}
    event->ignore();if(workspace_close_requested_)return;
    if(analysis_workspace_)activate_workspace(1);
    workspace_close_requested_=true;findChild<QWidget*>(QStringLiteral("workspaceRail"))->setEnabled(false);
    if(analysis_workspace_)analysis_workspace_->close();else begin_workspace_shutdown();
}

void PreviewWindow::dragEnterEvent(QDragEnterEvent* event) {
    const auto urls=event->mimeData()->urls();
    if(urls.size()==1 && urls.front().isLocalFile() && QFileInfo(urls.front().toLocalFile()).isFile())event->acceptProposedAction();
}
void PreviewWindow::dropEvent(QDropEvent* event) {
    const auto urls=event->mimeData()->urls();
    if(urls.size()!=1 || !urls.front().isLocalFile() || !QFileInfo(urls.front().toLocalFile()).isFile())return;
    open_path(urls.front().toLocalFile());event->acceptProposedAction();
}
