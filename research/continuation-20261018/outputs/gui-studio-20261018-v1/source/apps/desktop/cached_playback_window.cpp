#include "cached_playback_window.hpp"
#include "preview_window.hpp"
#include "theme.hpp"
#include "studio_controls.hpp"
#include <QFrame>
#include <QCloseEvent>
#include <QFileInfo>
#include <QHBoxLayout>
#include <QLabel>
#include <QProgressBar>
#include <QPushButton>
#include <QVBoxLayout>
#include <algorithm>

namespace {
std::filesystem::path native(const QString& value) {
#ifdef _WIN32
    return std::filesystem::path(value.toStdWString());
#else
    const auto s=value.toUtf8();return std::filesystem::path(std::u8string(s.begin(),s.end()));
#endif
}
}
CachedPlaybackWindow::CachedPlaybackWindow(const QString& source,frametrail::DetectorOptions options):source_(native(source)) {
    setWindowTitle(QStringLiteral("FrameTrail — Smooth playback"));resize(1120,760);setMinimumSize(800,560);install_studio_style();setStyleSheet(frametrail_theme());
    auto* shell=new QWidget;shell->setObjectName(QStringLiteral("shell"));auto* layout=new QVBoxLayout(shell);layout->setContentsMargins(20,18,20,18);layout->setSpacing(14);
    auto* title=new QLabel(QStringLiteral("Smooth playback"));title->setObjectName(QStringLiteral("title"));auto* heading=new QHBoxLayout;heading->addWidget(title);heading->addStretch();studio_heading(heading);layout->addLayout(heading);
    auto* settings=new QLabel(QStringLiteral("%1 · %2 · Confidence %3% · Detection overlays")
        .arg(QFileInfo(source).fileName()).arg(QString::fromUtf8(frametrail::model_name(options.variant).data())).arg(qRound(options.confidence*100)));
    settings->setTextFormat(Qt::PlainText);settings->setWordWrap(true);settings->setProperty("role","muted");layout->addWidget(settings);
    canvas_=new FrameCanvas;canvas_->set_empty_text(QStringLiteral("Preparing detections…\nPlayback begins when the video is ready."));layout->addWidget(canvas_,1);
    progress_=new QProgressBar;progress_->setTextVisible(false);progress_->setRange(0,0);progress_->setMaximumHeight(7);layout->addWidget(progress_);
    status_=new QLabel(QStringLiteral("Preparing video…"));status_->setObjectName(QStringLiteral("cacheStatus"));status_->setTextFormat(Qt::PlainText);status_->setWordWrap(true);layout->addWidget(status_);
    auto* controls=new QHBoxLayout;play_=new QPushButton(QStringLiteral("Pause"));play_->setObjectName(QStringLiteral("cachePlay"));play_->setEnabled(false);controls->addWidget(play_);
    replay_=new QPushButton(QStringLiteral("Replay"));replay_->setObjectName(QStringLiteral("cacheReplay"));replay_->setEnabled(false);controls->addWidget(replay_);
    cancel_=new QPushButton(QStringLiteral("Cancel preparation"));cancel_->setObjectName(QStringLiteral("cacheCancel"));controls->addWidget(cancel_);controls->addStretch();auto* transport=new QFrame;transport->setObjectName(QStringLiteral("transportBar"));transport->setLayout(controls);controls->setContentsMargins(10,9,10,9);layout->addWidget(transport);studio_button(play_,"play");studio_button(replay_,"replay");setCentralWidget(shell);
    connect(play_,&QPushButton::clicked,this,[this]{
        const auto now=std::chrono::steady_clock::now();playing_=!playing_;
        if(playing_ && clock_started_)clock_+=now-paused_;else paused_=now;
        play_->setText(playing_?QStringLiteral("Pause"):QStringLiteral("Play"));
        if(!playing_)status_->setText(QStringLiteral("Paused · cached detections"));
    });
    connect(replay_,&QPushButton::clicked,this,[this]{decoder_.stop();playing_=false;ready_=false;restart_=true;next_.reset();overlays_.reset();play_->setEnabled(false);replay_->setEnabled(false);});
    connect(cancel_,&QPushButton::clicked,this,[this]{preparation_.cancel();cancel_->setEnabled(false);status_->setText(QStringLiteral("Stopping preparation…"));});
    connect(&timer_,&QTimer::timeout,this,[this]{tick();});timer_.setTimerType(Qt::PreciseTimer);timer_.start(5);
    try {
        if(!scratch_.isValid())throw std::runtime_error("Cannot create temporary playback cache");
        cache_=native(scratch_.filePath(QStringLiteral("overlays.ftcache")));
        preparation_.start(source_,std::move(options),cache_);
    }catch(const std::exception& e){fail(e);preparation_done_=true;}
}
const std::vector<frametrail::Detection>& CachedPlaybackWindow::detections() const{return canvas_->detections();}
void CachedPlaybackWindow::fail(const std::exception& error){
    decoder_.stop();playing_=false;ready_=false;restart_=false;next_.reset();overlays_.reset();
    status_->setText(QStringLiteral("Could not prepare/play: ")+QString::fromUtf8(error.what()));
    play_->setEnabled(false);replay_->setEnabled(false);cancel_->hide();progress_->hide();
}
void CachedPlaybackWindow::replay(){
    if(frametrail::file_stamp(source_)!=preparation_.progress().source_stamp)throw std::runtime_error("Video changed; close this window and prepare it again");
    overlays_=std::make_unique<frametrail::OverlayCacheReader>(cache_);
    decoder_.start(source_); // No detector or model is created during playback.
    next_.reset();clock_started_=false;ready_=true;playing_=true;restart_=false;
    displayed_sequence_.reset();displayed_timestamp_.reset();play_->setEnabled(true);play_->setText(QStringLiteral("Pause"));replay_->setEnabled(true);
    status_->setText(QStringLiteral("Ready · starting cached playback"));
}
void CachedPlaybackWindow::tick(){
    try {
        auto prep=preparation_.progress();auto decode=decoder_.snapshot();
        if(closing_){if(!prep.active && !decode.worker_active)close();return;}
        if(prep.active){
            status_->setText(QStringLiteral("Preparing · %1 frames · %2 · cancel anytime").arg(prep.frames).arg(QString::fromStdString(prep.execution.provider)));
            if(prep.duration && prep.duration->count()>0 && prep.timestamp){progress_->setRange(0,1000);progress_->setValue(int(std::clamp(double(prep.timestamp->count())/prep.duration->count()*1000.,0.,1000.)));}
            return;
        }
        if(!preparation_done_){
            preparation_done_=true;progress_->hide();cancel_->hide();
            if(prep.state!="completed"){
                status_->setText(prep.state=="cancelled"?QStringLiteral("Preparation cancelled · no playback cache used"):QStringLiteral("Preparation failed: ")+QString::fromStdString(prep.error));return;
            }
            replay();return;
        }
        if(restart_){if(!decode.worker_active)replay();return;}
        if(!ready_ || !playing_)return;
        if(decode.state==frametrail::PreviewState::failed)throw std::runtime_error(decode.error);
        if(!next_)next_=decoder_.try_pop();
        if(next_){
            const auto now=std::chrono::steady_clock::now();
            if(!clock_started_){first_timestamp_=next_->frame.timestamp.value_or(std::chrono::microseconds{});first_sequence_=next_->frame.sequence;clock_=now;paused_=now;clock_started_=true;}
            std::optional<frametrail::PreviewFrame> present;std::vector<frametrail::Detection> objects;
            for(int budget=0;next_ && budget<8;++budget){
                const auto timestamp=next_->frame.timestamp.value_or(first_timestamp_+std::chrono::microseconds((next_->frame.sequence-first_sequence_)*33333));
                if(now-clock_<timestamp-first_timestamp_)break;
                objects=overlays_->read(next_->frame);present=std::move(next_);next_.reset();next_=decoder_.try_pop();
            }
            if(present){
                const auto& f=present->frame;QImage image(f.pixels.data(),f.width,f.height,f.stride,QImage::Format_RGB888);canvas_->set_image(image.copy(),std::move(objects));
                displayed_sequence_=f.sequence;displayed_timestamp_=f.timestamp;
                status_->setText(QStringLiteral("Playing · cached detections · frame %1 / %2").arg(f.sequence+1).arg(prep.frames));
            }
        }else if(!decode.worker_active && decode.queued_frames==0){
            overlays_->verify_end();if(frametrail::file_stamp(source_)!=prep.source_stamp)throw std::runtime_error("Video changed during playback");
            playing_=false;play_->setEnabled(false);play_->setText(QStringLiteral("Play"));status_->setText(QStringLiteral("Finished · Replay reuses prepared detections"));
        }
    }catch(const std::exception& e){fail(e);}
}
void CachedPlaybackWindow::closeEvent(QCloseEvent* event){
    if(preparation_.progress().active || decoder_.snapshot().worker_active){closing_=true;preparation_.cancel();decoder_.stop();event->ignore();status_->setText(QStringLiteral("Closing…"));}
    else {decoder_.release();overlays_.reset();event->accept();}
}
