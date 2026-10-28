"""Export a trained RF-DETR checkpoint for the app's "RF-DETR Open Images" profile (`rfdetr-oi`).

The app's RF adapter expects one input [1, 3, 512, 512] (RGB, plain resize, ImageNet normalisation)
and one output [1, 300, 4 + 615]: normalised (cx, cy, w, h) boxes, then one raw logit for each of the
app's 615 categories (dependencies/recognition-vocabulary.json). Each trained class is placed in the
column of its app category, found through the app's own Open Images name table; categories the model
was not trained on get a constant logit of -100, so they are never reported. rfdetr's no-object
column is dropped. The trained class names are also stored, as `frametrail.trained_classes`.

After export, the ONNX output is compared with PyTorch on a few test images, and a summary
(<out>.json) records the checkpoint and ONNX hashes, the parity errors and the CPU latency.

Example:
    python training/export.py --weights runs/pilot-small/checkpoint_best_total.pth --model small \\
        --images data/pilot/test --out runs/pilot-small/rfdetr_openimages.onnx

Copy the file into the app's models/ folder as rfdetr_openimages.onnx and pick
"RF-DETR · Open Images (trained)".
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import statistics
import sys
import time
from pathlib import Path

MODELS = ('nano', 'small', 'medium', 'base', 'large')
PROFILE = 'rfdetr-oi'
PREPROCESSING = 'rf-rgb512-normalized-v1'
RESOLUTION = 512
UNTRAINED_LOGIT = -100.0
TOLERANCE = dict(rtol=1e-3, atol=2e-3)
SHOWN = 0.3  # Detections at or above this score must be the same in ONNX and PyTorch.
HERE = Path(__file__).resolve().parent
# In the repository the app vocabulary sits in dependencies/; on the cluster the launcher uploads it into training/.
VOCABULARY_PATHS = (HERE.parent / 'dependencies' / 'recognition-vocabulary.json', HERE / 'recognition-vocabulary.json')


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def app_columns(names: list[str], vocabulary: dict) -> list[int]:
    """App category ID for each trained class, matched by Open Images label, then by category name."""
    by_label = {label.lower(): cid for label, cid in zip(vocabulary['openimages_labels'], vocabulary['openimages_ids'])}
    by_name = {name.lower(): cid for cid, name in enumerate(vocabulary['classes'])}
    ids = [by_label.get(name.lower(), by_name.get(name.lower())) for name in names]
    missing = [name for name, cid in zip(names, ids) if cid is None]
    if missing:
        raise SystemExit(f'No app category for: {", ".join(missing)}')
    if len(set(ids)) != len(ids):
        clashes = sorted({vocabulary['classes'][cid] for cid in ids if ids.count(cid) > 1})
        raise SystemExit(f'Several trained classes map to the same app category: {", ".join(clashes)}')
    return ids


def load_image(path: Path, resolution: int):
    """Same transform as the app: RGB, bilinear resize to a square, ImageNet normalisation."""
    import torch
    from PIL import Image
    from torchvision.transforms import functional
    with Image.open(path) as image:
        tensor = functional.to_tensor(image.convert('RGB'))
    tensor = functional.resize(tensor, [resolution, resolution], antialias=False)
    return functional.normalize(tensor, [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]).unsqueeze(0).to(torch.float32)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--weights', type=Path, required=True)
    parser.add_argument('--model', choices=MODELS, default='small')
    parser.add_argument('--out', type=Path, required=True, help='output .onnx path')
    parser.add_argument('--images', type=Path, required=True, help='folder of images for the parity check')
    parser.add_argument('--parity-images', type=int, default=8)
    parser.add_argument('--name', help='display name stored in the model; default is the output file name')
    parser.add_argument('--vocabulary', type=Path, help='app vocabulary JSON; default: dependencies/recognition-vocabulary.json')
    parser.add_argument('--opset', type=int, default=17)
    args = parser.parse_args(argv)

    import numpy as np
    import onnx
    import onnxruntime
    import rfdetr
    import torch
    from checkpoints import head_classes

    model_class = {'nano': rfdetr.RFDETRNano, 'small': rfdetr.RFDETRSmall, 'medium': rfdetr.RFDETRMedium,
                   'base': rfdetr.RFDETRBase, 'large': rfdetr.RFDETRLarge}[args.model]
    vocabulary_path = args.vocabulary or next((p for p in VOCABULARY_PATHS if p.exists()), None)
    if vocabulary_path is None:
        raise SystemExit('App vocabulary not found; pass --vocabulary dependencies/recognition-vocabulary.json')
    vocabulary = json.loads(vocabulary_path.read_text(encoding='utf-8'))
    model = model_class(pretrain_weights=str(args.weights), num_classes=head_classes(args.weights))
    names = list(model.class_names)
    resolution = int(model.model.resolution)
    if resolution != RESOLUTION:
        raise SystemExit(f'The app takes {RESOLUTION} px input; this model uses {resolution} px.')
    network = model.model.model.cpu().eval()
    rows = network.class_embed.weight.shape[0]
    if rows != len(names) + 1:
        raise SystemExit(f'Head has {rows} rows for {len(names)} class names; expected one extra no-object row.')
    columns = app_columns(names, vocabulary)
    classes, categories = len(names), len(vocabulary['classes'])
    # Output column 4 + c reads trained logit k where columns[k] == c, or the constant column for untrained c.
    source = [classes] * categories
    for k, cid in enumerate(columns):
        source[cid] = k

    class Packed(torch.nn.Module):
        def __init__(self, inner):
            super().__init__()
            self.inner = inner
            self.register_buffer('source', torch.tensor(source, dtype=torch.long))

        def forward(self, pixels):
            boxes, logits = self.inner(pixels)[:2]
            untrained = torch.full_like(logits[:, :, :1], UNTRAINED_LOGIT)
            trained = torch.cat([logits[:, :, :classes], untrained], dim=2)
            return torch.cat([boxes, trained.index_select(2, self.source)], dim=2)

    exportable = copy.deepcopy(network).eval()
    exportable.export()
    packed = Packed(exportable).eval()
    images = sorted(p for p in args.images.iterdir() if p.suffix.lower() in ('.jpg', '.jpeg', '.png'))
    if not images:
        raise SystemExit(f'No images in {args.images}')
    images = images[:args.parity_images]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with torch.inference_mode():
        torch.onnx.export(packed, load_image(images[0], resolution), str(args.out), input_names=['input'],
                          output_names=['output'], opset_version=args.opset, dynamo=False)

    exported = onnx.load(str(args.out))
    checkpoint_hash = sha256(args.weights)
    metadata = {
        'frametrail.profile': PROFILE,
        'frametrail.vocabulary': '\n'.join(vocabulary['classes']),
        'frametrail.preprocessing': PREPROCESSING,
        'frametrail.checkpoint_sha256': checkpoint_hash,
        'frametrail.trained_classes': '\n'.join(names),
        'frametrail.name': args.name or args.out.stem,
        'frametrail.architecture': f'rfdetr-{args.model}',
    }
    del exported.metadata_props[:]
    for key, value in metadata.items():
        entry = exported.metadata_props.add()
        entry.key, entry.value = key, value
    onnx.checker.check_model(exported)
    onnx.save(exported, str(args.out))

    options = onnxruntime.SessionOptions()
    options.intra_op_num_threads = 4
    session = onnxruntime.InferenceSession(str(args.out), sess_options=options, providers=['CPUExecutionProvider'])
    input_shape = session.get_inputs()[0].shape
    output_shape = session.get_outputs()[0].shape
    queries = int(network.num_queries)
    if input_shape != [1, 3, resolution, resolution] or output_shape != [1, queries, 4 + categories]:
        raise SystemExit(f'Unexpected ONNX shapes {input_shape} -> {output_shape}')

    # Queries are compared after pairing each PyTorch query with its nearest ONNX query: the decoder's query order
    # comes from a top-k over encoder scores, which tiny numeric differences can reorder without changing any
    # detection. The app reads all queries, so order does not matter; values and the detections shown do.
    box_error = logit_error = ordered_box_error = 0.0
    reordered = shown = shown_missing = 0
    passed = True
    untrained = np.ones(categories, dtype=bool)
    untrained[columns] = False
    latencies = []
    for path in images:
        pixels = load_image(path, resolution)
        with torch.inference_mode():
            reference = network(pixels)
        boxes = reference['pred_boxes'].numpy()
        logits = reference['pred_logits'][:, :, :classes].numpy()
        started = time.perf_counter()
        output = session.run(None, {'input': pixels.numpy()})[0]
        latencies.append(time.perf_counter() - started)
        placed = output[:, :, 4:][:, :, columns]
        ref_boxes, ref_logits, out_boxes, out_logits = boxes[0], logits[0], output[0, :, :4], placed[0]
        cost = (np.abs(ref_boxes[:, None] - out_boxes[None]).sum(-1)
                + np.abs(ref_logits[:, None] - out_logits[None]).mean(-1))
        pair = cost.argmin(1)
        one_to_one = len(set(pair.tolist())) == len(pair)
        reordered += int(np.sum(pair != np.arange(len(pair))))
        ordered_box_error = max(ordered_box_error, float(np.max(np.abs(ref_boxes - out_boxes))))
        box_error = max(box_error, float(np.max(np.abs(ref_boxes - out_boxes[pair]))))
        logit_error = max(logit_error, float(np.max(np.abs(ref_logits - out_logits[pair]))))
        ref_shown = 1 / (1 + np.exp(-ref_logits.max(1))) >= SHOWN
        out_shown = 1 / (1 + np.exp(-out_logits.max(1))) >= SHOWN
        shown += int(ref_shown.sum())
        shown_missing += int(np.sum(ref_shown != out_shown[pair]))
        passed &= bool(np.isfinite(output).all() and one_to_one
                       and np.allclose(ref_boxes, out_boxes[pair], **TOLERANCE)
                       and np.allclose(ref_logits, out_logits[pair], **TOLERANCE)
                       and ref_shown.sum() == out_shown.sum()
                       and np.all(output[:, :, 4:][:, :, untrained] == UNTRAINED_LOGIT))

    summary = {
        'onnx': str(args.out), 'onnx_sha256': sha256(args.out), 'checkpoint': str(args.weights),
        'checkpoint_sha256': checkpoint_hash, 'classes': classes, 'app_categories': columns,
        'input_shape': input_shape, 'output_shape': output_shape,
        'metadata': {k: v for k, v in metadata.items() if k not in ('frametrail.vocabulary', 'frametrail.trained_classes')},
        'parity': {'images': len(images), 'passed': passed, 'max_box_error': box_error,
                   'max_logit_error': logit_error, 'tolerance': TOLERANCE,
                   'reordered_queries': reordered, 'max_box_error_in_query_order': ordered_box_error,
                   f'detections_at_{SHOWN}': shown, 'detections_changed': shown_missing},
        'onnxruntime_cpu_median_seconds': statistics.median(latencies[1:] or latencies),
        'versions': {'torch': torch.__version__, 'onnx': onnx.__version__, 'onnxruntime': onnxruntime.__version__},
    }
    args.out.with_suffix('.json').write_text(json.dumps(summary, indent=1), encoding='utf-8')
    print(json.dumps(summary, indent=1), flush=True)
    if not passed:
        print('ONNX output differs from PyTorch beyond tolerance; do not use this export.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
