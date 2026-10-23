# RF GPU preview and FrameTrail agenda — 2026-10-16

## Playback diagnosis and delivered change

The user supplied two recordings: `RF-DETR.mp4` and `Recording 2026-10-16 222457.mp4` in Downloads. Their app status bars show CPU and about 461.7 / 370.0 ms per detection frame. Preview decodes and detects in sequence, so expensive inference limits presentation. The original experimental RF integration intentionally disabled GPU pending output verification.

The exact trained checkpoint is unchanged: KIT 7758628, update 1200, checkpoint SHA-256 `1b72fc6474780a6805e919db5b1393d7e78b95209debafafce98c929c633f0d7`. The ONNX export remains `5a5ea0754c11cb664a1b5962efb40071173a6b837e8cbcc490617c4cd227a1f5`.

Native DirectML inference on this PC's NVIDIA GeForce GTX 1650 Ti (4 GB) passed six raw-output/decoded probe comparisons and six full native preprocessing/inference/decoding comparisons against the checkpoint references. GPU loader verifies profile, vocabulary, learned-checkpoint hash and preprocessing metadata. CPU fallback remains explicit when GPU initialization/execution fails. The automatic adapter chooser selected the GTX rather than Intel UHD.

Warm GPU inference measured about 47–50 ms on the diagnostic probes; initial session creation took about 4.3 seconds. Full Qt preview, including decoding, preprocessing, tracking and drawing, presented 120 contiguous frames from each real source video at **14.2 fps daytime / 14.3 fps nighttime**, confidence 0.65. These offscreen measurements exclude initial loading and apply to this computer. Each presented source frame used its own detections; there is no frame skipping or reuse of older boxes. Video still runs slower than the original 25/30 fps. Do not describe it as full real-time playback or claim all lag is eliminated.

## Launch

Close the old app window and run the existing `out/FrameTrail-RF7758628-experimental/Run-RF-Experimental.cmd` launcher; it now forwards to the separate GPU preview package. Or run `out/FrameTrail-RF7758628-GPU-experimental/Run-RF-Experimental.cmd` directly. The RF flag selects GPU with CPU fallback. Actual execution is shown as GPU/CPU in the bottom status bar. Ordinary startup without the RF flag retains the existing default model.

Old app binaries remain preserved. Seven changed source files and the previous launcher are backed up in `C:\Users\nazee\.codex\visualizations\2026\10\15\01a141ae-c7a6-7303-a280-403af88736f3\rf-playback-7758628-v2\originals`. No annotations, videos, checkpoint weights or existing saved analyses were changed.

## Verification

15 backend/detection/preview/CLI/saved-run/desktop regression checks including fixtures passed. GPU preview, video analysis, save, CSV export, actual-provider persistence and read-only reopening passed. CPU fallback, cancellation and rejection of the wrong RF checkpoint were checked. Full evidence: `C:\Users\nazee\.codex\visualizations\2026\10\15\01a141ae-c7a6-7303-a280-403af88736f3\rf-playback-7758628-v2`. Initial interrupted builds and a post-build DLL copy collision were corrected before successful final checks; do not rerun one-shot preparation scripts on their existing outputs.

## Where we stand

We have a working native app, a genuinely trained experimental RF checkpoint, verified CPU/GPU exports and execution, assisted annotation tooling, and more positive hits on some reviewed objects. The candidate still failed adoption gates because false positives increased. Local app integration and faster inference do not repair those quality failures. The 12-photo calibration audit has not been trained into these weights.

The training release has 281 training photos, 704 reviewed boxes and 115 categories with training positives, within a 615-label registry. Fine-tuning supervision includes 6 cat boxes, 10 dog boxes and 4 lantern boxes. These counts exclude pretraining. `category-coverage.csv` records all categories across train/validation/test.

## Agreed agenda

1. **Playback performance first:** GPU preview is now available and substantially faster. Source-rate 25/30 fps remains an open performance target. If full smooth playback is required on this hardware, a separately designed pre-analysis/cache playback mode can preserve every frame and exact boxes; an asynchronous sampled overlay would require explicit handling of stale results. Neither mode has been silently introduced here.
2. **Strengthen weak existing categories AND expand the dataset together.** Both are priority streams for the next data release. Repair cat/dog confusion, lantern coverage and known false-positive classes using varied real scenes and reviewed positive/negative/completeness scopes. In parallel, choose priority underrepresented and genuinely missing categories, define them precisely and collect diverse independently sourced examples. Expansion has not been dropped or deferred indefinitely behind repairs.
3. **Review proposals and retain old strengths:** use automatic box proposals plus correction, add missed objects, preserve unknown labels as ignored. Mix new data with representative existing examples and retain useful person/vehicle capability. A detector's confident mistake must not become an accepted training label automatically.
4. **Measure on real videos:** freeze independent references before another experiment. The generated 29956a31 clip and these two real clips are now known diagnostic/development material, not fresh tests after fixes. Compare original RF, the current checkpoint and the next candidate. Protect all reviewed category scopes, not only the pretrained 80, and constrain false positives as well as positive hits.
5. **Train after a concrete release/protocol:** prepare a bounded experiment with explicit data/scope changes and validation criteria. No new acquisition cohort or GPU training job was launched by this performance task. Do not select a checkpoint or threshold using held-out outcomes.

The greatest model-quality need is balanced, reviewed supervision and stronger false-positive control per priority category. Increasing update count alone is not an evidence-based fix. Dataset expansion remains a first-class requirement alongside quality repair.
