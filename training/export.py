"""Export a trained RF-DETR checkpoint to the ONNX layout FrameTrail loads.

The app expects one input [1, 3, R, R] (RGB, plain resize to R x R, ImageNet normalisation) and one
output [1, queries, 4 + classes]: normalised (cx, cy, w, h) boxes followed by one raw logit per class.
rfdetr's extra no-object column is dropped. The class names, input size and preprocessing are stored
in the ONNX metadata, so the app needs no hardcoded vocabulary.

After export, the ONNX output is compared with PyTorch on a few test images, and a summary
(<out>.json) records the checkpoint and ONNX hashes, the parity errors and the CPU latency.

Example:
    python training/export.py --weights runs/pilot-small/checkpoint_best_total.pth --model small \\
        --images data/pilot/test --out runs/pilot-small/frametrail-pilot-small.onnx
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
OUTPUT_LAYOUT = 'rf-cxcywh-logits-v1'
TOLERANCE = dict(rtol=1e-3, atol=2e-3)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def preprocessing_id(resolution: int) -> str:
    return f'rf-rgb{resolution}-normalized-v1'


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
    parser.add_argument('--opset', type=int, default=17)
    args = parser.parse_args(argv)

    import numpy as np
    import onnx
    import onnxruntime
    import rfdetr
    import torch

    model_class = {'nano': rfdetr.RFDETRNano, 'small': rfdetr.RFDETRSmall, 'medium': rfdetr.RFDETRMedium,
                   'base': rfdetr.RFDETRBase, 'large': rfdetr.RFDETRLarge}[args.model]
    model = model_class(pretrain_weights=str(args.weights))
    names = list(model.class_names)
    resolution = int(model.model.resolution)
    network = model.model.model.cpu().eval()
    rows = network.class_embed.weight.shape[0]
    if rows != len(names) + 1:
        raise SystemExit(f'Head has {rows} rows for {len(names)} class names; expected one extra no-object row.')
    if any('\n' in name or not name.strip() for name in names):
        raise SystemExit('Class names must be non-empty single lines.')
    classes = len(names)

    class Packed(torch.nn.Module):
        def __init__(self, inner):
            super().__init__()
            self.inner = inner

        def forward(self, pixels):
            boxes, logits = self.inner(pixels)[:2]
            return torch.cat([boxes, logits[:, :, :classes]], dim=2)

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
        'frametrail.profile': 'rfdetr',
        'frametrail.name': args.name or args.out.stem,
        'frametrail.vocabulary': '\n'.join(names),
        'frametrail.preprocessing': preprocessing_id(resolution),
        'frametrail.output': OUTPUT_LAYOUT,
        'frametrail.checkpoint_sha256': checkpoint_hash,
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
    if input_shape != [1, 3, resolution, resolution] or output_shape != [1, queries, 4 + classes]:
        raise SystemExit(f'Unexpected ONNX shapes {input_shape} -> {output_shape}')

    box_error = logit_error = 0.0
    passed = True
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
        box_error = max(box_error, float(np.max(np.abs(boxes - output[:, :, :4]))))
        logit_error = max(logit_error, float(np.max(np.abs(logits - output[:, :, 4:]))))
        passed &= bool(np.isfinite(output).all() and np.allclose(boxes, output[:, :, :4], **TOLERANCE)
                       and np.allclose(logits, output[:, :, 4:], **TOLERANCE))

    summary = {
        'onnx': str(args.out), 'onnx_sha256': sha256(args.out), 'checkpoint': str(args.weights),
        'checkpoint_sha256': checkpoint_hash, 'classes': classes, 'input_shape': input_shape,
        'output_shape': output_shape, 'metadata': {k: v for k, v in metadata.items() if k != 'frametrail.vocabulary'},
        'parity': {'images': len(images), 'passed': passed, 'max_box_error': box_error,
                   'max_logit_error': logit_error, 'tolerance': TOLERANCE},
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
