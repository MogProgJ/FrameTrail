#include "live_window.hpp"
#include "model_selection.hpp"
#include "preview_window.hpp"
#include "theme.hpp"
#include "studio_controls.hpp"
#include <QFrame>
#include <QScrollArea>
#include <QCheckBox>
#include <QCloseEvent>
#include <QComboBox>
#include <QDoubleSpinBox>
#include <QFileInfo>
#include <QHBoxLayout>
#include <QLabel>
#include <QPushButton>
#include <QVBoxLayout>

LiveWindow::LiveWindow(QString model,frametrail::DetectorModel variant,frametrail::DetectorBackend backend):model_(std::move(model)) {
    setWindowTitle(QStringLiteral("FrameTrail — Live camera")); resize(1280, 820); setMinimumSize(980, 640);
    install_studio_style();setStyleSheet(frametrail_theme());
    auto* body = new QWidget; body->setObjectName(QStringLiteral("shell"));
    auto* layout = new QVBoxLayout(body); layout->setContentsMargins(20,18,20,18); layout->setSpacing(18);
    auto* header = new QHBoxLayout;
    auto* title = new QLabel(QStringLiteral("Live camera")); title->setObjectName(QStringLiteral("title")); header->addWidget(title);studio_heading(header);
    header->addStretch(); camera_indicator_ = new QLabel(QStringLiteral("Camera off"));
    camera_indicator_->setObjectName(QStringLiteral("cameraIndicator")); camera_indicator_->setProperty("role", "badge"); header->addWidget(camera_indicator_); layout->addLayout(header);
    auto* hint = new QLabel(QStringLiteral("Start camera activates your webcam. Frames stay on this device; no audio, recording, or upload."));
    hint->setWordWrap(true); hint->setProperty("role", "muted"); layout->addWidget(hint);
    auto* workspace = new QHBoxLayout; workspace->setSpacing(12);
    auto* video = new QVBoxLayout;
    canvas_ = new FrameCanvas; canvas_->set_empty_text(QStringLiteral("Your camera is off\nChoose a device, then click Start camera")); video->addWidget(canvas_,1);
    auto* transport = new QHBoxLayout;
    start_ = new QPushButton(QStringLiteral("Start camera")); start_->setObjectName(QStringLiteral("startCamera")); start_->setProperty("role", "primary"); transport->addWidget(start_);
    stop_ = new QPushButton(QStringLiteral("Stop camera")); stop_->setObjectName(QStringLiteral("stopCamera")); transport->addWidget(stop_);
    status_ = new QLabel; status_->setObjectName(QStringLiteral("liveStatus")); status_->setTextFormat(Qt::PlainText); status_->setWordWrap(true); transport->addWidget(status_,1); video->addLayout(transport);
    metrics_ = new QLabel(QStringLiteral("Capture and analysis metrics appear after Start.")); metrics_->setWordWrap(true); metrics_->setProperty("role", "muted"); video->addWidget(metrics_); workspace->addLayout(video,1);
    auto* panel = new QFrame; panel->setObjectName(QStringLiteral("inspector"));
    auto* options = new QVBoxLayout(panel); options->setContentsMargins(16,18,16,18); options->setSpacing(9);
    const auto caption = [&](const QString& text) {auto* label = new QLabel(text); label->setProperty("role","section"); options->addWidget(label);};
    caption(QStringLiteral("CAMERA SOURCE"));
    cameras_ = new QComboBox; cameras_->setObjectName(QStringLiteral("cameraDevices")); cameras_->setAccessibleName(QStringLiteral("Camera device")); cameras_->setSizeAdjustPolicy(QComboBox::AdjustToMinimumContentsLengthWithIcon); cameras_->setMinimumContentsLength(12); options->addWidget(cameras_);
    format_ = new QComboBox; format_->setAccessibleName(QStringLiteral("Capture format")); format_->addItems({QStringLiteral("Camera default format"),QStringLiteral("640 × 480 / 30 fps"),QStringLiteral("1280 × 720 / 30 fps")}); options->addWidget(format_);
    refresh_ = new QPushButton(QStringLiteral("Refresh cameras")); options->addWidget(refresh_);
    caption(QStringLiteral("ANALYSIS"));
    model_box_=model_selector(model_,this);model_box_->setMinimumWidth(0);model_box_->setSizePolicy(QSizePolicy::Ignored,QSizePolicy::Fixed);
    model_box_->setCurrentIndex(int(variant));
    options->addWidget(model_box_);
    backend_box_=backend_selector(this);backend_box_->setCurrentIndex(backend==frametrail::DetectorBackend::cpu ? 0:1);options->addWidget(backend_box_);
    detect_ = new QCheckBox(QStringLiteral("Detect objects")); detect_->setChecked(QFileInfo::exists(model_)); options->addWidget(detect_);
    auto* confidenceLabel = new QLabel(QStringLiteral("Confidence threshold")); options->addWidget(confidenceLabel);
    confidence_ = new QDoubleSpinBox; confidence_->setRange(.05,.95); confidence_->setSingleStep(.05); confidence_->setValue(.35); confidenceLabel->setBuddy(confidence_); confidence_->setAccessibleName(QStringLiteral("Confidence threshold")); options->addWidget(confidence_);
    track_ = new QCheckBox(QStringLiteral("Track && count")); track_->setChecked(true); options->addWidget(track_);
    classes_ = new QComboBox; classes_->setAccessibleName(QStringLiteral("Objects to count")); classes_->addItems({QStringLiteral("People & vehicles"),QStringLiteral("People"),QStringLiteral("Vehicles")}); options->addWidget(classes_);
    direction_ = new QComboBox; direction_->setAccessibleName(QStringLiteral("Crossing direction")); direction_->addItems({QStringLiteral("Both directions"),QStringLiteral("− → +"),QStringLiteral("+ → −")}); options->addWidget(direction_);
    draw_ = new QPushButton(QStringLiteral("Stop && draw line")); draw_->setObjectName(QStringLiteral("drawLiveLine")); options->addWidget(draw_);
    auto* settingsHint = new QLabel(QStringLiteral("Change settings while stopped. Restarting begins fresh IDs and counts.")); settingsHint->setWordWrap(true); settingsHint->setProperty("role","muted"); options->addWidget(settingsHint); options->addStretch();
    caption(QStringLiteral("THIS SESSION")); counts_ = new QLabel(QStringLiteral("Crossings: − → + 0  |  + → − 0")); counts_->setWordWrap(true); counts_->setObjectName(QStringLiteral("liveCounts")); options->addWidget(counts_);
    auto* scroll = new QScrollArea; scroll->setWidgetResizable(true); scroll->setFixedWidth(304);scroll->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff); scroll->setWidget(panel); workspace->addWidget(scroll); layout->addLayout(workspace,1); setCentralWidget(body);studio_button(start_,"camera");studio_button(stop_,"stop");studio_button(draw_,"analyse");
    connect(refresh_,&QPushButton::clicked,this,[this]{refresh();});
    connect(start_,&QPushButton::clicked,this,[this]{start();});
    connect(stop_,&QPushButton::clicked,this,[this]{session_.stop();status_->setText(QStringLiteral("Stopping camera…"));});
    connect(detect_,&QCheckBox::toggled,this,[this]{update_controls();});connect(track_,&QCheckBox::toggled,this,[this]{update_controls();});
    connect(draw_,&QPushButton::clicked,this,[this]{session_.stop();pending_edit_=true;update_controls();});
    canvas_->line_selected=[this](frametrail::CountingLine line){line_=line;editing_=false;status_->setText(QStringLiteral("Line ready. Start camera to begin fresh counts."));update_controls();};
    canvas_->line_cancelled=[this]{editing_=false;status_->setText(QStringLiteral("Line unchanged. Start camera to resume live capture."));update_controls();};
    connect(&timer_,&QTimer::timeout,this,[this]{tick();});timer_.setTimerType(Qt::PreciseTimer);timer_.start(10);
    refresh();
}
void LiveWindow::refresh() {
    if(session_.snapshot().active)return;
    cameras_->clear();devices_.clear();
    try {
        devices_=frametrail::list_cameras();
        for(const auto& device:devices_)cameras_->addItem(QString::fromStdString(device.name));
        status_->setText(devices_.empty() ? QStringLiteral("No camera found. Connect a webcam and Refresh cameras.") : QStringLiteral("Ready. The camera opens only when you click Start camera."));
    }catch(const std::exception& e){status_->setText(QString::fromUtf8(e.what()));}
    update_controls();
}
void LiveWindow::update_controls() {
    const bool active=session_.snapshot().active;const bool editable=!active && !editing_ && !pending_edit_ && !closing_;
    start_->setEnabled(editable && cameras_->currentIndex()>=0);stop_->setEnabled(active && !closing_);
    for(auto* widget:{static_cast<QWidget*>(cameras_),static_cast<QWidget*>(format_),static_cast<QWidget*>(refresh_),static_cast<QWidget*>(detect_)})widget->setEnabled(editable);
    model_box_->setEnabled(editable);backend_box_->setEnabled(editable);
    confidence_->setEnabled(editable && detect_->isChecked());track_->setEnabled(editable && detect_->isChecked());
    classes_->setEnabled(editable && detect_->isChecked() && track_->isChecked());direction_->setEnabled(classes_->isEnabled());
    draw_->setEnabled(!editing_ && !pending_edit_ && !closing_ && !canvas_->image().isNull() && detect_->isChecked() && track_->isChecked());
}
void LiveWindow::start() {
    if(cameras_->currentIndex()<0 || session_.snapshot().active)return;
    try {
        frametrail::CameraInput camera{devices_.at(cameras_->currentIndex()).id};
        if(format_->currentIndex()>0){camera.width=format_->currentIndex()==1 ? 640:1280;camera.height=format_->currentIndex()==1 ? 480:720;camera.fps=30;}
        std::optional<frametrail::DetectorOptions> detector;
        if(detect_->isChecked())detector=frametrail::DetectorOptions{std::filesystem::path(model_box_->currentData().toString().toStdWString()),float(confidence_->value()),.45f,selected_model(model_box_),selected_backend(backend_box_)};
        std::optional<frametrail::TrackingOptions> tracking;
        if(detector && track_->isChecked()) {
            tracking=frametrail::TrackingOptions{};if(classes_->currentIndex()==1)tracking->classes={0};if(classes_->currentIndex()==2)tracking->classes={1,2,3,5,7};
            line_.direction=direction_->currentIndex()==1 ? frametrail::CrossingDirection::negative_to_positive : direction_->currentIndex()==2 ? frametrail::CrossingDirection::positive_to_negative : frametrail::CrossingDirection::both;
            tracking->line=line_;
        }
        canvas_->set_image({});counts_->setText(QStringLiteral("Crossings: − → + 0  |  + → − 0"));
        session_.start(std::move(camera),std::move(detector),std::move(tracking));status_->setText(QStringLiteral("Opening camera…"));
    }catch(const std::exception& e){status_->setText(QString::fromUtf8(e.what()));}
    update_controls();
}
void LiveWindow::tick() {
    const auto state=session_.snapshot();
    camera_indicator_->setText(state.active ? QStringLiteral("Camera requested / in use") : QStringLiteral("Camera off"));
    if(closing_){if(!state.active)close();return;}
    if(auto frame=session_.try_pop()) {
        const auto& f=frame->frame;QImage borrowed(f.pixels.data(),f.width,f.height,f.stride,QImage::Format_RGB888);
        canvas_->set_image(borrowed.copy(),frame->detection ? frame->detection->objects : std::vector<frametrail::Detection>{},
            frame->tracking ? frame->tracking->objects : std::vector<frametrail::TrackedObject>{},frame->tracking ? std::optional(line_) : std::nullopt);
        const auto age=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-frame->arrived).count();
        metrics_->setText(QStringLiteral("%1 × %2 • captured %3 / analysed %4 • skipped before analysis %5 / before display %6 • processing %7 ms • arrival-to-display %8 ms")
            .arg(f.width).arg(f.height).arg(state.captured).arg(state.processed).arg(state.input_drops).arg(state.preview_drops).arg(frame->processing_ms,0,'f',1).arg(age,0,'f',1));
        if(frame->detection) {
            const auto& execution=frame->detection->execution;
            metrics_->setText(metrics_->text()+QStringLiteral(" · %1").arg(execution.provider=="DirectML" ? QStringLiteral("GPU"):QStringLiteral("CPU")));
            metrics_->setToolTip(QString::fromStdString(execution.provider+" / "+execution.runtime+" / "+execution.device+"\n"+execution.fallback));
        }
        if(frame->tracking)counts_->setText(QStringLiteral("Crossings: − → + %1  |  + → − %2").arg(frame->tracking->negative_to_positive).arg(frame->tracking->positive_to_negative));
    }
    if(pending_edit_ && !state.active) {pending_edit_=false;editing_=true;canvas_->begin_line_selection();status_->setText(QStringLiteral("Select A then B. Right-click cancels. Start camera afterwards."));}
    else if(!editing_ && (state.state!="idle" || !state.error.empty()))status_->setText(state.error.empty() ? QString::fromStdString(state.state) : QStringLiteral("Camera stopped: ")+QString::fromStdString(state.error));
    update_controls();
}
void LiveWindow::closeEvent(QCloseEvent* event) {
    if(session_.snapshot().active){closing_=true;session_.stop();event->ignore();status_->setText(QStringLiteral("Releasing camera…"));}
    else event->accept();
}
