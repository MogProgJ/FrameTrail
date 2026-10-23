# Next diagnostic: training-only classification signal

Status: prepared, not executed. This is a proposed read-only CPU gradient diagnostic, not approval for a GPU training run.

1. Use only the frozen IDs and hashes in `training-diagnostic-sample-selection.json`: two known-positive and, where available, two explicit-absent training photos per active class. Keep all existing targets and scope masks. The deterministic sample is for debugging, not a representative evaluation.
2. Load the same pinned model at step 0 and step 600. Keep eval mode, group one, the original 512×512 preprocessing, math attention, and all feature/box/encoder parameters frozen. Enable gradients only for the four previously approved final classifier rows.
3. For each sample, run the sealed scoped criterion. Record matched query IDs and IoUs, per-target class probabilities and IoU-aware soft targets, total target count used for normalization, individual loss components and the weighted total. Record each active row's gradient norm and direction at its matched positives. Distinguish frozen auxiliary/box losses from losses that can update the permitted head.
4. Check that explicit-negative scopes contribute suppression, unknown scopes contribute no direct logit gradient, and inactive classifier rows remain gradient-masked. Compare the recorded total against the sealed loss implementation; do not replace the objective during this check.
5. Do not create an optimizer or perform any parameter update. Verify parameter tensors and checkpoint hashes before and after. No test/validation-based hyperparameter tuning, model export, app change, new model download or remote job.
6. Use the resulting signal and `training-exposure.json` to prepare the narrowest next optimization proposal. If classifier gradients remain useful, consider a bounded classifier optimization budget/learning-rate change before expanding trainable model components. Preserve per-class retention guards and leave held-out data for a frozen useful candidate. A new GPU trial needs separate scope approval.

Why this comes next: every one of the 24 new-class validation targets already has a distinct decoder query with IoU ≥ .5. The measured failure is inadequate class confidence on those queries, so wider box-head training is not supported by this probe.
