#pragma once
#include <QString>

// Shared by all desktop windows; layouts live in Qt Designer .ui or native Qt layouts.
inline QString frametrail_theme() {
    return QStringLiteral(R"(
        QWidget { color: #e8edf5; font-family: 'Segoe UI'; font-size: 13px; }
        QMainWindow, QWidget#shell { background: #10151d; }
        QLabel { background: transparent; }
        QLabel#title { font-size: 25px; font-weight: 600; }
        QLabel#subtitle, QLabel#source, QLabel[role="muted"] { color: #a1afc2; }
        QLabel[role="section"] { color: #92a5bf; font-size: 11px; font-weight: 600; letter-spacing: 2px; }
        QLabel#state, QLabel#liveStatus { color: #78e2c4; }
        QLabel[role="badge"] { color: #84e8cf; background: #17352f; border-radius: 5px; padding: 6px 10px; }
        QFrame#inspector { background: #171f2a; border: 1px solid #2a3545; border-radius: 10px; }
        QScrollArea { border: none; background: transparent; }
        QScrollArea > QWidget > QWidget { background: transparent; }
        QPushButton { background: #243145; border: 1px solid #34445c; border-radius: 6px; padding: 9px 14px; font-weight: 500; }
        QPushButton:hover { background: #30425b; border-color: #607793; }
        QPushButton:pressed { background: #172332; }
        QPushButton:focus, QComboBox:focus, QDoubleSpinBox:focus, QListWidget:focus { border: 2px solid #8db9ff; }
        QPushButton:disabled { color: #7b8799; background: #1a2432; border-color: #273447; }
        QPushButton[role="primary"] { background: #78e2c4; color: #102820; border-color: #78e2c4; font-weight: 600; }
        QPushButton[role="primary"]:hover { background: #a1f2dc; }
        QPushButton[role="primary"]:disabled { background: #25453d; color: #96a9a2; border-color: #34564c; }
        QComboBox, QDoubleSpinBox { background: #101824; border: 1px solid #3c4d64; border-radius: 5px; padding: 7px 10px; min-height: 19px; }
        QComboBox:disabled, QDoubleSpinBox:disabled, QCheckBox:disabled { color: #7b8799; }
        QComboBox QAbstractItemView { background: #1b293b; selection-background-color: #365377; }
        QCheckBox { spacing: 9px; min-height: 28px; }
        QCheckBox::indicator { width: 17px; height: 17px; }
        QListWidget { background: #121b28; border: 1px solid #2a3545; border-radius: 6px; }
        QListWidget::item { padding: 10px; border-bottom: 1px solid #273447; }
        QListWidget::item:selected { background: #294965; }
        QProgressBar { background: #172332; border: 1px solid #34445c; border-radius: 4px; text-align: center; }
        QProgressBar::chunk { background: #397d70; }
        QToolTip { color: #edf4fc; background: #243145; border: 1px solid #607793; padding: 6px; }
        QScrollBar:vertical { background: #172332; width: 10px; }
        QScrollBar::handle:vertical { background: #52657e; min-height: 25px; border-radius: 4px; }
    )");
}
