# Current status

Updated: 2 October 2026.

## What exists

- Documentation for the product and its initial workflow.
- A text interface sketch and Mermaid architecture diagram.
- Proposed module responsibilities and data contracts.
- Equipment/dependency planning, milestones, and a glossary.
- Git ignore and text-formatting configuration.
- A C++20 media library using FFmpeg's native C APIs.
- A command-line inspector for local images and recordings, with optional frame CSV and first-frame PPM exports.
- A Qt desktop preview with Open media, Play/Pause, Stop, Replay, source details, and file errors.
- Stop/Play resumes at the held position. Settings and line edits preserve sequence/timestamp, re-analyse a bounded backlog, and restore the previous playing/paused state.
- A cancellable decoding worker, a two-frame queue with backpressure, and generation IDs for source changes.
- YOLOX-Nano CPU inference through ONNX Runtime, frame-aligned boxes/labels, a confidence control, and CLI detection CSV exports.
- A native motion-association tracker with confirmation/expiry, selected people/vehicle classes, observed IDs and bounded trails.
- Finite counting-line rules with direction filtering, deadband, re-arming, gap handling, desktop line drawing/counters, and streaming CLI track/event CSV.
- Frozen whole-file analysis jobs, SQLite saved runs, embedded event thumbnails, paged event lists/timeline markers, source review seeking/playback, reopening without inference, and saved CSV exports.
- Committed progress/events, idempotent event IDs, partial cancellation/failure status, and missing/changed-source checks.
- Windows webcam selection/capture, independent live capture and CPU analysis, capacity-one queues, skip/latency metrics, and stop/restart.
- Improved saved-review timing with a precise timer, overdue-frame catch-up, and a 60 FPS regression check.
- CMake presets, PowerShell dependency/build scripts, and CTest checks using generated synthetic media.
- A development guide explaining commands, ownership, timing, and current limitations.

Version 0.6 builds and runs on Windows x64. Recorded-file analysis and saved event review are joined by one live webcam. Live capture continues independently of CPU analysis and replaces pending frames when inference falls behind. Audio playback, live recording, and network cameras remain deferred. Representative accuracy and sustained resource measurements remain open. See [live camera](LIVE_CAMERA.md), [tracking](TRACKING.md), and [saved runs](SAVED_RUNS.md).

## Development baseline and validation

Inspected hardware: Intel Core i7-10750H, approximately 15.8 GiB reported RAM, Intel UHD Graphics, and NVIDIA GeForce GTX 1650 Ti. CPU execution remains the initial analysis target.

Tools used: Visual Studio 2022 MSVC 19.44, bundled CMake 3.31.6, checksum-pinned FFmpeg 8.1 branch, Qt 6.11.3 base, ONNX Runtime 1.30.0 CPU, YOLOX-Nano 0.1.1rc0, and SQLite 3.53.4 C amalgamation. Manifests are under `dependencies/`. No system-wide dependency installation was performed.

The suite now contains 21 checks, including live overload/lifecycle and 60 FPS review timing alongside the existing media, inference, tracking, storage, and desktop checks. The integrated webcam also passed two short capture/detect/track/stop cycles at 1280×720 with clean device release; see [live camera evidence](LIVE_CAMERA.md). Stored review continues to leave the database unchanged. These are integration checks, not natural-video counting-accuracy measurements. Representative labelled footage, unplug/reconnect behaviour, native dialogs, and sustained memory/disk/latency measurements remain open. No leak detector has been run.

## Repository publication

Working repository name: **FrameTrail**. GitHub owner: **MogProgJ**.

Repository: [MogProgJ/FrameTrail](https://github.com/MogProgJ/FrameTrail). Created as a private repository on 2 October 2026.

The user-facing checkout is `C:\Users\nazee\Documents\All Modules\FrameTrail`. An independent editing checkout under the MiniERP workspace is synchronized through this repository.

## Decisions already made

- Recorded files and images before live input.
- Stationary-camera person/vehicle crossing events as the first video use case.
- One source and one model for the initial release.
- CPU baseline before deciding on acceleration.
- C++ application with native C API integration; custom C modules only for a justified need.
- Robotics remains a separate shelved idea.
- Establish and validate the native application before experimenting with an embedded AI perception pipeline.
- Keep an agent-driven investigation service as a final, longer-term direction, after the application and any optional perception extension have been evaluated.
- Pretrained detection remains part of the native baseline; agent orchestration, a Python AI worker, and hosted AI services are deferred.
- Optional GPU inference, Python training, bwUniCluster use, a Python inference worker, and commercial cloud serving are governed by separate measurement gates; adopting one does not require the others.
- Initial tracking uses a deterministic greedy motion/overlap baseline with a bottom-center anchor. IDs are run-scoped; labelled evidence will determine whether to replace the association strategy.

## Decisions still open

- Confirm or rename FrameTrail.
- Initial repository visibility is private because no publication preference was specified; it can be changed later.
- Any future image-processing dependency; SQLite is now the selected local storage dependency.
- Representative labelled sample footage and model upgrades if the baseline misses required objects.
- Hardware-dependent targets and initial supported file formats.
- Measured tracker improvements and calibrated rule parameters after labelled evaluation.
- Project license and distribution model.
- Confirm the user's current bwUniCluster account lifetime, GPU partition access, project/account association, and permitted footage before preparing jobs.

## Immediate next work

Evaluate short labelled recorded/live people or vehicle crossings and run a sustained webcam test, including unplug/reconnect. The next implementation phase is profiling, optimization, and packaging, guided by measured failures rather than adding more features. Preview Fit/100% zoom and broader quality refinements remain deferred; the reported saved-review timing issue received a focused fix in 0.6.

The [compute and training plan](COMPUTE_AND_TRAINING.md) is integrated as conditional Phase 8. No cluster environment or cloud service will be added until evaluation identifies a concrete accuracy, throughput, or scale constraint.

Application implementation has begun following the user's instruction on 2 October 2026. Optional agent orchestration and hosted AI services remain deferred.
