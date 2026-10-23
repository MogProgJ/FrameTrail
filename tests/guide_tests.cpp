#include "preview_window.hpp"
#include "saved_run_window.hpp"
#include "model_selection.hpp"
#include <QApplication>
#include <QComboBox>
#include <QFile>
#include <QFontDatabase>
#include <QEvent>
#include <QJsonDocument>
#include <QJsonObject>
#include <QLineEdit>
#include <QListWidget>
#include <QLabel>
#include <QPushButton>
#include <QStackedWidget>
#include <QTemporaryDir>
#include <QTextBrowser>
#include <QtTest/QTest>
#include <fstream>
#include <filesystem>
#include <iostream>

namespace {void require(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}}
class ObservedApplication final:public QApplication {
public:
    using QApplication::QApplication;
    int preview_polls{};
    bool notify(QObject* receiver,QEvent* event) override {
        if(event->type()==QEvent::Timer && receiver->objectName()==QStringLiteral("previewPoll"))++preview_polls;
        return QApplication::notify(receiver,event);
    }
};
int main(int argc,char** argv){
    ObservedApplication app(argc,argv);QFontDatabase::addApplicationFont(qEnvironmentVariable("WINDIR")+QStringLiteral("/Fonts/segoeui.ttf"));app.setFont(QFont(QStringLiteral("Segoe UI"),10));if(argc!=3)return 2;
    const QString out=QString::fromLocal8Bit(argv[2]);QDir().mkpath(out);QJsonObject receipt;
    try{
        PreviewWindow window(QString::fromLocal8Bit(argv[1]));window.show();QTest::qWait(40);
        const int before=app.preview_polls;QTest::qWait(1000);const int idle_polls=app.preview_polls-before;require(idle_polls>=5 && idle_polls<=20,"Idle main window still polls at playback frequency");
        auto* stack=window.findChild<QStackedWidget*>(QStringLiteral("workspacePages"));
        require(!window.findChild<QWidget*>(QStringLiteral("guideWorkspace")),"Guide must be lazy");
        QTest::keyClick(&window,Qt::Key_K,Qt::ControlModifier);QTest::qWait(30);
        auto* guide=window.findChild<QWidget*>(QStringLiteral("guideWorkspace"));require(guide && stack->currentWidget()==guide,"Ctrl+K did not open embedded guide");
        auto* search=guide->findChild<QLineEdit*>(QStringLiteral("guideSearch"));auto* list=guide->findChild<QListWidget*>(QStringLiteral("guideResults"));auto* body=guide->findChild<QTextBrowser*>(QStringLiteral("guideBody"));auto* go=guide->findChild<QPushButton*>(QStringLiteral("guideGo"));
        require(search && list && body && go && list->count()==8,"Guide controls or tasks missing");
        require(window.grab().save(out+QStringLiteral("/guide-overview.png")),"Guide overview capture failed");
        search->setText(QStringLiteral("billboard"));require(list->count()>0 && list->item(0)->text().startsWith(QStringLiteral("Find billboard")),"Exact object lookup missing");
        require(body->toPlainText().contains(QStringLiteral("Broad recognition")) && body->toPlainText().contains(QStringLiteral("does not guarantee")),"Capability lookup overstated or missing");
        require(window.grab().save(out+QStringLiteral("/guide-billboard.png")),"Guide object capture failed");
        go->click();require(stack->currentIndex()==0 && window.findChild<QComboBox*>(QStringLiteral("modelSelection"))->currentIndex()==4,"Object lookup did not select broad model");
        QTest::keyClick(&window,Qt::Key_F1);QTest::qWait(20);require(stack->currentWidget()==guide,"F1 duplicated/lost guide");
        search->setText(QStringLiteral("washing machine"));require(list->item(0)->text().startsWith(QStringLiteral("Find washing machine")),"Washer lookup failed");
        QTest::keyClick(search,Qt::Key_Return);require(stack->currentIndex()==0 && window.findChild<QComboBox*>(QStringLiteral("modelSelection"))->currentIndex()==4,"Enter lookup action failed");
        window.findChild<QPushButton*>(QStringLiteral("quickGuide"))->click();search->setText(QStringLiteral("dog"));require(list->item(0)->text().startsWith(QStringLiteral("Find dog ·")),"Exact dog result not ranked first");go->click();require(window.findChild<QComboBox*>(QStringLiteral("modelSelection"))->currentIndex()==1,"Common object should use YOLOX-S");
        window.findChild<QPushButton*>(QStringLiteral("quickGuide"))->click();search->setText(QStringLiteral("csv"));require(list->count()>0 && body->toPlainText().contains(QStringLiteral("CSV")),"Task search failed");go->click();require(window.analysis_workspace() && stack->currentWidget()==window.analysis_workspace(),"Guide navigation failed");
        window.findChild<QPushButton*>(QStringLiteral("quickGuide"))->click();search->setText(QStringLiteral("no-such-task-68425"));require(list->count()==0 && !go->isEnabled() && body->toPlainText().contains(QStringLiteral("Try a shorter")),"Empty search unsafe or unexplained");search->clear();require(list->count()==8 && go->isEnabled(),"Clearing search did not recover");
        window.resize(1000,680);QTest::qWait(20);require(window.grab().save(out+QStringLiteral("/guide-compact.png")),"Compact guide capture failed");
        int windows=0;for(auto* w:QApplication::topLevelWidgets())if(w->isVisible() && dynamic_cast<QMainWindow*>(w))++windows;require(windows==1,"Guide opened a separate main window");
        int supported=0;for(int id=0;id<frametrail::recognition_classes;++id)if(frametrail::model_has_class(frametrail::DetectorModel::nano,id)||frametrail::model_has_class(frametrail::DetectorModel::yolox_s,id)||frametrail::model_has_class(frametrail::DetectorModel::world_s,id)||frametrail::model_has_class(frametrail::DetectorModel::openimages,id))++supported;require(supported==615,"Lean profiles lost category coverage");
        QTemporaryDir temp(QDir(out).filePath(QStringLiteral("guide-test-XXXXXX")));temp.setAutoRemove(false);require(temp.isValid(),"Temporary fixture unavailable");require(QFileInfo(temp.path()).canonicalFilePath().startsWith(QFileInfo(out).canonicalFilePath()+QStringLiteral("/")),"Temporary cleanup target escaped evidence folder");temp.setAutoRemove(true);QDir fixture(temp.path());require(fixture.mkpath(QStringLiteral("app/models")) && fixture.mkpath(QStringLiteral("optional/models")),"Fixture directories failed");
        const auto touch=[](const QString& path){QFile file(path);require(file.open(QIODevice::WriteOnly),"Fixture file failed");file.write("fixture");};
        const auto nano=fixture.filePath(QStringLiteral("app/models/yolox_nano.onnx"));touch(nano);const auto optional=fixture.filePath(QStringLiteral("optional/models/rfdetr_balanced7805570_step100.onnx"));touch(optional);
        auto* selector=model_selector(nano);require(selector->itemData(6).toString()==optional,"Sibling optional model not resolved");require(!qobject_cast<QStandardItemModel*>(selector->model())->item(5)->isEnabled(),"Missing optional model selectable");delete selector;
        const auto local=fixture.filePath(QStringLiteral("app/models/rfdetr_balanced7805570_step100.onnx"));touch(local);require(available_model_path(nano,QStringLiteral("rfdetr_balanced7805570_step100.onnx"))==local,"Local model precedence changed");
        window.close();for(int i=0;i<100 && window.isVisible();++i)QTest::qWait(10);require(!window.isVisible(),"Idle guide close failed");
        receipt={{"status","passed"},{"embedded_guide",true},{"CtrlK_and_F1",true},{"object_model_lookup",true},{"exact_name_ranking",true},{"task_navigation",true},{"empty_search",true},{"core_category_union",supported},{"optional_model_resolution",true},{"missing_optional_disabled",true},{"local_model_precedence",true},{"no_model_inference_needed",true},{"idle_main_polls_observed_in_1_second",idle_polls}};
    }catch(const std::exception& e){receipt={{"status","failed"},{"error",QString::fromUtf8(e.what())}};}
    std::ofstream file(std::filesystem::path(QDir(out).filePath(QStringLiteral("result.json")).toStdWString()));file<<QJsonDocument(receipt).toJson().toStdString();std::cout<<QJsonDocument(receipt).toJson().toStdString();return receipt["status"]=="passed"?0:1;
}
