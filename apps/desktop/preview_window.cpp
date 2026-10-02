#include "preview_window.hpp"

#include <QCloseEvent>
#include <QFileDialog>
#include <QFileInfo>
#include <QHBoxLayout>
#include <QLabel>
#include <QPainter>
#include <QPushButton>
#include <QVBoxLayout>
#include <algorithm>

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

void FrameCanvas::set_image(QImage image) {
    image_ = std::move(image);
    update();
}

void FrameCanvas::paintEvent(QPaintEvent*) {
    QPainter painter(this);
    painter.fillRect(rect(), QColor("#0c1118"));
    if (image_.isNull()) {
        painter.setPen(QColor("#8796a8"));
        painter.drawText(rect(), Qt::AlignCenter, QStringLiteral("Open an image or video to begin"));
        return;
    }
    const auto scaled = image_.size().scaled(size(), Qt::KeepAspectRatio);
    const QRect target((width() - scaled.width()) / 2, (height() - scaled.height()) / 2,
        scaled.width(), scaled.height());
    painter.setRenderHint(QPainter::SmoothPixmapTransform);
    painter.drawImage(target, image_);
}

PreviewWindow::PreviewWindow() {
    setWindowTitle(QStringLiteral("FrameTrail — Media preview"));
    resize(1080, 720);
    setMinimumSize(680, 480);
    setStyleSheet(QStringLiteral(
        "QMainWindow, QWidget#shell { background: #151d28; color: #e4edf7; }"
        "QLabel { color: #e4edf7; font-family: 'Segoe UI'; font-size: 13px; }"
        "QLabel#title { font-size: 24px; font-weight: 600; }"
        "QLabel#subtitle, QLabel#source { color: #92a5bc; }"
        "QLabel#state { color: #73dfc3; }"
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
    auto* subtitle = new QLabel(QStringLiteral("Image and video preview"));
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
    connect(&timer_, &QTimer::timeout, this, [this] { tick(); });
    timer_.start(10);
}

void PreviewWindow::open_file(const QString& path) {
    if (path.isEmpty() || closing_) return;
    pending_source_ = path;
    session_.stop();
    next_.reset();
    displayed_sequence_.reset();
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
}

void PreviewWindow::begin_pending_source() {
    source_ = pending_source_;
    pending_source_.clear();
    try {
        session_.start(native_path(source_));
        generation_ = session_.snapshot().generation;
        playing_ = true;
        stopped_ = false;
        clock_started_ = false;
        play_button_->setText(QStringLiteral("Pause"));
        play_button_->setEnabled(true);
        stop_button_->setEnabled(true);
        replay_button_->setEnabled(true);
    } catch (const std::exception& error) {
        state_label_->setText(QStringLiteral("Could not open: ") + QString::fromUtf8(error.what()));
        replay_button_->setEnabled(true);
    }
}

void PreviewWindow::toggle_playback() {
    if (stopped_ || !pending_source_.isEmpty()) return;
    const auto now = std::chrono::steady_clock::now();
    playing_ = !playing_;
    if (!playing_) pause_start_ = now;
    else if (clock_started_) playback_start_ += now - pause_start_;
    play_button_->setText(playing_ ? QStringLiteral("Pause") : QStringLiteral("Play"));
    state_label_->setText(playing_ ? QStringLiteral("Playing") : QStringLiteral("Paused"));
}

void PreviewWindow::stop_playback() {
    pending_source_.clear();
    session_.stop();
    next_.reset();
    playing_ = false;
    stopped_ = true;
    play_button_->setEnabled(false);
    stop_button_->setEnabled(false);
    state_label_->setText(QStringLiteral("Stopped"));
}

void PreviewWindow::display(frametrail::PreviewFrame wrapped) {
    if (wrapped.generation != generation_) return;
    const auto& frame = wrapped.frame;
    const QImage borrowed(frame.pixels.data(), frame.width, frame.height, frame.stride, QImage::Format_RGB888);
    canvas_->set_image(borrowed.copy()); // UI retains pixels after the frame leaves scope.
    displayed_sequence_ = frame.sequence;
    const auto info = session_.snapshot().info;
    details_label_->setText(QStringLiteral("%1 × %2    •    %3    •    Frame %4    •    %5")
        .arg(frame.width).arg(frame.height)
        .arg(info ? QString::fromStdString(info->codec) : QStringLiteral("Unknown codec"))
        .arg(frame.sequence).arg(timestamp_text(frame.timestamp)));
    state_label_->setText(QStringLiteral("Playing"));
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
    if (status.state == frametrail::PreviewState::failed) {
        next_.reset();
        stopped_ = true;
        playing_ = false;
        play_button_->setEnabled(false);
        stop_button_->setEnabled(false);
        state_label_->setText(QStringLiteral("Could not read: ") + QString::fromStdString(status.error));
        return;
    }
    if (!playing_) return;
    if (!next_) next_ = session_.try_pop();
    if (next_) {
        const auto now = std::chrono::steady_clock::now();
        if (!clock_started_) {
            first_timestamp_ = next_->frame.timestamp.value_or(std::chrono::microseconds{});
            playback_start_ = now;
            clock_started_ = true;
        }
        const auto timestamp = next_->frame.timestamp.value_or(
            first_timestamp_ + std::chrono::microseconds(next_->frame.sequence * 33333));
        if (now - playback_start_ >= timestamp - first_timestamp_) {
            display(std::move(*next_));
            next_.reset();
        }
    } else if (!status.worker_active && status.queued_frames == 0) {
        playing_ = false;
        stopped_ = true;
        play_button_->setEnabled(false);
        stop_button_->setEnabled(false);
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
