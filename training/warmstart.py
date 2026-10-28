"""Make a pretrained RF-DETR checkpoint start sensibly on our class list.

rfdetr fits a 91-slot COCO head to N classes by keeping the first N+1 rows, so our class k
silently inherits COCO id k (our first class gets COCO's unused slot 0, the second gets
"person", and so on). This module rebuilds every classification head instead:

- a class the starting model already knows keeps its row: from a run of ours (`build_from_trained`,
  e.g. the pilot for the full vocabulary) or from COCO (Person <- person, Mug <- cup);
- a new class starts from small random weights with the starting model's average class bias;
- the extra no-object slot keeps the starting model's no-object row.

The checkpoint then has exactly N+1 rows, so rfdetr loads it without trimming.
"""
from __future__ import annotations

from pathlib import Path

# Our target names (lower-case) whose COCO name differs; identical names match automatically.
COCO_ALIASES = {
    'table': 'dining table', 'television': 'tv', 'computer mouse': 'mouse', 'remote control': 'remote',
    'computer keyboard': 'keyboard', 'mobile phone': 'cell phone', 'microwave oven': 'microwave',
    'mug': 'cup', 'coffee cup': 'cup', 'doughnut': 'donut', 'football': 'sports ball', 'cattle': 'cow',
    'houseplant': 'potted plant', 'computer monitor': 'tv', 'motorbike': 'motorcycle',
}
# Classes an earlier run of ours knew under another name: the pilot merged Taxi into Car.
TRAINED_ALIASES = {'taxi': 'car'}
# Checkpoint entries that only matter for resuming the run that wrote them.
RUN_STATE = ('optimizer', 'lr_scheduler', 'epoch', 'state_dict', 'optimizer_states', 'lr_schedulers', 'loops',
             'callbacks', 'global_step', 'best_total_source', 'pytorch-lightning_version')


def coco_rows(class_names: list[str]) -> list[int | None]:
    """COCO category id (head row) for each class name, or None for classes COCO lacks."""
    from rfdetr.assets.coco_classes import COCO_CLASSES
    by_name = {name: cat_id for cat_id, name in COCO_CLASSES.items()}
    rows = []
    for name in class_names:
        key = name.lower()
        rows.append(by_name.get(COCO_ALIASES.get(key, key)))
    return rows


def trained_rows(class_names: list[str], known: list[str]) -> list[int | None]:
    """Row of each class in a head trained on `known` (rows follow that class order), or None."""
    index = {name.lower(): row for row, name in enumerate(known)}
    rows = []
    for name in class_names:
        key = name.lower()
        rows.append(index.get(key, index.get(TRAINED_ALIASES.get(key, ''))))
    return rows


def class_heads(state: dict) -> list[str]:
    return sorted({key.rsplit('.', 1)[0] for key in state if 'class_embed' in key and key.endswith('.weight')})


def rebuild_head(weight, bias, class_names: list[str], choices: list[tuple], no_object: int, generator):
    """New (N+1)-row head: each class takes the row of the first choice (weight, bias, rows) that knows it."""
    import torch
    new_weight = torch.randn(len(class_names) + 1, weight.shape[1], generator=generator, dtype=weight.dtype) * 0.01
    known_bias = torch.cat([bias[:no_object], bias[no_object + 1:]]) if no_object < len(bias) - 1 else bias[:-1]
    new_bias = torch.full((len(class_names) + 1,), float(known_bias.mean()), dtype=bias.dtype)
    sources = []
    for index in range(len(class_names)):
        source = None
        for label, (choice_weight, choice_bias, rows) in choices:
            if rows[index] is not None:
                new_weight[index], new_bias[index] = choice_weight[rows[index]], choice_bias[rows[index]]
                source = label
                break
        sources.append(source)
    new_weight[-1], new_bias[-1] = weight[no_object], bias[no_object]
    return new_weight, new_bias, sources


def finish(checkpoint: dict, class_names: list[str], out: Path) -> None:
    import torch
    for key in RUN_STATE:
        checkpoint.pop(key, None)
    args = checkpoint.get('args')
    if isinstance(args, dict):
        args['num_classes'] = len(class_names)
        args['class_names'] = list(class_names)
    elif args is not None:
        args.num_classes = len(class_names)
        args.class_names = list(class_names)
    if isinstance(checkpoint.get('model_config'), dict):
        checkpoint['model_config']['num_classes'] = len(class_names)
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(checkpoint, out)


def build(official: Path, class_names: list[str], out: Path, seed: int = 17) -> dict:
    """Start from the official COCO weights."""
    import torch
    checkpoint = torch.load(official, map_location='cpu', weights_only=False)
    state = checkpoint['model']
    heads = class_heads(state)
    rows = coco_rows(class_names)
    generator = torch.Generator().manual_seed(seed)
    for head in heads:
        weight, bias = state[f'{head}.weight'], state[f'{head}.bias']
        if weight.shape[0] != 91:
            raise ValueError(f'{official} is not a 91-slot COCO checkpoint ({head}: {tuple(weight.shape)})')
        state[f'{head}.weight'], state[f'{head}.bias'], _ = rebuild_head(
            weight, bias, class_names, [('coco', (weight, bias, rows))], 0, generator)
    finish(checkpoint, class_names, out)
    mapped = {name: row for name, row in zip(class_names, rows) if row is not None}
    return {'source': str(official), 'heads': len(heads), 'classes': len(class_names),
            'started_from_coco': len(mapped), 'mapping': mapped}


def build_from_trained(trained: Path, official: Path, class_names: list[str], out: Path, seed: int = 17) -> dict:
    """Start the whole network from an earlier run of ours (e.g. the pilot for the full vocabulary).

    Classes that run knew keep their trained rows; other classes take their COCO row from the official
    weights, or start fresh. Everything outside the classification heads comes from the trained run.
    """
    import torch
    checkpoint = torch.load(trained, map_location='cpu', weights_only=False)
    args = checkpoint.get('args')
    known = list(args.get('class_names') if isinstance(args, dict) else getattr(args, 'class_names', None) or [])
    state = checkpoint['model']
    heads = class_heads(state)
    if not known or state[f'{heads[0]}.weight'].shape[0] != len(known) + 1:
        raise ValueError(f'{trained} does not record one head row per class name plus no-object')
    coco = torch.load(official, map_location='cpu', weights_only=False)['model']
    if class_heads(coco) != heads:
        raise ValueError(f'{trained} and {official} have different classification heads')
    from_trained, from_coco = trained_rows(class_names, known), coco_rows(class_names)
    generator = torch.Generator().manual_seed(seed)
    for head in heads:
        weight, bias = state[f'{head}.weight'], state[f'{head}.bias']
        choices = [('trained', (weight, bias, from_trained)),
                   ('coco', (coco[f'{head}.weight'], coco[f'{head}.bias'], from_coco))]
        state[f'{head}.weight'], state[f'{head}.bias'], sources = rebuild_head(
            weight, bias, class_names, choices, len(known), generator)
    finish(checkpoint, class_names, out)
    return {'source': str(trained), 'coco_source': str(official), 'heads': len(heads), 'classes': len(class_names),
            'started_from_trained': sources.count('trained'), 'started_from_coco': sources.count('coco'),
            'started_fresh': sources.count(None),
            'mapping': {name: source for name, source in zip(class_names, sources) if source}}
