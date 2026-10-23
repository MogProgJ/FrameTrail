# Proposed next run: balanced two-class head continuation

**Proposal only; not approved, implemented as a training runner, or submitted.**

Continue from job 7780632's final checkpoint (old step 600), not its selected step-0 checkpoint and not the app's installed weights. Use a fresh AdamW optimizer because the old checkpoint contains no optimizer state. Only the final **billboard and washing-machine classifier rows** may change. Cat/dog rows, every other row, encoder classifier, features and all box heads stay frozen and bitwise checked.

- **Maximum:** 2,000 updates, accumulation 4, 8,000 image presentations; stop at update 1,000 if no eligible strict validation gain has been selected.
- **Learning rate:** unchanged at 0.0001; AdamW, zero decay, gradient clip 0.1, no AMP. This proposal does not simultaneously raise the learning rate or replace the loss.
- **Sampling:** each update has one photo from the 20 known-positive billboard training photos, one from the 21 washing-machine training photos, and two from the **35 training photos explicitly reviewed absent for both**. Preserve every existing target and scope. Frozen sampler seeds and the exact 2,000-update schedule are included.
- **Resources:** one A100 GPU, two CPU cores; at most 30 minutes of active-run elapsed time and a 45-minute Slurm allocation; no retries or downloads.
- **Checks:** validate at step 0 and every 100 updates. Keep confidence .35, NMS .45, matching IoU .5, top 300 pairs and maximum 100 detections. Retain all 72 reviewed classes' no-regression guards and the unscored-prediction drift alarm. Check against both the continuation baseline and the original trial baseline. Exact ties keep the earlier checkpoint.
- **Reserved evidence:** freeze/hash a strict improving candidate before using the existing 130 held-out photos and 24 reserved video frames. Export and app adoption remain separate gates; neither is automatic.

Why this is the narrowest supported next experiment: usable boxes already exist, both new classes retain upward classification gradients, and the original mixed sampler gave them only 217 and 226 positive-photo presentations. The proposal concentrates positive exposure while keeping the architecture, loss, learning rate and detection thresholds unchanged. Improvement is uncertain; the schedule repeats a small training set and can overfit. This is an optimization attempt, not a promise that more updates will solve recognition.

The protocol identity is `ddbb57c60855b5499ecdc039642fb5fd527634767e0575507e15b5774131e8c1`. `proposed-sampling-pools.json` and `proposed-sampling-plan.json` are hash-pinned in the protocol. A separately authorized implementation must verify the starting checkpoint hash and every sampler ID/asset before execution.

Separate GPU approval is required because `approval.json` for the completed run authorized exactly one four-classifier-row, 600-update trial and explicitly disabled automatic retries and application adoption. The new proposal changes the trainable rows, starting checkpoint, sampler and update budget. The current instruction authorized a read-only loss/gradient check and preparation of a proposal; it did not approve this new GPU job.
