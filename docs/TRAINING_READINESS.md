# Training readiness: low-light fox/dog pilot

Audited: 3 October 2026. Application baseline: `8a5a633` (0.12).

The selected first experiment is **fox/dog and related animals in low light**, as requested by the user. FrameTrail is ready to prepare this experiment. It is not yet ready for a full training run or adoption of a trained model: independent labelled evaluation, a custom-model loading/export contract, and a reproducible cluster environment are missing.

The next work is training preparation within conditional Phase 8. Completion of every unrelated roadmap item is not required. The accepted saved-analysis interface and choose/drop → analyse → review → save/export flow stay intact.

## What the audit establishes

| Area | Current evidence | Meaning for this pilot |
| --- | --- | --- |
| Native application | FFmpeg decoding, owned RGB frames, timestamped inference, tracking, saved appearances and CSV; CPU and optional DirectML | Reuse these modules. A Python inference service is unnecessary for a compatible ONNX model. |
| Integration correctness | 45 native/desktop checks and 18 Python scorer/registry checks passed in 0.12; Python/native comparison covers 15 strong targets | Substantial evidence that the supported profiles run correctly; these checks do not measure general recognition accuracy. |
| Recognition | Open Images recovered 3/4 selected real fox targets; the supplied dark generated fox remains missed at confidence 0.35 | A domain-specific gap is plausible. Four fox targets and generated video cannot establish its size or likely training benefit. |
| Evaluation | Small, partially annotated image sets; selected-target matching and tracking/event scorer tooling | Full target-class annotations, independent real footage and precision/recall evaluation are required before a training decision. |
| Custom model integration | Five fixed profiles, exact label-order checks, fixed output dimensions and schema-4 profile/vocabulary persistence | A new small-class checkpoint cannot simply replace an existing ONNX file. Extend model registration before spending substantial training compute. |
| Compute | Local GPU inference works; user reports bwUniCluster access | Enough capacity for a compact experiment in principle. Actual GPU entitlement and a Linux CUDA training environment remain unverified. |
| Sustained reliability | Bounded queues/pages and short integration/performance runs exist | Measure a representative recorded-analysis run, cancellation and resource use for this pilot. Full live-camera and public-release validation can remain separate. |

Evidence: [recognition report](RECOGNITION.md), [frozen measurements](benchmarks/recognition-0.12.json), [tracking evaluation](TRACKING_EVALUATION.md), [GPU integration](GPU_INFERENCE.md), and [saved analysis](SAVED_RUNS.md).

Our Open Images model is already pretrained on that dataset. Reusing more generic examples may help class coverage, but it does not automatically teach low-light fox/dog discrimination. Training can adapt features and decision boundaries to representative conditions. It cannot reliably recover distinguishing detail absent from a tiny, blurred or nearly black object. Detection also remains separate from tracking: better labels do not automatically fix identity switches or duplicate appearances.

## Scope and model choice

Start with fox and dog as the priority classes. Add only a few related animals/confounders for which adequate independent, reviewed data exists; cat, coyote or wolf are candidates, not a finalized class list. Freeze the list after the data inventory. Empty images are negative examples, not an object class called “background.” Keep daylight examples and varied backgrounds alongside low-light data.

Fine-tune a compact pretrained detector instead of training from scratch. A YOLOv8s-family candidate minimizes changes to the decoded YOLO adapter already present; select the exact starting weights and their terms during preparation. A changed class head may require initialization even when pretrained feature weights are reused. Experimental YOLO-World remains an evaluated baseline, not an assumed solution just because it accepts the word “fox.”

The first trained candidate should be an **optional wildlife profile**. Preserve YOLOX-S and broad recognition as separate choices. Replacing the 597-category general model with a small wildlife head would remove unrelated categories; fine-tuning the entire broad head would require much wider labelled coverage and explicit regression protection. That larger project is outside this pilot.

## Dataset candidates checked

| Source | Useful role | Important limit / intake decision |
| --- | --- | --- |
| [Open Images V7](https://storage.googleapis.com/openimages/web/download_v7.html) | Curated fox/dog and related-class boxes; varied daylight examples | Already used by the broad model. Retain provenance and attribution; verify image rights. Its published validation examples do not constitute an independently collected deployment test. |
| [Caltech Camera Traps, LILA](https://lila.science/datasets/caltech-camera-traps) | Camera-location diversity, animal scenes and empty-scene negatives | 243,100 images but about 66,000 boxes, with separate image/box annotations. Inspect species counts and join annotations correctly before selecting a subset. The publisher supplies location splits and a permissive CDLA license. Use selective image retrieval rather than the 105 GB archive. |
| [Lindenthal Camera Traps, LILA](https://lila.science/datasets/lindenthal-camera-traps/) | Fox/night scenes and a small supplementary evaluation source | 775 sequences but only 412 annotated images. Night intensity frames are infrared, whereas daytime frames are RGB. Evaluate modalities separately; infrared success does not establish colour-night performance. Avoid the 213 GB bulk archive for this pilot. |
| [ExDark](https://github.com/cs-chan/Exclusively-Dark-Image-Dataset) | Potential low-light dog/cat examples | 7,363 images and 12 classes; no fox class. The current README distinguishes software licensing, dataset materials and third-party image rights. Referenced dataset-terms material was not retrievable during this check. Keep it pending verification rather than treating the software's BSD license as permission for all images. |

Open Images labels are not exhaustive across classes. Missing annotations do not prove absence; its official evaluation also handles hierarchy and group-of boxes differently from ordinary box scoring. For this small pilot, fully review all selected target classes in each retained image and document treatment of ambiguous/group boxes before converting labels. Otherwise a normal YOLO loss can punish correct detections of unlabelled animals. See the [publisher's annotation/evaluation policy](https://storage.googleapis.com/openimages/web/evaluation.html).

No dataset has been downloaded or approved for ingestion by this audit. Metadata-first inspection is the next step. Record original image ID/URL, source version, applicable terms/attribution, camera/site/recording, modality, lighting condition, dimensions, labels and file hashes. Review bounding-box bounds, class mapping, mixed-species scenes and uncertain labels. Exclude unresolved species from species-specific scoring instead of forcing a guess.

Use the supplied Gemini clips as regression/stress examples. The primary test must contain real, permissioned footage with reliable species labels. Separate train, validation and test by camera/site/recording/session, and check exact and near duplicates across sources. Randomly splitting adjacent frames gives misleading results. Public-source overlap with pretraining must also be reported.

There is no universal minimum number of images. Inventory independent examples per class, lighting condition and camera before choosing a run. Hundreds of nearly identical frames from one animal passage are not hundreds of independent examples. If usable real low-light fox examples are sparse, collecting/reviewing them takes priority over a larger generic download.

## Four preparation gates

### A. Establish data and a trustworthy baseline

Deliver a small versioned manifest, frozen class map, label validator and grouped splits. Fully annotate the selected target classes, including all relevant instances, and include empty scenes and confusing animals/backgrounds. Treat colour low light and infrared as separate slices.

Extend the existing evaluation tooling to report per-class precision/recall, AP50 and AP50–95, wrong-class confusions, missed animals, and performance by lighting, size and occlusion. Report fox-as-dog errors separately from missed foxes. For negative recordings, measure false animal detections per minute; for appearance review, inspect timestamp continuity and fragmented appearances rather than calling tracker IDs verified unique animals.

Compare the existing broad model and World models on validation data first. Use YOLOX-S as the dog/people/vehicle control; it cannot emit fox. Choose confidence/NMS settings using validation only. Lock the independent test and acceptance thresholds before the main fine-tuning run. A simpler threshold adjustment is worth measuring, but hiding false labels while losing most animals does not satisfy the goal.

Exit: the domain gap is measured on real data, label completeness and split integrity are documented, and an evaluation command can reproduce the baseline. If the pretrained model meets the useful target, stop here.

### B. Prove that a custom checkpoint can reach the native app

Current boundaries are visible in [detector profiles](../include/frametrail/detector.hpp), [native decoding](../src/detector.cpp), [saved model identity](../src/run_store.cpp), and the [official-checkpoint exporter](../scripts/export-world.py). The exporter verifies publisher hashes and fixed vocabularies; it is not a general training-artifact exporter.

Add a versioned model descriptor/registration path containing input preprocessing, output layout, ordered raw labels, raw-to-canonical IDs, model hash and provenance. Reuse the decoded YOLO implementation while allowing a reviewed small class head. Extend selector and saved-model validation with explicit identity; preserve old schemas and vocabularies. Do not disguise a different head as the existing `openimages` profile or remove shape/label checks.

Export a configured small-class checkpoint before substantial training. Compare Python and native boxes/scores, verify CPU and optional DirectML execution, then exercise analyse/review/save/reopen/CSV with the exact vocabulary. This proves mechanical compatibility, not recognition quality. Pin export settings compatible with the existing adapter; do not copy newer framework defaults without checking their output layout.

Exit: a custom artifact completes that round trip, wrong label maps fail clearly, and existing model/saved-run behaviour remains protected.

### C. Establish a reproducible single-GPU cluster path

Confirm the user's active account/project, permitted GPU partition, allocation limits, storage lifetime and export/transfer route. Use one NVIDIA GPU initially. bwHPC documents Slurm GPU requests beginning at one GPU and short development queues; compute-heavy work belongs on compute nodes. Actual access and queue wait remain account-dependent. See [job policy](https://wiki.bwhpc.de/e/BwUniCluster3.0/Running_Jobs).

Create a pinned Linux CUDA/PyTorch environment. The Windows CPU-only recognition export environment and DirectML inference runtime do not establish training readiness. Enroot with Slurm integration is the recommended container route; Apptainer is also supported. Verify current partition names rather than copying older examples. See [supported containers](https://wiki.bwhpc.de/e/BwUniCluster3.0/Containers).

Run a bounded setup test: inspect the allocated GPU, load a tiny reviewed subset, verify loss/checkpoint creation, resume, export, and retrieve logs/artifact. This checks mechanics only. Record code revision, parent-weight hash, dataset/split hashes, class map, configuration, seed, environment/container identity, timing and peak accelerator memory. Preserve artifacts outside expiring scratch storage.

Exit: a repeatable small job and retrieval work, with a resource/time budget for the actual experiment. No cluster login, transfer or job submission was attempted by this audit.

### D. Run and assess one limited fine-tuning experiment

Only after A–C pass, run one compact candidate with validation-based early stopping and checkpoint retention. Start with a single GPU; distributed training, broad hyperparameter searches, hosted inference and agents are unnecessary for this experiment. Pretrained warm starts, checkpoint/resume and export are supported by the [training](https://docs.ultralytics.com/modes/train/) and [ONNX export](https://docs.ultralytics.com/modes/export/) tooling, but versions and artifact contracts must be pinned for FrameTrail.

Before the run, record minimum useful improvement in low-light fox recall at an agreed precision, tolerable fox/dog confusion and false detections per minute, and local CPU/GPU speed/memory limits. Set these from the baseline and intended usage; this audit does not invent an accuracy guarantee. Report class/slice counts and variability across independent clips, not only an aggregate score.

Select the checkpoint and operating threshold using validation; evaluate the locked test afterward. A disappointing test does not become a tuning set. Verify the exported native model on the same inputs, plus appearance timestamps, cancellation and a representative longer recording. Document source length, processed frames, peak memory, disk use and failures. Keep the candidate optional or reject it if useful accuracy gains do not survive native execution or its cost is excessive.

Exit: a reproducible comparison and explicit adoption/rejection decision. Lower training loss alone is insufficient.

## Necessary now, deferred work

Required before substantial training: scoped reviewed labels and independent evaluation, custom model/export round trip, and the Linux single-GPU setup test. Required before adopting its artifact: accuracy comparison and bounded recorded-file resource/workflow validation.

Live-camera soak/unplug testing, clean-machine/public distribution review, audio, network/multi-camera input, preview zoom, GUI animation, agents and a cloud API remain separate roadmap work. They need not delay this preparation. Existing model notices and dataset provenance still apply to any candidate; public distribution has its own unresolved review.

The immediate next module is **dataset inventory and evaluation preparation**, followed by custom-model registration and the cluster setup test. The UI remains unchanged. This audit adds a plan; it introduces no model, training job, dataset, dependency or application-code change.
