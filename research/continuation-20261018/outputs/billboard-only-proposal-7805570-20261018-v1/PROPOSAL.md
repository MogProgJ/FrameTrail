# One proposed billboard calibration job

**No cluster approval has been recorded and no new job has been submitted.**

## Exact proposed scope

- One A100 on KIT partition `gpu_a100_il`, two CPUs, at most 45 minutes of Slurm wall time and 30 minutes of active process time. No automatic retries or replacement jobs.
- Start from job **7805570, selected step 100**, checkpoint SHA-256 `c1e7b571476a9bdc02533359dfe3f599afab98822aa90df265e9068f43f46bd3`.
- Train **only classifier row 133, billboard**. Freeze washing machine, cat, dog, every other classifier row, all features, encoder and box regressors, with tensor/gradient checks.
- At most **3,000 updates / 12,000 image presentations**. Each update accumulates one billboard-positive photo and three distinct explicitly billboard-absent photos.
- Use only the existing sealed 700-photo training partition: 20 billboard-positive photos and 35 explicitly absent photos. No new labels, inferred negatives, photos, vocabulary, or thresholds.
- Fresh AdamW at learning rate 0.0001, weight decay zero, gradient clip 0.1, fixed seeds, FP32/math attention, model eval mode, accumulation four. No optimizer state was saved in the starting checkpoint.
- Validate on the unchanged 135 development photos at step zero and every 100 updates. Stop at step 1500 if no eligible strict gain has been selected; otherwise continue to step 3000.

## Why this is the next model experiment

The selected model improved washing-machine detection, but billboard remains 0/11 known validation targets and 0/19 known held-out targets. The rejected step-2000 state detected 7/11 validation billboard targets, accompanied by one measured billboard false positive and 41 unscored billboard predictions. It is not a replacement candidate.

An eight-photo, training-only diagnostic compared the selected and rejected states without an optimizer or parameter updates. Three of the four positive photos had covering queries; matched confidence increased with the later training. The explicit negatives generated suppressive billboard gradients. One positive photo has two targets without a query covering them at IoU 0.5; a frozen-box experiment cannot repair those locations. This small diagnostic supports a bounded calibration hypothesis, not a guarantee of improvement.

The proposed change raises the negative share from two to three explicitly absent presentations per update, focuses all permitted updates on billboard, and freezes the washing-machine gain. It does not causally isolate every effect of the new sampling and budget.

## Selection and evaluation limits

Against both the current selected model and the original job-7780632 step-zero baseline, every reviewed class must retain complete true positives and partial known-positive hits, without increasing complete-scope false positives. Aggregate unscored predictions may increase by at most five against either baseline; these predictions are not measured false positives. Because the current baseline has 528 unscored predictions and the original has 525, the effective cap remains 530. A strict validation ranking gain is required; ties retain step zero.

The 130 photos and reserved 24 video frames have now been scored and are **known regression evidence**, not a fresh test. Keep all older regression references too. A future experiment cannot claim a new independent generalization result from these reused sets. Further independent frozen evidence is needed for that claim. Do not reselect checkpoints from regression outcomes.

This proposal does not resolve the separate strict numerical ONNX-export hold. The new local app build provides an explicit preview while retaining the existing default and documenting that hold. Model training is not a repair for export-runtime numerical differences.

## Prepared and checked

- 2,921 sealed files, 965 photos and all 3,000 fixed sampling batches verified.
- Five CPU contracts passed, including exact schedule, missing-approval rejection, early-stop behavior, baseline retention and a synthetic update proving that only row 133 can change.
- Local pinned-runtime and starting-checkpoint metadata preflight passed; no real model optimizer update or GPU inference occurred.
- Bash syntax checks passed. Local fake-Slurm cases passed for preflight failure, repeated normal submission and ambiguous submission response; each latter case called mock sbatch only once.
- Helpers use the already verified Base64 SSH transport, load the existing pinned KIT module/overlay, and structurally compare returned JSON sampling values to the sealed original rather than comparing platform-dependent JSON formatting.

The executable draft is `rf-billboard-716ca2cf-v1`. Protocol SHA-256: `716ca2cf411984698e6d096f00fd5ef01995bee9ed4fe0c82a742e26c4bc6e1c`. The actual approval file is intentionally absent. `Launch-Approved-Run.ps1` stops before archive creation or SSH while it is absent. After approval, the archive is created exclusively from the verified seal plus the separately recorded approval, then transferred for one idempotent submission.

Next step: approve this one bounded cluster job, because it tests billboard learning while protecting the current washing-machine and retention gains.
