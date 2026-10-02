# FrameTrail

A planned native desktop application that turns images and video into detections, object tracks, and reviewable events.

**Status: architecture sketch only. There is no application to build or run yet.**

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

## Proposed implementation

C++20, CMake, Qt, FFmpeg, OpenCV, ONNX Runtime, and SQLite. These are architectural candidates, not installed or pinned dependencies. See [equipment and setup](docs/EQUIPMENT_AND_SETUP.md) for official references and pending decisions.

C++ will own the application and resource lifetimes. Native C APIs, particularly video decoding and storage, provide direct exposure to buffers, memory layout, and explicit resource management. Custom C components will be introduced only where a concrete interface or performance requirement justifies them.

## Scope and expectations

- Local processing; no cloud account required by the proposed design.
- One source at a time in the first release.
- An existing detection model; custom model training is outside the first release.
- CPU execution first; GPU acceleration follows measurement of actual hardware.
- Event accuracy and performance must be measured on representative footage.
- No fixed real-time frame-rate promise before benchmarking.

## Repository contents

This repository currently contains documentation and Git housekeeping only. Source directories, build configuration, dependencies, models, and executable code will be added during implementation.

Project licensing is undecided. No third-party binaries, models, or sample footage are bundled.
