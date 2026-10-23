# Separate local export and parity stage

The held-out evidence gate for job 7805570 step 100 passed against both pinned baselines. Washing-machine known-target hits on the 130 held-out photos rose from 0/15 to 3/15; billboard remained 0/19. All reviewed-class retention checks across six reference sets passed. This is a modest gain on small, assistant-reviewed evidence, not broad accuracy certification.

## Exact proposed work

1. Load only the selected checkpoint SHA-256 `c1e7b571476a9bdc02533359dfe3f599afab98822aa90df265e9068f43f46bd3`.
2. Export a new ONNX file under this preparation folder's exclusive `export-output-v1` directory. Preserve every existing checkpoint, model and app file.
3. Check raw boxes/logits on six reference-selected probes and decoded detection parity on all 202 unique images already evaluated. Use the existing RF parity tolerances: identical detection count and canonical classes, matching IoU at least 0.99, confidence difference at most 0.002, and normalized coordinate difference at most 0.002. Raw NumPy allclose uses rtol 0.0001 / atol 0.002.
4. Measure ONNX Runtime CPU forward latency with two CPU threads on the six fixed probes, two warmups and five measured calls each. This measures model runtime only; native GUI end-to-end performance remains a later gate.
5. Record output checksum, dimensions, checkpoint identity, parity results and latency. Stop if parity fails.

Input shape is `[1,3,512,512]`; output is `[1,300,619]`, consisting of four normalized box coordinates followed by 615 canonical foreground logits. The original extra background slot is omitted, following the existing native RF contract. The proposed experimental profile is `rfdetr-7805570`.

The sealed EXPORT_PLAN.json pins 410 input files and eight code/module files. It includes the exact six raw parity probes, installed dependency versions and expected output contract. Six synthetic parity contracts passed, covering permutation, empty results, detection count, class, confidence and geometry changes. Syntax checks passed for every prepared Python file. The export script checks the passed held-out decision before model export and requires a separate approval record bound to the plan checksum.

## Scope boundary requiring input

The frozen training protocol explicitly records `"automatic_export": false` and `"automatic_application_adoption": false`. A byte-identical copy is retained as frozen-training-protocol.json. The latest user instruction authorized the recommended held-out evaluation and continued preparation; this proposal makes the next distinct stage reviewable before permission is requested.

Requested approval is limited to local ONNX export, parity checks, and CPU model-runtime measurements. There is no new GPU job, optimizer update, model download, visible app launch, installation, or app adoption in this stage.

Next step: approve this exact local export/parity stage, because the selected checkpoint must preserve its detection behavior in the app-compatible model format before native performance or application adoption can be considered.
