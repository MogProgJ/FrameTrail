# CPU object detection (0.3)

## What you can do

Open an image or recording with **Detect objects (CPU)** checked. FrameTrail draws boxes, class names, and confidence scores for the displayed frame. Detection is enabled by default when the local model exists. Unchecking it restores preview-only playback. Changing detection settings restarts the current source from the beginning.

The confidence control defaults to 0.35. Raising it hides weaker predictions; lowering it shows more candidates and can introduce false positives. A score is not a calibrated probability that a label is correct. The initial detector recognizes the 80 COCO categories, including people, bicycles, cars, motorcycles, buses, and trucks. Version 0.4 adds selected tracking classes, run-scoped IDs, and crossing counts; see [TRACKING.md](TRACKING.md). Persisting/reopening results remains later work.

The status line reports detections on the current frame and CPU milliseconds for preprocessing, inference, and postprocessing. Model loading and file decoding are outside that per-frame number. CPU analysis may make playback slower than the recording's original speed. Every decoded frame is processed in order; this offline mode does not drop frames to meet a playback deadline.

## Model and runtime

The first baseline uses the publisher's **YOLOX-Nano 0.1.1rc0 ONNX export**, approximately 3.6 MB, with **ONNX Runtime 1.30.0** on the CPU. This is a compact baseline chosen for native integration and modest compute, not a claim of state-of-the-art accuracy. The native application requires no Python service, cloud account, GPU runtime, or model training.

The dependency and model manifests record exact URLs and SHA-256 hashes. ONNX Runtime's hash was checked against its GitHub release asset digest. The older YOLOX asset has no published GitHub digest; its hash was recorded after downloading from the publisher's release. Downloads are explicit and local; no inference-time download occurs.

References: [official YOLOX ONNX deployment guide](https://github.com/Megvii-BaseDetection/YOLOX/tree/6ddff4824372906469a7fae2dc3206c7aa4bbaee/demo/ONNXRuntime), [ONNX Runtime release](https://github.com/microsoft/onnxruntime/releases/tag/v1.30.0), [model manifest](../dependencies/yolox-nano.json).

## Exact input and output contract

| Stage | Implementation |
| --- | --- |
| Input | Owned RGB24 frame from FFmpeg, at original decoded resolution |
| Resize | Fit into 416x416 with aspect ratio preserved; integer resized dimensions are floored, with a minimum of one pixel |
| Sampling | Half-pixel bilinear interpolation, rounded to uint8; may differ by one intensity level from OpenCV's optimized integer implementation |
| Padding | Place resized image at the top-left; fill remaining bottom/right area with 114 |
| Tensor | Float32 `[1,3,416,416]`, BGR planar order, values 0..255; no division by 255 or mean subtraction |
| Raw output | Float32 `[1,3549,85]`: four box values, objectness, and 80 class scores |
| Box decoding | Grid strides 8, 16, 32; centers use grid offsets, dimensions use exponentials |
| Score | Objectness multiplied by the highest class score for each candidate |
| Filtering | Confidence threshold, finite-value checks, clipping to original image bounds, discard empty boxes |
| Duplicate suppression | Class-aware NMS at IoU 0.45, continuous-coordinate areas, at most 100 boxes |
| Display | Map coordinates back by the resize ratio, then through the same fitted rectangle used to paint the source image |

This adapter accepts the pinned model's exact tensor contract. Other ONNX models may use RGB, normalized values, different label maps, or already-decoded boxes; they are not interchangeable. Our NMS uses class-aware continuous-coordinate overlap rather than the upstream Python demo's default class-agnostic inclusive-pixel convention. This choice is deliberate and tested.

The source frame and displayed QImage retain the original resolution. Only a separate inference tensor is reduced to 416x416. Fine or distant objects can be missed at this model input size. Preview zoom/scaling improvements are deferred at the user's request.

## How this fits the C++ core

`Detector` hides ONNX Runtime behind a C++ interface. It owns the runtime environment and model session. Session options use the CPU provider, four intra-operation threads, one inter-operation thread, and sequential graph execution. Telemetry is disabled for this environment.

`PreviewSession` creates the detector on its background worker, then decodes and analyzes one frame at a time. A `PreviewFrame` carries the original frame, source generation, and optional `DetectionResult` together through the existing two-item queue. The UI receives a matched pair and paints its boxes; it does not run inference.

An empty detection list means analysis ran and found no qualifying objects. An absent result means detection was disabled. File replacement clears the displayed boxes and invalidates old generations. Stop wakes a blocked queue and requests termination of an active ONNX Runtime run. Model-session construction itself is not interruptible, so cancellation can wait for that local initialization to finish while the UI remains responsive.

## Setup and CLI exports

```powershell
.\scripts\fetch-dependencies.ps1
.\scripts\build.ps1
.\build\windows-msvc\Release\frametrail-desktop.exe
```

The fetch command adds the CPU runtime SDK (about 83 MB compressed) and model to the existing FFmpeg/Qt setup. Models remain ignored by Git. The build copies the model into the executable's `models` directory, so desktop launching does not depend on the terminal's working directory. If the model is missing, the app can still preview media; enabling detection reports a useful error. Run `fetch-model.ps1` and rebuild to restore it.

The CLI uses the same detector and exports one CSV row per detection:

```powershell
New-Item -ItemType Directory -Path output -Force
.\build\windows-msvc\Release\frametrail.exe inspect "C:\Videos\entrance.mp4" --detect .\models\yolox_nano.onnx --detections .\output\detections.csv --max-frames 100
```

Columns: frame sequence, source-relative timestamp in microseconds, class ID, label, confidence, left/top/right/bottom in original-frame pixels, and detection time in milliseconds. Frames with no objects have no detection rows; use `--csv output\frames.csv` alongside detection export for a complete frame list. Existing outputs are refused. Errors may leave partial output. The `--preview` PPM export remains an unannotated source frame.

## Validation and measurement

Preprocessing checks cover BGR channel order, value range, row padding, interpolation, and letterbox padding. Crafted model outputs exercise grid decoding, coordinate recovery, duplicate suppression, class separation, invalid values, and score thresholds. Real-model checks process synthetic images and video, preserve frame identity/order, cancel inference, and reject missing/invalid models.

An optional pinned upstream demonstration image provides a real-image smoke check:

```powershell
.\scripts\fetch-detection-sample.ps1
.\scripts\build.ps1
```

This adds tests requiring dog and bicycle detections, validates CLI exports, and renders the desktop overlay for inspection. The image is stored under `.deps/detection-samples/`, not committed or packaged. Its source URL and checksum are in the fetch script. It is a demonstration input, not a representative accuracy dataset.

With model and sample present, all 11 CTest checks pass. The inspected overlay found dog, bicycle, and car boxes on the 768x576 photo. On the inspected i7-10750H, two Release runs averaged approximately 15 and 20 ms per frame, each over ten warm detections with four CPU threads. The second run reported 61.1 MiB peak process working set. This includes preprocessing/postprocessing and excludes model load, file decode, and UI drawing. Subsequent runs can differ with load and power state. The sample test also reports process peak working set on Windows; this includes runtime and decoder memory and is not a model-only allocation measurement.

No precision/recall study, representative movie benchmark, long-running memory baseline, or tracking/event evaluation is complete. Next, use short people/vehicle clips with manually checked expectations to measure misses, false positives, throughput, and resource use before building tracking rules.

## Notices

ONNX Runtime's SDK contains its MIT license and third-party notices. YOLOX's upstream repository declares Apache-2.0; its model remains a separately acquired local artifact. Preserve the selected artifacts' notices and complete the existing distribution review before packaging. The reference photo has separate provenance and is used only as an optional local validation input.
