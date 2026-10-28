#include "frametrail/tracker.hpp"
#include <iostream>
#include <limits>
#include <stdexcept>
#include <cmath>
#include <tuple>

using namespace frametrail;
using namespace std::chrono_literals;
namespace {
void require(bool b, const char* message) { if (!b) throw std::runtime_error(message); }
Detection box(double x, double y, int id = 0) {
    return {id,0.9f,float(x*1000-40),float(y*1000-120),float(x*1000+40),float(y*1000)};
}
struct Run {
    Tracker tracker;
    std::uint64_t sequence{};
    Run(TrackingOptions options = {}) : tracker(std::move(options)) {}
    TrackingResult at(std::initializer_list<Detection> boxes) {
        const auto n = sequence++;
        return tracker.update(std::span(boxes.begin(),boxes.size()),n,std::chrono::microseconds(n*100000),1000,1000);
    }
};
template<class F> void rejects(F f, const char* message) {
    try { f(); } catch (const std::invalid_argument&) { return; }
    throw std::runtime_error(message);
}
void run() {
    Run r;
    const auto id = r.at({box(.5,.35)}).objects[0].id;
    require(!r.at({box(.5,.41)}).objects[0].confirmed,"Track confirmed too early");
    require(r.at({box(.5,.47)}).objects[0].confirmed,"Track did not confirm on observation three");
    auto crossing = r.at({box(.5,.54)});
    require(crossing.events.size()==1 && crossing.events[0].track_id==id && crossing.events[0].sequence==3 &&
        crossing.events[0].timestamp==300ms && crossing.negative_to_positive==1,"Single crossing identity/timing incorrect");
    require(std::abs(crossing.events[0].position.y-.5)<1e-8,"Crossing point missed line");
    for (double y : {.49,.51,.495,.505,.49}) require(r.at({box(.5,y)}).events.empty(),"Deadband jitter emitted a duplicate");
    r.at({box(.5,.60)}); // Move away to re-arm.
    r.at({box(.5,.54)});
    auto reverse = r.at({box(.5,.47)});
    require(reverse.events.size()==1 && reverse.positive_to_negative==1 && reverse.events[0].id==2,"Repeat reverse crossing failed");
    require(r.at({box(.5,.52)}).events.empty(),"Crossing re-armed immediately");
    r.at({box(.5,.58)});
    r.at({box(.5,.52)});
    require(r.at({box(.5,.46)}).positive_to_negative==2,"Later re-armed crossing failed");

    TrackingOptions directed; directed.line->direction=CrossingDirection::positive_to_negative;
    Run d(directed);
    for (double y : {.35,.41,.47,.54,.60,.54}) require(d.at({box(.5,y)}).events.empty(),"Direction filter counted forward motion");
    require(d.at({box(.5,.47)}).positive_to_negative==1,"Direction filter rejected reverse motion");

    Run outside;
    for (double y : {.35,.41,.47,.54}) require(outside.at({box(.95,y)}).events.empty(),"Crossing outside finite line was counted");

    TrackingOptions diagonal; diagonal.line->a={.2,.2}; diagonal.line->b={.8,.8};
    Run diag(diagonal);
    for (double y : {.30,.36,.42,.48}) diag.at({box(.5,y)});
    require(diag.at({box(.5,.55)}).events.size()==1,"Diagonal finite crossing failed");
    TrackingOptions reversed; reversed.line->a={.9,.5}; reversed.line->b={.1,.5};
    Run reversed_run(reversed);
    for (double y : {.35,.41,.47}) reversed_run.at({box(.5,y)});
    require(reversed_run.at({box(.5,.54)}).positive_to_negative==1,"Endpoint order did not reverse direction");

    Run brief;
    auto initial=brief.at({box(.5,.35)}).objects[0].id;
    brief.at({box(.5,.41)}); brief.at({box(.5,.47)}); brief.at({});
    auto resumed=brief.at({box(.5,.59)});
    require(resumed.objects[0].id==initial && resumed.events.size()==1,"Brief miss did not retain identity and crossing");
    Run gap;
    gap.at({box(.5,.35)});gap.at({box(.5,.41)});gap.at({box(.5,.47)});
    gap.at({});gap.at({});gap.at({});
    require(gap.at({box(.5,.60)}).events.empty(),"Long occlusion invented a crossing");
    for (int i=0;i<8;++i) gap.at({});
    require(gap.at({box(.5,.60)}).objects[0].id!=1,"Lost track never expired");

    Run nearby;
    auto pair=nearby.at({box(.35,.35),box(.65,.35)});
    const auto left=pair.objects[0].id,right=pair.objects[1].id;
    nearby.at({box(.60,.41),box(.40,.41)}); // Detection order reverses.
    pair=nearby.at({box(.45,.47),box(.55,.47)});
    require(pair.objects[0].id==left && pair.objects[1].id==right,"Nearby objects switched identities");
    pair=nearby.at({box(.50,.54),box(.50,.54)});
    require(pair.events.size()==2 && pair.objects[0].id!=pair.objects[1].id,"Assignment reused a track for two detections");
    pair=nearby.at({box(.45,.60),box(.55,.60)});
    require(pair.objects[0].id==right && pair.objects[1].id==left,"Predicted motion did not preserve crossing identities");

    Run classes;
    classes.at({box(.5,.35)});
    require(classes.at({box(.5,.35,2)}).objects[0].id!=1,"Class mismatch reused an identity");
    require(classes.at({box(.5,.35,16)}).objects.empty(),"Unselected class was tracked");
    Run flicker; // A car briefly labelled truck keeps its identity and class; a lasting change settles on truck.
    const auto car=flicker.at({box(.5,.35,2)}).objects[0].id;
    flicker.at({box(.5,.37,2)});
    auto relabelled=flicker.at({box(.5,.39,7)});
    require(relabelled.objects.size()==1 && relabelled.objects[0].id==car && relabelled.objects[0].detection.class_id==2,
        "Car/truck flicker split the track or changed its class");
    flicker.at({box(.5,.41,7)});
    relabelled=flicker.at({box(.5,.43,7)});
    require(relabelled.objects[0].id==car && relabelled.objects[0].detection.class_id==7,"Lasting class change did not settle");
    require(related_classes(2,7) && related_classes(16,15) && !related_classes(0,2),"Related class table wrong");
    TrackingOptions sampled; sampled.frame_step=5; Tracker every_fifth(sampled); // No timestamps: gaps count frames.
    std::uint64_t first{};std::uint64_t counted{};
    for(int k=0;k<6;++k) {
        const auto observed=box(.5,.35+.06*k);
        const auto result=every_fifth.update(std::span(&observed,1),std::uint64_t(k*5),std::nullopt,1000,1000);
        if(k==0)first=result.objects[0].id;
        require(result.objects[0].id==first,"Frame step broke a track across sampled frames");
        counted=result.negative_to_positive;
    }
    require(counted==1,"Frame step lost the crossing");
    rejects([]{TrackingOptions o;o.frame_step=0;Tracker t(o);},"Frame step 0 accepted");
    TrackingOptions no_line;no_line.line.reset(); Run ids_only(no_line);
    for(double y:{.35,.41,.47,.54}) require(ids_only.at({box(.5,y)}).events.empty(),"Disabled rule produced events");

    Tracker unknown;
    auto b=box(.5,.35);
    auto output=unknown.update(std::span(&b,1),0,{},1000,1000);
    b=box(.5,.41);unknown.update(std::span(&b,1),1,{},1000,1000);
    b=box(.5,.47);unknown.update(std::span(&b,1),2,{},1000,1000);
    b=box(.5,.54);output=unknown.update(std::span(&b,1),3,{},1000,1000);
    require(output.events.size()==1 && !output.events[0].timestamp,"Missing timestamp was fabricated");
    for (std::uint64_t n=4;n<40;++n) output=unknown.update(std::span(&b,1),n,{},1000,1000);
    require(output.objects[0].trail.size()==20,"Trail storage grew unbounded");
    require(unknown.update({},60,{},1000,1000).objects.empty(),"Missing detections painted predicted boxes");
    require(unknown.update(std::span(&b,1),61,{},1000,1000).objects[0].id!=1,"Sequence-based expiry failed");

    Tracker variable;
    for (const auto [seq,us,y] : {std::tuple{0,0,.35},std::tuple{1,40000,.37},std::tuple{2,240000,.47}}) {
        b=box(.5,y);output=variable.update(std::span(&b,1),seq,std::chrono::microseconds(us),1000,1000);
    }
    b=box(.5,.55);output=variable.update(std::span(&b,1),3,400ms,1000,1000);
    require(output.objects[0].id==1 && output.events.size()==1 && output.events[0].timestamp==400ms,"Variable-rate timing/prediction failed");
    b=box(.5,.65);output=variable.update(std::span(&b,1),4,500ms,2000,1000);
    require(output.objects[0].id!=1 && output.events.empty(),"Resolution change bridged old track state");

    rejects([&]{variable.update({},4,600ms,2000,1000);},"Duplicate sequence accepted");
    rejects([&]{variable.update({},5,300ms,2000,1000);},"Backward timestamp accepted");
    auto invalid=box(.5,.4);invalid.left=std::numeric_limits<float>::quiet_NaN();
    rejects([&]{Tracker t;t.update(std::span(&invalid,1),0,{},1000,1000);},"NaN box accepted");
    rejects([]{TrackingOptions o;o.line->b=o.line->a;Tracker t(o);},"Zero-length line accepted");
    rejects([]{TrackingOptions o;o.line->a.x=-.1;Tracker t(o);},"Out-of-frame line accepted");
    rejects([]{TrackingOptions o;o.classes={recognition_classes};Tracker t(o);},"Invalid class accepted");
    rejects([]{TrackingOptions o;o.association=static_cast<AssociationPolicy>(100);Tracker t(o);},"Invalid association policy accepted");
    rejects([]{parse_association("unknown");},"Unknown association name accepted");
}
}
int main() {
    try { run();std::cout<<"Tracking contracts passed: identities, finite lines, direction, jitter, re-arm, gaps, expiry, VFR, bounds\n";return 0; }
    catch(const std::exception& e) { std::cerr<<e.what()<<'\n';return 1; }
}
