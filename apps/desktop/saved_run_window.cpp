#include "saved_run_window.hpp"
#include "preview_window.hpp"
#include "theme.hpp"
#include <QCloseEvent>
#include <QFileDialog>
#include <QFileInfo>
#include <QHBoxLayout>
#include <QLabel>
#include <QListWidget>
#include <QMouseEvent>
#include <QPainter>
#include <QPushButton>
#include <QSignalBlocker>
#include <QSplitter>
#include <QVBoxLayout>
#include <algorithm>
#include <cmath>

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
    if(!time)return QStringLiteral("Unknown time");
    const auto ms=std::max<std::int64_t>(0,time->count()/1000);
    return QStringLiteral("%1:%2:%3.%4").arg(ms/3600000,2,10,QChar('0')).arg((ms/60000)%60,2,10,QChar('0'))
        .arg((ms/1000)%60,2,10,QChar('0')).arg(ms%1000,3,10,QChar('0'));
}
QImage thumbnail_image(const frametrail::StoredEvent& value) {
    return QImage::fromData(value.thumbnail.data(),int(value.thumbnail.size()),"PPM");
}
}

class EventTimeline : public QWidget {
public:
    explicit EventTimeline(QWidget* parent=nullptr):QWidget(parent) {setMinimumHeight(45);setObjectName(QStringLiteral("eventTimeline"));}
    std::function<void(int)> selected;
    void set_events(const std::vector<frametrail::StoredEvent>& events,std::int64_t duration) {
        times_.clear();duration_=std::max<std::int64_t>(1,duration);
        for(const auto& value:events)times_.push_back(value.event.timestamp);
        setToolTip(QStringLiteral("Click a marker to review an event on this page. Events with unknown time remain in the list."));update();
    }
protected:
    void paintEvent(QPaintEvent*) override {
        QPainter p(this);p.setRenderHint(QPainter::Antialiasing);
        p.setPen(QPen(QColor("#516579"),2));p.drawLine(12,16,width()-12,16);
        p.setPen(QPen(QColor("#ffce63"),3));
        for(const auto& t:times_)if(t) {const auto x=position(*t);p.drawLine(x,8,x,24);}
        p.setPen(QColor("#aabacb"));p.drawText(12,42,QStringLiteral("0:00"));
        p.drawText(width()-135,42,time_text(std::chrono::microseconds(duration_)));
    }
    void mousePressEvent(QMouseEvent* event) override {
        if(event->button()!=Qt::LeftButton)return;
        int nearest=-1;double distance=12;
        for(std::size_t i=0;i<times_.size();++i)if(times_[i]) {
            const double gap=std::abs(position(*times_[i])-event->position().x());
            if(gap<=distance) {nearest=int(i);distance=gap;}
        }
        if(nearest>=0 && selected)selected(nearest);
    }
private:
    int position(std::chrono::microseconds time) const {
        return 12+int(std::clamp(double(time.count())/duration_,0.0,1.0)*std::max(0,width()-24));
    }
    std::vector<std::optional<std::chrono::microseconds>> times_;
    std::int64_t duration_{1};
};

SavedRunWindow::SavedRunWindow(std::optional<frametrail::RunConfiguration> configuration):configuration_(std::move(configuration)) {
    setWindowTitle(QStringLiteral("FrameTrail — Saved analysis"));resize(1200,820);
    setStyleSheet(frametrail_theme());
    auto* shell=new QWidget; shell->setObjectName(QStringLiteral("shell"));auto* layout=new QVBoxLayout(shell);layout->setContentsMargins(20,18,20,18);
    auto* title=new QLabel(QStringLiteral("Saved analysis & event review"));title->setObjectName(QStringLiteral("title"));layout->addWidget(title);
    auto* actions=new QHBoxLayout;
    analyse_=new QPushButton(QStringLiteral("Analyse entire recording…"));analyse_->setObjectName(QStringLiteral("saveAnalysis")); analyse_->setProperty("role","primary");
    analyse_->setEnabled(configuration_.has_value());
    analyse_->setToolTip(QStringLiteral("Analyse from the start with the settings captured when this window opened. Preview edits do not change this run."));
    open_=new QPushButton(QStringLiteral("Open saved run…"));open_->setObjectName(QStringLiteral("openRun"));
    cancel_=new QPushButton(QStringLiteral("Cancel analysis"));cancel_->setObjectName(QStringLiteral("cancelAnalysis"));cancel_->setEnabled(false);
    export_=new QPushButton(QStringLiteral("Export events CSV…"));export_->setObjectName(QStringLiteral("exportRun"));export_->setEnabled(false);
    for(auto* button:{analyse_,open_,cancel_,export_})actions->addWidget(button);actions->addStretch();layout->addLayout(actions);
    source_=new QLabel(configuration_ ? text(configuration_->source) : QStringLiteral("Open a saved run, or select media and enable Detect objects + Track & count in the player."));
    source_->setTextFormat(Qt::PlainText);source_->setWordWrap(true);layout->addWidget(source_);
    settings_=new QLabel;settings_->setWordWrap(true);settings_->setTextFormat(Qt::PlainText);layout->addWidget(settings_);
    if(configuration_) {
        const auto& c=*configuration_;const auto& line=*c.tracking.line;
        settings_->setText(QStringLiteral("Captured settings: CPU %1 • confidence %2 • %3 tracked classes • line (%4,%5) → (%6,%7) • %8")
            .arg(QString::fromUtf8(frametrail::model_name(c.detector.variant).data())).arg(c.detector.confidence,0,'f',2).arg(c.tracking.classes.size()).arg(line.a.x).arg(line.a.y).arg(line.b.x).arg(line.b.y)
            .arg(QString::fromUtf8(frametrail::direction_name(line.direction).data())));
    }
    status_=new QLabel(QStringLiteral("Ready. A saved run is separate from the player’s temporary counters."));status_->setObjectName(QStringLiteral("analysisStatus"));
    status_->setTextFormat(Qt::PlainText);status_->setWordWrap(true);layout->addWidget(status_);
    auto* split=new QSplitter;auto* left=new QWidget;auto* left_layout=new QVBoxLayout(left);
    left_layout->addWidget(new QLabel(QStringLiteral("Crossing events — click to review")));
    events_=new QListWidget;events_->setObjectName(QStringLiteral("savedEvents"));events_->setIconSize(QSize(160,90));left_layout->addWidget(events_,1);
    auto* paging=new QHBoxLayout;previous_=new QPushButton(QStringLiteral("Previous 100"));more_=new QPushButton(QStringLiteral("Next 100"));
    previous_->setEnabled(false);more_->setEnabled(false);paging->addWidget(previous_);paging->addWidget(more_);left_layout->addLayout(paging);
    split->addWidget(left);canvas_=new FrameCanvas;split->addWidget(canvas_);split->setStretchFactor(0,0);split->setStretchFactor(1,1);split->setSizes({340,800});layout->addWidget(split,1);
    timeline_=new EventTimeline;layout->addWidget(timeline_);
    auto* playback=new QHBoxLayout;play_=new QPushButton(QStringLiteral("Play from event"));play_->setObjectName(QStringLiteral("reviewPlay"));play_->setEnabled(false);playback->addWidget(play_);
    auto* back=new QPushButton(QStringLiteral("Back to selected event"));playback->addWidget(back);
    review_status_=new QLabel(QStringLiteral("Review uses saved results and does not run detection."));review_status_->setObjectName(QStringLiteral("reviewStatus"));
    review_status_->setTextFormat(Qt::PlainText);review_status_->setWordWrap(true);playback->addWidget(review_status_,1);layout->addLayout(playback);setCentralWidget(shell);
    connect(analyse_,&QPushButton::clicked,this,[this] {
        if(!configuration_)return;
        const auto path=QFileDialog::getSaveFileName(this,QStringLiteral("Create a new saved run"),QFileInfo(text(configuration_->source)).completeBaseName()+QStringLiteral(".frametrail"),
            QStringLiteral("FrameTrail run (*.frametrail)"),nullptr,QFileDialog::DontConfirmOverwrite);
        if(!path.isEmpty()) {try {start_analysis(path,*configuration_);}catch(const std::exception& e){show_error(e);}}
    });
    connect(open_,&QPushButton::clicked,this,[this] {
        const auto path=QFileDialog::getOpenFileName(this,QStringLiteral("Open saved run"),{},QStringLiteral("FrameTrail run (*.frametrail);;All files (*)"));
        if(!path.isEmpty()){try{open_run(path);}catch(const std::exception& e){show_error(e);}}
    });
    connect(cancel_,&QPushButton::clicked,this,[this]{job_.cancel();status_->setText(QStringLiteral("Cancelling — preserving committed results…"));});
    connect(export_,&QPushButton::clicked,this,[this] {
        const auto path=QFileDialog::getSaveFileName(this,QStringLiteral("Export to a new CSV file"),{},QStringLiteral("CSV (*.csv)"),nullptr,QFileDialog::DontConfirmOverwrite);
        if(!path.isEmpty() && store_){try{store_->export_csv(native(path));status_->setText(QStringLiteral("Events exported to ")+path);}catch(const std::exception& e){show_error(e);}}
    });
    connect(events_,&QListWidget::currentRowChanged,this,[this](int row){review_event(row);});
    timeline_->selected=[this](int row){QSignalBlocker block(events_);events_->setCurrentRow(row);review_event(row);};
    connect(previous_,&QPushButton::clicked,this,[this] {
        if(cursors_.size()>1){cursors_.pop_back();try{load_page(cursors_.back());}catch(const std::exception& e){show_error(e);}}
    });
    connect(more_,&QPushButton::clicked,this,[this] {
        if(!page_.empty()){cursors_.push_back(page_.back().event.id);try{load_page(cursors_.back());}catch(const std::exception& e){show_error(e);}}
    });
    connect(play_,&QPushButton::clicked,this,[this]{toggle_playback();});
    connect(back,&QPushButton::clicked,this,[this]{review_event(events_->currentRow());});
    connect(&timer_,&QTimer::timeout,this,[this]{tick();});timer_.setTimerType(Qt::PreciseTimer);timer_.start(5);
}
void SavedRunWindow::show_error(const std::exception& error) {status_->setText(QStringLiteral("Could not complete: ")+QString::fromUtf8(error.what()));}
void SavedRunWindow::start_analysis(const QString& database,frametrail::RunConfiguration configuration) {
    if(analysing())throw std::logic_error("An analysis is already running");
    if(std::filesystem::exists(native(database)))throw std::runtime_error("Saved run already exists; choose a new filename");
    review_.stop();pending_review_.reset();next_.reset();playing_=false;play_->setEnabled(false);
    store_.reset();summary_.reset();page_.clear();events_->clear();canvas_->set_image({});timeline_->set_events({},1);
    database_=database;job_.start(native(database),std::move(configuration));awaiting_job_=true;
    analyse_->setEnabled(false);open_->setEnabled(false);cancel_->setEnabled(true);export_->setEnabled(false);
    previous_->setEnabled(false);more_->setEnabled(false);status_->setText(QStringLiteral("Starting full-file analysis…"));
}
void SavedRunWindow::open_run(const QString& database) {
    if(analysing())throw std::logic_error("Cancel the active analysis before opening another run");
    frametrail::RunStore candidate(native(database));auto info=candidate.summary();
    review_.stop();pending_review_.reset();next_.reset();playing_=false;awaiting_frame_=false;play_->setEnabled(false);displayed_timestamp_.reset();canvas_->set_image({});
    store_.emplace(std::move(candidate));summary_=std::move(info);database_=database;cursors_={0};
    const auto& s=*summary_;source_->setText(text(s.configuration.source));
    QStringList classes;for(auto id:s.configuration.tracking.classes)classes<<QString::fromUtf8(frametrail::class_name(id).data());
    const auto& line=*s.configuration.tracking.line;
    settings_->setText(QString::fromUtf8(frametrail::model_name(s.configuration.detector.variant).data())+QStringLiteral(" • ")+QStringLiteral("Saved %1 • confidence %2 • %3 • line (%4,%5) → (%6,%7) • %8")
        .arg(QString::fromStdString(s.created)).arg(s.configuration.detector.confidence,0,'f',2).arg(classes.join(QStringLiteral(", ")))
        .arg(line.a.x).arg(line.a.y).arg(line.b.x).arg(line.b.y).arg(QString::fromUtf8(frametrail::direction_name(line.direction).data())));
    const auto state=s.status=="running" ? QStringLiteral("Interrupted / unfinished") : QString::fromStdString(s.status);
    status_->setText(QStringLiteral("%1 • %2 frames analysed • %3 events • − → + %4  |  + → − %5%6")
        .arg(state).arg(s.processed_frames).arg(s.event_count).arg(s.forward).arg(s.reverse)
        .arg(s.error.empty() ? QString{} : QStringLiteral(" • ")+QString::fromStdString(s.error)));
    review_status_->setText(store_->source_available() ? QStringLiteral("Select an event to review its source frame. Playback cannot change saved counts.") :
        QStringLiteral("Source is missing or changed. Thumbnails and CSV remain available; restore the original recording to review."));
    export_->setEnabled(true);load_page(0);
}
void SavedRunWindow::load_page(std::uint64_t after) {
    if(!store_)return;
    auto page=store_->events(after);QSignalBlocker block(events_);events_->clear();page_=std::move(page);
    for(const auto& value:page_) {
        const auto& e=value.event;
        auto* item=new QListWidgetItem(QIcon(QPixmap::fromImage(thumbnail_image(value))),
            QStringLiteral("%1\n%2 • track #%3 • event #%4\n%5 • frame %6")
                .arg(time_text(e.timestamp)).arg(QString::fromUtf8(frametrail::class_name(e.class_id).data())).arg(e.track_id).arg(e.id)
                .arg(e.direction==frametrail::CrossingDirection::negative_to_positive ? QStringLiteral("− → +") : QStringLiteral("+ → −")).arg(e.sequence),events_);
        item->setSizeHint(QSize(310,110));
    }
    const auto end=summary_->media.duration.value_or(summary_->last_timestamp.value_or(std::chrono::microseconds{1}));
    timeline_->set_events(page_,end.count());previous_->setEnabled(cursors_.size()>1);
    more_->setEnabled(!page_.empty() && !store_->events(page_.back().event.id,1).empty());
    if(page_.empty())review_status_->setText(QStringLiteral("No crossing events saved. A completed run with zero events is valid."));
}
void SavedRunWindow::review_event(int row) {
    if(!store_ || row<0 || row>=int(page_.size()))return;
    review_.stop();next_.reset();pending_review_.reset();playing_=false;awaiting_frame_=false;clock_started_=false;
    displayed_timestamp_.reset();play_->setEnabled(false);play_->setText(QStringLiteral("Play from event"));
    const auto& value=page_[row];canvas_->set_image(thumbnail_image(value),{},{},summary_->configuration.tracking.line);
    if(!store_->source_available()) {
        review_status_->setText(QStringLiteral("Source is missing or changed. Showing the saved thumbnail; restore the original file to seek."));return;
    }
    pending_review_=frametrail::ReviewPosition{summary_->timestamp_seekable ? value.event.timestamp : std::nullopt,value.event.sequence};
    review_status_->setText(QStringLiteral("Seeking to event #%1 at %2…").arg(value.event.id).arg(time_text(value.event.timestamp)));
}
void SavedRunWindow::toggle_playback() {
    if(awaiting_frame_ || pending_review_ || !displayed_timestamp_ || !summary_)return;
    if(playing_) {playing_=false;paused_=std::chrono::steady_clock::now();play_->setText(QStringLiteral("Play"));}
    else {clock_+=std::chrono::steady_clock::now()-paused_;playing_=true;play_->setText(QStringLiteral("Pause"));}
}
void SavedRunWindow::tick() {
    const auto progress=job_.progress();
    if(closing_) {if(!progress.active && !review_.snapshot().worker_active)close();return;}
    if(awaiting_job_) {
        if(progress.active) {
            status_->setText(QStringLiteral("%1 • %2 frames • %3 events • %4 / %5")
                .arg(QString::fromStdString(progress.status)).arg(progress.frames).arg(progress.events).arg(time_text(progress.timestamp)).arg(time_text(progress.duration)));
        }else {
            awaiting_job_=false;analyse_->setEnabled(configuration_.has_value());open_->setEnabled(true);cancel_->setEnabled(false);
            try{open_run(database_);}catch(const std::exception& e){show_error(e);if(!progress.error.empty())status_->setText(QString::fromStdString(progress.error));}
        }
    }
    const auto state=review_.snapshot();
    if(pending_review_) {
        if(!state.worker_active) {
            try {
                review_.start(summary_->configuration.source,{},{},pending_review_);
                pending_review_.reset();awaiting_frame_=true;
            }catch(const std::exception& e){pending_review_.reset();review_status_->setText(QString::fromUtf8(e.what()));}
        }return;
    }
    if(state.state==frametrail::PreviewState::failed) {
        awaiting_frame_=false;playing_=false;play_->setEnabled(false);next_.reset();
        review_status_->setText(QStringLiteral("Could not review: ")+QString::fromStdString(state.error));return;
    }
    if(!awaiting_frame_ && !playing_)return;
    if(!next_)next_=review_.try_pop();
    if(next_) {
        const auto now=std::chrono::steady_clock::now();
        if(!clock_started_) {
            first_timestamp_=next_->frame.timestamp.value_or(std::chrono::microseconds{});first_sequence_=next_->frame.sequence;
            clock_=now;paused_=now;clock_started_=true;
        }
        // Present the latest due frame, retaining a future frame. A delayed UI
        // tick must not replay a backlog one frame at a time. Saved data is read-only.
        std::optional<frametrail::PreviewFrame> present;
        std::chrono::microseconds time{};
        for(int budget=0;next_ && budget<4;++budget) {
            const auto candidate_time=next_->frame.timestamp.value_or(first_timestamp_+std::chrono::microseconds((next_->frame.sequence-first_sequence_)*33333));
            if(!awaiting_frame_ && now-clock_<candidate_time-first_timestamp_)break;
            time=candidate_time;present=std::move(next_);next_.reset();
            if(awaiting_frame_)break;
            next_=review_.try_pop();
        }
        if(present) {
            const auto& f=present->frame;QImage pixels(f.pixels.data(),f.width,f.height,f.stride,QImage::Format_RGB888);
            canvas_->set_image(pixels.copy(),{},{},summary_->configuration.tracking.line);displayed_timestamp_=time;
            review_status_->setText(QStringLiteral("Review • %1 • saved counts unchanged • no inference").arg(time_text(f.timestamp)));
            if(awaiting_frame_) {awaiting_frame_=false;paused_=now;play_->setEnabled(true);}
        }
    }else if(!state.worker_active) {
        playing_=false;awaiting_frame_=false;play_->setEnabled(false);play_->setText(QStringLiteral("Finished"));
    }
}
void SavedRunWindow::closeEvent(QCloseEvent* event) {
    if(job_.progress().active || review_.snapshot().worker_active) {
        closing_=true;job_.cancel();review_.stop();event->ignore();status_->setText(QStringLiteral("Closing and preserving partial results…"));
    }else event->accept();
}
