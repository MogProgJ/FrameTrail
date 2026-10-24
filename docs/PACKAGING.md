# Windows preview package (0.12)

Extract the whole ZIP to a writable folder, then open **frametrail-desktop.exe**.
Keep the DLLs, `platforms`, `models`, and `qt.conf` beside the executable.
This is a Windows x64 private preview. It needs no Python service, compiler,
cloud account or separately installed Qt. Audio playback and live recording
are not implemented. The application is unsigned.

## Detection models

Choose **YOLOX-S** for the existing 80-category people/vehicle baseline, **Broad recognition · 597 categories** for the Open Images model (including fox), or experimental **YOLO-World S/M** for the 100-category export. Nano remains the faster CPU option. The private 0.12 preview includes these installed, checksum-verified models. Broader vocabulary has accuracy and speed tradeoffs; it does not fix the dark generated fox. S stays the default after comparison. See recognition.

Model changes preserve playback position. New schema-4 analyses require 0.12; schemas 1–3 remain readable. Open **Video analysis…**, choose/drop a video, analyse, review appearances, then save/export. See [the workflow](SAVED_RUNS.md).

## Optional GPU processing

The tested 0.12 preview includes DirectML under `backends/directml`; keep that folder with the app. Choose **Processing device → GPU · CPU fallback** in the main player before opening Video analysis. Its layout and flow remain unchanged. CPU stays the default and also handles unavailable GPU/runtime cases. No CUDA toolkit or global installation is needed. See [GPU setup and evidence](GPU_INFERENCE.md).

`package.ps1` includes the optional runtime and its notices only if the current build enabled it. For a strict local hardware check use `check-package.ps1 -GpuChecks`; the ordinary package check remains CPU-compatible.

## Camera behaviour

Opening the app does not activate a camera. **Live camera…** lists available
devices; **Start camera** explicitly starts capture. **Stop camera** releases it.
The live window displays camera state and explains local processing before Start.
No microphone is opened, and live frames are not recorded or uploaded.

Traditional Windows desktop apps can access a camera without a separate per-app
prompt when desktop camera access is enabled in Windows Settings → Privacy &
security → Camera. FrameTrail uses FFmpeg/DirectShow; it does not modify Windows
privacy settings. See [Microsoft's camera permissions explanation](https://support.microsoft.com/en-us/windows/privacy/manage-app-permissions-for-a-camera-in-windows).

## Build a package

From the repository, after fetching dependencies and the model:

```powershell
.\scripts\build.ps1
.\scripts\package.ps1
```

The script creates a new folder and ZIP under `out`, plus a ZIP SHA-256 file.
It refuses existing destinations and never deletes earlier builds. It includes
Release CLI/GUI executables, FFmpeg and ONNX Runtime DLLs, pinned Nano and optional S, World S/M and Open Images weights (when installed),
Qt libraries/plugins selected by `windeployqt`, app-local MSVC release runtime,
dependency manifests, upstream notices and Qt's supplied SBOM. `manifest.json`
records each staged file's size and SHA-256. Workflow guides are included under `docs`. No footage, saved runs, test
executables, editor files or credentials are included.

The script packages the current Release build; run `build.ps1` first to avoid
packaging an old executable. It does not download dependencies or install anything
system-wide. [Qt documents windeployqt here](https://doc.qt.io/qt-6/windows-deployment.html).

## Verify a package

```powershell
.\scripts\check-package.ps1 -PackageDirectory .\out\<package-folder> -InputFile .\build\windows-msvc\fixtures\variable.mkv
```

This verifies file hashes, clears development PATH/Qt plugin overrides, changes
the working directory, and checks local-file inference in the CLI and Qt GUI.
The GUI uses an offscreen platform and exits automatically. It never opens a
camera. `frametrail-desktop --smoke-test <local-file>` is a deployment diagnostic,
not a user playback mode.

This check on a development machine does **not** establish clean-machine support.
Before public release, test extraction/startup, Windows platform rendering, media,
saved review and camera permissions on a Windows machine without the SDKs. Source
availability/notices for all distributed components, FrameTrail's own license,
signing and installer policy also remain release gates. This package is for the
current private project's local evaluation; no public binary release is published.

## Tracking continuity

The 0.11 pipeline adds conservative scene-boundary resets and long-gap reconfirmation, while preserving the saved-analysis workflow. The GUI keeps greedy association; experimental global repair is an explicit CLI option until broader labels justify it. See tracking evidence and limits.
