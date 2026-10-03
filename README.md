# FrameTrail

A native desktop application being built to turn images and video into detections, object tracks, and reviewable events.

**Status: broader recognition implemented (0.12).** Optional native Open Images recognition expands to 597 categories, including fox; YOLO-World S/M offer an experimental 100-category vocabulary. Small reference-set results improve, while YOLOX-S stays the default after a people/vehicle regression with broader models. See [recognition and evidence](docs/RECOGNITION.md). Optional GPU processing and the existing saved-analysis workflow remain available. Dark-footage accuracy and broader acceptance remain open.

FrameTrail accepts local images, prerecorded video, and one Windows webcam through the native processing core. The initial use case is counting people or vehicles crossing a user-defined line in footage from a fixed camera.

## What a user will do

1. Open **Video analysis…** and choose or drop a recording.
2. Click **Analyse video**; optionally change model/confidence in Analysis settings.
3. Review object labels, first/last timestamps and thumbnails.
4. Click an appearance to review its source footage.
5. Save the analysis locally or export its CSV.

The main player separately supports image detections, playback and people/vehicle counting across a drawn line. Appearance IDs are approximate tracker associations, not verified unique real objects.

Still images support detections and an annotated preview. They do not support movement tracking or crossing events because those require observations over time.

## Start reading here

| Document | What it explains |
| --- | --- |
| [Project brief and interface sketch](docs/PROJECT_BRIEF.md) | The product, first release, and proposed screen |
| [Architecture](docs/ARCHITECTURE.md) | How frames move through the system and why the modules exist |
| [Equipment and setup](docs/EQUIPMENT_AND_SETUP.md) | Hardware, proposed dependencies, and what to inspect before installing anything |
| [Roadmap](docs/ROADMAP.md) | Implementation milestones and evidence needed to complete them |
| [Compute, training, and bwUniCluster](docs/COMPUTE_AND_TRAINING.md) | Realistic gates for GPU inference, Python training, KIT cluster use, and cloud services |
| [Dataset and training tooling](docs/TRAINING.md) | General-object catalogue, bounded sample, training/export commands, evidence and cluster handoff |
| [Training-readiness audit](docs/TRAINING_READINESS.md) | Broad recognition prerequisites; fox/dog and low light as difficult evaluation slices |
| [Current status](docs/STATUS.md) | What exists now, open decisions, and the next work |
| [Glossary](docs/GLOSSARY.md) | Plain-language definitions of the technical terms |
| [Build and development guide](docs/DEVELOPMENT.md) | How to run the desktop/CLI, read the source, and understand its checks |
| [Optional GPU inference](docs/GPU_INFERENCE.md) | Processing-device controls, isolated runtime, comparison and fallback |
| [Broader recognition](docs/RECOGNITION.md) | Open Images / YOLO-World choices, vocabulary, evidence, tradeoffs and optional export setup |
| [Model selection and evaluation](docs/MODEL_EVALUATION.md) | Nano/S choice, local comparison, speed tradeoffs and annotation tooling |
| [Tracking and counting lines](docs/TRACKING.md) | Desktop controls, CSV commands, association rules, crossing semantics, and accuracy limits |
| [Saved analysis and review](docs/SAVED_RUNS.md) | Video intake, timestamped appearances, review, optional saving, CSV, and partial results |
| [Live camera](docs/LIVE_CAMERA.md) | Webcam controls, bounded capture/analysis, skip metrics, and stop/restart |

## Build and try it (Windows x64)

With Visual Studio 2022 C++ tools and CMake installed, run these from the repository directory:

```powershell
.\scripts\fetch-dependencies.ps1
.\scripts\build.ps1
.\build\windows-msvc\Release\frametrail-desktop.exe
.\build\windows-msvc\Release\frametrail.exe inspect .\build\windows-msvc\fixtures\variable.mkv
```

For optional GPU inference, run `scripts/fetch-gpu.ps1`, rebuild, then select **Processing device → GPU · CPU fallback** in the player. That preference carries into Video analysis when you open its window. CPU is the default; the portable 0.12 preview includes GPU support.

For the optional stronger detector, also run `scripts/fetch-model.ps1 -Model all` **before building** and select **YOLOX-S · more detail** in the app.

For foxes and the wider vocabulary, select **Broad recognition · 597 categories**; the private 0.12 package includes it. Fresh source checkouts use the optional pinned export setup in [recognition](docs/RECOGNITION.md).

The dependency script downloads checksum-pinned FFmpeg, Qt, ONNX Runtime, YOLOX-Nano, and SQLite artifacts into ignored local folders. Use **Open media** with **Detect objects** and **Track & count** checked. Adjust confidence, draw the line, and choose a direction. Player edits preserve your position and reset temporary analysis counts there. **Stop** preserves your position for **Play**, while **Replay** returns to the beginning. For a whole recording, click **Video analysis…**, choose/drop the video, and **Analyse video**. Review appearances before using **Save analysis…** or **Export CSV…**; no counting line or player tracking setup is needed. Playback remains silent; CPU analysis can slow playback. See [saved runs](docs/SAVED_RUNS.md), [CPU detection](docs/DETECTION.md), and [tracking](docs/TRACKING.md).

## Implementation

C++20, CMake, FFmpeg, Qt Widgets, ONNX Runtime, and SQLite form the current implementation. Preprocessing and box decoding are native C++; OpenCV is not required. SQLite's C source is compiled locally into the core. See [equipment and setup](docs/EQUIPMENT_AND_SETUP.md) for official references and pending decisions.

C++ will own the application and resource lifetimes. Native C APIs, particularly video decoding and storage, provide direct exposure to buffers, memory layout, and explicit resource management. Custom C components will be introduced only where a concrete interface or performance requirement justifies them.

## Scope and expectations

- Local processing; no cloud account required by the proposed design.
- One source at a time in the first release.
- Existing pretrained detectors in the app; offline dataset/training tooling is available, with trained-model adoption gated by reviewed evaluation.
- CPU is the default; optional GPU acceleration has been measured on the target hardware.
- Event accuracy and performance must be measured on representative footage.
- No fixed real-time frame-rate promise before benchmarking.

## Longer-term direction

Build and validate the native application first. Measured limits can later trigger local GPU inference, Python model training on bwUniCluster, or an optional Python worker; each has an explicit stop condition. Commercial cloud serving and agent-driven investigations remain later possibilities. See the [roadmap](docs/ROADMAP.md) and [compute/training plan](docs/COMPUTE_AND_TRAINING.md); none is a first-release dependency.

## Repository contents

This repository contains a reusable media library, background preview controller, desktop window, CLI, CMake build, dependency/build scripts, behaviour checks, and documentation. Local SDKs, build products, generated test footage, and exports are ignored by Git. YOLOX-Nano is downloaded separately and copied beside local development executables; weights are not committed.

Project licensing is undecided. Third-party binaries are acquired locally by the dependency script and are not committed or published as release artifacts. Synthetic test footage is generated locally. An optional upstream demonstration photo is downloaded separately for detection validation.

## Performance and Windows preview package

The 0.7 desktop refresh adds a video-first workspace and shared styling. See [design](docs/DESIGN.md). Use `scripts/profile.ps1 -InputFile <local-video>` for stage timings and `scripts/package.ps1` after a Release build for a private portable ZIP. See [performance](docs/PERFORMANCE.md) and [packaging](docs/PACKAGING.md) for commands, measurement limits and remaining release checks.
