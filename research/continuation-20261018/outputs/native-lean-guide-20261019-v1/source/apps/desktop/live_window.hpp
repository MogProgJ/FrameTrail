#pragma once
#include "frametrail/live_session.hpp"
#include <QMainWindow>
#include <QTimer>
class QComboBox;
class QPushButton;
class QCheckBox;
class QDoubleSpinBox;
class QLabel;
class FrameCanvas;

class LiveWindow:public QMainWindow {
public:
    explicit LiveWindow(QString model, frametrail::DetectorModel variant=frametrail::DetectorModel::nano,
        frametrail::DetectorBackend backend=frametrail::DetectorBackend::cpu);
    void request_stop(){session_.stop();}
    bool active() const{return session_.snapshot().active;}
protected:
    void closeEvent(QCloseEvent*) override;
private:
    void refresh();
    void start();
    void tick();
    void update_controls();
    QString model_;
    frametrail::LiveSession session_;
    frametrail::CountingLine line_;
    QTimer timer_;
    QComboBox* model_box_{};
    QComboBox* backend_box_{};
    QComboBox *cameras_{},*format_{},*classes_{},*direction_{};
    QPushButton *start_{},*stop_{},*refresh_{},*draw_{};
    QCheckBox *detect_{},*track_{};
    QDoubleSpinBox* confidence_{};
    QLabel *status_{},*metrics_{},*counts_{},*camera_indicator_{};
    FrameCanvas* canvas_{};
    std::vector<frametrail::CameraDevice> devices_;
    bool closing_{},editing_{},pending_edit_{};
};
