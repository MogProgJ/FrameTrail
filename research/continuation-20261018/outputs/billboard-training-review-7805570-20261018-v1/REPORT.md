# Billboard training-only review

Eight fixed training photos (four positive, four explicitly absent) were inspected at the selected step-100 and rejected step-2000 states. Sixteen CPU forward/backward checks used no optimizer and made no parameter updates. Input hashes and complete model-state fingerprints stayed unchanged. Validation and held-out images were not used in this diagnostic.

At step 100, median maximum billboard probability was 0.0730 on positives and 0.0447 on explicit negatives. At the rejected step 2000 it was 0.5717 and 0.1009 respectively. Three of four positive photos had queries covering their known targets at IoU >= 0.5. The remaining photo's two targets had no covering queries, which a frozen-box experiment cannot repair. Explicit negative images generated suppressive gradients on the permitted billboard row.

This supports a bounded calibration hypothesis: try a higher explicit-negative share while training only billboard and freezing washing machine. It does not guarantee improvement or causally isolate sampling from budget changes. Step 2000 remains rejected and cannot replace the selected model.

The draft proposal uses one positive plus three distinct explicit negatives per update, drawn from the existing 20-positive/35-negative training pools. It retains both current and original validation guards. No new labels, data or thresholds are proposed.

Next step: approve the bounded single-row GPU proposal, because this small diagnostic identifies a plausible learning signal while explaining its limitations.
