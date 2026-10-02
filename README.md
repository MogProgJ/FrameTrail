# FrameTrail

A native desktop application being built to turn images and video into detections, object tracks, and reviewable events.

**Status: tracking and counting-line baseline implemented (0.4).** Open a recording to see YOLOX-Nano detections, people/vehicle track IDs, trails, and directional crossing counts. Draw a finite counting line and choose the tracked classes. The CLI exports detections, tracks, and events as CSV. Saved event review and live input remain planned; counting accuracy still needs evaluation on labelled footage.

FrameTrail will begin with local images and prerecorded video. A later release will accept a live camera feed through the same processing core. The initial use case is counting people or vehicles crossing a user-defined line in footage from a fixed camera.

## What a user will do

1. Open an image or video file.
2. Choose the object classes to detect, initially people and vehicles.
3. For video, draw a counting line and choose a crossing direction.
4. Run analysis and see boxes, object IDs, and recorded events.
5. Click an event to review the corresponding footage and export results as CSV.

Still images support detections and an annotated preview. They do not support movement tracking or crossing events because those require observations over time.

## Start reading here

| Document | What it explains |
| --- | --- |
| [Project brief and interface sketch](docs/PROJECT_BRIEF.md) | The product, first release, and proposed screen |
| [Architecture](docs/ARCHITECTURE.md) | How frames move through the system and why the modules exist |
| [Equipment and setup](docs/EQUIPMENT_AND_SETUP.md) | Hardware, proposed dependencies, and what to inspect before installing anything |
| [Roadmap](docs/ROADMAP.md) | Implementation milestones and evidence needed to complete them |
| [Compute, training, and bwUniCluster](docs/COMPUTE_AND_TRAINING.md) | Realistic gates for GPU inference, Python training, KIT cluster use, and cloud services |
| [Current status](docs/STATUS.md) | What exists now, open decisions, and the next work |
| [Glossary](docs/GLOSSARY.md) | Plain-language definitions of the technical terms |
| [Build and development guide](docs/DEVELOPMENT.md) | How to run the desktop/CLI, read the source, and understand its checks |
| [Tracking and counting lines](docs/TRACKING.md) | Desktop controls, CSV commands, association rules, crossing semantics, and accuracy limits |

## Build and try it (Windows x64)

With Visual Studio 2022 C++ tools and CMake installed, run these from the repository directory:

```powershell
.\scripts\fetch-dependencies.ps1
.\scripts\build.ps1
.\build\windows-msvc\Release\frametrail-desktop.exe
.\build\windows-msvc\Release\frametrail.exe inspect .\build\windows-msvc\fixtures\variable.mkv
```

The dependency script downloads checksum-pinned FFmpeg, Qt, ONNX Runtime, and YOLOX-Nano artifacts into ignored local folders. Use **Open media** with **Detect objects (CPU)** and **Track & count** checked. Adjust Confidence to filter predictions. Click **Draw counting line**, select A then B, and choose a direction. Settings apply at the current position and reset analysis IDs/counts there; playback resumes if it was playing and stays paused if it was paused. **Stop** preserves your position for **Play**, while **Replay** returns to the beginning. Playback remains silent; CPU analysis can slow playback. See [CPU detection](docs/DETECTION.md) and [tracking](docs/TRACKING.md) for contracts, exports, and validation limits.

## Implementation

C++20, CMake, FFmpeg, Qt Widgets, and ONNX Runtime form the current implementation. Preprocessing and box decoding are native C++; OpenCV is not required. SQLite remains planned. See [equipment and setup](docs/EQUIPMENT_AND_SETUP.md) for official references and pending decisions.

C++ will own the application and resource lifetimes. Native C APIs, particularly video decoding and storage, provide direct exposure to buffers, memory layout, and explicit resource management. Custom C components will be introduced only where a concrete interface or performance requirement justifies them.

## Scope and expectations

- Local processing; no cloud account required by the proposed design.
- One source at a time in the first release.
- An existing detection model; custom model training is outside the first release.
- CPU execution first; GPU acceleration follows measurement of actual hardware.
- Event accuracy and performance must be measured on representative footage.
- No fixed real-time frame-rate promise before benchmarking.

## Longer-term direction

Build and validate the native application first. Measured limits can later trigger local GPU inference, Python model training on bwUniCluster, or an optional Python worker; each has an explicit stop condition. Commercial cloud serving and agent-driven investigations remain later possibilities. See the [roadmap](docs/ROADMAP.md) and [compute/training plan](docs/COMPUTE_AND_TRAINING.md); none is a first-release dependency.

## Repository contents

This repository contains a reusable media library, background preview controller, desktop window, CLI, CMake build, dependency/build scripts, behaviour checks, and documentation. Local SDKs, build products, generated test footage, and exports are ignored by Git. YOLOX-Nano is downloaded separately and copied beside local development executables; weights are not committed.

Project licensing is undecided. Third-party binaries are acquired locally by the dependency script and are not committed or published as release artifacts. Synthetic test footage is generated locally. An optional upstream demonstration photo is downloaded separately for detection validation.
