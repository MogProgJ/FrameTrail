#include "frametrail/detector.hpp"
#include <onnxruntime_cxx_api.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <stdexcept>

namespace frametrail {
namespace {
constexpr std::string_view labels[] = {
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
    "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat",
    "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack",
    "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball",
    "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket",
    "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake",
    "chair", "couch", "potted plant", "bed", "dining table", "toilet", "tv", "laptop",
    "mouse", "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush"
};
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
    return id >= 0 && id < 80 ? labels[id] : "unknown";
}

std::string_view model_id(DetectorModel model) {
    switch(model) {case DetectorModel::nano:return "nano";case DetectorModel::yolox_s:return "small";}
    throw std::invalid_argument("Unsupported detector model");
}
std::string_view model_name(DetectorModel model) {return model_id(model)=="nano" ? "YOLOX-Nano" : "YOLOX-S";}
DetectorModel parse_model(std::string_view id) {
    if(id=="nano")return DetectorModel::nano;
    if(id=="small")return DetectorModel::yolox_s;
    throw std::invalid_argument("Model type must be nano or small");
}
int model_input_size(DetectorModel model) {return model_id(model)=="nano" ? 416 : 640;}
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

struct Detector::Impl {
    DetectorOptions options;
    Ort::Env env{ORT_LOGGING_LEVEL_WARNING,"FrameTrail"};
    Ort::Session session{nullptr};
    std::string input_name,output_name;
    explicit Impl(const DetectorOptions& supplied):options(supplied) {
        thresholds(options.confidence,options.nms_iou);
        const auto size=model_input_size(options.variant);
        if (!std::filesystem::is_regular_file(options.model))
            throw std::runtime_error("Detection model missing. Run scripts/fetch-model.ps1 and rebuild.");
        env.DisableTelemetryEvents();
        Ort::SessionOptions settings;
        settings.SetIntraOpNumThreads(4);
        settings.SetInterOpNumThreads(1);
        settings.SetExecutionMode(ExecutionMode::ORT_SEQUENTIAL);
        settings.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_ALL);
        session=Ort::Session(env,options.model.c_str(),settings);
        if (session.GetInputCount()!=1 || session.GetOutputCount()!=1)
            throw std::runtime_error("Expected a supported YOLOX export (one input and output)");
        const auto input=session.GetInputTypeInfo(0);
        const auto output=session.GetOutputTypeInfo(0);
        if (input.GetTensorTypeAndShapeInfo().GetElementType()!=ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT ||
            input.GetTensorTypeAndShapeInfo().GetShape()!=std::vector<int64_t>{1,3,size,size} ||
            output.GetTensorTypeAndShapeInfo().GetElementType()!=ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT ||
            output.GetTensorTypeAndShapeInfo().GetShape()!=std::vector<int64_t>{1,yolox::candidate_count(size),85})
            throw std::runtime_error("Model tensor contract differs from selected model type (Nano: 416/3549, S: 640/8400)");
        Ort::AllocatorWithDefaultOptions allocator;
        input_name=session.GetInputNameAllocated(0,allocator).get();
        output_name=session.GetOutputNameAllocated(0,allocator).get();
    }
};
Detector::Detector(const DetectorOptions& options):impl_(std::make_unique<Impl>(options)) {}
Detector::~Detector()=default;
DetectionResult Detector::detect(const Frame& frame,std::stop_token stop) {
    cancelled(stop);
    const auto started=std::chrono::steady_clock::now();
    const auto size=model_input_size(impl_->options.variant);
    auto input=yolox::preprocess(frame,size);
    const auto prepared=std::chrono::steady_clock::now();
    cancelled(stop);
    const std::array<int64_t,4> shape{1,3,size,size};
    const auto memory=Ort::MemoryInfo::CreateCpu(OrtArenaAllocator,OrtMemTypeDefault);
    auto tensor=Ort::Value::CreateTensor<float>(memory,input.tensor.data(),input.tensor.size(),shape.data(),shape.size());
    const char* inputs[]{impl_->input_name.c_str()};
    const char* outputs[]{impl_->output_name.c_str()};
    Ort::RunOptions run;
    std::stop_callback interrupt(stop,[&run]() noexcept { try { run.SetTerminate(); } catch (...) {} });
    auto values=impl_->session.Run(run,inputs,&tensor,1,outputs,1);
    const auto inferred=std::chrono::steady_clock::now();
    cancelled(stop);
    const auto info=values[0].GetTensorTypeAndShapeInfo();
    if (info.GetShape()!=std::vector<int64_t>{1,yolox::candidate_count(size),85}) throw std::runtime_error("Unexpected detection result shape");
    DetectionResult result;
    result.objects=yolox::postprocess({values[0].GetTensorData<float>(),info.GetElementCount()},
        input.ratio,frame.width,frame.height,impl_->options.confidence,impl_->options.nms_iou,size);
    cancelled(stop);
    const auto finished=std::chrono::steady_clock::now();
    result.elapsed_ms=std::chrono::duration<double,std::milli>(finished-started).count();
    result.preprocess_ms=std::chrono::duration<double,std::milli>(prepared-started).count();
    result.inference_ms=std::chrono::duration<double,std::milli>(inferred-prepared).count();
    result.postprocess_ms=std::chrono::duration<double,std::milli>(finished-inferred).count();
    return result;
}
}
