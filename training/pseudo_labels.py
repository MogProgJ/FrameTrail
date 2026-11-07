"""Round 3: fill in Open Images' missing labels with a teacher model (YOLOX-S, see teacher.py).

Open Images labels some objects on each photo and leaves the rest unmarked. Training treats every unmarked object as
background, so a model learns that handbags, backpacks, umbrellas and even people are "nothing" whenever the
annotators did not look for them. The Phase 2 model shows it: on Open Images test photos it finds handbags well
(AP 0.74, scored only where handbags were checked), but on street footage it finds none that YOLOX-S sees.

A box is only ever added for a class the annotators did NOT verify on that image (neither present nor absent), so
human labels stay authoritative. A teacher box is skipped when it overlaps a box already on the image.

Three steps, each reading what the last one wrote:

    run      teacher detections for every image of a split, saved as JSON lines (resumable)
    measure  precision of the teacher per class, on the validation split, against the human-verified labels
    fill     rewrite train/_annotations.coco.json with the teacher's boxes for classes that measured precise enough
             (the original is kept as _annotations.original.json; running fill again starts from it)

    python training/pseudo_labels.py run     --dataset data/full --split valid --teacher weights/yolox_s.onnx
    python training/pseudo_labels.py measure --dataset data/full --split valid --out runs/round3/teacher-measure.json
    python training/pseudo_labels.py run     --dataset data/full --split train --teacher weights/yolox_s.onnx
    python training/pseudo_labels.py fill    --dataset data/full --measure runs/round3/teacher-measure.json
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import oi_metric  # noqa: E402
import teacher as yolox  # noqa: E402

# COCO class names the dataset names differently (Open Images display names). Applied only when the target exists.
ALIASES = {'cow': 'cattle', 'tv': 'television', 'cell phone': 'mobile phone', 'potted plant': 'houseplant',
           'sports ball': 'ball', 'remote': 'remote control', 'frisbee': 'flying disc', 'skis': 'ski',
           'keyboard': 'computer keyboard', 'microwave': 'microwave oven'}
OVERLAP = 0.6        # A teacher box this much on top of a box already on the image is the same object.
MIN_SIDE = 0.01      # Smaller than this fraction of the image's long side: too small to label reliably.
CACHE_SCORE = 0.3    # The teacher's detections are kept from this score up, so thresholds can change without a rerun.
THRESHOLDS = (0.4, 0.5, 0.6, 0.7, 0.8)


# ---------------------------------------------------------------- class mapping

def class_map(coco: dict, summary: dict | None = None, names: list[str] | None = None) -> dict[str, int]:
    """Teacher (COCO) class name -> dataset category id, for every teacher class the dataset has."""
    known = {c['name'].lower(): int(c['id']) for c in coco['categories']}
    for entry in (summary or {}).get('classes', ()):
        for source in entry.get('open_images', ()):
            known.setdefault(source.lower(), int(entry['id']))
    mapped = {}
    for name in names or yolox.coco_names():
        target = known.get(name) or known.get(ALIASES.get(name, ''))
        if target is not None:
            mapped[name] = target
    return mapped


# ---------------------------------------------------------------- teacher run

def read_cache(path: Path) -> dict[str, list]:
    if not path.exists():
        return {}
    records = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.strip():
            row = json.loads(line)
            records[row['image']] = [(d[0], float(d[1]), tuple(d[2])) for d in row['detections']]
    return records


def run_teacher(dataset: Path, split: str, model: Path, cache: Path, threads: int, limit: int | None) -> None:
    coco = json.loads((dataset / split / '_annotations.coco.json').read_text(encoding='utf-8'))
    files = sorted(image['file_name'] for image in coco['images'])[:limit]
    done = read_cache(cache)
    todo = [f for f in files if f not in done]
    print(f'{split}: {len(files)} images, {len(done)} already done, {len(todo)} to run', flush=True)
    if not todo:
        return
    teacher = yolox.YoloxTeacher(model, threads=threads)
    cache.parent.mkdir(parents=True, exist_ok=True)
    started = time.time()

    def detect(name: str):
        try:
            return name, teacher.detect(dataset / split / name, CACHE_SCORE), None
        except Exception as error:  # A damaged image gets no teacher boxes, and counts as done.
            print(f'  no teacher output for {name}: {error}', flush=True)
            return name, [], str(error)

    with cache.open('a', encoding='utf-8') as handle, concurrent.futures.ThreadPoolExecutor(max(1, threads // 2)) as pool:
        for count, (name, detections, error) in enumerate(pool.map(detect, todo), 1):
            record = {'image': name, 'detections': [[n, round(s, 4), [round(v, 1) for v in b]] for n, s, b in detections]}
            if error:
                record['error'] = error
            handle.write(json.dumps(record) + '\n')
            if count % 500 == 0 or count == len(todo):
                handle.flush()
                rate = count / (time.time() - started)
                print(f'  {count}/{len(todo)} images, {rate:.1f}/s, about {(len(todo) - count) / rate / 60:.0f} min left',
                      flush=True)


# ---------------------------------------------------------------- measure

def measure_precision(truth: dict[str, oi_metric.ImageTruth], detections: dict[str, list], targets: dict[str, int],
                      thresholds=THRESHOLDS) -> dict[str, dict]:
    """Per teacher class and threshold: its boxes on images where the class was human-verified, split into right and wrong.

    Verified absent: every box is wrong. Verified present: a box is right when it overlaps a human box of the class at
    IoU 0.5 or lies mostly inside a group-of box, otherwise wrong (human boxes may be incomplete, so this is a little
    harsh). Images where the class was not verified are skipped here; those are the ones fill adds boxes to.
    """
    counts: dict[str, dict[float, list[int]]] = {n: {t: [0, 0] for t in thresholds} for n in targets}
    for image, found in detections.items():
        info = truth.get(image)
        if info is None:
            continue
        for name, score, box in found:
            category = targets.get(name)
            if category is None or (category not in info.positive and category not in info.negative):
                continue
            right = False
            if category in info.positive:
                right = any(b[0] == category and (oi_metric._ioa(box, b[1:5]) >= 0.5 if b[5]
                                                  else oi_metric._iou(box, b[1:5]) >= 0.5) for b in info.boxes)
            for t in thresholds:
                if score >= t:
                    counts[name][t][0 if right else 1] += 1
    return {name: {str(t): {'right': r, 'wrong': w} for t, (r, w) in by_threshold.items()}
            for name, by_threshold in counts.items()}


def choose_thresholds(measured: dict[str, dict], min_precision: float, min_checked: int) -> dict[str, dict]:
    """Per class, the lowest measured threshold whose precision is high enough on enough checked boxes."""
    chosen = {}
    for name, by_threshold in measured.items():
        for t in sorted(by_threshold, key=float):
            right, wrong = by_threshold[t]['right'], by_threshold[t]['wrong']
            if right + wrong >= min_checked and right / (right + wrong) >= min_precision:
                chosen[name] = {'threshold': float(t), 'precision': round(right / (right + wrong), 3),
                                'checked': right + wrong}
                break
    return chosen


# ---------------------------------------------------------------- fill

def _iou(a, b) -> float:
    return oi_metric._iou(a, b)


def new_boxes(image: dict, boxes: list[tuple], detections: list, targets: dict[str, int],
              thresholds: dict[int, float]) -> list[tuple[int, float, tuple]]:
    """Teacher boxes to add to one image: (category, score, xyxy).

    `boxes` are the boxes already on the image (xyxy). A class the annotators verified on the image, present or
    absent, is never touched; a box overlapping an existing or just-accepted box is the same object; boxes under the
    class threshold or too small are dropped.
    """
    verified = set(image.get('oi_verified_positive', ())) | set(image.get('oi_verified_negative', ()))
    smallest = MIN_SIDE * max(image['width'], image['height'])
    taken, added = list(boxes), []
    for name, score, box in sorted(detections, key=lambda d: -d[1]):
        category = targets.get(name)
        if category is None or category in verified or category not in thresholds or score < thresholds[category]:
            continue
        if box[2] - box[0] < smallest or box[3] - box[1] < smallest:
            continue
        if any(_iou(box, other) > OVERLAP for other in taken):
            continue
        taken.append(box)
        added.append((category, score, box))
    return added


def fill(coco: dict, cache: dict[str, list], targets: dict[str, int], thresholds: dict[int, float]) -> tuple[dict, dict]:
    """A copy of `coco` with the teacher's boxes added, and a report of what was added."""
    annotations = [dict(a) for a in coco['annotations']]
    by_image: dict[int, list[tuple]] = defaultdict(list)
    for a in annotations:
        x, y, w, h = a['bbox']
        by_image[a['image_id']].append((x, y, x + w, y + h))
    names = {c['id']: c['name'] for c in coco['categories']}
    images, per_class = [], defaultdict(lambda: [0, set()])
    next_id = max((a['id'] for a in annotations), default=0) + 1
    unmatched = 0
    for image in coco['images']:
        image = dict(image)
        found = cache.get(image['file_name'])
        if found is None:
            unmatched += 1
            images.append(image)
            continue
        added = new_boxes(image, by_image[image['id']], found, targets, thresholds)
        for category, score, (x0, y0, x1, y1) in added:
            annotations.append({'id': next_id, 'image_id': image['id'], 'category_id': category,
                                'bbox': [round(x0, 2), round(y0, 2), round(x1 - x0, 2), round(y1 - y0, 2)],
                                'area': round((x1 - x0) * (y1 - y0), 2), 'iscrowd': 0, 'oi_group_of': 0,
                                'oi_depiction': 0, 'oi_pseudo': 1, 'oi_score': round(score, 3)})
            next_id += 1
            per_class[category][0] += 1
            per_class[category][1].add(image['id'])
        if added:  # These classes now have boxes on the image, so they count as present (training only).
            image['oi_verified_positive'] = sorted(set(image.get('oi_verified_positive', ())) | {c for c, _, _ in added})
        images.append(image)
    report = {'images': len(images), 'images_without_teacher_output': unmatched,
              'boxes_before': len(coco['annotations']), 'boxes_added': len(annotations) - len(coco['annotations']),
              'per_class': {names[c]: {'boxes': n, 'images': len(seen), 'threshold': thresholds[c]}
                            for c, (n, seen) in sorted(per_class.items(), key=lambda kv: -kv[1][0])}}
    return {**coco, 'images': images, 'annotations': annotations}, report


# ---------------------------------------------------------------- audit

def write_audit(dataset: Path, out: Path, count: int, seed: int, classes: str | None) -> int:
    """Pictures of training images with what was added, for a human to judge: human boxes green, teacher boxes orange."""
    import random
    from PIL import Image, ImageDraw
    coco = json.loads((dataset / 'train' / '_annotations.coco.json').read_text(encoding='utf-8'))
    names = {c['id']: c['name'] for c in coco['categories']}
    wanted = {n.strip().lower() for n in classes.split(',')} if classes else None
    added = defaultdict(list)
    for a in coco['annotations']:
        if a.get('oi_pseudo') and (not wanted or names[a['category_id']].lower() in wanted):
            added[a['image_id']].append(a)
    pictures = sorted(added)
    random.Random(seed).shuffle(pictures)
    by_id = {i['id']: i for i in coco['images']}
    boxes = defaultdict(list)
    for a in coco['annotations']:
        boxes[a['image_id']].append(a)
    out.mkdir(parents=True, exist_ok=True)
    for number, image_id in enumerate(pictures[:count], 1):
        info = by_id[image_id]
        with Image.open(dataset / 'train' / info['file_name']) as source:
            picture = source.convert('RGB')
        draw = ImageDraw.Draw(picture)
        width = max(2, picture.width // 250)
        for a in boxes[image_id]:
            x, y, w, h = a['bbox']
            colour = (255, 150, 0) if a.get('oi_pseudo') else (60, 220, 90)
            draw.rectangle((x, y, x + w, y + h), outline=colour, width=width)
            draw.text((x + 3, y + 2), names[a['category_id']] + (f" {a['oi_score']:.2f}" if a.get('oi_pseudo') else ''), fill=colour)
        picture.thumbnail((900, 900))
        picture.save(out / f'{number:02d}-{info["file_name"]}', quality=88)
    print(f'Wrote {min(count, len(pictures))} pictures of {len(pictures)} images with added boxes to {out}')
    return 0


# ---------------------------------------------------------------- command line

def load_split(dataset: Path, split: str) -> dict:
    """A split's annotations as the humans made them (the original, once fill has rewritten the file)."""
    folder = dataset / split
    original = folder / '_annotations.original.json'
    return json.loads((original if original.exists() else folder / '_annotations.coco.json').read_text(encoding='utf-8'))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('run', 'measure', 'fill', 'status'):
        p = sub.add_parser(name)
        p.add_argument('--dataset', type=Path, required=True)
        p.add_argument('--cache', type=Path, help='teacher detections (default <dataset>/teacher-<split>.jsonl)')
        if name != 'fill':
            p.add_argument('--split', default='train' if name != 'measure' else 'train,valid',
                           help='train, valid or test' + ('; measure accepts a comma-separated list' if name == 'measure' else ''))
    audit = sub.add_parser('audit', help='draw some training images: human boxes green, added boxes orange')
    audit.add_argument('--dataset', type=Path, required=True)
    audit.add_argument('--out', type=Path, required=True)
    audit.add_argument('--count', type=int, default=24)
    audit.add_argument('--seed', type=int, default=3)
    audit.add_argument('--classes', help='comma-separated class names the images must have added boxes of')
    sub.choices['run'].add_argument('--teacher', type=Path, required=True, help='yolox_s.onnx')
    sub.choices['run'].add_argument('--threads', type=int, default=os.cpu_count() or 4)
    sub.choices['run'].add_argument('--limit', type=int, help='only the first N images (quick checks)')
    sub.choices['measure'].add_argument('--out', type=Path, required=True)
    sub.choices['fill'].add_argument('--measure', type=Path, help='the measure step\'s file: per-class thresholds')
    sub.choices['fill'].add_argument('--min-precision', type=float, default=0.8)
    sub.choices['fill'].add_argument('--min-checked', type=int, default=15,
                                     help='a class needs this many teacher boxes on verified images to be trusted')
    sub.choices['fill'].add_argument('--threshold', type=float,
                                     help='one threshold for every mapped class instead of measured ones (not advised)')
    sub.choices['fill'].add_argument('--only', help='comma-separated class names: add boxes for these only')
    sub.choices['fill'].add_argument('--report', type=Path, help='default <dataset>/pseudo_labels.json')
    args = parser.parse_args(argv)

    if args.command == 'audit':
        return write_audit(args.dataset, args.out, args.count, args.seed, args.classes)
    summary_path = args.dataset / 'dataset.json'
    summary = json.loads(summary_path.read_text(encoding='utf-8')) if summary_path.exists() else None
    split = getattr(args, 'split', 'train')
    cache = args.cache or args.dataset / f'teacher-{split.split(",")[0]}.jsonl'

    if args.command == 'status':  # Exit status 0 when the teacher has run on every image of the split.
        coco = load_split(args.dataset, split)
        done = read_cache(cache)
        total = len(coco['images'])
        finished = sum(1 for image in coco['images'] if image['file_name'] in done)
        print(f'{split}: teacher has run on {finished} of {total} images')
        return 0 if finished == total else 3

    if args.command == 'run':
        run_teacher(args.dataset, split, args.teacher, cache, args.threads, args.limit)
        return 0

    if args.command == 'measure':
        truth, detections, targets = {}, {}, {}
        for part in split.split(','):
            coco = load_split(args.dataset, part)
            part_truth, _ = oi_metric.truth_from_coco(coco)
            truth.update(part_truth)  # Open Images file names are unique across splits.
            targets = targets or class_map(coco, summary)
            detections.update(read_cache(args.cache if args.cache and ',' not in split else args.dataset / f'teacher-{part}.jsonl'))
        measured = measure_precision(truth, {k: v for k, v in detections.items() if k in truth}, targets)
        result = {'splits': split.split(','), 'images': len(detections), 'mapped_classes': targets,
                  'thresholds': list(THRESHOLDS), 'measured': measured}
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=1), encoding='utf-8')
        print(f'{"class":24s} ' + ' '.join(f'>={t:.1f}      ' for t in THRESHOLDS))
        for name, by_threshold in sorted(measured.items(), key=lambda kv: -sum(v['right'] + v['wrong'] for v in
                                                                              kv[1].values())):
            cells = []
            for t in THRESHOLDS:
                right, wrong = by_threshold[str(t)]['right'], by_threshold[str(t)]['wrong']
                cells.append(f'{right / (right + wrong):4.0%} of {right + wrong:<4d}' if right + wrong else '    -       ')
            if any(by_threshold[str(t)]['right'] + by_threshold[str(t)]['wrong'] for t in THRESHOLDS):
                print(f'{name:24s} ' + ' '.join(cells))
        return 0

    # fill
    train = args.dataset / 'train'
    original, current = train / '_annotations.original.json', train / '_annotations.coco.json'
    if not original.exists():
        original.write_text(current.read_text(encoding='utf-8'), encoding='utf-8')  # First time: keep the human labels.
    coco = json.loads(original.read_text(encoding='utf-8'))
    targets = class_map(coco, summary)
    if args.measure:
        measured = json.loads(args.measure.read_text(encoding='utf-8'))['measured']
        chosen = choose_thresholds(measured, args.min_precision, args.min_checked)
        thresholds = {targets[name]: info['threshold'] for name, info in chosen.items() if name in targets}
        print(f'{len(thresholds)} of {len(targets)} teacher classes are precise enough (precision >= '
              f'{args.min_precision:.0%} on >= {args.min_checked} checked boxes).')
    elif args.threshold:
        thresholds = {category: args.threshold for category in targets.values()}
        chosen = {}
    else:
        parser.error('fill needs --measure (advised) or --threshold')
    if args.only:
        wanted = {name.strip().lower() for name in args.only.split(',')}
        thresholds = {c: t for c, t in thresholds.items() if {n for n, i in targets.items() if i == c} & wanted}
    detections = read_cache(cache)
    if not detections:
        parser.error(f'no teacher detections in {cache}; run the "run" step first')
    filled, report = fill(coco, detections, targets, thresholds)
    current.write_text(json.dumps(filled), encoding='utf-8')
    report.update({'teacher': 'YOLOX-S 0.1.1rc0', 'overlap_skip_iou': OVERLAP, 'min_side_fraction': MIN_SIDE,
                   'class_precision_on_verified_images': chosen})
    (args.report or args.dataset / 'pseudo_labels.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
    print(f"Added {report['boxes_added']} boxes to {report['images']} training images "
          f"(there were {report['boxes_before']}); {report['images_without_teacher_output']} images had no teacher output.")
    for name, info in list(report['per_class'].items())[:15]:
        print(f"  {name:22s} {info['boxes']:6d} boxes on {info['images']:5d} images (teacher score >= {info['threshold']})")
    return 0


if __name__ == '__main__':
    sys.exit(main())
