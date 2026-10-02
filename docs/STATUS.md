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
- CMake presets, PowerShell dependency/build scripts, and CTest checks using generated synthetic media.
- A development guide explaining commands, ownership, timing, and current limitations.

Version 0.2 builds and runs on Windows x64. The desktop displays images and plays recorded video using source presentation timestamps. Each decoder remains sequential, while the UI runs separately. There is no audio playback, seeking, detector, tracker, event storage, or live input yet. No model has been selected, and no detection/event accuracy or representative footage benchmark has been produced.

## Development baseline and validation

Inspected hardware: Intel Core i7-10750H, approximately 15.8 GiB reported RAM, Intel UHD Graphics, and NVIDIA GeForce GTX 1650 Ti. CPU execution remains the initial analysis target.

Tools used: Visual Studio 2022 MSVC 19.44, bundled CMake 3.31.6, the checksum-pinned FFmpeg 8.1 branch SDK, and Qt 6.11.3 base SDK. Both SDK manifests are under `dependencies/`. No system-wide dependency installation was performed.

Six CTest checks cover media contracts, CLI exports, preview queue bounds and cancellation, source generations, and desktop controls. The desktop check uses Qt's offscreen platform to verify rendering, pause/resume, EOF, replay, stop, invalid-file recovery, rapid source replacement, and closing with an active worker. Its rendered window has also been inspected. Native file-dialog interaction and representative long recordings still need manual checks. No leak detector or long-running live test has been run.

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
- Versions/acquisition for the future inference, image-processing, and storage dependencies.
- Detection model, weights license, and sample sources.
- Hardware-dependent targets and initial supported file formats.
- Tracker choice and rule parameters.
- Project license and distribution model.

## Immediate next work

Try the desktop on representative images and recordings. Next, select one pretrained detector, document its preprocessing/output contract, and add CPU inference with boxes aligned to the displayed frame. Seeking and event navigation remain later review work. The CLI remains available for inspecting recordings.

Application implementation has begun following the user's instruction on 2 October 2026. Optional agent orchestration and hosted AI services remain deferred.
