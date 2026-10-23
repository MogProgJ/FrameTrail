# Expanded billboard task: data revision first

The user clarified that restaurant/business identity boards count as billboards, along with hotel/restaurant promotional boards. The earlier narrow task excluded those boards. Some old “false alarms” therefore match the intended product category, and some negative labels conflict with it. This is a supervision/specification mismatch; the old numerical results remain valid only for their frozen narrow task.

TASK_DEFINITION.json freezes the broader working rule before new labels. All323 eligible photos are queued uniformly:124 fresh-role photos,64 old TRAIN replay photos,135 old validation photos. No model fitting/inference or TEST scoring is part of this stage. Human feedback sets the product scope; the image annotations remain assistant reviews, not independent human gold.

The new draft must review every photo for complete class133 labels, including positives that may contain additional identity panels. Existing narrow labels/results remain archived. Other classes remain unchanged or unknown. Dedicated business/venue/service identity panels are included; ordinary traffic regulation and operational transit displays stay excluded. Ambiguous mixed cases are recorded as unresolved rather than forced absent.

After review, count role-specific positive/absent shortfalls before preparing any acquisition. Do not lower the original minima or replace photos based on scores. Prefer unused locally available candidates with their preassigned roles/source/scene evidence if additions are necessary. No new collection or training job has been prepared or submitted.

Both original/current baseline models and historical metrics are retained. A versioned expanded-label baseline/retention plan must explicitly handle class133 semantic conflicts and keep cap530/other-class guards; this document does not waive any gate. No old model can be declared qualified by relabeling its errors.

Next step: complete the expanded-definition original-image annotation audit, because training against the previous narrow negatives would teach the wrong task.
