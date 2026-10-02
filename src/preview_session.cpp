#include "frametrail/preview_session.hpp"
#include <algorithm>
#include <stdexcept>

namespace frametrail {
namespace {
bool same_detector(const std::optional<DetectorOptions>& a, const std::optional<DetectorOptions>& b) {
    if (bool(a) != bool(b)) return false;
    return !a || (a->model == b->model && a->confidence == b->confidence && a->nms_iou == b->nms_iou);
}
}
PreviewSession::~PreviewSession() { stop(); }

void PreviewSession::start(const std::filesystem::path& source, std::optional<DetectorOptions> detection,
    std::optional<TrackingOptions> tracking, std::optional<ReviewPosition> review) {
    if (tracking && !detection) throw std::invalid_argument("Tracking requires detection");
    if (review && (detection || tracking)) throw std::invalid_argument("Event review cannot run inference or tracking");
    {
        std::lock_guard lock(mutex_);
        if (status_.worker_active) throw std::logic_error("Stop the active preview before opening another source");
    }
    if (worker_.joinable()) worker_.join();
    reader_.reset();
    eof_ = false;
    source_stop_ = std::stop_source{};
    {
        std::lock_guard lock(mutex_);
        const auto generation = status_.generation + 1;
        frames_.clear(); pending_frames_.clear();
        source_ = source; detection_ = std::move(detection); tracking_ = std::move(tracking);
        review_ = review;
        status_ = {};
        status_.generation = generation;
        status_.analysis_revision = 1;
        status_.state = PreviewState::opening;
        status_.worker_active = true;
    }
    launch_worker();
}

void PreviewSession::retain_frame(Frame frame) {
    const auto position = std::ranges::lower_bound(pending_frames_,frame.sequence,{},&Frame::sequence);
    if (position == pending_frames_.end() || position->sequence != frame.sequence)
        pending_frames_.insert(position,std::move(frame));
    if (pending_frames_.size() > capacity + 3)
        throw std::logic_error("Reconfiguration exceeded the bounded preview backlog");
}

std::uint64_t PreviewSession::reconfigure(std::optional<DetectorOptions> detection,
    std::optional<TrackingOptions> tracking, std::vector<Frame> retained) {
    if (tracking && !detection) throw std::invalid_argument("Tracking requires detection");
    if (review_) throw std::logic_error("Event review settings are frozen");
    if (retained.size() > 2) throw std::invalid_argument("Retain only the displayed and pending presentation frames");
    bool launch;
    std::uint64_t revision;
    {
        std::lock_guard lock(mutex_);
        if (source_.empty() || source_stop_.stop_requested()) throw std::logic_error("No source available for reconfiguration");
        for (auto& frame : retained) retain_frame(std::move(frame));
        for (auto& frame : frames_) retain_frame(std::move(frame.frame));
        frames_.clear();
        detection_ = std::move(detection); tracking_ = std::move(tracking);
        revision = ++status_.analysis_revision;
        status_.state = PreviewState::opening;
        status_.error.clear();
        launch = !status_.worker_active;
        if (launch) status_.worker_active = true;
    }
    available_.notify_all();
    if (launch) {
        if (worker_.joinable()) worker_.join();
        launch_worker();
    }
    return revision;
}

void PreviewSession::launch_worker() {
    try {
        worker_ = std::jthread([this](std::stop_token stop) {
            PreviewState outcome = PreviewState::completed;
            std::string error;
            std::optional<Frame> in_flight;
            try {
                if (!reader_) {
                    reader_ = std::make_unique<MediaReader>(source_,source_stop_.get_token());
                    if(review_) {
                        std::optional<Frame> first;
                        if(review_->timestamp) {
                            try {first=reader_->seek(*review_->timestamp);}catch(const std::exception&) {
                                if(stop.stop_requested())throw;
                            }
                        }
                        if(!first || first->timestamp!=review_->timestamp) {
                            // Some formats have no usable seek index or timestamps.
                            // Decode from the start to the stored source sequence.
                            reader_=std::make_unique<MediaReader>(source_,source_stop_.get_token());
                            do {first=reader_->read();}while(first && first->sequence<review_->source_sequence);
                            if(!first)throw std::runtime_error("Saved event frame is no longer present in the source");
                        }
                        std::lock_guard lock(mutex_);
                        if(!stop.stop_requested())pending_frames_.push_back(std::move(*first));
                    }
                }
                std::unique_ptr<Detector> detector;
                std::unique_ptr<Tracker> tracker;
                std::optional<DetectorOptions> applied_detection;
                std::uint64_t applied_revision{};
                {
                    std::lock_guard lock(mutex_);
                    status_.info = reader_->info();
                }
                for (;;) {
                    std::unique_lock lock(mutex_);
                    if (stop.stop_requested()) break;
                    if (status_.analysis_revision != applied_revision) {
                        const auto revision = status_.analysis_revision;
                        const auto detection = detection_;
                        const auto tracking = tracking_;
                        lock.unlock();
                        try {
                            if (!same_detector(detection,applied_detection)) {
                                if (detection) detector = std::make_unique<Detector>(*detection);
                                else detector.reset();
                                applied_detection = detection;
                            }
                            tracker = tracking ? std::make_unique<Tracker>(*tracking) : nullptr;
                        } catch (...) {
                            lock.lock();
                            if (revision != status_.analysis_revision && !stop.stop_requested()) continue;
                            throw;
                        }
                        applied_revision = revision;
                        lock.lock();
                        if (revision == status_.analysis_revision) status_.state = PreviewState::decoding;
                        continue;
                    }
                    if (eof_ && pending_frames_.empty()) {
                        // Atomic with reconfigure: a revision either reaches this
                        // worker or launches its successor using the same reader.
                        status_.state = PreviewState::completed;
                        status_.worker_active = false;
                        return;
                    }
                    if (!available_.wait(lock,stop,[&] {
                        return status_.analysis_revision != applied_revision || frames_.size() < capacity;
                    })) break;
                    if (status_.analysis_revision != applied_revision) continue;
                    if (!pending_frames_.empty()) {
                        in_flight = std::move(pending_frames_.front());
                        pending_frames_.pop_front();
                        lock.unlock();
                    } else {
                        lock.unlock();
                        in_flight = reader_->read();
                        lock.lock();
                        if (!in_flight) { eof_ = true; continue; }
                        ++status_.decoded_frames;
                        if (stop.stop_requested()) break;
                        if (status_.analysis_revision != applied_revision) {
                            retain_frame(std::move(*in_flight)); in_flight.reset(); continue;
                        }
                        lock.unlock();
                    }
                    std::optional<DetectionResult> result;
                    if (detector) result = detector->detect(*in_flight,stop);
                    std::optional<TrackingResult> tracks;
                    if (tracker && !stop.stop_requested()) {
                        auto temporal = tracker->update(result->objects,in_flight->sequence,in_flight->timestamp,
                            in_flight->width,in_flight->height);
                        if (in_flight->sequence > 0) tracks = std::move(temporal);
                    }
                    lock.lock();
                    if (stop.stop_requested()) break;
                    if (status_.analysis_revision != applied_revision) {
                        retain_frame(std::move(*in_flight));
                    } else {
                        frames_.push_back({status_.generation,std::move(*in_flight),std::move(result),
                            std::move(tracks),applied_revision});
                    }
                    in_flight.reset();
                }
                if (stop.stop_requested()) outcome = PreviewState::cancelled;
            } catch (const std::exception& failure) {
                outcome = stop.stop_requested() ? PreviewState::cancelled : PreviewState::failed;
                if (outcome == PreviewState::failed) error = failure.what();
            }
            std::lock_guard lock(mutex_);
            if (outcome == PreviewState::failed && in_flight) retain_frame(std::move(*in_flight));
            status_.state = outcome;
            status_.error = std::move(error);
            status_.worker_active = false;
            if (outcome == PreviewState::cancelled) { frames_.clear(); pending_frames_.clear(); }
        });
    } catch (...) {
        std::lock_guard lock(mutex_);
        status_.worker_active = false;
        status_.state = PreviewState::failed;
        status_.error = "Could not start the preview worker";
        throw;
    }
}

void PreviewSession::stop() {
    source_stop_.request_stop();
    worker_.request_stop();
    {
        std::lock_guard lock(mutex_);
        frames_.clear(); pending_frames_.clear();
        if (!status_.worker_active) status_.state = PreviewState::cancelled;
    }
    available_.notify_all();
}

PreviewSnapshot PreviewSession::snapshot() const {
    std::lock_guard lock(mutex_);
    auto result = status_;
    result.queued_frames = frames_.size();
    return result;
}

std::optional<PreviewFrame> PreviewSession::try_pop() {
    std::lock_guard lock(mutex_);
    if (frames_.empty()) return std::nullopt;
    auto frame = std::move(frames_.front());
    frames_.pop_front();
    available_.notify_all();
    return frame;
}
} // namespace frametrail
