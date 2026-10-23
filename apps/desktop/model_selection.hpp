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
    box->addItem(QStringLiteral("YOLO-World S · experimental"),QFileInfo(nano_path).dir().filePath(QStringLiteral("yolo_world_s.onnx")));
    box->addItem(QStringLiteral("YOLO-World M · experimental"),QFileInfo(nano_path).dir().filePath(QStringLiteral("yolo_world_m.onnx")));
    box->addItem(QStringLiteral("Broad recognition · 597 categories"),QFileInfo(nano_path).dir().filePath(QStringLiteral("yolo_openimages.onnx")));
    box->addItem(QStringLiteral("RF-DETR · trained 7758628 · experimental"),QFileInfo(nano_path).dir().filePath(QStringLiteral("rfdetr_scale7758628.onnx")));
    box->setItemData(5,QStringLiteral("Experimental trained RF candidate for local testing. High false-positive rate in evaluation. CPU and DirectML GPU verified; automatic mode falls back to CPU if unavailable. Training contained positives for 115 categories; broader label support does not imply learned accuracy."),Qt::ToolTipRole);
    box->setToolTip(QStringLiteral("YOLOX: 80 categories. YOLO-World: 100, including fox, balloon and lantern. Open Images: 601 trained labels grouped into 597 categories, explicitly trained for foxes and many more types. World is experimental. All processing stays on this device. World M needs more compute. Broader vocabulary does not guarantee correct labels."));
    auto* items=qobject_cast<QStandardItemModel*>(box->model());
    for(int index=0;index<box->count();++index)if(!QFileInfo::exists(box->itemData(index).toString())) {
        items->item(index)->setEnabled(false);box->setItemText(index,box->itemText(index)+QStringLiteral(" · not installed"));
    }
    return box;
}
inline frametrail::DetectorModel selected_model(const QComboBox* box) {
    return static_cast<frametrail::DetectorModel>(box->currentIndex());
}
inline QComboBox* backend_selector(QWidget* parent=nullptr) {
    auto* box=new QComboBox(parent);box->setObjectName(QStringLiteral("backendSelection"));
    box->setAccessibleName(QStringLiteral("Processing device"));
    box->addItems({QStringLiteral("CPU"),QStringLiteral("GPU · CPU fallback")});
    box->setToolTip(QStringLiteral("GPU uses the optional native DirectML runtime. If unavailable or a run fails, processing continues on the CPU. No cloud processing."));
    return box;
}
inline frametrail::DetectorBackend selected_backend(const QComboBox* box) {
    return box->currentIndex()==1 ? frametrail::DetectorBackend::automatic:frametrail::DetectorBackend::cpu;
}
