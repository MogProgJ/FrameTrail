#include "frametrail/frame_export.hpp"
#include "frametrail/media_reader.hpp"
#include "frametrail/detector.hpp"

#include <charconv>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

void help() {
    std::cout << "FrameTrail 0.3 - native media and CPU detection\n\n"
                 "Usage: frametrail inspect <local-file> [options]\n"
                 "  --csv <path>       Export decoded frame metadata\n"
                 "  --preview <path>   Export the first decoded frame as a PPM image\n"
                 "  --max-frames <n>   Stop after n frames (positive integer)\n"
                 "  --detect <model>   Run the pinned YOLOX-Nano ONNX model on the CPU\n"
                 "  --detections <csv> Export detections (requires --detect)\n"
                 "  --help             Show this help\n\n"
                 "Use frametrail-desktop for the preview window.\n"
                 "Tracking and live input are still planned.\n";
}

std::filesystem::path path_from_utf8(const std::string& value) {
    const std::u8string utf8(value.begin(), value.end());
    return std::filesystem::path(utf8);
}

void check_output_path(const std::filesystem::path& path,
                       const std::filesystem::path& input) {
    if (std::filesystem::exists(path)) {
        throw std::runtime_error("Output already exists; choose a new output path");
    }
    if (std::filesystem::absolute(path).lexically_normal() ==
        std::filesystem::absolute(input).lexically_normal()) {
        throw std::runtime_error("Output must not replace the source media");
    }
}

int run(const std::vector<std::string>& args) {
    if (args.size() == 1 && args[0] == "--help") {
        help();
        return 0;
    }
    if (args.size() < 2 || args[0] != "inspect") {
        help();
        return 2;
    }
    const auto input = path_from_utf8(args[1]);
    std::optional<std::filesystem::path> csv_path;
    std::optional<std::filesystem::path> preview_path;
    std::optional<std::filesystem::path> model_path, detections_path;
    std::optional<std::uint64_t> maximum;
    for (std::size_t i = 2; i < args.size(); ++i) {
        const auto& option = args[i];
        if (option != "--csv" && option != "--preview" && option != "--max-frames" && option != "--detect" && option != "--detections") {
            throw std::runtime_error("Unknown option: " + option);
        }
        if (++i == args.size()) {
            throw std::runtime_error("Missing value for " + option);
        }
        if (option == "--csv") {
            if (csv_path) throw std::runtime_error("Duplicate --csv option");
            csv_path = path_from_utf8(args[i]);
        } else if (option == "--preview") {
            if (preview_path) throw std::runtime_error("Duplicate --preview option");
            preview_path = path_from_utf8(args[i]);
        } else if (option == "--detect") {
            if (model_path) throw std::runtime_error("Duplicate --detect option");
            model_path=path_from_utf8(args[i]);
        } else if (option == "--detections") {
            if (detections_path) throw std::runtime_error("Duplicate --detections option");
            detections_path=path_from_utf8(args[i]);
        } else {
            if (maximum) throw std::runtime_error("Duplicate --max-frames option");
            std::uint64_t value{};
            const auto* begin = args[i].data();
            const auto* end = begin + args[i].size();
            const auto parsed = std::from_chars(begin, end, value);
            if (parsed.ec != std::errc{} || parsed.ptr != end || value == 0) {
                throw std::runtime_error("--max-frames must be a positive integer");
            }
            maximum = value;
        }
    }
    if (csv_path) check_output_path(*csv_path, input);
    if (preview_path) check_output_path(*preview_path, input);
    if (detections_path) {
        if (!model_path) throw std::runtime_error("--detections requires --detect <model>");
        check_output_path(*detections_path,input);
        for (const auto& other:{csv_path,preview_path}) {
            if (other && std::filesystem::absolute(*other).lexically_normal()==std::filesystem::absolute(*detections_path).lexically_normal())
                throw std::runtime_error("Each export needs a different output path");
        }
    }
    if (csv_path && preview_path &&
        std::filesystem::absolute(*csv_path).lexically_normal() ==
            std::filesystem::absolute(*preview_path).lexically_normal()) {
        throw std::runtime_error("CSV and preview need different output paths");
    }

    const auto start = std::chrono::steady_clock::now();
    frametrail::MediaReader reader(input);
    std::unique_ptr<frametrail::Detector> detector;
    if (model_path) detector=std::make_unique<frametrail::Detector>(frametrail::DetectorOptions{*model_path});
    std::ofstream detections_csv;
    if (detections_path) {
        detections_csv.open(*detections_path,std::ios::binary);
        if (!detections_csv) throw std::runtime_error("Cannot open detection CSV");
        detections_csv << "sequence,timestamp_us,class_id,label,confidence,left,top,right,bottom,detection_ms\n";
    }
    std::cout << "Codec: " << reader.info().codec << "\nInitial dimensions: "
              << reader.info().width << 'x' << reader.info().height << '\n';
    std::ofstream csv;
    if (csv_path) {
        csv.open(*csv_path, std::ios::binary);
        if (!csv) throw std::runtime_error("Cannot open CSV output file");
        csv << "sequence,timestamp_us,width,height,stride,bytes\n";
    }
    std::uint64_t count = 0;
    std::uint64_t object_count=0;
    double detection_ms=0;
    std::optional<std::chrono::microseconds> first;
    std::optional<std::chrono::microseconds> last;
    while (!maximum || count < *maximum) {
        auto frame = reader.read();
        if (!frame) break;
        if (count == 0) {
            first = frame->timestamp;
            if (preview_path) frametrail::write_ppm(*frame, *preview_path);
        }
        last = frame->timestamp;
        if (detector) {
            const auto result=detector->detect(*frame);
            object_count+=result.objects.size();
            detection_ms+=result.elapsed_ms;
            for (const auto& object:result.objects) {
                if (detections_path) {
                    detections_csv << frame->sequence << ',';
                    if (frame->timestamp) detections_csv << frame->timestamp->count();
                    detections_csv << ',' << object.class_id << ',' << frametrail::class_name(object.class_id) << ','
                        << object.confidence << ',' << object.left << ',' << object.top << ',' << object.right << ','
                        << object.bottom << ',' << result.elapsed_ms << '\n';
                }
            }
            if (detections_path && !detections_csv) throw std::runtime_error("Failed writing detection CSV");
        }
        if (csv_path) {
            csv << frame->sequence << ',';
            if (frame->timestamp) csv << frame->timestamp->count();
            csv << ',' << frame->width << ',' << frame->height << ','
                << frame->stride << ',' << frame->pixels.size() << '\n';
            if (!csv) throw std::runtime_error("Failed while writing frame CSV");
        }
        ++count;
    }
    if (csv_path) {
        csv.close();
        if (!csv) throw std::runtime_error("Failed to finish frame CSV");
    }
    if (count == 0) throw std::runtime_error("No visual frames could be decoded");
    if (detections_path) {
        detections_csv.close();
        if (!detections_csv) throw std::runtime_error("Failed to finish detection CSV");
    }
    if (detector) std::cout << "Detections across frames: " << object_count
        << "\nAverage CPU detection (ms/frame): " << detection_ms/count << '\n';
    const double elapsed = std::chrono::duration<double>(
        std::chrono::steady_clock::now() - start).count();
    std::cout << "Frames decoded: " << count << "\nFirst timestamp (us): ";
    if (first) std::cout << first->count(); else std::cout << "unavailable";
    std::cout << "\nLast timestamp (us): ";
    if (last) std::cout << last->count(); else std::cout << "unavailable";
    std::cout << std::fixed << std::setprecision(3) << "\nElapsed (s): " << elapsed
              << (detector ? "\nDecode/detect/export throughput (fps): " : "\nDecode/export throughput (fps): ") << (elapsed > 0 ? count / elapsed : 0)
              << "\nStop condition: "
              << ((maximum && count == *maximum) ? "frame limit" : "end of file") << '\n';
    return 0;
}

int checked_run(const std::vector<std::string>& args) {
    try {
        return run(args);
    } catch (const std::exception& error) {
        std::cerr << "FrameTrail: " << error.what() << '\n';
        return 1;
    }
}

} // namespace

#ifdef _WIN32
int wmain(int argc, wchar_t* argv[]) {
    std::vector<std::string> args;
    for (int i = 1; i < argc; ++i) {
        const auto utf8 = std::filesystem::path(argv[i]).u8string();
        args.emplace_back(utf8.begin(), utf8.end());
    }
    return checked_run(args);
}
#else
int main(int argc, char* argv[]) {
    return checked_run(std::vector<std::string>(argv + 1, argv + argc));
}
#endif
