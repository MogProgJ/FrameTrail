"""Yardstick A: how good is a detector on photos in which every object of 80 everyday types is labelled?

COCO val2017 has complete labels for its 80 types, so a missed object and a false box both count, which Open Images
scoring cannot see. This scores any model that reports app category IDs (the trained RF-DETR through
`calibrate.py predict`) and YOLOX-S the same way:

- AP@0.5 per type and its mean (greedy matching by score, crowd regions ignored, all-point interpolation);
- at one confidence setting, as the app applies it: share of objects found (recall) and share of boxes right
  (precision), pooled over the 80 types, per type, and per object size (COCO's small/medium/large);
- the recall each model reaches at the same precision, which is the fair comparison when score scales differ.

A box counts for a COCO type when its app category is that type, a narrower Open Images class of it (taxi for car,
raven for bird), or a listed equivalent (cattle for cow, mug for cup): see `coco_classes`. Boxes of other
categories (footwear, tree, ...) cannot be judged on COCO and are left out. COCO val2017 is never trained or tuned on.

    python training/coco_yardstick.py predict-yolox --model models/yolox_s.onnx --images data/coco/val2017 \\
        --out runs/yardstick-a/yolox-s.jsonl
    python training/calibrate.py predict --model models/rfdetr_openimages.onnx --images data/coco/val2017 \\
        --out runs/yardstick-a/round3.jsonl
    python training/coco_yardstick.py score --annotations data/coco/annotations/instances_val2017.json \\
        --model yolox-s=runs/yardstick-a/yolox-s.jsonl --model round3=runs/yardstick-a/round3.jsonl \\
        --out runs/yardstick-a/report.md
    python training/coco_yardstick.py predict-rfdetr --images data/coco/val2017 --out stock-rfdetr-small.jsonl   # GPU machine
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import oi_metric

HERE = Path(__file__).resolve().parent
VOCABULARY = HERE.parent / 'dependencies' / 'recognition-vocabulary.json'
HIERARCHY = HERE.parent / 'src' / 'recognition_hierarchy.hpp'
# App categories that are the same thing as a COCO type under another name, or a kind of it that the Open Images
# hierarchy does not nest under it. Judgment calls, kept short and listed in every report.
EQUIVALENT = {
    'cow': ['cattle', 'bull'], 'tv': ['television', 'computer monitor'], 'cell phone': ['mobile phone'],
    'potted plant': ['houseplant'], 'sports ball': ['ball'], 'remote': ['remote control'], 'frisbee': ['flying disc'],
    'skis': ['ski'], 'keyboard': ['computer keyboard'], 'microwave': ['microwave oven'], 'cup': ['coffee cup', 'mug'],
    'dining table': ['table'], 'donut': ['doughnut'], 'hair drier': ['hair dryer'], 'car': ['taxi', 'van', 'limousine'],
    'bowl': ['mixing bowl'], 'mouse': ['computer mouse'], 'knife': ['kitchen knife'],
}
SIZES = (('small', 0, 32 ** 2), ('medium', 32 ** 2, 96 ** 2), ('large', 96 ** 2, float('inf')))
MERGE_IOU = 0.7      # After mapping, two boxes of one COCO type on one object (car and taxi) are one box, as in evaluate.py.
PRECISION_TARGETS = (0.8, 0.9)


def coco_classes(vocabulary: dict | None = None, hierarchy_text: str | None = None) -> dict[int, str]:
    """App category ID -> COCO type name, for every app category that counts as one of the 80 types."""
    vocabulary = vocabulary or json.loads(VOCABULARY.read_text(encoding='utf-8'))
    names = [n.lower() for n in vocabulary['classes']]
    text = hierarchy_text if hierarchy_text is not None else HIERARCHY.read_text(encoding='utf-8')
    children = defaultdict(set)
    for child, ancestor in re.findall(r'\{(\d+),(\d+)\}', text):
        children[int(ancestor)].add(int(child))
    mapped: dict[int, str] = {}
    for coco_id in range(80):
        roots = {coco_id} | {names.index(n) for n in EQUIVALENT.get(names[coco_id], ()) if n in names}
        for app in roots | {c for r in roots for c in children[r]}:
            if app >= 80 or app == coco_id:      # Another COCO type is never an alias.
                mapped.setdefault(app, names[coco_id])
    return mapped


def load_truth(path: Path) -> tuple[dict[str, dict[str, list]], dict[str, tuple[int, int]]]:
    """file name -> COCO type -> [(box, crowd?, area)], and file name -> (width, height)."""
    coco = json.loads(path.read_text(encoding='utf-8'))
    name_of = {c['id']: c['name'] for c in coco['categories']}
    file_of = {i['id']: i['file_name'] for i in coco['images']}
    truth: dict[str, dict[str, list]] = {f: defaultdict(list) for f in file_of.values()}
    for a in coco['annotations']:
        x, y, w, h = a['bbox']
        truth[file_of[a['image_id']]][name_of[a['category_id']]].append(((x, y, x + w, y + h), bool(a.get('iscrowd', 0)), a['area']))
    return truth, {i['file_name']: (i['width'], i['height']) for i in coco['images']}


def read_predictions(path: Path, mapping: dict[int, str]) -> dict[str, dict[str, list]]:
    """file name -> COCO type -> [(score, box)], best first, duplicates after mapping merged."""
    out: dict[str, dict[str, list]] = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        by_type = defaultdict(list)
        for cid, score, box in sorted(row['detections'], key=lambda d: -d[1]):
            name = mapping.get(int(cid))
            if name and all(oi_metric._iou(k[1], box) <= MERGE_IOU for k in by_type[name]):
                by_type[name].append((float(score), tuple(box)))
        out[row['image']] = by_type
    return out


def match(detections: list, boxes: list) -> tuple[list[tuple[float, bool]], list[float]]:
    """One image, one type. Returns [(score, right?)] for the boxes that count and, per ordinary object, the score of
    the box that found it (0 when missed). A box inside a crowd region is neither right nor wrong."""
    ordinary = [b for b in boxes if not b[1]]
    crowds = [b[0] for b in boxes if b[1]]
    found = [0.0] * len(ordinary)
    results = []
    for score, box in detections:      # Best first.
        best, best_iou = -1, 0.5
        for i, truth in enumerate(ordinary):
            overlap = oi_metric._iou(box, truth[0])
            if not found[i] and overlap >= best_iou:
                best, best_iou = i, overlap
        if best >= 0:
            found[best] = score
            results.append((score, True))
        elif not any(oi_metric._ioa(box, crowd) >= 0.5 for crowd in crowds):
            results.append((score, False))
    return results, found


def score_model(truth: dict, predictions: dict, types: list[str]) -> dict:
    """Everything the report needs: per type the scored boxes and per-object found scores (with the object's area)."""
    per_type = {}
    for name in types:
        scored, objects = [], []
        for file_name, by_type in truth.items():
            boxes = by_type.get(name, [])
            detections = predictions.get(file_name, {}).get(name, [])
            if not boxes and not detections:
                continue
            results, found = match(detections, boxes)
            scored.extend(results)
            objects.extend(zip(found, (b[2] for b in boxes if not b[1])))
        count = len(objects)
        per_type[name] = {'scored': scored, 'objects': objects,
                          'ap': oi_metric.average_precision([s for s, _ in scored], [t for _, t in scored], count) if count else None}
    return per_type


def at(per_type: dict, threshold: float, names: list[str] | None = None) -> dict:
    """Recall and precision at one confidence setting, pooled over `names` (default: every type)."""
    names = names or list(per_type)
    right = sum(t for n in names for s, t in per_type[n]['scored'] if s >= threshold)
    shown = sum(1 for n in names for s, _ in per_type[n]['scored'] if s >= threshold)
    objects = sum(len(per_type[n]['objects']) for n in names)
    return {'found': right / objects if objects else None, 'right': right / shown if shown else None,
            'objects': objects, 'boxes': shown}


def by_size(per_type: dict, threshold: float) -> dict[str, tuple[float, int]]:
    out = {}
    for label, low, high in SIZES:
        objects = [f for v in per_type.values() for f, area in v['objects'] if low <= area < high]
        out[label] = (sum(f >= threshold for f in objects) / len(objects) if objects else 0.0, len(objects))
    return out


def found_at_precision(per_type: dict, target: float) -> tuple[float, float] | None:
    """(recall, threshold) at the lowest setting whose pooled precision is at least `target`."""
    for step in range(2, 100):
        threshold = step / 100
        point = at(per_type, threshold)
        if point['right'] is not None and point['right'] >= target:
            return point['found'], threshold
    return None


def pct(value: float | None) -> str:
    return '-' if value is None else f'{value:.0%}'


def report(models: dict[str, dict], settings: dict[str, float], reference: str) -> tuple[str, dict]:
    names = list(models)
    types = list(models[names[0]])
    summary = {}
    for name in names:
        per_type = models[name]
        aps = [v['ap'] for v in per_type.values() if v['ap'] is not None]
        point = at(per_type, settings[name])
        summary[name] = {'map50': sum(aps) / len(aps), 'setting': settings[name], **point,
                         'by_size': by_size(per_type, settings[name]),
                         'at_precision': {str(t): found_at_precision(per_type, t) for t in PRECISION_TARGETS}}
    target = summary[reference]['right']
    lines = ['# Yardstick A: COCO val2017 (complete labels, 80 everyday types)', '',
             '| | ' + ' | '.join(names) + ' |', '| --- | ' + ' | '.join('---:' for _ in names) + ' |',
             '| AP@0.5, mean over types | ' + ' | '.join(f"{summary[n]['map50']:.3f}" for n in names) + ' |',
             '| confidence setting | ' + ' | '.join(f"{summary[n]['setting']:.2f}" for n in names) + ' |',
             '| objects found at that setting | ' + ' | '.join(pct(summary[n]['found']) for n in names) + ' |',
             '| boxes right at that setting | ' + ' | '.join(pct(summary[n]['right']) for n in names) + ' |',
             '| boxes shown | ' + ' | '.join(str(summary[n]['boxes']) for n in names) + ' |']
    for label, _, _ in SIZES:
        lines.append(f'| found, {label} objects ({summary[names[0]]["by_size"][label][1]}) | ' +
                     ' | '.join(pct(summary[n]['by_size'][label][0]) for n in names) + ' |')
    for t in PRECISION_TARGETS:
        cells = []
        for n in names:
            hit = summary[n]['at_precision'][str(t)]
            cells.append(f'{hit[0]:.0%} (setting {hit[1]:.2f})' if hit else 'never reached')
        lines.append(f'| found when {t:.0%} of boxes are right | ' + ' | '.join(cells) + ' |')
    cells = []
    for n in names:
        hit = found_at_precision(models[n], target)
        summary[n]['at_reference_precision'] = hit
        cells.append(f'{hit[0]:.0%} (setting {hit[1]:.2f})' if hit else 'never reached')
    lines += [f'| found at {reference}\'s share right ({target:.0%}) | ' + ' | '.join(cells) + ' |', '',
              f'Objects: {summary[names[0]]["objects"]} (crowd regions excluded). Sizes are COCO\'s: small under 32x32 px, '
              'large from 96x96 px, in the original photo.', '',
              '## Per type (objects, then AP@0.5 / found / right at each model\'s setting)', '',
              '| type | objects | ' + ' | '.join(names) + ' |', '| --- | ---: | ' + ' | '.join('---' for _ in names) + ' |']
    per_type_summary = {}
    for kind in sorted(types, key=lambda k: -len(models[names[0]][k]['objects'])):
        cells = []
        per_type_summary[kind] = {}
        for n in names:
            point = at(models[n], settings[n], [kind])
            ap = models[n][kind]['ap']
            per_type_summary[kind][n] = {'ap': ap, 'found': point['found'], 'right': point['right']}
            cells.append(f"{ap:.2f} / {pct(point['found'])} / {pct(point['right'])}" if ap is not None else '-')
        lines.append(f"| {kind} | {len(models[names[0]][kind]['objects'])} | " + ' | '.join(cells) + ' |')
    return '\n'.join(lines) + '\n', {'models': summary, 'types': per_type_summary}


def predict_yolox(args) -> int:
    import teacher
    names = [n.lower() for n in json.loads(VOCABULARY.read_text(encoding='utf-8'))['classes']]
    index = {name: names.index(name) for name in teacher.coco_names()}
    model = teacher.YoloxTeacher(args.model, threads=args.threads)
    files = sorted(p for p in args.images.iterdir() if p.suffix.lower() in ('.jpg', '.jpeg', '.png'))
    done = set()
    if args.out.exists():
        done = {json.loads(line)['image'] for line in args.out.read_text(encoding='utf-8').splitlines() if line.strip()}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('a', encoding='utf-8') as handle:
        for number, path in enumerate(files, 1):
            if path.name in done:
                continue
            detections = model.detect(path, confidence=args.floor)
            handle.write(json.dumps({'image': path.name, 'detections': [[index[n], round(s, 5), [round(v, 1) for v in b]]
                                                                        for n, s, b in detections]}) + '\n')
            if number % 500 == 0:
                handle.flush()
                print(f'{number}/{len(files)}', flush=True)
    print(f'{args.out}: {len(files)} images')
    return 0


def score(args) -> int:
    mapping = coco_classes()
    truth, _ = load_truth(args.annotations)
    types = sorted({name for by_type in truth.values() for name in by_type})
    models, settings = {}, {}
    for spec in args.model:
        name, _, path = spec.partition('=')
        name, _, setting = name.partition('@')
        predictions = read_predictions(Path(path), mapping)
        missing = len(set(truth) - set(predictions))
        if missing:
            print(f'{name}: no predictions for {missing} of {len(truth)} images', file=sys.stderr)
        models[name] = score_model(truth, predictions, types)
        settings[name] = float(setting) if setting else args.setting
    text, summary = report(models, settings, args.reference or next(iter(models)))
    vocabulary = json.loads(VOCABULARY.read_text(encoding='utf-8'))['classes']
    extra = defaultdict(list)
    for app, name in sorted(mapping.items()):
        if app >= 80:
            extra[name].append(vocabulary[app])
    text += '\nApp categories counted for a COCO type besides the type itself: ' + \
        '; '.join(f'{k}: {", ".join(v)}' for k, v in sorted(extra.items())) + '.\n'
    summary['counted_for'] = extra
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding='utf-8')
        args.out.with_suffix('.json').write_text(json.dumps(summary, indent=1), encoding='utf-8')
    print(text[:text.index('## Per type')])
    return 0


def predict_rfdetr(args) -> int:
    """RF-DETR through rfdetr itself (needs a GPU machine): the stock COCO-pretrained model when --weights is not
    given, which shows what this architecture reaches on the 80 types, or one of our checkpoints."""
    import rfdetr
    import mix_coco
    vocabulary = json.loads(VOCABULARY.read_text(encoding='utf-8'))
    model_class = {'nano': rfdetr.RFDETRNano, 'small': rfdetr.RFDETRSmall, 'medium': rfdetr.RFDETRMedium,
                   'base': rfdetr.RFDETRBase, 'large': rfdetr.RFDETRLarge}[args.size]
    if args.weights:
        from checkpoints import head_classes
        model = model_class(pretrain_weights=str(args.weights), num_classes=head_classes(args.weights))
    else:
        model = model_class()
    files = sorted(p for p in args.images.iterdir() if p.suffix.lower() in ('.jpg', '.jpeg', '.png'))
    done = set()
    if args.out.exists():
        done = {json.loads(line)['image'] for line in args.out.read_text(encoding='utf-8').splitlines() if line.strip()}
    todo = [p for p in files if p.name not in done]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    column: dict[str, int | None] = {}
    kept = 0
    with args.out.open('a', encoding='utf-8') as handle:
        for start in range(0, len(todo), args.batch):
            chunk = todo[start:start + args.batch]
            results = model.predict([str(p) for p in chunk], threshold=args.floor, include_source_image=False)
            if not isinstance(results, list):
                results = [results]
            for path, detections in zip(chunk, results):
                rows = []
                for box, name, score in zip(detections.xyxy, detections.data.get('class_name', []), detections.confidence):
                    name = str(name)
                    if name not in column:
                        column[name] = mix_coco.app_column(name, vocabulary)
                    if column[name] is not None:
                        rows.append([column[name], round(float(score), 5), [round(float(v), 1) for v in box]])
                kept += len(rows)
                handle.write(json.dumps({'image': path.name, 'detections': rows}) + '\n')
            if (start // args.batch) % 50 == 0:
                handle.flush()
                print(f'{start + len(chunk)}/{len(todo)}', flush=True)
    unknown = sorted(name for name, col in column.items() if col is None)
    print(f'{args.out}: {len(files)} images, {kept} new detections' + (f'; class names without an app category: {unknown}' if unknown else ''))
    return 0 if kept or not todo else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True)
    run = commands.add_parser('predict-yolox', help='run YOLOX-S (the app\'s default model) on a folder of images')
    run.add_argument('--model', type=Path, required=True)
    run.add_argument('--images', type=Path, required=True)
    run.add_argument('--out', type=Path, required=True)
    run.add_argument('--floor', type=float, default=0.02, help='lowest score kept, so AP sees the whole range')
    run.add_argument('--threads', type=int, default=4)
    run.set_defaults(action=predict_yolox)
    run = commands.add_parser('predict-rfdetr', help='run RF-DETR through rfdetr: the stock COCO model, or a checkpoint of ours')
    run.add_argument('--weights', type=Path, help='a checkpoint of ours; default: the official COCO-pretrained weights')
    run.add_argument('--size', default='small', choices=('nano', 'small', 'medium', 'base', 'large'))
    run.add_argument('--images', type=Path, required=True)
    run.add_argument('--out', type=Path, required=True)
    run.add_argument('--floor', type=float, default=0.02)
    run.add_argument('--batch', type=int, default=16)
    run.set_defaults(action=predict_rfdetr)
    judge = commands.add_parser('score', help='score prediction files against COCO annotations')
    judge.add_argument('--annotations', type=Path, required=True)
    judge.add_argument('--model', action='append', required=True, help='NAME=predictions.jsonl, or NAME@0.30=... for its own setting')
    judge.add_argument('--setting', type=float, default=0.35, help='confidence setting, the app\'s default')
    judge.add_argument('--reference', help='model whose share right the others are compared at; default: the first')
    judge.add_argument('--out', type=Path, help='report (.md); the numbers go beside it as .json')
    judge.set_defaults(action=score)
    args = parser.parse_args(argv)
    return args.action(args)


if __name__ == '__main__':
    sys.exit(main())
