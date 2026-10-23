# FrameTrail audited result and next experiment

Array7809335 is complete, downloaded and independently audited. All four tasks stopped at1500updates under the approved no-gain rule. All selected step0, whose model tensors equal job7805570step100. No returned model was adopted. Replayed64validation records and checked all best/last model tensors, schedules and selection decisions. The four tasks used43min31s aggregate allocation time (about0.725GPUhours), below the3GPUhour requested ceiling.

The main-head trials learned billboard detections (maximum training-run validation hits7,5,9,7 of11), but each improving checkpoint failed existing guards. Unknown-region predictions are unscored predictions, not measured false positives. The tight aggregate cap is530 because the original baseline525+5 is stricter than the current baseline528+5. Measured false positives also included regulatory signs.

Seventeen additional local heads tested uniform/hard-negative weighting, eight reviewed sign regions, teacher preservation on645otherwise-unknown TRAIN photos and a training-only RMS constraint. None passed strict-gain selection. All used exact cached frozen features or training-only sufficient statistics; no extra cluster jobs. This is development exploration, not fresh independent accuracy evidence.

Two matching frozen-selector controls were then run locally for1500updates each (one positive, two explicit negatives and one reviewed sign-region photo per update). Their32validation records and3000update traces were independently checked:

| Sign penalty | Updates | Final billboard hits | Measured complete FP | Final unscored | Selected |
| --- | --- | --- | --- | --- | --- |
| 1 | 1500 | 5/11 | 0 | 552 | step 0 |
| 3 | 1500 | 4/11 | 0 | 550 | step 0 |

Training-only geometry inspection finds encoder proposals covering52/54targets before top300selection,36/54after selection and37/54in final decoder boxes. This supports a proposal-selector experiment; it does not prove that selector training will improve accuracy. No fresh test images were used to choose this mechanism.

## Exact proposed cluster scope — NEW approval required

One upload/launch, one Slurm array0-3%2 on gpu_a100_il. Four trials: encoder billboard learning rate0.00001or0.00003 crossed with sign-region negative penalty1or3. Main billboard learning rate0.0001 throughout. Start the unchanged selected job7805570step100 checkpoint. Update only row133 in main and encoder proposal classifiers. All other rows, including washing machine, and all backbone/transformer/box-regressor parameters and buffers remain bitwise frozen. Changed proposal selection can change decoder features, box outputs and other detections.

Objective adds dense encoder billboard classification on the full proposal grid to the existing scoped main/aux/selected-encoder objective. Geometry Hungarian matches require IoU>=.5. The eight assistant-reviewed TRAIN sign panels supply billboard-negative queries at IoU>=.7 only within each panel; all outside scope remains unchanged. Original965photo release labels/scopes are preserved. No new downloads, test labels or whole-image absence claims. Same paired schedule: one positive +two distinct explicit negatives +one region photo each update (63distinct existing TRAIN photos).

Each task requests oneA100, twoCPUs,8GiB and45minutes wall time, bounded to3000updates,1800seconds training process and480seconds known regression. Stop at1500if no qualifying gain. Four tasks total<=12000updates,48000presentations, two concurrent GPUs and3aggregate requested GPUhours (2hours summed training process caps). No retries, requeue or replacement jobs. Failed/partial archives are retained.

Validation step0and every100 on the same135development photos. Same confidence.35/NMS.45/IoU.5 and both-baseline per-class retention/unscored+5 guard. Select by validation ranking only; earlier step/lower index wins ties. Score any frozen selected candidate automatically on202unique known-regression images/six references. Regression may veto adoption but never select a different trial. Step0 reuses current scores. Download all four tasks with one batch SFTP command, then structurally verify, independently rescore and audit both active rows/all frozen tensors locally.

Two cacheable controls have already run on CPU; the four new trials require fresh forward passes as encoder selection changes. Additional learning-rate/grid jobs would increase selection pressure before this mechanism shows a benefit. Account entitlements are not assumed: the approved launcher records authenticated scheduler/account evidence and requires sbatch --test-only before a single submission. No authenticated check has been performed for this NEW proposal yet.

Protocol SHA256: a77d9663fcc898b6a257f6722dd37bc24b1d3a2d3065eb8cce5f0625403f019a. Code/asset seal is package-files.json. New approval is absent; no transport archive, SSH, upload or submission has occurred. Earlier four-trial authorization applied to completed array7809335 and does not authorize this changed mechanism/region overlay.

Existing model remains job7805570step100: known washing3/15 and billboard0/19. Strict ONNX numerical qualification remains held; the explicit native preview is available, default YOLOX-S preserved and production_adoption=false. Known references are consumed, and fresh independently frozen evidence is still needed for a generalization claim.

Standing instructions: recommend the concrete next step at the end of every response; continue all authorized local audits/exports/parity/CPU benchmarks/reversible integration/packaging/fixes autonomously; pause before NEW cluster scope submission; batch useful independent work and preserve failure evidence. Do not launch a visible GUI without request. Never ask for pasted credentials. Preserve earlier receipts.

Next step: obtain explicit approval for this exact four-trial selector batch, because preparation and local controls are complete and posting a new cluster job is the remaining user decision.
