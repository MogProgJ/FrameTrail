#pragma once
#include "frametrail/frame.hpp"
#include <filesystem>
#include <memory>
#include <span>
#include <stop_token>
#include <string_view>

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
enum class DetectorModel { nano, yolox_s };
std::string_view model_id(DetectorModel model);
std::string_view model_name(DetectorModel model);
DetectorModel parse_model(std::string_view id);
int model_input_size(DetectorModel model);

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
