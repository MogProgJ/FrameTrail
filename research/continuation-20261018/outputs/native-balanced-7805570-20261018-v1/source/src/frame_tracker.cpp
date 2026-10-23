#include "frametrail/frame_tracker.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace frametrail {
SceneChange SceneBoundary::observe(const Frame& frame) {
    if(frame.width<=0 || frame.height<=0 || frame.width>std::numeric_limits<int>::max()/3 || frame.stride<frame.width*3 ||
        frame.pixels.size()<std::size_t(frame.stride)*frame.height)throw std::invalid_argument("Invalid RGB scene snapshot");
    std::array<double,32*18*3> current{};std::array<double,16*3> histogram{};
    std::array<double,3> shift{};
    for(int y=0;y<18;++y)for(int x=0;x<32;++x)for(int channel=0;channel<3;++channel) {
        double value{};
        for(int sy=0;sy<2;++sy)for(int sx=0;sx<2;++sx) {
            const auto py=std::min(frame.height-1,int((std::int64_t(y*4+sy*2+1)*frame.height)/72));
            const auto px=std::min(frame.width-1,int((std::int64_t(x*4+sx*2+1)*frame.width)/128));
            value+=frame.pixels[std::size_t(py)*frame.stride+px*3+channel]/(255.0*4);
        }
        const auto index=(y*32+x)*3+channel;current[index]=value;shift[channel]+=value-previous_[index];
        ++histogram[channel*16+std::min(15,int(value*16))];
    }
    SceneChange result;
    if(width_ && frame.width==width_ && frame.height==height_) {
        for(auto& value:shift)value/=32*18;
        for(std::size_t i=0;i<current.size();++i)result.difference+=std::abs(current[i]-previous_[i]-shift[i%3])/current.size();
        for(std::size_t i=0;i<histogram.size();++i)result.histogram_distance+=std::abs(histogram[i]-histogram_[i])/(2*32.*18*3);
        // Require both spatial and colour-distribution changes. Uniform exposure
        // changes are suppressed by removing the mean per-channel displacement.
        result.changed=result.difference>.16 && result.histogram_distance>.18;
    }else if(width_)result.changed=true;
    previous_=current;histogram_=histogram;width_=frame.width;height_=frame.height;return result;
}
TrackingResult FrameTracker::update(std::span<const Detection> detections,const Frame& frame) {
    if(sequence_ && frame.sequence<=*sequence_)throw std::invalid_argument("Tracking needs increasing frame sequences");
    if(timestamp_ && frame.timestamp && *frame.timestamp<*timestamp_)throw std::invalid_argument("Tracking timestamps must not move backwards");
    const auto begin=std::chrono::steady_clock::now();const auto scene=boundary_.observe(frame);
    if(scene.changed)tracker_.reset_continuity();
    auto result=tracker_.update(detections,frame.sequence,frame.timestamp,frame.width,frame.height);
    sequence_=frame.sequence;timestamp_=frame.timestamp;
    result.scene_boundary=scene.changed;result.scene_difference=scene.difference;result.scene_histogram_distance=scene.histogram_distance;
    result.elapsed_ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-begin).count();return result;
}
}
