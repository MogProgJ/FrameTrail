#pragma once
#include <QString>

inline QString frametrail_theme() {
    return QStringLiteral(R"(
        QWidget { color:#e7e7ec; font-family:'Segoe UI'; font-size:13px; selection-background-color:#3c4052; selection-color:#ffffff; }
        QMainWindow, QWidget#shell { background:#121315; }
        QLabel { background:transparent; }
        QLabel#title { font-size:20px; font-weight:600; letter-spacing:-0.4px; }
        QLabel#subtitle, QLabel#source, QLabel[role="muted"] { color:#a1a1ab; }
        QLabel#source { padding:8px 4px; font-size:12px; }
        QLabel[role="section"] { color:#9696a2; font-size:11px; font-weight:600; letter-spacing:1px; }
        QLabel#state, QLabel#liveStatus { color:#b8bad0; font-size:12px; }
        QLabel[role="badge"] { color:#c2c4d3; background:#25262d; border:1px solid #34353e; border-radius:10px; padding:5px 10px; font-size:11px; }
        QLabel#workspaceActivity[busy="true"] { color:#e2dcff; background:#302a43; border-color:#524771; }
        QStackedWidget#workspacePages { background:transparent; }
        QLabel#studioBrand { font-size:17px; font-weight:600; letter-spacing:-0.3px; padding:8px 2px; }
        QLabel#studioContext { font-size:12px; color:#8f8f9a; }
        QLabel#studioBreadcrumb { color:#b7b7c2; font-size:12px; }
        QFrame#inspector { background:#1b1c20; border:1px solid #2b2c33; border-radius:12px; }
        QFrame#workspaceRail { background:#17181b; border:1px solid #292a31; border-radius:12px; }
        QFrame#transportBar, QFrame#studioToolbar { background:#1b1c20; border:1px solid #2b2c33; border-radius:10px; }
        QScrollArea { border:none; background:transparent; }
        QScrollArea > QWidget > QWidget { background:transparent; }
        QPushButton, QToolButton { background:#26272e; border:1px solid #383942; border-radius:7px; padding:8px 13px; min-height:17px; font-weight:500; }
        QPushButton:hover, QToolButton:hover { background:#30313b; border-color:#555766; }
        QPushButton:pressed, QToolButton:pressed { background:#1d1e24; }
        QPushButton:focus, QToolButton:focus, QComboBox:focus, QDoubleSpinBox:focus, QListWidget:focus { border:1px solid #b8b2ff; }
        QPushButton:disabled, QToolButton:disabled { color:#757580; background:#202126; border-color:#2a2b31; }
        QPushButton[role="primary"] { background:#c1baff; color:#1a1730; border-color:#c1baff; font-weight:600; }
        QPushButton[role="primary"]:hover { background:#d2ccff; border-color:#d2ccff; }
        QPushButton[role="primary"]:pressed { background:#aaa0ef; }
        QPushButton[role="primary"]:disabled { color:#89849f; background:#383442; border-color:#474250; }
        QPushButton[role="navigation"] { text-align:left; background:transparent; border:1px solid transparent; padding:10px 10px; color:#a3a3ae; }
        QPushButton[role="navigation"]:hover { background:#24252c; color:#e5e5ed; }
        QPushButton:checked { color:#dedbff; background:#30303e; border-color:#4c4867; }
        QLabel#activeWorkspace { background:#2d2b3b; color:#ddd7ff; border:1px solid #464057; border-radius:7px; padding:11px 12px; font-weight:600; }
        QComboBox, QDoubleSpinBox { background:#141518; border:1px solid #383a43; border-radius:6px; padding:8px 10px; min-height:18px; }
        QComboBox:disabled, QDoubleSpinBox:disabled, QCheckBox:disabled { color:#7e7e8a; }
        QComboBox::drop-down { width:25px; border:0; background:transparent; }
        QComboBox::down-arrow { image:url(:/studio/down.png); width:12px; height:12px; }
        QDoubleSpinBox::up-arrow { image:url(:/studio/up.png); width:10px; height:10px; }
        QDoubleSpinBox::down-arrow { image:url(:/studio/down.png); width:10px; height:10px; }
        QComboBox QAbstractItemView { background:#23242b; color:#e5e5ed; border:1px solid #454651; selection-background-color:#3d3855; padding:4px; }
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { width:20px; border:0; background:#25262e; }
        QCheckBox { spacing:10px; min-height:28px; }
        QCheckBox::indicator { width:18px; height:18px; }
        QListWidget { background:#1b1c20; border:1px solid #2d2e35; border-radius:10px; outline:0; }
        QListWidget::item { padding:13px; margin:3px; border:1px solid transparent; border-radius:7px; }
        QListWidget::item:hover { background:#24252d; }
        QListWidget::item:selected { background:#302e41; border-color:#49425f; }
        QProgressBar { background:#292a32; border:none; border-radius:3px; text-align:center; min-height:5px; }
        QProgressBar::chunk { background:#b7adfa; border-radius:3px; }
        QToolTip { color:#eeeeF5; background:#2a2b33; border:1px solid #565866; padding:7px; }
        QScrollBar:vertical { background:transparent; width:7px; margin:3px 0; }
        QScrollBar::handle:vertical { background:#494b57; min-height:28px; border-radius:3px; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background:transparent; }
        QSplitter::handle { background:transparent; }
        QSplitter::handle:hover { background:#494458; border-radius:3px; }
        QTabWidget::pane { border:none; background:transparent; }
        QTabBar::tab { color:#9999a7; background:transparent; padding:9px 15px; border:1px solid transparent; border-radius:6px; margin:2px; }
        QTabBar::tab:selected { color:#e5e0ff; background:#34303f; border-color:#494253; }
        QTabBar::tab:hover { color:#f0edf9; background:#282831; }
        QMenu { background:#202127; border:1px solid #3a3b46; padding:5px; }
        QMenu::item { padding:8px 24px; }
        QMenu::item:selected { background:#393449; }
    )");
}
