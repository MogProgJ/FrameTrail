#include "live_window.hpp"
#include "preview_window.hpp"
#include <QCheckBox>
#include <QCloseEvent>
#include <QComboBox>
#include <QDoubleSpinBox>
#include <QFileInfo>
#include <QHBoxLayout>
#include <QLabel>
#include <QPushButton>
#include <QVBoxLayout>

LiveWindow::LiveWindow(QString model):model_(std::move(model)) {
    setWindowTitle(QStringLiteral("FrameTrail — Live camera"));resize(1100,760);
    setStyleSheet(QStringLiteral("QWidget{background:#171f2a;color:#e3eaf2;} QPushButton,QComboBox,QDoubleSpinBox{background:#29394c;padding:7px;} QPushButton:disabled{color:#758699;} QLabel{background:transparent;}"));
    auto* body=new QWidget;auto* layout=new QVBoxLayout(body);
    auto* title=new QLabel(QStringLiteral("Live camera • CPU detection & counting"));title->setStyleSheet(QStringLiteral("font-size:22px;"));layout->addWidget(title);
    auto* sources=new QHBoxLayout;cameras_=new QComboBox;cameras_->setObjectName(QStringLiteral("cameraDevices"));sources->addWidget(cameras_,1);
    format_=new QComboBox;format_->addItems({QStringLiteral("Camera default format"),QStringLiteral("640 × 480 / 30 fps"),QStringLiteral("1280 × 720 / 30 fps")});sources->addWidget(format_);
    refresh_=new QPushButton(QStringLiteral("Refresh cameras"));sources->addWidget(refresh_);
    start_=new QPushButton(QStringLiteral("Start camera"));start_->setObjectName(QStringLiteral("startCamera"));sources->addWidget(start_);
    stop_=new QPushButton(QStringLiteral("Stop camera"));stop_->setObjectName(QStringLiteral("stopCamera"));sources->addWidget(stop_);layout->addLayout(sources);
    auto* options=new QHBoxLayout;
    detect_=new QCheckBox(QStringLiteral("Detect objects (CPU)"));detect_->setChecked(QFileInfo::exists(model_));options->addWidget(detect_);
    confidence_=new QDoubleSpinBox;confidence_->setRange(.05,.95);confidence_->setSingleStep(.05);confidence_->setValue(.35);options->addWidget(new QLabel(QStringLiteral("Confidence")));options->addWidget(confidence_);
    track_=new QCheckBox(QStringLiteral("Track & count"));track_->setChecked(true);options->addWidget(track_);
    classes_=new QComboBox;classes_->addItems({QStringLiteral("People & vehicles"),QStringLiteral("People"),QStringLiteral("Vehicles")});options->addWidget(classes_);
    direction_=new QComboBox;direction_->addItems({QStringLiteral("Both directions"),QStringLiteral("− → +"),QStringLiteral("+ → −")});options->addWidget(direction_);
    draw_=new QPushButton(QStringLiteral("Stop & draw line"));draw_->setObjectName(QStringLiteral("drawLiveLine"));options->addWidget(draw_);layout->addLayout(options);
    auto* hint=new QLabel(QStringLiteral("Choose settings before Start. Stop releases the camera; restarting begins new counts. No recording or saved replay."));hint->setWordWrap(true);layout->addWidget(hint);
    counts_=new QLabel(QStringLiteral("Crossings: − → + 0  |  + → − 0"));counts_->setObjectName(QStringLiteral("liveCounts"));layout->addWidget(counts_);
    canvas_=new FrameCanvas;canvas_->set_empty_text(QStringLiteral("Choose a camera, then click Start camera"));layout->addWidget(canvas_,1);
    metrics_=new QLabel(QStringLiteral("Capture and analysis metrics appear after Start."));metrics_->setWordWrap(true);layout->addWidget(metrics_);
    status_=new QLabel;status_->setObjectName(QStringLiteral("liveStatus"));status_->setWordWrap(true);status_->setTextFormat(Qt::PlainText);layout->addWidget(status_);setCentralWidget(body);
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
        if(detect_->isChecked())detector=frametrail::DetectorOptions{std::filesystem::path(model_.toStdWString()),float(confidence_->value()),.45f};
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
    if(closing_){if(!state.active)close();return;}
    if(auto frame=session_.try_pop()) {
        const auto& f=frame->frame;QImage borrowed(f.pixels.data(),f.width,f.height,f.stride,QImage::Format_RGB888);
        canvas_->set_image(borrowed.copy(),frame->detection ? frame->detection->objects : std::vector<frametrail::Detection>{},
            frame->tracking ? frame->tracking->objects : std::vector<frametrail::TrackedObject>{},frame->tracking ? std::optional(line_) : std::nullopt);
        const auto age=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-frame->arrived).count();
        metrics_->setText(QStringLiteral("%1 × %2 • captured %3 / analysed %4 • skipped before analysis %5 / before display %6 • processing %7 ms • arrival-to-display %8 ms")
            .arg(f.width).arg(f.height).arg(state.captured).arg(state.processed).arg(state.input_drops).arg(state.preview_drops).arg(frame->processing_ms,0,'f',1).arg(age,0,'f',1));
        if(frame->tracking)counts_->setText(QStringLiteral("Crossings: − → + %1  |  + → − %2").arg(frame->tracking->negative_to_positive).arg(frame->tracking->positive_to_negative));
    }
    if(pending_edit_ && !state.active) {pending_edit_=false;editing_=true;canvas_->begin_line_selection();status_->setText(QStringLiteral("Select A then B. Right-click cancels. Start camera afterwards."));}
    else if(!editing_)status_->setText(state.error.empty() ? QString::fromStdString(state.state) : QStringLiteral("Camera stopped: ")+QString::fromStdString(state.error));
    update_controls();
}
void LiveWindow::closeEvent(QCloseEvent* event) {
    if(session_.snapshot().active){closing_=true;session_.stop();event->ignore();status_->setText(QStringLiteral("Releasing camera…"));}
    else event->accept();
}
