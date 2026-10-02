#include "frametrail/frame_export.hpp"
#include "frametrail/media_reader.hpp"

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
    std::cout << "FrameTrail 0.2 - native media inspector\n\n"
                 "Usage: frametrail inspect <local-file> [options]\n"
                 "  --csv <path>       Export decoded frame metadata\n"
                 "  --preview <path>   Export the first decoded frame as a PPM image\n"
                 "  --max-frames <n>   Stop after n frames (positive integer)\n"
                 "  --help             Show this help\n\n"
                 "Use frametrail-desktop for the preview window.\n"
                 "Object detection, tracking, and live input are still planned.\n";
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
    std::optional<std::uint64_t> maximum;
    for (std::size_t i = 2; i < args.size(); ++i) {
        const auto& option = args[i];
        if (option != "--csv" && option != "--preview" && option != "--max-frames") {
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
    if (csv_path && preview_path &&
        std::filesystem::absolute(*csv_path).lexically_normal() ==
            std::filesystem::absolute(*preview_path).lexically_normal()) {
        throw std::runtime_error("CSV and preview need different output paths");
    }

    const auto start = std::chrono::steady_clock::now();
    frametrail::MediaReader reader(input);
    std::cout << "Codec: " << reader.info().codec << "\nInitial dimensions: "
              << reader.info().width << 'x' << reader.info().height << '\n';
    std::ofstream csv;
    if (csv_path) {
        csv.open(*csv_path, std::ios::binary);
        if (!csv) throw std::runtime_error("Cannot open CSV output file");
        csv << "sequence,timestamp_us,width,height,stride,bytes\n";
    }
    std::uint64_t count = 0;
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
    const double elapsed = std::chrono::duration<double>(
        std::chrono::steady_clock::now() - start).count();
    std::cout << "Frames decoded: " << count << "\nFirst timestamp (us): ";
    if (first) std::cout << first->count(); else std::cout << "unavailable";
    std::cout << "\nLast timestamp (us): ";
    if (last) std::cout << last->count(); else std::cout << "unavailable";
    std::cout << std::fixed << std::setprecision(3) << "\nElapsed (s): " << elapsed
              << "\nDecode/export throughput (fps): " << (elapsed > 0 ? count / elapsed : 0)
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
