# CPU model selection and evaluation (0.8)

## Use the stronger option

Open the desktop application and choose **YOLOX-S · more detail** under **Detection model**. Keep **Detect objects** enabled. CPU is the default; [optional GPU inference](GPU_INFERENCE.md) is now available. Nano stays the default for faster playback. S requires more CPU, so recorded playback can run slower than real time. The live window offers the same choice while stopped and continues to report skipped frames when analysis falls behind.

Model changes preserve the displayed file frame and previous paused/playing state. Temporary tracking IDs and counters restart at that position. Saved analysis captures the selected model and thresholds for the entire run; changing the player afterwards does not alter that run.

Install both pinned exports in a fresh checkout:

```powershell
.\scripts\fetch-model.ps1 -Model all
.\scripts\build.ps1
.\build\windows-msvc\Release\frametrail-desktop.exe
```

A missing S option is disabled. Fetch, rebuild, and reopen the app. Neither model is downloaded during playback. The native application needs no Python service or GPU runtime.

| Model | Native input | Raw output | Weight size | Intended choice |
| --- | --- | --- | --- | --- |
| YOLOX-Nano | 416 × 416 | 3,549 × 85 | About 3.6 MB | Faster CPU preview |
| YOLOX-S | 640 × 640 | 8,400 × 85 | 35,858,002 bytes | More detailed offline analysis |

Both use the publisher's 0.1.1rc0 ONNX export and the same 80 COCO categories. S cannot add categories such as balloons. This is a controlled pretrained upgrade, not a state-of-the-art claim. See the [publisher's export guide](https://github.com/Megvii-BaseDetection/YOLOX/tree/6ddff4824372906469a7fae2dc3206c7aa4bbaee/demo/ONNXRuntime) and [pinned S manifest](../dependencies/yolox-small.json).

## What the integration audit found

The existing BGR channel order, 0–255 range, top-left letterbox, padding value 114, objectness × class confidence, and raw grid decoding agree with the publisher's expected contract. No major label-map or normalization error was identified. Half-pixel interpolation rounding and class-aware continuous-coordinate NMS remain documented implementation differences; no pixel-exact parity claim is made. See [native detection contract](DETECTION.md).

Each model now has an explicit profile. A wrong profile, wrong tensor dimensions, unsupported dtype or different number of inputs/outputs produces an error. Tensor shape alone does not establish that arbitrary weights have the right semantics: use the checksum-pinned exports. No filename guessing or generic ONNX compatibility is implied.

## Local comparison on 3 October 2026

A user-supplied 10-second generated park clip, H.264, 1280 × 720 at 24 FPS, supplied the regression input. Five snapshots were extracted using FFmpeg `fps=1/2`; 24 selected visible objects were manually annotated before examining detector output. Annotations use approximate visible bounding boxes. Other visible objects were deliberately left unlabelled, so this is **partial annotation**, not a complete benchmark. Source frames, annotations, output CSVs and detailed reports remain in ignored local storage; no user footage is committed or packaged.

Fixed settings: confidence 0.35, class-aware NMS IoU 0.45, one-to-one same-class matching at box IoU ≥ 0.5. The laptop baseline is an Intel Core i7-10750H, Windows x64 Release, ONNX Runtime 1.30.0 CPU, four intra-op threads and one inter-op thread.

| Selected targets | Nano matched | S matched |
| --- | --- | --- |
| Street: two people, dog, three cars, bus | 6 / 7 | 7 / 7 |
| Flying frisbee | 1 / 1 | 1 / 1 |
| Catching scene: two people, frisbee, dog | 3 / 4 | 4 / 4 |
| Five grounded birds | 1 / 5 | 5 / 5 |
| Seven plaza pedestrians | 7 / 7 | 7 / 7 |
| Total | **18 / 24** | **24 / 24** |

Nano's missed background dog had a spatially matching **person** prediction at confidence 0.368. S recovered the dog, the bus and the five selected birds. Both recovered the selected frisbee targets. The balloon is outside the supported vocabulary and was not included as a target.

A separate sequential full-video pass processed all 240 frames:

| Measurement | Nano | S |
| --- | --- | --- |
| Mean preprocessing + inference + postprocessing | 25.05 ms/frame | 188.91 ms/frame |
| Whole-process decode/detect/export throughput | 27.52 FPS | 5.03 FPS |
| Wall time including startup/model loading | 8.72 seconds | 47.77 seconds |

These are single-run observations, not controlled repeated benchmarks; power state, background load and temperature can change them. The video pass had no tracking or GUI. Snapshot first-inference times are separately available in the local JSON and must not be mistaken for warm video timing.

**Interpretation:** S recovered more of the selected targets, at substantial CPU cost. This does not establish precision, mAP, event accuracy, robustness on real footage, or absence of wrong labels. No whole-frame precision is reported from partial annotations. Keep Nano for responsiveness; select S when offline detail matters. The result justifies investigating optional acceleration next, before committing to training or a Python service.

## Repeatable evaluation tooling

The native CLI supports an explicit profile and confidence:

```powershell
.\build\windows-msvc\Release\frametrail.exe inspect .\samples\clip.mp4 --detect .\models\yolox_s.onnx --model-type small --confidence 0.35 --detections .\output\small.csv --profile .\output\small-timing.csv
.\scripts\profile.ps1 -InputFile .\samples\clip.mp4 -Model small
```

`--model-type` defaults to `nano`; model options require `--detect`. Existing output paths are refused. Profiling logs selected model identity and hashes.

For annotated images, `scripts/evaluate-detectors.py` uses only Python's standard library to call the native CLI twice. Python is a development/evaluation tool, not part of desktop inference. Create a JSON manifest beside your images:

```json
{
  "schema": 1,
  "images": [{
    "path": "example.png",
    "width": 1280,
    "height": 720,
    "complete": false,
    "objects": [{"class_id": 0, "box": [100, 100, 200, 400]}]
  }]
}
```

Coordinates are original-image `[left, top, right, bottom]`; IDs use the contiguous 0–79 label order in `src/detector.cpp`. The example box is illustrative, not a reference annotation. `complete: true` means **all supported visible objects** have been labelled, not just classes of interest. Leave false when uncertain. The tool rejects videos and mismatched dimensions, and refuses an existing output directory.

```powershell
python -B .\scripts\evaluate-detectors.py --manifest .\samples\annotations.json --cli .\build\windows-msvc\Release\frametrail.exe --models .\models --output .\output\comparison-new
python -B .\tests\test_evaluation.py
```

The report preserves image/model/executable/manifest hashes, fixed thresholds, matched and missed reference targets, spatial wrong-label review hints, and timings. Predictions are matched in confidence order, once per reference object. For partial annotations, precision and false-positive counts are null. Overlapping different labels are review hints because distinct objects can overlap. Empty-label images have undefined recall. This is a fixed-threshold comparison, not COCO mAP.

## Compatibility and remaining gates

Version 0.8 introduced schema 2 with `model_type`, reading schema 1 as Nano without modifying it. Version 0.9 adds schema 3 for appearance analysis while retaining read-only support for schemas 1/2; see [video analysis](SAVED_RUNS.md). Older apps cannot open newer schemas. The 0.8 validation passed 25 native/desktop CTest checks and six evaluation scorer checks. Its private ZIP passed manifest hashing, Nano/S CLI inference and offscreen GUI startup with development PATH removed; clean-machine validation remains open. Both variants are checked through native inference, coordinate contracts, cancellation, reference images, paused desktop switching and model metadata round trips. Camera testing for the 0.8 update used synthetic lifecycle tests and idle device enumeration only.

Next: broaden held-out detection and identity/crossing labels. Optional GPU inference is implemented; [tracking evaluation](TRACKING_EVALUATION.md) records the next gate. Keep CPU available. Real-world full annotations, false-positive inspection, tracking identity/crossing evaluation, camera soak tests and clean-machine package checks remain open. Cluster training, Python workers, cloud hosting and agents retain their separate roadmap gates.


## Recognition expansion (0.12)

The current additional comparison includes Open Images and experimental World S/M on fixed public animal/balloon references plus supplied-clip snapshots. See [recognition](RECOGNITION.md) and [recorded evidence](benchmarks/recognition-0.12.json). Open Images improves vocabulary and fox recovery but regresses on the earlier recording; the table above remains a historical Nano/S comparison. `evaluate-detectors.py --variants small world-s world-m openimages` uses the same original-image, same-class, one-to-one IoU matching and partial-label limitations. Application IDs now extend through 614 and are model-specific; use the reviewed recognition registry rather than raw publisher indices.
