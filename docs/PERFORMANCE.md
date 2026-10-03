# Reproducible CPU measurements

Phase 7 begins with measurements and a private Windows preview package. It does
not automatically enable GPU inference or replace the baseline detector.

```powershell
.\scripts\profile.ps1 -InputFile C:\Videos\sample.mp4 -Frames 180
```

Use footage you are authorized to process. The command opens only the supplied
local file, never a camera. It creates a fresh `output/profile-...` directory with
`frames.csv`, `run.txt`, `errors.txt` and `summary.json`. The summary records CPU,
OS, executable/input/model hashes, dimensions, thread settings, detection/rule
settings, frame limit, observed peak working set, wall time and mean/p50/p95 stage
times. Five initial frames are excluded from the statistical summary by default;
every frame remains in the raw CSV. The first model load is still included in
process wall time. Use `-Warmup 0` for short inputs.

The underlying CLI also accepts `--profile <new-csv>` alongside existing inspect
options. It refuses existing outputs and reports failed writes. A failed command
can leave a partial CSV; use only successful runs for comparisons.

## What each timing means

| Column | Included work |
|---|---|
| `decode_rgb_ms` | Next packet/frame decoding, RGB conversion and owned RGB allocation |
| `preprocess_ms` | Resize, BGR tensor preparation and padding |
| `inference_ms` | Tensor/run-option setup and ONNX Runtime execution |
| `postprocess_ms` | Output checks, box decoding, confidence filtering and NMS |
| `tracking_ms` | Native association, history and crossing rules |
| `pipeline_ms` | Read-to-result work plus requested export/storage work, excluding writing this profile row |
| `rgb_bytes` | Owned source RGB frame size; not total memory traffic or allocations |

These are sequential offline CPU timings. They do not measure GUI paint cost,
camera/driver latency, displayed FPS or real-time scheduling. Peak working set is
observed from OS process counters while polling; a short startup/exit peak can be
missed. It is not a leak detector. p50/p95 use nearest-rank sorted frame samples.

## Frame-copy audit

`MediaReader` owns one RGB vector per decoded frame. File preview moves frames
through its bounded queue; Qt copies the selected RGB frame into an owned QImage
to keep its lifetime independent of the worker. The player also retains the source
frame needed to re-analyse settings at the held timestamp. Live processing uses
capacity-one pending input/results and an owned display image. Saved review uses
its own bounded reader. A 1280×720 RGB24 image alone occupies 2,764,800 bytes.

Removing these ownership boundaries without a measured benefit risks stale images
or data races. No zero-copy claim is made. Record stage timings first; optimize the
dominant measured stage and verify frame identity, cancellation and detections.

Representative movie performance, multi-minute memory measurements and labelled
crossing accuracy remain acceptance work. See [the roadmap](ROADMAP.md) and
[conditional GPU/training gates](COMPUTE_AND_TRAINING.md).

## First measured baseline

Recorded 2 October 2026 UTC, Release, i7-10750H,
12 logical processors, Windows build 26200, pinned YOLOX-Nano and ORT 1.30.0 CPU,
4 intra-op / 1 inter-op threads, confidence 0.35 and default people/vehicle tracking.
Input: 180 frames of generated 1280×720, 30 FPS MPEG-4 test pattern. Five warmup
frames excluded, leaving 175 samples. No GUI or camera was involved.

| Stage | Mean ms/frame | p95 ms/frame |
|---|---:|---:|
| Decode + RGB | 1.95 | 3.34 |
| Preprocess | 3.69 | 4.63 |
| Inference including setup | 9.17 | 11.47 |
| Postprocess | 0.77 | 1.02 |
| Tracking / rules | 0.001 | 0.002 |
| Whole pipeline | 15.70 | 19.39 |

Observed peak working set: 70.3 MiB; process wall time: 3.08 seconds, including
startup/model load. This is a short synthetic baseline, not a sustained benchmark
or a natural-video accuracy/throughput result. Tracking with few/no detections is
particularly unrepresentative of a crowded scene. Other system load and power
state can materially change results.

Inference is the largest measured stage. This one run does not justify enabling
GPU support or removing safe image ownership/copies. Profile representative media
and UI presentation before selecting that work.

Raw evidence: [summary and hashes](benchmarks/2026-10-02-cpu.json),
[per-frame timings](benchmarks/2026-10-02-cpu-frames.csv). The executable hash records
the tested binary before the final stored engine-version string changed to 0.7;
that later metadata-only change does not alter this timing path.

Recreate the input using the pinned FFmpeg executable (choose a new output path):

```powershell
ffmpeg -hide_banner -loglevel error -n -f lavfi -i "testsrc2=size=1280x720:rate=30:duration=6" -c:v mpeg4 -q:v 4 profile720p.mkv
```

The generated container may have a different file hash on regeneration; keep the
input used for each run with its reported hash when making precise comparisons.

## Scene and association profiling in 0.11

Profile CSV appends `scene_boundary`, `scene_difference` and `scene_histogram_distance`; existing timing columns remain in place. Tracking time includes the bounded scene sampler. Experimental repair calls a bounded global assignment solver only when greedy coverage may be improved. The dense maximum-size solver stress case is deliberately more expensive than normal scenes; no blanket real-time or crowd-performance guarantee is made. See [tracking evaluation](TRACKING_EVALUATION.md).
