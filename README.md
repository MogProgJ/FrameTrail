# FrameTrail

A native Windows desktop app that turns images, videos and a webcam feed into detected objects, tracked appearances with timestamps, line-crossing counts and CSV exports. Private project.

The current focus is training a much stronger detector: an RF-DETR model fine-tuned on Open Images to recognise about 600 everyday object categories. See [AGENTS.md](AGENTS.md) for the goal, plan, rules and status, and [training/README.md](training/README.md) for the model pipeline.

## Use the app

1. Open a video or image in **Preview**, or choose **Video analysis** and drop in a recording.
2. Analyse it, then review each object's appearances with first/last timestamps and thumbnails.
3. Save the analysis or export CSV. Draw a line in Preview to count crossings.

## Build (Windows x64)

Needs Visual Studio 2022 C++ tools and CMake 3.25+.

```powershell
.\scripts\fetch-dependencies.ps1
.\scripts\fetch-model.ps1 -Model all
.\scripts\build.ps1
.\build\windows-msvc\Release\frametrail-desktop.exe
```

Optional GPU support: run `.\scripts\fetch-gpu.ps1`, rebuild, then pick **GPU · CPU fallback** in the app. More detail is in [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Layout

| Path | Contents |
| --- | --- |
| `apps/`, `src/`, `include/` | Desktop app, CLI and core library (C++20, Qt, FFmpeg, ONNX Runtime, SQLite) |
| `tests/` | Native CTest checks and Python tool tests |
| `scripts/` | Build, dependency, packaging and profiling scripts |
| `dependencies/` | Pinned external artifacts and the app's 615-label vocabulary |
| `training/` | RF-DETR dataset preparation, training, evaluation and KIT cluster jobs |
| `docs/` | App reference: [architecture](docs/ARCHITECTURE.md), [detection](docs/DETECTION.md), [tracking](docs/TRACKING.md), [saved runs](docs/SAVED_RUNS.md), [GPU](docs/GPU_INFERENCE.md), [camera](docs/LIVE_CAMERA.md), [packaging](docs/PACKAGING.md) |
