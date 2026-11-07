#include "frametrail/analysis_report.hpp"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <iomanip>
#include <iterator>
#include <locale>
#include <map>
#include <numeric>
#include <sstream>
#include <stdexcept>

namespace frametrail {
namespace {
constexpr double fallback_fps=30;
// The desktop's object-type colours (apps/desktop/theme.hpp, category_color), so the report matches the app.
constexpr const char* palette[]={"#2f9fd6","#4caf50","#e0a100","#f07a4a","#9a7be0","#22b3a8","#e8609d","#8fb534","#5f8fe0",
    "#d9a930","#c062e0","#41b878"};
std::string colour(int id) {constexpr int size=int(std::size(palette));return palette[((id%size)+size)%size];}
std::string fixed(double value,int digits) {
    std::ostringstream out;out.imbue(std::locale::classic());out<<std::fixed<<std::setprecision(digits)<<value;return out.str();
}
std::string percent(double share) {return std::to_string(std::lround(std::clamp(share,0.,1.)*100))+"%";}
std::string name(int id) {return std::string(class_name(id));}
std::string length_text(double seconds) {return seconds<60 ? fixed(seconds,seconds<10 ? 1:0)+" s" : clock_text(seconds);}
std::string count_text(std::uint64_t n,std::string_view one,std::string_view many) {return std::to_string(n)+" "+std::string(n==1 ? one:many);}
std::string list_text(const std::vector<std::string>& parts) {
    std::string out;
    for(std::size_t i=0;i<parts.size();++i)out+=(i==0 ? "" : i+1==parts.size() ? " and " : ", ")+parts[i];
    return out;
}
std::string utf8(const std::filesystem::path& path) {const auto value=path.u8string();return {value.begin(),value.end()};}
struct Interval {double start{},end{};int class_id{};};
// Largest number of intervals open at one time, and the first time it happens. Ends are exclusive.
std::pair<std::uint64_t,double> peak(const std::vector<Interval>& intervals) {
    std::vector<std::pair<double,int>> edges;
    for(const auto& value:intervals){edges.emplace_back(value.start,1);edges.emplace_back(value.end,-1);}
    std::sort(edges.begin(),edges.end(),[](const auto& a,const auto& b){return a.first<b.first || (a.first==b.first && a.second<b.second);});
    std::int64_t open=0,best=0;double at=0;
    for(const auto& [time,change]:edges){open+=change;if(open>best){best=open;at=time;}}
    return {std::uint64_t(best),at};
}
double union_length(std::vector<Interval> intervals) {
    std::sort(intervals.begin(),intervals.end(),[](const Interval& a,const Interval& b){return a.start<b.start;});
    double total=0,start=0,end=-1;
    for(const auto& value:intervals) {
        if(value.start>end){if(end>start)total+=end-start;start=value.start;end=value.end;}
        else end=std::max(end,value.end);
    }
    if(end>start)total+=end-start;
    return total;
}
std::string escape(std::string_view value) {
    std::string out;
    for(const char c:value) {
        switch(c){case '&':out+="&amp;";break;case '<':out+="&lt;";break;case '>':out+="&gt;";break;case '"':out+="&quot;";break;default:out+=c;}
    }
    return out;
}
}

std::string clock_text(double seconds,bool tenths) {
    char buffer[32];
    if(tenths) {
        const auto deci=std::max<long long>(0,std::llround(std::floor(seconds*10+1e-6)));
        std::snprintf(buffer,sizeof buffer,"%lld:%02lld.%lld",deci/600,deci/10%60,deci%10);
        return buffer;
    }
    const auto total=std::max<long long>(0,std::llround(std::floor(seconds)));
    if(total>=3600)std::snprintf(buffer,sizeof buffer,"%lld:%02lld:%02lld",total/3600,total/60%60,total%60);
    else std::snprintf(buffer,sizeof buffer,"%lld:%02lld",total/60,total%60);
    return buffer;
}

std::vector<Concern> appearance_concerns(const StoredAppearance& item,float threshold) {
    std::vector<Concern> out;
    const double span=item.first_timestamp && item.last_timestamp ? (*item.last_timestamp-*item.first_timestamp).count()/1e6 : -1;
    if(item.observations<=2)
        out.push_back({Concern::Kind::brief,3,"Seen in only "+count_text(item.observations,"analysed frame","analysed frames")});
    else if(span>=0 && span<.5)out.push_back({Concern::Kind::brief,2,"On screen for only "+fixed(span,1)+" s"});
    if(item.peak_confidence<threshold+.10f)
        out.push_back({Concern::Kind::uncertain,2,"Never above "+percent(item.peak_confidence)+" confidence"});
    else if(item.detailed && item.mean_confidence()<threshold+.05)
        out.push_back({Concern::Kind::uncertain,1,"Usually uncertain (average "+percent(item.mean_confidence())+")"});
    if(item.detailed && item.first_class>=0 && item.first_class!=item.first_detection.class_id)
        out.push_back({Concern::Kind::relabelled,1,"Label changed from "+name(item.first_class)});
    if(item.detailed && item.max_area>.5)
        out.push_back({Concern::Kind::large,1,"Box covers "+percent(item.max_area)+" of the frame"});
    return out;
}

AnalysisReport build_report(const RunStore& store,std::size_t bins) {
    AnalysisReport report;report.summary=store.summary();
    const auto& summary=report.summary;
    if(summary.configuration.kind!=RunKind::appearances)throw std::invalid_argument("Reports are made for object analyses, not line crossings");
    report.video_name=utf8(summary.configuration.source.filename());
    const auto items=store.appearance_details();
    const auto frames=store.frames();
    report.frame_details=store.has_frame_details() && !frames.empty();
    report.appearance_details=items.empty() ? store.has_frame_details() : items.front().detailed;
    const double threshold=summary.configuration.detector.confidence;
    const auto step=std::max(1u,summary.configuration.tracking.frame_step);

    // Seconds between decoded frames: measured from the analysed frames when possible.
    report.frame_interval=1/fallback_fps;
    {
        const StoredFrame* first=nullptr;const StoredFrame* last=nullptr;
        for(const auto& frame:frames)if(frame.timestamp){if(!first)first=&frame;last=&frame;}
        if(first && last && last->sequence>first->sequence)
            report.frame_interval=(*last->timestamp-*first->timestamp).count()/1e6/double(last->sequence-first->sequence);
        else if(summary.media.duration && summary.processed_frames>1)
            report.frame_interval=summary.media.duration->count()/1e6/double(summary.processed_frames);
    }
    const double analysed_interval=report.frame_interval*step;
    report.times_estimated=std::ranges::any_of(items,[](const StoredAppearance& item){return !item.first_timestamp || !item.last_timestamp;});
    report.covered=summary.last_timestamp ? summary.last_timestamp->count()/1e6+report.frame_interval : double(summary.processed_frames)*report.frame_interval;
    report.duration=summary.media.duration ? summary.media.duration->count()/1e6 : report.covered;
    if(summary.status=="completed")report.covered=std::max(report.covered,report.duration);
    report.tenths=std::max(report.duration,report.covered)<60;
    const double covered=std::max(report.covered,1e-9);
    const auto start_of=[&](const StoredAppearance& item){return item.first_timestamp ? item.first_timestamp->count()/1e6 : double(item.first_sequence)/fallback_fps;};
    const auto last_of=[&](const StoredAppearance& item){return item.last_timestamp ? item.last_timestamp->count()/1e6 : double(item.last_sequence)/fallback_fps;};

    // Per appearance: object types, time on screen and concerns.
    std::map<int,ObjectTypeReport> types;std::map<int,std::vector<Interval>> by_type;std::vector<Interval> all;
    std::map<int,double> confidence_sums,paths;
    for(const auto& item:items) {
        const int id=item.first_detection.class_id;const double start=start_of(item),last=last_of(item),end=last+analysed_interval;
        auto& type=types[id];
        if(!type.appearances){type.class_id=id;type.first_seen=start;type.first_id=item.id;}
        ++type.appearances;type.observations+=item.observations;type.screen_seconds+=end-start;
        if(start<type.first_seen){type.first_seen=start;type.first_id=item.id;}
        type.last_seen=std::max(type.last_seen,last);
        confidence_sums[id]+=item.detailed ? item.confidence_sum : double(item.peak_confidence)*double(item.observations);
        paths[id]+=item.path;
        type.peak_confidence=std::max(type.peak_confidence,double(item.peak_confidence));
        if(end-start>type.longest_seconds){type.longest_seconds=end-start;type.longest_id=item.id;}
        by_type[id].push_back({start,end,id});all.push_back({start,end,id});
        const auto concerns=appearance_concerns(item,float(threshold));
        if(!concerns.empty()) {
            ++type.concerns;ReportConcern row{item.id,id,start,0,{}};
            for(const auto& concern:concerns) {
                row.severity+=concern.severity;row.reasons+=(row.reasons.empty() ? "" : "; ")+concern.text;
                switch(concern.kind) {
                case Concern::Kind::brief:++report.brief;break;case Concern::Kind::uncertain:++report.uncertain;break;
                case Concern::Kind::relabelled:++report.relabelled;break;case Concern::Kind::large:++report.large;break;
                }
            }
            report.concerns.push_back(std::move(row));
        }
    }
    for(auto& [id,type]:types) {
        type.mean_confidence=type.observations ? confidence_sums[id]/double(type.observations) : 0;
        type.mean_path=type.appearances ? paths[id]/double(type.appearances) : 0;
        type.present_seconds=union_length(by_type[id]);
        std::tie(type.most_at_once,type.most_at_once_time)=peak(by_type[id]);
    }
    std::stable_sort(report.concerns.begin(),report.concerns.end(),[](const ReportConcern& a,const ReportConcern& b){
        return a.severity!=b.severity ? a.severity>b.severity : a.start<b.start;});

    // Visibility over time: exact from per-frame statistics, otherwise estimated from appearance spans.
    const std::size_t count=covered>0 ? std::max<std::size_t>(1,bins) : 0;
    const double width=covered/double(std::max<std::size_t>(1,count));
    report.activity.resize(count);
    for(std::size_t i=0;i<count;++i){report.activity[i].start=double(i)*width;report.activity[i].end=double(i+1)*width;}
    std::vector<std::map<int,double>> bin_types(count);
    const auto bin_of=[&](double time){return std::min(count-1,std::size_t(std::max(0.,time)/width+1e-9));}; // Tolerates rounding at bin edges
    if(report.frame_details) {
        report.analysed_frames=frames.size();
        std::vector<double> timings;timings.reserve(frames.size());
        std::vector<std::uint64_t> frames_in_bin(count);std::uint64_t with_objects=0;double total_objects=0;
        std::map<int,std::uint64_t> type_peaks;
        for(const auto& frame:frames) {
            const double time=frame.timestamp ? frame.timestamp->count()/1e6 : double(frame.sequence)*report.frame_interval;
            timings.push_back(frame.detect_ms);
            std::uint64_t visible=0;for(const auto& [id,n]:frame.objects)visible+=std::uint64_t(n);
            total_objects+=double(visible);if(visible)++with_objects;
            if(visible>report.most_objects) {
                report.most_objects=visible;report.most_objects_time=time;report.most_objects_mix.clear();
                for(const auto& [id,n]:frame.objects)report.most_objects_mix.emplace_back(id,std::uint64_t(n));
            }
            for(const auto& [id,n]:frame.objects) {
                auto& type=types[id];
                if(std::uint64_t(n)>type_peaks[id]){type_peaks[id]=std::uint64_t(n);type.most_at_once=std::uint64_t(n);type.most_at_once_time=time;}
            }
            if(frame.scene_cut)report.scene_cuts.push_back(time);
            if(count) {
                auto& bin=report.activity[bin_of(time)];const auto index=bin_of(time);
                ++frames_in_bin[index];bin.mean_objects+=double(visible);bin.most_objects=std::max(bin.most_objects,visible);
                bin.scene_cut=bin.scene_cut || frame.scene_cut;
                for(const auto& [id,n]:frame.objects)bin_types[index][id]+=n;
            }
        }
        for(std::size_t i=0;i<count;++i)if(frames_in_bin[i]) {
            report.activity[i].mean_objects/=double(frames_in_bin[i]);
            for(auto& [id,value]:bin_types[i])value/=double(frames_in_bin[i]);
        }
        report.mean_objects=frames.empty() ? 0 : total_objects/double(frames.size());
        report.share_with_objects=frames.empty() ? 0 : double(with_objects)/double(frames.size());
        if(!timings.empty()) {
            report.detect_ms_mean=std::accumulate(timings.begin(),timings.end(),0.)/double(timings.size());
            std::sort(timings.begin(),timings.end());
            report.detect_ms_p95=timings[std::min(timings.size()-1,std::size_t(std::ceil(.95*double(timings.size())))-1)];
            report.detect_ms_max=timings.back();
        }
        std::ranges::sort(report.most_objects_mix,[](const auto& a,const auto& b){return a.second>b.second;});
    } else {
        report.analysed_frames=(summary.processed_frames+step-1)/step;
        double screen=0;for(const auto& value:all)screen+=value.end-value.start;
        report.mean_objects=screen/covered;report.share_with_objects=union_length(all)/covered;
        std::tie(report.most_objects,report.most_objects_time)=peak(all);
        std::map<int,std::uint64_t> mix;
        for(const auto& value:all)if(value.start<=report.most_objects_time && report.most_objects_time<value.end)++mix[value.class_id];
        report.most_objects_mix.assign(mix.begin(),mix.end());
        std::ranges::sort(report.most_objects_mix,[](const auto& a,const auto& b){return a.second>b.second;});
        for(const auto& value:all)if(count) {
            for(auto index=bin_of(value.start);index<count && report.activity[index].start<value.end;++index) {
                const double overlap=std::min(value.end,report.activity[index].end)-std::max(value.start,report.activity[index].start);
                if(overlap<=0)continue;
                report.activity[index].mean_objects+=overlap/width;bin_types[index][value.class_id]+=overlap/width;
            }
        }
    }
    for(std::size_t i=0;i<count;++i) {
        report.activity[i].by_type.assign(bin_types[i].begin(),bin_types[i].end());
        std::ranges::sort(report.activity[i].by_type,[](const auto& a,const auto& b){return a.second>b.second;});
    }
    for(auto& [id,type]:types)if(type.appearances)report.types.push_back(type);
    std::ranges::sort(report.types,[](const ObjectTypeReport& a,const ObjectTypeReport& b){
        return a.appearances!=b.appearances ? a.appearances>b.appearances : a.screen_seconds>b.screen_seconds;});

    // Findings in plain language.
    auto& out=report.findings;
    const auto appearances=std::uint64_t(items.size());
    if(summary.status!="completed")
        out.push_back("The analysis was "+std::string(summary.status=="cancelled" ? "stopped early" : "not completed")+": it covers "+
            clock_text(report.covered,report.tenths)+(report.duration>report.covered ? " of "+clock_text(report.duration,report.tenths) : std::string{})+", so every number below is partial.");
    if(!appearances) {
        out.push_back("No objects were found at "+percent(threshold)+" confidence or more. Try a lower confidence or another model.");
    } else {
        out.push_back(count_text(appearances,"appearance","appearances")+" of "+count_text(report.types.size(),"object type","object types")+" in "+
            clock_text(report.covered,report.tenths)+" of video.");
        std::vector<std::string> top;
        for(std::size_t i=0;i<std::min<std::size_t>(3,report.types.size());++i) {
            const auto& type=report.types[i];
            top.push_back(name(type.class_id)+" ("+std::to_string(type.appearances)+", on screen "+percent(type.present_seconds/covered)+" of the time)");
        }
        out.push_back("Most frequent: "+list_text(top)+".");
        if(report.most_objects) {
            std::vector<std::string> mix;
            for(const auto& [id,n]:report.most_objects_mix)if(mix.size()<4)mix.push_back(std::to_string(n)+" "+name(id));
            out.push_back("Busiest moment: "+clock_text(report.most_objects_time,report.tenths)+" with "+count_text(report.most_objects,"object","objects")+
                " visible at once ("+list_text(mix)+").");
        }
        out.push_back("Something is visible "+percent(report.share_with_objects)+" of the time, "+fixed(report.mean_objects,1)+" objects on average.");
        const auto longest=std::ranges::max_element(report.types,{},&ObjectTypeReport::longest_seconds);
        out.push_back("Longest single appearance: "+name(longest->class_id)+" #"+std::to_string(longest->longest_id)+", on screen for "+
            length_text(longest->longest_seconds)+".");
        if(report.concerns.empty())out.push_back("No appearance looks doubtful by the report's checks.");
        else {
            std::vector<std::string> parts;
            if(report.brief)parts.push_back(std::to_string(report.brief)+" seen only briefly");
            if(report.uncertain)parts.push_back(std::to_string(report.uncertain)+" with low confidence");
            if(report.relabelled)parts.push_back(std::to_string(report.relabelled)+" whose label changed");
            if(report.large)parts.push_back(std::to_string(report.large)+" with a very large box");
            out.push_back(std::to_string(report.concerns.size())+" of "+std::to_string(appearances)+" appearances ("+percent(double(report.concerns.size())/double(appearances))+
                ") are worth a second look: "+list_text(parts)+". Review these first; the rest passed every check.");
        }
        std::vector<std::string> doubtful;
        for(const auto& type:report.types)if(type.concerns==type.appearances && doubtful.size()<8)doubtful.push_back(name(type.class_id));
        if(!doubtful.empty())out.push_back("Only doubtful appearances of: "+list_text(doubtful)+". Check these before trusting them.");
    }
    if(report.frame_details) {
        if(report.scene_cuts.empty())out.push_back("One continuous shot: no scene cuts were detected.");
        else {
            std::vector<std::string> times;
            for(std::size_t i=0;i<std::min<std::size_t>(6,report.scene_cuts.size());++i)times.push_back(clock_text(report.scene_cuts[i],report.tenths));
            out.push_back(count_text(report.scene_cuts.size(),"scene cut","scene cuts")+" (the picture changes completely) at "+list_text(times)+
                (report.scene_cuts.size()>6 ? " and later" : "")+". Tracks restart after a cut, so one object may count again.");
        }
        out.push_back("Detection took "+fixed(report.detect_ms_mean,0)+" ms per frame on average (95% within "+fixed(report.detect_ms_p95,0)+" ms) on "+
            (summary.execution.provider.empty() ? std::string("CPU") : summary.execution.provider)+
            (summary.execution.device.empty() ? std::string{} : " ("+summary.execution.device+")")+".");
    } else {
        out.push_back("This analysis was made by an older FrameTrail without per-frame statistics: busy moments are estimated from appearance times, "
            "and speed and scene cuts are unknown. Analyse the video again for exact figures.");
    }
    if(step>1)out.push_back("Every "+std::to_string(step)+(step==2 ? "nd" : step==3 ? "rd" : "th")+" frame was analysed, so times are accurate to about "+
        fixed(analysed_interval,2)+" s.");
    if(report.times_estimated)out.push_back("The video has no usable timestamps; times assume 30 frames per second.");
    return report;
}

std::string report_html(const AnalysisReport& r) {
    const auto& s=r.summary;
    std::ostringstream h;h.imbue(std::locale::classic());
    const double covered=std::max(r.covered,1e-9);
    h<<"<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
       "<title>FrameTrail analysis · "<<escape(r.video_name)<<"</title><style>"
       ":root{--bg:#fafafa;--card:#fff;--text:#1b1b1b;--muted:#5f5f5f;--line:#e3e3e3;--accent:#0f6cbd;--warn:#b54708}"
       "@media (prefers-color-scheme:dark){:root{--bg:#1a1a1a;--card:#242424;--text:#f3f3f3;--muted:#b4b4b4;--line:#3a3a3a;--accent:#60cdff;--warn:#fdb022}}"
       "*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 'Segoe UI',system-ui,sans-serif}"
       "main{max-width:1100px;margin:0 auto;padding:28px 20px 60px}h1{font-size:26px;margin:0 0 4px}h2{font-size:18px;margin:34px 0 10px}"
       ".muted{color:var(--muted)}.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-top:20px}"
       ".tile{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}.tile b{display:block;font-size:24px;font-weight:600}"
       ".tile span{color:var(--muted);font-size:13px}ul.findings{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 18px 14px 34px;margin:0}"
       "ul.findings li{margin:5px 0}table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden;font-size:14px}"
       "th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--muted);font-weight:600;background:rgba(127,127,127,.08)}"
       "td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:7px}"
       ".bar{height:8px;border-radius:4px;background:var(--accent);opacity:.75}.warn{color:var(--warn)}.chart{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px}"
       ".legend span{margin-right:16px;font-size:13px;white-space:nowrap}.scroll{overflow-x:auto}svg text{fill:var(--muted);font-size:11px}"
       "</style></head><body><main>";
    h<<"<h1>"<<escape(r.video_name)<<"</h1><div class=\"muted\">"<<escape(std::string(detector_name(s.configuration.detector)))<<" · confidence "
     <<percent(s.configuration.detector.confidence)<<" · "<<s.media.width<<"×"<<s.media.height<<" · "<<clock_text(r.duration,r.tenths)<<" · analysed "
     <<escape(s.created)<<" · "<<escape(s.status)<<"</div>";
    const auto tile=[&](const std::string& value,const std::string& label){h<<"<div class=\"tile\"><b>"<<escape(value)<<"</b><span>"<<escape(label)<<"</span></div>";};
    std::uint64_t appearances=0;for(const auto& type:r.types)appearances+=type.appearances;
    h<<"<div class=\"tiles\">";
    tile(std::to_string(appearances),"appearances");tile(std::to_string(r.types.size()),"object types");
    tile(std::to_string(r.most_objects),"most visible at once");tile(fixed(r.mean_objects,1),"visible on average");
    tile(percent(r.share_with_objects),"of the time something is visible");tile(std::to_string(r.concerns.size()),"worth a second look");
    if(r.frame_details){tile(fixed(r.detect_ms_mean,0)+" ms","detection per frame");tile(std::to_string(r.scene_cuts.size()),"scene cuts");}
    h<<"</div><h2>Findings</h2><ul class=\"findings\">";
    for(const auto& line:r.findings)h<<"<li>"<<escape(line)<<"</li>";
    h<<"</ul>";

    // Activity: average objects visible over time, stacked by the five most frequent types.
    if(!r.activity.empty()) {
        std::vector<int> shown;for(const auto& type:r.types)if(shown.size()<5)shown.push_back(type.class_id);
        double top=0;for(const auto& bin:r.activity)top=std::max({top,bin.mean_objects,double(bin.most_objects)});
        top=std::max(1.,std::ceil(top));
        const double w=900,hgt=170,left=34,bottom=20,plot=hgt-bottom-8,bar=(w-left)/double(r.activity.size());
        h<<"<h2>Activity over time</h2><div class=\"chart\"><div class=\"scroll\"><svg viewBox=\"0 0 "<<w<<' '<<hgt<<"\" width=\"100%\" role=\"img\" aria-label=\"Objects visible over time\">";
        for(int i=0;i<=2;++i) {
            const double y=8+plot-plot*i/2.;
            h<<"<line x1=\""<<left<<"\" x2=\""<<w<<"\" y1=\""<<fixed(y,1)<<"\" y2=\""<<fixed(y,1)<<"\" stroke=\"currentColor\" stroke-opacity=\".12\"/>"
             <<"<text x=\"0\" y=\""<<fixed(y+4,1)<<"\">"<<fixed(top*i/2.,top<4 ? 1:0)<<"</text>";
        }
        for(std::size_t i=0;i<r.activity.size();++i) {
            const auto& bin=r.activity[i];double y=8+plot;double other=bin.mean_objects;
            const double x=left+double(i)*bar;
            const auto rect=[&](double value,const std::string& fill) {
                if(value<=0)return;const double height=plot*value/top;y-=height;
                h<<"<rect x=\""<<fixed(x+.5,1)<<"\" y=\""<<fixed(y,1)<<"\" width=\""<<fixed(std::max(1.,bar-1),1)<<"\" height=\""<<fixed(height,1)<<"\" fill=\""<<fill<<"\"/>";
            };
            for(std::size_t k=0;k<shown.size();++k)for(const auto& [type,value]:bin.by_type)if(type==shown[k]){rect(value,report_series_colours[k]);other-=value;}
            rect(std::max(0.,other),"#9e9e9e");
            if(bin.scene_cut)h<<"<line x1=\""<<fixed(x,1)<<"\" x2=\""<<fixed(x,1)<<"\" y1=\"4\" y2=\""<<fixed(8+plot,1)<<"\" stroke=\"#d13438\" stroke-dasharray=\"3 3\"/>";
            h<<"<title>"<<clock_text(bin.start,r.tenths)<<"–"<<clock_text(bin.end,r.tenths)<<": "<<fixed(bin.mean_objects,1)<<" visible on average</title>";
        }
        for(int i=0;i<=4;++i)h<<"<text x=\""<<fixed(left+(w-left)*i/4.-(i==4 ? 30:0),1)<<"\" y=\""<<hgt-4<<"\">"<<clock_text(covered*i/4.,r.tenths)<<"</text>";
        h<<"</svg></div><div class=\"legend\">";
        for(std::size_t k=0;k<shown.size();++k)h<<"<span><i class=\"dot\" style=\"background:"<<report_series_colours[k]<<"\"></i>"<<escape(name(shown[k]))<<"</span>";
        h<<"<span><i class=\"dot\" style=\"background:#9e9e9e\"></i>other</span>";
        if(!r.scene_cuts.empty())h<<"<span style=\"color:#d13438\">┆ scene cut</span>";
        h<<"</div><div class=\"muted\" style=\"font-size:13px;margin-top:6px\">Average number of tracked objects visible in each stretch of the video"
         <<(r.frame_details ? "." : ", estimated from appearance times.")<<"</div></div>";
    }

    h<<"<h2>Object types</h2><div class=\"scroll\"><table><tr><th>Object</th><th class=\"n\">Appearances</th><th>On screen</th><th class=\"n\">Most at once</th>"
       "<th class=\"n\">First seen</th><th class=\"n\">Last seen</th><th class=\"n\">Longest</th><th class=\"n\">Avg conf.</th><th class=\"n\">Peak conf.</th>"
     <<(r.appearance_details ? "<th class=\"n\">Movement</th>" : "")<<"<th class=\"n\">Doubtful</th></tr>";
    for(const auto& t:r.types) {
        const double share=t.present_seconds/covered;
        h<<"<tr><td><i class=\"dot\" style=\"background:"<<colour(t.class_id)<<"\"></i>"<<escape(name(t.class_id))<<"</td><td class=\"n\">"<<t.appearances
         <<"</td><td><div style=\"display:flex;align-items:center;gap:8px\"><div class=\"bar\" style=\"width:"<<fixed(std::clamp(share,0.,1.)*90,1)<<"px\"></div>"
         <<percent(share)<<"</div></td><td class=\"n\">"<<t.most_at_once<<"</td><td class=\"n\">"<<clock_text(t.first_seen,r.tenths)<<"</td><td class=\"n\">"<<clock_text(t.last_seen,r.tenths)
         <<"</td><td class=\"n\">"<<length_text(t.longest_seconds)<<"</td><td class=\"n\">"<<percent(t.mean_confidence)<<"</td><td class=\"n\">"<<percent(t.peak_confidence)<<"</td>";
        if(r.appearance_details)h<<"<td class=\"n\">"<<fixed(t.mean_path,2)<<"</td>";
        h<<"<td class=\"n"<<(t.concerns ? " warn" : "")<<"\">"<<t.concerns<<"</td></tr>";
    }
    h<<"</table></div>";
    if(r.appearance_details)h<<"<div class=\"muted\" style=\"font-size:13px;margin-top:6px\">Movement: average distance each appearance travelled, in frame widths (0 = stood still).</div>";

    if(!r.concerns.empty()) {
        h<<"<h2>Worth a second look</h2><div class=\"scroll\"><table><tr><th class=\"n\">Time</th><th>Object</th><th class=\"n\">#</th><th>Why</th></tr>";
        const std::size_t limit=300;
        for(std::size_t i=0;i<std::min(limit,r.concerns.size());++i) {
            const auto& c=r.concerns[i];
            h<<"<tr><td class=\"n\">"<<clock_text(c.start,r.tenths)<<"</td><td><i class=\"dot\" style=\"background:"<<colour(c.class_id)<<"\"></i>"<<escape(name(c.class_id))
             <<"</td><td class=\"n\">"<<c.appearance<<"</td><td>"<<escape(c.reasons)<<"</td></tr>";
        }
        h<<"</table></div>";
        if(r.concerns.size()>limit)h<<"<div class=\"muted\">… and "<<r.concerns.size()-limit<<" more, in FrameTrail's Report tab.</div>";
    }

    h<<"<h2>Run details</h2><table>";
    const auto row=[&](const std::string& label,const std::string& value){h<<"<tr><th>"<<escape(label)<<"</th><td>"<<escape(value)<<"</td></tr>";};
    row("Video",utf8(s.configuration.source));row("Resolution",std::to_string(s.media.width)+" × "+std::to_string(s.media.height)+(s.media.codec.empty() ? "" : " · "+s.media.codec));
    row("Duration",clock_text(r.duration,r.tenths)+(r.covered+r.frame_interval<r.duration ? " (analysed: "+clock_text(r.covered,r.tenths)+")" : ""));
    row("Frames",std::to_string(r.analysed_frames)+" analysed"+(s.configuration.tracking.frame_step>1 ? ", every "+std::to_string(s.configuration.tracking.frame_step)+" frames" : "")
        +" · about "+fixed(1/std::max(r.frame_interval,1e-9),1)+" frames per second in the video");
    row("Model",std::string(detector_name(s.configuration.detector))+" · "+utf8(s.configuration.detector.model.filename()));
    row("Confidence threshold",percent(s.configuration.detector.confidence));
    row("Device",s.execution.provider+(s.execution.device.empty() ? "" : " · "+s.execution.device)+(s.execution.fallback.empty() ? "" : " · fallback: "+s.execution.fallback));
    if(r.frame_details)row("Detection time",fixed(r.detect_ms_mean,1)+" ms average · "+fixed(r.detect_ms_p95,1)+" ms 95th percentile · "+fixed(r.detect_ms_max,1)+" ms slowest");
    row("Status",s.status+(s.error.empty() ? "" : " · "+s.error));row("Run ID",s.id);row("Created",s.created);
    h<<"</table>";
    h<<"<h2>How to read this</h2><ul class=\"findings muted\">"
       "<li>An <b>appearance</b> is one tracked object from when it is first seen until it leaves (short gaps are bridged). The same real object can count twice if it leaves and returns or after a scene cut.</li>"
       "<li><b>On screen</b> is the share of the analysed video in which at least one object of that type is visible; <b>Most at once</b> is the highest number visible in a single frame.</li>"
       "<li><b>Worth a second look</b> uses simple checks: seen in two analysed frames or fewer, on screen under half a second, never more than 10 points above the confidence threshold, "
       "an average within 5 points of it, a label that changed between related types (car/truck), or a box covering more than half the frame. These are hints, not verdicts.</li>"
       "<li>Confidence is the model's own score, not a measured accuracy. Mark appearances right or wrong in FrameTrail's Review to measure it.</li></ul>";
    h<<"<p class=\"muted\" style=\"margin-top:30px;font-size:13px\">Made by FrameTrail on this device. Nothing was uploaded.</p></main></body></html>\n";
    return h.str();
}

void write_report_html(const AnalysisReport& report,const std::filesystem::path& output) {
    const auto html=report_html(report);
    std::FILE* file{};
#ifdef _WIN32
    _wfopen_s(&file,output.c_str(),L"wbx");
#else
    file=std::fopen(output.c_str(),"wbx");
#endif
    if(!file)throw std::runtime_error("Cannot create the report; choose a new file in a writable folder: "+utf8(output));
    const bool written=std::fwrite(html.data(),1,html.size(),file)==html.size();
    if(std::fclose(file)!=0 || !written) {
        std::error_code ignored;std::filesystem::remove(output,ignored);throw std::runtime_error("Could not write the report");
    }
}
}
