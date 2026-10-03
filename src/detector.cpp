#include "frametrail/detector.hpp"
#include "dml_inference.hpp"
#include "recognition_vocabulary.hpp"
#include <onnxruntime_cxx_api.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <stdexcept>

namespace frametrail {
namespace {
using vocabulary::labels;
void thresholds(float confidence, float iou) {
    if (!std::isfinite(confidence) || confidence <= 0 || confidence > 1 ||
        !std::isfinite(iou) || iou <= 0 || iou > 1)
        throw std::invalid_argument("Detection thresholds must be in (0, 1]");
}
float overlap(const Detection& a, const Detection& b) {
    const auto area = [](const Detection& d) { return (d.right-d.left)*(d.bottom-d.top); };
    const float intersection = std::max(0.f, std::min(a.right,b.right)-std::max(a.left,b.left)) *
        std::max(0.f, std::min(a.bottom,b.bottom)-std::max(a.top,b.top));
    return intersection / (area(a)+area(b)-intersection);
}
void cancelled(std::stop_token stop) {
    if (stop.stop_requested()) throw std::runtime_error("Object detection cancelled");
}
}
std::string_view class_name(int id) {
    return id >= 0 && id < recognition_classes ? labels[id] : "unknown";
}

std::string_view model_id(DetectorModel model) {
    switch(model) {case DetectorModel::nano:return "nano";case DetectorModel::yolox_s:return "small";
        case DetectorModel::world_s:return "world-s";case DetectorModel::world_m:return "world-m";case DetectorModel::openimages:return "openimages";}
    throw std::invalid_argument("Unsupported detector model");
}
std::string_view model_name(DetectorModel model) {
    switch(model) {case DetectorModel::nano:return "YOLOX-Nano";case DetectorModel::yolox_s:return "YOLOX-S";
        case DetectorModel::world_s:return "YOLO-World S";case DetectorModel::world_m:return "YOLO-World M";case DetectorModel::openimages:return "YOLOv8 Open Images";}
    throw std::invalid_argument("Unsupported detector model");
}
DetectorModel parse_model(std::string_view id) {
    if(id=="nano")return DetectorModel::nano;if(id=="small")return DetectorModel::yolox_s;
    if(id=="world-s")return DetectorModel::world_s;if(id=="world-m")return DetectorModel::world_m;
    if(id=="openimages")return DetectorModel::openimages;
    throw std::invalid_argument("Model type must be nano, small, world-s, world-m or openimages");
}
int model_input_size(DetectorModel model) {model_id(model);return model==DetectorModel::nano ? 416:640;}
int model_class_count(DetectorModel model) {model_id(model);return model==DetectorModel::openimages ? 601:(model==DetectorModel::nano || model==DetectorModel::yolox_s ? 80:100);}
int model_category_count(DetectorModel model) {return model==DetectorModel::openimages ? 597:model_class_count(model);}
std::vector<int64_t> model_output_shape(DetectorModel model) {
    if(model_class_count(model)>80)return {1,4+model_class_count(model),8400};
    return {1,yolox::candidate_count(model_input_size(model)),85};
}
std::vector<int> model_classes(DetectorModel model) {
    if(model==DetectorModel::openimages)return {vocabulary::openimages_ids.begin(),vocabulary::openimages_ids.end()};
    std::vector<int> ids;for(int id=0;id<model_class_count(model);++id)ids.push_back(id);return ids;
}
bool model_has_class(DetectorModel model,int id) {
    if(model!=DetectorModel::openimages)return id>=0 && id<model_class_count(model);
    return std::find(vocabulary::openimages_ids.begin(),vocabulary::openimages_ids.end(),id)!=vocabulary::openimages_ids.end();
}
std::string model_vocabulary(DetectorModel model) {
    std::string out;for(const auto id:model_classes(model)){if(!out.empty())out+='\n';out+=class_name(id);}return out;
}
std::string world_vocabulary(){return model_vocabulary(DetectorModel::world_s);}
int yolox::candidate_count(int size) {
    if(size!=416 && size!=640)throw std::invalid_argument("Supported YOLOX input sizes are 416 and 640");
    return (size/8)*(size/8)+(size/16)*(size/16)+(size/32)*(size/32);
}

yolox::Input yolox::preprocess(const Frame& frame, int size) {
    candidate_count(size);
    if (frame.width <= 0 || frame.height <= 0 || frame.stride <= 0 ||
        static_cast<std::int64_t>(frame.stride) < static_cast<std::int64_t>(frame.width)*3 ||
        frame.pixels.size() < static_cast<std::uint64_t>(frame.stride)*frame.height)
        throw std::invalid_argument("Invalid RGB frame for detection");
    Input result;
    result.ratio = std::min(double(size)/frame.width, double(size)/frame.height);
    result.resized_width = std::max(1, int(frame.width * result.ratio));
    result.resized_height = std::max(1, int(frame.height * result.ratio));
    const int plane = size*size;
    result.tensor.assign(3*plane, 114.f);
    // Half-pixel bilinear resize, rounded to uint8, top-left letterbox.
    // FFmpeg gives RGB; this export was trained with BGR values in [0,255].
    for (int y=0; y<result.resized_height; ++y) {
        const double sy = std::clamp((y+0.5)*frame.height/result.resized_height-0.5, 0.0, double(frame.height-1));
        const int y0=int(sy), y1=std::min(y0+1,frame.height-1);
        const double fy=sy-y0;
        for (int x=0; x<result.resized_width; ++x) {
            const double sx=std::clamp((x+0.5)*frame.width/result.resized_width-0.5, 0.0, double(frame.width-1));
            const int x0=int(sx), x1=std::min(x0+1,frame.width-1);
            const double fx=sx-x0;
            for (int c=0; c<3; ++c) {
                const auto pixel=[&](int px,int py) { return frame.pixels[std::size_t(py)*frame.stride+std::size_t(px)*3+(2-c)]; };
                const double top=pixel(x0,y0)*(1-fx)+pixel(x1,y0)*fx;
                const double bottom=pixel(x0,y1)*(1-fx)+pixel(x1,y1)*fx;
                result.tensor[c*plane+y*size+x]=float(std::round(top*(1-fy)+bottom*fy));
            }
        }
    }
    return result;
}

std::vector<Detection> yolox::postprocess(std::span<const float> output, double ratio,
    int width, int height, float confidence, float nms_iou, int size) {
    thresholds(confidence,nms_iou);
    if (output.size()!=std::size_t(candidate_count(size))*attributes || !std::isfinite(ratio) || ratio<=0 || width<=0 || height<=0)
        throw std::invalid_argument("Unexpected YOLOX output or image geometry");
    std::vector<Detection> proposals;
    int row=0;
    for (const int stride : {8,16,32}) {
        const int grid=size/stride;
        for (int y=0; y<grid; ++y) for (int x=0; x<grid; ++x,++row) {
            const float* p=output.data()+std::size_t(row)*attributes;
            if (!std::all_of(p,p+attributes,[](float value){return std::isfinite(value);})) continue;
            const auto best=std::max_element(p+5,p+85);
            const float score=p[4]*(*best);
            if (p[4]<0 || p[4]>1 || *best<0 || *best>1 || score<confidence) continue;
            const double cx=(p[0]+x)*stride/ratio, cy=(p[1]+y)*stride/ratio;
            const double w=std::exp(double(p[2]))*stride/ratio, h=std::exp(double(p[3]))*stride/ratio;
            if (!std::isfinite(w) || !std::isfinite(h)) continue;
            Detection d{int(best-(p+5)),score,
                float(std::clamp(cx-w/2,0.0,double(width))), float(std::clamp(cy-h/2,0.0,double(height))),
                float(std::clamp(cx+w/2,0.0,double(width))), float(std::clamp(cy+h/2,0.0,double(height)))};
            if (d.right>d.left && d.bottom>d.top) proposals.push_back(d);
        }
    }
    std::stable_sort(proposals.begin(),proposals.end(),[](const auto& a,const auto& b){return a.confidence>b.confidence;});
    std::vector<Detection> kept;
    for (const auto& candidate:proposals) {
        if (std::none_of(kept.begin(),kept.end(),[&](const auto& prior){
            return prior.class_id==candidate.class_id && overlap(prior,candidate)>nms_iou;
        })) kept.push_back(candidate);
        if (kept.size()==100) break;
    }
    return kept;
}

DetectorBackend parse_backend(std::string_view value) {
    if(value=="cpu")return DetectorBackend::cpu;
    if(value=="auto")return DetectorBackend::automatic;
    if(value=="directml")return DetectorBackend::directml;
    throw std::invalid_argument("Backend must be cpu, auto, or directml");
}
std::string_view backend_id(DetectorBackend backend) {
    switch(backend) {
        case DetectorBackend::cpu:return "cpu";
        case DetectorBackend::automatic:return "auto";
        case DetectorBackend::directml:return "directml";
    }
    throw std::invalid_argument("Invalid detector backend");
}

struct Detector::Impl {
    DetectorOptions options;
    Ort::Env env{ORT_LOGGING_LEVEL_WARNING,"FrameTrail"};
    Ort::Session session{nullptr};
    std::string input_name,output_name;
    std::unique_ptr<DmlInference> gpu;
    ExecutionInfo execution;
    explicit Impl(const DetectorOptions& supplied):options(supplied) {
        thresholds(options.confidence,options.nms_iou);
        backend_id(options.backend);
        if(options.gpu_device < -1)throw std::invalid_argument("GPU device must be -1 or a DXGI index");
        if (!std::filesystem::is_regular_file(options.model))
            throw std::runtime_error("Detection model missing. Run scripts/fetch-model.ps1 and rebuild.");
        env.DisableTelemetryEvents();
        if(options.backend!=DetectorBackend::cpu) {
            try{gpu=std::make_unique<DmlInference>(options);execution=gpu->info();return;}
            catch(const std::exception& e){if(options.backend==DetectorBackend::directml)throw;execution.fallback=e.what();}
        }
        initialise_cpu();
    }
    void initialise_cpu() {
        gpu.reset();execution.provider="CPU";execution.runtime=OrtGetApiBase()->GetVersionString();execution.device="Processor";
        const auto size=model_input_size(options.variant);
        Ort::SessionOptions settings;
        settings.SetIntraOpNumThreads(4);
        settings.SetInterOpNumThreads(1);
        settings.SetExecutionMode(ExecutionMode::ORT_SEQUENTIAL);
        settings.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_ALL);
        session=Ort::Session(env,options.model.c_str(),settings);
        if (session.GetInputCount()!=1 || session.GetOutputCount()!=1)
            throw std::runtime_error("Expected a supported detection export (one input and output)");
        const auto input=session.GetInputTypeInfo(0);
        const auto output=session.GetOutputTypeInfo(0);
        if (input.GetTensorTypeAndShapeInfo().GetElementType()!=ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT ||
            input.GetTensorTypeAndShapeInfo().GetShape()!=std::vector<int64_t>{1,3,size,size} ||
            output.GetTensorTypeAndShapeInfo().GetElementType()!=ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT ||
            output.GetTensorTypeAndShapeInfo().GetShape()!=model_output_shape(options.variant))
            throw std::runtime_error("Model tensor contract differs from selected model profile");
        Ort::AllocatorWithDefaultOptions allocator;
        if(model_class_count(options.variant)>80) {
            const auto metadata=session.GetModelMetadata();
            const auto profile=metadata.LookupCustomMetadataMapAllocated("frametrail.profile",allocator);
            const auto vocabulary=metadata.LookupCustomMetadataMapAllocated("frametrail.vocabulary",allocator);
            if(!profile || !vocabulary || std::string_view(profile.get())!=model_id(options.variant) ||
               std::string_view(vocabulary.get())!=model_vocabulary(options.variant))
                throw std::runtime_error("Recognition profile/vocabulary mismatch; use the pinned model export");
        }
        input_name=session.GetInputNameAllocated(0,allocator).get();
        output_name=session.GetOutputNameAllocated(0,allocator).get();
    }
};
Detector::Detector(const DetectorOptions& options):impl_(std::make_unique<Impl>(options)) {}
Detector::~Detector()=default;
const ExecutionInfo& Detector::execution_info() const{return impl_->execution;}
DetectionResult Detector::detect(const Frame& frame,std::stop_token stop) {
    cancelled(stop);
    const auto started=std::chrono::steady_clock::now();
    const auto size=model_input_size(impl_->options.variant);
    const bool world=model_class_count(impl_->options.variant)>80;
    yolo_world::Input world_input;
    yolox::Input legacy_input;
    if(world)world_input=yolo_world::preprocess(frame);else legacy_input=yolox::preprocess(frame,size);
    auto& tensor_data=world ? world_input.tensor:legacy_input.tensor;
    const auto prepared=std::chrono::steady_clock::now();
    cancelled(stop);
    std::vector<float> gpu_output;
    std::vector<Ort::Value> cpu_output;
    std::span<const float> output;
    if(impl_->gpu) {
        try{gpu_output=impl_->gpu->run(tensor_data,stop);output=gpu_output;}
        catch(const std::exception& e) {
            cancelled(stop);
            if(impl_->options.backend==DetectorBackend::directml)throw;
            impl_->execution.fallback=std::string("GPU run failed; CPU retry: ")+e.what();impl_->initialise_cpu();
        }
    }
    if(!impl_->gpu) {
        const std::array<int64_t,4> shape{1,3,size,size};
        const auto memory=Ort::MemoryInfo::CreateCpu(OrtArenaAllocator,OrtMemTypeDefault);
        auto tensor=Ort::Value::CreateTensor<float>(memory,tensor_data.data(),tensor_data.size(),shape.data(),shape.size());
        const char* inputs[]{impl_->input_name.c_str()};const char* outputs[]{impl_->output_name.c_str()};
        Ort::RunOptions run;
        std::stop_callback interrupt(stop,[&run]() noexcept {try{run.SetTerminate();}catch(...){}});
        cpu_output=impl_->session.Run(run,inputs,&tensor,1,outputs,1);
        const auto info=cpu_output[0].GetTensorTypeAndShapeInfo();
        if(info.GetShape()!=model_output_shape(impl_->options.variant))throw std::runtime_error("Unexpected detection result shape");
        output={cpu_output[0].GetTensorData<float>(),info.GetElementCount()};
    }
    const auto inferred=std::chrono::steady_clock::now();
    cancelled(stop);
    DetectionResult result;
    result.objects=world ? yolo_world::postprocess(output,world_input,frame.width,frame.height,impl_->options.confidence,impl_->options.nms_iou,impl_->options.variant):
        yolox::postprocess(output,legacy_input.ratio,frame.width,frame.height,impl_->options.confidence,impl_->options.nms_iou,size);
    cancelled(stop);
    const auto finished=std::chrono::steady_clock::now();
    result.elapsed_ms=std::chrono::duration<double,std::milli>(finished-started).count();
    result.preprocess_ms=std::chrono::duration<double,std::milli>(prepared-started).count();
    result.inference_ms=std::chrono::duration<double,std::milli>(inferred-prepared).count();
    result.postprocess_ms=std::chrono::duration<double,std::milli>(finished-inferred).count();
    result.execution=impl_->execution;
    return result;
}
}
