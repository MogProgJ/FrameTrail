#pragma once
#include <QIcon>
#include <QApplication>
#include <QResource>
#include <QProxyStyle>
#include <QStyleOption>
#include <QPainter>
#include <QPixmap>
#include <QPainterPath>
#include <QPushButton>
#include <QLabel>
#include <QHBoxLayout>

// Resolution-independent line icons drawn by Qt; no external font or asset dependency.
inline QIcon studio_icon(const QString& name, const QColor& color=QColor("#bab7d0")) {
    QPixmap p(48,48);p.fill(Qt::transparent);QPainter q(&p);q.scale(2,2);q.setRenderHint(QPainter::Antialiasing);q.setPen(QPen(color,1.6,Qt::SolidLine,Qt::RoundCap,Qt::RoundJoin));
    if(name=="open") {q.drawRoundedRect(QRectF(3,6,18,15),3,3);q.drawLine(8,6,8,3);q.drawLine(8,3,14,3);}
    else if(name=="analyse") {q.drawRoundedRect(QRectF(3,3,18,18),3,3);q.drawLine(7,16,7,12);q.drawLine(12,16,12,8);q.drawLine(17,16,17,6);}
    else if(name=="camera") {q.drawRoundedRect(QRectF(3,6,18,14),3,3);q.drawEllipse(QPointF(12,13),4,4);q.drawLine(7,6,9,3);q.drawLine(9,3,15,3);q.drawLine(15,3,17,6);}
    else if(name=="inspector") {q.drawRoundedRect(QRectF(3,3,18,18),3,3);q.drawLine(15,3,15,21);q.drawLine(18,7,19,7);q.drawLine(18,11,19,11);}
    else if(name=="play") {QPainterPath a;a.moveTo(8,5);a.lineTo(19,12);a.lineTo(8,19);a.closeSubpath();q.drawPath(a);}
    else if(name=="stop")q.drawRoundedRect(QRectF(6,6,12,12),2,2);
    else if(name=="replay") {q.drawArc(QRectF(5,5,14,14),40*16,285*16);q.drawLine(5,4,5,10);q.drawLine(5,10,11,10);}
    else if(name=="smooth") {q.drawRoundedRect(QRectF(3,3,18,18),3,3);q.drawLine(7,5,7,19);q.drawLine(17,5,17,19);q.drawLine(3,9,7,9);q.drawLine(17,15,21,15);}
    else if(name=="guide") {q.drawRoundedRect(QRectF(4,3,16,18),2,2);q.drawLine(8,3,8,21);q.drawLine(11,8,16,8);q.drawLine(11,12,16,12);}
    else {q.drawLine(3,9,3,3);q.drawLine(3,3,9,3);q.drawLine(15,3,21,3);q.drawLine(21,3,21,9);q.drawLine(21,15,21,21);q.drawLine(21,21,15,21);q.drawLine(9,21,3,21);q.drawLine(3,21,3,15);q.setBrush(color);q.drawEllipse(QPointF(12,12),2.2,2.2);}
    return QIcon(p);
}
inline void studio_button(QPushButton* button,const QString& icon) {button->setIcon(studio_icon(icon,button->property("role").toString()=="primary"?QColor("#282239"):QColor("#bab7d0")));button->setIconSize(QSize(16,16));button->setCursor(Qt::PointingHandCursor);}
inline void studio_heading(QHBoxLayout* header) {auto* mark=new QLabel;mark->setPixmap(studio_icon("brand",QColor("#c1baff")).pixmap(24,24));mark->setFixedSize(30,30);header->insertWidget(0,mark);}

class StudioStyle final : public QProxyStyle {
public:
    StudioStyle():QProxyStyle(QStringLiteral("Fusion")){setObjectName(QStringLiteral("frametrailStudio"));}
    void drawPrimitive(PrimitiveElement element,const QStyleOption* option,QPainter* painter,const QWidget* widget=nullptr) const override {
        if(element==PE_IndicatorArrowDown || element==PE_IndicatorArrowUp || element==PE_IndicatorSpinDown || element==PE_IndicatorSpinUp) {
            painter->save();painter->setRenderHint(QPainter::Antialiasing);
            painter->setPen(QPen(option->state&State_Enabled?QColor("#bdb9cd"):QColor("#666572"),1.5,Qt::SolidLine,Qt::RoundCap,Qt::RoundJoin));
            const auto c=QPointF(option->rect.center());const double dy=(element==PE_IndicatorArrowUp || element==PE_IndicatorSpinUp)?-1:1;
            painter->drawLine(c+QPointF(-3,-dy*1.5),c+QPointF(0,dy*1.5));painter->drawLine(c+QPointF(0,dy*1.5),c+QPointF(3,-dy*1.5));painter->restore();return;
        }
        if(element==PE_IndicatorCheckBox) {
            painter->save();painter->setRenderHint(QPainter::Antialiasing);const bool on=option->state&State_On,enabled=option->state&State_Enabled;
            const auto r=QRectF(option->rect).adjusted(1,1,-1,-1);painter->setPen(QPen(enabled?QColor(on?"#c1baff":"#656371"):QColor("#494853"),1));painter->setBrush(QColor(enabled&&on?"#c1baff":"#1a1b20"));painter->drawRoundedRect(r,4,4);
            if(on){painter->setPen(QPen(enabled?QColor("#272139"):QColor("#777482"),1.8,Qt::SolidLine,Qt::RoundCap,Qt::RoundJoin));const auto c=r.center();painter->drawLine(c+QPointF(-4,0),c+QPointF(-1,3));painter->drawLine(c+QPointF(-1,3),c+QPointF(4,-3));}
            painter->restore();return;
        }
        QProxyStyle::drawPrimitive(element,option,painter,widget);
    }
};
inline void install_studio_style(){if(qApp->style()->objectName()!=QStringLiteral("frametrailStudio")){Q_INIT_RESOURCE(studio_assets);QApplication::setStyle(new StudioStyle);}}
