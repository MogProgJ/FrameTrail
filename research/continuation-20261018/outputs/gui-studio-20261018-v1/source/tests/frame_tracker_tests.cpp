#include "frametrail/frame_tracker.hpp"
#include <iostream>
#include <stdexcept>

using namespace frametrail;
void require(bool value,const char* message){if(!value)throw std::runtime_error(message);}
Frame picture(std::uint64_t sequence,bool cut=false,int exposure=0) {
    Frame frame{sequence,std::chrono::microseconds(sequence*100000),320,180,960,std::vector<std::uint8_t>(320*180*3)};
    for(int y=0;y<180;++y)for(int x=0;x<320;++x)for(int c=0;c<3;++c) {
        const int value=cut ? (x<160 ? 245-c*10 : 10+c*10) : (x<160 ? 30+c*30 : 90-c*30);
        frame.pixels[y*frame.stride+x*3+c]=std::uint8_t(value+exposure);
    }
    return frame;
}
Detection object(float bottom){return {0,.9f,140,bottom-30,180,bottom};}
int main() {
    try {
        SceneBoundary boundary;require(!boundary.observe(picture(0)).changed,"First frame was a cut");
        require(!boundary.observe(picture(1)).changed,"Stationary image was a cut");
        require(!boundary.observe(picture(2,false,20)).changed,"Uniform exposure change was a cut");
        auto small=picture(3,false,20);for(int y=0;y<10;++y)for(int x=0;x<10;++x)small.pixels[y*960+x*3]=255;
        require(!boundary.observe(small).changed,"Small moving region was a cut");
        require(boundary.observe(picture(4,true)).changed,"Strong scene change was missed");
        FrameTracker tracker;std::uint64_t first{};TrackingResult result;
        for(unsigned n=0;n<3;++n){const auto d=object(63.f+n*11);result=tracker.update(std::span(&d,1),picture(n));if(!n)first=result.objects[0].id;}
        require(result.objects[0].confirmed,"Continuous observations did not confirm");
        auto d=object(97);result=tracker.update(std::span(&d,1),picture(3,true));
        require(result.scene_boundary && result.objects[0].id!=first && !result.objects[0].confirmed && result.events.empty(),"Scene cut bridged identity or invented a crossing");
        for(const auto [n,bottom]:{std::pair{4u,108.f},std::pair{5u,97.f},std::pair{6u,84.f}}){d=object(bottom);result=tracker.update(std::span(&d,1),picture(n,true));}
        require(result.positive_to_negative==1 && result.events.size()==1,"Tracking did not recover after cut");
        const auto previous=result.objects[0].id;d=object(97);result=tracker.update(std::span(&d,1),picture(7));
        require(result.scene_boundary && result.objects[0].id>previous && result.positive_to_negative==1 && result.events.empty(),"Cut reused IDs or erased valid accumulated counts");
        Tracker gap;d=object(63);
        for(unsigned n=0;n<3;++n)gap.update(std::span(&d,1),n,std::chrono::microseconds(n*100000),320,180);
        result=gap.update(std::span(&d,1),7,std::chrono::microseconds(700000),320,180);
        require(result.objects[0].id==1 && !result.objects[0].confirmed,"Long-gap identity skipped reconfirmation");
        bool rejected{};try{boundary.observe(Frame{});}catch(const std::invalid_argument&){rejected=true;}require(rejected,"Invalid RGB frame accepted");
        std::cout<<"Scene cuts, exposure suppression, local motion, IDs, cumulative counts and gap reconfirmation passed\n";return 0;
    }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
