# FrameTrail: efficient batch replaces single-trial proposal

Latest user instruction: prepare useful independent trials and automatic checks together before each cluster submission. This preference is saved in global, FrameTrail, Codex and continuation AGENTS.md files and explicitly confirmed in the latest user-provided AGENTS.md.

The unsubmitted single-trial draft is preserved. The new latest proposal is `C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\outputs\billboard-batch-proposal-7805570-20261018-v1\PROPOSAL.md`. No approval, upload or new job exists. Exact scope: one four-task array `0-3%2`, one A100/two CPUs/8 GiB/45 minutes per task, maximum two concurrent A100s, three aggregate requested GPU-hours. Each task has <=3000 updates, <=30 minutes training-process time and <=8 minutes automatic consumed-reference processing. No retries or replacements.

Matrix: positive:explicit-negative ratios 1:1 and 1:3, each at learning rates .0001 and .0003. Paired image schedules and one common input package. All start selected job7805570 step100; train only classifier row133. Everything else, including washing-machine gain, is frozen. Validate every100; stop at1500 if no eligible gain. Preserve guards against current and original baselines. All four selected checkpoints freeze before known regression; zero-gain tasks reuse current baseline scores. One Check and one Retrieve cover all four tasks and preserve failures.

Twelve CPU/structural tests and six local fake-Slurm/entry tests passed; five PowerShell5.1 helper syntax checks passed; all 3015 sealed files match. Tests used inert fixtures and synthetic optimizer heads, not real model training or GPU inference. Mock job123456789 is never a real KIT job. Actual approval.json is absent and launch blocks before packaging/SSH.

Account maximums are NOT yet verified. Authenticated launch records scheduler/account evidence and executes sbatch --test-only before the single real sbatch. Stop if rejected; do not automatically change scope or submit replacements. The requested two-GPU concurrency is a cap, not a guarantee of simultaneous scheduling or a claim to account entitlement.

Existing model evidence: selected step100 improved known washing-machine targets0/15 to3/15, billboard0/19. Strict numerical ONNX gate remains FAILED (three confidence cases above.002, three raw-array probes fail), though202-image scoped results match. Explicit native preview remains available in the sibling native-balanced folder; standard default YOLOX-S is unchanged. No production promotion. GPU training is separate from fixing numerical export qualification.

After retrieval the built-in validation-only comparison is provisional. Independently rescore validation predictions, replay selection against both baselines, inspect frozen/inactive tensors for best and last checkpoints, and independently replay known-regression reports locally before accepting any winner. Do not choose a different variant based on consumed regression. Any failure holds adoption; no automatic new job. Local audit/export/parity/integration are already authorized. Additional independent frozen evidence is required for a new generalization claim.

Next step: approve the complete four-trial scope, because it collects a controlled calibration comparison and regression evidence in one cluster submission.
