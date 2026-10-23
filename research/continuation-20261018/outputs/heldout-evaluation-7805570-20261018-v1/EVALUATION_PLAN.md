# Frozen evaluation of job 7805570, selected step 100

The user authorized the recommended held-out evaluation and continued work until input is required. This run performs local CPU inference only, with no optimizer, additional GPU allocation, checkpoint reselection, threshold tuning, export, or application adoption.

The three fixed models are the original job-7780632 step-zero baseline, that job's step-600 continuation baseline, and the independently audited job-7805570 step-100 candidate. Checkpoint SHA-256 values are fixed in evaluate.py and recorded in evaluation-lock.json before any inference.

The primary held-out evidence is the unchanged 130-photo test partition and the reserved 24 real video frames from six sequences. Older internal photos and three older video reference sets are retained as known regression evidence. Exact duplicate image bytes across reference sets are inferred once per model, then scored against each applicable unchanged reference.

The common RF pipeline uses 512×512 normalized RGB, FP32, PyTorch 2.8.0 CPU, RF-DETR 1.11.2, math attention, confidence 0.35, class-wise NMS IoU 0.45, top 300 class/query pairs, maximum 100 detections, and same-class matching IoU 0.5. The already-used scoped video scorer supplies separate complete and partial denominators. Source references are preserved; derived adapters add scorer metadata and translate the photo manifest's existing boxes and scopes without changing labels or completeness.

For every reference and class, the candidate must preserve complete true positives and partial known-positive hits and must not increase measured complete-scope false positives against either baseline. It must also show a strict total known-positive gain over both baselines on the primary photo/video evidence. Unmatched predictions in unknown scopes remain unscored. An evidence-gate pass only establishes eligibility for separate export, parity, and performance checks.

All source file and image hashes are checked before and after inference. All model state tensors are fingerprinted before and after inference. Per-image output receipts bind the exact checkpoint, image bytes and evaluation lock. Interrupted work may resume only with matching identities; previous outputs are preserved.

The six synthetic scoring contracts passed before preparation. They cover complete/partial/unknown denominators, duplicate matching, per-class retention, newly appearing false-positive classes, photo scope conversion, and missing image output.

These are small, purposive, assistant-reviewed references, without independent human recheck. The new photo labels were previously assisted by proposal evidence. Source, session and pretraining independence remain unproven. This evaluation does not estimate representative overall accuracy, full-vocabulary AP, tracking accuracy or statistical significance. Once scored, the reserved evidence must be treated as consumed regression evidence in future cycles.

Next step: complete the locked three-model comparison, because checkpoint-selection validation cannot establish generalization or retention on unused evidence.
