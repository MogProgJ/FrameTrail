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
- CMake presets, PowerShell dependency/build scripts, and CTest checks using generated synthetic media.
- A development guide explaining commands, ownership, timing, and current limitations.

The first media foundation builds and runs on Windows x64. It is sequential and has no UI, detector, tracker, event storage, or live input yet. No model has been selected, and no detection/event accuracy or representative footage benchmark has been produced.

## Development baseline and validation

Inspected hardware: Intel Core i7-10750H, approximately 15.8 GiB reported RAM, Intel UHD Graphics, and NVIDIA GeForce GTX 1650 Ti. CPU execution remains the initial analysis target.

Tools used: Visual Studio 2022 MSVC 19.44, bundled CMake 3.31.6, and the checksum-pinned FFmpeg 8.1 branch SDK in `dependencies/windows-ffmpeg.json`. No system-wide dependency installation was performed.

Local CTest checks cover RGB layout, buffer ownership, delayed-frame flushing, variable timestamps, cancellation, invalid/audio-only files, Unicode paths, padded exports, and CLI output behaviour. Repeated opening is tested, but no leak detector or long-running live test has been run.

## Repository publication

Working repository name: **FrameTrail**. GitHub owner: **MogProgJ**.

Repository: [MogProgJ/FrameTrail](https://github.com/MogProgJ/FrameTrail). Created as a private repository on 2 October 2026.

The documentation is prepared locally inside the currently writable workspace. This directory is an independent project, even though its temporary location is below the MiniERP workspace.

GitHub CLI authentication was verified outside the sandbox for the intended account, `MogProgj`. The connector is authenticated as another user and was not used to create this project.

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
- Versions/acquisition for the future UI, inference, image-processing, and storage dependencies.
- Detection model, weights license, and sample sources.
- Hardware-dependent targets and initial supported file formats.
- Tracker choice and rule parameters.
- Project license and distribution model.

## Immediate next work

Extend the media foundation with a desktop preview and cancellable worker handoff. Select the detector and representative sample footage before the inference milestone. The current CLI is also available for inspecting user-provided recordings.

Application implementation has begun following the user's instruction on 2 October 2026. Optional agent orchestration and hosted AI services remain deferred.
