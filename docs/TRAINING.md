# General recognition: datasets and training

Updated: 4 October 2026. Dataset/training tooling stage 0.13; the desktop application remains 0.12.

The product goal is broad everyday-object recognition. Fox/dog, low light, small objects and occlusion are difficult evaluation slices within that goal. They do not define the application's scope. RF-DETR Small is shortlisted as a challenger to the YOLO baseline.

No finite detector can promise every possible object in every scene. The practical path is measured coverage across useful domains, a stable category vocabulary, and later evaluation of open-vocabulary models for categories outside it. A wider vocabulary alone does not establish correct recognition.

## What this stage implements

| Module | Responsibility |
| --- | --- |
| [Scope](../training/scope.json) | Six everyday-object domains, bounded sampling budgets, hard evaluation slices and model shortlist |
| [Dataset catalogue and validation](../scripts/training_data.py) | SQLite indexing, source attribution, exact vocabulary, box validation, source-group splits, hashes and duplicate checks |
| [Dataset commands](../scripts/prepare-dataset.py) | Explicit index/sample/export steps; metadata-only selection unless image fetching is requested |
| [Training runner](../scripts/train-detector.py) | Preflight, pinned publisher warm start, bounded smoke mode, reviewed-data gate, experiment identity and checkpoint hashes |
| [Training export](../scripts/export-trained.py) | Full-vocabulary ONNX export with provenance; no installation into the GUI |
| [Native reference check](../scripts/check-recognition.py) | Optional trained artifact comparison on CPU/DirectML using the existing numerical/label guards |
| [Cluster job template](../training/run-cluster.sbatch) | One GPU, explicit paths/environment and preflight; requires an account-permitted partition |

These are offline Python developer tools. Playback, detection, tracking, storage and the accepted saved-analysis interface continue to run through the existing C++ application. No camera, Python inference service, cloud account or new GUI is involved.

## Dataset choice and coverage

The first source is [Open Images V7](https://storage.googleapis.com/openimages/web/download_v7.html). Its box annotations and image attribution metadata support a traceable sample across people/transport, furniture, kitchen/food, electronics/work, personal/outdoor objects and animals. All 601 raw publisher labels remain in the training head; the existing canonical mapping groups these into 597 application categories. The 96-image sampling budget is a mechanical starting point, not sufficient general-recognition training data.

The catalogue indexes the available metadata before downloading images. It reports per-class annotation counts, including zero-coverage classes, and stores the original source, author, license, box attributes and source-file hashes. Image retrieval is explicit and byte-bounded. Selection rejects source images with unsupported group/depiction annotations or uncertain rotation, and excludes the earlier recognition reference images.

The current sample uses publisher **validation** data and has incomplete labels. It is deliberately restricted to a mechanical smoke run. It must not become our production training set or an independent field-accuracy test. Open Images does not exhaustively annotate every class in every image; converting missing labels into background can punish correct predictions. See the [official evaluation policy](https://storage.googleapis.com/openimages/web/evaluation.html).

Full training needs source-train data or permissioned new examples with reviewed complete target labels, plus independent validation/test footage. Retaining the whole head prevents accidental vocabulary removal, but cannot guarantee preservation of each category's accuracy. Broad coverage/replay and per-domain regression evaluation remain necessary.

Source-author groups stay together in deterministic 60/20/20 partitions. This is a conservative grouping for public photographs, not proof of camera independence. For footage, use real camera/site/session groups. Exact file hashes and 64-bit difference hashes detect obvious duplicates; this simple perceptual check is not a complete crop/video-neighbour leakage detector. Lighting remains unreviewed until labelled; average brightness is recorded but does not establish night imagery.

## Local commands

Use a dedicated Python 3.12 environment for training. The existing optional recognition environment was reused for the bounded CPU validation; no packages were changed during this stage. For a new CPU environment, install the pinned CPU PyTorch/torchvision wheels, then [requirements-training.txt](../scripts/requirements-training.txt). Linux GPU training needs the corresponding CUDA wheels after checking the allocated driver. These environments are separate from the packaged desktop runtime.

```powershell
$taskPython = ".\.deps\recognition-python\Scripts\python.exe"

# Index already acquired official source metadata; keep raw source files outside Git.
& $taskPython -B scripts/prepare-dataset.py index `
  --boxes <boxes.csv> --classes <classes.csv> --metadata <image-attribution.csv> `
  --publisher-split train --output output/training/catalogue.sqlite

# Metadata-only by default; add --fetch-images for bounded explicit acquisition.
& $taskPython -B scripts/prepare-dataset.py sample `
  --catalogue output/training/catalogue.sqlite --output output/training/sample

# After label/rights review, export a new immutable YOLO + COCO bundle.
& $taskPython -B scripts/prepare-dataset.py export `
  --manifest <reviewed-manifest.json> --output output/training/reviewed-bundle
```

Export refuses incomplete review for a substantial run. `--smoke` explicitly permits unreviewed labels only for a mechanics test and tags the bundle accordingly. Training mode cannot use that bundle. The runner defaults to preflight; `--run` is required to start compute. A smoke run is limited to one epoch and at most 256 images. Existing output directories are preserved.

The reviewed manifest records per-image `review.complete_target_classes`, `review.rights_verified` and lighting, and permits box corrections before creating a new bundle. Those flags must represent actual review, not a bulk switch to bypass readiness. New bundles record all content hashes. Preflight rejects changed files, extra images, split leakage, changed class order, redirected data paths and embedded downloader instructions.

Completed local validation artifacts are under `output/training-0.13/`:

```powershell
& $taskPython -B scripts/train-detector.py `
  --dataset output/training-0.13/general-smoke-bundle `
  --config training/general-smoke.json `
  --weights .deps/world-export/weights/yolov8s-oiv7.pt --mode smoke

# Actual run: add --run --output <new-experiment-directory>.
# Export afterward to a new path, leaving application models untouched:
& $taskPython -B scripts/export-trained.py `
  --experiment <experiment-directory>/experiment.json --output <new-candidate.onnx>
```

The existing broad profile accepts this export because the full input/output contract and exact 601-label order are retained. Arbitrary smaller heads and RF-DETR require explicit native adapter/profile work. Do not relabel an incompatible graph as `openimages` or replace the app's default weights with an unevaluated checkpoint.

## Evidence from this stage

The official validation catalogue contains 41,620 image records, 303,980 boxes and annotations for 570 of the 601 raw labels. The frozen sample contains 96 images, 447 boxes and 132 canonical categories; domains contribute 15–18 selected images each. It downloaded 27,976,859 image bytes, below the explicit 150 MB image budget. Source-group partitions contain 70 training, 11 validation and 15 untouched test images. No exact/near duplicates were rejected in this selection. These are sample statistics, not coverage of all categories or independent accuracy evidence.

A CPU run performed one epoch at 320 pixels, batch 2, with the first ten backbone modules frozen and all 601 output labels retained. It produced best/last checkpoints. The final verified run took about 20.7 seconds and records source hashes, environment versions and local cache paths. Loss and validation metrics from this small, partially annotated publisher sample are not reported as product accuracy or improvement.

The best checkpoint exported at native 640-pixel resolution to float32 batch-1 ONNX, opset 17, output `[1,605,8400]`. Across three training images, two strong reference detections matched native CPU and DirectML results with box IoU above 0.999 and maximum score difference below 0.0014. Incorrect vocabulary metadata was rejected on both backends. This checks integration; it does not validate every class. The original packaged models and saved-analysis interface remain unchanged.

All 29 Python contract checks passed, including immutable bundle validation, split leakage, review gates and training preflight. See [aggregate evidence](benchmarks/training-0.13.json). Dataset photos, author metadata, checkpoints and local analysis files are ignored by Git.

## bwUniCluster handoff

For a beginner-friendly sequence using the available Python module and a prepared upload archive, follow [the KIT quickstart](KIT_CLUSTER_QUICKSTART.md). The user has now completed an A100 80 GB diagnostic job successfully; actual Linux environment installation and GPU training remain pending.

The user supplied `uc3.scc.kit.edu` and confirmed that login requires an interactive password and OTP. No credentials or account names are stored here. No cluster login or job submission was performed. Authenticate in your own terminal, then verify the account's permitted GPU partition, storage lifetime, and CUDA environment. [bwHPC documents the job policy](https://wiki.bwhpc.de/e/BwUniCluster3.0/Running_Jobs) and [supported container environments](https://wiki.bwhpc.de/e/BwUniCluster3.0/Containers).

Transfer the repository, one bundle, the pinned publisher checkpoint and the environment lock to a persistent project/workspace directory. Export `FT_ROOT`, `FT_PYTHON`, `FT_DATASET`, `FT_WEIGHTS` and a new `FT_OUTPUT`. Submit `training/run-cluster.sbatch` with the permitted partition. `FT_MODE=smoke` and `FT_CONFIG=.../training/general-cluster-smoke.json` select the short GPU setup test; override wall time to fit the development queue. Defaults select reviewed training, and fail preflight on the current smoke bundle. Do not execute compute-heavy work on the login node.

The Slurm script is prepared but has not been executed on KIT. CPU smoke success does not verify the Linux/CUDA job. Persist checkpoints and retrieve the chosen artifact/report before scratch storage expires.

## What comes next

1. Acquire/index publisher train metadata in a bounded staged workflow and curate broad examples plus hard-case supplements. Review target completeness and rights; add real camera/site information and stronger duplicate checks where appropriate.
2. Freeze independent real-world test data spanning the six domains and difficult conditions. Add full per-class precision/recall/AP and per-domain regression evaluation; measure confidence using validation only.
3. Run the authenticated single-GPU setup test and then a budgeted reviewed-data fine-tune. Compare against the unchanged broad model and people/vehicle baseline before adopting any artifact.
4. Evaluate shortlisted RF-DETR Small on the same reviewed dataset if useful, with its own preprocessing/output adapter and CPU/GPU resource measurements. Its [custom training](https://rfdetr.roboflow.com/latest/learn/train/) and [ONNX export](https://rfdetr.roboflow.com/latest/exports/onnx/) paths are documented, but no RF-DETR model has been installed or trained here.

Broader future datasets require taxonomy alignment and label/license checks before merging. Open-vocabulary expansion remains a separate model evaluation; it is not a guarantee of unlimited recognition. The saved-analysis UI stays as accepted.
