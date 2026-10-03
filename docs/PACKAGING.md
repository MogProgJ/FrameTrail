# Windows preview package (0.9)

Extract the whole ZIP to a writable folder, then open **frametrail-desktop.exe**.
Keep the DLLs, `platforms`, `models`, and `qt.conf` beside the executable.
This is a Windows x64 private preview. It needs no Python service, compiler,
cloud account or separately installed Qt. Audio playback and live recording
are not implemented. The application is unsigned.

## Detection models

Use the **Detection model** selector to choose faster Nano or more detailed, slower YOLOX-S. Both recognize 80 categories. S is included when `scripts/fetch-model.ps1 -Model all` was run before building/packaging. On one local 720p clip Nano processed about 27.5 FPS and S about 5 FPS; this varies with hardware and footage. Model changes preserve your playback position. New schema-3 saved runs require FrameTrail 0.9; older crossing runs remain readable. Open **Video analysis…**, choose/drop a video, analyse, review appearances, then save/export. See [the workflow](SAVED_RUNS.md).

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
Release CLI/GUI executables, FFmpeg and ONNX Runtime DLLs, pinned Nano and optional S weights (when installed),
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
