#pragma once
#include <QColor>
#include <algorithm>
#include <utility>
#include <QGuiApplication>
#include <QPalette>
#include <QString>

// FrameTrail design tokens: Windows 11 (Fluent 2) dark neutrals, the Windows accent colour,
// the Segoe UI Variable type ramp, 4 px control and 8 px card corners. Widgets use the
// stylesheet below; custom painting (video canvas, overlays, icons) reads the same tokens.
namespace ft::ui {
inline const QColor window{"#1a1a1a"};       // App background behind panes and pages
inline const QColor pane{"#1f1f1f"};         // Navigation pane
inline const QColor card{"#242424"};         // Cards, inspector, transport
inline const QColor card_hover{"#2b2b2b"};
inline const QColor control{"#2d2d2d"};      // Buttons, inputs
inline const QColor control_hover{"#343434"};
inline const QColor control_pressed{"#282828"};
inline const QColor canvas{"#111111"};       // Video surface
inline const QColor stroke{"#333333"};       // Card and divider strokes
inline const QColor stroke_control{"#3d3d3d"};
inline const QColor stroke_strong{"#5c5c5c"};
inline const QColor text{"#f3f3f3"};
inline const QColor text_secondary{"#c5c5c5"};
inline const QColor text_tertiary{"#969696"};
inline const QColor text_disabled{"#6b6b6b"};
inline const QColor success{"#6ccb5f"};
inline const QColor caution{"#fce100"};
inline const QColor critical{"#ff99a4"};
inline const QColor line_color{"#ffc83d"};   // Counting line

// The Windows accent, lightened for dark surfaces as Windows itself does; a fixed blue elsewhere.
inline QColor accent() {
    static const QColor value=[]{
        QColor base("#60cdff");
#ifdef Q_OS_WIN
        const auto system=QGuiApplication::palette().color(QPalette::Accent);
        if(system.isValid() && system.hslSaturation()>40) {
            base=system.toHsl();
            base.setHsl(base.hslHue(),std::max(base.hslSaturation(),170),std::max(base.lightness(),172));
            base=base.toRgb();
        }
#endif
        return base;
    }();
    return value;
}
inline QColor accent_hover() {return accent().darker(108);}
inline QColor accent_pressed() {return accent().darker(118);}
inline QColor on_accent() {return QColor("#000000");}
inline QColor accent_subtle() {auto c=accent();c.setAlpha(46);return c;}

// Distinct, dark-background-friendly colours for object types and tracks.
inline QColor category_color(int id) {
    static const QColor palette[]={QColor("#60cdff"),QColor("#6ccb5f"),QColor("#ffb900"),QColor("#ff8c64"),
        QColor("#c4a2ff"),QColor("#3fd2c7"),QColor("#ff7eb6"),QColor("#b5d95a"),QColor("#8fb8ff"),
        QColor("#ffd66b"),QColor("#e98bff"),QColor("#7fe0a3")};
    constexpr int size=int(sizeof(palette)/sizeof(palette[0]));
    return palette[((id%size)+size)%size];
}
}

inline QString frametrail_theme() {
    using namespace ft::ui;
    auto css=QStringLiteral(R"(
        QWidget { color:@text; font-family:'Segoe UI Variable Text','Segoe UI'; font-size:14px;
            selection-background-color:@accentSubtle; selection-color:@text; }
        QMainWindow, QWidget#shell { background:@window; }
        QLabel { background:transparent; }
        QLabel#title { font-size:20px; font-weight:600; }
        QLabel#subtitle, QLabel#source, QLabel[role="muted"] { color:@textSecondary; }
        QLabel[role="caption"], QLabel#details { color:@textTertiary; font-size:12px; }
        QLabel[role="section"] { color:@text; font-size:14px; font-weight:600; padding-top:4px; }
        QLabel#state, QLabel#liveStatus, QLabel#analysisStatus, QLabel#cacheStatus { color:@textSecondary; font-size:13px; }
        QLabel[role="badge"] { color:@textSecondary; background:@control; border:1px solid @strokeControl; border-radius:11px;
            padding:3px 10px; font-size:12px; }
        QLabel#workspaceActivity { background:transparent; border:none; color:@textTertiary; font-size:12px; padding:2px 0; }
        QLabel#workspaceActivity[busy="true"] { color:@accent; }
        QLabel#brandName { font-size:15px; font-weight:600; }
        QStackedWidget#workspacePages { background:transparent; }
        QFrame#workspaceRail { background:@pane; border:none; border-right:1px solid @stroke; }
        QFrame#inspector, QFrame#card { background:@card; border:1px solid @stroke; border-radius:8px; }
        QFrame#transportBar, QFrame#studioToolbar { background:@card; border:1px solid @stroke; border-radius:8px; }
        QFrame#navIndicator { background:@accent; border:none; border-radius:2px; }
        QFrame#divider { background:@stroke; border:none; max-height:1px; min-height:1px; }
        QScrollArea { border:none; background:transparent; }
        QScrollArea > QWidget > QWidget { background:transparent; }

        QPushButton, QToolButton { background:@control; color:@text; border:1px solid @strokeControl; border-bottom-color:#2a2a2a;
            border-radius:4px; padding:6px 14px; min-height:20px; }
        QPushButton:hover, QToolButton:hover { background:@controlHover; }
        QPushButton:pressed, QToolButton:pressed { background:@controlPressed; color:@textSecondary; }
        QPushButton:focus, QToolButton:focus { border:1px solid @strokeStrong; }
        QPushButton:disabled, QToolButton:disabled { color:@textDisabled; background:#252525; border-color:#2e2e2e; }
        QPushButton:checked, QToolButton:checked { background:@accentSubtle; border-color:@accent; }
        QPushButton[role="primary"] { background:@accent; color:@onAccent; border:1px solid @accent; font-weight:600; }
        QPushButton[role="primary"]:hover { background:@accentHover; border-color:@accentHover; }
        QPushButton[role="primary"]:pressed { background:@accentPressed; border-color:@accentPressed; }
        QPushButton[role="primary"]:disabled { color:@textDisabled; background:#2e2e2e; border-color:#2e2e2e; }
        QPushButton[role="subtle"] { background:transparent; border-color:transparent; }
        QPushButton[role="subtle"]:hover { background:@controlHover; }
        QPushButton[role="subtle"]:checked { background:@controlHover; border-color:transparent; }
        QPushButton[role="navigation"] { text-align:left; background:transparent; border:1px solid transparent; border-radius:4px;
            padding:8px 10px 8px 12px; color:@textSecondary; }
        QPushButton[role="navigation"]:hover { background:#2a2a2a; color:@text; }
        QPushButton[role="navigation"]:checked { background:#2d2d2d; color:@text; border-color:transparent; font-weight:600; }
        QPushButton[role="navigation"]:disabled { color:@textDisabled; }

        QComboBox, QDoubleSpinBox, QLineEdit { background:@control; border:1px solid @strokeControl; border-bottom-color:#4a4a4a;
            border-radius:4px; padding:6px 10px; min-height:20px; }
        QComboBox:hover, QDoubleSpinBox:hover, QLineEdit:hover { background:@controlHover; }
        QComboBox:focus, QDoubleSpinBox:focus, QLineEdit:focus { border-bottom:2px solid @accent; }
        QComboBox:disabled, QDoubleSpinBox:disabled, QLineEdit:disabled, QCheckBox:disabled { color:@textDisabled; }
        QComboBox::drop-down { width:28px; border:0; background:transparent; }
        QComboBox::down-arrow { image:url(:/studio/down.png); width:12px; height:12px; }
        QComboBox QAbstractItemView { background:#2c2c2c; color:@text; border:1px solid @strokeControl; border-radius:6px;
            selection-background-color:@controlHover; padding:4px; outline:0; }
        QDoubleSpinBox::up-arrow { image:url(:/studio/up.png); width:10px; height:10px; }
        QDoubleSpinBox::down-arrow { image:url(:/studio/down.png); width:10px; height:10px; }
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { width:22px; border:0; background:transparent; }
        QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover { background:@controlHover; }
        QCheckBox { spacing:10px; min-height:28px; }
        QCheckBox::indicator { width:20px; height:20px; }

        QListWidget { background:transparent; border:none; outline:0; }
        QListWidget::item { padding:8px; margin:2px 0; border:1px solid transparent; border-radius:6px; color:@text; }
        QListWidget::item:hover { background:@cardHover; }
        QListWidget::item:selected { background:#303030; border-color:#3a3a3a; }
        QTextBrowser { background:@card; border:1px solid @stroke; border-radius:8px; padding:12px; color:@text; }
        QProgressBar { background:#3a3a3a; border:none; border-radius:2px; text-align:center; min-height:4px; max-height:4px; }
        QProgressBar::chunk { background:@accent; border-radius:2px; }
        QToolTip { color:@text; background:#2c2c2c; border:1px solid @strokeControl; border-radius:4px; padding:6px 8px; }
        QScrollBar:vertical { background:transparent; width:8px; margin:4px 1px; }
        QScrollBar::handle:vertical { background:#5a5a5a; min-height:32px; border-radius:3px; }
        QScrollBar::handle:vertical:hover { background:#7a7a7a; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background:transparent; }
        QSplitter::handle { background:transparent; }
        QSplitter::handle:hover { background:@strokeControl; border-radius:2px; }
        QTabWidget::pane { border:none; background:transparent; }
        QTabBar { qproperty-drawBase:0; }
        QTabBar::tab { color:@textSecondary; background:transparent; padding:6px 2px 8px 2px; margin-right:18px;
            border:none; border-bottom:3px solid transparent; }
        QTabBar::tab:selected { color:@text; font-weight:600; border-bottom:3px solid @accent; }
        QTabBar::tab:hover:!selected { color:@text; border-bottom:3px solid #4a4a4a; }
        QMenu { background:#2c2c2c; border:1px solid @strokeControl; border-radius:8px; padding:4px; }
        QMenu::item { padding:7px 22px; border-radius:4px; }
        QMenu::item:selected { background:@controlHover; }
        QMessageBox { background:#2b2b2b; }
    )");
    const auto hex=[](const QColor& c){return c.alpha()==255 ? c.name(QColor::HexRgb) : QStringLiteral("rgba(%1,%2,%3,%4)").arg(c.red()).arg(c.green()).arg(c.blue()).arg(c.alpha());};
    // Longest names first so a token never replaces the start of a longer one.
    const std::pair<const char*,QColor> tokens[]={
        {"@accentSubtle",accent_subtle()},{"@accentPressed",accent_pressed()},{"@accentHover",accent_hover()},{"@accent",accent()},
        {"@onAccent",on_accent()},{"@window",window},{"@pane",pane},{"@cardHover",card_hover},{"@card",card},
        {"@controlPressed",control_pressed},{"@controlHover",control_hover},{"@control",control},
        {"@strokeControl",stroke_control},{"@strokeStrong",stroke_strong},{"@stroke",stroke},
        {"@textSecondary",text_secondary},{"@textTertiary",text_tertiary},{"@textDisabled",text_disabled},{"@text",text}};
    for(const auto& [name,color]:tokens)css.replace(QString::fromLatin1(name),hex(color));
    return css;
}
