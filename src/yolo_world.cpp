#include "frametrail/detector.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace frametrail::yolo_world {
Input preprocess(const Frame& frame) {
    constexpr int size=640,plane=size*size;
    if(frame.width<=0 || frame.height<=0 || frame.stride<=0 ||
       std::int64_t(frame.stride)<std::int64_t(frame.width)*3 ||
       frame.pixels.size()<std::uint64_t(frame.stride)*frame.height)
        throw std::invalid_argument("Invalid RGB frame for YOLO-World");
    Input out;
    out.ratio=std::min(double(size)/frame.width,double(size)/frame.height);
    // Python round uses ties-to-even, unlike std::round. Match the export reference.
    out.resized_width=std::clamp(int(std::nearbyint(frame.width*out.ratio)),1,size);
    out.resized_height=std::clamp(int(std::nearbyint(frame.height*out.ratio)),1,size);
    out.pad_x=(size-out.resized_width)/2;out.pad_y=(size-out.resized_height)/2;
    out.tensor.assign(3*plane,114.f/255.f);
    for(int y=0;y<out.resized_height;++y) {
        const double sy=std::clamp((y+.5)*frame.height/out.resized_height-.5,0.0,double(frame.height-1));
        const int y0=int(sy),y1=std::min(y0+1,frame.height-1);const double fy=sy-y0;
        for(int x=0;x<out.resized_width;++x) {
            const double sx=std::clamp((x+.5)*frame.width/out.resized_width-.5,0.0,double(frame.width-1));
            const int x0=int(sx),x1=std::min(x0+1,frame.width-1);const double fx=sx-x0;
            for(int c=0;c<3;++c) {
                const auto pixel=[&](int px,int py){return frame.pixels[std::size_t(py)*frame.stride+std::size_t(px)*3+c];};
                const double top=pixel(x0,y0)*(1-fx)+pixel(x1,y0)*fx;
                const double bottom=pixel(x0,y1)*(1-fx)+pixel(x1,y1)*fx;
                out.tensor[c*plane+(y+out.pad_y)*size+x+out.pad_x]=float(std::round(top*(1-fy)+bottom*fy))/255.f;
            }
        }
    }
    return out;
}
std::vector<Detection> postprocess(std::span<const float> output,const Input& input,
    int width,int height,float confidence,float nms_iou,DetectorModel model) {
    const auto classes=model_classes(model);
    const int class_count=model_class_count(model);
    constexpr int candidates=8400;
    if(output.size()!=std::size_t(candidates)*(4+class_count) || !std::isfinite(input.ratio) || input.ratio<=0 ||
       width<=0 || height<=0 || input.pad_x<0 || input.pad_y<0 ||
       !std::isfinite(confidence) || confidence<=0 || confidence>1 || !std::isfinite(nms_iou) || nms_iou<=0 || nms_iou>1)
        throw std::invalid_argument("Invalid YOLO-World output, geometry or thresholds");
    std::vector<Detection> proposals;
    for(int row=0;row<candidates;++row) {
        int best=-1;float score=0;
        bool valid=true;
        for(int cls=0;cls<class_count;++cls) {
            const float value=output[std::size_t(4+cls)*candidates+row];
            if(!std::isfinite(value) || value<0 || value>1){valid=false;break;}
            if(value>score){score=value;best=cls;}
        }
        if(!valid || best<0 || score<confidence)continue;
        const double cx=(output[row]-input.pad_x)/input.ratio;
        const double cy=(output[candidates+row]-input.pad_y)/input.ratio;
        const double w=output[2*candidates+row]/input.ratio,h=output[3*candidates+row]/input.ratio;
        if(!std::isfinite(cx) || !std::isfinite(cy) || !std::isfinite(w) || !std::isfinite(h) || w<=0 || h<=0)continue;
        Detection box{classes[best],score,float(std::clamp(cx-w/2,0.0,double(width))),float(std::clamp(cy-h/2,0.0,double(height))),
            float(std::clamp(cx+w/2,0.0,double(width))),float(std::clamp(cy+h/2,0.0,double(height)))};
        if(box.right>box.left && box.bottom>box.top)proposals.push_back(box);
    }
    std::stable_sort(proposals.begin(),proposals.end(),[](const auto& a,const auto& b){return a.confidence>b.confidence;});
    std::vector<Detection> kept;
    for(const auto& box:proposals) {
        if(std::none_of(kept.begin(),kept.end(),[&](const auto& prior){
            if(prior.class_id!=box.class_id)return false;
            const float intersection=std::max(0.f,std::min(prior.right,box.right)-std::max(prior.left,box.left))*
                std::max(0.f,std::min(prior.bottom,box.bottom)-std::max(prior.top,box.top));
            const float total=(prior.right-prior.left)*(prior.bottom-prior.top)+(box.right-box.left)*(box.bottom-box.top)-intersection;
            return intersection/total>nms_iou;
        }))kept.push_back(box);
        if(kept.size()==100)break;
    }
    return kept;
}
}
