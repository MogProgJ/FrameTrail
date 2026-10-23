"""Acquire only the first 60 frozen publisher-train IDs; never train or approve."""
import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import html
import json
import math
import os
from pathlib import Path
import re
import shutil
import sqlite3
import time
import urllib.error
import urllib.request
import uuid
import warnings

VERSION = 'photo-pilot-v1'
SELECTION_SHA = '69d67561b87f4efad265f4713a415ff985e7bc551fa01b931c574c1e16d68ef5'
CATALOGUE_SHA = 'bd42dbb1129406c16cda37401670ecba04d6d956cde0071ab79de6190162e78d'
COUNT, TOTAL_CAP, IMAGE_CAP, PIXEL_CAP = 60, 1000000000, 10000000, 40000000


class IntegrityError(RuntimeError):
    pass


class PermanentError(RuntimeError):
    pass


class RetryableError(RuntimeError):
    pass


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def now():
    return datetime.now(timezone.utc).isoformat()


def inspect_jpeg(path):
    from PIL import Image, ImageStat
    with warnings.catch_warnings():
        warnings.simplefilter('error', Image.DecompressionBombWarning)
        try:
            opened = Image.open(path)
        except Image.DecompressionBombError as error:
            raise PermanentError('JPEG exceeds safe decode dimensions') from error
        with opened as image:
            if image.format != 'JPEG' or image.width * image.height > PIXEL_CAP:
                raise PermanentError('Require JPEG within the 40-megapixel decode cap')
            if image.getexif().get(274, 1) != 1:
                raise PermanentError('Non-identity EXIF orientation needs manual box-alignment review')
            image.verify()
        with Image.open(path) as image:
            image.load()
            width, height = image.size
            gray = image.convert('L').resize((9, 8))
            pixels = [gray.getpixel((x, y)) for y in range(8) for x in range(9)]
            bits = 0
            for y in range(8):
                for x in range(8):
                    bits = (bits << 1) | (pixels[y * 9 + x] > pixels[y * 9 + x + 1])
            luma = round(ImageStat.Stat(image.convert('L').resize((64, 64))).mean[0], 2)
    return {'width': width, 'height': height, 'dhash': f'{bits:016x}', 'mean_luma': luma}


def paths(directory, image_id):
    if not re.fullmatch('[0-9a-f]{16}', image_id):
        raise IntegrityError('Invalid frozen image ID')
    image = directory / 'images' / (image_id + '.jpg')
    receipt = directory / 'receipts' / (image_id + '.json')
    part, state = image.with_suffix('.jpg.part'), receipt.with_suffix('.part.json')
    for path in (image, receipt, part, state):
        if path.is_symlink() or not path.resolve().is_relative_to(directory.resolve()):
            raise IntegrityError('Image/receipt path escaped the intake directory')
    return image, receipt, part, state


def verify_finished(image, receipt, part, state, url, context, checker):
    record = read(receipt)
    if record.get('url') != url or record.get('context') != context or record.get('status') != 'downloaded':
        raise IntegrityError('Completed receipt belongs to different inputs')
    candidate = image if image.exists() else part
    if (not candidate.exists() or candidate.stat().st_size != record['bytes']
            or sha(candidate) != record['sha256'] or checker(candidate) != record['decoded']):
        raise IntegrityError('Completed image/receipt identity changed; no automatic replacement')
    if not image.exists():
        os.link(part, image)  # Recover interruption between receipt and exclusive publication.
    if part.exists():
        if part.stat().st_size != record['bytes'] or sha(part) != record['sha256']:
            raise IntegrityError('Unexpected partial file beside a completed image')
        part.unlink()
    state.unlink(missing_ok=True)
    return record


def acquire_one(directory, image_id, remaining, context, opener=urllib.request.urlopen, checker=inspect_jpeg):
    """Checkpoint each chunk; resume only the same HTTP object and verified prefix."""
    image, receipt, part, state_path = paths(directory, image_id)
    url = f'https://open-images-dataset.s3.amazonaws.com/train/{image_id}.jpg'
    if receipt.exists():
        return verify_finished(image, receipt, part, state_path, url, context, checker)
    if image.exists():
        raise IntegrityError('Image without a valid receipt; refuse automatic replacement')
    offset, state, headers = 0, None, {'Accept-Encoding': 'identity'}
    if state_path.exists():
        state = read(state_path)
        if state.get('url') != url or state.get('context') != context:
            raise IntegrityError('Partial receipt belongs to different inputs')
        offset = state['bytes']
        if type(offset) is not int or not 0 <= offset <= state['expected_bytes'] <= IMAGE_CAP:
            raise IntegrityError('Invalid partial byte count')
        if not part.exists() or part.stat().st_size < offset:
            raise IntegrityError('Partial data missing or shorter than checkpoint')
        with part.open('rb') as stream:
            prefix = hashlib.sha256(stream.read(offset)).hexdigest()
        if prefix != state['prefix_sha256']:
            raise IntegrityError('Partial prefix changed; refuse to mix image versions')
        if part.stat().st_size > offset:
            # A killed process may have written one uncommitted chunk. Retain only
            # its verified checkpoint prefix, then request that range again.
            with part.open('r+b') as stream:
                stream.truncate(offset)
        if offset == state['expected_bytes']:
            response = None
        else:
            validator = state.get('etag') or state.get('last_modified')
            if not validator:
                raise PermanentError('No HTTP validator; cannot safely resume this partial image')
            headers.update({'Range': f'bytes={offset}-', 'If-Range': validator})
            response = opener(urllib.request.Request(url, headers=headers), timeout=30)
    else:
        if part.exists():
            raise IntegrityError('Unregistered partial image; inspect before recovery')
        response = opener(urllib.request.Request(url, headers=headers), timeout=30)
    if response is not None:
        with response:
            if response.geturl() != url:
                raise PermanentError('Unexpected image redirect; no fallback to original/private URLs')
            status = response.status
            try:
                length = int(response.headers['Content-Length'])
            except (KeyError, TypeError, ValueError) as error:
                raise PermanentError('Missing/invalid HTTP length') from error
            etag, modified = response.headers.get('ETag'), response.headers.get('Last-Modified')
            if state is not None:
                expected = state['expected_bytes']
                wanted_range = f'bytes {offset}-{expected - 1}/{expected}'
                if (status != 206 or response.headers.get('Content-Range') != wanted_range
                        or length != expected - offset or etag != state.get('etag')
                        or modified != state.get('last_modified')):
                    raise PermanentError('Server did not return the same image and exact resume range')
            else:
                expected = length
                if status != 200:
                    raise PermanentError('Require full HTTP 200 for a new image')
                state = {'schema': 1, 'url': url, 'context': context, 'expected_bytes': expected,
                         'etag': etag, 'last_modified': modified, 'bytes': 0,
                         'prefix_sha256': hashlib.sha256(b'').hexdigest()}
            if not 0 < expected <= IMAGE_CAP or expected - offset > remaining:
                raise PermanentError('Image exceeds per-image or remaining stored-payload budget')
            encoding = response.headers.get('Content-Encoding', 'identity')
            if encoding != 'identity':
                raise PermanentError('Require identity HTTP encoding for byte accounting')
            hasher = hashlib.sha256()
            if offset:
                with part.open('rb') as stream:
                    hasher.update(stream.read(offset))
            with part.open('ab' if state_path.exists() else 'xb') as stream:
                save(state_path, state)
                while True:
                    chunk = response.read(min(65536, expected - offset + 1))
                    if not chunk:
                        break
                    if offset + len(chunk) > expected:
                        raise PermanentError('HTTP body exceeded its advertised byte length')
                    stream.write(chunk)
                    stream.flush()
                    hasher.update(chunk)
                    offset += len(chunk)
                    state.update(bytes=offset, prefix_sha256=hasher.hexdigest())
                    save(state_path, state)
                if offset != expected:
                    raise RetryableError('Truncated image; verified partial bytes retained')
    try:
        decoded = checker(part)
    except (OSError, ValueError, Warning) as error:
        raise PermanentError('Image decode rejected: ' + str(error)) from error
    record = {'schema': 1, 'status': 'downloaded', 'url': url, 'context': context,
              'bytes': part.stat().st_size, 'sha256': sha(part), 'decoded': decoded,
              'retrieved_at_utc': now(), 'etag': state.get('etag'), 'last_modified': state.get('last_modified'),
              'verification': 'HTTP identity/length, local SHA256 and JPEG decode; no publisher checksum supplied'}
    save(receipt, record)
    os.link(part, image)  # Never overwrite existing photograph pixels.
    part.unlink()
    state_path.unlink(missing_ok=True)
    return record


@contextmanager
def intake_lock(directory):
    with (directory / '.acquisition.lock').open('a+b') as stream:
        stream.seek(0)
        if os.name == 'nt':
            import msvcrt
            if os.fstat(stream.fileno()).st_size == 0:
                stream.write(b'0')
                stream.flush()
            stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as error:
                raise IntegrityError('Another acquisition process holds this intake lock') from error
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as error:
                raise IntegrityError('Another acquisition process holds this intake lock') from error
            try:
                yield
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def load_inputs(root, selection_job):
    base = root / 'output/training-general-v1'
    selected = base / f'pilot-selection-v2-{selection_job}'
    selection_path, summary_path = selected / 'selection.json', selected / 'selection-summary.json'
    selection, report = read(selection_path), read(summary_path)
    if (sha(selection_path) != SELECTION_SHA or report['selection_sha256'] != SELECTION_SHA
            or report['job_id'] != selection_job or report['status'] != 'completed'
            or report['coverage_gate_passed'] is not True or report['missing_anchors']
            or selection['source']['publisher_split'] != 'train'):
        raise IntegrityError('Require the locally verified, completed selection 7449188')
    metadata_job = report['source_catalogue_job']
    if not re.fullmatch('[0-9]+', metadata_job):
        raise IntegrityError('Invalid source catalogue job ID')
    source_dir = base / f'catalogue-{metadata_job}'
    db_path = source_dir / 'openimages-train.sqlite'
    preparation = read(source_dir / 'preparation.json')
    scope_path = base / 'metadata-tools-v1/general-intake-pilot.json'
    registry_path = root / 'dependencies/recognition-vocabulary.json'
    exclusion_path = root / 'output/training-0.13/general-smoke-bundle/manifest.json'
    if (preparation['status'] != 'completed' or preparation['publisher_split'] != 'train'
            or sha(db_path) != CATALOGUE_SHA or report['source_catalogue_sha256'] != CATALOGUE_SHA
            or preparation['catalogue_sha256'] != CATALOGUE_SHA
            or sha(scope_path) != report['scope_sha256'] or preparation['scope_sha256'] != report['scope_sha256']
            or sha(registry_path) != report['vocabulary_sha256']
            or sha(exclusion_path) != report['exclusion_manifest_sha256']
            or sha(selected / 'inventory.json') != report['inventory_sha256']
            or read(scope_path) != selection['scope']):
        raise IntegrityError('Frozen source, scope, vocabulary or exclusion identity changed')
    registry = read(registry_path)
    classes = [{'raw_id': i, 'name': name, 'canonical_id': registry['openimages_ids'][i],
                'canonical_name': registry['classes'][registry['openimages_ids'][i]]}
               for i, name in enumerate(registry['openimages_labels'])]
    if len(classes) != 601 or len({item['canonical_id'] for item in classes}) != 597:
        raise IntegrityError('Unexpected vocabulary contract')
    smoke = read(exclusion_path)['images']
    exclude = {item['id'] if 'id' in item else Path(item['path']).stem for item in smoke}
    all_ids = [item['id'] for item in selection['images']]
    category_counts = Counter(item['selected_category'] for item in selection['images'])
    domains = selection['scope']['domains']
    anchors = {name for names in domains.values() for name in names}
    chosen = selection['images'][:COUNT]
    if (len(all_ids) != len(set(all_ids)) or len(all_ids) != 600 or set(all_ids) & exclude
            or any(not re.fullmatch('[0-9a-f]{16}', image_id) for image_id in all_ids)
            or dict(category_counts) != report['anchor_counts'] or set(category_counts) != anchors
            or len(chosen) != COUNT or {item['selected_category'] for item in chosen} != anchors
            or any(item['selected_category'] not in domains[item['selected_domain']] for item in selection['images'])):
        raise IntegrityError('Frozen selection uniqueness/domain/first-60 coverage gate failed')
    annotations = {}
    db = sqlite3.connect(db_path.as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    try:
        source = json.loads(db.execute("SELECT value FROM meta WHERE key='source'").fetchone()[0])
        if source != selection['source'] or source['vocabulary_sha256'] != sha(registry_path):
            raise IntegrityError('Catalogue source contract differs from selection')
        db_classes = list(db.execute('SELECT raw_id,name,canonical_id FROM classes ORDER BY raw_id'))
        if [tuple(row) for row in db_classes] != [(c['raw_id'], c['name'], c['canonical_id']) for c in classes]:
            raise IntegrityError('Catalogue class order/mapping differs')
        for item in chosen:
            row = db.execute('SELECT * FROM images WHERE id=?', (item['id'],)).fetchone()
            if row is None:
                raise IntegrityError('Selected image absent from catalogue')
            attribution = dict(row)
            if (attribution['rotation'] not in ('0', '0.0') or attribution['license'] not in
                    ('https://creativecommons.org/licenses/by/2.0/', 'http://creativecommons.org/licenses/by/2.0/')):
                raise IntegrityError('Selected source is no longer eligible')
            boxes = [dict(box) for box in db.execute('SELECT * FROM boxes WHERE image_id=? ORDER BY raw_id,x1,y1,x2,y2', (item['id'],))]
            for box in boxes:
                coords = [box[key] for key in ('x1', 'y1', 'x2', 'y2')]
                if (box['group_of'] != 0 or box['depiction'] != 0
                        or type(box['raw_id']) is not int or not 0 <= box['raw_id'] < 601
                        or not all(type(v) in (int, float) and math.isfinite(v) for v in coords)
                        or not 0 <= coords[0] < coords[2] <= 1 or not 0 <= coords[1] < coords[3] <= 1):
                    raise IntegrityError('Invalid/unsupported publisher box')
            canonical = {classes[box['raw_id']]['canonical_name'] for box in boxes}
            if item['selected_category'] not in canonical:
                raise IntegrityError('Anchor has no corresponding publisher box')
            annotations[item['id']] = {'attribution': attribution, 'boxes': boxes}
    finally:
        db.close()
    context = {'selection_sha256': SELECTION_SHA, 'catalogue_sha256': CATALOGUE_SHA,
               'scope_sha256': report['scope_sha256'], 'vocabulary_sha256': report['vocabulary_sha256'],
               'exclusion_manifest_sha256': report['exclusion_manifest_sha256'],
               'module': VERSION, 'runner_sha256': sha(__file__)}
    plan = {'schema': 1, 'module': VERSION, 'selection_job': selection_job, 'source_catalogue_job': metadata_job,
            'context': context, 'images': chosen, 'max_original_bytes': TOTAL_CAP, 'max_image_bytes': IMAGE_CAP,
            'max_decoded_pixels': PIXEL_CAP, 'approved_for_training': False}
    return plan, annotations, classes, source, smoke


def payload_bytes(directory):
    return sum(path.stat().st_size for path in (directory / 'images').iterdir()
               if path.name.endswith(('.jpg', '.jpg.part')))


def make_manifest(plan, records, annotations, classes, source, smoke):
    entries, duplicates = [], []
    comparison = [(item['id'], item['sha256'], item['dhash'], 'old-smoke') for item in smoke]
    for chosen in plan['images']:
        image_id = chosen['id']
        if image_id not in records:
            continue
        record = records[image_id]
        decoded = record['decoded']
        width, height = decoded['width'], decoded['height']
        holds = []
        for other_id, other_sha, other_dhash, origin in comparison:
            kind = ('exact' if other_sha == record['sha256'] else 'near-candidate'
                    if (int(other_dhash, 16) ^ int(decoded['dhash'], 16)).bit_count() <= 3 else None)
            if kind:
                duplicates.append({'id': image_id, 'of': other_id, 'origin': origin, 'kind': kind})
                holds.append(kind + '-duplicate-review')
        comparison.append((image_id, record['sha256'], decoded['dhash'], 'this-intake'))
        data = annotations[image_id]
        group = data['attribution']['author_url'] or data['attribution']['landing_url']
        if not group:
            holds.append('missing-source-group')
        objects = [{'raw_id': box['raw_id'],
                    'box': [box['x1'] * width, box['y1'] * height, box['x2'] * width, box['y2'] * height],
                    'normalized_box': [box[k] for k in ('x1', 'y1', 'x2', 'y2')],
                    'occluded': box['occluded'], 'truncated': box['truncated'],
                    'group_of': box['group_of'], 'depiction': box['depiction'], 'inside': None, 'source': box['source']}
                   for box in data['boxes']]
        entries.append(dict(chosen, path=f'images/{image_id}.jpg', bytes=record['bytes'],
                            sha256=record['sha256'], **decoded, attribution=data['attribution'], objects=objects,
                            publisher_split='train', group_id=group, split='unassigned',
                            intake_hold_reasons=sorted(set(holds)),
                            review={'complete_target_classes': False, 'rights_verified': False,
                                    'lighting': 'unreviewed', 'reviewer': None, 'reviewed_at_utc': None}))
    return {'schema': 1, 'id': VERSION + '-selection-' + plan['selection_job'],
            'purpose': 'publisher-train-intake-unreviewed', 'source': source, 'classes': classes,
            'context': plan['context'], 'split_policy': 'unassigned-unreviewed-intake',
            'images': entries, 'duplicate_candidates': duplicates, 'approved_for_training': False,
            'image_level_labels_indexed': False, 'publisher_inside_flags_indexed': False,
            'limits': 'Partial publisher annotations. Review the whole image and rights; unknown is not negative. Duplicate candidates need review. Luma is not a night label. No training/export/adoption approval.'}


def write_review(directory, manifest, plan):
    esc = html.escape
    cards, notes = [], ['# First-60 intake review notes', '',
                         'UNREVIEWED. Record observations, not approval flags. Inspect every visible object, not just the anchor.',
                         'Record missing/wrong boxes, ambiguous classes, source rights evidence, lighting, blur, small objects and duplicates.',
                         'The page is an inspection aid, not an annotation editor or a complete-target/rights approval.', '']
    for chosen in plan['images']:
        notes.extend([f'## {chosen["id"]} — {chosen["selected_category"]}', '',
                      '- Missing/wrong objects or boxes:', '- Rights/attribution evidence:',
                      '- Lighting, blur, occlusion, small objects:', '- Duplicate/ambiguity notes:',
                      '- Reviewer and time spent:', ''])
    for image in manifest['images']:
        image_id, width, height = image['id'], image['width'], image['height']
        boxes, labels = [], []
        for n, obj in enumerate(image['objects'], 1):
            x1, y1, x2, y2 = obj['box']
            name = manifest['classes'][obj['raw_id']]['name']
            boxes.append(f'<rect x="{x1}" y="{y1}" width="{x2-x1}" height="{y2-y1}"><title>{n}: {esc(name)}</title></rect>')
            labels.append(f'<li>{n}: {esc(name)}; raw ID {obj["raw_id"]}; occluded {obj["occluded"]}; truncated {obj["truncated"]}</li>')
        attribution = esc(json.dumps(image['attribution'], ensure_ascii=False, indent=2))
        holds = esc(', '.join(image['intake_hold_reasons']) or 'none detected (not proof of uniqueness)')
        cards.append(f'<article><h2>{image_id} — {esc(image["selected_category"])}</h2>'
                     f'<p>{esc(image["selected_domain"])} · {width} × {height} · <a href="{image["path"]}">Open clean JPEG</a></p>'
                     f'<div class="frame"><img loading="lazy" src="{image["path"]}" alt="Intake image {image_id}">'
                     f'<svg viewBox="0 0 {width} {height}" aria-label="Unreviewed publisher boxes">{"".join(boxes)}</svg></div>'
                     f'<p>Publisher boxes only; missing objects may be unlabelled. Duplicate/source holds: {holds}.</p>'
                     f'<details><summary>{len(labels)} publisher boxes and attribution</summary><ol>{"".join(labels)}</ol><pre>{attribution}</pre></details></article>')
    page = '<!doctype html><meta charset="utf-8"><title>FrameTrail intake — UNREVIEWED</title>'
    page += '<style>body{font:16px system-ui;max-width:1100px;margin:24px auto;padding:0 16px}article{border-top:1px solid #aaa;margin:30px 0;padding-top:16px}.frame{position:relative}.frame img{display:block;width:100%;height:auto}.frame svg{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}rect{fill:none;stroke:#ff3b30;stroke-width:2;vector-effect:non-scaling-stroke}pre{white-space:pre-wrap;overflow-wrap:anywhere}body.hide-boxes svg{display:none}</style>'
    page += '<h1>First-60 photograph intake — UNREVIEWED</h1><p>Clean originals are unchanged. Red overlays show publisher boxes, not complete labels or predictions. Do not approve training from this page. Record findings in your own copy of review-notes-template.md.</p>'
    page += '<button onclick="document.body.classList.toggle(\'hide-boxes\')">Show/hide publisher boxes</button>'
    page += ''.join(cards)
    (directory / 'review.html').write_text(page, encoding='utf-8')
    template = directory / 'review-notes-template.md'
    if not template.exists():
        template.write_text('\n'.join(notes) + '\n', encoding='utf-8')


def snapshot(directory, job_dir, plan, records, failures, annotations, classes, source, smoke, job_id, status):
    manifest = make_manifest(plan, records, annotations, classes, source, smoke)
    save(directory / 'manifest.json', manifest)
    write_review(directory, manifest, plan)
    report = {'schema': 1, 'module': VERSION, 'status': status, 'job_id': job_id,
              'selection_job': plan['selection_job'], 'source_catalogue_job': plan['source_catalogue_job'],
              'updated_at_utc': now(), 'context': plan['context'], 'requested_photographs': COUNT,
              'photographs_downloaded': len(records), 'failed_images': failures,
              'original_bytes': sum(r['bytes'] for r in records.values()),
              'stored_payload_bytes_including_partials': payload_bytes(directory),
              'max_original_bytes': TOTAL_CAP, 'max_image_bytes': IMAGE_CAP,
              'downloaded_anchor_categories': len({item['selected_category'] for item in manifest['images']}),
              'downloaded_domains': dict(Counter(item['selected_domain'] for item in manifest['images'])),
              'duplicate_candidates': manifest['duplicate_candidates'], 'approved_for_training': False,
              'manifest_sha256': sha(directory / 'manifest.json'),
              'intake_directory': str(directory),
              'limits': 'Acquisition status only, not annotation/rights approval or accuracy. Payload cap excludes small receipts/review metadata; HTTP retransmissions may add network traffic.'}
    save(directory / 'progress.json', report)
    save(job_dir / 'acquisition.json', report)
    return report


def run(args, opener=urllib.request.urlopen, checker=inspect_jpeg, sleep=time.sleep):
    root = args.root.resolve()
    if not all(re.fullmatch('[0-9]+', value) for value in (args.selection_job, args.job_id)):
        raise IntegrityError('Require actual numeric Slurm job IDs')
    plan, annotations, classes, source, smoke = load_inputs(root, args.selection_job)
    directory = root / f'output/training-general-v1/photo-pilot-{args.selection_job}-first60'
    job_dir = root / f'output/training-general-v1/photo-job-{args.job_id}'
    if directory.is_symlink() or job_dir.is_symlink():
        raise IntegrityError('Redirected output directory is not allowed')
    # Check Pillow on the compute node before opening any network connection.
    from PIL import Image
    print(json.dumps({'status': 'preflight', 'module': VERSION, 'job_id': args.job_id,
                      'selection_job': args.selection_job, 'requested_photographs': COUNT,
                      'anchors': len({item['selected_category'] for item in plan['images']}),
                      'intake_directory': str(directory), 'job_report_directory': str(job_dir),
                      'approved_for_training': False}, indent=2), flush=True)
    if not args.run:
        return
    if job_dir.exists():
        raise FileExistsError('Preserve the existing job report; submit a new job ID to resume')
    if shutil.disk_usage(root).free < TOTAL_CAP + 1000000000:
        raise PermanentError('Require at least 2 GB free filesystem space for this pilot')
    directory.mkdir(exist_ok=True)
    with intake_lock(directory):
        plan_path = directory / 'intake-plan.json'
        if plan_path.exists():
            if read(plan_path) != plan:
                raise IntegrityError('Intake plan changed; do not overwrite the old acquisition')
        else:
            if any(path.name != '.acquisition.lock' for path in directory.iterdir()):
                raise IntegrityError('Existing intake has no registered plan')
            save(plan_path, plan)
        for name in ('images', 'receipts'):
            subdir = directory / name
            if subdir.is_symlink():
                raise IntegrityError('Redirected intake subdirectory')
            subdir.mkdir(exist_ok=True)
        allowed_ids = {item['id'] for item in plan['images']}
        if any(path.is_symlink() or path.name not in
               {image_id + suffix for image_id in allowed_ids for suffix in ('.jpg', '.jpg.part')}
               for path in (directory / 'images').iterdir()):
            raise IntegrityError('Unregistered image entered this intake directory')
        job_dir.mkdir()
        records, failures = {}, []
        # Verify all completed receipts before spending any new network bytes.
        for chosen in plan['images']:
            image, receipt, part, state = paths(directory, chosen['id'])
            if receipt.exists():
                url = f'https://open-images-dataset.s3.amazonaws.com/train/{chosen["id"]}.jpg'
                records[chosen['id']] = verify_finished(image, receipt, part, state, url, plan['context'], checker)
            elif image.exists():
                raise IntegrityError('Existing image has no receipt')
        if payload_bytes(directory) > TOTAL_CAP:
            raise IntegrityError('Existing intake exceeds its frozen byte budget')
        manifest_path = directory / 'manifest.json'
        if manifest_path.exists():
            saved = read(manifest_path)
            saved_ids = {item['id'] for item in saved['images']}
            if not saved_ids <= set(records) or saved != make_manifest(
                    plan, {key: records[key] for key in saved_ids}, annotations, classes, source, smoke):
                raise IntegrityError('Intake manifest was edited; preserve review work instead of regenerating it')
        snapshot(directory, job_dir, plan, records, failures, annotations, classes, source, smoke, args.job_id, 'running')
        for chosen in plan['images']:
            image_id = chosen['id']
            if image_id in records:
                continue
            last_error = None
            for attempt in range(1, 4):
                try:
                    record = acquire_one(directory, image_id, TOTAL_CAP - payload_bytes(directory), plan['context'], opener, checker)
                    records[image_id] = record
                    last_error = None
                    break
                except IntegrityError:
                    raise  # Corruption/mixed provenance is a batch blocker, not a download retry.
                except urllib.error.HTTPError as error:
                    last_error = f'HTTP {error.code}'
                    if error.code not in (408, 429, 500, 502, 503, 504):
                        break
                except (RetryableError, urllib.error.URLError, TimeoutError, ConnectionError) as error:
                    last_error = str(error)
                except PermanentError as error:
                    last_error = str(error)
                    break
                if attempt < 3:
                    sleep(attempt)
            if last_error is not None:
                failures.append({'id': image_id, 'reason': last_error, 'attempts_this_job': attempt,
                                 'action': 'Inspect/retry the same frozen ID; no silent replacement'})
            print(f'Photo pilot: {len(records)}/{COUNT} decoded originals; {len(failures)} failures', flush=True)
            snapshot(directory, job_dir, plan, records, failures, annotations, classes, source, smoke, args.job_id, 'running')
        status = 'completed' if len(records) == COUNT and not failures else 'partial'
        report = snapshot(directory, job_dir, plan, records, failures, annotations, classes, source, smoke, args.job_id, status)
        print(json.dumps(report, indent=2), flush=True)
        if status != 'completed':
            raise RuntimeError('Photo acquisition incomplete; inspect the saved failures and receipts')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--selection-job', required=True)
    parser.add_argument('--job-id', required=True)
    parser.add_argument('--run', action='store_true', help='Fetch the first 60 frozen IDs; no training')
    run(parser.parse_args())


if __name__ == '__main__':
    main()
