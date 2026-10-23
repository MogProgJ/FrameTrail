#include "preview_window.hpp"
#include "model_selection.hpp"
#include "saved_run_window.hpp"
#include "cached_playback_window.hpp"
#include "live_window.hpp"
#include "theme.hpp"
#include "studio_controls.hpp"
#include "workspace_chrome.hpp"
#include <QDragEnterEvent>
#include <QDropEvent>
#include <QMimeData>
#include <QUrl>
#include <QShortcut>
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

QString timestamp_text(const std::optional<std::chrono::microseconds>& timestamp) {
    if (!timestamp) return QStringLiteral("Unknown time");
    const auto ms = std::max<std::int64_t>(0, timestamp->count() / 1000);
    return QStringLiteral("%1:%2:%3.%4")
        .arg(ms / 3600000, 2, 10, QChar('0'))
        .arg((ms / 60000) % 60, 2, 10, QChar('0'))
        .arg((ms / 1000) % 60, 2, 10, QChar('0'))
        .arg(ms % 1000, 3, 10, QChar('0'));
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
    QPainterPath surface;surface.addRoundedRect(QRectF(rect()).adjusted(1,1,-1,-1),12,12);
    painter.fillPath(surface,QColor("#17181c"));painter.setPen(QPen(QColor("#2b2c33"),1));painter.drawPath(surface);
    painter.setClipPath(surface);
    if (image_.isNull()) {
        const auto center=rect().center();
        const QRectF icon(center.x()-32,center.y()-108,64,64);
        painter.setPen(QPen(QColor("#45424f"),1));painter.setBrush(QColor("#25232e"));painter.drawRoundedRect(icon,17,17);
        painter.setPen(QPen(QColor("#c4bcfa"),2,Qt::SolidLine,Qt::RoundCap,Qt::RoundJoin));
        const int cx=center.x(),cy=center.y()-76;
        painter.drawLine(cx-12,cy-4,cx-12,cy+10);painter.drawLine(cx-12,cy+10,cx+12,cy+10);painter.drawLine(cx+12,cy+10,cx+12,cy-4);
        painter.drawLine(cx,cy+2,cx,cy-13);painter.drawLine(cx,cy-13,cx-5,cy-8);painter.drawLine(cx,cy-13,cx+5,cy-8);
        const bool preview=empty_text_==QStringLiteral("Open an image or video to begin");
        const auto lines=empty_text_.split('\n');
        auto title_font=painter.font();title_font.setPixelSize(width()<540?19:23);title_font.setWeight(QFont::DemiBold);painter.setFont(title_font);painter.setPen(QColor("#e9e8ee"));
        painter.drawText(QRect(22,center.y()-18,width()-44,64),Qt::AlignHCenter|Qt::AlignTop|Qt::TextWordWrap,preview?QStringLiteral("Open a video or image"):lines.first());
        auto hint_font=painter.font();hint_font.setPixelSize(13);hint_font.setWeight(QFont::Normal);painter.setFont(hint_font);painter.setPen(QColor("#a3a0ad"));
        const auto hint=preview?QStringLiteral("Drop a file into your workspace, or choose Open media."):lines.mid(1).join('\n');
        painter.drawText(QRect(28,center.y()+32,width()-56,68),Qt::AlignHCenter|Qt::AlignTop|Qt::TextWordWrap,hint);
        if(preview){painter.setPen(QColor("#767480"));hint_font.setPixelSize(11);painter.setFont(hint_font);painter.drawText(QRect(20,center.y()+87,width()-40,25),Qt::AlignCenter,QStringLiteral("MP4 · MOV · MKV · Images    /    Ctrl+O"));}
        return;
    }
    const QRect target = image_rect();
    painter.setRenderHint(QPainter::SmoothPixmapTransform);
    painter.drawImage(target, image_);
    painter.setClipRect(target);
    const double sx=double(target.width())/image_.width(), sy=double(target.height())/image_.height();
    for (const auto& object:objects_) {
        const frametrail::TrackedObject* matched{};
        for(const auto& track:tracks_)if(track.detection.class_id==object.class_id && track.detection.left==object.left &&
            track.detection.top==object.top && track.detection.right==object.right && track.detection.bottom==object.bottom){matched=&track;break;}
        const QColor color=temporal_style_ && matched ? (matched->confirmed ? QColor::fromHsv(int((matched->id*67)%360),150,230):QColor("#a0adbf")):
            QColor::fromHsv((object.class_id*47+150)%360,180,245);
        const QRectF box(target.left()+object.left*sx, target.top()+object.top*sy,
            (object.right-object.left)*sx, (object.bottom-object.top)*sy);
        painter.setPen(QPen(color,2,temporal_style_ && matched && !matched->confirmed ? Qt::DashLine:Qt::SolidLine));
        painter.drawRoundedRect(box,3,3);
        auto label=QStringLiteral("%1 %2%")
            .arg(QString::fromUtf8(frametrail::class_name(object.class_id).data()))
            .arg(qRound(object.confidence*100));
        if(matched)label += QStringLiteral(" #%1%2").arg(matched->id).arg(matched->confirmed ? QString{} : QStringLiteral("?"));
        const auto text_size=painter.fontMetrics().size(Qt::TextSingleLine,label);
        const double label_x=std::clamp(box.left(),double(target.left()),
            std::max(double(target.left()),double(target.right()-text_size.width()-8)));
        const double label_y=std::max(double(target.top()),box.top()-text_size.height()-6);
        const QRectF label_box(label_x,label_y,text_size.width()+8,text_size.height()+6);
        painter.setBrush(QColor("#ec16171d"));painter.setPen(QPen(color,1));painter.drawRoundedRect(label_box,4,4);
        painter.setPen(QColor("#f3f1f8"));
        painter.drawText(label_box,Qt::AlignCenter,label);
    }
    const auto screen = [&](frametrail::Point p) {
        return QPointF(target.left()+p.x*target.width(),target.top()+p.y*target.height());
    };
    painter.setRenderHint(QPainter::Antialiasing);
    for (const auto& track : tracks_) {
        auto color=QColor::fromHsv(int((track.id*67)%360),150,230);
        for (std::size_t i=1;i<track.trail.size();++i) {
            if(temporal_style_)color.setAlpha(50+int(180*i/(track.trail.size()-1)));
            painter.setPen(QPen(color,2));painter.drawLine(screen(track.trail[i-1]),screen(track.trail[i]));
        }
    }
    if (line_) {
        painter.setPen(QPen(QColor("#ffce63"),3));
        painter.drawLine(screen(line_->a),screen(line_->b));
        painter.drawEllipse(screen(line_->a),4,4); painter.drawEllipse(screen(line_->b),4,4);
        painter.drawText(screen(line_->a)+QPointF(8,-8),QStringLiteral("A"));
        painter.drawText(screen(line_->b)+QPointF(8,-8),QStringLiteral("B"));
        const auto dx=line_->b.x-line_->a.x,dy=line_->b.y-line_->a.y;
        const auto norm=std::hypot(dx,dy);
        const frametrail::Point middle{(line_->a.x+line_->b.x)/2,(line_->a.y+line_->b.y)/2};
        painter.drawText(screen({middle.x-dy/norm*0.05,middle.y+dx/norm*0.05}),QStringLiteral("+"));
        painter.drawText(screen({middle.x+dy/norm*0.05,middle.y-dx/norm*0.05}),QStringLiteral("−"));
    }
    if (selecting_line_) {
        painter.setPen(QPen(QColor("#ffce63"),2));
        if (first_point_) painter.drawEllipse(screen(*first_point_),6,6);
        painter.drawText(target.adjusted(12,12,-12,-12),Qt::AlignTop|Qt::AlignLeft,
            first_point_ ? QStringLiteral("Click endpoint B • Right-click to cancel") : QStringLiteral("Click endpoint A • Right-click to cancel"));
    }
}

PreviewWindow::PreviewWindow(const QString& model_path) {
    model_path_=model_path.isEmpty() ? QCoreApplication::applicationDirPath()+QStringLiteral("/models/yolox_nano.onnx") : model_path;
    Ui::PreviewLayout ui;
    ui.setupUi(this);
    setWindowTitle(QStringLiteral("FrameTrail — Video workspace"));
    setMinimumSize(900, 600);
    install_studio_style();setStyleSheet(frametrail_theme()+QStringLiteral("QLabel#details { color:#92909f; font-size:11px; padding:2px; }"));
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
    auto* open = ui.open; auto* live = ui.liveCamera;
    connect(live,&QPushButton::clicked,this,[this,live] {
        if(playing_)toggle_playback();
        auto* window=new LiveWindow(model_box_->itemData(0).toString(),selected_model(model_box_),selected_backend(backend_box_));window->setAttribute(Qt::WA_DeleteOnClose);
        live->setEnabled(false);connect(window,&QObject::destroyed,this,[live]{live->setEnabled(true);});window->show();
    });
    auto* smooth=new QPushButton(QStringLiteral("Smooth playback…"));smooth->setObjectName(QStringLiteral("smoothPlayback"));
    smooth->setToolTip(QStringLiteral("Prepare detections once, then play the video at its original pace."));
    ui.header->addWidget(smooth);
    connect(smooth,&QPushButton::clicked,this,[this,smooth]{
        auto path=source_;
        if(path.isEmpty())path=QFileDialog::getOpenFileName(this,QStringLiteral("Choose a video for smooth playback"),{},QStringLiteral("Video (*.mp4 *.mkv *.avi *.mov *.webm);;All files (*)"));
        if(path.isEmpty())return;
        if(playing_)toggle_playback();
        frametrail::DetectorOptions options{native_path(model_path_),float(confidence_box_->value()),.45f,selected_model(model_box_),selected_backend(backend_box_)};
        auto* window=new CachedPlaybackWindow(path,std::move(options));window->setAttribute(Qt::WA_DeleteOnClose);
        smooth->setEnabled(false);connect(window,&QObject::destroyed,this,[smooth]{smooth->setEnabled(true);});window->show();
    });
    auto* saved = ui.savedAnalysis;
    connect(saved,&QPushButton::clicked,this,[this,saved] {
        if(playing_)toggle_playback();
        frametrail::RunConfiguration configuration;
        configuration.source=source_.isEmpty() ? std::filesystem::path{} : native_path(source_);
        configuration.detector={native_path(model_path_),float(confidence_box_->value()),.45f,selected_model(model_box_),selected_backend(backend_box_)};
        configuration.kind=frametrail::RunKind::appearances;
        configuration.tracking.line.reset();
        auto* window=new SavedRunWindow(std::move(configuration));
        saved->setEnabled(false);
        connect(window,&QObject::destroyed,this,[saved]{saved->setEnabled(true);});
        window->setAttribute(Qt::WA_DeleteOnClose);window->show();
    });

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
    setAcceptDrops(true);
    auto* open_shortcut=new QShortcut(QKeySequence::Open,this);
    connect(open_shortcut,&QShortcut::activated,open,&QPushButton::click);
    auto* play_shortcut=new QShortcut(QKeySequence(Qt::Key_Space),this);
    connect(play_shortcut,&QShortcut::activated,this,[this]{if(play_button_->isEnabled())toggle_playback();});
    update_controls();
    connect(&timer_, &QTimer::timeout, this, [this] { tick(); });
    timer_.start(10);
}

void PreviewWindow::open_file(const QString& path) {
    if (path.isEmpty() || closing_) return;
    pending_source_ = path;
    session_.stop();
    next_.reset();
    displayed_sequence_.reset();
    displayed_frame_.reset();
    updating_ = false; line_editing_ = false;
    canvas_->set_image({});
    stopped_ = true;
    playing_ = false;
    play_button_->setEnabled(false);
    stop_button_->setEnabled(false);
    replay_button_->setEnabled(false);
    state_label_->setText(QStringLiteral("Opening…"));
    source_label_->setText(QFileInfo(path).fileName());
    source_label_->setToolTip(path);source_transition_->stop();source_transition_->start();
    details_label_->setText(QStringLiteral("Reading media…"));
    counts_label_->setText(QStringLiteral("Video counts: − → +  0    |    + → −  0"));
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
    const bool ready = !stopped_ && !updating_ && !line_editing_ && pending_source_.isEmpty();
    play_button_->setEnabled(ready);
    stop_button_->setEnabled(ready && playing_);
    replay_button_->setEnabled(!source_.isEmpty() && pending_source_.isEmpty() && !closing_);
    play_button_->setText(playing_ ? QStringLiteral("Pause") : QStringLiteral("Play"));
    const bool tracking = detect_box_->isChecked() && track_box_->isChecked();
    track_box_->setEnabled(detect_box_->isChecked());
    classes_box_->setEnabled(tracking); direction_box_->setEnabled(tracking);
    line_button_->setEnabled(tracking && displayed_frame_.has_value() && !updating_);
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
    try {
        auto [detection,tracking] = analysis_options();
        session_.start(native_path(source_),std::move(detection),std::move(tracking));
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
    if (stopped_ || updating_ || line_editing_ || !pending_source_.isEmpty()) return;
    const auto now = std::chrono::steady_clock::now();
    playing_ = !playing_;
    if (!playing_) pause_start_ = now;
    else if (clock_started_) playback_start_ += now - pause_start_;
    update_controls();
    state_label_->setText(playing_ ? QStringLiteral("Playing") : QStringLiteral("Paused"));
}

void PreviewWindow::stop_playback() {
    if (playing_) toggle_playback();
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
    details_label_->setText(QStringLiteral("%1 × %2    •    %3    •    Frame %4    •    %5")
        .arg(frame.width).arg(frame.height)
        .arg(info ? QString::fromStdString(info->codec) : QStringLiteral("Unknown codec"))
        .arg(frame.sequence).arg(timestamp_text(frame.timestamp)));
    if (wrapped.detection) details_label_->setText(details_label_->text()+QStringLiteral("    •    %1 objects    •    %2 ms/frame")
        .arg(wrapped.detection->objects.size()).arg(wrapped.detection->elapsed_ms,0,'f',1));
    if (wrapped.tracking) {
        counts_label_->setText(QStringLiteral("Video counts: − → +  %1    |    + → −  %2    •    %3 observed tracks    •    Rules %4 ms")
            .arg(wrapped.tracking->negative_to_positive).arg(wrapped.tracking->positive_to_negative)
            .arg(wrapped.tracking->objects.size()).arg(wrapped.tracking->elapsed_ms,0,'f',2));
    } else counts_label_->setText(QStringLiteral("Video counts: − → +  0    |    + → −  0"));
    if(wrapped.detection) {
        const auto& execution=wrapped.detection->execution;
        details_label_->setText(details_label_->text()+QStringLiteral(" · %1").arg(execution.provider=="DirectML" ? QStringLiteral("GPU"):QStringLiteral("CPU")));
        details_label_->setToolTip(QString::fromStdString(execution.provider+" / ONNX Runtime "+execution.runtime+" / "+execution.device+
            (execution.fallback.empty() ? "": "\nCPU fallback: "+execution.fallback)));
    }
    displayed_frame_ = std::move(wrapped.frame);
    state_label_->setText(playing_ ? QStringLiteral("Playing") : QStringLiteral("Paused"));
    update_controls();
}

void PreviewWindow::tick() {
    auto status = session_.snapshot();
    if (closing_) {
        if (!status.worker_active) close();
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
        update_controls();
        state_label_->setText(displayed_sequence_ ? QStringLiteral("Finished") : QStringLiteral("No frames decoded"));
    }
}

void PreviewWindow::closeEvent(QCloseEvent* event) {
    if (session_.snapshot().worker_active) {
        closing_ = true;
        pending_source_.clear();
        session_.stop();
        state_label_->setText(QStringLiteral("Closing…"));
        event->ignore();
    } else {
        event->accept();
    }
}

void PreviewWindow::dragEnterEvent(QDragEnterEvent* event) {
    const auto urls=event->mimeData()->urls();
    if(urls.size()==1 && urls.front().isLocalFile() && QFileInfo(urls.front().toLocalFile()).isFile())event->acceptProposedAction();
}
void PreviewWindow::dropEvent(QDropEvent* event) {
    const auto urls=event->mimeData()->urls();
    if(urls.size()!=1 || !urls.front().isLocalFile() || !QFileInfo(urls.front().toLocalFile()).isFile())return;
    open_file(urls.front().toLocalFile());event->acceptProposedAction();
}
