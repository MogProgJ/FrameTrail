"""The class count of an RF-DETR checkpoint, which rfdetr must be told when it differs from 90.

rfdetr 1.11 configures 90 classes unless told otherwise. It loads a checkpoint with more classes and then cuts the
head back to 90 rows, so every class after the 90th silently disappears (the pilot has 110, the full vocabulary 595).
Building the model with num_classes=head_classes(weights) keeps the whole head.
"""
from __future__ import annotations

from pathlib import Path


def head_classes(weights: Path | str) -> int:
    """Classes in a checkpoint's detection head: its rows minus the extra no-object row."""
    import torch
    checkpoint = torch.load(weights, map_location='cpu', weights_only=False)
    state = checkpoint.get('model')
    if state is None:  # PyTorch Lightning .ckpt
        state = {key.removeprefix('model.'): value for key, value in checkpoint['state_dict'].items()}
    return int(state['class_embed.bias'].shape[0]) - 1


def epochs_done(checkpoint: dict) -> int | None:
    """Training epochs completed when a checkpoint was written (Lightning's own count), or None if not recorded."""
    try:
        return int(checkpoint['loops']['fit_loop']['epoch_progress']['current']['completed'])
    except (KeyError, TypeError):
        return None


def averaged(checkpoint: Path, out: Path, like: Path | None = None) -> dict:
    """Write a .pth that scoring and export can load from a Lightning checkpoint such as last.ckpt.

    rfdetr validates and picks its best checkpoint with the averaged (EMA) weights, and checkpoint_best_total.pth
    holds them under "model". last.ckpt holds them in the EMA callback's state and the plain weights under
    "state_dict"; this puts the averaged ones under "model" (the plain ones if no average was kept). `like` is a
    .pth of the same run that lends the settings a .ckpt may lack (class names among them)."""
    import torch
    data = torch.load(checkpoint, map_location='cpu', weights_only=False)
    plain = {key.removeprefix('model.'): value for key, value in data['state_dict'].items()}
    model, source = plain, 'regular'
    for name, state in (data.get('callbacks') or {}).items():
        average = state.get('average_model_state_dict') if isinstance(state, dict) else None
        if 'EMA' in str(name) and isinstance(average, dict):
            model = {key.removeprefix('module.').removeprefix('model.'): value
                     for key, value in average.items() if key != 'n_averaged'}
            source = 'ema'
    if set(model) != set(plain):
        raise SystemExit(f'{checkpoint}: the averaged weights do not have the model\'s layers '
                         f'({len(set(model) ^ set(plain))} names differ)')
    if like is not None:
        lender = torch.load(like, map_location='cpu', weights_only=False)
        for key in ('args', 'model_name', 'model_config', 'rfdetr_version'):
            if key not in data and key in lender:
                data[key] = lender[key]
    for key in ('optimizer_states', 'lr_schedulers', 'callbacks'):   # Not needed to score, and most of the file.
        data.pop(key, None)
    data['model'] = model
    data['state_dict'] = {'model.' + key: value for key, value in model.items()}
    data['averaged_source'] = source
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(data, out)
    return {'epoch': epochs_done(data), 'weights': source, 'classes': int(model['class_embed.bias'].shape[0]) - 1}


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json
    parser = argparse.ArgumentParser(description='Checkpoint helpers for the job scripts.')
    commands = parser.add_subparsers(dest='command', required=True)
    epoch = commands.add_parser('epoch', help='print the epochs completed when a checkpoint was written')
    epoch.add_argument('checkpoint', type=Path)
    convert = commands.add_parser('averaged', help='a scorable .pth with the averaged weights of a Lightning .ckpt')
    convert.add_argument('--checkpoint', type=Path, required=True)
    convert.add_argument('--out', type=Path, required=True)
    convert.add_argument('--like', type=Path, help='a .pth of the same run, for settings the .ckpt lacks')
    args = parser.parse_args(argv)
    if args.command == 'epoch':
        import torch
        done = epochs_done(torch.load(args.checkpoint, map_location='cpu', weights_only=False))
        if done is None:
            raise SystemExit(f'{args.checkpoint} does not record its epoch')
        print(done)
    else:
        print(json.dumps(averaged(args.checkpoint, args.out, args.like)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
