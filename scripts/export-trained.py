"""Export a training artifact for native comparison; never installs it in the GUI."""
import argparse
import json
import os
from pathlib import Path

from training_data import ROOT, digest, read_json, vocabulary, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiment', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = read_json(args.experiment)
    if report.get('status') != 'completed' or report.get('raw_labels') != 601:
        raise ValueError('Only a completed full-vocabulary experiment can use the existing native profile')
    weights = args.experiment.parent / 'weights/best.pt'
    if digest(weights) != report['checkpoints'].get('best.pt'):
        raise ValueError('Training checkpoint differs from the recorded artifact')
    if args.output.exists() or args.output.with_suffix('.export.json').exists():
        raise FileExistsError('Choose a new artifact path')
    os.environ['YOLO_CONFIG_DIR'] = str(ROOT / '.deps/training-settings')
    os.environ['YOLO_AUTOINSTALL'] = 'false'
    import onnx
    import torch
    import ultralytics
    from ultralytics import YOLO
    if ultralytics.__version__ != '8.3.228' or onnx.__version__ != '1.19.1':
        raise RuntimeError('Use the pinned training/export requirements')
    torch.set_num_threads(4)
    model = YOLO(str(weights))
    classes = vocabulary()
    if list(model.names.values()) != [item['name'] for item in classes]:
        raise ValueError('Trained checkpoint changed the exact raw publisher class order')
    export = Path(model.export(format='onnx', imgsz=640, batch=1, dynamic=False,
                  simplify=False, opset=17, device='cpu', half=False, nms=False))
    graph = onnx.load(str(export))
    shape = [dimension.dim_value for dimension in graph.graph.output[0].type.tensor_type.shape.dim]
    if len(graph.graph.input) != 1 or len(graph.graph.output) != 1 or shape != [1, 605, 8400]:
        raise ValueError(f'Trained export is incompatible with the native broad profile: {shape}')
    metadata = {item.key: item.value for item in graph.metadata_props if item.key != 'date'}
    metadata.update({'frametrail.profile': 'openimages', 'frametrail.vocabulary_id': 'openimages-v1',
                     'frametrail.vocabulary': '\n'.join(item['canonical_name'] for item in classes),
                     'frametrail.experiment_sha256': digest(args.experiment),
                     'frametrail.artifact_status': 'smoke-only' if report['mode'] == 'smoke' else 'evaluation-required'})
    onnx.helper.set_model_props(graph, dict(sorted(metadata.items())))
    onnx.checker.check_model(graph)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    onnx.save(graph, str(args.output))
    provenance = {'schema': 1, 'profile': 'openimages', 'vocabulary_id': 'openimages-v1',
                  'input': [1, 3, 640, 640], 'output': shape, 'opset': 17,
                  'checkpoint_sha256': digest(weights), 'onnx_sha256': digest(args.output),
                  'experiment_sha256': digest(args.experiment), 'dataset_lock_sha256': report['dataset_lock_sha256'],
                  'mode': report['mode'], 'approved_for_application': False,
                  'ultralytics': ultralytics.__version__, 'torch': torch.__version__, 'onnx': onnx.__version__,
                  'preprocess': 'RGB float32 /255, centered letterbox 114',
                  'limits': 'Native contract compatibility is not an accuracy/adoption claim. Existing application models are preserved.'}
    write_json(args.output.with_suffix('.export.json'), provenance)
    print(json.dumps(provenance, indent=2))


if __name__ == '__main__':
    main()
