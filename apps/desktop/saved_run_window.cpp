#include "saved_run_window.hpp"
#include "preview_window.hpp"
#include "model_selection.hpp"
#include "theme.hpp"
#include <QCloseEvent>
#include <QCoreApplication>
#include <QDragEnterEvent>
#include <QDropEvent>
#include <QFile>
#include <QFileDialog>
#include <QFileInfo>
#include <QHBoxLayout>
#include <QLabel>
#include <QListWidget>
#include <QMessageBox>
#include <QMimeData>
#include <QProgressBar>
#include <QPushButton>
#include <QSaveFile>
#include <QSignalBlocker>
#include <QSplitter>
#include <QToolButton>
#include <QUuid>
#include <QUrl>
#include <QVBoxLayout>
#include <QDoubleSpinBox>
#include <algorithm>
#include <numeric>

namespace {
std::filesystem::path native(const QString& value) {
#ifdef _WIN32
    return std::filesystem::path(value.toStdWString());
#else
    const auto bytes=value.toUtf8();return std::filesystem::path(std::u8string(bytes.begin(),bytes.end()));
#endif
}
QString text(const std::filesystem::path& path) {
    const auto bytes=path.u8string();return QString::fromUtf8(reinterpret_cast<const char*>(bytes.data()),qsizetype(bytes.size()));
}
QString time_text(std::optional<std::chrono::microseconds> time) {
    if(!time)return QStringLiteral("Time unavailable");
    const auto ms=std::max<std::int64_t>(0,time->count()/1000);
    return QStringLiteral("%1:%2:%3.%4").arg(ms/3600000,2,10,QChar('0')).arg((ms/60000)%60,2,10,QChar('0'))
        .arg((ms/1000)%60,2,10,QChar('0')).arg(ms%1000,3,10,QChar('0'));
}
QImage thumbnail_image(const std::vector<std::uint8_t>& value) {return QImage::fromData(value.data(),int(value.size()),"PPM");}
QString save_dialog(QWidget* parent,const QString& title,const QString& name,const QString& filter,const QString& suffix) {
    QFileDialog dialog(parent,title,name,filter);dialog.setAcceptMode(QFileDialog::AcceptSave);
    dialog.setFileMode(QFileDialog::AnyFile);dialog.setDefaultSuffix(suffix);
    return dialog.exec()==QDialog::Accepted ? dialog.selectedFiles().value(0) : QString{};
}
void atomic_copy(const QString& source,const QString& destination,bool replace) {
    std::error_code equivalent_error;
    if(std::filesystem::equivalent(native(source),native(destination),equivalent_error))
        throw std::runtime_error("Choose a different destination from the working analysis");
    if(QFileInfo(source).canonicalFilePath()==QFileInfo(destination).canonicalFilePath() && QFileInfo::exists(destination))
        throw std::runtime_error("Choose a different destination from the working analysis");
    if(!replace && QFileInfo::exists(destination))throw std::runtime_error("That file already exists; choose a new filename");
    QFile input(source);
    if(!input.open(QIODevice::ReadOnly))throw std::runtime_error(input.errorString().toStdString());
    QSaveFile output(destination);output.setDirectWriteFallback(false);
    if(!output.open(QIODevice::WriteOnly))throw std::runtime_error(output.errorString().toStdString());
    while(!input.atEnd()) {
        const auto bytes=input.read(1024*1024);
        if(bytes.isEmpty() && input.error()!=QFileDevice::NoError)throw std::runtime_error(input.errorString().toStdString());
        if(output.write(bytes)!=bytes.size())throw std::runtime_error(output.errorString().toStdString());
    }
    if(!output.commit())throw std::runtime_error(output.errorString().toStdString());
}
void protect_inputs(const frametrail::RunSummary& summary,const QString& output) {
    const auto destination=native(output);
    for(const auto& input:{summary.configuration.source,summary.configuration.detector.model}) {
        std::error_code error;
        if(std::filesystem::equivalent(input,destination,error) ||
            QFileInfo(text(input)).absoluteFilePath().compare(QFileInfo(output).absoluteFilePath(),Qt::CaseInsensitive)==0)
            throw std::runtime_error("Saving or exporting must not replace the video or model file");
    }
}
QString dropped_file(const QMimeData* data) {
    if(!data->hasUrls() || data->urls().size()!=1 || !data->urls()[0].isLocalFile())return {};
    const auto path=data->urls()[0].toLocalFile();const QFileInfo file(path);
    return file.isFile() && file.isReadable() ? file.absoluteFilePath() : QString{};
}
}

SavedRunWindow::SavedRunWindow(std::optional<frametrail::RunConfiguration> configuration):configuration_(std::move(configuration)) {
    setWindowTitle(QStringLiteral("FrameTrail — Video analysis"));resize(1240,820);setMinimumSize(920,620);setAcceptDrops(true);
    setStyleSheet(frametrail_theme()+QStringLiteral("QToolButton { color: #a1afc2; border: none; padding: 6px; background: transparent; }"));
    auto* shell=new QWidget;shell->setObjectName(QStringLiteral("shell"));auto* layout=new QVBoxLayout(shell);
    layout->setContentsMargins(24,22,24,22);layout->setSpacing(14);
    auto* header=new QHBoxLayout;auto* title=new QLabel(QStringLiteral("Video analysis"));title->setObjectName(QStringLiteral("title"));header->addWidget(title);header->addStretch();
    choose_=new QPushButton(QStringLiteral("Choose video…"));choose_->setObjectName(QStringLiteral("chooseVideo"));header->addWidget(choose_);
    open_=new QPushButton(QStringLiteral("Open analysis…"));open_->setObjectName(QStringLiteral("openRun"));header->addWidget(open_);layout->addLayout(header);
    source_=new QLabel(QStringLiteral("Drop a video into this window, or choose one to begin."));source_->setObjectName(QStringLiteral("analysisSource"));source_->setProperty("role","muted");source_->setTextFormat(Qt::PlainText);source_->setWordWrap(true);layout->addWidget(source_);
    auto* actions=new QHBoxLayout;
    analyse_=new QPushButton(QStringLiteral("Analyse video"));analyse_->setObjectName(QStringLiteral("saveAnalysis"));analyse_->setProperty("role","primary");actions->addWidget(analyse_);
    cancel_=new QPushButton(QStringLiteral("Cancel"));cancel_->setObjectName(QStringLiteral("cancelAnalysis"));actions->addWidget(cancel_);
    save_=new QPushButton(QStringLiteral("Save analysis…"));save_->setObjectName(QStringLiteral("saveRun"));actions->addWidget(save_);
    export_=new QPushButton(QStringLiteral("Export CSV…"));export_->setObjectName(QStringLiteral("exportRun"));actions->addWidget(export_);actions->addStretch();
    settings_toggle_=new QToolButton;settings_toggle_->setText(QStringLiteral("Analysis settings"));settings_toggle_->setCheckable(true);actions->addWidget(settings_toggle_);layout->addLayout(actions);
    settings_panel_=new QWidget;auto* options=new QHBoxLayout(settings_panel_);options->setContentsMargins(0,0,0,0);
    const auto nano=configuration_ && configuration_->detector.variant==frametrail::DetectorModel::nano && !configuration_->detector.model.empty() ?
        text(configuration_->detector.model) : QCoreApplication::applicationDirPath()+QStringLiteral("/models/yolox_nano.onnx");
    model_=model_selector(nano,this);
    if(configuration_ && configuration_->detector.variant==frametrail::DetectorModel::yolox_s) {
        model_->setItemData(1,text(configuration_->detector.model));model_->setCurrentIndex(1);
    }
    options->addWidget(new QLabel(QStringLiteral("Model")));options->addWidget(model_);
    options->addWidget(new QLabel(QStringLiteral("Confidence")));confidence_=new QDoubleSpinBox;confidence_->setObjectName(QStringLiteral("analysisConfidence"));
    confidence_->setRange(.05,.95);confidence_->setSingleStep(.05);confidence_->setValue(configuration_ ? configuration_->detector.confidence : .35);options->addWidget(confidence_);
    auto* hint=new QLabel(QStringLiteral("All 80 object categories · processed on this device"));hint->setProperty("role","muted");options->addWidget(hint);options->addStretch();
    settings_panel_->hide();layout->addWidget(settings_panel_);
    progress_=new QProgressBar;progress_->setObjectName(QStringLiteral("analysisProgress"));progress_->setTextVisible(false);progress_->setMaximumHeight(7);progress_->hide();layout->addWidget(progress_);
    status_=new QLabel(QStringLiteral("Choose a video to begin."));status_->setObjectName(QStringLiteral("analysisStatus"));status_->setTextFormat(Qt::PlainText);status_->setWordWrap(true);layout->addWidget(status_);
    auto* split=new QSplitter;canvas_=new FrameCanvas;canvas_->set_empty_text(QStringLiteral("Drop a video here\nChoose → Analyse → Review → Save"));split->addWidget(canvas_);
    auto* results=new QWidget;results_panel_=results;auto* results_layout=new QVBoxLayout(results);results_layout->setContentsMargins(0,0,0,0);results_layout->setSpacing(10);
    results_title_=new QLabel(QStringLiteral("Object appearances"));results_title_->setProperty("role","section");results_layout->addWidget(results_title_);
    events_=new QListWidget;events_->setObjectName(QStringLiteral("savedEvents"));events_->setIconSize(QSize(96,54));events_->setAcceptDrops(false);events_->viewport()->setAcceptDrops(false);results_layout->addWidget(events_,1);
    auto* paging=new QHBoxLayout;previous_=new QPushButton(QStringLiteral("Previous"));more_=new QPushButton(QStringLiteral("Next"));previous_->setObjectName(QStringLiteral("previousResults"));more_->setObjectName(QStringLiteral("nextResults"));paging->addWidget(previous_);paging->addWidget(more_);results_layout->addLayout(paging);previous_->hide();more_->hide();previous_->setEnabled(false);more_->setEnabled(false);
    split->addWidget(results);split->setStretchFactor(0,1);split->setStretchFactor(1,0);split->setSizes({810,345});layout->addWidget(split,1);
    auto* playback=new QHBoxLayout;play_=new QPushButton(QStringLiteral("Play"));play_->setObjectName(QStringLiteral("reviewPlay"));playback->addWidget(play_);
    back_=new QPushButton(QStringLiteral("Back to appearance"));back_->setObjectName(QStringLiteral("backToAppearance"));playback->addWidget(back_);
    review_status_=new QLabel(QStringLiteral("Results will appear here after analysis."));review_status_->setObjectName(QStringLiteral("reviewStatus"));review_status_->setProperty("role","muted");review_status_->setTextFormat(Qt::PlainText);review_status_->setWordWrap(true);playback->addWidget(review_status_,1);layout->addLayout(playback);setCentralWidget(shell);
    connect(choose_,&QPushButton::clicked,this,[this]{
        const auto path=QFileDialog::getOpenFileName(this,QStringLiteral("Choose a video"),{},QStringLiteral("Video (*.mp4 *.mkv *.avi *.mov *.webm *.m4v *.wmv *.mpg *.mpeg *.ts *.mts *.m2ts);;All files (*)"));
        if(!path.isEmpty())select_video(path);
    });
    connect(analyse_,&QPushButton::clicked,this,[this]{try{analyse_video();}catch(const std::exception& e){show_error(e);}});
    connect(open_,&QPushButton::clicked,this,[this]{
        const auto path=QFileDialog::getOpenFileName(this,QStringLiteral("Open analysis"),{},QStringLiteral("FrameTrail analysis (*.frametrail);;All files (*)"));
        if(!path.isEmpty()){try{open_run(path);}catch(const std::exception& e){show_error(e);}}
    });
    connect(cancel_,&QPushButton::clicked,this,[this]{job_.cancel();cancel_->setEnabled(false);status_->setText(QStringLiteral("Stopping analysis…"));});
    connect(save_,&QPushButton::clicked,this,[this]{choose_save();});
    connect(export_,&QPushButton::clicked,this,[this]{
        const auto name=summary_ ? QFileInfo(text(summary_->configuration.source)).completeBaseName()+QStringLiteral("-analysis.csv") : QStringLiteral("analysis.csv");
        const auto path=save_dialog(this,QStringLiteral("Export analysis CSV"),name,QStringLiteral("CSV (*.csv)"),QStringLiteral("csv"));
        if(!path.isEmpty()){try{export_analysis_csv(path,true);}catch(const std::exception& e){show_error(e);}}
    });
    connect(settings_toggle_,&QToolButton::toggled,settings_panel_,&QWidget::setVisible);
    connect(events_,&QListWidget::currentRowChanged,this,[this](int row){review_event(row);});
    connect(previous_,&QPushButton::clicked,this,[this]{if(cursors_.size()>1){cursors_.pop_back();try{load_page(cursors_.back());}catch(const std::exception& e){show_error(e);}}});
    connect(more_,&QPushButton::clicked,this,[this]{
        if(!appearances_.empty())cursors_.push_back(appearances_.back().id);
        else if(!page_.empty())cursors_.push_back(page_.back().event.id);
        else return;
        try{load_page(cursors_.back());}catch(const std::exception& e){show_error(e);}
    });
    connect(play_,&QPushButton::clicked,this,[this]{toggle_playback();});connect(back_,&QPushButton::clicked,this,[this]{review_event(events_->currentRow());});
    connect(&timer_,&QTimer::timeout,this,[this]{tick();});timer_.setTimerType(Qt::PreciseTimer);timer_.start(5);
    if(configuration_ && !configuration_->source.empty())select_video(text(configuration_->source));
    update_controls();
}
void SavedRunWindow::show_error(const std::exception& error) {status_->setText(QStringLiteral("Could not complete: ")+QString::fromUtf8(error.what()));update_controls();}
void SavedRunWindow::update_controls() {
    const bool busy=analysing() || awaiting_job_ || closing_;
    choose_->setEnabled(!busy);open_->setEnabled(!busy);analyse_->setEnabled(!busy && !selected_video_.isEmpty());
    cancel_->setVisible(busy && !closing_);cancel_->setEnabled(analysing() && job_.progress().status!="cancelled");
    save_->setVisible(store_.has_value());export_->setVisible(store_.has_value());save_->setEnabled(store_.has_value() && !busy);export_->setEnabled(store_.has_value() && !busy);
    settings_toggle_->setEnabled(!busy);model_->setEnabled(!busy);confidence_->setEnabled(!busy);
    results_panel_->setVisible(store_.has_value());
    play_->setVisible(store_.has_value());back_->setVisible(store_.has_value());
    if(busy){play_->setEnabled(false);back_->setEnabled(false);}
}
bool SavedRunWindow::confirm_discard() {
    if(!unsaved_)return true;
    const auto answer=QMessageBox::question(this,QStringLiteral("Keep this analysis?"),QStringLiteral("Save this analysis before continuing?"),QMessageBox::Save|QMessageBox::Discard|QMessageBox::Cancel,QMessageBox::Save);
    if(answer==QMessageBox::Save)return choose_save();
    if(answer==QMessageBox::Discard){unsaved_=false;return true;}
    return false;
}
bool SavedRunWindow::choose_save() {
    if(!store_ || analysing())return false;
    const auto name=QFileInfo(text(summary_->configuration.source)).completeBaseName()+QStringLiteral(".frametrail");
    const auto path=save_dialog(this,QStringLiteral("Save analysis"),name,QStringLiteral("FrameTrail analysis (*.frametrail)"),QStringLiteral("frametrail"));
    if(path.isEmpty())return false;
    try{save_analysis(path,true);return true;}catch(const std::exception& e){show_error(e);return false;}
}
bool SavedRunWindow::select_video(const QString& video) {
    if(analysing() || awaiting_job_ || closing_)return false;
    const QFileInfo file(video);
    if(!file.isFile() || !file.isReadable()){status_->setText(QStringLiteral("Choose one readable local video file."));return false;}
    if(!confirm_discard())return false;
    review_.stop();pending_review_.reset();next_.reset();playing_=false;awaiting_frame_=false;displayed_timestamp_.reset();
    store_.reset();summary_.reset();page_.clear();appearances_.clear();events_->clear();cursors_={0};database_.clear();unsaved_=false;
    selected_video_=file.absoluteFilePath();source_->setText(file.fileName());source_->setToolTip(selected_video_);
    canvas_->set_image({});canvas_->set_empty_text(QStringLiteral("Ready to analyse\n%1").arg(file.fileName()));
    status_->setText(QStringLiteral("Ready. Analyse the video to find object appearances."));review_status_->setText(QStringLiteral("Click an appearance to review its timestamp."));results_title_->setText(QStringLiteral("Object appearances"));
    play_->setEnabled(false);back_->setEnabled(false);previous_->hide();more_->hide();progress_->hide();update_controls();return true;
}
void SavedRunWindow::dragEnterEvent(QDragEnterEvent* event) {
    if(!analysing() && !awaiting_job_ && !closing_ && !dropped_file(event->mimeData()).isEmpty())event->acceptProposedAction();
}
void SavedRunWindow::dropEvent(QDropEvent* event) {
    const auto path=dropped_file(event->mimeData());
    if(!path.isEmpty() && select_video(path))event->acceptProposedAction();
}
void SavedRunWindow::analyse_video() {
    if(selected_video_.isEmpty())throw std::runtime_error("Choose or drop a video first");
    if(!scratch_.isValid())throw std::runtime_error("Could not create a temporary analysis workspace");
    if(!confirm_discard())return;
    frametrail::RunConfiguration config;
    config.source=native(selected_video_);config.detector={native(model_->currentData().toString()),float(confidence_->value()),.45f,selected_model(model_)};
    if(configuration_) {config.detector.backend=configuration_->detector.backend;config.detector.gpu_device=configuration_->detector.gpu_device;}
    config.kind=frametrail::RunKind::appearances;config.tracking.classes.resize(80);std::iota(config.tracking.classes.begin(),config.tracking.classes.end(),0);config.tracking.line.reset();
    start_analysis(scratch_.filePath(QUuid::createUuid().toString(QUuid::WithoutBraces)+QStringLiteral(".frametrail")),std::move(config));
}
void SavedRunWindow::start_analysis(const QString& database,frametrail::RunConfiguration configuration) {
    if(analysing())throw std::logic_error("An analysis is already running");
    if(std::filesystem::exists(native(database)))throw std::runtime_error("Analysis destination already exists; choose a new filename");
    review_.stop();pending_review_.reset();next_.reset();playing_=false;awaiting_frame_=false;play_->setEnabled(false);back_->setEnabled(false);displayed_timestamp_.reset();preview_sequence_.reset();
    store_.reset();summary_.reset();page_.clear();appearances_.clear();events_->clear();canvas_->set_image({});canvas_->set_empty_text(QStringLiteral("Starting analysis…"));unsaved_=false;
    previous_->hide();more_->hide();source_->setText(QFileInfo(text(configuration.source)).fileName());source_->setToolTip(text(configuration.source));
    database_=database;draft_job_=QFileInfo(database).absolutePath()==scratch_.path();job_.start(native(database),std::move(configuration));awaiting_job_=true;
    progress_->setRange(0,0);progress_->show();status_->setText(QStringLiteral("Starting analysis…"));review_status_->setText(QStringLiteral("Processing locally. Save the result when you’re ready."));update_controls();
}
void SavedRunWindow::save_analysis(const QString& output,bool replace) {
    if(!store_ || analysing() || awaiting_job_)throw std::logic_error("Wait for analysis to finish before saving");
    protect_inputs(*summary_,output);
    atomic_copy(database_,output,replace);unsaved_=false;status_->setText(QStringLiteral("Analysis saved · %1").arg(QFileInfo(output).fileName()));
}
void SavedRunWindow::export_analysis_csv(const QString& output,bool replace) {
    if(!store_ || analysing() || awaiting_job_)throw std::logic_error("Wait for analysis to finish before exporting");
    protect_inputs(*summary_,output);
    std::error_code equivalent_error;
    if(std::filesystem::equivalent(native(database_),native(output),equivalent_error) ||
        QFileInfo(database_).absoluteFilePath().compare(QFileInfo(output).absoluteFilePath(),Qt::CaseInsensitive)==0)
        throw std::runtime_error("CSV export must not replace the working analysis file");
    const auto staging=scratch_.filePath(QUuid::createUuid().toString(QUuid::WithoutBraces)+QStringLiteral(".csv"));
    if(summary_->configuration.kind==frametrail::RunKind::appearances)store_->export_appearances_csv(native(staging));else store_->export_csv(native(staging));
    try{atomic_copy(staging,output,replace);}catch(...){QFile::remove(staging);throw;}
    QFile::remove(staging);status_->setText(QStringLiteral("CSV exported · %1").arg(QFileInfo(output).fileName()));
}
void SavedRunWindow::open_run(const QString& database) {
    if(analysing())throw std::logic_error("Cancel the active analysis before opening another result");
    frametrail::RunStore candidate(native(database));auto info=candidate.summary();
    if(!confirm_discard())return;
    review_.stop();pending_review_.reset();next_.reset();playing_=false;awaiting_frame_=false;play_->setEnabled(false);back_->setEnabled(false);displayed_timestamp_.reset();canvas_->set_image({});
    store_.emplace(std::move(candidate));summary_=std::move(info);database_=database;cursors_={0};unsaved_=false;
    const auto& s=*summary_;source_->setText(QFileInfo(text(s.configuration.source)).fileName());source_->setToolTip(text(s.configuration.source));
    selected_video_=store_->source_available() ? text(s.configuration.source) : QString{};
    const bool objects=s.configuration.kind==frametrail::RunKind::appearances;
    results_title_->setText(objects ? QStringLiteral("Object appearances") : QStringLiteral("Line crossings · earlier analysis"));
    const auto outcome=s.status=="completed" ? QStringLiteral("Analysis completed") : s.status=="cancelled" ? QStringLiteral("Analysis cancelled · partial results") : QStringLiteral("Analysis incomplete");
    status_->setText(outcome+(objects ? QStringLiteral(" · %1 appearances · %2 object types").arg(s.appearance_count).arg(s.class_count) : QStringLiteral(" · %1 crossings").arg(s.event_count)));
    if(!s.error.empty())status_->setText(status_->text()+QStringLiteral(" · ")+QString::fromStdString(s.error));
    canvas_->set_empty_text(objects ? QStringLiteral("No object appearances found\nTry a lower confidence in Analysis settings") : QStringLiteral("No crossing events in this analysis"));
    review_status_->setText(store_->source_available() ? QStringLiteral("Click an appearance to review it.") : QStringLiteral("Video missing or changed. Thumbnails and exports are still available."));
    progress_->hide();load_page(0);update_controls();
}
void SavedRunWindow::load_page(std::uint64_t after) {
    if(!store_)return;
    const bool objects=summary_->configuration.kind==frametrail::RunKind::appearances;
    QSignalBlocker block(events_);events_->clear();page_.clear();appearances_.clear();
    if(objects) {
        appearances_=store_->appearances(after);
        for(const auto& value:appearances_) {
            auto* item=new QListWidgetItem(QIcon(QPixmap::fromImage(thumbnail_image(value.thumbnail))),
                QStringLiteral("%1\n%2 → %3").arg(QString::fromUtf8(frametrail::class_name(value.first_detection.class_id).data())).arg(time_text(value.first_timestamp)).arg(time_text(value.last_timestamp)),events_);
            item->setSizeHint(QSize(300,78));item->setToolTip(QStringLiteral("Appearance #%1 · %2 observations · peak confidence %3%\nFrame span includes short detection gaps; IDs belong to this analysis.").arg(value.id).arg(value.observations).arg(value.peak_confidence*100,0,'f',1));
        }
    } else {
        page_=store_->events(after);
        for(const auto& value:page_) {
            const auto& e=value.event;
            auto* item=new QListWidgetItem(QIcon(QPixmap::fromImage(thumbnail_image(value.thumbnail))),QStringLiteral("%1\n%2").arg(QString::fromUtf8(frametrail::class_name(e.class_id).data())).arg(time_text(e.timestamp)),events_);
            item->setSizeHint(QSize(300,78));
        }
    }
    const auto last=objects ? (appearances_.empty() ? 0:appearances_.back().id) : (page_.empty() ? 0:page_.back().event.id);
    const bool next=last && (objects ? !store_->appearances(last,1).empty() : !store_->events(last,1).empty());
    previous_->setVisible(cursors_.size()>1 || next);more_->setVisible(cursors_.size()>1 || next);previous_->setEnabled(cursors_.size()>1);more_->setEnabled(next);
    if(events_->count()>0){events_->setCurrentRow(0);review_event(0);}
    else {back_->setEnabled(false);play_->setEnabled(false);}
}
void SavedRunWindow::review_event(int row) {
    if(!store_ || row<0 || row>=events_->count())return;
    review_.stop();next_.reset();pending_review_.reset();playing_=false;awaiting_frame_=false;clock_started_=false;review_box_.reset();
    displayed_timestamp_.reset();play_->setEnabled(false);play_->setText(QStringLiteral("Play"));back_->setEnabled(true);
    std::optional<std::chrono::microseconds> timestamp;std::uint64_t sequence;
    if(summary_->configuration.kind==frametrail::RunKind::appearances) {
        const auto& value=appearances_.at(row);timestamp=value.first_timestamp;sequence=value.first_sequence;review_box_=value.first_detection;
        canvas_->set_image(thumbnail_image(value.thumbnail));
    }else {
        const auto& value=page_.at(row);timestamp=value.event.timestamp;sequence=value.event.sequence;canvas_->set_image(thumbnail_image(value.thumbnail));
    }
    if(!store_->source_available()){review_status_->setText(QStringLiteral("Video missing or changed. Showing the saved thumbnail."));return;}
    pending_review_=frametrail::ReviewPosition{summary_->timestamp_seekable ? timestamp : std::nullopt,sequence};review_status_->setText(QStringLiteral("Opening %1…").arg(time_text(timestamp)));
}
void SavedRunWindow::toggle_playback() {
    if(awaiting_frame_ || pending_review_ || !displayed_timestamp_ || !summary_)return;
    if(playing_){playing_=false;paused_=std::chrono::steady_clock::now();play_->setText(QStringLiteral("Play"));}
    else {clock_+=std::chrono::steady_clock::now()-paused_;playing_=true;play_->setText(QStringLiteral("Pause"));}
}
void SavedRunWindow::tick() {
    const auto progress=job_.progress();
    if(closing_) {
        if(!progress.active && !review_.snapshot().worker_active) {
            if(awaiting_job_) {
                awaiting_job_=false;
                try{open_run(database_);unsaved_=draft_job_;}catch(const std::exception& e){show_error(e);}
            }
            closing_=false;update_controls();close();
        }
        return;
    }
    if(awaiting_job_) {
        if(progress.active) {
            status_->setText(QStringLiteral("Analysing video · %1 / %2").arg(time_text(progress.timestamp)).arg(time_text(progress.duration)));
            if(progress.duration && progress.duration->count()>0 && progress.timestamp){progress_->setRange(0,100);progress_->setValue(int(std::clamp(double(progress.timestamp->count())/progress.duration->count()*100,0.,99.)));}
            if(progress.preview && preview_sequence_!=progress.preview->frame.sequence) {
                const auto& frame=progress.preview->frame;QImage image(frame.pixels.data(),frame.width,frame.height,frame.stride,QImage::Format_RGB888);
                canvas_->set_image(image.copy(),progress.preview->detections);preview_sequence_=frame.sequence;
            }
            return;
        }
        awaiting_job_=false;progress_->hide();
        try{open_run(database_);unsaved_=draft_job_;if(unsaved_)review_status_->setText(review_status_->text()+QStringLiteral(" Save analysis to keep these results."));}
        catch(const std::exception& e){show_error(e);if(!progress.error.empty())status_->setText(QString::fromStdString(progress.error));}
        update_controls();
    }
    const auto state=review_.snapshot();
    if(pending_review_) {
        if(!state.worker_active){try{review_.start(summary_->configuration.source,{},{},pending_review_);pending_review_.reset();awaiting_frame_=true;}catch(const std::exception& e){pending_review_.reset();review_status_->setText(QString::fromUtf8(e.what()));}}
        return;
    }
    if(state.state==frametrail::PreviewState::failed){awaiting_frame_=false;playing_=false;play_->setEnabled(false);next_.reset();review_status_->setText(QStringLiteral("Could not review: ")+QString::fromStdString(state.error));return;}
    if(!awaiting_frame_ && !playing_)return;
    if(!next_)next_=review_.try_pop();
    if(next_) {
        const auto now=std::chrono::steady_clock::now();
        if(!clock_started_){first_timestamp_=next_->frame.timestamp.value_or(std::chrono::microseconds{});first_sequence_=next_->frame.sequence;clock_=now;paused_=now;clock_started_=true;}
        std::optional<frametrail::PreviewFrame> present;std::chrono::microseconds time{};
        for(int budget=0;next_ && budget<4;++budget) {
            const auto candidate=next_->frame.timestamp.value_or(first_timestamp_+std::chrono::microseconds((next_->frame.sequence-first_sequence_)*33333));
            if(!awaiting_frame_ && now-clock_<candidate-first_timestamp_)break;
            time=candidate;present=std::move(next_);next_.reset();if(awaiting_frame_)break;next_=review_.try_pop();
        }
        if(present) {
            const auto& frame=present->frame;QImage image(frame.pixels.data(),frame.width,frame.height,frame.stride,QImage::Format_RGB888);
            canvas_->set_image(image.copy(),awaiting_frame_ && review_box_ ? std::vector<frametrail::Detection>{*review_box_} : std::vector<frametrail::Detection>{});displayed_timestamp_=time;
            review_status_->setText(time_text(frame.timestamp));
            if(awaiting_frame_){awaiting_frame_=false;paused_=now;play_->setEnabled(true);}
        }
    }else if(!state.worker_active){playing_=false;awaiting_frame_=false;play_->setEnabled(false);play_->setText(QStringLiteral("Finished"));}
}
void SavedRunWindow::closeEvent(QCloseEvent* event) {
    if(!closing_ && !analysing() && !awaiting_job_ && !confirm_discard()){event->ignore();return;}
    if(job_.progress().active || review_.snapshot().worker_active){closing_=true;job_.cancel();review_.stop();event->ignore();status_->setText(QStringLiteral("Closing analysis…"));}
    else {review_.release();store_.reset();event->accept();}
}
