# FrameTrail: complete project understanding and current-status handoff

Prepared 24 October 2026, Europe/Berlin, for an AI model taking over the project. This document combines the product purpose, implemented software, research history, current evidence, user decisions, operational constraints and exact next work. It is intentionally detailed enough to be useful when the earlier chat is unavailable.

The source and evidence baseline for this handoff is private repository **MogProgJ/FrameTrail**, branch **main**, commit **6077472fb3ad1f4bfbe174578daa286d71bdb682**. That is the verified GitHub sync immediately before this document was written. The handoff itself will appear in a later commit. Use the live `main` ref for subsequent publication metadata; distinguish that from the frozen scientific artifacts described here.

This is a continuation brief, not a new experiment approval, a dataset release or a claim that the product is finished. The scientific work described here was last advanced on 22 October. On 24 October, the latest source was consolidated into the main repository, the findings were published, and the app and archive were checked. Preparing this handoff introduces no new model result.

## 1. The essential current picture

FrameTrail is a working native Windows application for analysing local images and video. It detects objects, associates detections over time, records timestamped appearances and line-crossing events, and lets the user inspect and export the evidence. The app uses C++20, Qt Widgets, FFmpeg, ONNX Runtime and SQLite. Offline Python tooling supports datasets, annotation, model experiments and export. There is no Python inference service, cloud account or LLM dependency in the desktop runtime.

The broad product ambition is useful everyday-object recognition. People and vehicles in fixed-camera recordings were the original engineering baseline. Fox/dog confusion, dark imagery, small objects, billboards and washing machines have exposed recognition limitations. Those difficult cases guide evaluation; they do not reduce the whole project to a billboard detector or a wildlife application.

The desktop currently has one window containing **Preview, Analysis, Smooth Playback, Camera and Quick Guide**. YOLOX-S remains the normal default when installed. A broader Open Images profile and experimental alternatives are available explicitly. An RF-DETR candidate from job 7805570, selected step 100, is an explicit preview with a small measured washing-machine improvement. It is held from production adoption because numerical export qualification remains incomplete.

The immediate research priority is **correct data under an agreed billboard definition**. A four-condition detector experiment failed its frozen acceptance rules. Three subsequent bounded TRAIN-only diagnostic studies also failed their clean held-fold improvement criteria. A review then exposed a task-definition mismatch: restaurant/business identity boards had sometimes been treated as negative while promotional boards counted as positive. The user explicitly confirmed that both types should count.

The broader definition is now recorded, and a first visual pass over 323 original photos is complete. The revised annotations remain a draft. They are not approved for training. The corrected fresh draft lacks **11 TRAIN, 6 validation and 4 TEST truly absent photos**. A local inventory contains **223 unused candidates** with fixed prospective roles. Reviewing and qualifying that existing inventory is the best next work. No new training job, model adaptation or baseline inference is needed to begin it.

Current invariants:

| Item | Verified state |
| --- | --- |
| Default desktop model | YOLOX-S when installed |
| Explicit RF preview | Job 7805570, selected step 100 |
| RF export numerical gate | Still held |
| Production adoption | `false` |
| Latest four-condition detector experiment | Complete; `winner=null` |
| Three later TRAIN-only CPU studies | Complete; 24 fits / 3,840 diagnostic updates total |
| Deployable architecture chosen by those probes | None |
| Broader billboard annotation release | First-pass draft; not qualified for training |
| Fresh TEST model predictions in this research cycle | Zero |
| Background process, cluster follow-up or automation left by this handoff | None |
| Source and findings on GitHub | Published and verified; local main was clean at the baseline commit |

Sources: [current project progress](PROJECT_PROGRESS.md), [current handoff](CURRENT_HANDOFF.md), [expanded-definition report](research/continuation-20261018/outputs/broad-billboard-definition-20261022-v1/REVISION_REPORT.md), [GitHub publication receipt](research/sync-20261024/PUSH_RECEIPT.json).

## 2. What the user wants from the project

The practical problem is that reviewing long recordings by hand is slow. FrameTrail should turn footage into reviewable observations: what appeared, when it appeared, where it was detected, and whether a configured event occurred. The user should be able to return to the source evidence instead of trusting a summary without timestamps.

The original fixed-camera use case was counting people or vehicles crossing a user-defined line. The product has since grown into a broader local analysis workflow. The accepted recorded-file workflow is:

1. Choose or drop a recording.
2. Start analysis, with optional model, confidence and processing-device settings.
3. Review object appearances, first/last timestamps and thumbnails.
4. Open an appearance in the source footage.
5. Optionally save the analysis locally or export CSV.

This workflow should stay straightforward. Saving is a deliberate action after reviewing temporary results. The user should not need to create a database or configure a counting line simply to obtain an appearance list.

The main Preview section separately supports detections, playback, tracking and direction-aware counting across a drawn line. Still images support boxes and confidence scores. A one-frame image supplies no temporal evidence for tracking or crossings.

The software recognises configured categories and applies explicit temporal rules. It does not establish the real identity of a person or object, understand every activity, or guarantee that all visible objects will be recognised. A tracker appearance ID is an approximate association within a run, not a verified real-world identity or a globally unique physical-object count.

The user has also wanted broad everyday-object coverage. Six planning domains are people/transport, home/furniture, kitchen/food, electronics/work, personal/outdoor objects and animals/hard cases. Wider label availability is useful, but the project deliberately separates vocabulary coverage from measured accuracy. The current billboard work is a mechanism test within that wider recognition effort. Washing-machine recall remains an unresolved product target too.

Cloud serving, an agent-driven investigation service, arbitrary prompt-driven runtime detection, segmentation, multi-camera operation and robotics navigation are future or separately scoped directions. They are not prerequisites for the current data-review task. The current application is local and native.

Sources: [project brief](docs/PROJECT_BRIEF.md), [training scope](training/scope.json), [training overview](docs/TRAINING.md), [recognition evidence](docs/RECOGNITION.md).

## 3. Where the project actually lives

### 3.1 Repository and local directories

| Purpose | Location |
| --- | --- |
| Private repository | `https://github.com/MogProgJ/FrameTrail` |
| Main branch | `main` |
| Current source checkout | `C:/Users/nazee/Documents/All Modules/FrameTrail` |
| Canonical local research continuation | `C:/Users/nazee/Documents/Codex/2026-10-18/frametrail-continuation` |
| Current local launcher | `C:/Users/nazee/Documents/Codex/2026-10-18/frametrail-continuation/Run-FrameTrail.cmd` |
| Canonical research output root | `C:/Users/nazee/Documents/Codex/2026-10-18/frametrail-continuation/outputs` |
| GitHub copy of that continuation | `research/continuation-20261018/` in the repository |
| GitHub copy of earlier app output text | `research/local-output/` |
| GitHub publication procedure and checks | `research/sync-20261024/` |
| Pinned local Python | `C:/Users/nazee/Documents/All Modules/FrameTrail/.deps/rfdetr-probe-cpu/Scripts/python.exe` |

The pinned Python reported **3.12.14** during this handoff review. Use `-u -B -X utf8` for these local research scripts where appropriate. Existing environments are intentional and should not be upgraded as a routine restart step.

The saved chat/project mapping can point at **MiniERP**, which is unrelated. Work in the explicit FrameTrail directories above. Do not edit MiniERP to continue FrameTrail. Some older handoffs mention an auxiliary FrameTrail checkout under MiniERP; that historical reference is not an instruction to resume there.

The latest packaged application remains in the canonical continuation output. Publishing the source did not replace its launcher or silently swap model weights. The main Git checkout now contains the latest source needed to build the single-window app and Quick Guide.

### 3.2 What happened during the GitHub sync

The main checkout was behind the versioned continuation source. We preserved its uncommitted source/tooling/docs as commit `e73759ea85a3a46343dc957d89a93d53fb7fcddf`, then consolidated the latest previously verified desktop source from `outputs/native-lean-guide-20261019-v1/source` into the main build tree. All 106 snapshot source files copied/compared were verified; 41 files differed from or were new to the earlier checkout.

Commit `e1523333e03ea2282f57436f9021000550c77a71` contains the consolidated source and research archive. Commit `6077472fb3ad1f4bfbe174578daa286d71bdb682` records the verified publication and continuation handoff. Git remote, GitHub API and local head agreed on that latter commit. The working tree was clean.

**27,994 original source/evidence files**, totalling **885,258,419 bytes before Git compression**, were archived. Every archived source file's SHA-256 was checked against the original, including a check reading the committed Git blobs. The archive includes old source snapshots, code, plans, user authorization receipts, unsuccessful attempts, metrics, reports, annotation drafts, provenance records and handoffs.

Raw photos and video, model/checkpoint weights, feature/cache binaries, SDKs, build products, package ZIPs, and authentication/runtime artifacts remain local. The inventory enumerates 11,754 exclusions from the scanned project artifact roots; this count is not an exhaustive inventory of every SDK file in `.deps`. Available scientific artifact hashes and package/model export receipts are included. GitHub is a source/evidence archive, not a full binary backup or an admitted dataset/model release.

The source manifest covers copied original records. Contemporary publication metadata under `research/sync-20261024/`, and this handoff, are separate newly authored records. Git attributes disable newline conversion inside `research/` so the original source-byte hashes remain meaningful. Historical absolute paths describe the original environment and will need an explicit mapping on another machine.

Sources: [source consolidation receipt](docs/SOURCE_CONSOLIDATION_20261024.json), [archive guide](research/README.md), [source manifest](research/SOURCE_MANIFEST.json), [local artifact inventory](research/LOCAL_ARTIFACT_INVENTORY.json), [publication validation](research/sync-20261024/VALIDATION_RECEIPT.json), [committed-blob audit](research/sync-20261024/git-blob-verification.json).

## 4. Which records to trust when they disagree

Read the latest user clarification, `AGENTS.md`, the top of `CURRENT_HANDOFF.md`, the latest task definition and the latest versioned completion/audit records together. A filename such as `FINAL_RECEIPT.json` means final for that particular stage, not necessarily current for the entire project.

Important examples of historical text that is now superseded:

- The original brief describes webcam and GPU support as later work. Both have since been implemented, with limits.
- Older architecture paragraphs describe saved-run schema 3. Current `src/run_store.cpp` writes schema 4 and reads schemas 1–4.
- The original balanced-continuation proposal receipt says it awaits submission. Job 7805570 later ran, its selected checkpoint was evaluated, and an explicit native preview was implemented.
- The four-trial postrun report proposes a discrimination study. That study and two distinct follow-up studies have all completed.
- The photo-level loss report asks for a human product-boundary decision. The user has answered it: business/restaurant identity boards and promotional boards both count.
- Some strategy reports mention a KIT outage. That was a stage-specific condition; later work completed. Do not infer current cluster availability from that old text. No cluster access is needed for the immediate local review task.
- The 19 October strategy folder's `CURRENT_READINESS.json` reports zero eligible fresh records at that planning stage. The later narrow release and broader v4 draft supersede those counts. Recompute readiness for an actual new release instead of treating the old filename as a live project-wide counter.
- Old assistant-written approval flags such as `automatic_export=false` do not override the user's later autonomy clarification. Scientific qualification gates remain binding.

Preserve old receipts. Record a superseding decision or versioned overlay instead of editing history to look cleaner. A new annotation interpretation does not make an old failed experiment successful retroactively.

## 5. The implemented desktop application

### 5.1 One window, five sections

**Preview** opens images or recordings, shows detections and optional tracks/counting lines, and supplies the familiar playback controls. Stop preserves position for Play; Replay explicitly restarts. Editing settings preserves the decoder position and refreshes held/buffered frames under a new analysis revision. Earlier work addressed unwanted jumps and analysis resets.

**Analysis** runs whole-recording appearance analysis in the shared window. It can continue while the user visits another section. The shared activity indicator reports background work. Temporary results can be reviewed, saved, exported to CSV and reopened. Closing or replacing unsaved work uses Save/Discard/Cancel. Cancellation can preserve partial results with an explicit state.

**Smooth Playback** prepares an analysed cache before replay. Source selection and preparation are explicit. Prepared overlays persist across navigation; hidden playback pauses. Replacing the source releases the old cache so old overlays cannot appear on a new recording. Closing during preparation stops workers and does not promote an incomplete cache. Smooth replay after preparation is not real-time model inference.

**Camera** embeds the existing live controls. Navigating to it does not acquire hardware. Leaving requests capture to stop. Camera lifecycle/navigation was checked without activating a real camera in the latest workflow tests; actual driver/hardware behaviour still needs its own verification.

**Quick Guide** is an embedded searchable help section, opened with Ctrl+K or F1. It explains eight common tasks, navigates to existing sections and looks up category support in installed model profiles. A search such as “billboard” can select the broader model; common COCO objects prefer YOLOX-S. This is local catalogue/help logic, with no LLM, network, web component or new inference dependency. It states that category support does not guarantee correct detections.

The app keeps one main workspace rather than opening a new top-level analysis/playback window for each task. Existing file dialogs and unsaved-result dialogs remain normal dialogs. Navigation reuses sections and retains state.

### 5.2 Latest packaging and responsiveness work

The lean package separated optional models from the core distribution. The core keeps YOLOX-Nano, YOLOX-S, YOLO-World S and the broader Open Images model. World-M and the two RF previews live in sibling `optional/models/`. Existing local model paths take precedence; missing optional choices are disabled.

The four core profiles retain a combined catalogue union of 615 canonical labels. This is a union across model choices, not 615 reliable categories from the default detector. Six labels requiring World-S beyond the YOLOX/Open Images union are wolf, firefly, traffic cone, stroller, forklift and shopping cart.

Recorded package sizes:

| Measurement | Bytes |
| --- | ---: |
| Previous application folder | 731,418,828 |
| Lean core application folder | 386,138,634 |
| Separate optional models | 344,952,714 |
| Lean core ZIP | 227,065,172 |

The core reduction was 47.21%. Keeping core plus optional models retains approximately the previous overall size. This is a distribution-size result, not an inference-speed, working-memory or whole-workspace disk-saving result. Runtime codec/GPU libraries were retained where required. The test-only Qt Test DLL was removed from the distributable, not from development tests.

The main Preview idle poll interval changed from 10 ms to 100 ms while fast polling remains during relevant activity. The guide test observed nine idle main-timer events in one second. That is a measured reduction in scheduled polling, not a measured percentage CPU saving.

Sources: [lean-core and guide report](research/continuation-20261018/outputs/native-lean-guide-20261019-v1/REPORT.md), [unified-workspace report](research/continuation-20261018/outputs/native-unified-20261019-v1/REPORT.md), [current desktop source](apps/desktop/preview_window.cpp), [model selector](apps/desktop/model_selection.hpp).

## 6. Architecture and code map

The central path is:

```text
Local file / image / Windows webcam
    -> FFmpeg decode/capture
    -> owned RGB frame + source sequence/timestamp
    -> profile-specific preprocessing
    -> native ONNX Runtime inference
    -> original-frame detections
    -> optional temporal association / line rules
    -> timestamped appearances or crossing events
    -> SQLite evidence / CSV / source review
```

Qt owns presentation and user interaction. The media, inference, tracking and storage work is separated into reusable C++ modules. Native C resources are wrapped with C++ RAII so handles, buffers, sessions and threads have clear lifetimes. OpenCV is not required by the current native adapters.

| Area | Main files | Responsibility |
| --- | --- | --- |
| Build and profiles | `CMakeLists.txt`, `CMakePresets.json`, `dependencies/` | Native targets, tests and pinned external artifact contracts |
| CLI | `apps/cli/main.cpp` | Media inspection, optional analysis and CSV/saved-run commands |
| Main workspace | `apps/desktop/preview_window.*`, `preview_layout.ui`, `workspace_chrome.*` | Navigation, Preview, shared activity and coordinated shutdown |
| Styling/controls | `apps/desktop/theme.hpp`, `studio_controls.hpp`, `studio_assets.qrc` | Shared native UI presentation |
| Analysis UI | `apps/desktop/saved_run_window.*` | Intake, analysis progress, appearances, save/CSV/reopen |
| Playback UI | `apps/desktop/playback_workspace.*`, `cached_playback_window.*` | Explicit preparation and retained analysed playback |
| Camera UI | `apps/desktop/live_window.*` | Live source controls and lifecycle |
| Guide | `apps/desktop/guide_workspace.*` | Local task search and model-category lookup |
| Frame/media | `include/frametrail/frame.hpp`, `media_reader.hpp`, `src/media_reader.cpp` | Owned RGB pixels, strides, timestamps and decoding |
| Preview lifecycle | `include/frametrail/preview_session.hpp` and implementation | Bounded worker handoff, generation/revision identities, reconfiguration |
| Detector | `include/frametrail/detector.hpp`, `src/detector.cpp` | Profile contracts, session ownership, shared detection result |
| GPU adapter | `src/dml_inference.*` | Isolated DirectML runtime, execution metadata and fallback |
| RF adapter | `src/rfdetr.cpp` | Exact RF resize/normalization and packed-output decoding |
| Tracking | `tracker.hpp`, `frame_tracker.hpp`, `src/assignment.*` | Association, continuity guards and event rules |
| Ordered analysis | `analysis_job.hpp`, `src/analysis_job.cpp` | Whole-file processing, cancellation, progress and storage writes |
| Live processing | `live_session.hpp` and implementation | Capture/analysis slots, replacement counters and shutdown |
| Playback cache | `playback_cache.hpp`, `src/playback_cache.cpp` | Prepared frame/overlay playback and incomplete-cache lifecycle |
| Persistence | `run_store.hpp`, `src/run_store.cpp` | Run configuration, appearances/events, compatibility, read-only review |
| Tests | `tests/` | Native contracts, workflow checks, dataset/annotation/research-tool checks |
| Offline tooling | `scripts/`, `training/`, research output scripts | Acquisition, review, training, export and reproducible experiments |

### 6.1 Frame identity, timing and concurrency

A frame contains owned RGB pixel data, width/height/stride, sequence and an optional source-relative timestamp. A source generation distinguishes different opened sources; an analysis revision distinguishes settings changes. Results must match generation, revision and frame identity before being displayed. An old worker result must not overwrite a newer revision.

For variable-frame-rate media, source timestamps come from decoded presentation timing, not frame index divided by an assumed FPS. Processing duration is a different clock from the time a frame belongs in the recording. Live application-arrival timing is not automatically sensor-to-display latency.

The offline analysis worker preserves order for detection, tracking, event evaluation and persistence. Bounded queues apply backpressure. The current file Preview uses a two-frame queue. The analysis preview is a replaceable recent snapshot rather than a growing log of UI frames.

Live capture and analysis use capacity-one latest-frame/latest-result slots. Replacements are counted so latency can be bounded without pretending all frames were analysed. Dropped live frames can reduce tracking and event evidence. Driver buffers and in-flight inference exist in addition to the explicit application slots.

Cancellation must wake blocked queues and stop/join workers before their buffers and native handles are destroyed. Source review is decode-only and cannot become another analysis writer. Leaving a section and cancelling a job are different actions.

### 6.2 Tracking and storage semantics

The tracker associates detections; IDs can split or switch. The default association remains greedy. A bounded experimental global/Hungarian repair did not pass its default-adoption gate on the reviewed crowd example, so it remains experimental. A scene-boundary/gap guard breaks inappropriate continuity while retaining run-level count/ID semantics.

The original line rule uses an original-frame-normalized finite segment, direction filtering, deadband, re-arming and temporal confirmation. An apparent side change outside the finite segment is insufficient. Track loss can still create missed or duplicate real-world counts despite storage-level event deduplication.

Current saved runs use SQLite **schema 4**, with readers supporting versions 1–4. Newer profiles freeze the vocabulary/model configuration. Old evidence must not be silently relabelled, recomputed or migrated into a new interpretation. Review/export uses read-only access; the analysis worker owns writing. Source media is referenced, not copied into the database. Thumbnails are small evidence previews, not retained source video. Missing/changed source files must be explained to the user.

Completed, cancelled, failed and unfinished states are distinct. Temporary analysis results precede optional atomic save/export. Event idempotence prevents duplicate database writes; it does not prove object identity or event correctness.

Sources: [architecture](docs/ARCHITECTURE.md), [saved runs](docs/SAVED_RUNS.md), [tracking](docs/TRACKING.md), [tracking evaluation](docs/TRACKING_EVALUATION.md), [live camera](docs/LIVE_CAMERA.md), [current schema implementation](src/run_store.cpp).

## 7. Model choices and their actual meaning

| Profile | Catalogue/contract | Current role |
| --- | --- | --- |
| YOLOX-Nano | 80 COCO categories; 416 input | Faster CPU baseline and development/test model |
| YOLOX-S | 80 COCO categories; 640 input | Normal app default when installed; good selected people/vehicle recovery |
| YOLO-World S | Fixed reviewed 100-label vocabulary; 640 input | Experimental broad alternative; retained in lean core for union coverage |
| YOLO-World M | Same reviewed 100-label vocabulary; more compute | Optional experimental alternative |
| Broad recognition | 601 raw Open Images labels mapped to 597 canonical categories; 640 input | Wider labels including fox and household objects |
| RF legacy profile | Explicit `rfdetr-7758628` native contract | Optional experimental trained model; broad output support does not establish accuracy |
| RF balanced preview | Explicit `rfdetr-7805570`; selected step 100 | Optional preview retaining measured washing-machine gain; numerical hold persists |

Canonical application IDs span 0–614. COCO IDs 0–79 retain their meaning; World additions extend through 99; further Open Images mappings extend through 614. Human aliases such as Man/Woman/Boy/Girl/Person map to person in the broad profile. **Billboard is class 133; washing machine is class 593.** Keep exact label order and profile metadata. Shape compatibility alone does not establish model compatibility.

YOLOX uses its BGR/grid/objectness contract. The broader YOLO exports use RGB normalized by 255, a centred letterbox and decoded `[1,4+classes,8400]` output without a separate objectness channel. The RF native contract uses full-image resize to 512, ImageNet RGB normalization and 300 query rows. Its packed output has 619 attributes: four normalized box coordinates plus 615 canonical foreground logits. RF decoding applies sigmoid, a top-300 query/class-pair limit, class-aware NMS and a maximum of 100 detections. Its image transform must not be replaced with a YOLO letterbox under the same profile name.

Current scientific operating values are confidence **0.35**, NMS IoU **0.45**, matching IoU **0.5**, top pairs **300**, max detections **100**. An image-space matching metric is separate from inference suppression. The later binary probes have different scores and thresholds; their 0.5 or approximately 0.03 cutoffs are not app settings.

CPU remains the default processing backend. Optional DirectML runs inside the native detector boundary, with a separate isolated runtime. Automatic mode can fall back to CPU and records actual provider/runtime/device/fallback metadata. Strict `directml` is distinct from the user-facing automatic fallback choice. No cloud processing is implied by selecting GPU.

### 7.1 Earlier broad-recognition evidence

The small fixed comparison used partial selected targets:

| Model | Public references, /21 selected targets | Real fox targets /4 | Earlier recording /24 selected targets | Supplied generated-clip snapshots /12 targets |
| --- | ---: | ---: | ---: | ---: |
| YOLOX-S | 6 | 0; class unavailable | 24 | 3 |
| YOLO-World S | 10 | 0 | 22 | 4 |
| YOLO-World M | 8 | 0 | 20 | 5 |
| Broad recognition | 16 | 3 | 18 | 3 |

The dark generated fox remained missed at confidence 0.35. Wider vocabulary improved some selected targets and regressed others, which is why broader recognition did not replace YOLOX-S automatically. These references are small, purposive and partly publisher-derived. They do not establish complete precision, full-vocabulary AP or general deployment performance.

Short warm-pipeline measurements on the recorded laptop/GTX 1650 Ti setup were YOLOX-S 7.58 CPU / 27.58 GPU FPS, World-S 5.03 / 16.31, World-M 2.21 / 10.84 and broad recognition 4.59 / 15.50. They excluded five warmup frames from a 60-frame measurement and do not establish sustained throughput. Sampled process RAM is not VRAM. Smooth playback after preparation is a different measurement again.

Sources: [recognition evidence](docs/RECOGNITION.md), [detector interface/contracts](include/frametrail/detector.hpp), [vocabulary registry](dependencies/recognition-vocabulary.json), [RF decoder](src/rfdetr.cpp).

## 8. Research history and why the current model stayed unchanged

### 8.1 Early dataset/training mechanics

The early general-recognition tooling indexed Open Images metadata and prepared a 96-image mechanical sample with 447 boxes and 132 canonical categories. That sample came from publisher validation data with incomplete labels. Its bounded smoke training demonstrated mechanics; it was not a legitimate production training release or an independent field-accuracy test. Substantial training requires appropriate source-train/new data with real label/rights/split qualification.

Later photo acquisition and browser-based correction tooling added per-class annotation scopes, proposal review, provenance and immutable exports. Missing publisher labels were never supposed to become blanket background supervision. Earlier acquisition, annotation UI and RF probe work is already completed history; do not restart those setup stages merely because an old guide says “next”.

### 8.2 Job 7780632 and its TRAIN signal diagnosis

This was a completed 600-update constrained RF trial. Its selected best step remained zero. A subsequent CPU TRAIN-only diagnosis inspected 12 frozen training photos at steps zero and 600, with no optimizer updates. It found usable classification gradients for the new billboard/washing-machine rows, no disconnected sampled new-class signal and appropriate masking of unknown scopes. Frozen feature/box components contributed constant parts of the total loss; a modest total-loss change could not be interpreted as no classifier learning.

The diagnosis supported focused classifier optimization before assuming box or feature unfreezing was required. That led to the separate balanced continuation. The early completion receipt that still says results were not yet retrieved is a historical retrieval-stage snapshot, not the latest project state.

### 8.3 Job 7805570: the retained balanced candidate

The balanced continuation trained only the final billboard and washing-machine classifier rows while retaining the other rows, feature/transformer/box components and buffers. The selected checkpoint was **step 100**, with SHA-256:

```text
c1e7b571476a9bdc02533359dfe3f599afab98822aa90df265e9068f43f46bd3
```

It passed its then-frozen known-reference retention comparison against both pinned baselines. On 130 held-out photos, washing-machine known hits improved from 0/15 to 3/15; billboard stayed 0/19; cat stayed 23/23 and dog stayed 15/19. These new-class positive scopes were partial, so those ratios establish selected known-target recovery, not class precision. Primary known-positive hits across the declared photo/video references increased from 139 to 142.

The six reference views contained 202 unique image byte identities. CPU inference evaluated three fixed models for 606 records. The overlapping eight-photo internal regression view was not counted as independent extra evidence. Those held-out references are now consumed and must remain regression evidence rather than being called fresh again.

This candidate became the starting state for later billboard experiments and an explicit native preview. It did not become the normal app default or a fully qualified production model.

### 8.4 The separate numerical export hold

Across the 202 unique images, the ONNX export preserved decoded counts/classes and measured scoped scores. Nevertheless, three image confidence comparisons exceeded the original **0.002** tolerance. The maximum difference was **0.004229903**, or about 0.423 percentage points. Three of six raw-query-array probes also failed their numerical check.

The fixed diagnostic investigated export preparation, ONNX Runtime optimization/fusion changes, a regular export using cached input positional tables and a newer Dynamo/opset-18 export. Individual numerical changes did not produce a uniform qualifying fix. Alternate ONNX files remain diagnostics. No original tolerance, confidence threshold or gate was relaxed, and the pinned training environment was not upgraded to force success.

The native adapter itself passed its decoded parity probes and workflow checks. This is compatible with the stricter numerical export hold remaining open. Equal counts, selected metric agreement and native adapter correctness are different assertions from full numerical qualification.

Measured CPU inference median was roughly 612 ms/frame on six probes. An older smooth-cache test prepared 120 frames in 133.705 seconds. Smooth replay of the prepared sequence does not establish live inference at source frame rate.

Sources: [TRAIN signal diagnosis](research/continuation-20261018/outputs/training-signal-7780632-20261018-v1/REPORT.md), [7805570 held-out evaluation](research/continuation-20261018/outputs/heldout-evaluation-7805570-20261018-v1/REPORT.md), [native balanced preview](research/continuation-20261018/outputs/native-balanced-7805570-20261018-v1/REPORT.md), [export investigation](research/continuation-20261018/outputs/export-numerics-7805570-20261018-v1/REPORT.md).

### 8.5 Older billboard-only batches: 7809335 and 7818553

Array **7809335** tested four billboard final-row conditions: positive-to-negative exposure 1:1 or 1:3 crossed with learning rates 0.0001 or 0.0003. Each completed 1,500 updates. Final known billboard hits on the old development set were 7/11, 5/11, 9/11 and 7/11, with measured billboard FP 2, 1, 2 and 1 and unscored counts 577, 551, 587 and 569. None met the unchanged selection rules. Every selected `best.pt` retained the starting model state; different serialized hashes could reflect provenance rather than changed selected weights.

Array **7818553** allowed the main and encoder proposal billboard classifier rows. Maximum old-development hits were 5/11, 5/11, 6/11 and 7/11. Final complete FP were 1, 0, 1, 1 and unscored counts 550, 553, 590, 586. Selected step remained zero for all four tasks. Higher encoder learning rates improved TRAIN geometry coverage to 50/54 targets from 37/54, but no eligible validation state followed.

The original baseline had 525 aggregate unscored predictions and the continuation baseline had 528. Their separate +5 drift guards imply caps 530 and 533; satisfying both retains the stricter effective cap **530**. Unscored predictions are not measured false positives. The cap is a conservative drift guard, and it was not rewritten because a new experiment exceeded it.

Additional cached-feature CPU controls, teacher preservation and boundary-held positive comparisons were also explored and preserved. A conservative later control reached 6/11 hits with zero measured FP but 539 unscored predictions, still above 530. Those repeated development comparisons did not create independent generalization evidence. Scene review also exposed concentration: five Times Square photos supplied 28 of 54 old TRAIN billboard targets.

These failures motivated source-diverse fresh data and scene/identity controls. Their old next-step collection proposals have subsequently been executed/reviewed; they are not instructions to resubmit those collection jobs now.

Sources: [7809335 diagnosis](research/continuation-20261018/outputs/billboard-batch-diagnosis-7809335-20261018-v1/REPORT.md), [7818553 diagnosis](research/continuation-20261018/outputs/selector-diagnosis-7818553-20261018-v1/REPORT.md), [later strategy](research/continuation-20261018/outputs/training-strategy-20261019-v1/STRATEGY.md).

## 9. The completed fresh four-condition experiment: 7870268

### 9.1 Data, methods and bounds

The narrow-definition fresh release had 124 photos:

| Role | Positive photos | Whole-photo absent photos | Known billboard targets |
| --- | ---: | ---: | ---: |
| TRAIN | 30 | 30 | 38 |
| Validation | 12 | 20 | 14 |
| TEST | 12 | 20 | 16 |

That original release and its labels/results remain immutable. Its manifest is `outputs/data-review-7840599-20261021-v1/reviewed-release-v1/scoped-fresh-additions-v1.json`, SHA-256:

```text
b262af61db8141abadd61cc026454953f6c172bd2fff552334c456170b5feb09
```

The fresh starting checkpoint baseline recovered zero of 14 known validation billboard targets with zero billboard FP. The declared three-hit improvement was therefore mathematically possible. The four scientific conditions were:

| Condition | Sampling seed | Updated parameters | Execution |
| --- | ---: | --- | --- |
| M0 | 17 | Main billboard classifier row only | Local exact-layout cached CPU control |
| M0 | 29 | Main billboard classifier row only | Local exact-layout cached CPU control |
| M1 | 17 | Main and encoder proposal billboard rows | GPU array task 0 |
| M1 | 29 | Main and encoder proposal billboard rows | GPU array task 1 |

The initialization remained the same pretrained/current state; paired stochastic sampling schedules supplied the relevant seed difference. Schedules were sealed after the baseline but before fits, as recorded in `EXECUTION_ORDER_NOTE.json`. Describe that execution order accurately; do not call every implementation detail fully preregistered before baseline inference.

Each condition had a 1,500-update maximum, 6,000 total. Only M1 required 3,000 GPU updates in total. The active cap was 1,800 seconds per condition including the defined common scoring work. The historical GPU envelope was two A100 array tasks, at most two concurrent GPUs, two CPUs and 8 GiB per task, 45 minutes wall per task and 1.5 allocated GPU-hours overall. These are historical batch bounds, not a new resource entitlement.

The validation steps were 0, 100, 250, 500, 1,000 and 1,500: 24 planned records across four conditions. Qualification required at least three additional fresh known hits, no extra fresh billboard FP, the original per-class retention rules against both baselines, and the legacy unknown cap. Both seeds had to qualify for a method to proceed. Validation alone selected an eligible checkpoint; a single frozen winner could later face regression and fresh-TEST vetoes. Runner-up substitution after TEST failure was prohibited.

### 9.2 Actual fresh-validation results

Cells show known hits / billboard FP on 32 validation photos with 14 targets, under frozen narrow labels and the unchanged decoder:

| Method / seed | Step 0 | 100 | 250 | 500 | 1,000 | 1,500 |
| --- | --- | --- | --- | --- | --- | --- |
| M0 / 17 | 0 / 0 | 0 / 0 | 0 / 0 | 4 / 2 | 9 / 7 | 11 / 8 |
| M0 / 29 | 0 / 0 | 0 / 0 | 0 / 0 | 5 / 2 | 9 / 7 | 10 / 8 |
| M1 / 17 | 0 / 0 | 0 / 0 | 0 / 0 | 3 / 2 | 10 / 7 | 12 / 8 |
| M1 / 29 | 0 / 0 | 0 / 0 | 0 / 0 | 4 / 1 | 11 / 8 | 13 / 7 |

Every checkpoint with enough additional hits also added FP. Each also added one billboard FP on the older reviewed set, failing retention against both baselines. Final old unscored counts were M0 538/538 and M1 542/538 for seeds 17/29, above the unchanged cap 530. Other reviewed classes did not trigger the recorded per-class retention failures.

**Outcome: all four conditions complete; neither method qualified in either seed; `winner=null`.** No winner lock or fresh-TEST consumption lock was created. The conditional winner regression/fresh-TEST inference was not run. Fresh TEST photos used: zero.

### 9.3 Fixed final TRAIN diagnosis

This later read-only diagnostic used the same 124 approved narrow-scope TRAIN photos: 60 fresh plus 64 old replay photos, with 47 positive and 77 absent photos. It did not reopen validation selection.

| State | Fresh TRAIN hits /38 | Fresh-positive FP | Fresh-absent FP | Old-absent FP | Fresh query geometry coverage /38 | Old coverage /50 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Starting model | 0 | 0 | 0 | 0 | 36 | 35 |
| M0-17 final | 27 | 7 | 12 | 7 | 36 | 35 |
| M0-29 final | 27 | 6 | 8 | 7 | 36 | 35 |
| M1-17 final | 30 | 4 | 13 | 8 | 38 | 47 |
| M1-29 final | 27 | 7 | 12 | 6 | 37 | 47 |

M1 could provide overlapping boxes for almost every fresh TRAIN target but still miss targets at the operating point and alarm on absent contexts. Updating the encoder classifier can change which proposals are selected even when box-regressor weights are frozen. Better geometry coverage alone did not solve discrimination. The evidence did not justify declaring box-regressor unfreezing necessary.

All 24 saved validation records, 6,000 update-log entries and selection decisions were audited. The M1 combined training/common-validation active times were 1,071.375397 and 1,063.400694 seconds. The starting checkpoint and frozen/inactive parameter guards passed. The exact existing retrieval/local-follow-up was consumed once and is complete: do not retrieve, reseal, resubmit, retrain or re-evaluate this package as a restart action.

Sources: [complete postrun report](research/continuation-20261018/outputs/fresh-selector-batch-20261022-v1/POSTRUN_REPORT.md), [completion receipt](research/continuation-20261018/outputs/fresh-selector-batch-20261022-v1/COMPLETION_RECEIPT_7870268.json), [independent audit](research/continuation-20261018/outputs/fresh-selector-batch-20261022-v1/postrun-audit-7870268-v1/INDEPENDENT_AUDIT.json), [TRAIN diagnosis](research/continuation-20261018/outputs/fresh-selector-batch-20261022-v1/postrun-train-diagnosis-7870268-v1/REPORT.json).

## 10. The three completed TRAIN-only discrimination studies

These were three distinct scopes, each separately authorized by the user. All have finished. They used cached TRAIN features, not new image inference. None saved a deployable model, read validation/TEST feature caches, submitted a GPU job, exported a model or changed the application.

### 10.1 Shared design and limits

The source TRAIN pool had 124 photos. The diagnostic used 122: **45 positive photos with 71 one-to-one geometry-covered positive queries, plus 77 whole-photo absent photos** under the old narrow labels. Two old positive photos had no covered query and were excluded explicitly, not relabelled negative. Unmatched queries in positive photos, especially unknown regions of partial old labels, were not treated as background.

Four folds keep each recorded transitive scene/identity component together, including old cross-author Times Square links. Old cross-author scene linkage is not claimed exhaustive. Folds are reused TRAIN development folds, not an independent validation or test cohort. The original preparation lacked fresh positives in fold zero; metadata-only balancing was repaired before fitting. Actual first-study inputs are `PLAN_V2.json` / `FOLDS_V2.json`; the failed earlier preparation is preserved.

The fixed models were linear 256→1 and MLP 256→32→1. Each of four folds fitted both architectures: eight fits per study, 160 AdamW updates each, learning rate 0.003, weight decay 0.0001, initialization seed 17, two CPU threads, fitting-only normalization, equal class/photo mass and a 1,800-second timed cap. No grid expansion or retries followed a failure.

Each fit retained a fixed probe score cutoff 0.5 and a fitting-only zero-alarm cutoff strictly above the maximum score over all 300 queries of its fitting absent photos. That latter cutoff was locked before scoring the held fold. These are binary-probe score criteria, not calibrated detector confidence thresholds.

### 10.2 Study 1: 64 fitting negative queries per absent photo

The first study supervised 32 baseline-hard plus 32 uniformly spaced remaining negative queries per absent fitting photo; all 300 queries were scored on held absent photos and used for fitting-only calibration. Eight fits / 1,280 updates completed in 5.187 seconds of the recorded load/fit/integrity phase.

The MLP improved average query ranking but did not provide an all-four-fold clean advantage. Low sampled training loss still accompanied alarms on some fitting photos when all 300 queries were inspected. That motivated controlling omitted-query coverage, without proving omissions caused every error.

### 10.3 Study 2: all 300 negative queries supervised

The second study retained the exact folds, initialization, models, normalization and update recipe. All 300 negative queries entered the loss: the same 32 baseline-hard queries shared half the photo mass and the other 268 shared half. `PLAN_V3.json` is the authoritative plan; earlier preparation is historical. Eight fits / 1,280 updates completed in 8.672 seconds.

Remaining fitting alarms were traced to queries that were actually supervised. Missing negative-query coverage therefore cannot explain the whole failure. The MLP improved query AP versus the linear control in all four folds, but extra held-photo alarms in two folds failed the frozen clean-gain rule. Automatic query-sampling/capacity fitting stopped.

### 10.4 Study 3: photo-level worst-negative loss

The third objective directly penalized each absent photo's worst false alarm. The positive-photo term was the mean `softplus(-logit)` of selected positive queries; the negative-photo term was `softplus(max(all 300 negative logits))`; positive/negative class mass stayed 0.5/0.5. Previous full-query BCE fits were reused as controls, not refitted. Eight fits / 1,280 updates completed in 10.406 seconds.

The MLP fit every selected fitting positive above 0.5 and every fitting absent query below 0.5 in all four folds. Highest fitting-negative probabilities were approximately 0.0278–0.0416. This demonstrates that this capacity/objective can fit this selected query task. It does not establish full-image detector fit or generalization.

### 10.5 All held TRAIN-fold results

| Study / probe | Mean fold query AP | Hits at 0.5 /71 | Absent photos alarmed at 0.5 /77 | Hits at fitting-zero-alarm cutoff /71 | Absent photos alarmed there /77 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 64-query / linear | 0.6391 | 68 | 77 | 18 | 4 |
| 64-query / MLP32 | 0.6849 | 51 | 21 | 22 | 6 |
| 300-query BCE / linear | 0.4991 | 68 | 77 | 1 | 2 |
| 300-query BCE / MLP32 | 0.6908 | 51 | 20 | 22 | 5 |
| Photo-max / linear | 0.7047 | 70 | 44 | 38 | 8 |
| Photo-max / MLP32 | 0.7160 | 48 | 15 | 63 | 29 |

Neither photo-max architecture had nondecreasing hits with nonincreasing alarmed photos in every paired fold against its frozen BCE control. `objective_clean_support_methods=[]`. Fewer alarms at 0.5 came with fewer hits; the fitting-zero-alarm cutoff produced many held alarms after fitting negatives were strongly suppressed. Average AP was not substituted for the declared count criterion after outcomes were observed.

The right interpretation is a transfer/generalization problem under this particular supervised query task and its reused TRAIN folds. It does not identify a unique cause among scene diversity, semantic labels, feature limitations, calibration and other choices. It does not prove that larger heads solve the problem or that frozen features can never work. Positive-query geometry conditioning, absent NMS/other-class competition and incomplete historical scene linkage limit the conclusion.

The third study brought the total to **24 diagnostic fits / 3,840 updates**. An audit list-order comparison was repaired without rerunning fits or changing scores; the original script/evidence and repair note remain. Automatic old-scope classifier/query/loss grids are closed. The later user definition answer supersedes the report's pending human-boundary question.

Sources: [first study](research/continuation-20261018/outputs/train-discrimination-7870268-20261022-v1/STUDY_REPORT.md), [full-query control](research/continuation-20261018/outputs/train-discrimination-full-query-7870268-20261022-v1/CONTROL_REPORT.md), [photo-level study](research/continuation-20261018/outputs/train-photo-max-loss-7870268-20261022-v1/STUDY_REPORT.md). Each directory contains plans, authorization, traces and independent audit receipts.

## 11. The accepted broader billboard definition

The user was asked about a promotional hotel/restaurant board labelled positive and large restaurant-name signs labelled absent. The answer was:

> “they should both be considered. they are both at the end, billboards”

The user had also said, “All right, go ahead. Proceed to the next step.” The product decision is resolved: business/restaurant identity boards count alongside promotional boards. Do not ask the same broad question again.

The recorded task-definition version is **`frametrail-billboard-business-identity-v2-20261022`**, class **133**.

| Included in the working definition | Excluded or subject to the stated boundary |
| --- | --- |
| Dedicated physical advertising/campaign boards or panels | Traffic regulation/safety signs |
| Business, venue, institution, product or service identity boards | Pure operational routes, timetables or wayfinding without business/venue identity or advertising as the main function |
| Freestanding restaurant names and dedicated service/garage panels | Generic whiteboards, computer/TV equipment and classroom projection |
| Event promotion/identity boards and public-service campaign billboards | Decorative framed photos/art and ordinary household objects |
| Printed or digital dedicated advertising panels | Bare letters directly applied to a facade/object are not automatically a billboard |

Venue/institution/service panels are a documented implementation interpretation of the user's expansion, not individual user confirmation of every possible photo. Small retail price cards, mixed service/operational displays, nonplanar lantern/umbrella signs and dense scenes remain held where a unit/boundary is unresolved. Contractor/permit/owner markings integral to the billboard fixture are not automatically separate display faces. Dedicated business panels are considered separately.

Review the whole photo for class133 completeness or absence. A publisher category, an anchor label or a board-shaped object is not enough to declare absence. Likewise, bare facade lettering is a candidate negative confuser only after checking the entire photo for other in-scope panels.

Some earlier negative supervision conflicts with this accepted task. Consequently, the old 77-photo “absent” TRAIN denominator and its alarm counts are frozen narrow-task measurements. They must not be presented as 77 qualified negatives or all true false positives under the broader task. The revision also does not prove that all observed alarms were label errors.

Old labels, results, source hashes and selection decisions remain frozen. Prepare a separate qualified truth overlay with exact provenance. No retroactive rescoring may be used to proclaim an old rejected run a success.

Source: [task definition](research/continuation-20261018/outputs/broad-billboard-definition-20261022-v1/TASK_DEFINITION.json), [user authorization record](research/continuation-20261018/outputs/broad-billboard-definition-20261022-v1/AUTHORIZATION.json).

## 12. Exact current annotation state

The authoritative revision folder is:

```text
outputs/broad-billboard-definition-20261022-v1/
```

Resolve it under the canonical continuation locally, or under `research/continuation-20261018/` in GitHub. Read `REVISION_REPORT.md`, `TASK_DEFINITION.json`, `PLAN.json`, then the latest **`first-pass-v4/`** files. Earlier `fresh-train-draft-v1`, `fresh-role-draft-v2` and `review-stage-v3` are preserved stages, not the latest annotation truth.

### 12.1 What was actually reviewed

The fixed queue contains **323 original photos**: fresh TRAIN 60, fresh validation 32, fresh TEST 32, old TRAIN replay 64 and old validation 135. All 323 originals were viewed during the first pass, and their image hashes were checked. This was an assistant review, not independent human annotation or a representative new gold standard.

The 204 previously scoped records have explicit draft target/absence decisions. The 119 previously unknown old-validation photos have first-pass visual notes and retain unknown scope. Thirty-two of those 119 have display/boundary follow-ups. They are not converted to negative supervision or cleared scoring truth by default.

The draft adds **41 proposed boxes** and retains **129 inherited targets for provenance**, including one explicitly ineligible semantic conflict. Twenty formerly absent photos contain in-scope boards: 19 fresh photos and one old TRAIN laundromat identity photo, `399048f892919b4c`.

There are 29 reviewed draft-photo holds, as well as the 119 old unknown records still awaiting separate qualification. A completed first pass is not completion of whole-photo annotation, rights clearance, scene analysis or final release admission. Dense old positive-only scenes stay partial when boxes remain incomplete.

### 12.2 Fresh-role draft counts

| Role | Complete positive photos | Partial positive photos | Whole-photo absent | Unknown/hold | Missing absent photos to original minimum |
| --- | ---: | ---: | ---: | ---: | ---: |
| TRAIN | 34 | 6 | 19 | 1 | 11 |
| Validation | 16 | 1 | 14 | 1 | 6 |
| TEST | 13 | 3 | 16 | 0 | 4 |

These are draft counts. They are not approved release counts. The partial positives do not establish full-photo completeness. Even a complete-positive draft must still pass the other qualification checks.

The old TRAIN absent pool of 47 becomes 45 absent, one unknown and one complete positive in the draft. The old positive pool of 17 becomes five complete positives and 12 partial positives. Old validation totals become nine absent, two complete positive, four partial positive and 120 unknown, including the 119 originally unknown photos plus one held small-retail-card case. These distributions describe the new draft and do not modify the old experiment inputs.

### 12.3 Exact inherited-target conflict

Photo **`88ced829147507c7`**, the second inherited target (zero-based index 1), encloses a **7 Av street-name sign**. Its normalized centre/size box is:

```json
[0.1366665, 0.509375, 0.273333, 0.06000000000000005]
```

That is operational wayfinding, excluded under both the narrow and broader working rules. The latest draft marks this target:

```text
semantic_review_status = excluded-operational-sign-conflict-held-not-admissible
eligible_for_training_or_scoring = false
```

Keep the old source target and metrics unchanged. Exclude/correct this target only in a new qualified overlay with an exact receipt. An inherited box is provenance, not proof that the new truth is semantically valid. Generic wording about retaining old positives must not override this explicit target-level hold.

### 12.4 Integrity and readiness

The original narrow fresh-release SHA remains `b262af61db8141abadd61cc026454953f6c172bd2fff552334c456170b5feb09`. The current v4 annotation draft SHA is `6bc12636d7d71242527c7742b3a66872f193775bae45a9d95d3c12ed3c0def2d`. Its completion receipt records structural checks passing but semantic/rights/scene/role/guard qualification incomplete. The revision folder's final manifest checked 108 files at closure; excluded local visual assets are not all present in the GitHub text archive.

The revision stage performed zero optimizer updates, zero new model inference, zero TEST predictions and zero cluster jobs. `approved_for_training=false`; `production_adoption=false`.

Sources: [v4 completion](research/continuation-20261018/outputs/broad-billboard-definition-20261022-v1/first-pass-v4/COMPLETION_RECEIPT.json), [v4 annotations](research/continuation-20261018/outputs/broad-billboard-definition-20261022-v1/first-pass-v4/ANNOTATIONS_DRAFT.json), [qualification queue](research/continuation-20261018/outputs/broad-billboard-definition-20261022-v1/first-pass-v4/QUALIFICATION_QUEUE.json), [inherited-target conflict](research/continuation-20261018/outputs/broad-billboard-definition-20261022-v1/first-pass-v4/INHERITED_TARGET_CONFLICT.json), [overlay QA](research/continuation-20261018/outputs/broad-billboard-definition-20261022-v1/first-pass-v4/OVERLAY_QA_REVIEW.json).

## 13. Data requirements and unused inventory

The frozen engineering pilot requirements remain:

| Role | Positive-photo minimum | Absent-photo minimum | Scene/concentration requirements |
| --- | ---: | ---: | --- |
| Fresh TRAIN | 30 | 30 | At least 20 positive and 20 absent scenes; at most two photos per scene |
| Fresh validation | 12 | 20 | At most one photo per scene |
| Fresh TEST | 12 | 20 | At most one photo per scene |

The original minimum per TRAIN absent confuser family is **five**, not six or eight. Current draft absent families are household/laundry 7, indoor frames/screens/boards 8, traffic/information 4 and shop/business-lettering 0. The family shortfalls are therefore **one traffic** and **five shop** confusers. These family requirements sit inside the overall missing 11 TRAIN absences; they are not 6 additional photos on top of 11.

The family name “shop/business-lettering” predates the expanded target definition. Physical business identity panels now count positive. Valid future negatives in that family need genuinely out-of-scope street/shop confusers, with whole-photo absence established. Do not manufacture negative coverage by retaining a known semantic contradiction.

The inventory at `review-stage-v3/UNUSED_LOCAL_INVENTORY.json` enumerates 347 source-eligible visual-queue records from two existing intakes. Of those, 124 are already in the narrow fresh release, leaving **223 unused**. This is the inventory scope, not a claim that every photo ever acquired across the project has been reviewed or enumerated here.

| Prospective role | Billboard-anchor candidates | Other-anchor candidates | Total unused |
| --- | ---: | ---: | ---: |
| TRAIN | 52 | 33 | 85 |
| Validation | 57 | 11 | 68 |
| TEST | 66 | 4 | 70 |
| Total | 175 | 48 | 223 |

The 48 contrast anchors comprise TRAIN monitor 5, picture frame 10, traffic sign 6, washing machine 4, whiteboard 8; validation monitor 3, picture frame 2, traffic sign 3, washing machine 1, whiteboard 2; TEST one each of monitor, picture frame, washing machine and whiteboard. Anchor categories are source selection metadata, not class133 absence labels.

All 223 image hashes were checked during inventory. No current exact-hash or cross-role resolved-owner conflicts were found in that metadata check. This does not clear content, licensing, perceptual duplicates, scenes or sessions. Four TEST contrast candidates matching the numerical gap does not guarantee four usable TEST negatives.

The source queues are:

```text
outputs/data-review-7824179-20261020-v1/VISUAL_REVIEW_QUEUE.json
outputs/data-review-7840599-20261021-v1/VISUAL_REVIEW_QUEUE.json
```

Original prospective roles are fixed. All unused source-eligible candidates were enumerated without model-outcome filtering. Review originals under those roles; do not move a convenient TEST photo into TRAIN or replace a validation example because a model finds it easy/hard. If fewer candidates qualify than required, retain an explicit shortfall and prepare the next justified collection scope rather than silently substituting data.

Source-specific publisher/license corroboration is one stage of provenance, not automatic final rights clearance. Resolved author identities/aliases, scene/session links, exact/perceptual duplication, source evidence and full-photo target/absence review remain necessary. Records such as `photo-specific-license-corroborated` do not justify bulk-setting `approved_for_training=true`.

Sources: [experiment design and minima](research/continuation-20261018/outputs/training-strategy-20261019-v1/EXPERIMENT_DESIGN.json), [unused inventory](research/continuation-20261018/outputs/broad-billboard-definition-20261022-v1/review-stage-v3/UNUSED_LOCAL_INVENTORY.json), [revision report](research/continuation-20261018/outputs/broad-billboard-definition-20261022-v1/REVISION_REPORT.md).

## 14. Scientific rules that must survive the handoff

**Scope is per image and class.** A complete class scope supports TP/FP/FN scoring within that declared task; explicit absence supports negative supervision. Partial known positives support known-target recall but not general precision. Unknown scope supports neither blanket negative supervision nor an automatic FP judgement. A publisher annotation list is not proof that unlisted objects are absent.

**Keep TRAIN, validation and TEST roles distinct.** Optimizer fitting and probe normalization/calibration use fitting TRAIN data only. Validation is development/selection evidence and has already been used under the narrow task. The fresh TEST cohort remains model-prediction-unconsumed; visual annotation review is not the same as model evaluation. The older 130-photo/reserved-video references from 7805570 have already been consumed and remain regression evidence.

**Retain both baselines.** Keep the original model and the 7805570 step-100 continuation state, their scores, hashes and per-class guards. Effective unknown cap remains 530. Do not replace the stricter cap with 533, treat unknowns as measured FP, or discard the original baseline because the newer model looks better on a priority class.

These both-baseline rules refer to the pinned RF checkpoint states named by the experiment protocols. The separate native YOLOX-S default is a product/runtime choice. Preserve each protocol's exact checkpoint identities instead of interpreting the word “baseline” as a freely interchangeable model.

**Keep comparison and release gates separate.** Scientific eligibility, strict ONNX numerical qualification, CPU latency/memory, app workflow compatibility and distribution/rights readiness are independent. Passing one does not waive the others. The current ONNX hold stays visible.

**Freeze plans and hashes before outcomes where required, and report actual ordering.** Keep deterministic paired schedules, declared validation points, budgets and selection rules. Do not add validation checkpoints, extend runs, change thresholds, swap examples or relax guards after a failed result. If a new scientific scope is needed, state it separately and preserve the old failure.

**Cached features require exact contract verification.** Earlier attempts to trim full tensor layouts exposed FP32 GEMM differences. Successful replay retained complete layouts and checked outputs/losses/gradients. A smaller-looking tensor is not automatically an equivalent cache. GPU-side scores do not replace the declared common CPU-reference selection device.

**Other classes and model state remain guarded.** In constrained experiments, only specifically allowed rows may change; fingerprint other parameters and buffers. Encoder row changes can alter proposals even with frozen regressors. Lack of direct gradient on unknown logits does not establish every indirect output is invariant.

**A semantic conflict with an old class133 gate needs an explicit resolution.** The broader task includes objects that old truth may call absent. Do not optimize against contradictory labels or silently waive the legacy gate. Document a new truth/comparison contract and surface a consequential unresolved policy choice if one remains after the available records and user clarification are applied.

**Avoid stronger conclusions than the evidence.** Query AP is not detector mAP; overlapping-box coverage is not detection recall; assistant visual review is not independent human gold; warm FPS is not sustained performance; counts/class agreement is not strict tensor parity; fewer alarms with fewer hits is not a clean improvement. Do not claim all failures are explained by labels or all errors require feature/box unfreezing.

## 15. What to do next, in execution order

The immediate authorized continuation is local data qualification under the broader definition. Continue autonomously while concrete work is possible. The recommended first work block is:

1. Read this handoff, `AGENTS.md`, the top of `CURRENT_HANDOFF.md`, the task definition, v4 completion/annotation/QA files, the experiment minima and the unused inventory. Check the working tree before editing. Preserve all sealed outputs.
2. Confirm access to the original local images named by the inventory/source queues. Resolve the recorded source path and verify its hash before reviewing it. A GitHub-only clone has text evidence but does not contain the original photos or model/feature binaries.
3. Create a new versioned continuation/review output, retaining a pre-outcome candidate queue and original roles. Review the existing candidates systematically. No model predictions, threshold tuning or baseline inference is needed for this step.
4. Seek truly absent additions for the 11 TRAIN / 6 validation / 4 TEST gaps, with the five shop and one traffic TRAIN family gaps explicitly represented. Review the whole image under the accepted definition. Keep uncertain content unknown/held, and record why each candidate is admitted, held or rejected.
5. Complete known annotation holds in the current draft, including target extent/unit issues, dense partial scenes and the explicit 7 Av inherited-target exclusion. Do not rewrite old labels/results. Use exact provenance for every new/changed/removed target in the new overlay.
6. Recheck source/rights evidence, owner/alias and scene/session groups, within/cross-cohort exact/perceptual duplication, role separation and scene concentration. Existing metadata checks are reusable evidence, not a substitute for the missing checks.
7. Recompute readiness from the actual admitted records. Count complete/partial/absent/unknown photos separately. Verify per-role and per-family minima and document any shortfall. Do not promote a draft because its raw photo count looks sufficient.
8. Write an explicit comparison plan resolving broader class133 semantics versus the retained legacy gates. Preserve other-class retention, both baselines, unknown drift constraints and fresh-TEST isolation. A necessary unresolved consequential choice may require human input, but the general business-board definition is already decided.
9. Only once a genuinely qualified versioned dataset and guard-compatible plan exist should an expanded-task baseline or a separate bounded adaptation proposal be considered. The failed old row/query/loss grids remain closed. No deployable architecture is already chosen.
10. Update the plain-language status, focused handoff, manifests and GitHub with the new evidence. State remaining uncertainty and the single next concrete project step.

Do not start a new collection job simply because a previous proposal mentions one. There are 223 unused local candidates to qualify first. If they cannot meet the frozen requirements, the exact measured shortfall should drive a bounded prospective collection design. Preserve failed/held candidates and original split roles.

If original photos or private repo access are unavailable to the new model, continue reading the available documentation and metadata, then identify the precise missing source directory/artifact needed to perform visual qualification. Do not pretend that a text description or thumbnail constitutes a completed original-image review. Ask the user to provide authorized access through the appropriate interface; never ask them to paste credentials.

## 16. User preferences, authorization and operational boundaries

The standing user instruction is to keep working autonomously on authorized FrameTrail work. Do not stop for routine local exports, parity checks, CPU benchmarks, reversible app integration, packaging, reviews or fixes. The user has explicitly expressed frustration with repeated permission requests.

The latest 18 October continuous-work instruction superseded an earlier blanket requirement to pause solely for new cluster approval within the established scope and resource limits. Preserve exact scope and authorization provenance before submission. It did not grant unlimited resources, waive model/data gates, authorize automatic retries/replacements or reopen failed scientific recipes. The three eight-fit studies were separately authorized and are now complete; the current data revision contains zero further fits.

Ask for input only when genuinely needed: unavailable credentials/access, direct KIT OTP/password interaction, an unresolved consequential choice, or a higher-priority restriction. User authorization does not override the new model's own tool/sandbox rules. Do not infer a new budget from old protocol maxima. Do not ask again whether business identity boards count; the answer is already recorded.

Cluster use must be strictly limited to FrameTrail. Ignore **Carrington Event and all other projects' jobs, files, logs, results, environments and sessions**, even on a shared account. Use explicit receipt-verified FrameTrail job IDs/paths. No account-wide or wildcard job management. Minimum aggregate quota information is permissible only when needed for admission; unrelated job details are not project evidence. Preserve other projects' SSH identities/services.

Before any future justified cluster batch, identify useful independent experiments and bounded dependent checks together, prefer one upload/launch and a bounded array/dependency workflow, state concurrency and aggregate budget, and verify live authenticated scheduler/account entitlement. Public partition maxima are not account entitlements. Preserve failed-task evidence; do not automatically retry, replace, requeue or add a sweep. Authentication must happen directly in the appropriate local terminal/interface; never collect pasted passwords, OTPs, private keys or tokens.

Explain practical meaning in plain language. Keep technical formulas and long receipts available in artifacts, but do not make a file the only explanation. Every user-facing response must end with the **single best concrete next FrameTrail step and a brief reason**. A recommendation does not grant new authorization for a restricted action. Carry these preferences and verified state into every handoff.

In the previous environment, the active shell was Windows PowerShell and the sandbox writable roots were unrelated MiniERP plus a visualization staging folder. Reads of FrameTrail were available; writes to the true FrameTrail directories used approved `require_escalated` calls. A future runtime may differ: inspect its actual permissions and work in the correct project rather than editing the unrelated writable project. No subagents were used; current standing instructions prohibit spawning them unless the user or applicable project/skill instructions explicitly request delegation.

Sources: [standing instructions](AGENTS.md), [current handoff](CURRENT_HANDOFF.md).

## 17. Build, run and inspect without restarting the research

These commands document the existing setup. Execute them only as relevant to actual work; data review does not require rerunning models or reinstalling dependencies.

### 17.1 Existing Windows checkout

```powershell
Set-Location -LiteralPath 'C:\Users\nazee\Documents\All Modules\FrameTrail'
git status --short --branch
git log -3 --oneline

# Existing native build and ordinary CTest suite.
.\scripts\build.ps1

# Existing standard-library Python checks; does not start a training experiment.
& '.\.deps\rfdetr-probe-cpu\Scripts\python.exe' -u -B -X utf8 `
  -m unittest discover -s tests -p 'test*.py'

# Read CLI usage, without analysis.
.\build\windows-msvc\Release\frametrail.exe --help
```

The CMake preset is `windows-msvc`, Visual Studio 2022 x64, with CMake at least 3.25. Release build/test presets are `release`. The project pins Qt **6.11.3**, ONNX Runtime CPU **1.30.0**, FFmpeg **8.1.3-9-g29e619e767** and SQLite through dependency manifests. These are project-pinned artifact versions, not a statement that the latest upstream versions should be installed. Optional GPU/export environments are separate.

On a fresh authorized machine, consult `docs/DEVELOPMENT.md` and the pinned fetch scripts before acquiring missing SDKs/models. CMake and the app do not silently download dependencies. `.deps`, models and source photos are excluded from Git. Avoid upgrading pinned packages or replacing checkpoints as a routine attempt to make an old script run.

### 17.2 Existing app launchers

```powershell
& 'C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\Run-FrameTrail.cmd'
& 'C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\Run-Balanced-Preview.cmd'
```

The second launcher explicitly selects the held RF preview. Running it does not make that model adopted. Do not activate a real camera as a routine smoke test; hardware capture requires the relevant user authorization.

### 17.3 Read-only archive verification

```powershell
& '.\.deps\rfdetr-probe-cpu\Scripts\python.exe' -u -B -X utf8 `
  scripts/verify-research-archive.py --git-ref HEAD
```

The verifier checks copied original archive files against `research/SOURCE_MANIFEST.json`, reading Git blobs when `--git-ref` is provided. It does not run archived scripts, submit jobs, fit a model or load scientific images. The source manifest does not include this newly authored handoff as an original archived experiment record.

### 17.4 Existing native analysis commands

The CLI supports `inspect <local-file>` with optional decoded-frame metadata/preview, detections, tracks, line events, saved runs and per-frame profiles. Supported profile IDs are `nano`, `small`, `world-s`, `world-m`, `openimages`, `rfdetr-7758628` and `rfdetr-7805570`. Backends are `cpu`, `auto` and strict `directml`. `frametrail run <saved-run> --export <new-csv>` inspects/exports saved evidence without requiring the source or model. Output paths should be new or follow the existing protected/atomic save rules.

Never execute an archived `START_*`, submission helper, exclusive snapshot script or result-retrieval helper simply to explore it. Several deliberately refuse overwrites or encode one-shot consumed scopes. Read their receipts and plans first.

## 18. Latest verification and remaining product limitations

During the 24 October publication, the earlier checkout passed 37 ordinary native checks and its 120 existing Python checks. After source consolidation, the latest source built successfully and passed all 37 ordinary native checks. Quick Guide checks passed at normal and simulated 125% scale, including lookup, task navigation, optional/local model resolution and empty search. The unified-window workflow passed state retention, background activity, save/CSV/reopen, cache navigation/source replacement and coordinated shutdown.

Those latest checks used local application fixtures and offscreen windows. They did not acquire a camera, submit a cluster job or run scientific fresh-TEST evaluation. They are distinct from the zero-new-image-inference claims inside the three earlier cached-feature studies and the annotation revision stage. State precisely which activity a zero-inference assertion refers to.

All 27,994 copied original archive files passed committed-blob SHA-256 verification. Credential-pattern scans of selected source/evidence files found no matches. Binary/authentication artifacts were excluded. GitHub API, remote Git ref and local `main` matched, with no uncommitted project changes after the sync.

Open or limited product areas include sustained representative accuracy, dense-scene/identity/event reliability, low-light/small/blurred object performance, long-running live resource/driver behaviour, physical-monitor accessibility, public distribution/licensing readiness and strict RF numerical qualification. Audio playback, network/multi-camera work and recording/retention are not completed deliverables of this continuation. Some older docs list additional deferred player refinements; inspect current code before making a new UI scope claim.

Project licensing is recorded as undecided in the main README. Third-party model/export licensing differs between the YOLOX baseline and broader alternatives; source/runtime notices and private evaluation do not establish public redistribution readiness. Retain dependency provenance and consult the project's third-party inventory before a separately scoped release.

The app is usable and technically substantial, but the current recognition research has not qualified a general accuracy upgrade. Keep the default/model choice, preview labels, numerical hold and evidence limits visible.

Sources: [publication checks](research/sync-20261024/VALIDATION_RECEIPT.json), [guide result](research/sync-20261024/guide-result.json), [125% guide result](research/sync-20261024/guide125-result.json), [unified workflow result](research/sync-20261024/unified-result.json), [development guide](docs/DEVELOPMENT.md), [packaging policy](docs/PACKAGING.md).

## 19. Evidence map for deeper work

Use paths relative to the repository unless working in the canonical local continuation. In the latter case, remove the `research/continuation-20261018/` prefix. Historical absolute paths inside files remain provenance and should be mapped explicitly on another machine.

| Need | Start here |
| --- | --- |
| Short current status | `PROJECT_PROGRESS.md` |
| Latest continuation and communication rules | `CURRENT_HANDOFF.md`, `AGENTS.md` |
| Original product purpose | `docs/PROJECT_BRIEF.md` |
| Native architecture | `docs/ARCHITECTURE.md`, current `include/frametrail/` and `src/` |
| Current schema/profile truth | `src/run_store.cpp`, `include/frametrail/detector.hpp`, `src/detector.cpp` |
| Accepted recorded-analysis flow | `docs/SAVED_RUNS.md`, `apps/desktop/saved_run_window.*` |
| Broad models and measured tradeoffs | `docs/RECOGNITION.md`, `docs/benchmarks/recognition-0.12.json` |
| Latest desktop/package work | `research/continuation-20261018/outputs/native-lean-guide-20261019-v1/REPORT.md` |
| Source merge provenance | `docs/SOURCE_CONSOLIDATION_20261024.json` |
| Current scientific strategy/minima | `research/continuation-20261018/outputs/training-strategy-20261019-v1/STRATEGY.md`, `EXPERIMENT_DESIGN.json` |
| Retained RF checkpoint evaluation | `research/continuation-20261018/outputs/heldout-evaluation-7805570-20261018-v1/REPORT.md` |
| Numerical hold | `research/continuation-20261018/outputs/export-numerics-7805570-20261018-v1/REPORT.md` |
| 7809335 failure | `research/continuation-20261018/outputs/billboard-batch-diagnosis-7809335-20261018-v1/REPORT.md` |
| 7818553 failure/data motivation | `research/continuation-20261018/outputs/selector-diagnosis-7818553-20261018-v1/REPORT.md` |
| Narrow fresh data | `research/continuation-20261018/outputs/data-review-7840599-20261021-v1/reviewed-release-v1/scoped-fresh-additions-v1.json` |
| Completed fresh experiment | `research/continuation-20261018/outputs/fresh-selector-batch-20261022-v1/POSTRUN_REPORT.md` |
| First discrimination study | `research/continuation-20261018/outputs/train-discrimination-7870268-20261022-v1/STUDY_REPORT.md` |
| Full-query control | `research/continuation-20261018/outputs/train-discrimination-full-query-7870268-20261022-v1/CONTROL_REPORT.md` |
| Photo-level objective | `research/continuation-20261018/outputs/train-photo-max-loss-7870268-20261022-v1/STUDY_REPORT.md` |
| Current product definition | `research/continuation-20261018/outputs/broad-billboard-definition-20261022-v1/TASK_DEFINITION.json` |
| Current data report | `research/continuation-20261018/outputs/broad-billboard-definition-20261022-v1/REVISION_REPORT.md` |
| Latest draft / holds / target conflict | That folder's `first-pass-v4/` |
| Next candidate inventory | That folder's `review-stage-v3/UNUSED_LOCAL_INVENTORY.json` |
| Focused research continuation | `research/continuation-20261018/NEXT_CHAT_BROAD_BILLBOARD_20261022.md` |
| Original-byte archive manifest | `research/SOURCE_MANIFEST.json` |
| Excluded local assets and original roots | `research/LOCAL_ARTIFACT_INVENTORY.json` |
| Publication evidence | `research/sync-20261024/` |

The v4 draft was built by helpers archived at `research/continuation-20261018/outputs/`: `prepare_broad_billboard_revision.py`, `build_broad_draft.py`, `build_fresh_role_draft.py`, `finalize_broad_review_stage.py` and `close_broad_first_pass.py`. Read them to understand schema/lineage. Preserve their versioned outputs and exclusive-creation behaviour. New continuation work should create a new version rather than overwriting v4.

## 20. Restart instructions to the incoming AI model

You have enough context here to explain the project and identify the current blocker without asking the user to retell its history. First inspect the actual repository/workspace and available artifacts. If this document and live records differ because later work exists, verify the newer receipts and preserve the historical account instead of blindly enforcing this snapshot.

Your immediate objective is to advance **the versioned broader-definition data qualification**, beginning with the unused local photo inventory and the concrete 11/6/4 absence gaps. Use the already accepted definition, original prospective roles and explicit target-level holds. Retain the old experiments, both model baselines, numerical hold and fresh-TEST isolation.

In the first useful progress update, state the verified workspace/commit, the current annotation qualification state and the exact review block you are starting. If originals are unavailable, identify the precise source queue/path or private artifact access missing, and continue useful metadata review while resolving access. Do not claim to have reviewed an original image from a text description.

Report new work using concrete counts, new versioned artifact paths, source/hash checks, remaining holds and practical implications. Explain what changed and what did not qualify. Keep GitHub and the current handoff aligned as progress is made. Do not reopen a completed study, invent a new model winner, convert unknowns to background or silently relax a gate.

**The single best next project step is to qualify the existing unused photos for the missing 11 TRAIN, 6 validation and 4 TEST truly absent examples, including five valid TRAIN shop confusers and one traffic confuser, because the accepted broader billboard task needs that trustworthy coverage before a new baseline or training comparison.**
