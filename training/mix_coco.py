"""Add COCO's fully labelled photos to an Open Images dataset built by openimages.py (round 4).

Open Images labels a few classes per photo; everything else is unknown, and plain training reads "unknown" as
"absent". COCO train2017 labels every object of 80 everyday types on every photo. This puts both in one training
set and records, per image, what its labels vouch for, so `train.py --unverified-weight` (missing_labels.py) can
treat each source correctly:

- a COCO box goes to the training class that means the same thing (cow -> Cattle, dining table -> Table, tv ->
  Television; see PRIMARY), or to the same-named class. Cup gets a class of its own, because Open Images only has
  Coffee cup and Mug;
- on a COCO photo each of the 80 types is verified: present where it has boxes, absent where it has none;
- narrower classes of a type (Taxi and Van for car, Raven for bird, Mug for cup) are absent where the type is
  absent, and unknown (not pushed either way) where it is present: COCO does not say which kind it is;
- a type that only appears as a crowd region is unknown, and a type with boxes and a crowd keeps its boxes but is
  not pushed towards "absent" elsewhere on that photo;
- two types do not line up with one class. COCO's "tv" lumps televisions and computer monitors, which are
  different classes here: its boxes are not used, and both classes are unknown where a tv is present and absent
  where none is (UNION). Our Table is wider than COCO's "dining table" (desks, side tables): dining-table boxes
  are used, but a COCO photo never says "no Table here" (BROADER);
- every other class (footwear, tree, ...) stays unverified on COCO photos, as on Open Images photos;
- on Open Images photos, a type's main class is unknown where one of its narrower classes is present (Computer
  monitor present: Television is not pushed down; Mug present: Cup is not pushed down).

Which classes count as a COCO type is the same table yardstick A scores with (coco_yardstick.coco_classes).
COCO val2017 is never used here: it is the held-out yardstick.

    python training/mix_coco.py shrink --dataset data/full                    # Open Images train photos to 640 px
    python training/mix_coco.py add --dataset data/full --annotations data/coco/annotations/instances_train2017.json
    python training/mix_coco.py add ... --plan-only                           # numbers only, nothing downloaded
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import shutil
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

import coco_yardstick

IMAGE_URL = 'http://images.cocodataset.org/train2017/{file}'
PREFIX = 'coco_'                              # File names of COCO photos in train/, so they never clash.
BACKUP = '_annotations.openimages.json'       # The training annotations before COCO was added.
ROLES = ('train', 'valid', 'test')
# COCO type -> training class, where the names differ. Open Images' Mouse is the animal.
PRIMARY = {
    'cow': 'Cattle', 'frisbee': 'Flying disc', 'skis': 'Ski', 'sports ball': 'Ball', 'cup': 'Cup',
    'donut': 'Doughnut', 'potted plant': 'Houseplant', 'dining table': 'Table', 'tv': 'Television',
    'mouse': 'Computer mouse', 'remote': 'Remote control', 'keyboard': 'Computer keyboard',
    'cell phone': 'Mobile phone', 'microwave': 'Microwave oven', 'hair drier': 'Hair dryer',
}
UNION = {'tv'}                                # Types that lump classes which are different things: no boxes from them.
BROADER = {'dining table'}                    # Types whose class is wider than the type: boxes, but no "absent".
NEW_CLASSES = {'cup': 'Cup'}                  # COCO types without any class of their own: added to the dataset.
NOT_NARROWER = {'mouse'}                      # Class names (lower-case) that share an app category with a COCO type by accident.


def app_column(name: str, vocabulary: dict) -> int | None:
    """App category of a training class name, as export.py maps it."""
    key = name.lower()
    labels = {label.lower(): column for label, column in zip(vocabulary['openimages_labels'], vocabulary['openimages_ids'])}
    if key in labels:
        return int(labels[key])
    names = [n.lower() for n in vocabulary['classes']]
    return names.index(key) if key in names else None


def class_map(categories: list[dict], vocabulary: dict | None = None,
              hierarchy_text: str | None = None) -> dict[str, tuple[int, list[int]]]:
    """COCO type name -> (category id of its main class, ids of its narrower classes). Types the class list
    lacks are left out: their boxes are not used and nothing is vouched for them."""
    vocabulary = vocabulary or json.loads(coco_yardstick.VOCABULARY.read_text(encoding='utf-8'))
    type_of_column = coco_yardstick.coco_classes(vocabulary, hierarchy_text)
    by_name = {c['name'].lower(): int(c['id']) for c in categories}
    family = defaultdict(set)
    for category in categories:
        coco_type = type_of_column.get(app_column(category['name'], vocabulary))
        if coco_type and category['name'].lower() not in NOT_NARROWER:
            family[coco_type].add(int(category['id']))
    mapping, owner = {}, {}
    for coco_type in (n.lower() for n in vocabulary['classes'][:80]):
        primary = by_name.get(PRIMARY.get(coco_type, coco_type).lower())
        if primary is None:
            continue
        narrower = sorted(family[coco_type] - {primary})
        for cat in (primary, *narrower):
            if owner.setdefault(cat, coco_type) != coco_type:
                raise ValueError(f'category {cat} would count for both {owner[cat]} and {coco_type}')
        mapping[coco_type] = (primary, narrower)
    return mapping


def convert(coco: dict, mapping: dict[str, tuple[int, list[int]]]) -> tuple[list[dict], dict]:
    """COCO annotations -> one record per usable photo: boxes in our categories and what the photo vouches for."""
    type_of = {int(c['id']): c['name'].lower() for c in coco['categories']}
    boxes, present, crowds = defaultdict(list), defaultdict(set), defaultdict(set)
    dropped = Counter()
    for a in coco['annotations']:
        coco_type = type_of[int(a['category_id'])]
        image_id = int(a['image_id'])
        if coco_type not in mapping:
            dropped['boxes of types without a class'] += 1
            continue
        x, y, w, h = (float(v) for v in a['bbox'])
        if a.get('iscrowd', 0):
            crowds[image_id].add(coco_type)
        elif w < 1 or h < 1:
            dropped['boxes under 1 px'] += 1
            crowds[image_id].add(coco_type)                # Something is there, so the type is not "absent".
        elif coco_type in UNION:
            dropped['boxes of types that lump several classes'] += 1
            present[image_id].add(coco_type)
        else:
            present[image_id].add(coco_type)
            boxes[image_id].append((coco_type, x, y, w, h))
    records = []
    for image in sorted(coco['images'], key=lambda i: int(i['id'])):
        image_id = int(image['id'])
        if not boxes[image_id]:
            dropped['photos without a usable box'] += 1
            continue
        positive, negative, unknown = set(), set(), set()
        for coco_type, (primary, narrower) in mapping.items():
            family = (primary, *narrower)
            there, crowd = coco_type in present[image_id], coco_type in crowds[image_id]
            if coco_type in UNION:
                (unknown if there or crowd else negative).update(family)
            elif coco_type in BROADER:
                unknown.update(family)
                if there:
                    positive.add(primary)
            elif there:
                positive.add(primary)
                unknown.update(narrower)
                if crowd:
                    unknown.add(primary)
            elif crowd:
                unknown.update(family)
            else:
                negative.update(family)
        records.append({'file': image['file_name'], 'width': int(image['width']), 'height': int(image['height']),
                        'coco_id': image_id, 'positive': positive, 'negative': negative, 'unknown': unknown,
                        'boxes': [(mapping[t][0], x, y, w, h) for t, x, y, w, h in boxes[image_id]]})
    return records, dict(dropped)


def select(records: list[dict], cap: int | None) -> list[dict]:
    """At most about `cap` photos per class, rarest class first (as openimages.py selects); all of them without a cap."""
    if not cap:
        return records
    holders = defaultdict(list)
    for index, record in enumerate(records):
        for cat in record['positive']:
            holders[cat].append(index)
    chosen, count = set(), Counter()
    for cat in sorted(holders, key=lambda c: (len(holders[c]), c)):
        for index in holders[cat]:
            if count[cat] >= cap:
                break
            if index not in chosen:
                chosen.add(index)
                count.update(records[index]['positive'])
    return [records[i] for i in sorted(chosen)]


def fetch_image(record: dict, folder: Path, url: str, source: Path | None) -> str | None:
    """Put one COCO photo into the training folder; return why it was skipped, or None."""
    from PIL import Image
    target = folder / (PREFIX + record['file'])
    if not target.exists():
        partial = target.with_suffix('.part')
        if source is not None:
            if not (source / record['file']).is_file():
                return 'not in --images-dir'
            shutil.copyfile(source / record['file'], partial)
        else:
            data, reason = None, 'download failed'
            for attempt in range(4):
                try:
                    with urllib.request.urlopen(url.format(file=record['file']), timeout=60) as response:
                        data = response.read()
                    break
                except Exception as error:  # Network errors are retried, then reported.
                    reason = f'download: {error}'
                    time.sleep(2 ** attempt)
            if data is None:
                return reason
            partial.write_bytes(data)
        partial.replace(target)
    try:
        with Image.open(target) as image:
            if image.size != (record['width'], record['height']):
                return f'size {image.size} differs from the annotations'
            if image.getexif().get(274, 1) != 1:
                return 'EXIF rotation'
            image.verify()
    except Exception as error:
        return f'decode: {error}'
    return None


def fetch_all(records: list[dict], folder: Path, url: str, source: Path | None, workers: int) -> dict[str, str]:
    failures = {}
    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        futures = {pool.submit(fetch_image, r, folder, url, source): r for r in records}
        for done, future in enumerate(concurrent.futures.as_completed(futures), 1):
            reason = future.result()
            if reason:
                record = futures[future]
                failures[record['file']] = reason
                (folder / (PREFIX + record['file'])).unlink(missing_ok=True)
            if done % 10000 == 0 or done == len(futures):
                print(f'  COCO: {done}/{len(futures)} photos, {len(failures)} skipped', flush=True)
    return failures


def with_new_classes(categories: list[dict], coco_types: set[str]) -> tuple[list[dict], list[str]]:
    """The category list plus the classes NEW_CLASSES adds for COCO types the annotations contain."""
    names = {c['name'].lower() for c in categories}
    added = [name for coco_type, name in NEW_CLASSES.items() if coco_type in coco_types and name.lower() not in names]
    next_id = max(int(c['id']) for c in categories) + 1
    return (categories + [{'id': next_id + i, 'name': name, 'supercategory': 'object'} for i, name in enumerate(added)],
            added)


def mark_open_images(images: list[dict], mapping: dict[str, tuple[int, list[int]]]) -> int:
    """On Open Images photos: a type's main class is unknown where a narrower class of it is present."""
    marked = 0
    for image in images:
        positive = set(image.get('oi_verified_positive', ()))
        verified = positive | set(image.get('oi_verified_negative', ()))
        unknown = {primary for primary, narrower in mapping.values()
                   if primary not in verified and positive.intersection(narrower)}
        if unknown:
            image['oi_unknown'] = sorted(unknown)
            marked += 1
    return marked


def add(args) -> int:
    train = args.dataset / 'train'
    path, backup = train / '_annotations.coco.json', train / BACKUP
    base = json.loads((backup if backup.exists() else path).read_text(encoding='utf-8'))   # Always from the original.
    if base.get('info', {}).get('mix'):
        raise SystemExit(f'{backup if backup.exists() else path} already holds COCO photos')
    coco = json.loads(args.annotations.read_text(encoding='utf-8'))
    categories, added = with_new_classes(base['categories'], {c['name'].lower() for c in coco['categories']})
    mapping = class_map(categories)
    missing = sorted(c['name'] for c in coco['categories'] if c['name'].lower() not in mapping)
    records, dropped = convert(coco, mapping)
    usable = len(records)
    records = select(records, args.cap)
    name_of = {int(c['id']): c['name'] for c in categories}
    per_class = Counter(cat for r in records for cat, *_ in r['boxes'])
    summary = {'source': 'COCO train2017', 'annotations': str(args.annotations), 'cap': args.cap,
               'photos_usable': usable, 'photos_selected': len(records),
               'boxes_selected': sum(per_class.values()), 'dropped': dropped,
               'types_mapped': len(mapping), 'types_without_a_class': missing, 'classes_added': added,
               'classes': {t: {'class': name_of[p], 'narrower': [name_of[n] for n in narrower]}
                           for t, (p, narrower) in mapping.items()},
               'boxes_per_class': {name_of[c]: n for c, n in sorted(per_class.items(), key=lambda kv: -kv[1])}}
    print(f"COCO: {usable} usable photos, {len(records)} selected with {summary['boxes_selected']} boxes; "
          f"{len(mapping)} of {len(coco['categories'])} types have a class"
          + (f"; added: {', '.join(added)}" if added else '') + (f"; without a class: {', '.join(missing)}" if missing else ''))
    print(f"Open Images: {len(base['images'])} training photos, {len(base['annotations'])} boxes")
    if args.plan_only:
        args.dataset.joinpath('mix_coco.plan.json').write_text(json.dumps(summary, indent=1), encoding='utf-8')
        return 0

    failures = fetch_all(records, train, args.images_url, args.images_dir, args.workers)
    records = [r for r in records if r['file'] not in failures]
    if not backup.exists():
        shutil.copyfile(path, backup)
    summary['open_images_photos_marked_unknown'] = mark_open_images(base['images'], mapping)
    images, annotations = base['images'], base['annotations']
    image_id = max((int(i['id']) for i in images), default=0)
    annotation_id = max((int(a['id']) for a in annotations), default=0)
    for record in records:
        image_id += 1
        images.append({'id': image_id, 'file_name': PREFIX + record['file'], 'width': record['width'],
                       'height': record['height'], 'coco_image_id': record['coco_id'],
                       'oi_verified_positive': sorted(record['positive']),
                       'oi_verified_negative': sorted(record['negative']),
                       'oi_unknown': sorted(record['unknown'])})
        for cat, x, y, w, h in record['boxes']:
            annotation_id += 1
            annotations.append({'id': annotation_id, 'image_id': image_id, 'category_id': cat,
                                'bbox': [round(x, 2), round(y, 2), round(w, 2), round(h, 2)], 'area': round(w * h, 2),
                                'iscrowd': 0, 'oi_group_of': 0, 'oi_depiction': 0, 'source': 'coco'})
    summary.update(photos_added=len(records), photos_skipped=len(failures),
                   skipped_examples=dict(list(failures.items())[:10]), photos_total=len(images),
                   boxes_total=len(annotations))
    base['categories'] = categories
    base.setdefault('info', {})['mix'] = {k: summary[k] for k in ('source', 'photos_added', 'photos_total', 'classes_added')}
    path.write_text(json.dumps(base), encoding='utf-8')
    for role in ROLES[1:]:                                   # The same class list everywhere, so labels line up.
        other = args.dataset / role / '_annotations.coco.json'
        if added and other.exists():
            data = json.loads(other.read_text(encoding='utf-8'))
            data['categories'], _ = with_new_classes(data['categories'], set(NEW_CLASSES))
            other.write_text(json.dumps(data), encoding='utf-8')
    described = args.dataset / 'dataset.json'
    if described.exists():
        data = json.loads(described.read_text(encoding='utf-8'))
        known = {c['name'] for c in data['classes']}
        data['classes'] += [{'id': c['id'], 'name': c['name'], 'open_images': [], 'coco': True}
                            for c in categories if c['name'] not in known]
        data['coco'] = {k: v for k, v in summary.items() if k not in ('boxes_per_class', 'classes', 'skipped_examples')}
        described.write_text(json.dumps(data, indent=1), encoding='utf-8')
    args.dataset.joinpath('mix_coco.json').write_text(json.dumps(summary, indent=1), encoding='utf-8')
    print(f"Added {len(records)} COCO photos ({len(failures)} skipped): the training set now has {len(images)} photos "
          f"and {len(annotations)} boxes in {len(categories)} classes.")
    return 0


def shrink_image(file: Path, max_side: int, quality: int) -> tuple[int, int]:
    from PIL import Image
    partial = file.with_suffix('.part')
    with Image.open(file) as image:
        width, height = image.size
        if max(width, height) <= max_side:
            return width, height
        scale = max_side / max(width, height)
        size = (max(1, round(width * scale)), max(1, round(height * scale)))
        image.draft('RGB', size)                     # Lets the JPEG decoder skip detail that is thrown away anyway.
        image.convert('RGB').resize(size, Image.LANCZOS).save(partial, 'JPEG', quality=quality)
    partial.replace(file)
    return size


def shrink(args) -> int:
    """Store a split's photos with the long side at most --max-side, and scale its boxes to match. Safe to run
    again: photos already small are left alone, and the annotations follow the files' real sizes."""
    folder = args.dataset / args.split
    path = folder / '_annotations.coco.json'
    coco = json.loads(path.read_text(encoding='utf-8'))
    before = sum((folder / i['file_name']).stat().st_size for i in coco['images'])
    with concurrent.futures.ThreadPoolExecutor(args.workers) as pool:
        sizes = list(pool.map(lambda i: shrink_image(folder / i['file_name'], args.max_side, args.quality), coco['images']))
    real = {image['file_name']: size for image, size in zip(coco['images'], sizes)}
    changed = 0
    for file in (path, folder / BACKUP):                 # The copy from before COCO was added follows too.
        if not file.exists():
            continue
        data = coco if file == path else json.loads(file.read_text(encoding='utf-8'))
        scale = {}
        for image in data['images']:
            width, height = real[image['file_name']]
            if (width, height) != (image['width'], image['height']):
                scale[image['id']] = (width / image['width'], height / image['height'])
                image['width'], image['height'] = width, height
        for a in data['annotations']:
            if a['image_id'] in scale:
                sx, sy = scale[a['image_id']]
                x, y, w, h = a['bbox']
                a['bbox'] = [round(x * sx, 2), round(y * sy, 2), round(w * sx, 2), round(h * sy, 2)]
                a['area'] = round(a['bbox'][2] * a['bbox'][3], 2)
        if scale:
            file.write_text(json.dumps(data), encoding='utf-8')
        if file == path:
            changed = len(scale)
    after = sum((folder / i['file_name']).stat().st_size for i in coco['images'])
    print(f'{args.split}: {changed} of {len(coco["images"])} photos shrunk to {args.max_side} px; '
          f'{before / 1e9:.1f} GB -> {after / 1e9:.1f} GB')
    return 0


def status(args) -> int:
    info = json.loads((args.dataset / 'train' / '_annotations.coco.json').read_text(encoding='utf-8')).get('info', {})
    if not info.get('mix'):
        print('No COCO photos in this dataset.')
        return 1
    print(json.dumps(info['mix']))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('add', help='add COCO photos and their labels to the training split')
    p.add_argument('--dataset', type=Path, required=True)
    p.add_argument('--annotations', type=Path, required=True, help='COCO instances_train2017.json')
    p.add_argument('--images-url', default=IMAGE_URL, help='where photos are downloaded from; {file} is the file name')
    p.add_argument('--images-dir', type=Path, help='copy photos from this folder instead of downloading')
    p.add_argument('--cap', type=int, help='at most about this many photos per class (default: all usable photos)')
    p.add_argument('--workers', type=int, default=48)
    p.add_argument('--plan-only', action='store_true')
    p.set_defaults(run=add)
    p = commands.add_parser('shrink', help='store photos smaller and scale their boxes')
    p.add_argument('--dataset', type=Path, required=True)
    p.add_argument('--split', default='train')
    p.add_argument('--max-side', type=int, default=640, help="COCO's own size, and above the model's 512 px input")
    p.add_argument('--quality', type=int, default=90)
    p.add_argument('--workers', type=int, default=8)
    p.set_defaults(run=shrink)
    p = commands.add_parser('status', help='exit 0 when the dataset holds COCO photos')
    p.add_argument('--dataset', type=Path, required=True)
    p.set_defaults(run=status)
    args = parser.parse_args(argv)
    return args.run(args)


if __name__ == '__main__':
    sys.exit(main())
