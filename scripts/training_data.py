"""Dataset catalogue and immutable training bundles; offline developer tooling."""
import csv
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import sqlite3
import urllib.request
import uuid
from functools import lru_cache

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / 'dependencies/recognition-vocabulary.json'
SPLITS = ('train', 'val', 'test')


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


@lru_cache(maxsize=1)
def vocabulary():
    registry = read_json(REGISTRY)
    return [{'raw_id': i, 'name': name, 'canonical_id': registry['openimages_ids'][i],
             'canonical_name': registry['classes'][registry['openimages_ids'][i]]}
            for i, name in enumerate(registry['openimages_labels'])]


def contained(root, name):
    path = (Path(root) / name).resolve()
    if not path.is_relative_to(Path(root).resolve()):
        raise ValueError('Dataset path escapes its root')
    return path


def valid_box(box, width=1, height=1):
    return (len(box) == 4 and all(type(x) in (int, float) and math.isfinite(x) for x in box)
            and 0 <= box[0] < box[2] <= width and 0 <= box[1] < box[3] <= height)


def split_for(group, seed):
    # One source group always stays in one partition, independent of selection order.
    value = int(hashlib.sha256(f'{seed}:{group}'.encode()).hexdigest()[:8], 16) % 100
    return 'train' if value < 60 else 'val' if value < 80 else 'test'


def image_info(path):
    from PIL import Image, ImageStat
    with Image.open(path) as image:
        image.load()
        width, height = image.size
        gray = image.convert('L').resize((9, 8))
        pixels = [gray.getpixel((x, y)) for y in range(8) for x in range(9)]
        bits = 0
        for y in range(8):
            for x in range(8):
                bits = (bits << 1) | (pixels[y * 9 + x] > pixels[y * 9 + x + 1])
        brightness = ImageStat.Stat(image.convert('L').resize((64, 64))).mean[0]
    return width, height, f'{bits:016x}', round(brightness, 2)


def catalogue(boxes_path, classes_path, metadata_path, output, publisher_split):
    if publisher_split not in ('train', 'validation', 'test'):
        raise ValueError('Unknown publisher split')
    output = Path(output)
    if output.exists():
        raise FileExistsError('Choose a new catalogue; existing data is preserved')
    output.parent.mkdir(parents=True, exist_ok=True)
    classes = vocabulary()
    by_name = {item['name']: item for item in classes}
    with Path(classes_path).open(newline='', encoding='utf-8-sig') as stream:
        mids = {row[0]: by_name[row[1]] for row in csv.reader(stream)}
    if {item['raw_id'] for item in mids.values()} != set(range(len(classes))):
        raise ValueError('Source class list differs from the frozen 601-label vocabulary')
    partial = output.with_name(output.name + '.' + uuid.uuid4().hex + '.partial')
    partial.touch(exist_ok=False)
    connection = sqlite3.connect(partial)
    try:
        connection.executescript('''
        PRAGMA foreign_keys=ON;
        CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE classes(raw_id INTEGER PRIMARY KEY, mid TEXT UNIQUE, name TEXT, canonical_id INTEGER);
        CREATE TABLE images(id TEXT PRIMARY KEY, landing_url TEXT, original_url TEXT,
          license TEXT, author TEXT, author_url TEXT, title TEXT, rotation TEXT);
        CREATE TABLE boxes(image_id TEXT, raw_id INTEGER REFERENCES classes(raw_id),
          x1 REAL,y1 REAL,x2 REAL,y2 REAL,occluded INTEGER,truncated INTEGER,
          group_of INTEGER,depiction INTEGER,source TEXT);
        CREATE INDEX box_class ON boxes(raw_id,image_id);
        CREATE INDEX box_image ON boxes(image_id);
        ''')
        with connection:
            connection.executemany('INSERT INTO classes VALUES(?,?,?,?)',
                [(value['raw_id'], mid, value['name'], value['canonical_id']) for mid, value in mids.items()])
            with Path(metadata_path).open(newline='', encoding='utf-8-sig') as stream:
                for row in csv.DictReader(stream):
                    if not re.fullmatch('[0-9a-f]{16}', row['ImageID']):
                        raise ValueError('Invalid publisher image ID')
                    if row['Subset'] != publisher_split:
                        raise ValueError('Attribution metadata belongs to another publisher split')
                    connection.execute('INSERT INTO images VALUES(?,?,?,?,?,?,?,?)', (
                        row['ImageID'], row['OriginalLandingURL'], row['OriginalURL'], row['License'],
                        row['Author'], row['AuthorProfileURL'], row['Title'], row['Rotation']))
            with Path(boxes_path).open(newline='', encoding='utf-8-sig') as stream:
                for row in csv.DictReader(stream):
                    box = [float(row[key]) for key in ('XMin', 'YMin', 'XMax', 'YMax')]
                    flags = [int(row[key]) for key in ('IsOccluded', 'IsTruncated', 'IsGroupOf', 'IsDepiction')]
                    if not valid_box(box) or any(flag not in (-1, 0, 1) for flag in flags):
                        raise ValueError('Invalid publisher box/flags')
                    connection.execute('INSERT INTO boxes VALUES(?,?,?,?,?,?,?,?,?,?,?)', (
                        row['ImageID'], mids[row['LabelName']]['raw_id'], *box, *flags, row['Source']))
            orphan_count = connection.execute('SELECT COUNT(*) FROM boxes b LEFT JOIN images i ON i.id=b.image_id WHERE i.id IS NULL').fetchone()[0]
            if orphan_count:
                raise ValueError('Bounding boxes have no attribution metadata')
            meta = {'schema': 1, 'publisher_split': publisher_split,
                    'source': 'https://storage.googleapis.com/openimages/web/download_v7.html',
                    'annotation_license': 'CC BY 4.0', 'vocabulary_sha256': digest(REGISTRY),
                    'files': {str(Path(p).name): digest(p) for p in (boxes_path, classes_path, metadata_path)}}
            connection.execute('INSERT INTO meta VALUES(?,?)', ('source', json.dumps(meta)))
        connection.close()
        # Exclusive publication on both Windows and Linux; never replace an existing catalogue.
        os.link(partial, output)
        return meta
    finally:
        connection.close()
        partial.unlink(missing_ok=True)


def inventory(db, policy):
    classes = vocabulary()
    by_canonical = {item['canonical_name']: item['canonical_id'] for item in classes}
    for domain, names in policy['domains'].items():
        if not domain or any(name not in by_canonical for name in names):
            raise ValueError('Scope contains categories outside the current broad model')
    counts = dict(db.execute('SELECT raw_id,COUNT(DISTINCT image_id) FROM boxes GROUP BY raw_id'))
    return {'schema': 1, 'scope_id': policy['id'], 'raw_labels': len(classes),
            'canonical_categories': len(set(item['canonical_id'] for item in classes)),
            'catalogue_images': db.execute('SELECT COUNT(*) FROM images').fetchone()[0],
            'catalogue_boxes': db.execute('SELECT COUNT(*) FROM boxes').fetchone()[0],
            'classes': [dict(item, annotated_images=counts.get(item['raw_id'], 0)) for item in classes],
            'domains': policy['domains'], 'limits': 'Counts are publisher annotation coverage, not exhaustive labels or deployment accuracy.'}


def select_candidates(db, policy, exclude=()):
    classes = vocabulary()
    canonical_names = {item['canonical_name']: item['canonical_id'] for item in classes}
    selected, used = [], set(exclude)
    # Interleave domains/classes so a small download budget cannot become an animal-only subset.
    domains = list(policy['domains'].items())
    for position in range(max(map(lambda pair: len(pair[1]), domains))):
        for domain, names in domains:
            if position >= len(names):
                continue
            canonical_id = canonical_names[names[position]]
            candidates = db.execute('''SELECT DISTINCT i.id FROM images i JOIN boxes b ON b.image_id=i.id
              JOIN classes c ON c.raw_id=b.raw_id WHERE c.canonical_id=?
              AND i.rotation IN ('0','0.0') AND i.license IN
              ('https://creativecommons.org/licenses/by/2.0/','http://creativecommons.org/licenses/by/2.0/')
              AND NOT EXISTS(SELECT 1 FROM boxes q WHERE q.image_id=i.id AND (q.group_of!=0 OR q.depiction!=0))''',
              (canonical_id,)).fetchall()
            candidates.sort(key=lambda row: hashlib.sha256(f"{policy['seed']}:{row[0]}".encode()).digest())
            added = 0
            for (image_id,) in candidates:
                if image_id in used:
                    continue
                used.add(image_id)
                selected.append({'id': image_id, 'selected_domain': domain, 'selected_category': names[position]})
                added += 1
                if len(selected) >= policy['max_images']:
                    return selected
                if added >= policy['images_per_category']:
                    break
    return selected


def fetch_image(url, path, remaining, per_image=10000000):
    path = Path(path)
    if path.exists():
        return path.stat().st_size
    part = path.with_suffix('.download')
    size = 0
    try:
        with urllib.request.urlopen(url, timeout=30) as response, part.open('xb') as stream:
            while chunk := response.read(65536):
                size += len(chunk)
                if size > min(remaining, per_image):
                    raise ValueError('Explicit image download budget exceeded')
                stream.write(chunk)
        image_info(part)
        part.replace(path)
        return size
    finally:
        part.unlink(missing_ok=True)


def prepare(db_path, policy_path, output, fetch=False, exclude=()):
    policy = read_json(policy_path)
    if (policy.get('schema') != 1 or type(policy.get('max_images')) is not int or not 0 < policy['max_images'] <= 10000
            or type(policy.get('images_per_category')) is not int or policy['images_per_category'] <= 0
            or type(policy.get('max_download_bytes')) is not int or policy['max_download_bytes'] <= 0):
        raise ValueError('Invalid bounded sampling policy')
    output = Path(output)
    if output.exists():
        raise FileExistsError('Choose a new dataset directory')
    db = sqlite3.connect(f'file:{Path(db_path).resolve().as_posix()}?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    try:
        report = inventory(db, policy)
        output.mkdir(parents=True)
        (output / 'images').mkdir()
        write_json(output / 'inventory.json', report)
        chosen = select_candidates(db, policy, exclude)
        source = json.loads(db.execute("SELECT value FROM meta WHERE key='source'").fetchone()[0])
        write_json(output / 'selection.json', {'scope': policy, 'source': source, 'images': chosen})
        if not fetch:
            return {'selected': len(chosen), 'fetched': 0, 'inventory': str(output / 'inventory.json')}
        entries, rejected, total = [], [], 0
        for chosen_image in chosen:
            image_id = chosen_image['id']
            metadata = dict(db.execute('SELECT * FROM images WHERE id=?', (image_id,)).fetchone())
            path = output / 'images' / f'{image_id}.jpg'
            url = f"https://open-images-dataset.s3.amazonaws.com/{source['publisher_split']}/{image_id}.jpg"
            total += fetch_image(url, path, policy['max_download_bytes'] - total)
            if total > policy['max_download_bytes']:
                raise ValueError('Dataset exceeds image byte budget')
            width, height, dhash, brightness = image_info(path)
            sha = digest(path)
            duplicate = next((item for item in entries if item['sha256'] == sha or
                              (int(item['dhash'], 16) ^ int(dhash, 16)).bit_count() <= 3), None)
            if duplicate:
                rejected.append({'id': image_id, 'reason': 'exact/near duplicate', 'of': duplicate['id']})
                continue
            group = metadata['author_url'] or metadata['landing_url']
            if not group:
                raise ValueError('Image has no source group for splitting')
            objects = [{'raw_id': row['raw_id'], 'box': [row['x1'] * width, row['y1'] * height, row['x2'] * width, row['y2'] * height],
                        'occluded': row['occluded'], 'truncated': row['truncated'], 'source': row['source']}
                       for row in db.execute('SELECT * FROM boxes WHERE image_id=? ORDER BY raw_id,x1,y1', (image_id,))]
            entries.append(dict(chosen_image, path=f'images/{image_id}.jpg', width=width, height=height,
                sha256=sha, dhash=dhash, mean_luma=brightness, group_id=group, split=split_for(group, policy['seed']),
                publisher_split=source['publisher_split'], attribution=metadata, objects=objects,
                review={'complete_target_classes': False, 'rights_verified': False, 'lighting': 'unreviewed'}))
            print(f"Dataset: {len(entries)} images, {total / 1000000:.1f} MB", flush=True)
        manifest = {'schema': 1, 'id': policy['id'], 'purpose': 'publisher-sample-unreviewed',
                    'scope_sha256': digest(policy_path), 'source': source, 'classes': vocabulary(),
                    'split_policy': 'source-author-grouped-sha256-60-20-20', 'seed': policy['seed'],
                    'images': entries, 'rejected': rejected,
                    'limits': 'Publisher validation sample, not an independent field test. Partial labels; no accuracy/adoption claim. Luma is not a night label.'}
        write_json(output / 'manifest.json', manifest)
        return {'selected': len(chosen), 'fetched': len(entries), 'rejected_duplicates': len(rejected),
                'bytes': total, 'splits': {split: sum(item['split'] == split for item in entries) for split in SPLITS}}
    finally:
        db.close()


def validate_manifest(path, smoke=False):
    path = Path(path)
    manifest = read_json(path)
    if manifest.get('schema') != 1 or manifest.get('classes') != vocabulary() or not manifest.get('images'):
        raise ValueError('Invalid dataset schema or frozen class map')
    seen, groups, hashes, images = set(), {}, {}, manifest['images']
    for image in images:
        if image['split'] not in SPLITS or image['id'] in seen:
            raise ValueError('Invalid split or duplicate image ID')
        seen.add(image['id'])
        source = contained(path.parent, image['path'])
        if digest(source) != image['sha256']:
            raise ValueError('Image changed after dataset preparation')
        width, height, dhash, _ = image_info(source)
        if (width, height, dhash) != (image['width'], image['height'], image['dhash']):
            raise ValueError('Image dimensions/fingerprint changed')
        group = image['group_id']
        if not group or groups.setdefault(group, image['split']) != image['split']:
            raise ValueError('Source group crosses dataset partitions')
        if image['sha256'] in hashes:
            raise ValueError('Duplicate image content')
        hashes[image['sha256']] = image['split']
        for obj in image['objects']:
            if type(obj['raw_id']) is not int or not 0 <= obj['raw_id'] < len(vocabulary()) or not valid_box(obj['box'], width, height):
                raise ValueError('Invalid class ID or original-image box')
        if not smoke:
            if image['review'].get('complete_target_classes') is not True or image['review'].get('rights_verified') is not True:
                raise ValueError('Substantial training requires reviewed complete target labels and image rights')
            if image['publisher_split'] in ('validation', 'test') and image['split'] == 'train':
                raise ValueError('Publisher evaluation images cannot enter a production training split')
    for i, image in enumerate(images):
        for other in images[:i]:
            if image['split'] != other['split'] and (int(image['dhash'], 16) ^ int(other['dhash'], 16)).bit_count() <= 3:
                raise ValueError('Near duplicate crosses dataset partitions')
    if any(not any(item['split'] == split for item in images) for split in SPLITS):
        raise ValueError('Training, validation and locked test partitions are all required')
    return manifest


def export_bundle(manifest_path, output, smoke=False):
    manifest = validate_manifest(manifest_path, smoke)
    exported_manifest = copy.deepcopy(manifest)
    output = Path(output)
    if output.exists():
        raise FileExistsError('Existing training bundles are immutable; choose a new directory')
    output.mkdir(parents=True)
    categories = [{'id': item['raw_id'], 'name': item['name'], 'supercategory': 'object'} for item in manifest['classes']]
    for split, rf_split in (('train', 'train'), ('val', 'valid'), ('test', 'test')):
        image_dir, label_dir = output / split / 'images', output / split / 'labels'
        image_dir.mkdir(parents=True)
        label_dir.mkdir()
        coco_dir = output / 'coco' / rf_split
        coco_dir.mkdir(parents=True)
        coco = {'images': [], 'annotations': [], 'categories': categories}
        for image_id, image in enumerate(item for item in manifest['images'] if item['split'] == split):
            source = contained(Path(manifest_path).parent, image['path'])
            name = f"{image['id']}.jpg"
            shutil.copyfile(source, image_dir / name)
            shutil.copyfile(source, coco_dir / name)
            next(item for item in exported_manifest['images'] if item['id'] == image['id'])['path'] = f'{split}/images/{name}'
            width, height = image['width'], image['height']
            lines = []
            coco['images'].append({'id': image_id, 'file_name': name, 'width': width, 'height': height})
            for obj in image['objects']:
                x1, y1, x2, y2 = obj['box']
                lines.append(f"{obj['raw_id']} {(x1+x2)/(2*width):.9f} {(y1+y2)/(2*height):.9f} {(x2-x1)/width:.9f} {(y2-y1)/height:.9f}")
                coco['annotations'].append({'id': len(coco['annotations']), 'image_id': image_id,
                    'category_id': obj['raw_id'], 'bbox': [x1, y1, x2-x1, y2-y1], 'area': (x2-x1)*(y2-y1), 'iscrowd': 0})
            (label_dir / f"{image['id']}.txt").write_text('\n'.join(lines) + ('\n' if lines else ''), encoding='utf-8')
        write_json(coco_dir / '_annotations.coco.json', coco)
    # JSON is a YAML subset. Relative image paths make the bundle relocatable to Linux.
    write_json(output / 'data.yaml', {'train': 'train/images', 'val': 'val/images', 'test': 'test/images',
                                    'names': [item['name'] for item in manifest['classes']]})
    write_json(output / 'manifest.json', exported_manifest)
    files = {p.relative_to(output).as_posix(): digest(p) for p in sorted(output.rglob('*')) if p.is_file()}
    lock = {'schema': 1, 'purpose': 'mechanical-smoke-only' if smoke else 'reviewed-training',
            'source_manifest_sha256': digest(manifest_path), 'classes': manifest['classes'], 'files': files,
            'images': {split: sum(item['split'] == split for item in manifest['images']) for split in SPLITS}}
    write_json(output / 'dataset-lock.json', lock)
    return lock


def verify_bundle(path, smoke=False):
    path = Path(path)
    lock = read_json(path / 'dataset-lock.json')
    if lock.get('schema') != 1 or lock.get('classes') != vocabulary():
        raise ValueError('Bundle class map differs from the frozen vocabulary')
    if not smoke and lock['purpose'] != 'reviewed-training':
        raise ValueError('Unreviewed smoke data cannot be used for a substantial training run')
    if any(lock['images'].get(split, 0) <= 0 for split in SPLITS):
        raise ValueError('Missing train/validation/test partition')
    settings = read_json(path / 'data.yaml')
    expected_settings = {'train': 'train/images', 'val': 'val/images', 'test': 'test/images',
                         'names': [item['name'] for item in vocabulary()]}
    if settings != expected_settings:
        raise ValueError('Dataset settings changed, redirect data or contain download instructions')
    for name, expected in lock['files'].items():
        if digest(contained(path, name)) != expected:
            raise ValueError(f'Training bundle changed: {name}')
    manifest = validate_manifest(path / 'manifest.json', smoke)
    expected_files = {'data.yaml', 'manifest.json'}
    for split, rf_split in (('train', 'train'), ('val', 'valid'), ('test', 'test')):
        members = [image for image in manifest['images'] if image['split'] == split]
        if lock['images'][split] != len(members):
            raise ValueError('Bundle split counts disagree with its manifest')
        expected_images = {f"{image['id']}.jpg" for image in members}
        expected_labels = {f"{image['id']}.txt" for image in members}
        if ({p.name for p in (path / split / 'images').iterdir()} != expected_images or
                {p.name for p in (path / split / 'labels').iterdir()} != expected_labels):
            raise ValueError('Unregistered images or labels entered the training bundle')
        expected_files.add(f'coco/{rf_split}/_annotations.coco.json')
        for image in members:
            if image['path'] != f"{split}/images/{image['id']}.jpg":
                raise ValueError('Image is stored in the wrong split')
            expected_files.update((image['path'], f"{split}/labels/{image['id']}.txt", f"coco/{rf_split}/{image['id']}.jpg"))
    if set(lock['files']) != expected_files:
        raise ValueError('Bundle lock does not cover exactly the required dataset files')
    return lock
