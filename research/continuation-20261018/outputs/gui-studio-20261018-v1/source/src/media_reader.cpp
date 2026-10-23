#include "frametrail/media_reader.hpp"

extern "C" {
#include <libavcodec/avcodec.h>
#include <libavdevice/avdevice.h>
#include <libavformat/avformat.h>
#include <libavutil/error.h>
#include <libavutil/imgutils.h>
#include <libswscale/swscale.h>
}

#include <cerrno>
#include <limits>
#include <stdexcept>
#include <utility>
#include <mutex>
#include <thread>

namespace frametrail {
namespace {

std::string error_text(int code) {
    char buffer[AV_ERROR_MAX_STRING_SIZE]{};
    av_strerror(code, buffer, sizeof(buffer));
    return buffer;
}

void check(int code, const char* operation) {
    if (code < 0) {
        throw std::runtime_error(std::string(operation) + ": " + error_text(code));
    }
}

struct FormatDeleter {
    void operator()(AVFormatContext* context) const { avformat_close_input(&context); }
};
struct CodecDeleter {
    void operator()(AVCodecContext* context) const { avcodec_free_context(&context); }
};
struct PacketDeleter {
    void operator()(AVPacket* packet) const { av_packet_free(&packet); }
};
struct FrameDeleter {
    void operator()(AVFrame* frame) const { av_frame_free(&frame); }
};
struct ScaleDeleter {
    void operator()(SwsContext* context) const { sws_freeContext(context); }
};
const AVInputFormat* camera_format() {
    static std::once_flag registered;
    std::call_once(registered,[]{avdevice_register_all();});
    const auto* format=av_find_input_format("dshow");
    if(!format)throw std::runtime_error("This build does not support Windows DirectShow cameras");
    return format;
}

} // namespace

struct MediaReader::Impl {
    std::stop_token stop;
    std::unique_ptr<AVFormatContext, FormatDeleter> format;
    std::unique_ptr<AVCodecContext, CodecDeleter> codec;
    std::unique_ptr<AVPacket, PacketDeleter> packet;
    std::unique_ptr<AVFrame, FrameDeleter> decoded;
    std::unique_ptr<SwsContext, ScaleDeleter> scale;
    MediaInfo metadata;
    int stream_index{-1};
    AVRational time_base{};
    std::optional<std::int64_t> origin;
    std::uint64_t sequence{};
    bool draining{};
    bool ended{};
    bool live{};

    void check_cancelled() const {
        if (stop.stop_requested()) {
            throw std::runtime_error("Media decoding cancelled");
        }
    }

    static int interrupt(void* opaque) {
        return static_cast<Impl*>(opaque)->stop.stop_requested() ? 1 : 0;
    }

    void open(const std::filesystem::path& path, const CameraInput* camera=nullptr) {
        check_cancelled();
        live=camera!=nullptr;
        if (!live && !std::filesystem::is_regular_file(path)) {
            throw std::runtime_error("Input must be an existing local media file");
        }
        const auto utf8 = live ? std::u8string{} : std::filesystem::absolute(path).u8string();
        const std::string filename=live ? "video="+camera->device : std::string(utf8.begin(),utf8.end());
        const auto* input_format=live ? camera_format() : nullptr;
        AVFormatContext* context = avformat_alloc_context();
        if (!context) {
            throw std::bad_alloc();
        }
        context->interrupt_callback = {interrupt, this};
        if(live) {
            context->flags |= AVFMT_FLAG_NONBLOCK;
            context->max_picture_buffer=16*1024*1024;
        }
        AVDictionary* options = nullptr;
        const int option_result = av_dict_set(&options, "protocol_whitelist", "file", 0);
        if (option_result < 0) {
            avformat_free_context(context);
            av_dict_free(&options);
            check(option_result, "Configure local-file protocols");
        }
        if(live && camera->width>0) {
            const auto size=std::to_string(camera->width)+"x"+std::to_string(camera->height);
            av_dict_set(&options,"video_size",size.c_str(),0);
            av_dict_set(&options,"framerate",std::to_string(camera->fps).c_str(),0);
        }
        const int result = avformat_open_input(&context, filename.c_str(), input_format, &options);
        av_dict_free(&options);
        format.reset(context);
        check_cancelled();
        check(result, live ? "Open camera (check Windows camera permission, other camera apps, and format)" : "Open media");
        if(!live)check(avformat_find_stream_info(format.get(), nullptr), "Read stream information");
        check_cancelled();

        const AVCodec* decoder = nullptr;
        stream_index = av_find_best_stream(format.get(), AVMEDIA_TYPE_VIDEO, -1, -1, &decoder, 0);
        check(stream_index, "Find an image/video stream");
        const AVStream* stream = format->streams[stream_index];
        codec.reset(avcodec_alloc_context3(decoder));
        if (!codec) {
            throw std::bad_alloc();
        }
        check(avcodec_parameters_to_context(codec.get(), stream->codecpar), "Configure decoder");
        codec->pkt_timebase = stream->time_base;
        check(avcodec_open2(codec.get(), decoder, nullptr), "Open decoder");
        packet.reset(av_packet_alloc());
        decoded.reset(av_frame_alloc());
        if (!packet || !decoded) {
            throw std::bad_alloc();
        }

        time_base = stream->time_base;
        if (stream->start_time != AV_NOPTS_VALUE) {
            origin = stream->start_time;
        }
        metadata.codec = decoder->name;
        metadata.width = codec->width;
        metadata.height = codec->height;
        if (stream->duration != AV_NOPTS_VALUE && stream->duration >= 0) {
            metadata.duration = std::chrono::microseconds(
                av_rescale_q(stream->duration, time_base, AVRational{1, 1000000}));
        } else if (format->duration != AV_NOPTS_VALUE && format->duration >= 0) {
            metadata.duration = std::chrono::microseconds(format->duration);
        }
    }

    Frame snapshot() {
        Frame output;
        output.sequence = sequence++;
        output.width = decoded->width;
        output.height = decoded->height;
        const int bytes = av_image_get_buffer_size(AV_PIX_FMT_RGB24, output.width, output.height, 1);
        check(bytes, "Calculate RGB frame storage");
        if (output.width <= 0 || output.height <= 0 ||
            output.width > std::numeric_limits<int>::max() / 3) {
            throw std::runtime_error("Unsupported frame dimensions");
        }
        output.stride = output.width * 3;
        output.pixels.resize(static_cast<std::size_t>(bytes));

        // sws_getCachedContext may free its input when replacing it. Release the
        // old owner before handing that pointer back to FFmpeg.
        auto source_format=static_cast<AVPixelFormat>(decoded->format);
        bool full_range=decoded->color_range==AVCOL_RANGE_JPEG;
        // MJPEG webcams commonly use the deprecated YUVJ names. Normalize them
        // so swscale can reuse its context, retaining their full-range semantics.
        switch(source_format) {
        case AV_PIX_FMT_YUVJ420P:source_format=AV_PIX_FMT_YUV420P;full_range=true;break;
        case AV_PIX_FMT_YUVJ422P:source_format=AV_PIX_FMT_YUV422P;full_range=true;break;
        case AV_PIX_FMT_YUVJ444P:source_format=AV_PIX_FMT_YUV444P;full_range=true;break;
        case AV_PIX_FMT_YUVJ440P:source_format=AV_PIX_FMT_YUV440P;full_range=true;break;
        default:break;
        }
        auto* updated = sws_getCachedContext(scale.release(), output.width, output.height,
            source_format, output.width, output.height,
            AV_PIX_FMT_RGB24, SWS_BILINEAR, nullptr, nullptr, nullptr);
        scale.reset(updated);
        if (!scale) {
            throw std::runtime_error("Could not create RGB conversion context");
        }
        const auto* coefficients=sws_getCoefficients(decoded->colorspace==AVCOL_SPC_BT709 ? SWS_CS_ITU709 : SWS_CS_DEFAULT);
        check(sws_setColorspaceDetails(scale.get(),coefficients,full_range ? 1 : 0,coefficients,1,0,1<<16,1<<16),"Configure RGB colour range");
        std::uint8_t* destination[4] = {output.pixels.data(), nullptr, nullptr, nullptr};
        int strides[4] = {output.stride, 0, 0, 0};
        const int rows = sws_scale(scale.get(), decoded->data, decoded->linesize, 0,
            output.height, destination, strides);
        if (rows != output.height) {
            throw std::runtime_error("Incomplete RGB frame conversion");
        }

        const auto pts = decoded->best_effort_timestamp;
        if (pts != AV_NOPTS_VALUE) {
            if (!origin) {
                origin = pts;
            }
            // Preserve presentation timing rather than estimating it from FPS.
            output.timestamp = std::chrono::microseconds(
                av_rescale_q(pts - *origin, time_base, AVRational{1, 1000000}));
        }
        av_frame_unref(decoded.get());
        return output;
    }

    std::optional<Frame> read() {
        check_cancelled();
        const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(5);
        if (ended) {
            return std::nullopt;
        }
        for (;;) {
            check_cancelled();
            const int result = avcodec_receive_frame(codec.get(), decoded.get());
            if (result >= 0) {
                return snapshot();
            }
            if (result == AVERROR_EOF) {
                ended = true;
                return std::nullopt;
            }
            if (result != AVERROR(EAGAIN)) {
                check(result, "Decode frame");
            }
            if (draining) {
                throw std::runtime_error("Decoder requested more packets after end-of-file flush");
            }

            // Feed only the selected visual stream. Audio is ignored for now.
            for (;;) {
                check_cancelled();
                const int input_result = av_read_frame(format.get(), packet.get());
                check_cancelled();
                if(live && input_result==AVERROR(EAGAIN)) {
                    if(std::chrono::steady_clock::now()>=deadline)
                        throw std::runtime_error("Camera has not delivered a frame for 5 seconds; check connection and restart");
                    std::this_thread::sleep_for(std::chrono::milliseconds(5));continue;
                }
                if (input_result == AVERROR_EOF) {
                    check(avcodec_send_packet(codec.get(), nullptr), "Flush delayed frames");
                    draining = true;
                    break;
                }
                check(input_result, "Read media packet");
                if (packet->stream_index == stream_index) {
                    const int send_result = avcodec_send_packet(codec.get(), packet.get());
                    av_packet_unref(packet.get());
                    check(send_result, "Send packet to decoder");
                    break;
                }
                av_packet_unref(packet.get());
            }
        }
    }
};

MediaReader::MediaReader(const std::filesystem::path& path, std::stop_token stop)
    : impl_(std::make_unique<Impl>()) {
    impl_->stop = stop;
    impl_->open(path);
}
MediaReader::MediaReader(const CameraInput& camera,std::stop_token stop):impl_(std::make_unique<Impl>()) {
    if(camera.device.empty() || camera.device.find(':')!=std::string::npos ||
        !((camera.width==0 && camera.height==0 && camera.fps==0) ||
          (camera.width>0 && camera.width<=3840 && camera.height>0 && camera.height<=2160 && camera.fps>0 && camera.fps<=60)))
        throw std::invalid_argument("Select a camera and a valid capture format");
    impl_->stop=stop;impl_->open({},&camera);
}
std::vector<CameraDevice> list_cameras() {
    AVDeviceInfoList* devices{};
    const auto result=avdevice_list_input_sources(camera_format(),nullptr,nullptr,&devices);
    struct Guard {AVDeviceInfoList*& list;~Guard(){avdevice_free_list_devices(&list);}} guard{devices};
    std::vector<CameraDevice> out;
    if(devices)for(int i=0;i<devices->nb_devices;++i) {
        const auto* device=devices->devices[i];
        for(int j=0;j<device->nb_media_types;++j)if(device->media_types[j]==AVMEDIA_TYPE_VIDEO) {
            out.push_back({device->device_name,device->device_description});break;
        }
    }
    if(result<0 && out.empty() && result!=AVERROR(EIO))check(result,"List cameras");
    return out;
}
MediaReader::~MediaReader() = default;
MediaReader::MediaReader(MediaReader&&) noexcept = default;
MediaReader& MediaReader::operator=(MediaReader&&) noexcept = default;

const MediaInfo& MediaReader::info() const {
    if (!impl_) {
        throw std::logic_error("MediaReader was moved from");
    }
    return impl_->metadata;
}

std::optional<Frame> MediaReader::read() {
    if (!impl_) {
        throw std::logic_error("MediaReader was moved from");
    }
    return impl_->read();
}

std::optional<Frame> MediaReader::seek(std::chrono::microseconds target) {
    if (!impl_) throw std::logic_error("MediaReader was moved from");
    if(impl_->live)throw std::logic_error("Live cameras cannot seek");
    if (target.count()<0) throw std::invalid_argument("Review timestamp must be nonnegative");
    impl_->check_cancelled();
    if (!impl_->origin) {
        const auto first=impl_->read();
        if (!first || !first->timestamp) throw std::runtime_error("Source has no seekable presentation timestamps");
    }
    const auto offset=av_rescale_q(target.count(),AVRational{1,1000000},impl_->time_base);
    if (offset>std::numeric_limits<std::int64_t>::max()-std::max<std::int64_t>(0,*impl_->origin))
        throw std::invalid_argument("Review timestamp exceeds the source time range");
    check(av_seek_frame(impl_->format.get(),impl_->stream_index,*impl_->origin+offset,AVSEEK_FLAG_BACKWARD),"Seek recording");
    impl_->check_cancelled();
    avcodec_flush_buffers(impl_->codec.get());
    av_packet_unref(impl_->packet.get());av_frame_unref(impl_->decoded.get());
    impl_->draining=false;impl_->ended=false;impl_->sequence=0;
    while(auto frame=impl_->read()) {
        if(!frame->timestamp) throw std::runtime_error("Source has no seekable presentation timestamps");
        if(*frame->timestamp>=target)return frame;
    }
    return {};
}

} // namespace frametrail
