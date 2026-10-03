#include "frametrail/analysis_job.hpp"
#include <algorithm>
#include <cmath>
#include <iostream>
#include <numeric>
#include <thread>

namespace {
using namespace frametrail;
void require(bool value,const char* message){if(!value)throw std::runtime_error(message);}
template<class F> void fails(F action,const char* message){try{action();}catch(const std::exception&){return;}throw std::runtime_error(message);}
double overlap(const Detection& a,const Detection& b) {
    const auto intersection=std::max(0.f,std::min(a.right,b.right)-std::max(a.left,b.left))*std::max(0.f,std::min(a.bottom,b.bottom)-std::max(a.top,b.top));
    return intersection/((a.right-a.left)*(a.bottom-a.top)+(b.right-b.left)*(b.bottom-b.top)-intersection);
}
Frame first(const std::filesystem::path& source){MediaReader reader(source);auto frame=reader.read();require(frame.has_value(),"No test frame");return std::move(*frame);}
void contract(const std::filesystem::path& source,DetectorOptions options) {
    const auto frame=first(source);Detector cpu(options);const auto baseline=cpu.detect(frame);
    require(baseline.execution.provider=="CPU" && baseline.execution.runtime=="1.30.0","CPU baseline runtime was replaced");
    options.backend=DetectorBackend::automatic;options.gpu_device=100000;
    Detector fallback(options);const auto result=fallback.detect(frame);
    require(result.execution.provider=="CPU" && !result.execution.fallback.empty(),"Automatic backend did not report unavailable GPU fallback");
    require(result.objects.size()==baseline.objects.size(),"Fallback changed detections");
    for(std::size_t i=0;i<result.objects.size();++i)require(result.objects[i].class_id==baseline.objects[i].class_id && overlap(result.objects[i],baseline.objects[i])>.999,"Fallback changed boxes/classes");
    options.backend=DetectorBackend::directml;fails([&]{Detector strict(options);},"Strict GPU silently fell back to CPU");
    options.gpu_device=-2;fails([&]{Detector invalid(options);},"Invalid GPU adapter was accepted");
    fails([&]{parse_backend("cloud");},"Unknown backend was accepted");
    std::stop_source stopped;stopped.request_stop();fails([&]{fallback.detect(frame,stopped.get_token());},"Cancelled fallback request ran inference");
    std::cout<<"CPU isolation, explicit fallback, strict failure, option validation and cancellation passed\n";
}
void compare(const std::filesystem::path& source,DetectorOptions options) {
    const auto frame=first(source);Detector cpu(options);const auto reference=cpu.detect(frame);
    options.backend=DetectorBackend::directml;Detector gpu(options);
    auto result=gpu.detect(frame);
    require(result.execution.provider=="DirectML" && result.execution.runtime=="1.24.4" && !result.execution.device.empty() && result.execution.fallback.empty(),"GPU check passed through a fallback");
    require(!result.objects.empty(),"GPU returned no reference predictions");
    int checked{};
    for(const auto& expected:reference.objects) {
        if(expected.confidence<.55)continue;
        require(std::any_of(result.objects.begin(),result.objects.end(),[&](const auto& actual){return actual.class_id==expected.class_id && overlap(actual,expected)>.98 && std::abs(actual.confidence-expected.confidence)<.02;}),"GPU changed a strong reference class/box/confidence");
        ++checked;
    }
    require(checked>=3,"Reference comparison has too few strong targets");
    double milliseconds{};
    for(int i=0;i<10;++i) {
        const auto repeated=gpu.detect(frame);require(repeated.objects.size()==result.objects.size(),"Repeated GPU runs changed result count");
        for(std::size_t j=0;j<result.objects.size();++j)require(repeated.objects[j].class_id==result.objects[j].class_id && overlap(repeated.objects[j],result.objects[j])>.9999,"Repeated GPU results changed identity/geometry");
        milliseconds+=repeated.elapsed_ms;
    }
    std::stop_source stopped;stopped.request_stop();fails([&]{gpu.detect(frame,stopped.get_token());},"Cancelled GPU request ran inference");
    require(gpu.detect(frame).execution.provider=="DirectML","Cancellation poisoned the next GPU run");
    // The linked CPU runtime must still be usable after the isolated module loads.
    require(cpu.detect(frame).execution.runtime=="1.30.0","GPU loading replaced the linked CPU runtime");
    std::cout<<"Strong-target agreement: "<<checked<<"; GPU "<<result.execution.device<<"; warm mean "<<milliseconds/10<<" ms/frame\n";
}
void saved(const std::filesystem::path& source,DetectorOptions options,const std::filesystem::path& fixtures) {
    RunConfiguration config;config.source=source;config.detector=options;config.detector.backend=DetectorBackend::directml;
    config.kind=RunKind::appearances;config.tracking.line.reset();config.tracking.classes.resize(80);std::iota(config.tracking.classes.begin(),config.tracking.classes.end(),0);
    const auto destination=fixtures/("gpu-appearance-"+std::to_string(std::chrono::steady_clock::now().time_since_epoch().count())+".frametrail");
    AnalysisJob job;job.start(destination,config);
    const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(30);
    while(job.progress().active && std::chrono::steady_clock::now()<deadline)std::this_thread::sleep_for(std::chrono::milliseconds(5));
    require(!job.progress().active && job.progress().status=="completed","Ordered GPU analysis failed or timed out");
    RunStore run(destination);const auto summary=run.summary();
    require(summary.processed_frames==6 && summary.appearance_count>=3 && summary.class_count>=3,"GPU analysis skipped source frames or lost object appearances");
    require(summary.execution.provider=="DirectML" && summary.execution.runtime=="1.24.4" && summary.configuration.detector.backend==DetectorBackend::directml,"Saved analysis lost actual/requested backend identity");
    const auto entries=run.appearances();for(const auto& entry:entries)require(entry.last_sequence<6 && entry.first_timestamp && entry.last_timestamp,"GPU result lost source timestamp identity");
    std::cout<<"Ordered GPU analysis, appearance timestamps and persisted runtime identity passed\n";
}
}
int main(int argc,char** argv) {
    try {
        require(argc==5 || argc==6,"Expected mode/source/model/profile and optional fixtures");
        DetectorOptions options;options.model=argv[3];options.variant=parse_model(argv[4]);
        const std::string_view mode=argv[1];
        if(mode=="contract")contract(argv[2],options);
        else if(mode=="gpu")compare(argv[2],options);
        else if(mode=="saved" && argc==6)saved(argv[2],options,argv[5]);
        else throw std::runtime_error("Unknown backend test mode");
        return 0;
    }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
