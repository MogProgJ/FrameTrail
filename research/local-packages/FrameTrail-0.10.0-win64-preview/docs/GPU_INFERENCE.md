# Optional native GPU inference (0.10)

The next Phase 8 slice adds an optional **DirectML GPU backend**. It accelerates the existing Nano/S detector; it does not add categories, train a model or improve its learned labels. C++ still owns decoding, preprocessing, tracking, persistence and the GUI. No Python service, CUDA toolkit installation, cloud account or cluster job is introduced.

## Try it

From the repository, explicitly acquire the optional native dependency, then rebuild:

```powershell
.\scripts\fetch-gpu.ps1
.\scripts\build.ps1
.\build\windows-msvc\Release\frametrail-desktop.exe
```

The tested private 0.10 package already includes it. In the main player's inspector choose **Processing device → GPU · CPU fallback**. Choose **YOLOX-S · more detail** when the stronger detector is useful. The display reports the actual GPU/CPU path; hover over the frame details for provider, runtime, device and any fallback reason. Switching retains the current source position and paused/playing state.

CPU remains the default. It starts quickly and consumes less memory; short Nano runs do not necessarily benefit from GPU startup. If optional runtime loading, adapter selection, session creation or an inference call fails, the automatic option retries on the CPU. Cancellation does not trigger fallback. The GUI remains responsive while its existing ordered worker creates or runs the session. Driver/device-loss behaviour beyond the tested failure cases remains to be evaluated.

**Saved analysis keeps the 0.9 layout and flow.** Select the processing device in the main player before opening Video analysis; that window captures the preference and uses it for its next runs. Its existing model/confidence controls, choose/drop → analyse → review → save/export sequence and older-file review remain unchanged. An already open analysis window keeps its captured preference. The live window also has a processing-device selector, editable while stopped. No camera was activated during this update.

## CLI and reproducible comparison

```powershell
.\build\windows-msvc\Release\frametrail.exe inspect recording.mp4 --detect models\yolox_s.onnx --model-type small --backend auto
.\build\windows-msvc\Release\frametrail.exe inspect recording.mp4 --detect models\yolox_s.onnx --model-type small --backend directml
.\scripts\compare-backends.ps1 -InputFile recording.mp4 -Frames 120 -Warmup 10
```

`cpu` is the CLI default. `auto` permits GPU-to-CPU fallback. `directml` is a strict diagnostic path: missing support or GPU failure is an error, so benchmarks cannot quietly measure a CPU fallback. Optional `--gpu-device N` chooses a DXGI adapter index. Without it, the adapter enumerates DirectX 12 hardware devices and chooses the one with most dedicated video memory. This selected the laptop's GTX 1650 Ti, rather than the integrated Intel GPU. It is a simple explicit policy, not a general ranking of every GPU.

The comparison script runs CPU and strict GPU sequentially for both models using identical source, model and executable hashes. It records warm pipeline mean/p50/p95, process wall time, OS working-set sampling, runtime and device. Pipeline time includes decode/RGB, preprocessing, synchronized inference/transfers, postprocessing and tracking. It is not GUI presentation FPS, sensor latency or a sustained temperature guarantee. GPU memory is not measured by the process working-set counter.

Developer label tooling accepts `--backend cpu` or `--backend directml`. It checks actual provider identity before scoring. Python remains an optional local development tool, outside the shipped application.

## Measured gate result

On this laptop: Intel Core i7-10750H, GTX 1650 Ti 4 GiB, NVIDIA driver 581.95, Windows x64 Release. The comparison used the first 120 frames of the supplied 1280 × 720 / 24 FPS generated park clip, excluding the first 10 frames from warm metrics. Confidence 0.35, NMS IoU 0.45 and the same tracking/counting configuration were used for both paths.

| Model | CPU pipeline | GPU pipeline | Warm effective FPS, CPU → GPU | Pipeline gain | Whole 120-frame process, CPU → GPU |
| --- | --- | --- | --- | --- | --- |
| Nano | 20.44 ms | 17.21 ms | 48.93 → 58.09 | 1.19× | 2.82 → 4.18 s |
| S | 163.41 ms | 39.21 ms | 6.12 → 25.51 | 4.17× | 19.77 → 5.95 s |

GPU p95 pipeline times were 23.62 ms for Nano and 46.53 ms for S. Sampled process peaks grew from about 79/161 MiB on CPU to 289/326 MiB on GPU for Nano/S. Model loading and graph preparation account for part of the short-run cost. The important result is that S benefits substantially while Nano has a modest warm gain and loses on short overall duration. See the [sanitized measurement summary](benchmarks/2026-10-03-gpu.json); raw input, annotations and detailed results stay local and ignored.

The frozen 24 selected targets from five partially labelled snapshots produced the same recovery counts: Nano 18/24 and S 24/24 on CPU and GPU. The public reference-photo checks also compare strong same-class boxes/confidences and repeated GPU outputs. This is limited regression evidence, not full precision, event accuracy or exact numerical equality. GPU arithmetic can change scores near thresholds or NMS boundaries.

## Runtime/module boundaries

The linked **CPU ONNX Runtime 1.30.0 is preserved**. Microsoft's published DirectML package is **1.24.4**, with DirectML 1.15.4; the versions differ. The GPU DLLs live under `backends/directml`, loaded by an absolute application-relative path. `DmlInference` binds its own C API-24 table and owns that module's environments, sessions, run options and tensors through RAII. It never hands them to the linked CPU runtime's C++ API. Runtime version is checked before use, and telemetry is disabled in both environments.

This makes the measurement a comparison of the two shipped runtime paths, not a provider-only experiment on one runtime version. The packages/checksums/native file map are pinned in `dependencies/windows-directml.json`. Acquisition extracts only selected x64 files, headers and notices into ignored `.deps`. No global DLL path or Windows setting is changed.

GPU session execution is sequential with memory-pattern optimization disabled. One ordered worker owns each session; concurrent calls to the same DirectML session are not supported. Preprocessing/postprocessing and source-coordinate mapping are shared with CPU. `Run` is synchronous, including host/device transfers; output tensors become owned CPU values before the GPU resources are released. ONNX Runtime may assign unsupported graph operations to CPU within a DirectML session; provider selection does not mean every operator is a GPU kernel. See [Microsoft's DirectML execution-provider contract](https://onnxruntime.ai/docs/execution-providers/DirectML-ExecutionProvider.html).

DirectML is in sustained engineering; Microsoft's current Windows guidance prefers WinML for new Windows integrations. This isolated optional adapter is a bounded compatibility experiment, not a commitment to DirectML as the final backend. The backend seam and measurements can guide a later WinML/CUDA comparison without changing the saved-analysis flow. See [Windows runtime guidance](https://onnxruntime.ai/docs/get-started/with-windows.html).

New schema-3 analyses add optional requested/actual backend, runtime, device and fallback fields. The reader detects those columns; prior schema-1/2/3 files remain read-only and do not acquire invented runtime versions. Appearance CSV appends the actual execution metadata. It describes the final provider; a run that falls back can contain earlier GPU frames, with the transition explained in CPU fallback. No evidence rows are discarded or relabelled by backend switching.

## Checks and deployment

The standard suite now has 27 checks. `scripts/build.ps1 -GpuChecks` explicitly adds four hardware checks for Nano/S reference agreement, ordered GPU appearance analysis and desktop switching/save/export. All 31 native/desktop checks and six Python scorer checks passed on this laptop. An independent build with `FRAMETRAIL_ENABLE_DIRECTML=OFF` verifies the optional dependency boundary and CPU fallback. Old appearance files retain their original evidence.

`package.ps1` includes GPU binaries/notices only when the current build enabled the module, and records their hashes. `check-package.ps1 -GpuChecks` checks strict Nano/S GPU inference with development PATH removed. All smoke input is file-based; it does not start a camera. CPU-only machines can use the same private preview with automatic fallback. GPU removal/driver resets, multiple concurrent windows, additional adapters/DPI settings, long-recording memory/temperature and GPU live-camera latency remain evaluation work.

Training, bwUniCluster, Python inference and cloud services remain separate conditional branches. This slice demonstrates a useful local speed gain for S; it does not establish a need to start those branches.
