#pragma once
#include "frametrail/frame.hpp"
#include <filesystem>
#include <memory>
#include <span>
#include <stop_token>
#include <string_view>
#include <string>

namespace frametrail {
enum class DetectorBackend { cpu, automatic, directml };
DetectorBackend parse_backend(std::string_view value);
std::string_view backend_id(DetectorBackend backend);
struct ExecutionInfo {
    std::string provider{"CPU"}, runtime, device, fallback;
    bool operator==(const ExecutionInfo&) const = default;
};
struct Detection {
    int class_id{};
    float confidence{};
    float left{}, top{}, right{}, bottom{}; // Continuous original-frame pixel coordinates.
};
struct DetectionResult {
    std::vector<Detection> objects;
    double elapsed_ms{}; // Preprocessing + inference + postprocessing, excludes model load.
    double preprocess_ms{}, inference_ms{}, postprocess_ms{};
    ExecutionInfo execution;
};
enum class DetectorModel { nano, yolox_s, world_s, world_m, openimages, rf_scale7758628 };
std::string_view model_id(DetectorModel model);
std::string_view model_name(DetectorModel model);
DetectorModel parse_model(std::string_view id);
int model_input_size(DetectorModel model);
int model_class_count(DetectorModel model); // Raw output scores; Open Images has human aliases.
int model_category_count(DetectorModel model); // Distinct canonical categories shown to users.
inline constexpr int recognition_classes = 615; // Stable canonical IDs; COCO 0..79, world-v1 0..99.
std::vector<int64_t> model_output_shape(DetectorModel model);
std::vector<int> model_classes(DetectorModel model);
bool model_has_class(DetectorModel model, int id);
std::string model_vocabulary(DetectorModel model);
std::string world_vocabulary(); // Exact newline-separated metadata; protects class-to-label mapping.

struct DetectorOptions {
    std::filesystem::path model;
    float confidence{0.35f};
    float nms_iou{0.45f};
    DetectorModel variant{DetectorModel::nano};
    DetectorBackend backend{DetectorBackend::cpu}; // Explicit baseline; GUI can opt into automatic GPU/CPU.
    int gpu_device{-1}; // DXGI index; -1 selects a capable adapter with most dedicated memory.
};
std::string_view class_name(int id);

// Explicit contracts for the publisher's Nano (416) and S (640) 0.1.1rc0 exports.
namespace yolox {
inline constexpr int input_size = 416;
inline constexpr int candidates = 3549;
inline constexpr int attributes = 85;
struct Input {
    std::vector<float> tensor;
    double ratio{};
    int resized_width{}, resized_height{};
};
int candidate_count(int size);
Input preprocess(const Frame& frame, int size = input_size);
std::vector<Detection> postprocess(std::span<const float> output, double ratio,
    int width, int height, float confidence, float nms_iou, int size = input_size);
}

// Decoded YOLO-World / Open Images exports: RGB / 255, centered letterbox,
// decoded xywh + per-class scores in [1,4+classes,8400]. No objectness channel.
namespace yolo_world {
struct Input {
    std::vector<float> tensor;
    double ratio{};
    int resized_width{}, resized_height{}, pad_x{}, pad_y{};
};
Input preprocess(const Frame& frame);
std::vector<Detection> postprocess(std::span<const float> output, const Input& input,
    int width, int height, float confidence, float nms_iou, DetectorModel model=DetectorModel::world_s);
}

// Exact experimental trained RF contract: RGB full-image resize512, ImageNet
// normalization; packed normalized boxes plus canonical foreground logits.
namespace rfdetr {
inline constexpr int input_size=512, queries=300, attributes=619;
inline constexpr std::string_view checkpoint_sha256="1b72fc6474780a6805e919db5b1393d7e78b95209debafafce98c929c633f0d7";
std::vector<float> preprocess(const Frame& frame);
std::vector<Detection> postprocess(std::span<const float> output,int width,int height,float confidence,float nms_iou);
}

class Detector {
public:
    explicit Detector(const DetectorOptions& options);
    ~Detector();
    Detector(const Detector&) = delete;
    Detector& operator=(const Detector&) = delete;
    DetectionResult detect(const Frame& frame, std::stop_token stop = {});
    const ExecutionInfo& execution_info() const;
private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};
}
