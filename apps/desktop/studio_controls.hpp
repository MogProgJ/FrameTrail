#pragma once
#include "fluent_icons.hpp"
#include "theme.hpp"
#include <QIcon>
#include <QApplication>
#include <QEvent>
#include <QFrame>
#include <QHash>
#include <QResource>
#include <QProxyStyle>
#include <QStyleOption>
#include <QPainter>
#include <QPixmap>
#include <QPainterPath>
#include <QPushButton>
#include <QLabel>
#include <QHBoxLayout>
#include <QGraphicsOpacityEffect>
#include <QPropertyAnimation>

// Fluent UI System Icons (see fluent_icons.hpp), parsed once into 20 x 20 painter paths.
inline const QPainterPath& fluent_path(QString name) {
    if(name==QStringLiteral("analyse"))name=QStringLiteral("analysis");
    if(name==QStringLiteral("smooth"))name=QStringLiteral("playback");
    static QHash<QString,QPainterPath> cache;
    if(const auto found=cache.constFind(name);found!=cache.cend())return *found;
    QPainterPath path;path.setFillRule(Qt::WindingFill);
    for(const auto& [key,data]:fluent_icon_paths) {
        if(QLatin1StringView(key.data(),qsizetype(key.size()))!=name)continue;
        const auto text=QString::fromLatin1(data.data(),qsizetype(data.size()));
        qsizetype i=0;
        const auto number=[&]{
            while(i<text.size() && (text[i]==QLatin1Char(' ') || text[i]==QLatin1Char(',')))++i;
            const auto start=i;
            while(i<text.size() && (text[i].isDigit() || text[i]==QLatin1Char('.') || text[i]==QLatin1Char('-') || text[i]==QLatin1Char('e')))++i;
            return text.mid(start,i-start).toDouble();
        };
        const auto point=[&]{const double x=number();return QPointF(x,number());};
        while(i<text.size()) {
            const auto command=text[i++].toLatin1();
            if(command=='M')path.moveTo(point());
            else if(command=='L')path.lineTo(point());
            else if(command=='Q'){const auto c=point();path.quadTo(c,point());}
            else if(command=='C'){const auto c1=point();const auto c2=point();path.cubicTo(c1,c2,point());}
            else if(command=='Z')path.closeSubpath();
        }
        break;
    }
    return *cache.insert(name,path);
}
// trailing: transparent space after the glyph. Qt draws a fixed 4 px gap between a button's icon and
// text; the extra space gives Windows 11 spacing (8 px, or 12 px in the navigation pane).
inline QPixmap fluent_pixmap(const QString& name,const QColor& color,int size=20,qreal ratio=2.,int trailing=0) {
    QPixmap pixmap(QSize(size+trailing,size)*ratio);pixmap.setDevicePixelRatio(ratio);pixmap.fill(Qt::transparent);
    QPainter painter(&pixmap);painter.setRenderHint(QPainter::Antialiasing);painter.scale(size/20.,size/20.);
    painter.fillPath(fluent_path(name),color);
    return pixmap;
}
inline QIcon studio_icon(const QString& name,const QColor& color=ft::ui::text,const QColor& checked=QColor(),int trailing=0) {
    QIcon icon;
    for(const int size:{16,18,20,24}) {
        icon.addPixmap(fluent_pixmap(name,color,size,2.,trailing),QIcon::Normal,QIcon::Off);
        icon.addPixmap(fluent_pixmap(name,ft::ui::text_disabled,size,2.,trailing),QIcon::Disabled,QIcon::Off);
        icon.addPixmap(fluent_pixmap(name,checked.isValid()?checked:color,size,2.,trailing),QIcon::Normal,QIcon::On);
    }
    return icon;
}
inline void studio_button(QPushButton* button,const QString& icon) {
    if(!button)return;
    const auto role=button->property("role").toString();
    const auto color=role==QStringLiteral("primary")?ft::ui::on_accent():role==QStringLiteral("navigation")?ft::ui::text_secondary:ft::ui::text;
    const int trailing=button->text().isEmpty()?0:role==QStringLiteral("navigation")?8:4;
    button->setIcon(studio_icon(icon,color,role==QStringLiteral("navigation")?ft::ui::accent():QColor(),trailing));
    button->setIconSize(QSize(18+trailing,18));button->setCursor(Qt::PointingHandCursor);
}
inline QLabel* brand_mark(int size=24) {
    auto* mark=new QLabel;mark->setPixmap(fluent_pixmap(QStringLiteral("brand"),ft::ui::accent(),size));mark->setFixedSize(size+6,size+6);
    mark->setAlignment(Qt::AlignCenter);return mark;
}
// Short confirmation at the bottom of a window that fades away by itself.
inline void show_toast(QWidget* window,const QString& text,const QString& icon=QStringLiteral("check")) {
    if(!window)return;
    if(auto* old=window->findChild<QFrame*>(QStringLiteral("toast"),Qt::FindDirectChildrenOnly))old->deleteLater();
    auto* toast=new QFrame(window);toast->setObjectName(QStringLiteral("toast"));toast->setAttribute(Qt::WA_TransparentForMouseEvents);
    auto* layout=new QHBoxLayout(toast);layout->setContentsMargins(14,10,16,10);layout->setSpacing(10);
    auto* mark=new QLabel;mark->setPixmap(fluent_pixmap(icon,ft::ui::success,18));layout->addWidget(mark);
    auto* label=new QLabel(text);label->setTextFormat(Qt::PlainText);layout->addWidget(label);
    toast->adjustSize();toast->move((window->width()-toast->width())/2,window->height()-toast->height()-48);toast->show();toast->raise();
    auto* effect=new QGraphicsOpacityEffect(toast);toast->setGraphicsEffect(effect);
    auto* fade=new QPropertyAnimation(effect,"opacity",toast);fade->setDuration(3200);
    fade->setKeyValueAt(0,0.);fade->setKeyValueAt(.06,1.);fade->setKeyValueAt(.85,1.);fade->setKeyValueAt(1,0.);
    QObject::connect(fade,&QPropertyAnimation::finished,toast,&QObject::deleteLater);fade->start(QAbstractAnimation::DeleteWhenStopped);
}
// Fade a page in when switching sections.
inline void fade_in(QWidget* page,int duration=170) {
    if(!page || page->graphicsEffect())return;
    auto* effect=new QGraphicsOpacityEffect(page);effect->setOpacity(0);page->setGraphicsEffect(effect);
    auto* fade=new QPropertyAnimation(effect,"opacity",page);fade->setDuration(duration);fade->setStartValue(0.);fade->setEndValue(1.);fade->setEasingCurve(QEasingCurve::OutCubic);
    QObject::connect(fade,&QPropertyAnimation::finished,page,[page]{page->setGraphicsEffect(nullptr);});fade->start(QAbstractAnimation::DeleteWhenStopped);
}
// Standalone windows show the brand mark; the shared workspace hides it when embedding a page.
inline void studio_heading(QHBoxLayout* header) {header->insertWidget(0,brand_mark());}

// Selection marker for navigation buttons: a short accent bar on the left edge, as in Windows 11.
class NavIndicator final : public QObject {
public:
    explicit NavIndicator(QPushButton* button):QObject(button),button_(button),bar_(new QFrame(button)) {
        bar_->setObjectName(QStringLiteral("navIndicator"));bar_->setAttribute(Qt::WA_TransparentForMouseEvents);
        bar_->setVisible(button->isChecked());button->installEventFilter(this);
        QObject::connect(button,&QPushButton::toggled,bar_,&QWidget::setVisible);
    }
protected:
    bool eventFilter(QObject*,QEvent* event) override {
        if(event->type()==QEvent::Resize || event->type()==QEvent::Show)bar_->setGeometry(0,(button_->height()-16)/2,3,16);
        return false;
    }
private:
    QPushButton* button_;
    QFrame* bar_;
};

class StudioStyle final : public QProxyStyle {
public:
    StudioStyle():QProxyStyle(QStringLiteral("Fusion")){setObjectName(QStringLiteral("frametrailStudio"));}
    int styleHint(StyleHint hint,const QStyleOption* option=nullptr,const QWidget* widget=nullptr,QStyleHintReturn* data=nullptr) const override {
        if(hint==SH_Slider_AbsoluteSetButtons)return Qt::LeftButton; // Click on a timeline jumps there.
        return QProxyStyle::styleHint(hint,option,widget,data);
    }
    void drawPrimitive(PrimitiveElement element,const QStyleOption* option,QPainter* painter,const QWidget* widget=nullptr) const override {
        if(element==PE_IndicatorArrowDown || element==PE_IndicatorArrowUp || element==PE_IndicatorSpinDown || element==PE_IndicatorSpinUp) {
            painter->save();painter->setRenderHint(QPainter::Antialiasing);
            painter->setPen(QPen(option->state&State_Enabled?ft::ui::text_secondary:ft::ui::text_disabled,1.5,Qt::SolidLine,Qt::RoundCap,Qt::RoundJoin));
            const auto c=QPointF(option->rect.center());const double dy=(element==PE_IndicatorArrowUp || element==PE_IndicatorSpinUp)?-1:1;
            painter->drawLine(c+QPointF(-3.5,-dy*1.75),c+QPointF(0,dy*1.75));painter->drawLine(c+QPointF(0,dy*1.75),c+QPointF(3.5,-dy*1.75));painter->restore();return;
        }
        if(element==PE_IndicatorCheckBox) {
            painter->save();painter->setRenderHint(QPainter::Antialiasing);
            const bool on=option->state&State_On,enabled=option->state&State_Enabled,hover=option->state&State_MouseOver;
            const auto r=QRectF(option->rect).adjusted(1.5,1.5,-1.5,-1.5);
            if(on){painter->setPen(Qt::NoPen);painter->setBrush(enabled?(hover?ft::ui::accent_hover():ft::ui::accent()):QColor("#3a3a3a"));}
            else{painter->setPen(QPen(enabled?QColor("#9a9a9a"):QColor("#4a4a4a"),1));painter->setBrush(hover&&enabled?QColor("#2f2f2f"):QColor("#262626"));}
            painter->drawRoundedRect(r,4,4);
            if(on){
                painter->setPen(QPen(enabled?ft::ui::on_accent():ft::ui::text_disabled,1.6,Qt::SolidLine,Qt::RoundCap,Qt::RoundJoin));
                const auto c=r.center();QPainterPath tick;tick.moveTo(c+QPointF(-4,0.5));tick.lineTo(c+QPointF(-1.2,3.2));tick.lineTo(c+QPointF(4.2,-2.8));
                painter->setBrush(Qt::NoBrush);painter->drawPath(tick);
            }
            painter->restore();return;
        }
        QProxyStyle::drawPrimitive(element,option,painter,widget);
    }
};
inline void install_studio_style(){if(qApp->style()->objectName()!=QStringLiteral("frametrailStudio")){Q_INIT_RESOURCE(studio_assets);QApplication::setStyle(new StudioStyle);}}
