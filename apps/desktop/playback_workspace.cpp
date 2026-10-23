#include "playback_workspace.hpp"
#include "cached_playback_window.hpp"
#include "preview_window.hpp"
#include "studio_controls.hpp"
#include <QFileDialog>
#include <QFileInfo>
#include <QLabel>
#include <QPushButton>
#include <QVBoxLayout>
#include <QHBoxLayout>

PlaybackWorkspace::PlaybackWorkspace(QString source,frametrail::DetectorOptions options,QWidget* parent)
    :QWidget(parent),source_(std::move(source)),options_(std::move(options)) {
    setObjectName(QStringLiteral("playbackWorkspace"));
    auto* layout=new QVBoxLayout(this);layout->setContentsMargins(0,0,0,0);layout->setSpacing(12);
    auto* heading=new QHBoxLayout;auto* title=new QLabel(QStringLiteral("Smooth playback"));title->setObjectName(QStringLiteral("title"));heading->addWidget(title);heading->addStretch();
    choose_=new QPushButton(QStringLiteral("Choose video…"));choose_->setObjectName(QStringLiteral("choosePlaybackVideo"));studio_button(choose_,"open");heading->addWidget(choose_);layout->addLayout(heading);
    auto* actions=new QHBoxLayout;prepare_=new QPushButton(QStringLiteral("Prepare playback"));prepare_->setObjectName(QStringLiteral("preparePlayback"));prepare_->setProperty("role","primary");studio_button(prepare_,"smooth");actions->addWidget(prepare_);
    use_preview_=new QPushButton(QStringLiteral("Use preview video"));use_preview_->setObjectName(QStringLiteral("usePreviewVideo"));actions->addWidget(use_preview_);actions->addStretch();layout->addLayout(actions);
    source_label_=new QLabel;source_label_->setObjectName(QStringLiteral("playbackSource"));source_label_->setTextFormat(Qt::PlainText);source_label_->setWordWrap(true);layout->addWidget(source_label_);
    settings_label_=new QLabel;settings_label_->setProperty("role","muted");settings_label_->setTextFormat(Qt::PlainText);settings_label_->setWordWrap(true);layout->addWidget(settings_label_);
    content_=new QVBoxLayout;content_->setContentsMargins(0,0,0,0);layout->addLayout(content_,1);
    empty_=new FrameCanvas;empty_->setObjectName(QStringLiteral("playbackEmpty"));empty_->set_empty_text(QStringLiteral("Prepare once. Play smoothly.\nChoose a video, then prepare its detections.\nSwitch sections while preparation continues."));content_->addWidget(empty_,1);
    connect(choose_,&QPushButton::clicked,this,[this]{const auto path=QFileDialog::getOpenFileName(this,QStringLiteral("Choose playback video"),{},QStringLiteral("Video (*.mp4 *.mkv *.avi *.mov *.webm);;All files (*)"));if(!path.isEmpty())select_video(path,options_);});
    connect(use_preview_,&QPushButton::clicked,this,[this]{if(preview_selection){auto [source,options]=preview_selection();if(source.isEmpty()){source_label_->setText(QStringLiteral("Open a video in Preview first, or choose one here."));return;}select_video(std::move(source),std::move(options));}});
    connect(prepare_,&QPushButton::clicked,this,[this]{prepare();});
    connect(&timer_,&QTimer::timeout,this,[this]{tick();});timer_.start(40);refresh();
}
bool PlaybackWorkspace::preparing() const{return cache_ && cache_->preparing();}
void PlaybackWorkspace::select_video(QString source,frametrail::DetectorOptions options){
    if(preparing() || replacing_ || resetting_ || closing_)return;
    if(cache_){cache_->hide();cache_->request_shutdown();resetting_=true;empty_->show();}
    source_=std::move(source);options_=std::move(options);refresh();
}
void PlaybackWorkspace::suspend_playback(){if(cache_)cache_->suspend_playback();}
void PlaybackWorkspace::request_shutdown(){closing_=true;replacing_=false;if(cache_)cache_->request_shutdown();refresh();}
bool PlaybackWorkspace::shutdown_complete() const{return !cache_ || cache_->shutdown_complete();}
void PlaybackWorkspace::prepare(){
    if(source_.isEmpty() || preparing() || replacing_ || resetting_ || closing_)return;
    replacing_=true;if(cache_)cache_->request_shutdown();refresh();tick();
}
void PlaybackWorkspace::tick(){
    if(resetting_ && shutdown_complete()){content_->removeWidget(cache_);delete cache_;cache_=nullptr;resetting_=false;}
    if(replacing_ && shutdown_complete()){
        if(cache_){content_->removeWidget(cache_);delete cache_;cache_=nullptr;}
        empty_->hide();cache_=new CachedPlaybackWindow(source_,options_);cache_->setParent(this,Qt::Widget);cache_->setMinimumSize(0,0);
        cache_->centralWidget()->layout()->setContentsMargins(0,0,0,0);
        // The shared workspace supplies the heading/settings; keep only the
        // actual cache canvas, feedback and transport in this embedded view.
        auto* nested=cache_->centralWidget()->layout();for(int i=0;i<2;++i){auto* item=nested->itemAt(i);if(item->widget())item->widget()->hide();else if(item->layout())for(int j=0;j<item->layout()->count();++j)if(auto* widget=item->layout()->itemAt(j)->widget())widget->hide();}
        content_->addWidget(cache_,1);cache_->show();replacing_=false;
    }
    refresh();
}
void PlaybackWorkspace::refresh(){
    const bool busy=preparing() || replacing_ || resetting_ || closing_;
    const bool preview_available=preview_selection && !preview_selection().first.isEmpty();
    choose_->setEnabled(!busy);use_preview_->setEnabled(!busy && preview_available);prepare_->setEnabled(!busy && !source_.isEmpty());
    prepare_->setText(cache_ ? QStringLiteral("Prepare again") : QStringLiteral("Prepare playback"));
    source_label_->setText(source_.isEmpty() ? QStringLiteral("No video selected") : QFileInfo(source_).fileName());source_label_->setToolTip(source_);
    settings_label_->setText(QStringLiteral("%1 · %2% confidence · %3\nUse preview video also copies its model and device settings.")
        .arg(QString::fromUtf8(frametrail::model_name(options_.variant).data())).arg(qRound(options_.confidence*100)).arg(options_.backend==frametrail::DetectorBackend::cpu ? QStringLiteral("CPU") : QStringLiteral("GPU / automatic")));
}
