#pragma once
#include "frametrail/detector.hpp"
#include <QComboBox>
#include <QFileInfo>
#include <QDir>
#include <QStandardItemModel>

inline QComboBox* model_selector(const QString& nano_path, QWidget* parent = nullptr) {
    auto* box=new QComboBox(parent);
    box->setObjectName(QStringLiteral("modelSelection"));
    box->setAccessibleName(QStringLiteral("Detection model"));
    box->addItem(QStringLiteral("YOLOX-Nano · faster"),nano_path);
    const auto small=QFileInfo(nano_path).dir().filePath(QStringLiteral("yolox_s.onnx"));
    box->addItem(QStringLiteral("YOLOX-S · more detail"),small);
    box->setToolTip(QStringLiteral("Both recognize 80 categories. S uses more CPU and may slow playback. Install with scripts/fetch-model.ps1 -Model all, rebuild, then reopen."));
    if(!QFileInfo::exists(small)) {
        auto* items=qobject_cast<QStandardItemModel*>(box->model());
        items->item(1)->setEnabled(false);
        box->setItemText(1,QStringLiteral("YOLOX-S · not installed"));
    }
    return box;
}
inline frametrail::DetectorModel selected_model(const QComboBox* box) {
    return box->currentIndex()==1 ? frametrail::DetectorModel::yolox_s : frametrail::DetectorModel::nano;
}
