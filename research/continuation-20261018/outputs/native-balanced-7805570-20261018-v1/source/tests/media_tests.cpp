#include "frametrail/frame_export.hpp"
#include "frametrail/media_reader.hpp"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <stop_token>
#include <string>
#include <vector>

namespace {
void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

template<class Function>
void expect_failure(Function function, const char* message) {
    try { function(); } catch (const std::runtime_error&) { return; }
    throw std::runtime_error(message);
}

void image(const std::filesystem::path& root) {
    frametrail::MediaReader reader(root / "still.png");
    auto frame = reader.read();
    require(frame.has_value(), "Image must decode");
    require(frame->sequence == 0, "Sequence must start at zero");
    require(frame->width == 18 && frame->height == 14, "Image dimensions changed");
    require(frame->stride == 54 && frame->pixels.size() == 756, "RGB layout is wrong");
    require(frame->pixels[0] > 240 && frame->pixels[1] < 10 && frame->pixels[2] < 10,
        "Red image was not converted to RGB");
    require(!reader.read(), "A still image must produce one frame");
    require(!reader.read(), "EOF must remain stable");
    const auto unicode_path = root / std::filesystem::path(u8"entrée 空.png");
    std::filesystem::copy_file(root / "still.png", unicode_path,
        std::filesystem::copy_options::overwrite_existing);
    frametrail::MediaReader unicode_reader(unicode_path);
    require(unicode_reader.read().has_value(), "Unicode media path failed");
    frametrail::write_ppm(*frame, root / "export.ppm");
    require(std::filesystem::file_size(root / "export.ppm") > frame->pixels.size(),
        "PPM export is incomplete");
    frametrail::Frame invalid;
    expect_failure([&] { frametrail::write_ppm(invalid, root / "bad.ppm"); },
        "Invalid RGB frame was accepted");
    // Padding bytes must not leak into a PPM's tightly packed pixel payload.
    frametrail::Frame padded;
    padded.width = 1;
    padded.height = 2;
    padded.stride = 4;
    padded.pixels = {255, 0, 0, 99, 0, 255, 0, 99};
    frametrail::write_ppm(padded, root / "padded.ppm");
    std::ifstream exported(root / "padded.ppm", std::ios::binary);
    const std::string contents((std::istreambuf_iterator<char>(exported)), {});
    const std::string expected("P6\n1 2\n255\n\xff\0\0\0\xff\0", 17);
    require(contents == expected, "PPM export included row padding or incorrect pixels");
}

void delayed_frames(const std::filesystem::path& root) {
    frametrail::MediaReader reader(root / "delayed.mkv");
    auto retained = reader.read();
    require(retained.has_value(), "Video has no first frame");
    const auto original = retained->pixels;
    std::uint64_t count = 1;
    auto previous = retained->timestamp;
    while (auto frame = reader.read()) {
        require(frame->sequence == count, "Frame sequence skipped or repeated");
        require(frame->timestamp && previous && *frame->timestamp > *previous,
            "Presentation timestamps are not ordered");
        previous = frame->timestamp;
        ++count;
    }
    require(count == 10, "Decoder lost delayed B-frames at EOF");
    require(retained->pixels == original, "A later decode overwrote retained frame pixels");
    require(previous && previous->count() == 900000, "Final video timestamp is incorrect");
}

void variable_timestamps(const std::filesystem::path& root) {
    frametrail::MediaReader reader(root / "variable.mkv");
    std::vector<long long> times;
    while (auto frame = reader.read()) {
        require(frame->timestamp.has_value(), "Variable-rate fixture lost timestamps");
        times.push_back(frame->timestamp->count());
    }
    require(times.size() == 10, "Variable-rate frame count is incorrect");
    require(times[0] == 0 && times[1] == 100000 && times[2] == 200000 && times[3] == 400000,
        "Reader replaced variable timing with nominal frame-rate timing");
    require(times.back() == 1600000, "Variable-rate final timestamp is incorrect");
}

void cancellation_and_errors(const std::filesystem::path& root) {
    for (const auto* name : {"missing.mp4", "invalid.txt", "audio.wav"}) {
        expect_failure([&] { frametrail::MediaReader reader(root / name); },
            "Invalid or non-visual input was accepted");
    }
    std::stop_source before;
    before.request_stop();
    expect_failure([&] { frametrail::MediaReader reader(root / "still.png", before.get_token()); },
        "Cancellation before opening was ignored");
    std::stop_source during;
    frametrail::MediaReader reader(root / "delayed.mkv", during.get_token());
    require(reader.read().has_value(), "Cancellation fixture could not decode");
    during.request_stop();
    expect_failure([&] { (void)reader.read(); }, "Cancellation between reads was ignored");

    // Repeated destruction exercises ownership of decoder handles and frames.
    for (int i = 0; i < 30; ++i) {
        frametrail::MediaReader reopened(root / "delayed.mkv");
        require(reopened.read().has_value(), "Reopening failed");
    }
}
} // namespace

int main(int argc, char* argv[]) {
    try {
        require(argc == 2, "Expected fixture directory");
        const auto root = std::filesystem::path(argv[1]);
        image(root);
        delayed_frames(root);
        variable_timestamps(root);
        cancellation_and_errors(root);
        std::cout << "Media contracts passed: RGB, ownership, EOF, VFR, cancellation, errors\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
