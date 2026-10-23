#include "frametrail/detector.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace frametrail::rfdetr {
std::vector<float> preprocess(const Frame& frame) {
    if(frame.width<=0 || frame.height<=0 || frame.stride<=0 ||
       std::int64_t(frame.stride)<std::int64_t(frame.width)*3 ||
       frame.pixels.size()<std::uint64_t(frame.stride)*frame.height)
        throw std::invalid_argument("Invalid RGB frame for RF detection");
    constexpr int plane=input_size*input_size;
    constexpr float mean[]{.485f,.456f,.406f},stddev[]{.229f,.224f,.225f};
    std::vector<float> tensor(3*plane);
    for(int y=0;y<input_size;++y) {
        const float sy=std::clamp((float(y)+.5f)*float(frame.height)/input_size-.5f,0.f,float(frame.height-1));
        const int y0=int(sy),y1=std::min(y0+1,frame.height-1);const float fy=sy-y0;
        for(int x=0;x<input_size;++x) {
            const float sx=std::clamp((float(x)+.5f)*float(frame.width)/input_size-.5f,0.f,float(frame.width-1));
            const int x0=int(sx),x1=std::min(x0+1,frame.width-1);const float fx=sx-x0;
            for(int c=0;c<3;++c) {
                const auto pixel=[&](int px,int py){return frame.pixels[std::size_t(py)*frame.stride+std::size_t(px)*3+c]/255.f;};
                const float top=pixel(x0,y0)*(1-fx)+pixel(x1,y0)*fx;
                const float bottom=pixel(x0,y1)*(1-fx)+pixel(x1,y1)*fx;
                tensor[c*plane+y*input_size+x]=((top*(1-fy)+bottom*fy)-mean[c])/stddev[c];
            }
        }
    }
    return tensor;
}
std::vector<Detection> postprocess(std::span<const float> output,int width,int height,float confidence,float nms_iou) {
    if(output.size()!=std::size_t(queries)*attributes || width<=0 || height<=0 ||
       !std::isfinite(confidence) || confidence<=0 || confidence>1 ||
       !std::isfinite(nms_iou) || nms_iou<=0 || nms_iou>1 ||
       !std::all_of(output.begin(),output.end(),[](float v){return std::isfinite(v);}))
        throw std::invalid_argument("Invalid RF output/geometry/threshold contract");
    struct Score{int query,cid;float value;};std::vector<Score> scores;
    for(int q=0;q<queries;++q)for(int cid=0;cid<recognition_classes;++cid) {
        const float logit=output[std::size_t(q)*attributes+4+cid];
        const float p=logit>=0 ? 1.f/(1.f+std::exp(-logit)):std::exp(logit)/(1.f+std::exp(logit));
        if(p>=confidence)scores.push_back({q,cid,p});
    }
    const auto order=[](const Score& a,const Score& b){return a.value!=b.value ? a.value>b.value:(a.query!=b.query ? a.query<b.query:a.cid<b.cid);};
    if(scores.size()>300){std::partial_sort(scores.begin(),scores.begin()+300,scores.end(),order);scores.resize(300);}
    else std::sort(scores.begin(),scores.end(),order);
    std::vector<Detection> kept;
    const auto overlap=[](const Detection& a,const Detection& b){
        const float area=std::max(0.f,std::min(a.right,b.right)-std::max(a.left,b.left))*std::max(0.f,std::min(a.bottom,b.bottom)-std::max(a.top,b.top));
        return area/((a.right-a.left)*(a.bottom-a.top)+(b.right-b.left)*(b.bottom-b.top)-area);
    };
    for(const auto& s:scores) {
        const auto* b=output.data()+std::size_t(s.query)*attributes;
        if(b[2]<=0 || b[3]<=0)continue;
        Detection d{s.cid,s.value,std::clamp((b[0]-b[2]/2)*width,0.f,float(width)),std::clamp((b[1]-b[3]/2)*height,0.f,float(height)),std::clamp((b[0]+b[2]/2)*width,0.f,float(width)),std::clamp((b[1]+b[3]/2)*height,0.f,float(height))};
        if(d.right<=d.left || d.bottom<=d.top)continue;
        if(std::none_of(kept.begin(),kept.end(),[&](const Detection& p){return p.class_id==d.class_id && overlap(p,d)>nms_iou;}))kept.push_back(d);
        if(kept.size()==100)break;
    }
    return kept;
}
}
