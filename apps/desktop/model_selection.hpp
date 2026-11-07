#pragma once
#include "frametrail/detector.hpp"
#include <QComboBox>
#include <QFileInfo>
#include <QDir>
#include <QStandardItemModel>

inline QString available_model_path(const QString& nano_path, const QString& filename) {
    const auto directory=QFileInfo(nano_path).dir();
    const auto local=directory.filePath(filename);
    if(QFileInfo::exists(local))return local;
    const auto optional=QDir::cleanPath(directory.filePath(QStringLiteral("../../optional/models/")+filename));
    return QFileInfo::exists(optional)?optional:local;
}

inline constexpr int combined_index=8; // "Combined" entry: the trained RF-DETR plus YOLOX-S (Analysis only).
inline constexpr int companion_role=Qt::UserRole+1;
inline QComboBox* model_selector(const QString& nano_path, QWidget* parent = nullptr, bool combined = false) {
    auto* box=new QComboBox(parent);
    box->setObjectName(QStringLiteral("modelSelection"));
    box->setAccessibleName(QStringLiteral("Detection model"));
    box->addItem(QStringLiteral("YOLOX-Nano · faster"),nano_path);
    const auto small=available_model_path(nano_path,QStringLiteral("yolox_s.onnx"));
    box->addItem(QStringLiteral("YOLOX-S · more detail"),small);
    box->addItem(QStringLiteral("YOLO-World S · experimental"),available_model_path(nano_path,QStringLiteral("yolo_world_s.onnx")));
    box->addItem(QStringLiteral("YOLO-World M · experimental"),available_model_path(nano_path,QStringLiteral("yolo_world_m.onnx")));
    box->addItem(QStringLiteral("Broad recognition · 597 categories"),available_model_path(nano_path,QStringLiteral("yolo_openimages.onnx")));
    box->addItem(QStringLiteral("RF-DETR · experimental"),available_model_path(nano_path,QStringLiteral("rfdetr_scale7758628.onnx")));
    box->setItemData(5,QStringLiteral("Experimental trained RF candidate for local testing. High false-positive rate in evaluation. CPU and DirectML GPU verified; automatic mode falls back to CPU if unavailable. Training contained positives for 115 categories; broader label support does not imply learned accuracy."),Qt::ToolTipRole);
    box->addItem(QStringLiteral("RF-DETR · balanced preview"),available_model_path(nano_path,QStringLiteral("rfdetr_balanced7805570_step100.onnx")));
    box->setItemData(6,QStringLiteral("Local experimental model. On 130 held-out photos, detected 3 of 15 known washing-machine targets and 0 of 19 billboard targets; measured cat/dog results retained. Small assistant-reviewed evidence; 615 labels do not imply accuracy for every category."),Qt::ToolTipRole);
    box->addItem(QStringLiteral("RF-DETR · Open Images (trained)"),available_model_path(nano_path,QStringLiteral("rfdetr_openimages.onnx")));
    box->setItemData(7,QStringLiteral("RF-DETR fine-tuned on Open Images (training/export.py). Only detects the categories it was trained on; its scores are in the training run's eval-test.json. CPU or DirectML GPU; automatic mode falls back to CPU if unavailable."),Qt::ToolTipRole);
    if(combined) {
        box->addItem(QStringLiteral("Combined · trained RF-DETR + YOLOX-S"),box->itemData(7));
        box->setItemData(combined_index,small,companion_role);
        box->setItemData(combined_index,QStringLiteral("Runs both models on every frame and merges their boxes: YOLOX-S's people, vehicles, bags and umbrellas "
            "plus the trained model's 595 object types. About 1.5 times the trained model's time."),Qt::ToolTipRole);
    }
    box->setToolTip(QStringLiteral("YOLOX: 80 categories. YOLO-World: 100, including fox, balloon and lantern. Open Images: 601 trained labels grouped into 597 categories, explicitly trained for foxes and many more types. World is experimental. All processing stays on this device. World M needs more compute. Broader vocabulary does not guarantee correct labels."));
    auto* items=qobject_cast<QStandardItemModel*>(box->model());
    for(int index=0;index<box->count();++index)if(!QFileInfo::exists(box->itemData(index).toString()) ||
        (index==combined_index && !QFileInfo::exists(box->itemData(index,companion_role).toString()))) {
        items->item(index)->setEnabled(false);box->setItemText(index,box->itemText(index)+QStringLiteral(" · not installed"));
    }
    return box;
}
inline frametrail::DetectorModel selected_model(const QComboBox* box) {
    if(box->currentIndex()==combined_index)return frametrail::DetectorModel::rf_openimages;
    return static_cast<frametrail::DetectorModel>(box->currentIndex());
}
// The YOLOX-S model run next to the main one, or empty.
inline QString selected_companion(const QComboBox* box) {
    return box->currentIndex()==combined_index ? box->currentData(companion_role).toString() : QString{};
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
