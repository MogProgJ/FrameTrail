# FrameTrail

A native Windows desktop app that turns images, videos and a webcam feed into detected objects, tracked appearances with timestamps, line-crossing counts and CSV exports. Private project.

The current focus is training a much stronger detector: an RF-DETR model fine-tuned on Open Images to recognise about 600 everyday object categories. See [AGENTS.md](AGENTS.md) for the goal, plan, rules and status, and [training/README.md](training/README.md) for the model pipeline.

## Run and update

- **Open FrameTrail:** the **FrameTrail** shortcut on the desktop or in the Start menu, or double-click `FrameTrail.cmd`. It opens the built app at once; nothing is compiled.
- **After code updates:** double-click `Update-FrameTrail.cmd`. It pulls the new code, rebuilds only the app (seconds for small changes, a few minutes after large ones), refreshes the shortcuts and opens FrameTrail. Close FrameTrail first.
- The full `.\scripts\build.ps1` also builds and runs all test programs; use it to check changes, not to open the app.

## Use the app

1. Start on **Home**: drop a video or photo, or pick a tool. Recent files are listed there.
2. **Preview** plays it with live detection; drag the timeline to jump, click an object type under *In view* to focus on it, Ctrl+S saves a snapshot. Draw a line to count crossings.
3. **Analysis** scans a whole video once: object chips, a timeline of appearances and thumbnails. Save the analysis or export CSV.

## Build (Windows x64)

Needs Visual Studio 2022 C++ tools and CMake 3.25+.

```powershell
.\scripts\fetch-dependencies.ps1
.\scripts\fetch-model.ps1 -Model all
.\scripts\build.ps1
.\scripts\install-shortcut.ps1
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
