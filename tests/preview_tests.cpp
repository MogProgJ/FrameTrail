#include "frametrail/preview_session.hpp"
#include <chrono>
#include <iostream>
#include <stdexcept>
#include <thread>
#include <vector>

using namespace std::chrono_literals;

namespace {
void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

template<class Predicate>
void wait_for(Predicate predicate) {
    const auto deadline = std::chrono::steady_clock::now() + 3s;
    while (!predicate()) {
        if (std::chrono::steady_clock::now() > deadline) throw std::runtime_error("Preview timed out");
        std::this_thread::sleep_for(2ms);
    }
}

void run(const std::filesystem::path& root) {
    frametrail::PreviewSession session;
    session.start(root / "variable.mkv");
    const auto first_generation = session.snapshot().generation;
    wait_for([&] { return session.snapshot().queued_frames == session.capacity; });
    std::this_thread::sleep_for(50ms);
    require(session.snapshot().queued_frames == session.capacity, "Paused preview queue grew beyond its bound");
    require(session.snapshot().decoded_frames == session.capacity, "Worker decoded beyond bounded handoff");
    session.stop();
    wait_for([&] { return !session.snapshot().worker_active; });
    require(session.snapshot().state == frametrail::PreviewState::cancelled, "Blocked producer did not cancel");
    require(!session.try_pop(), "Stopped source left stale frames");

    session.start(root / "delayed.mkv");
    const auto second_generation = session.snapshot().generation;
    require(second_generation > first_generation, "Restart did not change generation identity");
    std::vector<frametrail::PreviewFrame> frames;
    wait_for([&] {
        while (auto frame = session.try_pop()) frames.push_back(std::move(*frame));
        auto status = session.snapshot();
        return !status.worker_active && status.queued_frames == 0;
    });
    require(session.snapshot().state == frametrail::PreviewState::completed, "Offline preview failed");
    require(frames.size() == 10, "Offline preview dropped frames");
    for (std::size_t i = 0; i < frames.size(); ++i) {
        require(frames[i].generation == second_generation && frames[i].frame.sequence == i,
            "Frame ordering or source identity is incorrect");
    }
    session.start(root / "invalid.txt");
    wait_for([&] { return !session.snapshot().worker_active; });
    require(session.snapshot().state == frametrail::PreviewState::failed && !session.snapshot().error.empty(),
        "Invalid source did not report an error");

    for (int i = 0; i < 10; ++i) {
        session.start(root / "still.png");
        wait_for([&] { return !session.snapshot().worker_active; });
        require(session.try_pop().has_value(), "Restart after failure or EOF failed");
    }
    // Destructor must also wake and join a producer waiting on a full queue.
    {
        frametrail::PreviewSession closing;
        closing.start(root / "delayed.mkv");
        wait_for([&] { return closing.snapshot().queued_frames == closing.capacity; });
    }
}
} // namespace

int main(int argc, char* argv[]) {
    try {
        require(argc == 2, "Expected fixture directory");
        run(std::filesystem::path(argv[1]));
        std::cout << "Preview lifecycle passed: bounds, cancellation, generations, EOF, restart, shutdown\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
