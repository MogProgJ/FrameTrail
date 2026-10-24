#pragma once
#include "theme.hpp"
#include <QPainter>
#include <QSlider>
#include <algorithm>
#include <cmath>
#include <vector>

// Video position slider with an activity strip: bars above the track show how many objects were
// detected at each moment seen so far, coloured by the most frequent object type.
class TimelineSlider final : public QSlider {
public:
    explicit TimelineSlider(QWidget* parent=nullptr):QSlider(Qt::Horizontal,parent) {setMinimumHeight(36);}
    void reset_activity() {std::fill(bins_.begin(),bins_.end(),Bin{});peak_=1;update();}
    void add_activity(double fraction,int objects,int dominant_class) {
        if(!std::isfinite(fraction) || objects<=0)return;
        auto& bin=bins_[std::size_t(std::clamp(int(fraction*double(bins_.size())),0,int(bins_.size())-1))];
        if(objects>=bin.objects){bin.objects=objects;bin.dominant=dominant_class;}
        if(objects>peak_)peak_=objects;
        update();
    }
protected:
    void paintEvent(QPaintEvent* event) override {
        {
            QPainter painter(this);painter.setRenderHint(QPainter::Antialiasing);
            const double left=9,right=width()-9.,base=height()/2.-5,room=std::max(4.,base-3);
            const double step=(right-left)/double(bins_.size());
            for(std::size_t i=0;i<bins_.size();++i) {
                if(!bins_[i].objects)continue;
                auto color=ft::ui::category_color(bins_[i].dominant);color.setAlpha(isEnabled()?210:90);
                const double h=std::max(2.,room*std::sqrt(double(bins_[i].objects)/double(peak_)));
                painter.setPen(Qt::NoPen);painter.setBrush(color);
                painter.drawRoundedRect(QRectF(left+i*step+.5,base-h,std::max(1.,step-1.),h),1,1);
            }
        }
        QSlider::paintEvent(event);
    }
private:
    struct Bin {int objects{},dominant{};};
    std::vector<Bin> bins_=std::vector<Bin>(180);
    int peak_{1};
};
