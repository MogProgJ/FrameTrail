# Current status

Updated: 3 October 2026.

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
- Optional isolated DirectML inference on DirectX 12 hardware, CPU fallback and actual-provider/runtime/device metadata; player/live device selectors.
- Selectable YOLOX-Nano / YOLOX-S CPU inference through ONNX Runtime, frame-aligned boxes/labels, a confidence control, and CLI detection CSV exports.
- A native motion-association tracker with confirmation/expiry, selected people/vehicle classes, observed IDs and bounded trails.
- Finite counting-line rules with direction filtering, deadband, re-arming, gap handling, desktop line drawing/counters, and streaming CLI track/event CSV.
- Independent video-analysis intake with local drag/drop, all-category object appearances, first/last timestamps, thumbnails, bounded review pages and progress previews.
- Temporary analysis followed by optional atomic saving and formatted UTF-8 CSV export; unsaved-result prompts, protected destinations, cancellation/close-time partial results and read-only legacy crossing review.
- Committed progress/events, idempotent event IDs, partial cancellation/failure status, and missing/changed-source checks.
- Windows webcam selection/capture, independent live capture and CPU analysis, capacity-one queues, skip/latency metrics, and stop/restart.
- Improved saved-review timing with a precise timer, overdue-frame catch-up, and a 60 FPS regression check.
- CMake presets, PowerShell dependency/build scripts, and CTest checks using generated synthetic media.
- A development guide explaining commands, ownership, timing, and current limitations.

Version 0.10 builds and runs on Windows x64. Recorded-file appearance analysis and saved review are joined by one live webcam. Live capture continues independently of CPU analysis and replaces pending frames when inference falls behind. Audio playback, live recording, and network cameras remain deferred. Representative accuracy and sustained resource measurements remain open. See [live camera](LIVE_CAMERA.md), [tracking](TRACKING.md), and [saved runs](SAVED_RUNS.md).

## Model upgrade and evaluation (0.8)

YOLOX-S is now selectable in the file and live workspaces, with native 640 × 640 inference, explicit CLI profile/thresholds, checksum-pinned acquisition, optional packaging and saved-run model identity. Schema-1 runs remain readable without migration. A local partial-label comparison recovered 18/24 selected targets with Nano and 24/24 with S; full-clip CPU throughput was about 27.5 versus 5.0 FPS. See [evaluation](MODEL_EVALUATION.md) for methodology and limits. Full real-world precision/event evaluation is still open; The optional GPU path was evaluated in 0.10; training/cluster/Python/cloud remain deferred.

## Development baseline and validation

Inspected hardware: Intel Core i7-10750H, approximately 15.8 GiB reported RAM, Intel UHD Graphics, and NVIDIA GeForce GTX 1650 Ti. CPU execution remains the initial analysis target.

Tools used: Visual Studio 2022 MSVC 19.44, bundled CMake 3.31.6, checksum-pinned FFmpeg 8.1 branch, Qt 6.11.3 base, ONNX Runtime 1.30.0 CPU, YOLOX-Nano 0.1.1rc0, and SQLite 3.53.4 C amalgamation. Manifests are under `dependencies/`. No system-wide dependency installation was performed.

The standard 0.10 suite has 27 checks; all 31 native/desktop checks pass with four opt-in GPU hardware tests, alongside the six Python scorer checks. A separate CPU-only build passes its dependency/fallback check. The 0.9 suite passed 26 native/desktop CTest checks, including the rebuilt appearance intake, persistence, CSV and partial-result paths. Six standard-library Python evaluation checks remain part of the 0.8 model tooling. The new intake/save/export/reopen flow also passed on the supplied local recording; this is workflow evidence, not accuracy evaluation. The 0.7 baseline contained 22 checks, including live overload/lifecycle and 60 FPS review timing alongside the existing media, inference, tracking, storage, and desktop checks. The integrated webcam also passed two short capture/detect/track/stop cycles at 1280×720 with clean device release; see [live camera evidence](LIVE_CAMERA.md). Stored review continues to leave the database unchanged. These are integration checks, not natural-video counting-accuracy measurements. Representative labelled footage, unplug/reconnect behaviour, native dialogs, and sustained memory/disk/latency measurements remain open. No leak detector has been run.

## Repository publication

Working repository name: **FrameTrail**. GitHub owner: **MogProgJ**.

Repository: [MogProgJ/FrameTrail](https://github.com/MogProgJ/FrameTrail). Created as a private repository on 2 October 2026.

The user-facing checkout is `C:\Users\nazee\Documents\All Modules\FrameTrail`. An independent editing checkout under the MiniERP workspace is synchronized through this repository.

## Decisions already made

- Recorded files and images before live input.
- Stationary-camera person/vehicle crossing events as the first video use case.
- One source and one selected detector per workspace; Nano and S are supported.
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

## Phase 7 additions

Stage-separated CPU profiling and a private portable Windows packaging workflow
are available. The desktop uses a Qt Designer form and shared visual theme with
a right-hand settings inspector, more space for video, and explicit idle camera
messaging. See [performance](PERFORMANCE.md), [packaging](PACKAGING.md), and
[design](DESIGN.md). No new real-camera test was performed for this update.

## Saved-analysis revamp (0.9)

Video analysis accepts a recording directly without a counting line, displays timestamped appearances, then offers Save analysis and Export CSV. The GUI hides advanced settings and unused result/paging controls, and preserves older crossing files. Run IDs and first/last source times are exported; short gaps and uncertain tracker identities are documented. The native CPU/model baseline is unchanged. See [the new workflow](SAVED_RUNS.md).

## Optional GPU branch (0.10)

A native DirectML adapter uses a separately pinned 1.24.4 runtime without replacing CPU ONNX Runtime 1.30.0. CPU remains the default; automatic mode reports failures and falls back, while strict GPU mode validates benchmarks. On this GTX 1650 Ti the warm S pipeline improved from 6.12 to 25.51 FPS (4.17×), with higher memory use and loading cost. Nano's short overall run was slower despite a modest warm gain. Frozen selected-target recovery stayed 18/24 for Nano and 24/24 for S. Saved-analysis layout/flow remain unchanged; its preference is inherited from the player, and runtime evidence is stored/exported. See [GPU inference](GPU_INFERENCE.md).

## Immediate next work

Validate the new video-analysis workflow through native File Explorer/dialogs and representative longer recordings. Broaden real-footage annotations and assess tracking identities/event reliability before selecting another model or training branch. Evaluate short labelled recorded/live people or vehicle crossings; schedule a sustained webcam test, including unplug/reconnect, only with explicit camera authorization. Profiling and private packaging are now implemented; use their measurements to guide optimization and validate the package on a clean Windows machine. Preview Fit/100% zoom and broader quality refinements remain deferred; the reported saved-review timing issue received a focused fix in 0.6.

The [compute and training plan](COMPUTE_AND_TRAINING.md) is integrated as conditional Phase 8. No cluster environment or cloud service will be added until evaluation identifies a concrete accuracy, throughput, or scale constraint.

Application implementation has begun following the user's instruction on 2 October 2026. Optional agent orchestration and hosted AI services remain deferred.
