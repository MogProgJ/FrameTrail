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
void reconfiguration(const std::filesystem::path& root) {
    frametrail::PreviewSession session;
    session.start(root/"variable.mkv");
    const auto generation=session.snapshot().generation;
    wait_for([&]{return session.snapshot().queued_frames==session.capacity;});
    auto displayed=session.try_pop(); auto pending=session.try_pop();
    require(displayed && pending,"Missing retained playback frames");
    std::uint64_t revision{};
    for(int i=0;i<30;++i) {
        revision=session.reconfigure({},{},{displayed->frame,pending->frame});
        require(session.snapshot().generation==generation,"Settings changed source generation");
        if(i%3==0) std::this_thread::sleep_for(2ms);
    }
    std::vector<frametrail::PreviewFrame> frames;
    wait_for([&]{
        while(auto frame=session.try_pop()) frames.push_back(std::move(*frame));
        const auto status=session.snapshot();
        return !status.worker_active && status.queued_frames==0;
    });
    require(session.snapshot().state==frametrail::PreviewState::completed && frames.size()==10,
        "Reconfiguration lost or duplicated buffered frames");
    require(session.snapshot().decoded_frames==10,"Settings re-decoded the source");
    frametrail::MediaReader baseline(root/"variable.mkv");
    for(std::size_t i=0;i<frames.size();++i) {
        const auto reference=baseline.read();
        require(reference && frames[i].frame.sequence==i && frames[i].frame.timestamp==reference->timestamp &&
            frames[i].frame.pixels==reference->pixels && frames[i].analysis_revision==revision,
            "New settings lost original frame identity/pixels or exposed obsolete analysis");
    }
    auto last=frames.back().frame;
    revision=session.reconfigure({},{},{last});
    wait_for([&]{return !session.snapshot().worker_active;});
    auto refreshed=session.try_pop();
    require(refreshed && refreshed->frame.sequence==9 && refreshed->frame.timestamp==last.timestamp &&
        refreshed->analysis_revision==revision && !session.try_pop(),"EOF refresh changed playback position");
    require(session.snapshot().decoded_frames==10,"EOF refresh reopened or re-decoded the source");
    session.stop();
    wait_for([&]{return !session.snapshot().worker_active;});
    session.start(root/"still.png");
    wait_for([&]{return !session.snapshot().worker_active;});
    const auto image=session.try_pop();
    require(image.has_value(),"Still image missing");
    session.reconfigure({},{},{image->frame});
    wait_for([&]{return !session.snapshot().worker_active;});
    const auto refreshed_image=session.try_pop();
    require(refreshed_image && refreshed_image->frame.pixels==image->frame.pixels,"Still-image refresh lost pixels");
}
} // namespace

int main(int argc, char* argv[]) {
    try {
        require(argc == 2 || argc == 3 || argc == 4, "Expected fixture directory and optional model/sample or reconfiguration mode");
        if(argc==3) {
            require(std::string_view(argv[2])=="--reconfigure","Unknown test mode");
            reconfiguration(std::filesystem::path(argv[1]));
            std::cout<<"Reconfiguration passed: coalescing, bounded buffers, frame identity, no re-decoding, EOF, still images\n";
            return 0;
        }
        if (argc == 4) {
            frametrail::PreviewSession session;
            frametrail::DetectorOptions detector{std::filesystem::path(argv[2])};
            frametrail::TrackingOptions tracker;
            tracker.classes={16};
            session.start(std::filesystem::path(argv[3]),detector,tracker);
            wait_for([&]{return !session.snapshot().worker_active;});
            const auto image=session.try_pop();
            require(image && image->detection && !image->detection->objects.empty() && !image->tracking,
                "Still-image detection lost or acquired temporal state");
            session.start(std::filesystem::path(argv[1])/"variable.mkv",detector,tracker);
            std::vector<frametrail::PreviewFrame> frames;
            wait_for([&]{
                while(auto frame=session.try_pop()) frames.push_back(std::move(*frame));
                const auto status=session.snapshot();
                return !status.worker_active && status.queued_frames==0;
            });
            require(session.snapshot().state==frametrail::PreviewState::completed && frames.size()==10,"Tracking pipeline failed or dropped frames");
            require(!frames[0].tracking,"Temporal output was exposed before frame two");
            for(std::size_t i=1;i<frames.size();++i) require(frames[i].tracking && frames[i].frame.sequence==i &&
                frames[i].generation==session.snapshot().generation,"Tracking detached from frame/source identity");
            session.start(std::filesystem::path(argv[1])/"variable.mkv",detector,tracker);
            wait_for([&]{return session.snapshot().queued_frames==session.capacity;});
            session.stop();
            wait_for([&]{return !session.snapshot().worker_active;});
            require(!session.try_pop(),"Stopped tracking left stale state");
            require(session.snapshot().state==frametrail::PreviewState::cancelled,"Blocked tracking producer did not cancel");
            std::cout<<"Preview tracking passed: still-image boundary, ordered frame pairing, generation and cancellation\n";
            return 0;
        }
        run(std::filesystem::path(argv[1]));
        std::cout << "Preview lifecycle passed: bounds, cancellation, generations, EOF, restart, shutdown\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
