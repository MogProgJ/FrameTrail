"""Build an RF-DETR (Roboflow COCO layout) dataset from Open Images V7.

Output layout, as rfdetr expects:
    <out>/train/_annotations.coco.json + images
    <out>/valid/_annotations.coco.json + images
    <out>/test/_annotations.coco.json  + images
    <out>/dataset.json                 summary: classes, counts, settings

Each COCO image also stores the Open Images human-verified labels for our classes
(`oi_verified_positive` / `oi_verified_negative`, category ids). Open Images labels are
not exhaustive, so evaluation only scores a class on images where it was verified.
Each annotation keeps `oi_group_of` so group-of boxes can be scored the Open Images way.

Usage:
    python training/openimages.py --classes training/classes/pilot.txt --out data/pilot
    python training/openimages.py --classes training/classes/pilot.txt --out data/smoke --smoke
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import random
import sys
import time
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

GCS = 'https://storage.googleapis.com/openimages'
META = {
    'classes': f'{GCS}/v7/oidv7-class-descriptions-boxable.csv',
    'boxes': {'train': f'{GCS}/v6/oidv6-train-annotations-bbox.csv',
              'validation': f'{GCS}/v5/validation-annotations-bbox.csv',
              'test': f'{GCS}/v5/test-annotations-bbox.csv'},
    'labels': {'train': f'{GCS}/v7/oidv7-train-annotations-human-imagelabels.csv',
               'validation': f'{GCS}/v7/oidv7-val-annotations-human-imagelabels.csv',
               'test': f'{GCS}/v7/oidv7-test-annotations-human-imagelabels.csv'},
    'images': {'train': f'{GCS}/2018_04/train/train-images-boxable-with-rotation.csv',
               'validation': f'{GCS}/2018_04/validation/validation-images-with-rotation.csv',
               'test': f'{GCS}/2018_04/test/test-images-with-rotation.csv'},
}
IMAGE_URL = 'https://open-images-dataset.s3.amazonaws.com/{split}/{image_id}.jpg'
ROLES = ('test', 'valid', 'train')  # Selection order: held-out roles first when sources are shared.
DUPLICATE_IOU = 0.7  # Boxes of one merged class overlapping this much are the same object labelled twice.
MAX_PIXELS = 40_000_000


@dataclass(frozen=True)
class Category:
    id: int
    name: str
    sources: tuple[str, ...]  # Open Images display names merged into this category.


# ---------------------------------------------------------------- metadata

def fetch(url: str, cache: Path) -> Path:
    """Download url into cache once; partial downloads never look complete."""
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / url.rsplit('/', 1)[1]
    if target.exists():
        return target
    partial = target.with_suffix(target.suffix + '.part')
    print(f'Downloading {url}', flush=True)
    with urllib.request.urlopen(url, timeout=120) as response, partial.open('wb') as handle:
        while chunk := response.read(1 << 22):
            handle.write(chunk)
    partial.rename(target)
    return target


def parse_class_spec(path: Path, mid_by_name: dict[str, str]) -> list[Category]:
    """Read 'Target' or 'Target = Source, Source' lines; ids start at 1 in file order."""
    categories, seen_targets, seen_sources = [], set(), set()
    for number, raw in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        line = raw.split('#', 1)[0].strip()
        if not line:
            continue
        target, _, sources = (part.strip() for part in line.partition('='))
        names = tuple(s.strip() for s in sources.split(',')) if sources else (target,)
        unknown = [n for n in names if n not in mid_by_name]
        if unknown:
            raise ValueError(f'{path}:{number}: not Open Images boxable classes: {unknown}')
        if target in seen_targets or seen_sources.intersection(names):
            raise ValueError(f'{path}:{number}: duplicate target or source in {line!r}')
        seen_targets.add(target)
        seen_sources.update(names)
        categories.append(Category(len(categories) + 1, target, names))
    if not categories:
        raise ValueError(f'{path}: no classes')
    return categories


def read_class_descriptions(path: Path) -> dict[str, str]:
    import pandas as pd
    frame = pd.read_csv(path)
    return dict(zip(frame['DisplayName'], frame['LabelName']))


def load_boxes(path: Path, cat_by_mid: dict[str, int]):
    """Boxes of our classes as a DataFrame with a `cat` column; other classes are skipped while streaming."""
    import pandas as pd
    columns = ['ImageID', 'LabelName', 'XMin', 'XMax', 'YMin', 'YMax', 'IsGroupOf', 'IsDepiction']
    parts = []
    for chunk in pd.read_csv(path, usecols=columns, chunksize=2_000_000):
        chunk = chunk[chunk['LabelName'].isin(cat_by_mid.keys())]
        parts.append(chunk.assign(cat=chunk['LabelName'].map(cat_by_mid)).drop(columns='LabelName'))
    boxes = pd.concat(parts, ignore_index=True)
    boxes = boxes[(boxes.XMax > boxes.XMin) & (boxes.YMax > boxes.YMin)]
    return boxes.astype({'cat': 'int32', 'IsGroupOf': 'int8', 'IsDepiction': 'int8'})


def load_verified(path: Path, cat_by_mid: dict[str, int], image_ids: set[str]) -> dict[str, tuple[set[int], set[int]]]:
    """Human-verified presence (1) / absence (0) of our classes per image.

    A merged category is positive if any source is verified present, otherwise negative if
    any source is verified absent. That last rule can miss an unverified sibling (a Woman on
    an image verified to have no Man); the evaluator tolerates that small noise.
    """
    import pandas as pd
    verdict: dict[tuple[str, int], int] = {}
    for chunk in pd.read_csv(path, usecols=['ImageID', 'LabelName', 'Confidence'], chunksize=4_000_000):
        chunk = chunk[chunk['LabelName'].isin(cat_by_mid.keys()) & chunk['ImageID'].isin(image_ids)]
        for image_id, mid, confidence in zip(chunk['ImageID'], chunk['LabelName'], chunk['Confidence']):
            key = (image_id, cat_by_mid[mid])
            verdict[key] = max(verdict.get(key, 0), int(confidence >= 0.5))
    result: dict[str, tuple[set[int], set[int]]] = defaultdict(lambda: (set(), set()))
    for (image_id, cat), present in verdict.items():
        result[image_id][0 if present else 1].add(cat)
    return result


def rotated_images(path: Path) -> set[str]:
    """Images Open Images marks as needing rotation; their boxes would not match the stored pixels."""
    import pandas as pd
    frame = pd.read_csv(path, usecols=['ImageID', 'Rotation'])
    return set(frame.loc[frame['Rotation'].fillna(0) != 0, 'ImageID'])


# ---------------------------------------------------------------- selection

def iou(a, b) -> float:
    w = min(a[1], b[1]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[2], b[2])
    if w <= 0 or h <= 0:
        return 0.0
    inter = w * h
    return inter / ((a[1] - a[0]) * (a[3] - a[2]) + (b[1] - b[0]) * (b[3] - b[2]) - inter)


def deduplicate(boxes_by_image: dict[str, list[tuple]], merged: set[int]) -> int:
    """Drop near-identical boxes of the same merged category (e.g. one person boxed as Person and Man)."""
    removed = 0
    for image_id, boxes in boxes_by_image.items():
        kept = []
        for box in boxes:
            if box[0] in merged and any(k[0] == box[0] and iou(k[1:5], box[1:5]) > DUPLICATE_IOU for k in kept):
                removed += 1
                continue
            kept.append(box)
        boxes_by_image[image_id] = kept
    return removed


def select_images(boxes_by_image: dict[str, list[tuple]], categories: list[Category], cap: int,
                  seed: int, exclude: set[str]) -> list[str]:
    """Greedy class-balanced choice: rarest class first, up to `cap` images per class.

    A chosen image counts toward every class it contains, so common classes (people, cars)
    exceed the cap through co-occurrence. That is intended: they appear in real scenes.
    """
    rng = random.Random(seed)
    images_by_cat: dict[int, list[str]] = defaultdict(list)
    for image_id in sorted(boxes_by_image):
        if image_id in exclude:
            continue
        for cat in {box[0] for box in boxes_by_image[image_id]}:
            images_by_cat[cat].append(image_id)
    counts: dict[int, int] = defaultdict(int)
    chosen: list[str] = []
    chosen_set: set[str] = set()
    for category in sorted(categories, key=lambda c: (len(images_by_cat[c.id]), c.id)):
        candidates = images_by_cat[category.id][:]
        rng.shuffle(candidates)
        for image_id in candidates:
            if counts[category.id] >= cap:
                break
            if image_id in chosen_set:
                continue
            chosen.append(image_id)
            chosen_set.add(image_id)
            for cat in {box[0] for box in boxes_by_image[image_id]}:
                counts[cat] += 1
    return chosen


# ---------------------------------------------------------------- images

def download_image(image_id: str, split: str, target: Path) -> tuple[int, int] | str:
    """Fetch one original; return (width, height) or a reason it was skipped."""
    from PIL import Image
    if not target.exists():
        url = IMAGE_URL.format(split=split, image_id=image_id)
        data, reason = None, 'download failed'
        for attempt in range(3):
            try:
                with urllib.request.urlopen(url, timeout=60) as response:
                    data = response.read()
                break
            except Exception as error:  # Network errors are retried, then reported.
                reason = f'download: {error}'
                time.sleep(2 ** attempt)
        if data is None:
            return reason
        partial = target.with_suffix('.part')
        partial.write_bytes(data)
        partial.rename(target)
    try:
        with Image.open(target) as image:
            if image.width * image.height > MAX_PIXELS:
                return 'too large'
            if image.getexif().get(274, 1) != 1:
                return 'EXIF rotation'
            image.verify()
            return image.width, image.height
    except Exception as error:
        return f'decode: {error}'


def download_all(image_ids: list[str], split: str, folder: Path, workers: int) -> tuple[dict, dict]:
    folder.mkdir(parents=True, exist_ok=True)
    sizes, failures = {}, {}
    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        futures = {pool.submit(download_image, i, split, folder / f'{i}.jpg'): i for i in image_ids}
        for done, future in enumerate(concurrent.futures.as_completed(futures), 1):
            image_id = futures[future]
            result = future.result()
            if isinstance(result, tuple):
                sizes[image_id] = result
            else:
                failures[image_id] = result
                (folder / f'{image_id}.jpg').unlink(missing_ok=True)
            if done % 5000 == 0 or done == len(futures):
                print(f'  {split}: {done}/{len(futures)} images, {len(failures)} skipped', flush=True)
    return sizes, failures


# ---------------------------------------------------------------- COCO

def build_coco(image_ids: list[str], sizes: dict, boxes_by_image: dict, verified: dict,
               categories: list[Category]) -> dict:
    images, annotations = [], []
    for image_id in image_ids:
        if image_id not in sizes:
            continue
        width, height = sizes[image_id]
        number = len(images) + 1
        positive, negative = verified.get(image_id, (set(), set()))
        boxed = {box[0] for box in boxes_by_image[image_id]}
        positive = positive | boxed  # A box is proof of presence even without an image-level verdict.
        images.append({'id': number, 'file_name': f'{image_id}.jpg', 'width': width, 'height': height,
                       'oi_image_id': image_id,
                       'oi_verified_positive': sorted(positive),
                       'oi_verified_negative': sorted(negative - positive)})
        for cat, x0, x1, y0, y1, group_of, depiction in boxes_by_image[image_id]:
            x, y, w, h = x0 * width, y0 * height, (x1 - x0) * width, (y1 - y0) * height
            annotations.append({'id': len(annotations) + 1, 'image_id': number, 'category_id': cat,
                                'bbox': [round(x, 2), round(y, 2), round(w, 2), round(h, 2)],
                                'area': round(w * h, 2), 'iscrowd': 0,
                                'oi_group_of': int(group_of), 'oi_depiction': int(depiction)})
    return {'info': {'description': 'FrameTrail Open Images V7 subset'},
            'images': images, 'annotations': annotations,
            'categories': [{'id': c.id, 'name': c.name, 'supercategory': 'object'} for c in categories]}


# ---------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--classes', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--cache', type=Path, default=Path('data/openimages-metadata'))
    parser.add_argument('--train-cap', type=int, default=600, help='target images per class for training')
    parser.add_argument('--valid-cap', type=int, default=25)
    parser.add_argument('--test-cap', type=int, default=60)
    parser.add_argument('--seed', type=int, default=17)
    parser.add_argument('--workers', type=int, default=48, help='parallel image downloads')
    parser.add_argument('--smoke', action='store_true',
                        help='take every role from the small validation split (local pipeline test)')
    parser.add_argument('--plan-only', action='store_true',
                        help='select images and report counts without downloading images or image labels')
    args = parser.parse_args(argv)

    sources = {'train': 'train', 'valid': 'validation', 'test': 'test'}
    if args.smoke:
        sources = {role: 'validation' for role in sources}
    caps = {'train': args.train_cap, 'valid': args.valid_cap, 'test': args.test_cap}
    if args.out.exists() and any(args.out.iterdir()) and not (args.out / 'dataset.json').exists():
        print(f'{args.out} exists without dataset.json; resuming downloads into it.')

    mid_by_name = read_class_descriptions(fetch(META['classes'], args.cache))
    categories = parse_class_spec(args.classes, mid_by_name)
    cat_by_mid = {mid_by_name[name]: c.id for c in categories for name in c.sources}
    merged = {c.id for c in categories if len(c.sources) > 1}

    loaded: dict[str, tuple] = {}
    for split in sorted(set(sources.values())):
        boxes = load_boxes(fetch(META['boxes'][split], args.cache), cat_by_mid)
        skip = rotated_images(fetch(META['images'][split], args.cache))
        boxes = boxes[~boxes['ImageID'].isin(skip)]
        by_image: dict[str, list[tuple]] = defaultdict(list)
        for row in boxes.itertuples(index=False):
            by_image[row.ImageID].append((int(row.cat), float(row.XMin), float(row.XMax), float(row.YMin),
                                          float(row.YMax), int(row.IsGroupOf), int(row.IsDepiction)))
        removed = deduplicate(by_image, merged)
        print(f'{split}: {len(boxes)} boxes on {len(by_image)} images; {removed} duplicate merged boxes removed;'
              f' {len(skip)} rotated images skipped', flush=True)
        loaded[split] = (by_image, removed)

    summary = {'classes': [{'id': c.id, 'name': c.name, 'open_images': list(c.sources)} for c in categories],
               'settings': {k: str(v) for k, v in vars(args).items()}, 'sources': sources, 'roles': {}}
    used: dict[str, set[str]] = defaultdict(set)
    for role in ROLES:
        split = sources[role]
        by_image, _ = loaded[split]
        chosen = select_images(by_image, categories, caps[role], args.seed, used[split])
        used[split].update(chosen)
        if args.plan_only:
            per_class = defaultdict(lambda: [0, 0])
            for image_id in chosen:
                for cat in {box[0] for box in by_image[image_id]}:
                    per_class[cat][0] += 1
                for box in by_image[image_id]:
                    per_class[box[0]][1] += 1
            summary['roles'][role] = {'open_images_split': split, 'images': len(chosen),
                                      'boxes': sum(len(by_image[i]) for i in chosen),
                                      'images_and_boxes_per_class': {c.name: per_class[c.id] for c in categories}}
            print(f'{role}: {len(chosen)} images planned', flush=True)
            continue
        folder = args.out / role
        sizes, failures = download_all(chosen, split, folder, args.workers)
        verified = load_verified(fetch(META['labels'][split], args.cache), cat_by_mid, set(sizes))
        coco = build_coco(chosen, sizes, by_image, verified, categories)
        (folder / '_annotations.coco.json').write_text(json.dumps(coco), encoding='utf-8')
        per_class = defaultdict(lambda: [0, 0])
        for image in coco['images']:
            for cat in image['oi_verified_positive']:
                per_class[cat][0] += 1
        for annotation in coco['annotations']:
            per_class[annotation['category_id']][1] += 1
        summary['roles'][role] = {
            'open_images_split': split, 'images': len(coco['images']), 'boxes': len(coco['annotations']),
            'skipped_images': len(failures), 'skip_reasons': sorted({r.split(':')[0] for r in failures.values()}),
            'images_and_boxes_per_class': {c.name: per_class[c.id] for c in categories}}
        print(f'{role}: {len(coco["images"])} images, {len(coco["annotations"])} boxes, '
              f'{len(failures)} skipped', flush=True)
    args.out.mkdir(parents=True, exist_ok=True)
    name = 'plan.json' if args.plan_only else 'dataset.json'
    (args.out / name).write_text(json.dumps(summary, indent=1), encoding='utf-8')
    empty = [c.name for c in categories if summary['roles']['train']['images_and_boxes_per_class'][c.name][1] == 0]
    if empty:
        print(f'Warning: classes without training boxes: {empty}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
