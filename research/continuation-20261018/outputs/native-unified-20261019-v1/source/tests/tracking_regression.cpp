#include "frametrail/tracker.hpp"
#include <iostream>
#include <map>
#include <set>
#include <stdexcept>

using namespace frametrail;
namespace {
AssociationPolicy selected=AssociationPolicy::repair;
Detection box(double x,double y,int cls=0) {return {cls,.9f,float(x*1000-40),float(y*1000-120),float(x*1000+40),float(y*1000)};}
struct Observation {int identity;Detection detection;};
struct Measure {std::string name;unsigned changes{},observations{},events{},ids{};double max_ms{};};
Measure replay(std::string name,const std::vector<std::vector<Observation>>& frames) {
    TrackingOptions options;options.association=selected;
    Tracker tracker(options);Measure out;out.name=std::move(name);
    std::map<int,std::uint64_t> previous;std::set<std::uint64_t> ids;
    for(std::size_t frame=0;frame<frames.size();++frame) {
        std::vector<Detection> detections;for(const auto& item:frames[frame])detections.push_back(item.detection);
        const auto result=tracker.update(detections,frame,std::chrono::microseconds(frame*100000),1000,1000);
        if(result.objects.size()!=frames[frame].size())throw std::runtime_error("Replay lost a selected observation");
        for(std::size_t i=0;i<result.objects.size();++i) {
            const auto identity=frames[frame][i].identity;
            const auto id=result.objects[i].id;
            if(previous.contains(identity) && previous[identity]!=id)++out.changes;
            previous[identity]=id;ids.insert(id);++out.observations;
        }
        out.events+=unsigned(result.events.size());out.max_ms=std::max(out.max_ms,result.elapsed_ms);
    }
    out.ids=unsigned(ids.size());return out;
}
}
int main(int argc,char** argv) {
    try {
        const bool baseline=argc==2 && std::string_view(argv[1])=="--baseline";
        if(baseline)selected=AssociationPolicy::greedy;
        std::vector<Measure> results;
        results.push_back(replay("competing_candidates",{{{1,box(.35,.35)},{2,box(.45,.35)}},
            {{2,box(.38,.41)},{1,box(.25,.41)}},{{1,box(.15,.47)},{2,box(.31,.47)}},
            {{2,box(.24,.54)},{1,box(.10,.54)}}}));
        results.push_back(replay("brief_occlusion",{{{1,box(.5,.35)}},{{1,box(.5,.41)}},
            {{1,box(.5,.47)}},{},{{1,box(.5,.59)}}}));
        results.push_back(replay("overlap_and_order",{{{1,box(.35,.35)},{2,box(.65,.35)}},
            {{2,box(.60,.41)},{1,box(.40,.41)}},{{1,box(.45,.47)},{2,box(.55,.47)}},
            {{1,box(.50,.54)},{2,box(.50,.54)}},{{2,box(.45,.60)},{1,box(.55,.60)}}}));
        results.push_back(replay("class_isolation",{{{1,box(.5,.35,0)},{2,box(.5,.35,2)}},
            {{2,box(.5,.41,2)},{1,box(.5,.41,0)}},{{1,box(.5,.47,0)},{2,box(.5,.47,2)}},
            {{2,box(.5,.54,2)},{1,box(.5,.54,0)}}}));
        const unsigned expected_events[]{2,1,2,2};
        std::cout<<"{\"schema\":1,\"kind\":\"synthetic tracker-only replay, not detector or real-footage accuracy\",\"cases\":[";
        for(std::size_t i=0;i<results.size();++i) {
            const auto& r=results[i];if(i)std::cout<<',';
            std::cout<<"{\"name\":\""<<r.name<<"\",\"observations\":"<<r.observations<<",\"identity_changes\":"<<r.changes
                <<",\"distinct_tracks\":"<<r.ids<<",\"events\":"<<r.events<<",\"expected_events\":"<<expected_events[i]<<",\"max_tracking_ms\":"<<r.max_ms<<'}';
            if(!baseline && (r.changes || r.events!=expected_events[i]))throw std::runtime_error("Tracking regression failed: "+r.name);
        }
        std::cout<<"]}\n";return 0;
    }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
