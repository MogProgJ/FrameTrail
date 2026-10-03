# Broader recognition (0.12)

FrameTrail now has an optional model that can actually emit **fox**, alongside hundreds of additional categories. Choose **Broad recognition · 597 categories** in the player's Detection model selector, or in Video analysis → Analysis settings. The existing choose/drop → analyse → review → save/export workflow is preserved. Everything runs locally through C++ and ONNX Runtime.

## Which model to choose

| Choice | Vocabulary | Use and limitation |
|---|---|---|
| YOLOX-Nano | 80 COCO categories | Faster CPU baseline; cannot emit fox |
| YOLOX-S | 80 COCO categories | Default when installed; strongest recovery on the earlier selected people/vehicle recording |
| Broad recognition | 601 Open Images model labels grouped into 597 application categories | YOLOv8s Open Images V7; fox, rabbit, deer, lantern, balloon, many animals, household objects and object parts |
| YOLO-World S / M | Reviewed 100-category vocabulary | Experimental open-vocabulary models exported with text embeddings already embedded; M costs more compute and did not consistently improve recovery |

Open Images distinguishes fox from dog in its trained labels. That makes the distinction possible; it does not make every prediction correct. Its hierarchical labels can overlap: bicycle, bicycle wheel, wheel and tire may legitimately describe the same region at different levels. These appearances are predictions, not a unique-object count. Broad recognition also produced fewer selected matches on the earlier recording, so it does not replace YOLOX-S as the default.

YOLO-World is integrated as requested, but the tested exports are **not** the fox solution. A text label in the vocabulary is not proof that a model recognizes it reliably. The official [YOLO-World deployment guide](https://github.com/AILab-CVC/YOLO-World/blob/master/docs/deploy.md) describes offline vocabulary embedding; [Ultralytics documents custom World vocabularies](https://docs.ultralytics.com/models/yolo-world/) and [Open Images V7 models](https://docs.ultralytics.com/datasets/detect/open-images-v7/).

## What the comparison actually showed

All native runs used confidence 0.35, class-aware NMS 0.45, CPU inference, and same-class matching at box IoU ≥ 0.5. References were frozen before inference. Full details and model hashes are in [recognition-0.12.json](benchmarks/recognition-0.12.json).

| Model | Public references: 21 selected targets | Real fox targets | Earlier recording: 24 selected targets | New supplied-clip snapshots: 12 targets |
|---|---:|---:|---:|---:|
| YOLOX-S | 6/21 | 0/4; fox absent from vocabulary | 24/24 | 3/12 |
| YOLO-World S | 10/21 | 0/4 | 22/24 | 4/12 |
| YOLO-World M | 8/21 | 0/4 | 20/24 | 5/12 |
| Broad recognition | 16/21 | 3/4 | 18/24 | 3/12 |

The public set consists of the first four eligible Open Images validation images per selected category, ordered by image ID: fox, dog, balloon and bird. Broad recognition recovered 4/4 dog targets, 5/9 balloon targets and 4/4 bird targets. One balloon scene is visually ambiguous and remains in the fixed selection. These are publisher validation references, not an independent unseen deployment test. Images are separately acquired local inputs and are not packaged or committed.

The supplied-video set contains four manually reviewed snapshots from AI-generated clips, with only 12 selected targets. **The dark generated fox remains missed at 0.35**, including with broad recognition. Exploratory Python screens of World L and YOLOE-11S also recovered none of the four real fox targets; neither is shipped. No full-clip precision, false-positive rate, mAP or counting-accuracy claim follows from these small, partial-label comparisons.

The integration itself was checked against the official Python letterbox and ONNX reference on three lossless images. Fifteen strong targets across the three expanded models agreed with native CPU inference: minimum box IoU 0.99785 and maximum score difference 0.00183. CPU/DirectML tests compare strong classes, boxes and scores, verify repeatability and cancellation, and reject same-shaped models with incorrect embedded vocabularies. Saved analysis additionally checks wider-category progress, ordered timestamps, persistence and CSV export.

## Compute cost on this laptop

A sequential native CLI comparison used the first 60 frames of the same supplied 1280 × 720 recording, excluded five warmup frames, and included decode, RGB conversion, inference, tracking and profiling work. CPU used four threads; strict GPU used the GTX 1650 Ti through DirectML. No GUI or camera ran.

| Model | Warm CPU pipeline FPS | Warm GPU pipeline FPS | Sampled process peak MiB: CPU / GPU |
|---|---:|---:|---:|
| YOLOX-S | 7.58 | 27.58 | 158 / 322 |
| YOLO-World S | 5.03 | 16.31 | 232 / 340 |
| YOLO-World M | 2.21 | 10.84 | 355 / 404 |
| Broad recognition | 4.59 | 15.50 | 224 / 392 |

These short timings vary with load and power state, exclude model loading from warm FPS, and do not establish sustained performance. Process peak is sampled system RAM, not GPU VRAM. Broad recognition's total 60-frame run took about 13.3 seconds on CPU and 5.8 seconds on GPU including startup. Select **GPU · CPU fallback** before opening Video analysis for acceleration; the default remains CPU. The native player can run slower than source playback when analysis falls behind. Larger vocabulary and a larger model both have measurable costs.

## Native architecture

The decoding, player, tracker, counting rules and SQLite pipeline remain shared. A separate native adapter handles the newer model contract:

1. Keep the original owned RGB frame.
2. Resize a separate inference input to 640 × 640, center it in padding of intensity 114, and normalize RGB to float32 / 255.
3. Run one static ONNX graph on CPU or the isolated DirectML backend.
4. Read decoded center/width/height boxes plus class scores. World output is `[1,104,8400]`; Open Images output is `[1,605,8400]`. Neither has a separate objectness channel.
5. Map raw class indices to stable application IDs, undo the letterbox, clamp boxes, and perform class-aware suppression.
6. Pass the original-frame detections to the existing tracker and review pipeline.

This is deliberately separate from YOLOX's BGR 0–255 input and grid/objectness output. Input/output type and dimensions, model profile and the exact label order are checked before processing. Native interpolation rounding can differ by one intensity unit from OpenCV, so reference agreement uses explicit numerical tolerances.

Canonical IDs 0–79 preserve COCO meaning. World additions occupy 80–99; further Open Images categories extend the registry through 614. Open Images supports a noncontiguous subset. Man, Woman, Boy, Girl and Person map to **person** before NMS/tracking, avoiding duplicate human categories. Raw publisher label order and its canonical mapping are recorded in [recognition-vocabulary.json](../dependencies/recognition-vocabulary.json); [world-vocabulary.json](../dependencies/world-vocabulary.json) records the 100 World prompts. The model output label count and distinct application category count are intentionally separate.

New saved analyses use schema 4 and freeze profile plus exact vocabulary. Schemas 1–3 remain readable without modification. Earlier versions cannot open new schema-4 runs. Saved evidence is never silently relabelled or recomputed.

## Acquisition and optional export tooling

The portable private preview includes the validated ONNX files and needs no Python installation or network during inference. A fresh source checkout acquires the baseline as before; broader models use an explicit optional developer export environment. Nothing is automatically downloaded by the application or CMake.

```powershell
# Optional developer environment, Python 3.12
py -3.12 -m venv .deps/recognition-python
$py = ".\.deps\recognition-python\Scripts\python.exe"
& $py -m pip install setuptools==78.1.0 wheel==0.48.0
& $py -m pip install torch==2.8.0 torchvision==0.23.0 --index-url https://download.pytorch.org/whl/cpu
& $py -m pip install --no-build-isolation -r scripts/requirements-world.txt
.\scripts\fetch-model.ps1 -Model openimages
.\scripts\fetch-model.ps1 -Model world-all
.\scripts\build.ps1 -GpuChecks
```

`fetch-world.ps1 -Python <venv-python>` can select a different Python environment. It verifies the official checkpoint hash, exports through pinned Ultralytics 8.3.228/PyTorch 2.8.0/ONNX 1.19.1, checks the normalized ONNX checksum and preserves existing files. The export is static float32, batch 1, opset 17, with no embedded NMS or graph simplifier. Export time metadata is removed for reproducibility. Repeated World S and Open Images exports matched the recorded hashes. CLIP is an export-only dependency for World; its text encoder is removed from the final graph.

Changing World prompts requires a reviewed registry/export/manifest update and rebuild; there is no arbitrary runtime prompt textbox in this release. A user's text prompt is not passed to a cloud service.

Example CLI:

```powershell
.\build\windows-msvc\Release\frametrail.exe inspect "C:\Videos\wildlife.mp4" --detect .\models\yolo_openimages.onnx --model-type openimages --backend auto --detections .\output\wildlife.csv
```

Developer reference check, after acquiring local reference images:

```powershell
& $py -B scripts/check-recognition.py --cli build/windows-msvc/Release/frametrail.exe --output output/recognition-check --images <dog-photo> <fox-photo-1> <fox-photo-2>
```

## Remaining accuracy work

Broader vocabulary addresses an unavailable class. It does not repair small object size, dark imagery, blur, synthetic-video artifacts, training-domain differences or tracker association errors. Raising confidence hides weaker predictions and can remove useful true detections; it is not a correctness guarantee.

The next recognition gate is a fully annotated, permissioned real-world wildlife/night subset with explicit false-positive and recall targets. Choose the useful classes and domain before tuning or training. If pretrained models remain inadequate, the existing conditional bwUniCluster training branch can fine-tune a compact model, export ONNX, and compare on a held-out test set. Cloud services, agents and a Python inference worker remain separate later branches.

Ultralytics model/export licensing differs from the Apache-licensed YOLOX baseline. The preview includes upstream AGPL/GPL notices and stays within the existing private evaluation/distribution-review policy; see [third-party inventory](THIRD_PARTY_NOTICES.md).
