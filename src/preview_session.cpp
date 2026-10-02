#include "frametrail/preview_session.hpp"
#include <stdexcept>

namespace frametrail {

PreviewSession::~PreviewSession() { stop(); }

void PreviewSession::start(const std::filesystem::path& source) {
    {
        std::lock_guard lock(mutex_);
        if (status_.worker_active) {
            throw std::logic_error("Stop the active preview before opening another source");
        }
    }
    if (worker_.joinable()) worker_.join();
    std::uint64_t generation;
    {
        std::lock_guard lock(mutex_);
        generation = status_.generation + 1;
        frames_.clear();
        status_ = {};
        status_.generation = generation;
        status_.state = PreviewState::opening;
        status_.worker_active = true;
    }
    try {
        worker_ = std::jthread([this, source, generation](std::stop_token stop) {
            PreviewState outcome = PreviewState::completed;
            std::string error;
            try {
                MediaReader reader(source, stop);
                {
                    std::lock_guard lock(mutex_);
                    status_.info = reader.info();
                    status_.state = PreviewState::decoding;
                }
                while (!stop.stop_requested()) {
                    // Wait before decoding as well as before enqueueing: a
                    // paused consumer never causes an unbounded frame backlog.
                    std::unique_lock lock(mutex_);
                    if (!available_.wait(lock, stop, [this] { return frames_.size() < capacity; })) break;
                    lock.unlock();
                    auto frame = reader.read();
                    if (!frame) break;
                    lock.lock();
                    if (stop.stop_requested()) break;
                    frames_.push_back({generation, std::move(*frame)});
                    ++status_.decoded_frames;
                }
                if (stop.stop_requested()) outcome = PreviewState::cancelled;
            } catch (const std::exception& failure) {
                outcome = stop.stop_requested() ? PreviewState::cancelled : PreviewState::failed;
                if (outcome == PreviewState::failed) error = failure.what();
            }
            std::lock_guard lock(mutex_);
            status_.state = outcome;
            status_.error = std::move(error);
            status_.worker_active = false;
            if (outcome == PreviewState::cancelled) frames_.clear();
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
    worker_.request_stop();
    {
        std::lock_guard lock(mutex_);
        frames_.clear();
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
