# Roadmap and acceptance evidence

These milestones are ordered by dependencies, not estimated calendar dates. Implementation has begun with the native media library and CLI; see [current status](STATUS.md) and the [development guide](DEVELOPMENT.md).

## Phase map

| Phase | Purpose | Status / entry rule |
| --- | --- | --- |
| 0–2 | Project definition and native media foundation | Implemented; representative-media validation remains |
| 3 | CPU object detection | Implemented; evaluate on labelled people/vehicle footage |
| 4 | Tracking and line-crossing events | Baseline implemented; labelled event/identity evaluation remains |
| 5 | Persist and review events | Baseline implemented; representative workflow/resource evaluation remains |
| 6 | One live input | Windows webcam baseline implemented; sustained hardware and accuracy validation remains |
| 7 | Profile, optimize, and package | After the complete native workflow is measurable |
| 8 | Conditional compute and model expansion | Enter individual gates only when measured limits justify them |
| 9 | Optional advanced perception and agents | After the native product proves useful |

Phases 0–7 are the core product path. Phase 8 is a set of optional branches, not a promise to add every technology. A branch may be pulled forward after Phase 3 or 4 if a measured detector or throughput failure blocks the next core phase. Otherwise it stays deferred.

## 0. Project sketch — complete

Deliver the product brief, interface sketch, architecture, equipment plan, roadmap, and glossary in a standalone Git repository.

Completion evidence: documentation links resolve, diagrams are present, and the sketch was published in the standalone repository. Documentation now reflects the initial runnable media foundation.

## 1. Confirm the implementation baseline

Progress: hardware and C++ tools inspected; FFmpeg acquisition is pinned and validated. YOLOX-Nano and ONNX Runtime are pinned. A reference-image smoke test exists; representative evaluation footage and later dependencies remain open.

Inspect hardware and compiler availability. Choose dependency versions and acquisition strategy. Select an appropriately licensed detection model and permissioned samples. Specify exact initial formats after checking decoder support.

Completion evidence: reproducible environment specification, model metadata, and sample manifest with manually labelled expected detections/events. Choose measurable accuracy and performance targets after the baseline measurements, not before.

## 2. Media foundation

Progress: local image/video decoding, timestamped owned RGB frames, CLI exports, Qt desktop playback, resumable Stop/Play, asynchronous cancellation, bounded handoff, and synthetic checks are implemented. Settings and counting-line edits now refresh at the current sequence/timestamp without seeking or re-decoding the source. Seeking, representative-media checks, and memory-growth measurements remain to be done. Seeking is developed further with event review.

Implement image loading and video decoding/playback with timestamped frames, source metadata, cancellation, and explicit ownership.

Completion evidence: representative images and recordings display correctly; timestamps survive variable-frame-rate input; invalid files produce useful errors; opening/closing and cancellation release resources. Track a repeated-open memory baseline.

## 3. Object detection

Progress: YOLOX-Nano CPU inference, documented preprocessing/output contracts, original-frame overlays, confidence filtering, ordered video analysis, and detection CSV exports are implemented. Contract, real-model, and reference-image checks pass. A warm CPU timing baseline is recorded; representative accuracy and sustained resource measurements remain open. See [DETECTION.md](DETECTION.md).

Add preprocessing and CPU inference for one model. Render boxes in original-frame coordinates. Support image detection export and ordered offline video detections.

Completion evidence: results align with the correct frame and coordinates; preprocessing agrees with the model specification; inference timing and peak memory are recorded on the target machine. No temporal events are generated for images.

## 4. Tracking and crossing events

Progress: native class-gated greedy motion association, confirmed IDs, expiry, finite-line crossings, direction filtering, deadband/re-arming, short-gap handling, trails, desktop line drawing/counters, and CLI track/event CSV are implemented. Synthetic rules and reference-model integration checks pass. Representative labelled footage, event accuracy, and identity-switch measurements remain open. See [TRACKING.md](TRACKING.md); this is not completion of the accuracy acceptance criteria below.

Add an explicit initial association strategy, track expiry, one finite counting line, direction filtering, hysteresis, and event re-arming. A basic tracker is a baseline, not an accuracy guarantee.

Completion evidence: compare output with manually labelled clips for single crossings, reverse direction, jitter, repeat crossings, obstruction, and nearby objects. Report missed events, false/duplicate events, and identity changes. Adjust or replace tracking based on those results.

## 5. Review and persistence

Persist run configuration and events. Add event thumbnails, timeline markers, review seeking, CSV export, and reopening saved results.

Progress: one SQLite file per frozen whole-file run, committed event/progress transactions, bounded thumbnail pages, page timeline markers, native seeking with source-sequence fallback, silent review playback without inference, reopening without a model, and CSV export are implemented. Cancellation/failure retain clearly labelled partial results. Contract and real-model/desktop integration checks cover these paths; see [saved runs](SAVED_RUNS.md). Representative people/vehicle recordings, event accuracy, native file dialogs, and sustained resource behaviour remain to be evaluated before calling this product workflow reliable.

Completion evidence: a user completes the full recorded-video workflow; replay seeking does not modify analysis; event writes are idempotent; missing source files and failed exports produce useful errors. Verify CSV quoting and timestamp consistency.

## 6. First live input

Add one webcam adapter, bounded live queues, drop metrics, gap-aware tracking, disconnection handling, and clean stop/restart. Live event replay remains unavailable unless a recording feature is explicitly added.

Progress: Windows DirectShow capture, device/default-format selection, independent capture and analysis, capacity-one frame/result slots, application skip/latency counters, timeout/error reporting, and stop/restart are implemented. Synthetic overload/lifecycle checks exercise ordering, replacement, bounded observed latency, and source release. Hardware soak/disconnect tests and labelled accuracy remain open. See [live camera](LIVE_CAMERA.md). Recorded-file acceptance work continues alongside this baseline; saved review now uses a finer precise timer and skips overdue presentation frames after UI stalls.

Completion evidence: latency and queue capacity stay bounded under deliberately slow inference; dropped frames are reported; cancellation unblocks workers; run a documented sustained-input test and check memory growth and event reliability.

## 7. Optimize and package

Progress: per-frame decode/RGB, preprocessing, inference, postprocessing, tracking
and pipeline profiling, reproducible hardware/settings/hash summaries, a frame-copy
audit and a private Windows package builder are implemented. The Qt desktop layout
now has a video-first workspace and shared styling. Local package verification covers
hashes and file-based CLI/GUI with SDK PATH removed; clean-machine validation,
public-distribution readiness and representative sustained benchmarks remain open.
See [performance](PERFORMANCE.md), [packaging](PACKAGING.md), and [design](DESIGN.md).

Profile stage timings and copies. If measurements trigger the Phase 8 acceleration gate, evaluate a GPU backend against the CPU baseline. Package the first Windows release with documented dependencies and artifact notices.

Completion evidence: results and timing measurements state hardware, model, input resolution, settings, and backend. Verify installation on a machine without the development setup.

## 8. Conditional compute and model expansion

This phase covers four independent gates: local GPU inference, Python-based model training, an optional Python inference worker, and a commercial cloud service. Detailed triggers, stop conditions, and the bwUniCluster execution plan are in [Compute, training, and bwUniCluster](COMPUTE_AND_TRAINING.md).

No Phase 8 branch is selected now. **Custom training on bwUniCluster** becomes a plausible first branch only if labelled evaluation shows that YOLOX-Nano errors materially limit tracking or crossing accuracy. KIT documents a shared Slurm system with modern A100/H100 accelerators, which is ample for a compact detector. Shared hardware does not mean guaranteed or immediate GPU access; account entitlement, queue access, fair-share priority, and dataset permission must be verified first.

Local GPU inference is considered separately and only after end-to-end profiling. A Python training environment may produce an ONNX artifact while the shipped application remains C++. A Python inference worker is reserved for valuable models that cannot fit the native adapter. Commercial cloud serving remains last because bwUniCluster can cover scheduled training, while the current product does not require a remote always-on API.

Completion evidence for any adopted branch: compare it with the unchanged CPU/model baseline on held-out inputs; record accuracy, end-to-end latency, throughput, resource use, reproducibility, operational burden, and failure behavior. Reject or remove the branch if the benefit does not justify the added system.

## Measurement vocabulary

Report processing FPS separately from preview FPS. Measure processing latency by stage; for live mode also measure arrival-to-result latency (not true sensor-to-result latency unless capture timing is available). Report queue high-water marks, drops, peak memory, run failures, and event accuracy. Preserve the test inputs and settings so comparisons are repeatable.

## 9. Future AI direction

The agreed sequence is native product first, optional AI perception later, and a possible agent-driven service at the end. These are deferred directions, not required implementation milestones or commitments to a provider.

### A. Prove the native product

Complete and evaluate the recorded-file workflow, followed by live input and packaging. Pretrained object detection remains in the baseline. Establish event accuracy, responsiveness, resource use, and usefulness on representative footage before adding agent orchestration.

### B. Evaluate embedded AI perception

Investigate prompt-driven detection/segmentation and optional reasoning on ambiguous visual cases. Candidate models discussed include the SAM family; no model, runtime, framework, or hardware purchase is selected. A separate local AI worker is one possible integration, not a current dependency.

Compare the extension with the native baseline on the same inputs. Measure whether it expands useful object selection or improves accuracy, together with latency, memory, integration effort, hardware requirements, and artifact licensing. Keep it optional if it does not justify those costs. Preserve a stable result contract so the application does not depend on a specific model or agent framework.

### C. Consider an agent-driven service

Only after the product is established, explore autonomous investigations: selecting recordings, running analyses, reviewing evidence, and assembling timestamped reports. Service operation, deployment, provider choice, data access, permissions, and cost would need a separate design. A service need not imply sending all footage to a cloud provider.

Neither future direction changes the first-release scope or adds agent integration to the current implementation work. A Python worker from Phase 8 is an execution adapter; it does not by itself make the product agent-driven.

## Deferred projects

Preview Fit/100% zoom and rendering-quality refinements are deferred while CPU analysis is the focus.

Robotics navigation is shelved as a separate future project. Multi-camera processing, network input, recording/retention, and region rules require their own scope decisions. Custom model training now has a conditional Phase 8 gate rather than being an assumed deliverable.
