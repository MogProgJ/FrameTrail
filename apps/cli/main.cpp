#include "frametrail/frame_export.hpp"
#include "frametrail/media_reader.hpp"
#include "frametrail/detector.hpp"
#include "frametrail/tracker.hpp"
#include "frametrail/frame_tracker.hpp"
#include "frametrail/run_store.hpp"

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
#include <set>
#include <algorithm>
#include <cwctype>

namespace {

void help() {
    std::cout << "FrameTrail 0.12 - Native analysis, saved review and live webcam\n\n"
                 "Usage: frametrail inspect <local-file> [options]\n"
                 "  --csv <path>       Export decoded frame metadata\n"
                 "  --preview <path>   Export the first decoded frame as a PPM image\n"
                 "  --max-frames <n>   Stop after n frames (positive integer)\n"
                 "  --detect <model>   Run a supported native ONNX model\n"
                 "  --model-type <id>  nano (default), small, world-s, world-m, openimages, rfdetr-7758628, rfdetr-7805570\n"
                 "  --backend <id>     cpu (default), auto (GPU/CPU), or directml (strict GPU)\n"
                 "  --gpu-device <n>   Optional DXGI adapter index; default selects capable GPU\n"
                 "  --confidence <n>   Confidence in (0,1], default 0.35\n"
                 "  --detections <csv> Export detections (requires --detect)\n"
                 "  --track            Track people/vehicles (requires --detect)\n"
                 "  --association <id> greedy (default), repair (experimental global repair)\n"
                 "  --tracks <csv>     Export observed track boxes (requires --track)\n"
                 "  --events <csv>     Export line crossings (requires --track)\n"
                 "  --line x1,y1,x2,y2 Normalized endpoints [0,1]; default 0.1,0.5,0.9,0.5\n"
                 "  --direction <d>    both, forward (- to +), or reverse (+ to -)\n"
                 "  --classes <ids>    FrameTrail IDs (COCO 0..79, World additions 80..99, Open Images through 614; see vocabulary); default 0,1,2,3,5,7\n"
                 "  --save-run <path>  Save a whole-file run (requires --detect and --track)\n"
                 "  --profile <csv>    Export per-frame pipeline timings and RGB bytes\n"
                 "  --help             Show this help\n\n"
                 "Use frametrail-desktop for the preview window.\n"
                 "Usage: frametrail run <saved-run> [--export <new-csv>]\n"
                 "Saved run inspection/export needs no model or source file.\n"
                 "One-frame images have detections only. Use the desktop Live camera window for a webcam.\n";
}

std::vector<std::string_view> split(const std::string& value) {
    std::vector<std::string_view> parts;
    std::string_view remaining(value);
    for (;;) {
        const auto comma = remaining.find(',');
        parts.push_back(remaining.substr(0,comma));
        if (comma == std::string_view::npos) return parts;
        remaining.remove_prefix(comma+1);
    }
}
template<class T> T number(std::string_view value) {
    T result{};
    const auto parsed = std::from_chars(value.data(),value.data()+value.size(),result);
    if (parsed.ec != std::errc{} || parsed.ptr != value.data()+value.size())
        throw std::runtime_error("Invalid numeric option value");
    return result;
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

std::filesystem::path output_key(const std::filesystem::path& path) {
    auto key = std::filesystem::weakly_canonical(std::filesystem::absolute(path));
#ifdef _WIN32
    auto native = key.native();
    std::ranges::transform(native,native.begin(),[](wchar_t c) { return wchar_t(std::towlower(c)); });
    key = native;
#endif
    return key;
}

int run(const std::vector<std::string>& args) {
    if (args.size() == 1 && args[0] == "--help") {
        help();
        return 0;
    }
    if(args.size()>=2 && args[0]=="run") {
        if(args.size()!=2 && (args.size()!=4 || args[2]!="--export"))throw std::runtime_error("Use run <saved-run> [--export <new-csv>]");
        const frametrail::RunStore saved(path_from_utf8(args[1]));const auto summary=saved.summary();
        std::cout<<"Run status: "<<summary.status<<"\nFrames analysed: "<<summary.processed_frames
            <<"\nModel: "<<frametrail::model_name(summary.configuration.detector.variant)<<"\nConfidence: "<<summary.configuration.detector.confidence<<'\n';
        if(summary.configuration.kind==frametrail::RunKind::crossings)
            std::cout<<"Events saved: "<<summary.event_count<<"\nCrossings (- to +): "<<summary.forward<<"\nCrossings (+ to -): "<<summary.reverse<<'\n';
        std::cout<<"Execution provider: "<<summary.execution.provider<<"\nRuntime: "<<summary.execution.runtime<<"\nDevice: "<<summary.execution.device<<"\nCPU fallback: "<<summary.execution.fallback<<'\n';
        if(!summary.error.empty())std::cout<<"Run error: "<<summary.error<<'\n';
        if(summary.configuration.kind==frametrail::RunKind::appearances)
            std::cout<<"Object appearances: "<<summary.appearance_count<<"\nObject types: "<<summary.class_count<<'\n';
        if(args.size()==4) {
            if(summary.configuration.kind==frametrail::RunKind::appearances)saved.export_appearances_csv(path_from_utf8(args[3]));
            else saved.export_csv(path_from_utf8(args[3]));
        }
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
    std::optional<std::filesystem::path> tracks_path, events_path;
    std::optional<std::filesystem::path> saved_path, profile_path;
    bool tracking = false;
    frametrail::DetectorOptions detector_options;
    frametrail::TrackingOptions tracking_options;
    std::set<std::string> seen;
    std::optional<std::uint64_t> maximum;
    for (std::size_t i = 2; i < args.size(); ++i) {
        const auto& option = args[i];
        if (!seen.insert(option).second) throw std::runtime_error("Duplicate option: " + option);
        if (option == "--track") { tracking = true; continue; }
        if (option != "--csv" && option != "--preview" && option != "--max-frames" && option != "--detect" && option != "--detections" &&
            option != "--tracks" && option != "--events" && option != "--line" && option != "--direction" && option != "--classes" && option != "--save-run" && option != "--profile" && option != "--model-type" && option != "--confidence" && option != "--backend" && option != "--gpu-device" && option != "--association") {
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
        } else if (option == "--model-type") {
            detector_options.variant=frametrail::parse_model(args[i]);
        } else if (option == "--backend") {
            detector_options.backend=frametrail::parse_backend(args[i]);
        } else if (option == "--association") {
            tracking_options.association=frametrail::parse_association(args[i]);
        } else if (option == "--gpu-device") {
            detector_options.gpu_device=number<int>(args[i]);
        } else if (option == "--confidence") {
            detector_options.confidence=number<float>(args[i]);
        } else if (option == "--detections") {
            if (detections_path) throw std::runtime_error("Duplicate --detections option");
            detections_path=path_from_utf8(args[i]);
        } else if (option == "--tracks") {
            tracks_path = path_from_utf8(args[i]);
        } else if (option == "--events") {
            events_path = path_from_utf8(args[i]);
        } else if (option == "--profile") {
            profile_path = path_from_utf8(args[i]);
        } else if (option == "--save-run") {
            saved_path = path_from_utf8(args[i]);
        } else if (option == "--line") {
            const auto parts = split(args[i]);
            if (parts.size() != 4) throw std::runtime_error("--line needs x1,y1,x2,y2");
            tracking_options.line->a = {number<double>(parts[0]),number<double>(parts[1])};
            tracking_options.line->b = {number<double>(parts[2]),number<double>(parts[3])};
        } else if (option == "--direction") {
            const auto& d = args[i];
            if (d == "both") tracking_options.line->direction = frametrail::CrossingDirection::both;
            else if (d == "forward") tracking_options.line->direction = frametrail::CrossingDirection::negative_to_positive;
            else if (d == "reverse") tracking_options.line->direction = frametrail::CrossingDirection::positive_to_negative;
            else throw std::runtime_error("--direction must be both, forward, or reverse");
        } else if (option == "--classes") {
            tracking_options.classes.clear();
            for (const auto& part : split(args[i])) tracking_options.classes.push_back(number<int>(part));
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
    if (!model_path && (seen.contains("--model-type") || seen.contains("--confidence") || seen.contains("--backend") || seen.contains("--gpu-device")))
        throw std::runtime_error("Model settings require --detect");
    if (model_path) detector_options.model=*model_path;
    if (tracking && !model_path) throw std::runtime_error("--track requires --detect <model>");
    if(saved_path && (!tracking || maximum))throw std::runtime_error("--save-run requires --track and whole-file analysis (no --max-frames)");
    if (!tracking && (tracks_path || events_path || seen.contains("--line") || seen.contains("--direction") || seen.contains("--classes") || seen.contains("--association")))
        throw std::runtime_error("Track exports and rule settings require --track");
    std::unique_ptr<frametrail::FrameTracker> tracker;
    if(tracking)for(const auto id:tracking_options.classes)if(!frametrail::model_has_class(detector_options.variant,id))
        throw std::runtime_error("Tracking category is not supported by the selected model");
    if (tracking) tracker = std::make_unique<frametrail::FrameTracker>(tracking_options);
    const std::vector<std::optional<std::filesystem::path>> outputs{csv_path,preview_path,detections_path,tracks_path,events_path,saved_path,profile_path};
    std::set<std::filesystem::path> output_names;
    for (const auto& path : outputs) if (path) {
        check_output_path(*path,input);
        if (!output_names.insert(output_key(*path)).second)
            throw std::runtime_error("Each export needs a different output path");
    }
    if (detections_path && !model_path) throw std::runtime_error("--detections requires --detect <model>");

    const auto start = std::chrono::steady_clock::now();
    frametrail::MediaReader reader(input);
    std::unique_ptr<frametrail::Detector> detector;
    if (model_path) detector=std::make_unique<frametrail::Detector>(detector_options);
    struct SavedRunGuard {
        std::optional<frametrail::RunStore> value;
        bool finished{};
        ~SavedRunGuard() {if(value && !finished){try{value->finish("failed","CLI did not finish; see its error output");}catch(...){}}}
    } saved;
    if(saved_path) {saved.value.emplace(frametrail::RunStore::create(*saved_path,{input,detector_options,tracking_options},reader.info()));saved.value->record_execution(detector->execution_info());}
    std::ofstream profile_csv;
    if (profile_path) {
        profile_csv.open(*profile_path, std::ios::binary);
        if (!profile_csv) throw std::runtime_error("Cannot open profile CSV");
        profile_csv << "sequence,timestamp_us,width,height,rgb_bytes,decode_rgb_ms,preprocess_ms,inference_ms,postprocess_ms,tracking_ms,pipeline_ms,scene_boundary,scene_difference,scene_histogram_distance\n";
        profile_csv << std::fixed << std::setprecision(6);
    }
    std::ofstream detections_csv;
    std::ofstream tracks_csv, events_csv;
    if (tracks_path) {
        tracks_csv.open(*tracks_path,std::ios::binary);
        if (!tracks_csv) throw std::runtime_error("Cannot open track CSV");
        tracks_csv << "sequence,timestamp_us,track_id,class_id,label,confirmed,confidence,left,top,right,bottom\n";
    }
    if (events_path) {
        events_csv.open(*events_path,std::ios::binary);
        if (!events_csv) throw std::runtime_error("Cannot open event CSV");
        events_csv << "event_id,sequence,timestamp_us,track_id,class_id,label,direction,x_normalized,y_normalized\n";
    }
    std::uint64_t forward = 0, reverse = 0, scene_boundaries=0;
    double tracking_ms = 0;
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
        const auto frame_started = std::chrono::steady_clock::now();
        auto frame = reader.read();
        const auto decoded = std::chrono::steady_clock::now();
        double prepare_ms=0, infer_ms=0, post_ms=0, rules_ms=0;
        bool scene_boundary=false;double scene_difference=0,scene_histogram=0;
        if (!frame) break;
        if (count == 0) {
            first = frame->timestamp;
            if (preview_path) frametrail::write_ppm(*frame, *preview_path);
        }
        last = frame->timestamp;
        if (detector) {
            const auto result=detector->detect(*frame);
            if(saved.value)saved.value->record_execution(result.execution);
            prepare_ms=result.preprocess_ms; infer_ms=result.inference_ms; post_ms=result.postprocess_ms;
            object_count+=result.objects.size();
            detection_ms+=result.elapsed_ms;
            if (tracker) {
                const auto temporal = tracker->update(result.objects,*frame);
                scene_boundary=temporal.scene_boundary;scene_difference=temporal.scene_difference;scene_histogram=temporal.scene_histogram_distance;
                if(scene_boundary)++scene_boundaries;
                tracking_ms += temporal.elapsed_ms; rules_ms=temporal.elapsed_ms;
                if(saved.value)saved.value->record_frame(*frame,temporal.events);
                if (frame->sequence > 0) {
                    forward = temporal.negative_to_positive; reverse = temporal.positive_to_negative;
                    for (const auto& object : temporal.objects) if (tracks_path) {
                        const auto& d = object.detection;
                        tracks_csv << frame->sequence << ',';
                        if (frame->timestamp) tracks_csv << frame->timestamp->count();
                        tracks_csv << ',' << object.id << ',' << d.class_id << ',' << frametrail::class_name(d.class_id) << ','
                            << object.confirmed << ',' << d.confidence << ',' << d.left << ',' << d.top << ',' << d.right << ',' << d.bottom << '\n';
                    }
                    for (const auto& event : temporal.events) if (events_path) {
                        events_csv << event.id << ',' << event.sequence << ',';
                        if (event.timestamp) events_csv << event.timestamp->count();
                        events_csv << ',' << event.track_id << ',' << event.class_id << ',' << frametrail::class_name(event.class_id) << ','
                            << frametrail::direction_name(event.direction) << ',' << event.position.x << ',' << event.position.y << '\n';
                    }
                }
                if ((tracks_path && !tracks_csv) || (events_path && !events_csv)) throw std::runtime_error("Failed writing tracking exports");
            }
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
        if (profile_path) {
            const double decode_ms=std::chrono::duration<double,std::milli>(decoded-frame_started).count();
            const double pipeline_ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-frame_started).count();
            profile_csv << frame->sequence << ',';
            if (frame->timestamp) profile_csv << frame->timestamp->count();
            profile_csv << ',' << frame->width << ',' << frame->height << ',' << frame->pixels.size() << ','
                << decode_ms << ',' << prepare_ms << ',' << infer_ms << ',' << post_ms << ',' << rules_ms << ',' << pipeline_ms
                << ',' << scene_boundary << ',' << scene_difference << ',' << scene_histogram << '\n';
            if (!profile_csv) throw std::runtime_error("Failed writing profile CSV");
        }
        ++count;
    }
    if (csv_path) {
        csv.close();
        if (!csv) throw std::runtime_error("Failed to finish frame CSV");
    }
    if (profile_path) {
        profile_csv.close();
        if (!profile_csv) throw std::runtime_error("Failed to finish profile CSV");
    }
    if (count == 0) throw std::runtime_error("No visual frames could be decoded");
    if (detections_path) {
        detections_csv.close();
        if (!detections_csv) throw std::runtime_error("Failed to finish detection CSV");
    }
    if (detector) std::cout << "Execution provider: " << detector->execution_info().provider << "\nRuntime: " << detector->execution_info().runtime << "\nDevice: " << detector->execution_info().device << "\nFallback: " << detector->execution_info().fallback << "\nModel: " << frametrail::model_name(detector_options.variant) << "\nDetections across frames: " << object_count
        << "\nAverage detection (ms/frame): " << detection_ms/count << '\n';
    for (auto* stream : {&tracks_csv,&events_csv}) if (stream->is_open()) {
        stream->close();
        if (!*stream) throw std::runtime_error("Failed to finish tracking export");
    }
    if (tracker) std::cout << "Crossings (- to +): " << forward << "\nCrossings (+ to -): " << reverse
        << "\nAssociation: " << frametrail::association_name(tracking_options.association)
        << "\nScene boundary resets: " << scene_boundaries << "\nAverage tracking/rules (ms/frame): " << tracking_ms/count << '\n';
    if(saved.value) {
        const auto info=saved.value->summary();
        if(!saved.value->source_available() || frametrail::file_stamp(*model_path)!=info.model_stamp)
            throw std::runtime_error("Source or model changed during analysis; saved results are partial");
        saved.value->finish("completed");saved.finished=true;
    }
    const double elapsed = std::chrono::duration<double>(
        std::chrono::steady_clock::now() - start).count();
    std::cout << "Frames decoded: " << count << "\nFirst timestamp (us): ";
    if (first) std::cout << first->count(); else std::cout << "unavailable";
    std::cout << "\nLast timestamp (us): ";
    if (last) std::cout << last->count(); else std::cout << "unavailable";
    std::cout << std::fixed << std::setprecision(3) << "\nElapsed (s): " << elapsed
              << (tracker ? "\nDecode/detect/track/export throughput (fps): " :
                  detector ? "\nDecode/detect/export throughput (fps): " : "\nDecode/export throughput (fps): ") << (elapsed > 0 ? count / elapsed : 0)
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
