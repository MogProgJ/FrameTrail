#include "preview_window.hpp"

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
    painter.fillRect(rect(), QColor("#0c1118"));
    if (image_.isNull()) {
        painter.setPen(QColor("#8796a8"));
        painter.drawText(rect(), Qt::AlignCenter, QStringLiteral("Open an image or video to begin"));
        return;
    }
    const QRect target = image_rect();
    painter.setRenderHint(QPainter::SmoothPixmapTransform);
    painter.drawImage(target, image_);
    painter.setClipRect(target);
    const double sx=double(target.width())/image_.width(), sy=double(target.height())/image_.height();
    for (const auto& object:objects_) {
        const QColor color=QColor::fromHsv((object.class_id*47+150)%360,180,245);
        const QRectF box(target.left()+object.left*sx, target.top()+object.top*sy,
            (object.right-object.left)*sx, (object.bottom-object.top)*sy);
        painter.setPen(QPen(color,2));
        painter.drawRect(box);
        auto label=QStringLiteral("%1 %2%")
            .arg(QString::fromUtf8(frametrail::class_name(object.class_id).data()))
            .arg(qRound(object.confidence*100));
        for (const auto& track : tracks_) if (track.detection.class_id == object.class_id &&
            track.detection.left == object.left && track.detection.top == object.top &&
            track.detection.right == object.right && track.detection.bottom == object.bottom) {
            label += QStringLiteral(" #%1%2").arg(track.id).arg(track.confirmed ? QString{} : QStringLiteral("?"));
            break;
        }
        const auto text_size=painter.fontMetrics().size(Qt::TextSingleLine,label);
        const double label_x=std::clamp(box.left(),double(target.left()),
            std::max(double(target.left()),double(target.right()-text_size.width()-8)));
        const double label_y=std::max(double(target.top()),box.top()-text_size.height()-6);
        const QRectF label_box(label_x,label_y,text_size.width()+8,text_size.height()+6);
        painter.fillRect(label_box,color);
        painter.setPen(QColor("#09131a"));
        painter.drawText(label_box,Qt::AlignCenter,label);
    }
    const auto screen = [&](frametrail::Point p) {
        return QPointF(target.left()+p.x*target.width(),target.top()+p.y*target.height());
    };
    painter.setRenderHint(QPainter::Antialiasing);
    for (const auto& track : tracks_) {
        painter.setPen(QPen(QColor::fromHsv(int((track.id*67)%360),150,230),2));
        for (std::size_t i=1;i<track.trail.size();++i) painter.drawLine(screen(track.trail[i-1]),screen(track.trail[i]));
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
    setWindowTitle(QStringLiteral("FrameTrail — tracking and line crossings"));
    resize(1080, 720);
    setMinimumSize(680, 480);
    setStyleSheet(QStringLiteral(
        "QMainWindow, QWidget#shell { background: #151d28; color: #e4edf7; }"
        "QLabel { color: #e4edf7; font-family: 'Segoe UI'; font-size: 13px; }"
        "QLabel#title { font-size: 24px; font-weight: 600; }"
        "QLabel#subtitle, QLabel#source { color: #92a5bc; }"
        "QLabel#state { color: #73dfc3; }"
        "QCheckBox { color: #e4edf7; font-size: 13px; }"
        "QDoubleSpinBox { background: #263448; color: #e4edf7; padding: 5px; }"
        "QComboBox { background: #263448; color: #e4edf7; padding: 5px; }"
        "QPushButton { color: #e4edf7; background: #263448; border: 1px solid #394b62;"
        " border-radius: 6px; padding: 9px 18px; font-size: 13px; }"
        "QPushButton:hover { background: #33465f; }"
        "QPushButton:disabled { color: #60738a; background: #1b2635; border-color: #263448; }"
        "QPushButton#open { background: #187f6a; border-color: #239c82; }"
        "QPushButton#open:hover { background: #209b81; }"));

    auto* shell = new QWidget;
    shell->setObjectName(QStringLiteral("shell"));
    auto* layout = new QVBoxLayout(shell);
    layout->setContentsMargins(24, 22, 24, 22);
    layout->setSpacing(16);
    auto* header = new QHBoxLayout;
    auto* branding = new QVBoxLayout;
    auto* title = new QLabel(QStringLiteral("FrameTrail"));
    title->setObjectName(QStringLiteral("title"));
    auto* subtitle = new QLabel(QStringLiteral("CPU detection • Object IDs • Line crossings"));
    subtitle->setObjectName(QStringLiteral("subtitle"));
    branding->addWidget(title);
    branding->addWidget(subtitle);
    header->addLayout(branding);
    header->addStretch();
    auto* open = new QPushButton(QStringLiteral("Open media"));
    open->setObjectName(QStringLiteral("open"));
    header->addWidget(open);
    layout->addLayout(header);
    source_label_ = new QLabel(QStringLiteral("No file selected"));
    source_label_->setObjectName(QStringLiteral("source"));
    source_label_->setTextFormat(Qt::PlainText);
    layout->addWidget(source_label_);
    auto* analysis_controls=new QHBoxLayout;
    detect_box_=new QCheckBox(QStringLiteral("Detect objects (CPU)"));
    detect_box_->setObjectName(QStringLiteral("detectObjects"));
    detect_box_->setChecked(QFileInfo::exists(model_path_));
    detect_box_->setToolTip(QStringLiteral("YOLOX-Nano: 80 classes. Settings apply at the current position; analysis counts reset."));
    analysis_controls->addWidget(detect_box_);
    analysis_controls->addWidget(new QLabel(QStringLiteral("Confidence")));
    confidence_box_=new QDoubleSpinBox;
    confidence_box_->setObjectName(QStringLiteral("confidence"));
    confidence_box_->setRange(0.05,0.95);
    confidence_box_->setSingleStep(0.05);
    confidence_box_->setValue(0.35);
    analysis_controls->addWidget(confidence_box_);
    analysis_controls->addStretch();
    auto* model_label=new QLabel(QFileInfo::exists(model_path_) ? QStringLiteral("YOLOX-Nano • 80 classes") :
        QStringLiteral("Model missing — run fetch-model.ps1 and rebuild"));
    model_label->setObjectName(QStringLiteral("subtitle"));
    analysis_controls->addWidget(model_label);
    layout->addLayout(analysis_controls);
    auto* tracking_controls = new QHBoxLayout;
    track_box_ = new QCheckBox(QStringLiteral("Track && count"));
    track_box_->setObjectName(QStringLiteral("trackObjects")); track_box_->setChecked(true);
    track_box_->setEnabled(detect_box_->isChecked());
    tracking_controls->addWidget(track_box_);
    classes_box_ = new QComboBox;
    classes_box_->setObjectName(QStringLiteral("trackingClasses"));
    classes_box_->addItems({QStringLiteral("People & vehicles"),QStringLiteral("People"),QStringLiteral("Vehicles")});
    tracking_controls->addWidget(classes_box_);
    line_button_ = new QPushButton(QStringLiteral("Draw counting line"));
    line_button_->setObjectName(QStringLiteral("drawLine"));
    line_button_->setToolTip(QStringLiteral("Pause here, click A then B, and continue from this position. Right-click cancels."));
    tracking_controls->addWidget(line_button_);
    direction_box_ = new QComboBox;
    direction_box_->setObjectName(QStringLiteral("crossingDirection"));
    direction_box_->addItems({QStringLiteral("Both directions"),QStringLiteral("− → +"),QStringLiteral("+ → −")});
    direction_box_->setToolTip(QStringLiteral("Sides refer to the A→B line shown on the frame. For the default left-to-right line, + is below."));
    tracking_controls->addWidget(direction_box_);
    tracking_controls->addStretch();
    layout->addLayout(tracking_controls);
    counts_label_ = new QLabel(QStringLiteral("Video counts: − → +  0    |    + → −  0"));
    counts_label_->setObjectName(QStringLiteral("crossingCounts"));
    layout->addWidget(counts_label_);
    canvas_ = new FrameCanvas;
    layout->addWidget(canvas_, 1);
    auto* controls = new QHBoxLayout;
    play_button_ = new QPushButton(QStringLiteral("Pause"));
    play_button_->setObjectName(QStringLiteral("play"));
    stop_button_ = new QPushButton(QStringLiteral("Stop"));
    stop_button_->setObjectName(QStringLiteral("stop"));
    replay_button_ = new QPushButton(QStringLiteral("Replay"));
    replay_button_->setObjectName(QStringLiteral("replay"));
    for (auto* button : {play_button_, stop_button_, replay_button_}) {
        controls->addWidget(button);
        button->setEnabled(false);
    }
    controls->addStretch();
    state_label_ = new QLabel(QStringLiteral("Ready"));
    state_label_->setObjectName(QStringLiteral("state"));
    state_label_->setTextFormat(Qt::PlainText);
    state_label_->setWordWrap(true);
    controls->addWidget(state_label_, 1);
    layout->addLayout(controls);
    details_label_ = new QLabel(QStringLiteral("Local files • Image or silent video playback"));
    details_label_->setObjectName(QStringLiteral("subtitle"));
    layout->addWidget(details_label_);
    setCentralWidget(shell);

    connect(open, &QPushButton::clicked, this, [this] {
        const auto path = QFileDialog::getOpenFileName(this, QStringLiteral("Open image or video"), {},
            QStringLiteral("Media (*.mp4 *.mkv *.avi *.mov *.webm *.png *.jpg *.jpeg *.bmp *.ppm);;All files (*)"));
        if (!path.isEmpty()) open_file(path);
    });
    connect(play_button_, &QPushButton::clicked, this, [this] { toggle_playback(); });
    connect(stop_button_, &QPushButton::clicked, this, [this] { stop_playback(); });
    connect(replay_button_, &QPushButton::clicked, this, [this] { open_file(source_); });
    connect(detect_box_,&QCheckBox::toggled,this,[this](bool){reconfigure_analysis();});
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
    source_label_->setToolTip(path);
    details_label_->setText(QStringLiteral("Reading media…"));
    counts_label_->setText(QStringLiteral("Video counts: − → +  0    |    + → −  0"));
}

std::pair<std::optional<frametrail::DetectorOptions>,std::optional<frametrail::TrackingOptions>> PreviewWindow::analysis_options() {
    std::optional<frametrail::DetectorOptions> detection;
    if (detect_box_->isChecked()) detection=frametrail::DetectorOptions{
        native_path(model_path_),float(confidence_box_->value()),0.45f};
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
    if (wrapped.detection) details_label_->setText(details_label_->text()+QStringLiteral("    •    %1 objects    •    CPU %2 ms/frame")
        .arg(wrapped.detection->objects.size()).arg(wrapped.detection->elapsed_ms,0,'f',1));
    if (wrapped.tracking) {
        counts_label_->setText(QStringLiteral("Video counts: − → +  %1    |    + → −  %2    •    %3 observed tracks    •    Rules %4 ms")
            .arg(wrapped.tracking->negative_to_positive).arg(wrapped.tracking->positive_to_negative)
            .arg(wrapped.tracking->objects.size()).arg(wrapped.tracking->elapsed_ms,0,'f',2));
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
