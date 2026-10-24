#include "frametrail/detector.hpp"
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>

using namespace frametrail;
namespace {
void require(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
template<class F>void fails(F f){try{f();}catch(const std::exception&){return;}throw std::runtime_error("Invalid RF contract accepted");}
void contract(){
    require(model_input_size(DetectorModel::rf_scale7758628)==512 && model_class_count(DetectorModel::rf_scale7758628)==615,"RF profile dimensions");
    require(model_output_shape(DetectorModel::rf_scale7758628)==std::vector<int64_t>({1,300,619}),"RF output contract");
    require(parse_model("rfdetr-7758628")==DetectorModel::rf_scale7758628 && model_has_class(DetectorModel::rf_scale7758628,600),"RF canonical registry");
    require(parse_model("rfdetr-7805570")==DetectorModel::rf_balanced7805570 && model_output_shape(DetectorModel::rf_balanced7805570)==std::vector<int64_t>({1,300,619}),"Balanced RF identity/shape");
    require(rfdetr::checkpoint_for(DetectorModel::rf_balanced7805570)!=rfdetr::checkpoint_for(DetectorModel::rf_scale7758628),"RF checkpoints conflated");
    require(parse_model("rfdetr-oi")==DetectorModel::rf_openimages && model_id(DetectorModel::rf_openimages)=="rfdetr-oi" &&
        is_rf_model(DetectorModel::rf_openimages) && model_output_shape(DetectorModel::rf_openimages)==std::vector<int64_t>({1,300,619}),"Open Images RF identity/shape");
    require(rfdetr::checkpoint_for(DetectorModel::rf_openimages).empty(),"Open Images RF exports are identified by metadata, not one pinned checkpoint");
    Frame frame;frame.width=2;frame.height=2;frame.stride=8;frame.pixels={255,0,0,0,255,0,99,99,0,0,255,255,255,255,99,99};
    auto input=rfdetr::preprocess(frame);require(input.size()==3*512*512,"RF input size");
    require(std::abs(input[0]-(1-.485f)/.229f)<1e-6f && std::abs(input[512*512]-(-.456f/.224f))<1e-6f,"RF RGB normalization/stride");
    require(std::abs(input[511]-(0-.485f)/.229f)<1e-6f,"RF full-image resize");
    frame.stride=5;fails([&]{rfdetr::preprocess(frame);});
    std::vector<float> output(300*619,-20.f);
    for(int q=0;q<300;++q){auto* b=output.data()+q*619;b[0]=.5f;b[1]=.5f;b[2]=.2f;b[3]=.2f;}
    output[4+600]=3;output[4]=2;output[619+4+600]=4;
    auto detections=rfdetr::postprocess(output,1000,500,.35f,.45f);
    require(detections.size()==2 && detections[0].class_id==600 && detections[1].class_id==0,"RF global top-k, canonical IDs or per-class NMS");
    require(std::abs(detections[0].left-400)<1e-4 && std::abs(detections[0].bottom-300)<1e-4,"RF original frame geometry");
    output[0]=std::numeric_limits<float>::quiet_NaN();fails([&]{rfdetr::postprocess(output,100,100,.35f,.45f);});
    fails([&]{rfdetr::postprocess({},100,100,.35f,.45f);});
    std::cout<<"RF adapter contracts passed\n";
}
void probe(const std::filesystem::path& model,const std::filesystem::path& raw,int width,int height,const std::filesystem::path& prefix,bool use_gpu,DetectorModel variant){
    Frame frame;frame.width=width;frame.height=height;frame.stride=width*3;
    std::ifstream file(raw,std::ios::binary);frame.pixels={std::istreambuf_iterator<char>(file),{}};
    require(frame.pixels.size()==std::size_t(width)*height*3,"RGB input bytes differ");
    const auto tensor=rfdetr::preprocess(frame);
    {std::ofstream out(prefix.string()+".input.f32",std::ios::binary);out.write(reinterpret_cast<const char*>(tensor.data()),tensor.size()*sizeof(float));}
    Detector detector({model,.35f,.45f,variant,use_gpu ? DetectorBackend::directml:DetectorBackend::cpu});
    auto result=detector.detect(frame);
    std::ofstream out(prefix.string()+".csv");out<<"class_id,confidence,left,top,right,bottom\n"<<std::setprecision(10);
    for(const auto& d:result.objects)out<<d.class_id<<','<<d.confidence<<','<<d.left<<','<<d.top<<','<<d.right<<','<<d.bottom<<'\n';
    require(result.execution.provider==(use_gpu ? "DirectML":"CPU"),"RF requested execution provider differs");
    std::ofstream timing(prefix.string()+".timing.json");timing<<"{\"preprocess_ms\":"<<result.preprocess_ms<<",\"inference_ms\":"<<result.inference_ms<<",\"postprocess_ms\":"<<result.postprocess_ms<<",\"detections\":"<<result.objects.size()<<"}";
    std::stop_source stop;stop.request_stop();fails([&]{detector.detect(frame,stop.get_token());});
    fails([&]{Detector strict({model,.35f,.45f,variant,DetectorBackend::directml,100000});});
    if(!use_gpu) {
        Detector fallback({model,.35f,.45f,variant,DetectorBackend::automatic,100000});
        require(fallback.execution_info().provider=="CPU" && !fallback.execution_info().fallback.empty(),"Unavailable RF GPU did not report CPU fallback");
        require(fallback.detect(frame).objects.size()==result.objects.size(),"CPU fallback changed RF detections");
    }
    std::cout<<"RF native detections: "<<result.objects.size()<<"; "<<result.elapsed_ms<<" ms\n";
}
}
int main(int argc,char** argv){
    try{
        if(argc==1)contract();
        else if(const std::string_view mode=argc==7 ? argv[1]:""; mode=="probe" || mode=="probe-gpu" || mode=="probe-balanced" || mode=="probe-balanced-gpu" || mode=="probe-openimages" || mode=="probe-openimages-gpu")
            probe(argv[2],argv[3],std::stoi(argv[4]),std::stoi(argv[5]),argv[6],mode.ends_with("-gpu"),
                mode.starts_with("probe-balanced") ? DetectorModel::rf_balanced7805570:mode.starts_with("probe-openimages") ? DetectorModel::rf_openimages:DetectorModel::rf_scale7758628);
        else throw std::runtime_error("Unexpected RF probe arguments");
        return 0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
