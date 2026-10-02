# Roadmap and acceptance evidence

These milestones are ordered by dependencies, not estimated calendar dates. No executable implementation has started.

## 0. Project sketch — current milestone

Deliver the product brief, interface sketch, architecture, equipment plan, roadmap, and glossary in a standalone Git repository.

Completion evidence: documentation links resolve, diagrams are present, repository content accurately says that there is no runnable application. Remote publication is tracked separately in the status document.

## 1. Confirm the implementation baseline

Inspect hardware and compiler availability. Choose dependency versions and acquisition strategy. Select an appropriately licensed detection model and permissioned samples. Specify exact initial formats after checking decoder support.

Completion evidence: reproducible environment specification, model metadata, and sample manifest with manually labelled expected detections/events. Choose measurable accuracy and performance targets after the baseline measurements, not before.

## 2. Media foundation

Implement image loading and video decoding/playback with timestamped frames, source metadata, cancellation, and explicit ownership.

Completion evidence: representative images and recordings display correctly; timestamps survive variable-frame-rate input; invalid files produce useful errors; opening/closing and cancellation release resources. Track a repeated-open memory baseline.

## 3. Object detection

Add preprocessing and CPU inference for one model. Render boxes in original-frame coordinates. Support image detection export and ordered offline video detections.

Completion evidence: results align with the correct frame and coordinates; preprocessing agrees with the model specification; inference timing and peak memory are recorded on the target machine. No temporal events are generated for images.

## 4. Tracking and crossing events

Add an explicit initial association strategy, track expiry, one finite counting line, direction filtering, hysteresis, and event re-arming. A basic tracker is a baseline, not an accuracy guarantee.

Completion evidence: compare output with manually labelled clips for single crossings, reverse direction, jitter, repeat crossings, obstruction, and nearby objects. Report missed events, false/duplicate events, and identity changes. Adjust or replace tracking based on those results.

## 5. Review and persistence

Persist run configuration and events. Add event thumbnails, timeline markers, review seeking, CSV export, and reopening saved results.

Completion evidence: a user completes the full recorded-video workflow; replay seeking does not modify analysis; event writes are idempotent; missing source files and failed exports produce useful errors. Verify CSV quoting and timestamp consistency.

## 6. First live input

Add one webcam adapter, bounded live queues, drop metrics, gap-aware tracking, disconnection handling, and clean stop/restart. Live event replay remains unavailable unless a recording feature is explicitly added.

Completion evidence: latency and queue capacity stay bounded under deliberately slow inference; dropped frames are reported; cancellation unblocks workers; run a documented sustained-input test and check memory growth and event reliability.

## 7. Optimize and package

Profile stage timings and copies. Try hardware acceleration if supported and justified. Package the first Windows release with documented dependencies and artifact notices.

Completion evidence: results and timing measurements state hardware, model, input resolution, settings, and backend. Verify installation on a machine without the development setup.

## Measurement vocabulary

Report processing FPS separately from preview FPS. Measure processing latency by stage; for live mode also measure arrival-to-result latency (not true sensor-to-result latency unless capture timing is available). Report queue high-water marks, drops, peak memory, run failures, and event accuracy. Preserve the test inputs and settings so comparisons are repeatable.

## Future AI direction

The agreed sequence is native product first, optional AI perception later, and a possible agent-driven service at the end. These are deferred directions, not required implementation milestones or commitments to a provider.

### A. Prove the native product

Complete and evaluate the recorded-file workflow, followed by live input and packaging. Pretrained object detection remains in the baseline. Establish event accuracy, responsiveness, resource use, and usefulness on representative footage before adding agent orchestration.

### B. Evaluate embedded AI perception

Investigate prompt-driven detection/segmentation and optional reasoning on ambiguous visual cases. Candidate models discussed include the SAM family; no model, runtime, framework, or hardware purchase is selected. A separate local AI worker is one possible integration, not a current dependency.

Compare the extension with the native baseline on the same inputs. Measure whether it expands useful object selection or improves accuracy, together with latency, memory, integration effort, hardware requirements, and artifact licensing. Keep it optional if it does not justify those costs. Preserve a stable result contract so the application does not depend on a specific model or agent framework.

### C. Consider an agent-driven service

Only after the product is established, explore autonomous investigations: selecting recordings, running analyses, reviewing evidence, and assembling timestamped reports. Service operation, deployment, provider choice, data access, permissions, and cost would need a separate design. A service need not imply sending all footage to a cloud provider.

Neither future direction changes the first-release scope or authorizes application implementation in this documentation step.

## Deferred projects

Robotics navigation is shelved as a separate future project. Multi-camera processing, network input, recording/retention, region rules, and custom model training are extensions requiring their own scope decisions.
