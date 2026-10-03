"""Export a pinned expanded recognition model. Developer tooling, never run by the app."""
import argparse
import hashlib
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--weights', type=Path, required=True, help='Official yolov8s/m-worldv2.pt checkpoint')
    parser.add_argument('--profile', choices=('world-s', 'world-m', 'openimages'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    os.environ['YOLO_CONFIG_DIR'] = str(root / '.deps/world-export/config')
    os.environ['YOLO_AUTOINSTALL'] = 'false'
    os.environ['YOLO_VERBOSE'] = 'false'
    import torch
    import onnx
    import ultralytics
    from ultralytics import YOLOWorld, YOLO
    if ultralytics.__version__ != '8.3.228':
        raise RuntimeError('Use the pinned requirements-world.txt export environment')
    is_world = args.profile != 'openimages'
    vocabulary = json.loads((root / ('dependencies/world-vocabulary.json' if is_world else
        'dependencies/recognition-vocabulary.json')).read_text(encoding='utf-8'))
    labels = vocabulary['classes'] if is_world else [vocabulary['classes'][i] for i in vocabulary['openimages_ids']]
    if is_world and (vocabulary['id'] != 'world-v1' or len(labels) != 100 or len(set(labels)) != 100):
        raise ValueError('Expected the reviewed 100-class world-v1 vocabulary')
    if args.output.exists():
        raise FileExistsError('Choose a new export path; existing models are never overwritten')
    weights = args.weights.resolve(strict=True)
    manifest = json.loads((root / f'dependencies/yolo-{args.profile}.json').read_text(encoding='utf-8'))
    if hashlib.sha256(weights.read_bytes()).hexdigest() != manifest['weights_sha256']:
        raise ValueError('Checkpoint hash differs from the official pinned weights')
    torch.set_num_threads(4)
    model = YOLOWorld(str(weights)) if is_world else YOLO(str(weights))
    # Text encoder is only used here, cached inside the project; no downloads at runtime.
    if is_world:
        import clip
        from unittest.mock import patch
        original_load = clip.load
        model.model.clip_model = None
        with patch('clip.load', side_effect=lambda *a, **kw: original_load(*a,
                **dict(kw, download_root=str(root / '.deps/world-export/clip')))):
            model.set_classes(labels)
        del model.model.clip_model
    elif list(model.names.values()) != vocabulary['openimages_labels']:
        raise ValueError('Publisher label order differs from the reviewed canonical mapping')
    export = Path(model.export(format='onnx', imgsz=640, batch=1, dynamic=False,
        simplify=False, opset=17, device='cpu', half=False, nms=False))
    graph = onnx.load(str(export))
    metadata = {item.key: item.value for item in graph.metadata_props}
    metadata.pop('date', None)  # Upstream wall-clock metadata would change the artifact checksum.
    metadata.update({'frametrail.profile': args.profile, 'frametrail.vocabulary': '\n'.join(labels),
                     'frametrail.vocabulary_id': 'world-v1' if is_world else 'openimages-v1'})
    onnx.helper.set_model_props(graph, dict(sorted(metadata.items())))
    onnx.checker.check_model(graph)
    shape = [d.dim_value for d in graph.graph.output[0].type.tensor_type.shape.dim]
    if shape != [1, 4+len(labels), 8400] or len(graph.graph.input) != 1 or len(graph.graph.output) != 1:
        raise RuntimeError(f'Unexpected exported contract: {shape}')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    onnx.save(graph, str(args.output))
    provenance = {'schema': 1, 'profile': args.profile, 'vocabulary_id': 'world-v1' if is_world else 'openimages-v1',
        'weights_sha256': hashlib.sha256(weights.read_bytes()).hexdigest(),
        'onnx_sha256': hashlib.sha256(args.output.read_bytes()).hexdigest(),
        'bytes': args.output.stat().st_size, 'ultralytics': ultralytics.__version__,
        'torch': torch.__version__, 'onnx': onnx.__version__,
        'input': [1, 3, 640, 640], 'output': shape, 'opset': 17,
        'preprocess': 'RGB float32 / 255, centered letterbox 114, bilinear resize',
        'postprocess': f'decoded xywh + {len(labels)} scores, native best-class selection, canonical mapping and class-aware NMS'}
    args.output.with_suffix('.export.json').write_text(json.dumps(provenance, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(provenance, indent=2))


if __name__ == '__main__':
    main()
