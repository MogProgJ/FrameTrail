#pragma once
#include "frametrail/frame.hpp"
#include <filesystem>
#include <memory>
#include <span>
#include <stop_token>
#include <string_view>

namespace frametrail {
struct Detection {
    int class_id{};
    float confidence{};
    float left{}, top{}, right{}, bottom{}; // Continuous original-frame pixel coordinates.
};
struct DetectionResult {
    std::vector<Detection> objects;
    double elapsed_ms{}; // Preprocessing + inference + postprocessing, excludes model load.
};
struct DetectorOptions {
    std::filesystem::path model;
    float confidence{0.35f};
    float nms_iou{0.45f};
};
std::string_view class_name(int id);

// Fixed contract for the official YOLOX-Nano 0.1.1rc0 ONNX export.
namespace yolox {
inline constexpr int input_size = 416;
inline constexpr int candidates = 3549;
inline constexpr int attributes = 85;
struct Input {
    std::vector<float> tensor;
    double ratio{};
    int resized_width{}, resized_height{};
};
Input preprocess(const Frame& frame);
std::vector<Detection> postprocess(std::span<const float> output, double ratio,
    int width, int height, float confidence, float nms_iou);
}

class Detector {
public:
    explicit Detector(const DetectorOptions& options);
    ~Detector();
    Detector(const Detector&) = delete;
    Detector& operator=(const Detector&) = delete;
    DetectionResult detect(const Frame& frame, std::stop_token stop = {});
private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};
}
