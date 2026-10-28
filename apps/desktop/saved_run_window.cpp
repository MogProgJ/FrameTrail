#include "saved_run_window.hpp"
#include "preview_window.hpp"
#include "model_selection.hpp"
#include "theme.hpp"
#include "studio_controls.hpp"
#include "processing_feedback.hpp"
#include "appearance_timeline.hpp"
#include "recent_files.hpp"
#include "model_comparison.hpp"
#include <QPainter>
#include <QDir>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QShortcut>
#include <QStandardPaths>
#include <QPainterPath>
#include <map>
#include <QFrame>
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
// Saved thumbnail with the object picked out: the rest of the frame dimmed, the box in its type colour.
QIcon appearance_icon(const QImage& thumbnail,const frametrail::Detection& box,int width,int height,std::optional<bool> verdict={}) {
    if(thumbnail.isNull())return {};
    auto image=thumbnail.convertToFormat(QImage::Format_RGB32).scaled(thumbnail.size()*2,Qt::KeepAspectRatio,Qt::SmoothTransformation);
    const double sx=double(image.width())/std::max(1,width),sy=double(image.height())/std::max(1,height);
    const QRectF object(box.left*sx,box.top*sy,(box.right-box.left)*sx,(box.bottom-box.top)*sy);
    QPainter painter(&image);painter.setRenderHint(QPainter::Antialiasing);
    QPainterPath outside;outside.addRect(image.rect());QPainterPath inside;inside.addRect(object);
    painter.fillPath(outside.subtracted(inside),QColor(0,0,0,120));
    painter.setPen(QPen(ft::ui::category_color(box.class_id),2.5));painter.setBrush(Qt::NoBrush);painter.drawRect(object);
    if(verdict) { // Review badge: green check for correct, red cross for wrong.
        const double r=image.height()*.2;const QPointF centre(image.width()-r-5,image.height()-r-5);
        painter.setPen(QPen(QColor(0,0,0,140),2));painter.setBrush(*verdict ? QColor("#3fae4f") : QColor("#e0444f"));painter.drawEllipse(centre,r,r);
        painter.save();painter.translate(centre-QPointF(r*.7,r*.7));painter.scale(r*1.4/20.,r*1.4/20.);
        painter.fillPath(fluent_path(*verdict ? QStringLiteral("check") : QStringLiteral("dismiss")),Qt::white);painter.restore();
    }
    return QIcon(QPixmap::fromImage(image));
}
// 0:02.4 style: minutes, seconds and tenths.
QString short_time(std::optional<std::chrono::microseconds> time) {
    if(!time)return QStringLiteral("?");
    const auto tenths=std::max<std::int64_t>(0,time->count()/100000);
    return QStringLiteral("%1:%2.%3").arg(tenths/600).arg(tenths/10%60,2,10,QChar('0')).arg(tenths%10);
}
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
    install_studio_style();setStyleSheet(frametrail_theme());
    auto* shell=new QWidget;shell->setObjectName(QStringLiteral("shell"));auto* layout=new QVBoxLayout(shell);
    layout->setContentsMargins(20,18,20,18);layout->setSpacing(14);
    auto* header=new QHBoxLayout;auto* title=new QLabel(QStringLiteral("Analysis"));title->setObjectName(QStringLiteral("title"));header->addWidget(title);studio_heading(header);header->addStretch();
    choose_=new QPushButton(QStringLiteral("Choose video…"));choose_->setObjectName(QStringLiteral("chooseVideo"));header->addWidget(choose_);
    open_=new QPushButton(QStringLiteral("Open analysis…"));open_->setObjectName(QStringLiteral("openRun"));header->addWidget(open_);layout->addLayout(header);
    source_=new QLabel(QStringLiteral("No video chosen"));source_->setObjectName(QStringLiteral("analysisSource"));source_->setProperty("role","muted");source_->setTextFormat(Qt::PlainText);source_->setMinimumWidth(0);source_->setSizePolicy(QSizePolicy::Ignored,QSizePolicy::Preferred);header->insertWidget(header->indexOf(title)+1,source_,1);
    auto* actions=new QHBoxLayout;
    analyse_=new QPushButton(QStringLiteral("Analyse video"));analyse_->setObjectName(QStringLiteral("saveAnalysis"));analyse_->setProperty("role","primary");actions->addWidget(analyse_);
    cancel_=new QPushButton(QStringLiteral("Cancel"));cancel_->setObjectName(QStringLiteral("cancelAnalysis"));actions->addWidget(cancel_);
    save_=new QPushButton(QStringLiteral("Save analysis…"));save_->setObjectName(QStringLiteral("saveRun"));actions->addWidget(save_);
    export_=new QPushButton(QStringLiteral("Export CSV…"));export_->setObjectName(QStringLiteral("exportRun"));actions->addWidget(export_);
    export_review_=new QPushButton(QStringLiteral("Export review…"));export_review_->setObjectName(QStringLiteral("exportReview"));actions->addWidget(export_review_);
    compare_=new QPushButton(QStringLiteral("Compare models"));compare_->setObjectName(QStringLiteral("compareModels"));
    compare_->setToolTip(QStringLiteral("Compare the reviewed analyses of this video made with different models"));actions->addWidget(compare_);actions->addStretch();
    settings_toggle_=new QToolButton;settings_toggle_->setText(QStringLiteral("Settings"));settings_toggle_->setCheckable(true);actions->addWidget(settings_toggle_);layout->addLayout(actions);
    settings_panel_=new QWidget;auto* options=new QHBoxLayout(settings_panel_);options->setContentsMargins(0,0,0,0);
    const auto nano=configuration_ && configuration_->detector.variant==frametrail::DetectorModel::nano && !configuration_->detector.model.empty() ?
        text(configuration_->detector.model) : QCoreApplication::applicationDirPath()+QStringLiteral("/models/yolox_nano.onnx");
    model_=model_selector(nano,this);
    if(configuration_) {
        const auto index=int(configuration_->detector.variant);
        if(!configuration_->detector.model.empty())model_->setItemData(index,text(configuration_->detector.model));
        model_->setCurrentIndex(index);
    } else if(QFileInfo::exists(model_->itemData(1).toString()))model_->setCurrentIndex(1);
    options->addWidget(new QLabel(QStringLiteral("Model")));options->addWidget(model_);
    options->addWidget(new QLabel(QStringLiteral("Confidence")));confidence_=new QDoubleSpinBox;confidence_->setObjectName(QStringLiteral("analysisConfidence"));
    confidence_->setRange(.05,.95);confidence_->setSingleStep(.05);confidence_->setValue(configuration_ ? configuration_->detector.confidence : .35);options->addWidget(confidence_);
    options->addWidget(new QLabel(QStringLiteral("Frames")));frame_step_=new QComboBox;frame_step_->setObjectName(QStringLiteral("analysisFrameStep"));
    for(const auto& [label,step]:{std::pair{QStringLiteral("Every frame"),1},{QStringLiteral("Every 2nd · faster"),2},
        {QStringLiteral("Every 3rd · faster"),3},{QStringLiteral("Every 5th · fastest"),5}})frame_step_->addItem(label,step);
    frame_step_->setToolTip(QStringLiteral("Run the detector on every Nth frame. Long videos finish several times faster; tracks continue between "
        "the analysed frames, and appearance times are accurate to a few frames."));
    if(configuration_)frame_step_->setCurrentIndex(std::max(0,frame_step_->findData(int(configuration_->tracking.frame_step))));
    options->addWidget(frame_step_);
    model_->setMinimumWidth(0);model_->setMaximumWidth(300);model_->setSizePolicy(QSizePolicy::Ignored,QSizePolicy::Fixed);
    auto* hint=new QLabel;hint->setWordWrap(true);hint->setMinimumWidth(0);
    const auto update_hint=[this,hint]{hint->setText(frametrail::is_rf_model(selected_model(model_)) ? QStringLiteral("Experimental RF · false alarms expected") : QStringLiteral("All %1 object categories · on this device").arg(frametrail::model_category_count(selected_model(model_))));};
    update_hint();connect(model_,&QComboBox::currentIndexChanged,this,[update_hint]{update_hint();});hint->setProperty("role","muted");options->addWidget(hint);options->addStretch();
    settings_panel_->hide();layout->addWidget(settings_panel_);
    progress_=new QProgressBar;progress_->setObjectName(QStringLiteral("analysisProgress"));progress_->setTextVisible(false);progress_->setMaximumHeight(7);progress_->hide();layout->addWidget(progress_);
    status_=new QLabel(QStringLiteral("Choose a video to begin."));status_->setObjectName(QStringLiteral("analysisStatus"));status_->setTextFormat(Qt::PlainText);status_->setWordWrap(true);layout->addWidget(status_);
    auto* split=new QSplitter;split->setHandleWidth(12);split->setChildrenCollapsible(false);
    auto* review=new QWidget;auto* review_layout=new QVBoxLayout(review);review_layout->setContentsMargins(0,0,0,0);review_layout->setSpacing(10);
    canvas_=new FrameCanvas;canvas_->set_empty_icon(QStringLiteral("analysis"));canvas_->set_empty_text(QStringLiteral("Find every object in a video\nDrop a video here or choose one. Analyse it once, then review, save or export the appearances."));review_layout->addWidget(canvas_,1);
    auto* transport=new QFrame;transport->setObjectName(QStringLiteral("transportBar"));auto* playback=new QHBoxLayout(transport);playback->setContentsMargins(8,6,12,6);playback->setSpacing(6);
    play_=new QPushButton(QStringLiteral("Play"));play_->setObjectName(QStringLiteral("reviewPlay"));play_->setProperty("role","subtle");playback->addWidget(play_);
    back_=new QPushButton(QStringLiteral("Back to appearance"));back_->setObjectName(QStringLiteral("backToAppearance"));back_->setProperty("role","subtle");playback->addWidget(back_);
    review_status_=new QLabel(QStringLiteral("Results will appear here after analysis."));review_status_->setObjectName(QStringLiteral("reviewStatus"));review_status_->setProperty("role","muted");review_status_->setTextFormat(Qt::PlainText);playback->addWidget(review_status_,1);
    correct_=new QPushButton(QStringLiteral("Correct"));correct_->setObjectName(QStringLiteral("markCorrect"));
    correct_->setIcon(studio_icon(QStringLiteral("check"),ft::ui::success,QColor(),4));correct_->setIconSize(QSize(22,18));
    correct_->setToolTip(QStringLiteral("The box and label are right · C"));playback->addWidget(correct_);
    wrong_=new QPushButton(QStringLiteral("Wrong"));wrong_->setObjectName(QStringLiteral("markWrong"));
    wrong_->setIcon(studio_icon(QStringLiteral("dismiss"),QColor("#ff7b84"),QColor(),4));wrong_->setIconSize(QSize(22,18));
    wrong_->setToolTip(QStringLiteral("A false alarm or the wrong object type · X  (U clears)"));playback->addWidget(wrong_);
    review_layout->addWidget(transport);
    timeline_=new AppearanceTimeline;timeline_->hide();review_layout->addWidget(timeline_);
    timeline_->activated=[this](std::uint64_t id){select_appearance(id);};
    split->addWidget(review);
    auto* results=new QFrame;results->setObjectName(QStringLiteral("inspector"));results_panel_=results;auto* results_layout=new QVBoxLayout(results);results_layout->setContentsMargins(14,16,14,14);results_layout->setSpacing(10);
    results_title_=new QLabel(QStringLiteral("Object appearances"));results_title_->setProperty("role","section");results_title_->setContentsMargins(4,0,0,0);results_layout->addWidget(results_title_);
    review_progress_=new QLabel;review_progress_->setObjectName(QStringLiteral("reviewProgress"));review_progress_->setProperty("role","caption");
    review_progress_->setWordWrap(true);review_progress_->setTextFormat(Qt::PlainText);review_progress_->setContentsMargins(4,0,0,0);results_layout->addWidget(review_progress_);
    review_bar_=new QProgressBar;review_bar_->setObjectName(QStringLiteral("reviewBar"));review_bar_->setTextVisible(false);review_bar_->setMaximumHeight(4);results_layout->addWidget(review_bar_);
    chips_=new QWidget;chips_layout_=new FlowLayout(chips_,6);chips_->hide();results_layout->addWidget(chips_);
    events_=new QListWidget;events_->setObjectName(QStringLiteral("savedEvents"));events_->setIconSize(QSize(96,54));events_->setAcceptDrops(false);events_->viewport()->setAcceptDrops(false);results_layout->addWidget(events_,1);
    auto* paging=new QHBoxLayout;previous_=new QPushButton(QStringLiteral("Previous"));more_=new QPushButton(QStringLiteral("Next"));previous_->setObjectName(QStringLiteral("previousResults"));more_->setObjectName(QStringLiteral("nextResults"));paging->addWidget(previous_);paging->addWidget(more_);results_layout->addLayout(paging);previous_->hide();more_->hide();previous_->setEnabled(false);more_->setEnabled(false);
    split->addWidget(results);split->setStretchFactor(0,1);split->setStretchFactor(1,0);split->setSizes({820,360});layout->addWidget(split,1);setCentralWidget(shell);
    connect(choose_,&QPushButton::clicked,this,[this]{
        const auto path=QFileDialog::getOpenFileName(this,QStringLiteral("Choose a video"),{},QStringLiteral("Video (*.mp4 *.mkv *.avi *.mov *.webm *.m4v *.wmv *.mpg *.mpeg *.ts *.mts *.m2ts);;All files (*)"));
        if(!path.isEmpty())select_video(path);
    });
    connect(analyse_,&QPushButton::clicked,this,[this]{try{analyse_video();}catch(const std::exception& e){show_error(e);}});
    connect(open_,&QPushButton::clicked,this,[this]{
        const auto path=QFileDialog::getOpenFileName(this,QStringLiteral("Open analysis"),{},QStringLiteral("FrameTrail analysis (*.frametrail);;All files (*)"));
        if(!path.isEmpty()){try{open_run(path);}catch(const std::exception& e){show_error(e);}}
    });
    connect(cancel_,&QPushButton::clicked,this,[this]{cancel_requested_=true;job_.cancel();cancel_->setEnabled(false);status_->setText(QStringLiteral("Stopping analysis…"));});
    connect(save_,&QPushButton::clicked,this,[this]{choose_save();});
    connect(export_,&QPushButton::clicked,this,[this]{
        const auto name=summary_ ? QFileInfo(text(summary_->configuration.source)).completeBaseName()+QStringLiteral("-analysis.csv") : QStringLiteral("analysis.csv");
        const auto path=save_dialog(this,QStringLiteral("Export analysis CSV"),name,QStringLiteral("CSV (*.csv)"),QStringLiteral("csv"));
        if(!path.isEmpty()){try{export_analysis_csv(path,true);}catch(const std::exception& e){show_error(e);}}
    });
    connect(settings_toggle_,&QToolButton::toggled,settings_panel_,&QWidget::setVisible);
    review_folder_=QDir(QStandardPaths::writableLocation(QStandardPaths::AppDataLocation)).filePath(QStringLiteral("reviews"));
    connect(correct_,&QPushButton::clicked,this,[this]{set_verdict(events_->currentRow(),true,true);});
    connect(wrong_,&QPushButton::clicked,this,[this]{set_verdict(events_->currentRow(),false,true);});
    const std::pair<Qt::Key,int> keys[]={{Qt::Key_C,1},{Qt::Key_X,0},{Qt::Key_U,-1}};
    for(const auto& [key,value]:keys) {
        auto* shortcut=new QShortcut(QKeySequence(key),this);shortcut->setContext(Qt::WidgetWithChildrenShortcut);
        connect(shortcut,&QShortcut::activated,this,[this,value]{
            if(!correct_->isVisible() || !correct_->isEnabled())return;
            set_verdict(events_->currentRow(),value<0 ? std::nullopt : std::optional<bool>(value==1),value>=0);
        });
    }
    connect(compare_,&QPushButton::clicked,this,[this]{
        if(summary_)show_model_comparison(this,review_folder_,QFileInfo(text(summary_->configuration.source)).fileName());
    });
    connect(export_review_,&QPushButton::clicked,this,[this]{
        const auto name=summary_ ? QFileInfo(text(summary_->configuration.source)).completeBaseName()+QStringLiteral("-review.csv") : QStringLiteral("review.csv");
        const auto path=save_dialog(this,QStringLiteral("Export review"),name,QStringLiteral("CSV (*.csv)"),QStringLiteral("csv"));
        if(!path.isEmpty()){try{export_review_csv(path,true);}catch(const std::exception& e){show_error(e);}}
    });
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
    studio_button(choose_,"open");studio_button(open_,"history");studio_button(analyse_,"analysis");studio_button(play_,"play");
    studio_button(save_,"save");studio_button(export_,"export");studio_button(export_review_,"check");studio_button(compare_,"analysis");studio_button(back_,"replay");studio_button(cancel_,"dismiss");
    settings_toggle_->setIcon(studio_icon(QStringLiteral("settings")));settings_toggle_->setToolButtonStyle(Qt::ToolButtonTextBesideIcon);
    update_controls();
}
void SavedRunWindow::show_error(const std::exception& error) {status_->setText(QStringLiteral("Could not complete: ")+QString::fromUtf8(error.what()));update_controls();}
void SavedRunWindow::update_controls() {
    const bool busy=analysing() || awaiting_job_ || closing_;
    choose_->setEnabled(!busy);open_->setEnabled(!busy);analyse_->setEnabled(!busy && !selected_video_.isEmpty());
    cancel_->setVisible(busy && !closing_);cancel_->setEnabled(analysing() && !cancel_requested_);
    save_->setVisible(store_.has_value());export_->setVisible(store_.has_value());save_->setEnabled(store_.has_value() && !busy);export_->setEnabled(store_.has_value() && !busy);
    settings_toggle_->setEnabled(!busy);model_->setEnabled(!busy);confidence_->setEnabled(!busy);frame_step_->setEnabled(!busy);
    results_panel_->setVisible(store_.has_value());
    play_->setVisible(store_.has_value());back_->setVisible(store_.has_value());
    const bool reviewable=store_.has_value() && summary_ && summary_->configuration.kind==frametrail::RunKind::appearances;
    correct_->setVisible(reviewable);wrong_->setVisible(reviewable);review_progress_->setVisible(reviewable);review_bar_->setVisible(reviewable);
    correct_->setEnabled(reviewable && !busy && events_->currentRow()>=0);wrong_->setEnabled(correct_->isEnabled());
    export_review_->setVisible(reviewable && !verdicts_.empty());export_review_->setEnabled(!busy);
    compare_->setVisible(reviewable);compare_->setEnabled(!busy);
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
    store_.reset();summary_.reset();page_.clear();appearances_.clear();events_->clear();verdicts_.clear();cursors_={0};database_.clear();unsaved_=false;
    selected_video_=file.absoluteFilePath();source_->setText(file.fileName());source_->setToolTip(selected_video_);remember_file(selected_video_);
    timeline_->set_spans({},0);timeline_->hide();chips_->hide();
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
    config.kind=frametrail::RunKind::appearances;config.tracking.classes=frametrail::model_classes(config.detector.variant);std::sort(config.tracking.classes.begin(),config.tracking.classes.end());
    config.tracking.classes.erase(std::unique(config.tracking.classes.begin(),config.tracking.classes.end()),config.tracking.classes.end());config.tracking.line.reset();
    config.tracking.frame_step=unsigned(frame_step_->currentData().toInt());
    start_analysis(scratch_.filePath(QUuid::createUuid().toString(QUuid::WithoutBraces)+QStringLiteral(".frametrail")),std::move(config));
}
void SavedRunWindow::start_analysis(const QString& database,frametrail::RunConfiguration configuration) {
    if(analysing())throw std::logic_error("An analysis is already running");
    if(std::filesystem::exists(native(database)))throw std::runtime_error("Analysis destination already exists; choose a new filename");
    review_.stop();pending_review_.reset();next_.reset();playing_=false;awaiting_frame_=false;play_->setEnabled(false);back_->setEnabled(false);displayed_timestamp_.reset();preview_sequence_.reset();
    store_.reset();summary_.reset();page_.clear();appearances_.clear();events_->clear();verdicts_.clear();load_overview();canvas_->set_image({});canvas_->set_empty_text(QStringLiteral("Starting analysis…"));unsaved_=false;
    previous_->hide();more_->hide();source_->setText(QFileInfo(text(configuration.source)).fileName());source_->setToolTip(text(configuration.source));
    database_=database;draft_job_=QFileInfo(database).absolutePath()==scratch_.path();cancel_requested_=false;analysis_started_=std::chrono::steady_clock::now();job_.start(native(database),std::move(configuration));awaiting_job_=true;
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
    if(QFileInfo(database).absolutePath()!=scratch_.path())remember_file(database);
    const auto& s=*summary_;source_->setText(QFileInfo(text(s.configuration.source)).fileName());source_->setToolTip(text(s.configuration.source));
    selected_video_=store_->source_available() ? text(s.configuration.source) : QString{};
    const bool objects=s.configuration.kind==frametrail::RunKind::appearances;
    results_title_->setText(objects ? QStringLiteral("Object appearances") : QStringLiteral("Line crossings · earlier analysis"));
    const auto outcome=s.status=="completed" ? QStringLiteral("Analysis completed") : s.status=="cancelled" ? QStringLiteral("Analysis cancelled · partial results") : QStringLiteral("Analysis incomplete");
    status_->setText(outcome+(objects ? QStringLiteral(" · %1 appearances · %2 object types").arg(s.appearance_count).arg(s.class_count) : QStringLiteral(" · %1 crossings").arg(s.event_count)));
    status_->setToolTip(QString::fromStdString(s.error)); // Keep raw diagnostics available without presenting a requested cancellation as an error.
    if(!s.error.empty() && s.status!="cancelled")status_->setText(status_->text()+QStringLiteral(" · ")+QString::fromStdString(s.error));
    canvas_->set_empty_text(objects ? QStringLiteral("No object appearances found\nTry a lower confidence in Analysis settings") : QStringLiteral("No crossing events in this analysis"));
    review_status_->setText(store_->source_available() ? QStringLiteral("Click an appearance to review it.") : QStringLiteral("Video missing or changed. Thumbnails and exports are still available."));
    progress_->hide();load_reviews();load_overview();load_page(0);update_review_summary();update_controls();
}
void SavedRunWindow::load_page(std::uint64_t after) {
    if(!store_)return;
    const bool objects=summary_->configuration.kind==frametrail::RunKind::appearances;
    QSignalBlocker block(events_);events_->clear();page_.clear();appearances_.clear();
    if(objects) {
        appearances_=store_->appearances(after);
        for(const auto& value:appearances_) {
            const auto seconds=value.first_timestamp && value.last_timestamp ? double((*value.last_timestamp-*value.first_timestamp).count())/1e6 : 0.;
            const auto found=verdicts_.find(value.id);
            auto* item=new QListWidgetItem(appearance_icon(thumbnail_image(value.thumbnail),value.first_detection,summary_->media.width,summary_->media.height,
                    found==verdicts_.end() ? std::nullopt : std::optional<bool>(found->second.correct)),
                QStringLiteral("%1\n%2 – %3  ·  %4 s  ·  %5%").arg(QString::fromUtf8(frametrail::class_name(value.first_detection.class_id).data()),
                    short_time(value.first_timestamp),short_time(value.last_timestamp)).arg(seconds,0,'f',1).arg(qRound(value.peak_confidence*100)),events_);
            item->setSizeHint(QSize(300,70));item->setToolTip(QStringLiteral("Appearance #%1 · %2 observations · peak confidence %3%\nFrame span includes short detection gaps; IDs belong to this analysis.").arg(value.id).arg(value.observations).arg(value.peak_confidence*100,0,'f',1));
        }
    } else {
        page_=store_->events(after);
        for(const auto& value:page_) {
            const auto& e=value.event;
            auto* item=new QListWidgetItem(QIcon(QPixmap::fromImage(thumbnail_image(value.thumbnail))),QStringLiteral("%1\n%2").arg(QString::fromUtf8(frametrail::class_name(e.class_id).data())).arg(time_text(e.timestamp)),events_);
            item->setSizeHint(QSize(300,68));
        }
    }
    const auto last=objects ? (appearances_.empty() ? 0:appearances_.back().id) : (page_.empty() ? 0:page_.back().event.id);
    const bool next=last && (objects ? !store_->appearances(last,1).empty() : !store_->events(last,1).empty());
    previous_->setVisible(cursors_.size()>1 || next);more_->setVisible(cursors_.size()>1 || next);previous_->setEnabled(cursors_.size()>1);more_->setEnabled(next);
    if(events_->count()>0){events_->setCurrentRow(0);review_event(0);}
    else {back_->setEnabled(false);play_->setEnabled(false);}
}
void SavedRunWindow::load_overview() {
    while(auto* item=chips_layout_->takeAt(0)){delete item->widget();delete item;}
    chips_by_type_.clear();
    if(!store_ || summary_->configuration.kind!=frametrail::RunKind::appearances){timeline_->set_spans({},0);timeline_->hide();chips_->hide();return;}
    std::vector<AppearanceTimeline::Span> spans;
    std::map<int,std::pair<int,std::uint64_t>> types; // object type -> appearances, first appearance id
    std::uint64_t after=0;
    for(int page=0;page<20;++page) { // Overview of the first 2,000 appearances; the list pages through all of them.
        const auto rows=store_->appearances(after,100);if(rows.empty())break;
        for(const auto& value:rows) {
            after=value.id;auto& type=types[value.first_detection.class_id];if(!type.first)type.second=value.id;++type.first;
            if(value.first_timestamp)spans.push_back({value.id,value.first_detection.class_id,value.first_timestamp->count()/1e6,
                value.last_timestamp.value_or(*value.first_timestamp).count()/1e6});
        }
    }
    timeline_->set_spans(std::move(spans),summary_->media.duration ? summary_->media.duration->count()/1e6 : 0.);timeline_->setVisible(!timeline_->empty());
    std::vector<std::pair<int,std::pair<int,std::uint64_t>>> ordered(types.begin(),types.end());
    std::stable_sort(ordered.begin(),ordered.end(),[](const auto& a,const auto& b){return a.second.first>b.second.first;});
    for(const auto& [type,info]:ordered) {
        auto* chip=new QPushButton(QStringLiteral("%1  %2").arg(QString::fromUtf8(frametrail::class_name(type).data())).arg(info.first));
        chip->setProperty("role","chip");chip->setCursor(Qt::PointingHandCursor);chip->setToolTip(QStringLiteral("Jump to the first appearance"));
        QPixmap dot(QSize(10,10)*2);dot.setDevicePixelRatio(2);dot.fill(Qt::transparent);
        {QPainter painter(&dot);painter.setRenderHint(QPainter::Antialiasing);painter.setPen(Qt::NoPen);painter.setBrush(ft::ui::category_color(type));painter.drawEllipse(QRectF(1,1,8,8));}
        chip->setIcon(QIcon(dot));chip->setIconSize(QSize(10,10));
        const auto first=info.second;connect(chip,&QPushButton::clicked,this,[this,first]{select_appearance(first);});
        chips_by_type_[type]={info.first,chip};
        chips_layout_->addWidget(chip);
    }
    chips_->setVisible(!ordered.empty());
}
void SavedRunWindow::select_appearance(std::uint64_t id) {
    for(int row=0;row<int(appearances_.size());++row)if(appearances_[std::size_t(row)].id==id){events_->setCurrentRow(row);return;}
    if(id==0 || !store_)return;
    cursors_.push_back(id-1);
    try{load_page(id-1);}catch(const std::exception& e){show_error(e);}
}
void SavedRunWindow::review_event(int row) {
    if(!store_ || row<0 || row>=events_->count())return;
    review_.stop();next_.reset();pending_review_.reset();playing_=false;awaiting_frame_=false;clock_started_=false;review_box_.reset();
    displayed_timestamp_.reset();play_->setEnabled(false);play_->setText(QStringLiteral("Play"));back_->setEnabled(true);
    std::optional<std::chrono::microseconds> timestamp;std::uint64_t sequence;
    if(summary_->configuration.kind==frametrail::RunKind::appearances) {
        const auto& value=appearances_.at(row);timestamp=value.first_timestamp;sequence=value.first_sequence;review_box_=value.first_detection;
        canvas_->set_image(thumbnail_image(value.thumbnail));timeline_->set_selected(value.id);
        timeline_->set_playhead(value.first_timestamp ? std::optional<double>(value.first_timestamp->count()/1e6) : std::nullopt);
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
void SavedRunWindow::suspend_playback(){if(playing_)toggle_playback();}
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
            if(cancel_requested_){status_->setText(QStringLiteral("Stopping analysis…"));return;}
            const auto elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-analysis_started_).count();
            const auto feedback=processing_feedback(progress.frames,elapsed,progress.first_timestamp,progress.timestamp,progress.duration);
            status_->setText(progress.frames ? QStringLiteral("Analysing · %1").arg(feedback.text) : QStringLiteral("Opening video and detector… · %1 elapsed").arg(work_duration(elapsed)));
            if(feedback.permille){progress_->setRange(0,1000);progress_->setValue(*feedback.permille);}
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
            canvas_->set_image(image.copy(),awaiting_frame_ && review_box_ ? std::vector<frametrail::Detection>{*review_box_} : std::vector<frametrail::Detection>{});displayed_timestamp_=time;timeline_->set_playhead(time.count()/1e6);
            review_status_->setText(time_text(frame.timestamp));
            if(awaiting_frame_){awaiting_frame_=false;paused_=now;play_->setEnabled(true);}
        }
    }else if(!state.worker_active){playing_=false;awaiting_frame_=false;play_->setEnabled(false);play_->setText(QStringLiteral("Finished"));}
}
void SavedRunWindow::closeEvent(QCloseEvent* event) {
    if(!closing_ && !analysing() && !awaiting_job_ && !confirm_discard()){event->ignore();if(workspace_close_decision)workspace_close_decision(false);return;}
    if(job_.progress().active || review_.snapshot().worker_active){closing_=true;job_.cancel();review_.stop();event->ignore();status_->setText(QStringLiteral("Closing analysis…"));}
    else {review_.release();store_.reset();event->accept();if(workspace_close_decision)workspace_close_decision(true);}
}

// --- Review: correct / wrong verdicts per appearance -------------------------------------------
void SavedRunWindow::set_review_folder(const QString& folder) {review_folder_=folder;if(store_){load_reviews();load_page(cursors_.back());update_review_summary();}}
QString SavedRunWindow::review_file() const {
    return summary_ ? QDir(review_folder_).filePath(QString::fromStdString(summary_->id)+QStringLiteral(".json")) : QString{};
}
std::optional<bool> SavedRunWindow::verdict(int row) const {
    if(row<0 || row>=int(appearances_.size()))return std::nullopt;
    const auto found=verdicts_.find(appearances_[std::size_t(row)].id);
    return found==verdicts_.end() ? std::nullopt : std::optional<bool>(found->second.correct);
}
void SavedRunWindow::load_reviews() {
    verdicts_.clear();
    QFile file(review_file());
    if(review_file().isEmpty() || !file.open(QIODevice::ReadOnly))return;
    const auto root=QJsonDocument::fromJson(file.readAll()).object();
    if(root.value(QStringLiteral("run_id")).toString()!=QString::fromStdString(summary_->id))return;
    for(const auto& entry:root.value(QStringLiteral("verdicts")).toArray()) {
        const auto row=entry.toObject();
        const auto id=row.value(QStringLiteral("appearance")).toInteger(0);
        if(id>0)verdicts_[std::uint64_t(id)]={row.value(QStringLiteral("correct")).toBool(),row.value(QStringLiteral("class_id")).toInt()};
    }
}
void SavedRunWindow::save_reviews() {
    if(!summary_)return;
    QJsonArray rows;
    for(const auto& [id,value]:verdicts_)rows.append(QJsonObject{{QStringLiteral("appearance"),qint64(id)},{QStringLiteral("class_id"),value.class_id},
        {QStringLiteral("object"),QString::fromUtf8(frametrail::class_name(value.class_id).data())},{QStringLiteral("correct"),value.correct}});
    const QJsonObject root{{QStringLiteral("schema"),1},{QStringLiteral("run_id"),QString::fromStdString(summary_->id)},
        {QStringLiteral("video"),QFileInfo(text(summary_->configuration.source)).fileName()},
        {QStringLiteral("model"),QString::fromUtf8(frametrail::model_name(summary_->configuration.detector.variant).data())},
        {QStringLiteral("confidence"),summary_->configuration.detector.confidence},
        {QStringLiteral("appearances"),qint64(summary_->appearance_count)},{QStringLiteral("verdicts"),rows}};
    QSaveFile file(review_file());
    if(!QDir().mkpath(review_folder_) || !file.open(QIODevice::WriteOnly) || file.write(QJsonDocument(root).toJson())<0 || !file.commit())
        status_->setText(QStringLiteral("Could not save the review in %1").arg(QDir::toNativeSeparators(review_folder_)));
}
void SavedRunWindow::refresh_item(int row) {
    if(row<0 || row>=int(appearances_.size()) || row>=events_->count())return;
    const auto& value=appearances_[std::size_t(row)];
    events_->item(row)->setIcon(appearance_icon(thumbnail_image(value.thumbnail),value.first_detection,summary_->media.width,summary_->media.height,verdict(row)));
}
void SavedRunWindow::set_verdict(int row,std::optional<bool> correct,bool advance) {
    if(!store_ || !summary_ || summary_->configuration.kind!=frametrail::RunKind::appearances || row<0 || row>=int(appearances_.size()))return;
    const auto& value=appearances_[std::size_t(row)];
    if(correct)verdicts_[value.id]={*correct,value.first_detection.class_id};else verdicts_.erase(value.id);
    save_reviews();refresh_item(row);update_review_summary();update_controls();
    if(!advance)return;
    for(int next=row+1;next<int(appearances_.size());++next)if(!verdict(next)){events_->setCurrentRow(next);return;}
    if(more_->isEnabled()) { // Continue on the next page at its first unreviewed appearance.
        more_->click();
        for(int next=0;next<int(appearances_.size());++next)if(!verdict(next)){events_->setCurrentRow(next);return;}
    }
}
QString SavedRunWindow::review_summary() const {return review_progress_->text();}
void SavedRunWindow::update_review_summary() {
    const auto total=summary_ ? std::max<std::uint64_t>(summary_->appearance_count,verdicts_.size()) : 0;
    const auto reviewed=verdicts_.size();
    const auto correct=std::count_if(verdicts_.begin(),verdicts_.end(),[](const auto& entry){return entry.second.correct;});
    review_bar_->setRange(0,int(std::max<std::uint64_t>(1,total)));review_bar_->setValue(int(reviewed));
    if(!reviewed)review_progress_->setText(QStringLiteral("Not reviewed yet. Select an appearance and press C if it is right or X if it is wrong."));
    else review_progress_->setText(QStringLiteral("%1 %2 of %3  ·  %4 correct, %5 wrong  ·  %6% correct")
        .arg(reviewed==total ? QStringLiteral("All reviewed:") : QStringLiteral("Reviewed")).arg(reviewed).arg(total).arg(correct).arg(qint64(reviewed)-correct)
        .arg(qRound(100.*double(correct)/double(reviewed))));
    for(auto& [type,entry]:chips_by_type_) {
        int seen=0,right=0;
        for(const auto& [id,value]:verdicts_)if(value.class_id==type){++seen;right+=value.correct;}
        auto label=QStringLiteral("%1  %2").arg(QString::fromUtf8(frametrail::class_name(type).data())).arg(entry.first);
        if(seen)label+=QStringLiteral("  ·  %1%").arg(qRound(100.*right/seen));
        entry.second->setText(label);
        entry.second->setToolTip(seen ? QStringLiteral("%1 of %2 reviewed: %3 correct, %4 wrong. Click to jump to the first one.").arg(seen).arg(entry.first).arg(right).arg(seen-right)
                                      : QStringLiteral("Jump to the first appearance"));
    }
}
void SavedRunWindow::export_review_csv(const QString& output,bool replace) {
    if(!store_ || analysing() || awaiting_job_)throw std::logic_error("Wait for analysis to finish before exporting");
    protect_inputs(*summary_,output);
    const auto staging=scratch_.filePath(QUuid::createUuid().toString(QUuid::WithoutBraces)+QStringLiteral(".csv"));
    {
        QFile file(staging);if(!file.open(QIODevice::WriteOnly))throw std::runtime_error(file.errorString().toStdString());
        QByteArray out("\xef\xbb\xbfAppearance ID,Object,First (s),Last (s),Peak confidence,Verdict\r\n");
        std::uint64_t after=0;
        for(;;) {
            const auto rows=store_->appearances(after,100);if(rows.empty())break;
            for(const auto& value:rows) {
                after=value.id;const auto found=verdicts_.find(value.id);
                const auto seconds=[](std::optional<std::chrono::microseconds> time){return time ? QString::number(time->count()/1e6,'f',3) : QString{};};
                out+=QStringLiteral("%1,\"%2\",%3,%4,%5,%6\r\n").arg(value.id).arg(QString::fromUtf8(frametrail::class_name(value.first_detection.class_id).data()))
                    .arg(seconds(value.first_timestamp),seconds(value.last_timestamp)).arg(value.peak_confidence,0,'f',3)
                    .arg(found==verdicts_.end() ? QString{} : found->second.correct ? QStringLiteral("correct") : QStringLiteral("wrong")).toUtf8();
            }
        }
        if(file.write(out)!=out.size())throw std::runtime_error(file.errorString().toStdString());
    }
    try{atomic_copy(staging,output,replace);}catch(...){QFile::remove(staging);throw;}
    QFile::remove(staging);status_->setText(QStringLiteral("Review exported · %1").arg(QFileInfo(output).fileName()));
}
