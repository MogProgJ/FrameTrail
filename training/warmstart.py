"""Make a COCO-pretrained RF-DETR checkpoint start sensibly on our class list.

rfdetr fits a 91-slot COCO head to N classes by keeping the first N+1 rows, so our class k
silently inherits COCO id k (our first class gets COCO's unused slot 0, the second gets
"person", and so on). This module rebuilds every classification head instead:

- a class that exists in COCO starts from that COCO class's row (Person <- person, Mug <- cup);
- a new class starts from small random weights with the COCO prior bias;
- the extra no-object slot keeps COCO slot 0.

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


def coco_rows(class_names: list[str]) -> list[int | None]:
    """COCO category id (head row) for each class name, or None for classes COCO lacks."""
    from rfdetr.assets.coco_classes import COCO_CLASSES
    by_name = {name: cat_id for cat_id, name in COCO_CLASSES.items()}
    rows = []
    for name in class_names:
        key = name.lower()
        rows.append(by_name.get(COCO_ALIASES.get(key, key)))
    return rows


def build(official: Path, class_names: list[str], out: Path, seed: int = 17) -> dict:
    import torch
    checkpoint = torch.load(official, map_location='cpu', weights_only=False)
    state = checkpoint['model']
    heads = sorted({key.rsplit('.', 1)[0] for key in state if 'class_embed' in key and key.endswith('.weight')})
    rows = coco_rows(class_names)
    generator = torch.Generator().manual_seed(seed)
    for head in heads:
        weight, bias = state[f'{head}.weight'], state[f'{head}.bias']
        if weight.shape[0] != 91:
            raise ValueError(f'{official} is not a 91-slot COCO checkpoint ({head}: {tuple(weight.shape)})')
        new_weight = torch.randn(len(class_names) + 1, weight.shape[1], generator=generator, dtype=weight.dtype) * 0.01
        new_bias = torch.full((len(class_names) + 1,), float(bias[1:].mean()), dtype=bias.dtype)
        for index, row in enumerate(rows):
            if row is not None:
                new_weight[index], new_bias[index] = weight[row], bias[row]
        new_weight[-1], new_bias[-1] = weight[0], bias[0]
        state[f'{head}.weight'], state[f'{head}.bias'] = new_weight, new_bias
    for key in ('optimizer', 'lr_scheduler', 'epoch'):
        checkpoint.pop(key, None)
    args = checkpoint.get('args')
    if isinstance(args, dict):
        args['num_classes'] = len(class_names)
    elif args is not None:
        args.num_classes = len(class_names)
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(checkpoint, out)
    mapped = {name: row for name, row in zip(class_names, rows) if row is not None}
    return {'source': str(official), 'heads': len(heads), 'classes': len(class_names),
            'started_from_coco': len(mapped), 'mapping': mapped}
