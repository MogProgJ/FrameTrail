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
- A cancellable decoding worker, a two-frame queue with backpressure, and generation IDs for source changes.
- YOLOX-Nano CPU inference through ONNX Runtime, frame-aligned boxes/labels, a confidence control, and CLI detection CSV exports.
- CMake presets, PowerShell dependency/build scripts, and CTest checks using generated synthetic media.
- A development guide explaining commands, ownership, timing, and current limitations.

Version 0.3 builds and runs on Windows x64. Decoding and optional CPU detection execute sequentially on a background worker. Original-resolution frames and detections travel together to the UI. There is no audio playback, seeking, tracker, event storage, or live input yet. A reference-image smoke check and small CPU timing baseline exist; representative accuracy and movie benchmarks remain open. See [CPU detection](DETECTION.md).

## Development baseline and validation

Inspected hardware: Intel Core i7-10750H, approximately 15.8 GiB reported RAM, Intel UHD Graphics, and NVIDIA GeForce GTX 1650 Ti. CPU execution remains the initial analysis target.

Tools used: Visual Studio 2022 MSVC 19.44, bundled CMake 3.31.6, the checksum-pinned FFmpeg 8.1 branch SDK, Qt 6.11.3 base SDK, ONNX Runtime 1.30.0 CPU SDK, and YOLOX-Nano 0.1.1rc0. Manifests are under `dependencies/`. No system-wide dependency installation was performed.

Eleven CTest checks pass with the model and optional reference sample present. They cover media/CLI behaviour, queues/cancellation, preprocessing, box decoding, NMS, real inference, matched frame identity, exports, and desktop controls/overlays. Offscreen renderings have been inspected. The user also confirmed native playback of a large movie in 0.2. Representative detection clips, long-running memory behaviour, and native detection interaction still need evaluation. No leak detector or live-input test has been run.

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

## Decisions still open

- Confirm or rename FrameTrail.
- Initial repository visibility is private because no publication preference was specified; it can be changed later.
- Storage dependencies and any future image-processing dependency.
- Representative labelled sample footage and model upgrades if the baseline misses required objects.
- Hardware-dependent targets and initial supported file formats.
- Tracker choice and rule parameters.
- Project license and distribution model.

## Immediate next work

Evaluate detection on short people/vehicle clips, then implement tracking and line-crossing events. Preview Fit/100% zoom and quality refinements are explicitly deferred at the user's request. Seeking and event navigation remain later review work.

Application implementation has begun following the user's instruction on 2 October 2026. Optional agent orchestration and hosted AI services remain deferred.
