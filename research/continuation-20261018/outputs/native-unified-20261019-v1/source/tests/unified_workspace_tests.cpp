#include "preview_window.hpp"
#include "saved_run_window.hpp"
#include "playback_workspace.hpp"
#include "cached_playback_window.hpp"
#include "live_window.hpp"
#include <QApplication>
#include <QFontDatabase>
#include <QJsonDocument>
#include <QJsonObject>
#include <QLabel>
#include <QListWidget>
#include <QMessageBox>
#include <QPointer>
#include <QPushButton>
#include <QComboBox>
#include <QStackedWidget>
#include <QtTest/QTest>
#include <fstream>
#include <iostream>

namespace {
void require(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
template<class F>void wait(F fn){for(int i=0;i<24000;++i){if(fn())return;QTest::qWait(5);}throw std::runtime_error("Unified workspace timed out");}
QString text(const std::filesystem::path& p){return QString::fromStdWString(p.wstring());}
void one_window(){int count=0;for(auto* w:QApplication::topLevelWidgets())if(w->isVisible() && dynamic_cast<QMainWindow*>(w))++count;require(count==1,"A workspace section opened another top-level window");}
void capture(QWidget& window,const std::filesystem::path& file){require(window.grab().save(text(file)),"Unified capture failed");}
}
int main(int argc,char** argv){
    QApplication app(argc,argv);QFontDatabase::addApplicationFont(qEnvironmentVariable("WINDIR")+QStringLiteral("/Fonts/segoeui.ttf"));app.setFont(QFont(QStringLiteral("Segoe UI"),10));
    if(argc!=5)return 2;
    const std::filesystem::path model=argv[1],long_video=argv[2],short_video=argv[3],out=argv[4];std::filesystem::create_directories(out);QJsonObject receipt;
    try{
        PreviewWindow window(text(model));window.show();auto* stack=window.findChild<QStackedWidget*>(QStringLiteral("workspacePages"));require(stack,"Workspace stack missing");
        const auto click=[&](const char* name){auto* button=window.findChild<QPushButton*>(QString::fromLatin1(name));require(button && button->isEnabled(),"Navigation is unavailable");button->click();QTest::qWait(30);one_window();};
        capture(window,out/"01-preview.png");
        click("savedAnalysis");auto* analysis=window.analysis_workspace();require(analysis && !analysis->isWindow() && stack->currentWidget()==analysis,"Analysis was not embedded");capture(window,out/"02-analysis-empty.png");
        click("smoothPlayback");auto* playback=window.playback_workspace();require(playback && !playback->isWindow() && stack->currentWidget()==playback,"Playback was not embedded");capture(window,out/"03-playback-empty.png");
        click("liveCamera");auto* camera=window.camera_workspace();require(camera && !camera->isWindow() && !camera->active(),"Opening camera section acquired hardware");capture(window,out/"04-camera-idle.png");
        click("previewWorkspace");window.open_file(text(long_video));wait([&]{return window.displayed_sequence().has_value();});
        click("savedAnalysis");require(window.analysis_workspace()==analysis,"Navigation duplicated analysis");analysis->select_video(text(long_video));analysis->analyse_video();
        wait([&]{return !static_cast<FrameCanvas*>(analysis->findChild<QWidget*>(QStringLiteral("frameCanvas")))->image().isNull();});
        click("previewWorkspace");require(analysis->analysing(),"Leaving analysis cancelled the job");require(window.findChild<QLabel*>(QStringLiteral("workspaceActivity"))->text().contains(QStringLiteral("Analysis running")),"Hidden analysis has no activity indication");capture(window,out/"05-background-analysis.png");
        click("savedAnalysis");analysis->findChild<QPushButton*>(QStringLiteral("cancelAnalysis"))->click();wait([&]{return !analysis->analysing() && analysis->findChild<QPushButton*>(QStringLiteral("saveRun"))->isEnabled();});
        const auto saved=out/"saved-partial.frametrail";analysis->save_analysis(text(saved));analysis->export_analysis_csv(text(out/"saved-partial.csv"));
        const auto appearances=analysis->findChild<QListWidget*>(QStringLiteral("savedEvents"))->count();require(appearances>0,"Test fixture yielded no saved appearances");
        wait([&]{return analysis->displayed_timestamp().has_value();});capture(window,out/"06-analysis-results.png");
        click("smoothPlayback");playback->select_video(text(short_video),{model,.35f,.45f,frametrail::DetectorModel::nano,frametrail::DetectorBackend::cpu});playback->findChild<QPushButton*>(QStringLiteral("preparePlayback"))->click();
        wait([&]{return playback->cache() && playback->cache()->prepared();});auto* cache=playback->cache();require(!cache->isWindow(),"Cache escaped into another window");wait([&]{return cache->displayed_sequence().has_value();});
        click("previewWorkspace");require(!cache->playing(),"Cached playback continued hidden");const auto paused=cache->displayed_sequence();QTest::qWait(100);require(cache->displayed_sequence()==paused,"Hidden playback advanced");
        QTest::keyClick(&window,Qt::Key_3,Qt::ControlModifier);QTest::qWait(30);require(stack->currentWidget()==playback && playback->cache()==cache,"Keyboard navigation lost prepared cache");one_window();capture(window,out/"07-playback-ready.png");
        window.resize(1100,720);QTest::qWait(30);capture(window,out/"08-compact-playback.png");window.resize(1400,900);
        QPointer<CachedPlaybackWindow> previous_cache=cache;
        playback->select_video(text(short_video),{model,.35f,.45f,frametrail::DetectorModel::nano,frametrail::DetectorBackend::cpu});
        wait([&]{return previous_cache.isNull();});require(!playback->cache(),"Changing source kept stale overlays attached");
        playback->findChild<QPushButton*>(QStringLiteral("preparePlayback"))->click();wait([&]{return playback->cache() && playback->cache()->prepared();});cache=playback->cache();
        click("savedAnalysis");require(analysis->findChild<QListWidget*>(QStringLiteral("savedEvents"))->count()==appearances,"Switching sections lost results");
        analysis->open_run(text(saved));wait([&]{return analysis->displayed_timestamp().has_value();});
        analysis->analyse_video();wait([&]{return !static_cast<FrameCanvas*>(analysis->findChild<QWidget*>(QStringLiteral("frameCanvas")))->image().isNull();});
        bool prompt_seen=false;QTimer answer;answer.setInterval(5);QObject::connect(&answer,&QTimer::timeout,[&]{if(auto* dialog=qobject_cast<QMessageBox*>(QApplication::activeModalWidget())){prompt_seen=true;answer.stop();dialog->button(QMessageBox::Cancel)->click();}});answer.start();
        window.close();wait([&]{return prompt_seen;});QTest::qWait(30);require(window.isVisible() && !analysis->analysing() && analysis->findChild<QPushButton*>(QStringLiteral("saveRun"))->isEnabled(),"Cancelling quit lost the partial analysis");
        click("previewWorkspace");click("savedAnalysis");capture(window,out/"09-quit-cancel-preserved.png");
        analysis->save_analysis(text(out/"quit-preserved.frametrail"));analysis->analyse_video();wait([&]{return !static_cast<FrameCanvas*>(analysis->findChild<QWidget*>(QStringLiteral("frameCanvas")))->image().isNull();});
        bool discard_seen=false;QTimer discard;discard.setInterval(5);QObject::connect(&discard,&QTimer::timeout,[&]{if(auto* dialog=qobject_cast<QMessageBox*>(QApplication::activeModalWidget())){discard_seen=true;discard.stop();dialog->button(QMessageBox::Discard)->click();}});discard.start();
        window.close();wait([&]{return !window.isVisible();});require(discard_seen,"Quit omitted the unsaved-result decision");
        require(!playback->preparing() && playback->shutdown_complete() && !camera->active(),"Main window closed before workers stopped");
        PreviewWindow preparing(text(model));preparing.show();
        preparing.findChild<QPushButton*>(QStringLiteral("liveCamera"))->click();require(!preparing.camera_workspace()->active(),"Camera-first navigation started capture");
        preparing.findChild<QPushButton*>(QStringLiteral("smoothPlayback"))->click();auto* pending=preparing.playback_workspace();pending->select_video(text(long_video),{model,.35f,.45f,frametrail::DetectorModel::nano,frametrail::DetectorBackend::cpu});pending->findChild<QPushButton*>(QStringLiteral("preparePlayback"))->click();
        wait([&]{return pending->cache() && pending->cache()->prepared_frames()>1;});
        preparing.findChild<QPushButton*>(QStringLiteral("previewWorkspace"))->click();QTest::qWait(30);one_window();
        require(pending->preparing() && preparing.findChild<QLabel*>(QStringLiteral("workspaceActivity"))->text().contains(QStringLiteral("Playback preparing")),"Preparation did not continue with visible activity");capture(preparing,out/"10-background-preparation.png");
        preparing.close();wait([&]{return !preparing.isVisible();});require(pending->shutdown_complete() && !pending->cache()->prepared(),"Quitting promoted or abandoned incomplete preparation");
        receipt={{"status","passed"},{"single_top_level_workspace",true},{"analysis_state_preserved",true},{"background_activity_visible",true},{"cache_retained_across_navigation",true},{"source_replacement_releases_old_cache",true},{"background_preparation_and_quit",true},{"lazy_section_order",true},{"hidden_playback_paused",true},{"camera_not_acquired_on_navigation",true},{"keyboard_navigation",true},{"save_csv_reopen",true},{"active_analysis_quit_cancel_preserved",true},{"active_analysis_quit_discard_shutdown",true},{"prepared_frames",double(cache->prepared_frames())},{"saved_appearances",appearances}};
    }catch(const std::exception& e){receipt={{"status","failed"},{"error",QString::fromUtf8(e.what())}};}
    std::ofstream result(out/"result.json");result<<QJsonDocument(receipt).toJson().toStdString();std::cout<<QJsonDocument(receipt).toJson().toStdString();return receipt["status"]=="passed"?0:1;
}
