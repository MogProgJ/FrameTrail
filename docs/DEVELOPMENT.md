# Build and understand FrameTrail

## What runs today

FrameTrail 0.5 has a desktop preview, saved-analysis review window, and command-line inspector backed by a reusable C++ library. They open local images/recordings and produce owned RGB24 pixels with source timestamps. Whole-file analysis stores configuration, events, thumbnails, and progress in SQLite; review plays the source without inference.

The preview has Open media, Play/Pause, Stop, Replay, and Saved analysis. CPU detection adds boxes, labels, confidence filtering, and CSV; see [detection](DETECTION.md). Tracking adds IDs, trails, line rules, and counters; see [tracking](TRACKING.md). Saved analysis adds immutable run files, event thumbnails/markers, review seeking, and CSV; see [saved runs](SAVED_RUNS.md). Audio playback, live input, and agents remain planned. CLI throughput includes enabled stages; it is not a live-performance promise.

## Windows setup

Requirements: Windows x64, Visual Studio 2022 with Desktop development with C++ and its Windows SDK, CMake 3.25 or newer, and PowerShell. The scripts discover Visual Studio's bundled CMake without changing PATH.

From the FrameTrail repository directory:

```powershell
.\scripts\fetch-dependencies.ps1
.\scripts\build.ps1
.\build\windows-msvc\Release\frametrail-desktop.exe
```

Fetching downloads approximately 81 MB of FFmpeg and 40 MB of Qt base into `.deps/`, verifies SHA-256 hashes, and extracts the SDKs. CMake handles Qt's 7z archive. It also fetches ONNX Runtime (about 83 MB), YOLOX-Nano (about 3.6 MB), and SQLite source (about 3 MB). Nothing is installed system-wide. Building configures x64, compiles Release, copies runtime DLLs/plugins, and runs CTest. With the model and optional detection sample, twenty checks are available. Existing checkouts can fetch only the new source with `.\scripts\fetch-storage.ps1`.

For Debug:

```powershell
.\scripts\build.ps1 -Configuration Debug
```

To build only the core and CLI without acquiring Qt (CPU detection remains included):

```powershell
.\scripts\fetch-dependencies.ps1 -MediaOnly
.\scripts\build.ps1 -MediaOnly
```

## Opening a fresh copy in VS Code

Each clone needs its own SDKs: `.deps/` is ignored by Git. Selecting a compiler/preset does not download dependencies. Run `./scripts/fetch-dependencies.ps1` before the first configure.

Choose **Windows x64 (Visual Studio 2022)** (`windows-msvc`). Visual Studio supplies the compiler; VS Code is the editor. Run **CMake: Configure**, choose the `release` or `debug` build preset, and run **CMake: Build**. Select `frametrail-desktop` as the launch target. The [CMake Tools preset guide](https://github.com/microsoft/vscode-cmake-tools/blob/main/docs/cmake-presets.md) explains these commands.

If paused inside `CMakeLists.txt` on a `find_path` error, stop the CMake debugging session, fetch dependencies, and configure normally. Missing `libavcodec/avcodec.h` means the FFmpeg development SDK is absent or `FFMPEG_ROOT` is wrong. Installing only `ffmpeg.exe` does not provide development headers/libraries. Missing `Qt6Config.cmake` requires the Qt SDK too.

The build script performs configure/build/checks together. Stop any active CMake session before running it against the same build directory.

If CMake is on PATH, manual equivalents are:

```powershell
cmake --preset windows-msvc
cmake --build --preset release
ctest --preset release
```

Custom compatible SDKs can be specified through `-DFFMPEG_ROOT=<ffmpeg-directory>` and `-DFRAMETRAIL_QT_ROOT=<qt-directory>`. CLI-only configuration uses `-DFRAMETRAIL_BUILD_GUI=OFF`. The convenience build script intentionally uses the manifests' SDK paths and refreshes both root paths on each configure.

## Using the desktop

Use **Open media** to select a local file. Videos start automatically. **Pause** and **Stop** hold the current position; **Play** resumes from there with the same analysis state. **Replay** starts the same source from the beginning. Settings changes re-analyse the held frame and buffered backlog at the same sequence/timestamp, then restore whether playback was playing or paused. Counts and IDs start a new analysis segment at that point. Line drawing holds the frame until you confirm A/B or right-click to cancel. Opening another file cancels the old worker before starting the new source. Closing requests cancellation and waits for the worker without blocking the UI event thread.

The window shows dimensions, codec, zero-based frame number, and source-relative timestamp. A synthetic example is available after tests generate the fixtures:

```powershell
.\build\windows-msvc\Release\frametrail-desktop.exe .\build\windows-msvc\fixtures\variable.mkv
```

This test pattern is deliberately tiny (64x48, ten frames), so enlarging it looks pixelated. Try a real recording for a useful preview. Playback uses decoded presentation timestamps and preserves order. If decoding falls behind, playback slows instead of dropping frames. Unknown timestamps use an approximately 30 FPS display fallback but remain unknown in the frame contract and CSV. Still images remain displayed after the source finishes.

## Using the inspector

```powershell
.\build\windows-msvc\Release\frametrail.exe --help
.\build\windows-msvc\Release\frametrail.exe inspect .\build\windows-msvc\fixtures\variable.mkv
New-Item -ItemType Directory -Path output -Force
.\build\windows-msvc\Release\frametrail.exe inspect "C:\Videos\entrance.mp4" --csv output\frames.csv --preview output\first-frame.ppm --max-frames 100
```

Replace the example input with your recording. Output directories must exist; existing output files are refused. Choose fresh names for subsequent exports. A failed decode/write may leave partial output, and a nonzero exit status indicates failure.

Without `--max-frames`, inspection reads to EOF. `timestamp_us` is source-relative presentation time in microseconds (one million per second); unknown timing stays blank. Initial metadata dimensions may differ from individual frames. The desktop can open the exported PPM image.

## Source map

| Location | Responsibility |
| --- | --- |
| `include/frametrail/frame.hpp` | Sequence, optional timestamp, dimensions, stride, owned pixels |
| `include/frametrail/media_reader.hpp`, `src/media_reader.cpp` | Local file validation, FFmpeg ownership, decoding/flushing, timing, RGB conversion |
| `src/frame_export.cpp` | PPM writing with row padding |
| `include/frametrail/preview_session.hpp`, `src/preview_session.cpp` | Worker lifecycle, cancellation, bounded queue, status, source generations |
| `apps/desktop/preview_window.cpp` | Controls, playback clock, generation checks, image ownership, painting |
| `apps/desktop/main.cpp` | Qt entry point and optional initial file argument |
| `apps/cli/main.cpp` | Arguments, export validation, frame loop, CSV, summary |
| `include/frametrail/detector.hpp`, `src/detector.cpp` | Model session, preprocessing, grid decoding, NMS, labels, and CPU timings |
| `include/frametrail/tracker.hpp`, `src/tracker.cpp` | Motion/overlap association, confirmation/expiry, bounded trails, finite-line crossing state and counters |
| `include/frametrail/run_store.hpp`, `src/run_store.cpp` | SQLite C API ownership, frozen run schema, transactional events/progress, read-only pages/CSV |
| `include/frametrail/analysis_job.hpp`, `src/analysis_job.cpp` | Whole-file decode/detect/track/persist worker, progress and partial cancellation/failure |
| `apps/desktop/saved_run_window.cpp` | Saved run workflow, thumbnails/pages/markers, asynchronous decode-only event review |
| `tests/` | Synthetic fixtures, media/CLI/worker/desktop behaviour checks |
| `scripts/` | Explicit dependency acquisition and build/check commands |
| `dependencies/` | Pinned FFmpeg, Qt, ONNX Runtime, model, and SQLite source artifacts |

FFmpeg is a C library called directly from our C++ code. RAII wrappers release native contexts, packets, frames, and conversion resources even when an operation fails. Returned frames own their pixels and remain valid when the reader advances. At EOF the reader flushes delayed decoder output, which matters for codecs that reorder frames internally.

## Worker, timing, and ownership

```mermaid
flowchart LR
    UI[Qt controls on UI thread] --> SESSION[PreviewSession start / stop]
    SESSION --> WORKER[One C++ jthread]
    WORKER --> READER[MediaReader / FFmpeg]
    READER --> QUEUE[Owned frames: capacity 2]
    QUEUE --> TIMER[UI timer and playback clock]
    TIMER --> IMAGE[Copy pixels into owned QImage]
    IMAGE --> CANVAS[Paint aspect-preserving preview]
    UI --> CANCEL[Source replacement or close wakes blocked queue]
    CANCEL --> WORKER
```

With detection enabled, the same worker runs inference after decoding. With tracking enabled, it then updates the source's tracker and crossing rules, and enqueues the frame with detections/tracks/events/counters. The worker never touches Qt widgets. A mutex protects status and the queue. A stop-aware condition variable waits when the queue is full; the UI polls without waiting for frames. Pause and the player Stop leave a bounded backlog instead of decoding the entire recording into memory. Counts shown by the UI belong to the displayed frame.

Each source start increments a generation ID. Each settings change increments an analysis revision. The UI returns its displayed/pending raw frames; the controller merges them with queued raw pixels in source order, de-duplicates sequences, and rejects obsolete results. The worker applies the latest settings before processing that backlog, resets tracking, and retains the decoder's current position. Rapid changes coalesce into the latest revision. The detector is reused when its settings are unchanged. At EOF a later revision can refresh the held frame using a successor worker and the retained reader, without re-opening the source.

Source replacement waits for the previous worker to become inactive and joins it before starting another. `PreviewSession::stop()` is internal cancellation for replacement/close, not the player's Stop button. It requests the source and worker stop tokens, clears queued frames, and wakes the producer. `std::jthread` is the last session member so destruction joins before reader/synchronization objects disappear. The reader retains the source handle at EOF until replacement/close. Decoding can finish before playback: the UI reaches Finished only after the accepted frames are displayed.

The result queue holds at most two frames. Normal playback also holds one pending presentation frame, one displayed raw RGB frame for refreshes, and its QImage. During reconfiguration the ordered raw backlog is capped at five frames (displayed, pending presentation, two queued, and one in-flight); results and in-flight work move through that backlog rather than accumulate a recording. A retained displayed copy, inference/model buffers, decoder/conversion buffers, and temporary copies add memory. This bounds frame count, not bytes: larger resolutions use more memory. The deliberate QImage copy prevents dangling pixels. Profiling may justify reducing copies later.

Source presentation timestamps govern playback; a steady clock measures elapsed playback time. Pause shifts the playback clock's anchor. The reader is sequential and must not be read concurrently. Its stop token interrupts FFmpeg I/O; the CLI currently relies on OS process interruption rather than a graceful interactive cancel command.

## Checks and limitations

The original six checks cover fixture generation, media contracts, CLI help, CLI exports, preview lifecycle, and desktop controls. Detection and tracking add the contracts/integration described in their guides. Media checks verify colour/layout, retained ownership, delayed EOF, variable timing, cancellation, invalid/audio-only inputs, Unicode paths, and padded export. Worker checks cover bounds, blocked-producer cancellation, generation/revision identity, repeated reconfiguration, exact sequence/timestamp/pixels, no re-decoding, EOF/still refreshes, failure recovery, and shutdown. Desktop checks exercise Stop/Play continuity, paused/playing settings, line apply/cancel, confidence/classes/direction/detection/tracking toggles, rapid changes, replay, source replacement, errors, and closing during work.

Desktop checks use Qt's offscreen platform and load the installed Windows Segoe UI font for readable screenshots. The rendered window was inspected, but native file-dialog interaction and representative long recordings still need manual checks. No leak detector or sustained live-input test has been run. Windows x64 is the verified platform.

Event review seeking is implemented, with sequence fallback when timestamps/indexes are unsuitable. Audio, general player scrubbing, rotation metadata, and non-square sample aspect-ratio correction remain unimplemented. The canvas preserves pixel-dimension aspect ratio. Supported codecs depend on FFmpeg; every format has not been verified. Memory growth and representative performance still need measurement.

## Dependency provenance

FFmpeg is an LGPL-shared 8.1 branch build from [BtbN/FFmpeg-Builds](https://github.com/BtbN/FFmpeg-Builds). The pinned September 2026 monthly build has longer retention than daily archives, but availability is finite. Qt 6.11.3 base comes from the [official SDK repository](https://download.qt.io/online/qtsdkrepository/windows_x86/desktop/qt6_6113/). Neither script silently falls back to an unpinned latest archive.

Licenses/notices remain inside `.deps`. Local development builds do not complete the distribution milestone; packaging needs the selected binaries' notices and licensing review. See [equipment and setup](EQUIPMENT_AND_SETUP.md).

## Next slice

Evaluate detection, track identities, crossing events, and the saved recorded-file workflow on short labelled people/vehicle clips, using [TRACKING.md](TRACKING.md) and [SAVED_RUNS.md](SAVED_RUNS.md). First live input follows after that workflow is reliable. Optional AI perception and an agent-driven service remain deferred.
