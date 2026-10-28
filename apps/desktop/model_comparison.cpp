#include "model_comparison.hpp"
#include <QDialog>
#include <QDialogButtonBox>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QHeaderView>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QLabel>
#include <QTableWidget>
#include <QVBoxLayout>
#include <cmath>
#include <set>

std::vector<ReviewedRun> reviewed_runs(const QString& folder,const QString& video) {
    std::map<QString,ReviewedRun> newest;
    for(const auto& entry:QDir(folder).entryInfoList({QStringLiteral("*.json")},QDir::Files)) {
        QFile file(entry.filePath());
        if(!file.open(QIODevice::ReadOnly))continue;
        const auto root=QJsonDocument::fromJson(file.readAll()).object();
        if(root.value(QStringLiteral("schema")).toInt()!=1 || root.value(QStringLiteral("video")).toString()!=video)continue;
        ReviewedRun run;
        run.run_id=root.value(QStringLiteral("run_id")).toString();run.video=video;
        run.model=root.value(QStringLiteral("model")).toString();run.confidence=root.value(QStringLiteral("confidence")).toDouble();
        run.appearances=root.value(QStringLiteral("appearances")).toInteger();run.saved=entry.lastModified();
        for(const auto& value:root.value(QStringLiteral("verdicts")).toArray()) {
            const auto verdict=value.toObject();
            const bool correct=verdict.value(QStringLiteral("correct")).toBool();
            auto& object=run.objects[verdict.value(QStringLiteral("object")).toString()];
            ++run.reviewed;++object.first;
            if(correct){++run.correct;++object.second;}
        }
        if(!run.reviewed || run.model.isEmpty())continue;
        auto& kept=newest[run.model];
        if(kept.model.isEmpty() || run.saved>kept.saved)kept=std::move(run);
    }
    std::vector<ReviewedRun> runs;
    for(auto& [model,run]:newest)runs.push_back(std::move(run));
    return runs;
}

QTableWidget* comparison_table(const std::vector<ReviewedRun>& runs,QWidget* parent) {
    std::set<QString> objects;
    for(const auto& run:runs)for(const auto& [name,counts]:run.objects)objects.insert(name);
    auto* table=new QTableWidget(int(4+objects.size()),int(runs.size()),parent);
    table->setObjectName(QStringLiteral("modelComparison"));
    table->setEditTriggers(QAbstractItemView::NoEditTriggers);table->setSelectionMode(QAbstractItemView::NoSelection);
    QStringList rows{QStringLiteral("Appearances found"),QStringLiteral("Reviewed"),QStringLiteral("Marked correct"),
                     QStringLiteral("Correct appearances (estimate)")};
    for(const auto& name:objects)rows<<QStringLiteral("%1 · correct").arg(name);
    table->setVerticalHeaderLabels(rows);
    const auto percent=[](int correct,int reviewed){return QStringLiteral("%1%  (%2 of %3)").arg(std::lround(100.*correct/reviewed)).arg(correct).arg(reviewed);};
    for(int column=0;column<int(runs.size());++column) {
        const auto& run=runs[std::size_t(column)];
        table->setHorizontalHeaderItem(column,new QTableWidgetItem(QStringLiteral("%1\nconfidence %2").arg(run.model).arg(run.confidence,0,'f',2)));
        const QStringList values{QString::number(run.appearances),QString::number(run.reviewed),percent(run.correct,run.reviewed),
                                 QString::number(std::llround(double(run.appearances)*run.correct_share()))};
        for(int row=0;row<values.size();++row)table->setItem(row,column,new QTableWidgetItem(values[row]));
        int row=4;
        for(const auto& name:objects) {
            const auto found=run.objects.find(name);
            table->setItem(row++,column,new QTableWidgetItem(found==run.objects.end() ? QStringLiteral("–") : percent(found->second.second,found->second.first)));
        }
    }
    // The better model per row in bold: more found, a higher share correct, more correct (not "Reviewed").
    const auto mark=[&](int row,const auto& value) {
        int best=-1,valued=0;double top=-1;bool tie=false;
        for(int column=0;column<int(runs.size());++column) {
            const auto v=value(runs[std::size_t(column)]);
            if(v<0)continue;
            ++valued;
            if(v>top){top=v;best=column;tie=false;}else if(v==top)tie=true;
        }
        if(valued<2 || tie)return;
        auto font=table->item(row,best)->font();font.setBold(true);table->item(row,best)->setFont(font);
    };
    mark(0,[](const ReviewedRun& r){return double(r.appearances);});
    mark(2,[](const ReviewedRun& r){return r.correct_share();});
    mark(3,[](const ReviewedRun& r){return double(r.appearances)*r.correct_share();});
    int row=4;
    for(const auto& name:objects)mark(row++,[&](const ReviewedRun& r){
        const auto found=r.objects.find(name);return found==r.objects.end() ? -1. : double(found->second.second)/found->second.first;});
    table->horizontalHeader()->setSectionResizeMode(QHeaderView::Stretch);
    return table;
}

void show_model_comparison(QWidget* parent,const QString& folder,const QString& video) {
    const auto runs=reviewed_runs(folder,video);
    QDialog dialog(parent);dialog.setWindowTitle(QStringLiteral("Compare models · %1").arg(video));dialog.resize(720,520);
    auto* layout=new QVBoxLayout(&dialog);
    auto* note=new QLabel;note->setWordWrap(true);note->setTextFormat(Qt::PlainText);
    if(runs.size()<2) {
        note->setText(runs.empty() ? QStringLiteral("No reviewed analyses of this video yet. Analyse it, mark some appearances correct or wrong, "
                                                    "then do the same with another model.")
                                   : QStringLiteral("Only %1 has been reviewed on this video. Analyse it with another model and review some "
                                                    "appearances to compare.").arg(runs.front().model));
    } else {
        note->setText(QStringLiteral("The newest review of each model on this video. \"Marked correct\" is measured on the appearances you "
            "reviewed, so review a similar number with each model. The estimate multiplies the appearances found by that share: "
            "higher means more real objects found."));
    }
    layout->addWidget(note);
    if(!runs.empty())layout->addWidget(comparison_table(runs,&dialog),1);
    auto* buttons=new QDialogButtonBox(QDialogButtonBox::Close);
    QObject::connect(buttons,&QDialogButtonBox::rejected,&dialog,&QDialog::reject);layout->addWidget(buttons);
    dialog.exec();
}
