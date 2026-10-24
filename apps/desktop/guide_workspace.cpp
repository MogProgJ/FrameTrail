#include "guide_workspace.hpp"
#include "frametrail/detector.hpp"
#include "studio_controls.hpp"
#include <QAction>
#include <QComboBox>
#include <QFileInfo>
#include <QHBoxLayout>
#include <QLabel>
#include <QLineEdit>
#include <QListWidget>
#include <QPushButton>
#include <QTextBrowser>
#include <QVBoxLayout>
#include <algorithm>

GuideWorkspace::GuideWorkspace(const QComboBox* models,QWidget* parent):QWidget(parent) {
    setObjectName(QStringLiteral("guideWorkspace"));
    for(int i=0;i<models->count();++i)installed_.push_back(QFileInfo::exists(models->itemData(i).toString()));
    tasks_={
        {"Open an image or video", "Start in Preview. Click Open media, press Ctrl+O, or drag a file into Preview.\n\nUse Space to play or pause. Preview shows the current scene; it does not save a full analysis.", "open import image video photo drag drop preview space", "Open Preview",0},
        {"Find an object or choose a model", "Type an object name into the search above, such as billboard, washing machine, dog or fox. The guide checks the installed models' category lists.\n\nYOLOX-S covers common objects. Broad recognition includes billboards and washing machines. A listed category does not guarantee a correct detection.\n\nThe model and confidence controls are in Preview's Detection inspector. Ctrl+I shows or hides that inspector.", "model category categories object detect billboard washing machine fox inspector confidence", "Open Preview",0},
        {"Find every appearance in a video", "Open Analysis, choose a video and start analysis. Review the appearances and jump to the moments you need.\n\nYou can visit another section while analysis continues. The badge at the top shows work in progress. Stop keeps partial results for review and saving.", "analyse analyze analysis appearances search timeline stop cancel background", "Open Analysis",1},
        {"Watch smooth playback", "Open Playback. Choose a video, or use Use preview video to copy Preview's video and settings. Click Prepare playback.\n\nPreparation runs detection once, then playback reuses the saved boxes. Preparation can take time; it is not instant live detection. Leaving this section pauses playback.", "smooth playback prepare cache stutter lag speed replay", "Open Playback",2},
        {"Check how accurate the model is", "In Analysis, analyse a video, then select each appearance and press C if the box and label are right or X if it is wrong (U clears). The list moves on to the next one by itself.\n\nThe panel shows how many you reviewed and the share that is correct, overall and on each object chip. Reviews are kept for that analysis and come back when you reopen it. Export review writes them to a CSV, so two models can be compared on the same video.", "review accuracy correct wrong false alarm check verify precision compare model mark", "Open Analysis",1},
        {"Save results or export a CSV", "In Analysis, use Save to keep a .frametrail analysis you can reopen. Use CSV export for a table of the results.\n\nSave before discarding or replacing results you want to keep. If you close while work is running, the app waits and offers a choice for unsaved results.", "save export csv table results reopen analysis file", "Open Analysis",1},
        {"Track movement and count crossings", "In Preview, open the Tracking inspector. Enable tracking and choose the object types you need.\n\nDraw a counting line by clicking endpoints A and B. Right-click cancels drawing. Set the crossing direction; counts belong to this session. Tracking links detections over time, so missed detections can affect counts.", "track tracking movement count counting crossings line direction", "Open Preview",0},
        {"Use a camera", "Open Camera, choose a device and click Start. Entering Camera does not turn it on. Leaving the section requests capture to stop.\n\nA working camera and driver are required. If no device is available, use a video in Preview or Analysis instead.", "camera webcam live capture device start stop", "Open Camera",3},
        {"Keyboard shortcuts and faster processing", "Ctrl+1  Preview\nCtrl+2  Analysis\nCtrl+3  Playback\nCtrl+4  Camera\nCtrl+K or F1  This guide and search\nCtrl+O  Open media in Preview\nCtrl+I  Preview inspector\nSpace  Play / pause in Preview\n\nFor quicker detection, try YOLOX-Nano when its category list covers your object. A faster model may miss more detail. Smooth Playback prepares boxes once; it does not make detection itself faster. All processing stays on this device.", "keyboard shortcut navigation help guide faster performance cpu gpu", "Open Preview",0}
    };
    auto* root=new QVBoxLayout(this);root->setContentsMargins(24,18,24,18);root->setSpacing(12);
    auto* heading=new QLabel(QStringLiteral("What would you like to do?"));heading->setObjectName(QStringLiteral("title"));root->addWidget(heading);
    auto* intro=new QLabel(QStringLiteral("A short guide to the workspace. Search a task or an object name."));intro->setWordWrap(true);intro->setProperty("role","muted");root->addWidget(intro);
    search_=new QLineEdit;search_->setObjectName(QStringLiteral("guideSearch"));search_->setAccessibleName(QStringLiteral("Search tasks and object categories"));search_->setPlaceholderText(QStringLiteral("Search tasks or objects, e.g. export or billboard"));search_->setClearButtonEnabled(true);search_->setMinimumHeight(36);root->addWidget(search_);
    summary_=new QLabel;summary_->setObjectName(QStringLiteral("guideSummary"));summary_->setProperty("role","muted");summary_->setWordWrap(true);root->addWidget(summary_);
    auto* columns=new QHBoxLayout;columns->setSpacing(18);
    results_=new QListWidget;results_->setObjectName(QStringLiteral("guideResults"));results_->setAccessibleName(QStringLiteral("Guide search results"));results_->setWordWrap(true);results_->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);results_->setResizeMode(QListView::Adjust);results_->setMinimumWidth(190);results_->setMaximumWidth(285);results_->setSpacing(1);columns->addWidget(results_,1);
    auto* detail=new QVBoxLayout;detail->setSpacing(12);title_=new QLabel;title_->setObjectName(QStringLiteral("guideTitle"));title_->setTextFormat(Qt::PlainText);title_->setWordWrap(true);title_->setStyleSheet(QStringLiteral("font-size:18px;font-weight:600;padding-top:6px;"));detail->addWidget(title_);
    body_=new QTextBrowser;body_->setObjectName(QStringLiteral("guideBody"));body_->setAccessibleName(QStringLiteral("Guide instructions"));body_->setOpenExternalLinks(false);detail->addWidget(body_,1);
    go_=new QPushButton;go_->setObjectName(QStringLiteral("guideGo"));go_->setProperty("role","primary");detail->addWidget(go_,0,Qt::AlignLeft);columns->addLayout(detail,2);root->addLayout(columns,1);
    connect(search_,&QLineEdit::textChanged,this,[this]{filter();});
    connect(results_,&QListWidget::currentRowChanged,this,[this]{show_entry();});
    connect(search_,&QLineEdit::returnPressed,go_,&QPushButton::click);
    connect(results_,&QListWidget::itemActivated,go_,[this]{go_->click();});
    connect(go_,&QPushButton::clicked,this,[this]{const auto row=results_->currentRow();if(navigate && row>=0 && row<visible_.size())navigate(visible_[row].section,visible_[row].model);});
    filter();
}
void GuideWorkspace::focus_search(){search_->setFocus(Qt::ShortcutFocusReason);search_->selectAll();}
void GuideWorkspace::filter(){
    const auto query=search_->text().simplified().toLower().replace('_',' ').replace('-',' ');
    visible_.clear();results_->clear();
    for(const auto& task:tasks_)if(query.isEmpty() || (task.title+' '+task.keywords+' '+task.body).contains(query,Qt::CaseInsensitive))visible_.push_back(task);
    if(query.size()>=2){
        QVector<int> matches;
        for(int id=0;id<frametrail::recognition_classes;++id)if(QString::fromUtf8(frametrail::class_name(id).data(),int(frametrail::class_name(id).size())).contains(query,Qt::CaseInsensitive))matches.push_back(id);
        std::stable_sort(matches.begin(),matches.end(),[&](int a,int b){return (QString::fromUtf8(frametrail::class_name(a).data(),int(frametrail::class_name(a).size())).compare(query,Qt::CaseInsensitive)==0)>(QString::fromUtf8(frametrail::class_name(b).data(),int(frametrail::class_name(b).size())).compare(query,Qt::CaseInsensitive)==0);});
        if(matches.size()>8)matches.resize(8);
        for(auto match=matches.crbegin();match!=matches.crend();++match){
            const int id=*match;
            const auto name=QString::fromUtf8(frametrail::class_name(id).data(),int(frametrail::class_name(id).size()));int preferred=-1;QStringList supported;
            for(const int index:{1,4,0,2,3,7,6,5})if(index<installed_.size() && installed_[index] && frametrail::model_has_class(static_cast<frametrail::DetectorModel>(index),id)){
                if(preferred<0)preferred=index;supported<<QString::fromUtf8(frametrail::model_name(static_cast<frametrail::DetectorModel>(index)).data(),int(frametrail::model_name(static_cast<frametrail::DetectorModel>(index)).size()));
            }
            const auto model=preferred==4?QStringLiteral("Broad recognition"):preferred<0?QString{}:QString::fromUtf8(frametrail::model_name(static_cast<frametrail::DetectorModel>(preferred)).data(),int(frametrail::model_name(static_cast<frametrail::DetectorModel>(preferred)).size()));
            const auto explanation=preferred<0?QStringLiteral("No installed model lists this object. Optional models are separate from the main app package. Restart after installing an optional model."):QStringLiteral("%1 is listed by %2.\n\nUse the button below to select that model in Preview. Turn on Detect objects and open your image or video.\n\nA category in a model's list does not guarantee a correct detection. Check the boxes yourself before relying on the results. Experimental models remain previews.\n\nInstalled models listing this object:\n%3").arg(name,model,supported.join(QStringLiteral("\n")));
            visible_.prepend({QStringLiteral("Find %1 · object type").arg(name),explanation,name,preferred<0?QStringLiteral("Open Preview"):QStringLiteral("Use in Preview"),0,preferred});
        }
    }
    for(const auto& item:visible_)results_->addItem(item.title);
    summary_->setText(query.isEmpty()?QStringLiteral("%1 quick guides · Ctrl+K to search from any section").arg(tasks_.size()):QStringLiteral("%1 matches · object suggestions show up to 8 category names").arg(visible_.size()));
    if(!visible_.isEmpty())results_->setCurrentRow(0);else show_entry();
}
void GuideWorkspace::show_entry(){
    const auto row=results_->currentRow();const bool valid=row>=0 && row<visible_.size();go_->setEnabled(valid);
    title_->setText(valid?visible_[row].title:QStringLiteral("No matching task or object"));
    body_->setPlainText(valid?visible_[row].body:QStringLiteral("Try a shorter word, such as save, camera, dog or washing machine. Category names are in English."));go_->setText(valid?visible_[row].action:QStringLiteral("Choose a result"));
}
