"""Reproducible YOLO Open Images fine-tuning; never changes the application's models."""
import argparse
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import time

from training_data import ROOT, digest, read_json, verify_bundle, write_json


def preflight(dataset, config, mode, weights):
    lock = verify_bundle(dataset, smoke=mode == 'smoke')
    if (config.get('schema') != 1 or config.get('family') != 'yolov8s-openimages'
            or type(config.get('epochs')) is not int or not 1 <= config['epochs'] <= 200
            or type(config.get('batch')) is not int or config['batch'] <= 0
            or config.get('imgsz') not in (320, 640) or config.get('device') not in ('cpu', '0')
            or type(config.get('seed')) is not int or config['seed'] < 0
            or type(config.get('freeze')) is not int or not 0 <= config['freeze'] <= 22
            or type(config.get('patience')) is not int or config['patience'] <= 0
            or type(config.get('lr0')) not in (int, float) or not math.isfinite(config['lr0']) or not 0 < config['lr0'] <= 1):
        raise ValueError('Unsupported bounded training configuration')
    if mode == 'smoke' and (config['epochs'] != 1 or sum(lock['images'].values()) > 256):
        raise ValueError('A smoke run is limited to one epoch and at most 256 images')
    publisher = read_json(ROOT / 'dependencies/yolo-openimages.json')
    if digest(weights) != publisher['weights_sha256']:
        raise ValueError('Initial checkpoint differs from the pinned broad publisher weights')
    return {'schema': 1, 'mode': mode, 'dataset_lock_sha256': digest(Path(dataset) / 'dataset-lock.json'),
            'parent_weights_sha256': digest(weights), 'config': config, 'images': lock['images'],
            'raw_labels': len(lock['classes']), 'canonical_categories': len({item['canonical_id'] for item in lock['classes']}),
            'limits': 'Smoke runs prove mechanics only. A trained artifact needs independent evaluation before adoption.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--weights', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--mode', choices=('smoke', 'train'), default='train')
    parser.add_argument('--run', action='store_true', help='Without this flag, only validate inputs; no training or downloads')
    args = parser.parse_args()
    dataset, weights = args.dataset.resolve(strict=True), args.weights.resolve(strict=True)
    config = read_json(args.config)
    report = preflight(dataset, config, args.mode, weights)
    if not args.run:
        print(json.dumps(report, indent=2))
        return
    if not args.output or args.output.exists():
        parser.error('Training requires a new --output directory')
    output = args.output.resolve()
    os.environ['YOLO_CONFIG_DIR'] = str(ROOT / '.deps/training-settings')
    os.environ['YOLO_AUTOINSTALL'] = 'false'
    os.environ['MPLCONFIGDIR'] = str(ROOT / '.deps/training-settings/matplotlib')
    os.environ['WANDB_DISABLED'] = 'true'
    os.environ['COMET_MODE'] = 'DISABLED'
    import torch
    import ultralytics
    from ultralytics import YOLO, settings
    if ultralytics.__version__ != '8.3.228' or torch.__version__.split('+')[0] != '2.8.0':
        raise RuntimeError('Use the pinned training requirements; do not update the application environment')
    if config['device'] == '0' and not torch.cuda.is_available():
        raise RuntimeError('CUDA training GPU unavailable; DirectML inference is not a CUDA training backend')
    settings.update({'wandb': False, 'mlflow': False, 'clearml': False, 'comet': False, 'neptune': False, 'dvc': False, 'hub': False})
    torch.set_num_threads(4)
    output.mkdir(parents=True)
    try:
        git_result = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True)
        revision = git_result.stdout.strip() if git_result.returncode == 0 else None
    except FileNotFoundError:
        revision = None
    packages = {distribution.metadata['Name']: distribution.version for distribution in importlib.metadata.distributions()
                if distribution.metadata['Name']}
    write_json(output / 'environment-packages.json', dict(sorted(packages.items())))
    report.update(status='running', code_revision=revision, config_sha256=digest(args.config),
        source_sha256={name: digest(ROOT / name) for name in ('scripts/train-detector.py', 'scripts/training_data.py')},
        environment={'python': platform.python_version(), 'platform': platform.platform(),
                     'torch': torch.__version__, 'ultralytics': ultralytics.__version__, 'cuda': torch.version.cuda,
                     'packages_sha256': digest(output / 'environment-packages.json')},
        device=torch.cuda.get_device_name(0) if config['device'] == '0' else 'CPU')
    write_json(output / 'experiment.json', report)
    started = time.monotonic()
    try:
        model = YOLO(str(weights))
        model.train(data=str(dataset / 'data.yaml'), epochs=config['epochs'], imgsz=config['imgsz'],
            batch=config['batch'], device=config['device'], workers=0, seed=config['seed'], deterministic=True,
            optimizer='AdamW', lr0=config['lr0'], freeze=config['freeze'], patience=config['patience'],
            amp=False, cache=False, plots=False, project=str(output.parent), name=output.name, exist_ok=True,
            save=True, val=True, verbose=False)
        if list(model.names.values()) != [item['name'] for item in verify_bundle(dataset, args.mode == 'smoke')['classes']]:
            raise RuntimeError('Training changed the frozen raw class order')
        report.update(status='completed', elapsed_seconds=time.monotonic() - started,
            checkpoints={p.name: digest(p) for p in sorted((output / 'weights').glob('*.pt'))},
            locked_test_evaluated=False, approved_for_application=False)
    except BaseException as error:
        report.update(status='failed', elapsed_seconds=time.monotonic() - started, error=str(error))
        raise
    finally:
        write_json(output / 'experiment.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
