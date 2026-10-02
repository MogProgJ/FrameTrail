# FrameTrail

A native desktop application being built to turn images and video into detections, object tracks, and reviewable events.

**Status: desktop preview implemented (0.2).** Open a local image or recorded video, play/pause, stop, and replay it in a Qt window. Decoding runs on a cancellable background worker with a bounded frame queue. The CLI still provides frame inspection and exports. Detection, tracking, event review, and live input are still planned.

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
| [Current status](docs/STATUS.md) | What exists now, open decisions, and the next work |
| [Glossary](docs/GLOSSARY.md) | Plain-language definitions of the technical terms |
| [Build and development guide](docs/DEVELOPMENT.md) | How to run the desktop/CLI, read the source, and understand its checks |

## Build and try it (Windows x64)

With Visual Studio 2022 C++ tools and CMake installed, run these from the repository directory:

```powershell
.\scripts\fetch-dependencies.ps1
.\scripts\build.ps1
.\build\windows-msvc\Release\frametrail-desktop.exe
.\build\windows-msvc\Release\frametrail.exe inspect .\build\windows-msvc\fixtures\variable.mkv
```

The dependency script downloads checksum-pinned FFmpeg and Qt SDKs into an ignored local folder. The build script compiles the application and runs six checks. In the window, use **Open media** to choose a file. Playback is silent; seeking and analysis overlays come later. See the [development guide](docs/DEVELOPMENT.md) for export examples, prerequisites, and current limitations.

## Implementation

C++20, CMake, FFmpeg, and Qt Widgets form the current implementation. OpenCV, ONNX Runtime, and SQLite remain candidates for later stages. See [equipment and setup](docs/EQUIPMENT_AND_SETUP.md) for official references and pending decisions.

C++ will own the application and resource lifetimes. Native C APIs, particularly video decoding and storage, provide direct exposure to buffers, memory layout, and explicit resource management. Custom C components will be introduced only where a concrete interface or performance requirement justifies them.

## Scope and expectations

- Local processing; no cloud account required by the proposed design.
- One source at a time in the first release.
- An existing detection model; custom model training is outside the first release.
- CPU execution first; GPU acceleration follows measurement of actual hardware.
- Event accuracy and performance must be measured on representative footage.
- No fixed real-time frame-rate promise before benchmarking.

## Longer-term direction

Build and validate the native application first. The baseline includes pretrained object detection but no agent orchestration. After the core workflow proves useful and reliable, evaluate an optional prompt-driven AI perception pipeline. An agent-driven investigation service is a final, longer-term possibility. See the [roadmap](docs/ROADMAP.md#future-ai-direction) for the staged decisions; neither extension is a first-release dependency.

## Repository contents

This repository contains a reusable media library, background preview controller, desktop window, CLI, CMake build, dependency/build scripts, behaviour checks, and documentation. Local SDKs, build products, generated test footage, and exports are ignored by Git. No model has been selected or bundled.

Project licensing is undecided. Third-party binaries are acquired locally by the dependency script and are not committed or published as release artifacts. Test footage is generated locally from synthetic sources.
