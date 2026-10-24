"""Fine-tune RF-DETR on a dataset built by openimages.py.

The whole detector is trained (backbone at a lower learning rate, as rfdetr does by default).
Re-running the same command resumes from <out>/last.ckpt (or the newest checkpoint_<epoch>.ckpt),
so a run can span several Slurm jobs.

Example:
    python training/train.py --dataset data/pilot --out runs/pilot-small --model small --epochs 12
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

MODELS = ('nano', 'small', 'medium', 'base', 'large')


def git_commit() -> str | None:
    try:
        return subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True,
                              cwd=Path(__file__).resolve().parent).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def describe_environment() -> dict:
    import rfdetr
    import torch
    info = {'python': platform.python_version(), 'torch': torch.__version__,
            'rfdetr': getattr(rfdetr, '__version__', None), 'cuda': torch.version.cuda,
            'gpus': [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]}
    try:
        from importlib.metadata import version
        info['rfdetr'] = version('rfdetr')
    except Exception:
        pass
    return info


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--model', choices=MODELS, default='small')
    parser.add_argument('--weights', help='starting checkpoint; default is the official COCO-pretrained weights')
    parser.add_argument('--no-warmstart', action='store_true',
                        help="use rfdetr's own head resizing instead of mapping COCO classes by name (see warmstart.py)")
    parser.add_argument('--epochs', type=int, default=12)
    parser.add_argument('--batch-size', type=int, default=8)
    parser.add_argument('--grad-accum', type=int, default=2, help='effective batch = batch-size x grad-accum')
    parser.add_argument('--lr', type=float, default=1e-4)
    parser.add_argument('--lr-encoder', type=float, default=1.5e-4)
    parser.add_argument('--lr-scheduler', choices=('cosine', 'step'), default='cosine',
                        help="cosine decays to zero over the run; rfdetr's 'step' only drops the rate after "
                             "100 epochs, so shorter runs would never decay. Keep --epochs fixed when resuming.")
    parser.add_argument('--workers', type=int, default=8)
    parser.add_argument('--device', default=None, help='cuda, cpu, ...; default lets rfdetr choose')
    parser.add_argument('--checkpoint-interval', type=int, default=4,
                        help='keep a full archive every N epochs; last.ckpt is refreshed every epoch')
    args = parser.parse_args(argv)

    import rfdetr
    model_class = {'nano': rfdetr.RFDETRNano, 'small': rfdetr.RFDETRSmall, 'medium': rfdetr.RFDETRMedium,
                   'base': rfdetr.RFDETRBase, 'large': rfdetr.RFDETRLarge}[args.model]
    args.out.mkdir(parents=True, exist_ok=True)
    archives = sorted(args.out.glob('checkpoint_*.ckpt'), key=lambda p: int(p.stem.split('_')[1]))
    resume = args.out / 'last.ckpt' if (args.out / 'last.ckpt').exists() else (archives[-1] if archives else None)
    summary = args.dataset / 'dataset.json'
    record = {
        'started': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'arguments': {k: str(v) for k, v in vars(args).items()},
        'git_commit': git_commit(), 'environment': describe_environment(),
        'dataset_summary_sha256': hashlib.sha256(summary.read_bytes()).hexdigest() if summary.exists() else None,
        'resumed_from': str(resume) if resume else None}
    with (args.out / 'runs.jsonl').open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(record) + '\n')
    print(json.dumps(record, indent=1), flush=True)

    weights = args.weights or model_class().model_config.pretrain_weights  # Downloads official weights once.
    if not args.no_warmstart and not resume:
        import warmstart
        coco = json.loads((args.dataset / 'train' / '_annotations.coco.json').read_text(encoding='utf-8'))
        names = [c['name'] for c in coco['categories']]
        report = warmstart.build(Path(weights), names, args.out / 'warmstart.pth')
        (args.out / 'warmstart.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
        print(f"Warm start: {report['started_from_coco']}/{report['classes']} classes begin from their COCO head rows",
              flush=True)
        weights = args.out / 'warmstart.pth'
    elif resume and (args.out / 'warmstart.pth').exists():
        weights = args.out / 'warmstart.pth'  # Same head layout as the run being resumed.
    model = model_class(pretrain_weights=str(weights))
    options = dict(dataset_dir=str(args.dataset), output_dir=str(args.out), epochs=args.epochs,
                   batch_size=args.batch_size, grad_accum_steps=args.grad_accum, lr=args.lr,
                   lr_encoder=args.lr_encoder, lr_scheduler=args.lr_scheduler, num_workers=args.workers,
                   checkpoint_interval=args.checkpoint_interval, tensorboard=True)
    if args.device:
        options['device'] = args.device
    if resume:
        options['resume'] = str(resume)
    model.train(**options)
    (args.out / 'finished.json').write_text(json.dumps({'finished': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                                                         'epochs': args.epochs}), encoding='utf-8')
    print(f'Finished. Best weights: {args.out / "checkpoint_best_total.pth"}', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
