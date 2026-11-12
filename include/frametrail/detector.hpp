#pragma once
#include "frametrail/frame.hpp"
#include <array>
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
enum class DetectorModel { nano, yolox_s, world_s, world_m, openimages, rf_scale7758628, rf_balanced7805570, rf_openimages };
bool is_rf_model(DetectorModel model);
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
    // Zoom: also run the model on four overlapping, enlarged quarters of the frame and merge the boxes, so small
    // objects get more model pixels. About five model runs per frame instead of one.
    bool zoom{};
    // Combined: a YOLOX-S model run on the same frame next to the main model, boxes merged (the more confident box
    // wins among same or related classes on one object). Empty: no companion. Only with an RF-DETR Open Images main
    // model, whose vocabulary already contains YOLOX's 80 categories.
    std::filesystem::path companion;
    // RF-DETR Open Images only: apply <model>.calibration.csv when it sits next to the model (see rfdetr::Calibration).
    // Off shows the model's raw scores, for measuring.
    bool calibrate{true};
};
// "RF-DETR Open Images (trained)", or "... + YOLOX-S" for a combined detector: names a run's detector in reports and reviews.
std::string detector_name(const DetectorOptions& options);
// Zoom tiles: the four quarters, each zoom_tile of the frame's width and height, overlapping in the middle.
inline constexpr double zoom_tile=0.55;
// Merges whole-frame and tile detections (already in frame coordinates): drops tile boxes cut by a tile's inner
// edge, then keeps the most confident box among same or related-class boxes on one object (IoU above `iou`).
std::vector<Detection> merge_zoom(std::vector<Detection> whole,std::vector<std::pair<std::vector<Detection>,std::array<float,4>>> tiles,
    int width,int height,float iou=0.5f);
std::string_view class_name(int id);
// Open Images nests its classes: a dog is also a carnivore, a mammal and an animal; a taxi is also a car.
bool is_ancestor(int ancestor, int category);
// Same class, nested classes, or classes sharing an Open Images parent (car and truck are both land vehicles):
// a detector may flicker between them on one object, so a track may change between them.
bool related_classes(int a, int b);
// Drops a box whose class is a parent of another box's class on the same object (IoU above `iou`), so a dog shows
// as Dog rather than Dog plus Animal. Also drops a few second labels the hierarchy does not nest (wheel on a bicycle
// wheel, tire on a wheel, clothing on a person; IoU above 0.5). Applied to the Open Images models' detections.
std::vector<Detection> hide_parent_duplicates(std::vector<Detection> detections, float iou = 0.7f);

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
// rf_openimages is any training/export.py export: identified by its profile, vocabulary
// and preprocessing metadata instead of one pinned checkpoint, so retrained models drop in.
namespace rfdetr {
inline constexpr int input_size=512, queries=300, attributes=619;
inline constexpr std::string_view checkpoint_sha256="1b72fc6474780a6805e919db5b1393d7e78b95209debafafce98c929c633f0d7";
std::string_view checkpoint_for(DetectorModel model); // Empty when the profile pins no checkpoint.
std::vector<float> preprocess(const Frame& frame);
// Per-class score calibration, fitted by training/calibrate.py on human-verified validation images:
// score = sigmoid(slope * logit + offset), an estimate of "chance this box is right". The trained model's raw scores
// are not comparable between classes (a correct Bowl box often scores 0.15), and one confidence setting serves all.
// Classes without an entry keep their raw score.
struct Calibration {
    std::array<float,recognition_classes> slope, offset;
    int classes{}; // Entries read from the file.
    Calibration(){slope.fill(1.f);offset.fill(0.f);}
};
// File next to the model: rfdetr_openimages.onnx -> rfdetr_openimages.calibration.csv.
std::filesystem::path calibration_path(const std::filesystem::path& model);
// Reads "class_id,slope,offset[,...]" rows after a header line. Throws std::runtime_error on a malformed file.
Calibration read_calibration(const std::filesystem::path& file);
std::vector<Detection> postprocess(std::span<const float> output,int width,int height,float confidence,float nms_iou,
    const Calibration* calibration=nullptr);
}

class Detector {
public:
    explicit Detector(const DetectorOptions& options);
    ~Detector();
    Detector(const Detector&) = delete;
    Detector& operator=(const Detector&) = delete;
    DetectionResult detect(const Frame& frame, std::stop_token stop = {});
    const ExecutionInfo& execution_info() const;
    int calibrated_classes() const; // 0 when no score calibration is applied.
private:
    DetectionResult detect_once(const Frame& frame, std::stop_token stop);
    DetectionResult detect_main(const Frame& frame, std::stop_token stop);
    struct Impl;
    std::unique_ptr<Impl> impl_;
    std::unique_ptr<Detector> companion_;
};
}
