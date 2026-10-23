"""Offline, append-only annotation correction drafts. Never publishes training approval."""
import copy
import csv
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import subprocess

from training_data import contained, digest, image_info, read_json, valid_box, vocabulary, write_json

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / 'training/annotation-policy-v1.json'
TEMPLATE = ROOT / 'scripts/annotation-editor-simple.html'
EDITOR_SCRIPT = ROOT / 'scripts/annotation-editor.js'
STATES = ('pending', 'confirmed', 'rejected')
REVIEW_KEYS = {'reviewer', 'notes', 'geometry_pass', 'coverage_pass', 'holds', 'rights_evidence'}
OBJECT_KEYS = {'raw_id', 'box', 'status', 'note'}


def utc():
    return datetime.now(timezone.utc).isoformat()


def check_intake(path):
    path = Path(path).resolve(strict=True)
    source = read_json(path)
    if source.get('schema') != 1 or source.get('classes') != vocabulary():
        raise ValueError('Intake must have the frozen 601-label vocabulary')
    if source.get('approved_for_training') is not False:
        raise ValueError('This tool accepts unapproved intake, not an existing training release')
    ids, hashes = set(), set()
    for image in source['images']:
        if not re.fullmatch('[0-9a-f]{16}', image['id']) or image['id'] in ids:
            raise ValueError('Duplicate or invalid image ID')
        ids.add(image['id'])
        photo = contained(path.parent, image['path'])
        if digest(photo) != image['sha256'] or photo.stat().st_size != image['bytes']:
            raise ValueError('Original photograph hash/size changed')
        if image['sha256'] in hashes:
            raise ValueError('Duplicate original photograph bytes')
        hashes.add(image['sha256'])
        width, height, dhash, _ = image_info(photo)
        from PIL import Image
        with Image.open(photo) as decoded:
            if decoded.getexif().get(274, 1) != 1:
                raise ValueError('EXIF-rotated photos need explicit geometry reconciliation before annotation')
        if (width, height, dhash) != (image['width'], image['height'], image['dhash']):
            raise ValueError('Photograph geometry or visual identity changed')
        for obj in image['objects']:
            check_object({'raw_id': obj['raw_id'], 'box': obj['box'], 'status': 'pending', 'note': ''}, image)
    if not ids:
        raise ValueError('Empty intake')
    return source


def check_object(obj, image):
    if type(obj['raw_id']) is not int or not 0 <= obj['raw_id'] < len(vocabulary()):
        raise ValueError('Class ID is outside the frozen vocabulary')
    if not valid_box(obj['box'], image['width'], image['height']):
        raise ValueError('Box must be finite, positive-area and inside the original image')
    if obj['status'] not in STATES or not isinstance(obj['note'], str):
        raise ValueError('Invalid box review state/note')
    if obj['status'] == 'rejected' and not obj['note'].strip():
        raise ValueError('Rejected boxes require a reason')


def check_review(review):
    if set(review) != REVIEW_KEYS:
        raise ValueError('Invalid image review fields')
    if any(not isinstance(review[key], str) for key in ('reviewer', 'notes', 'rights_evidence')):
        raise ValueError('Invalid reviewer or evidence text')
    if any(type(review[key]) is not bool for key in ('geometry_pass', 'coverage_pass')):
        raise ValueError('Invalid review checklist value')
    if not isinstance(review['holds'], list) or any(not isinstance(x, str) or not x.strip() for x in review['holds']):
        raise ValueError('Holds must be nonempty strings')
    if (review['geometry_pass'] or review['coverage_pass']) and not review['reviewer'].strip():
        raise ValueError('A checklist pass requires a named reviewer')


def check_observation(obj, image):
    """A boxed observation is not a class in the frozen detector head."""
    if set(obj) != {'id', 'label', 'box', 'status', 'note', 'origin'}:
        raise ValueError('Invalid observation fields; observations cannot have training class IDs')
    label = obj['label']
    if not isinstance(label, str) or not label.strip() or label != label.strip() or len(label) > 120 or any(ord(x) < 32 or ord(x) == 127 for x in label):
        raise ValueError('Observation needs a short, nonempty object name')
    known = {x[key].casefold() for x in vocabulary() for key in ('name', 'canonical_name')}
    if label.casefold() in known:
        raise ValueError('This name is a supported class; choose it from the label dropdown')
    if not valid_box(obj['box'], image['width'], image['height']):
        raise ValueError('Observation box must be finite, positive-area and inside the photo')
    if obj['status'] not in STATES or not isinstance(obj['note'], str) or (obj['status'] == 'rejected' and not obj['note'].strip()):
        raise ValueError('Invalid observation state/note')
    model_origin = obj['origin'].get('kind') == 'model-observation' and set(obj['origin']) == {'kind','model','pack_id','candidate_id','confidence','model_sha256'}
    if (obj['origin'] != {'kind': 'manual-observation'} and not model_origin) or not re.fullmatch('observation-[a-zA-Z0-9-]+', obj['id']):
        raise ValueError('Invalid observation provenance or ID')


def iou(a, b):
    intersection = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    union = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - intersection
    return intersection / union if union else 0


def event(state, image_id, kind, object_id, after, actor, proposals=None):
    image = next(x for x in state['images'] if x['id'] == image_id)
    if kind == 'review':
        before = image['review']
    elif kind in ('add', 'observation-add', 'proposal-add'):
        before = None
    else:
        collection = image.get('observations', []) if kind == 'observation-update' else image['objects']
        before = next(x for x in collection if x['id'] == object_id)
    change = {'seq': len(state['events']) + 1, 'at': utc(), 'actor': actor,
              'image_id': image_id, 'kind': kind, 'object_id': object_id,
              'before': copy.deepcopy(before), 'after': copy.deepcopy(after)}
    apply_event(state, change, proposals)
    state['events'].append(change)


def apply_event(state, change, proposals=None):
    if set(change) != {'seq', 'at', 'actor', 'image_id', 'kind', 'object_id', 'before', 'after'}:
        raise ValueError('Malformed correction event')
    if not isinstance(change['actor'], str) or not change['actor'].strip():
        raise ValueError('Every correction needs an actor')
    try:
        datetime.fromisoformat(change['at'])
    except (ValueError, TypeError):
        raise ValueError('Invalid correction timestamp') from None
    image = next((x for x in state['images'] if x['id'] == change['image_id']), None)
    if image is None:
        raise ValueError('Correction references an unknown photograph')
    after = change['after']
    if change['kind'] == 'proposal-add':
        from rfdetr_annotations import proposal_object
        expected = proposal_object(proposals, image['id'], after['origin']['candidate_id'])
        if after != expected or change['object_id'] != after['id'] or change['before'] is not None:
            raise ValueError('RF proposal must match its immutable inference catalogue')
        if any(x['id'] == after['id'] for x in image['objects'] + image.get('observations', [])):
            raise ValueError('RF proposal already adopted or rejected')
        image.setdefault('observations', []).append(copy.deepcopy(after)) if 'label' in after else image['objects'].append(copy.deepcopy(after))
        return
    if change['kind'] == 'review':
        if change['object_id'] is not None or change['before'] != image['review']:
            raise ValueError('Review event does not match its preceding state')
        check_review(after)
        image['review'] = copy.deepcopy(after)
        return
    if change['kind'] in ('observation-add', 'observation-update'):
        check_observation(after, image)
        if after['id'] != change['object_id']:
            raise ValueError('Observation identity mismatch')
        observations = image.get('observations', [])
        existing = next((x for x in observations if x['id'] == after['id']), None)
        if change['kind'] == 'observation-add':
            if existing is not None or change['before'] is not None or after['origin'] != {'kind':'manual-observation'}:
                raise ValueError('New observations require unique IDs')
            image.setdefault('observations', []).append(copy.deepcopy(after))
        else:
            if existing is None or change['before'] != existing:
                raise ValueError('Observation history mismatch')
            if after['origin'] != existing['origin']:
                raise ValueError('Observation provenance is immutable')
            observations[observations.index(existing)] = copy.deepcopy(after)
        return
    check_object(after, image)
    if after['id'] != change['object_id']:
        raise ValueError('Correction object identity mismatch')
    existing = next((x for x in image['objects'] if x['id'] == change['object_id']), None)
    if change['kind'] == 'add':
        if existing is not None or change['before'] is not None or not re.fullmatch('manual-[a-zA-Z0-9-]+', after['id']):
            raise ValueError('New boxes require unique manual IDs')
        if set(after) != {'id', 'raw_id', 'box', 'status', 'note', 'origin'} or after['origin'] != {'kind': 'manual'}:
            raise ValueError('Manual boxes cannot impersonate source provenance')
        image['objects'].append(copy.deepcopy(after))
    elif change['kind'] == 'update':
        if existing is None or change['before'] != existing or set(after) != set(existing):
            raise ValueError('Correction does not match its preceding object')
        if any(after[key] != existing[key] for key in existing if key not in OBJECT_KEYS):
            raise ValueError('Source provenance and identities are immutable')
        image['objects'][image['objects'].index(existing)] = copy.deepcopy(after)
    else:
        raise ValueError('Unknown correction event type')


def validate_state(seed, state, proposals=None):
    if proposals is not None:
        from rfdetr_annotations import validate_pack
        validate_pack(proposals, seed)
    if not isinstance(state.get('events'), list):
        raise ValueError('Missing correction history')
    expected = copy.deepcopy(seed)
    for number, change in enumerate(state['events'], 1):
        if type(change['seq']) is not int or change['seq'] != number:
            raise ValueError('Correction history is out of sequence')
        apply_event(expected, change, proposals)
        expected['events'].append(copy.deepcopy(change))
    if expected != state:
        raise ValueError('Unlogged changes or altered source/policy/approval fields')
    for image in state['images']:
        ids = [x['id'] for x in image['objects']]
        if len(ids) != len(set(ids)):
            raise ValueError('Duplicate annotation IDs')
        for obj in image['objects']:
            check_object(obj, image)
        observations = image.get('observations', [])
        if not isinstance(observations, list) or len({x['id'] for x in observations}) != len(observations):
            raise ValueError('Invalid or duplicate observations')
        for obj in observations:
            check_observation(obj, image)
        check_review(image['review'])
        if (image['review']['geometry_pass'] or image['review']['coverage_pass']) and any(x['status'] == 'pending' for x in image['objects'] + observations):
            raise ValueError('Image checklist passes require resolving all pending boxes')
    return state


def audit_sections(text, ids):
    # Accept existing Markdown or plain-text note headings; never rewrite the notes.
    hits = list(re.finditer('|'.join(re.escape(x) for x in ids), text)) if text else []
    result = {}
    for number, hit in enumerate(hits):
        end = hits[number+1].start() if number+1 < len(hits) else len(text)
        result.setdefault(hit.group(), []).append(text[hit.start():end].strip())
    return {key: '\n\n'.join(value) for key, value in result.items()}


def native_suggestions(image, source_root, output, executable, model):
    output = output / 'suggestions' / (image['id'] + '.csv')
    command = [str(executable), 'inspect', str(contained(source_root, image['path'])),
               '--max-frames', '1', '--detect', str(model), '--model-type', 'openimages',
               '--backend', 'cpu', '--confidence', '0.25', '--detections', str(output)]
    run = subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)
    if run.returncode != 0:
        raise ValueError('Suggestion inference failed for ' + image['id'] + ': ' + run.stderr[-1000:])
    classes = vocabulary()
    candidates = []
    with output.open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            if row['sequence'] != '0':
                raise ValueError('Suggestion CSV is not a single-image result')
            canonical = int(row['class_id'])
            choices = [x for x in classes if x['canonical_id'] == canonical]
            if not choices or row['label'] != choices[0]['canonical_name']:
                raise ValueError('Native suggestion vocabulary does not match the frozen registry')
            choice = next((x for x in choices if x['name'] == 'Person'), choices[0])
            box = [round(float(row[key]), 3) for key in ('left', 'top', 'right', 'bottom')]
            box = [max(0, min(value, image['width'] if n % 2 == 0 else image['height'])) for n, value in enumerate(box)]
            score = float(row['confidence'])
            if not valid_box(box, image['width'], image['height']) or not math.isfinite(score) or not 0 <= score <= 1:
                raise ValueError('Malformed suggestion box/score')
            candidates.append({'raw_id': choice['raw_id'], 'box': box, 'score': score, 'canonical_id': canonical})
    return candidates, digest(output)


def prepare(manifest, output, executable=None, model=None, corrections=None):
    manifest, output = Path(manifest).resolve(strict=True), Path(output).resolve()
    source = check_intake(manifest)
    if output.exists():
        raise FileExistsError('Choose a new annotation workspace; existing work is preserved')
    if output == manifest.parent or output.is_relative_to(manifest.parent / 'images') or output.is_relative_to(manifest.parent / 'receipts'):
        raise ValueError('Annotation output cannot replace intake or photographs/receipts')
    if bool(executable) != bool(model):
        raise ValueError('Suggestions require both the existing native executable and model')
    output.mkdir(parents=True, exist_ok=False)
    (output / 'suggestions').mkdir()
    source_hash = digest(manifest)
    notes, note_hashes = {}, {}
    ids = [x['id'] for x in source['images']]
    for name in ('my-review-notes.md', 'assistant-audit-15-60.md'):
        path = manifest.parent / name
        if path.is_file():
            note_hashes[name] = digest(path)
            for image_id, section in audit_sections(path.read_text(encoding='utf-8-sig'), ids).items():
                notes.setdefault(image_id, []).append(name + '\n' + section)
    suggestions_info = {'enabled': bool(model), 'purpose': 'Unverified proposals, not ground truth or independent evaluation'}
    if model:
        executable, model = Path(executable).resolve(strict=True), Path(model).resolve(strict=True)
        suggestions_info.update(model_sha256=digest(model), executable_sha256=digest(executable), confidence=0.25, backend='cpu')
    seed = {'schema': 1, 'purpose': 'annotation-draft-only', 'approved_for_training': False,
            'source_manifest_sha256': source_hash, 'policy': read_json(POLICY),
            'classes': vocabulary(), 'suggestions': suggestions_info, 'images': [], 'events': []}
    skipped = 0
    for number, image in enumerate(source['images'], 1):
        objects = [{'id': 'publisher-' + str(n+1), 'raw_id': obj['raw_id'], 'box': obj['box'],
                    'status': 'pending', 'note': '', 'origin': {'kind': 'publisher', 'record': obj}}
                   for n, obj in enumerate(image['objects'])]
        if model:
            candidates, csv_hash = native_suggestions(image, manifest.parent, output, executable, model)
            for n, candidate in enumerate(candidates, 1):
                if any(vocabulary()[obj['raw_id']]['canonical_id'] == candidate['canonical_id'] and iou(obj['box'], candidate['box']) >= 0.45 for obj in objects):
                    skipped += 1
                    continue
                objects.append({'id': 'model-' + str(n), 'raw_id': candidate['raw_id'], 'box': candidate['box'],
                                'status': 'pending', 'note': 'Model suggestion: visually verify class and boundary.',
                                'origin': {'kind': 'model', 'confidence': candidate['score'], 'csv_sha256': csv_hash}})
        photo_url = Path(os.path.relpath(contained(manifest.parent, image['path']), output)).as_posix()
        seed['images'].append({'id': image['id'], 'number': number, 'anchor': image['selected_category'],
                              'domain': image['selected_domain'], 'sha256': image['sha256'],
                              'width': image['width'], 'height': image['height'], 'photo_url': photo_url,
                              'attribution': image['attribution'], 'audit': '\n\n'.join(notes.get(image['id'], [])),
                              'objects': objects, 'review': {'reviewer': '', 'notes': '', 'geometry_pass': False,
                                'coverage_pass': False, 'holds': ['Whole-image label completeness unverified',
                                   'Hierarchy/parts/special-case policy requires release review', 'Source-use rights unverified'],
                                'rights_evidence': ''}})
        print(f'Prepared photo {number}/{len(ids)}: {image["id"]}', flush=True)
    state = copy.deepcopy(seed)
    if corrections:
        apply_corrections(state, corrections, source_hash)
    validate_state(seed, state)
    write_json(output / 'seed.json', seed)
    write_json(output / 'annotations.json', state)
    write_json(output / 'workspace.json', {'schema': 1, 'source_manifest': str(manifest),
        'source_manifest_sha256': source_hash, 'seed_sha256': digest(output / 'seed.json'),
        'policy_sha256': digest(POLICY), 'note_sha256': note_hashes, 'created_at_utc': utc(),
        'visual_audit_acceptance': 'User accepted the 60 visual audits; box completeness and rights not approved',
        'overlapping_model_candidates_skipped': skipped})
    render_editor(seed, state, output / 'editor.html')
    write_json(output / 'preparation-summary.json', summary(state))
    return state


def render_editor(seed, state, path, proposals=None):
    validate_state(seed, state, proposals)
    path = Path(path)
    if path.exists():
        raise FileExistsError('Existing editor is preserved; choose a new file')
    document = TEMPLATE.read_text(encoding='utf-8')
    # Every new page has hidden RF controls; old generated pages remain untouched.
    document = document.replace('<aside>', '<aside><section id="rf-panel" hidden><h2>RF-DETR suggestions</h2>'
        '<p class="small">Click a teal box or a suggestion below. Check the label and edges, then Confirm, Save, or write a reason and Remove. '
        'These predictions are not yet saved annotations. Check for duplicates and missed objects.</p>'
        '<label><input id="show-rf" type="checkbox" checked> Show RF-DETR suggestions (teal dashed)</label>'
        '<p id="rf-counts" class="small"></p><div id="rf-list"></div><hr></section>')
    document = document.replace('<fieldset id="box-fields"', '<p id="rf-duplicate" class="warning small" hidden></p><fieldset id="box-fields"')
    document = document.replace('</style>', '#rf-list{max-height:180px;overflow:auto}#rf-list button{display:block;width:100%;text-align:left;margin-bottom:4px;font-size:13px}</style>')
    if proposals is not None:
        document = document.replace('</header>', '</header><p class="warning" style="margin:12px 18px">'
            'RF-DETR-assisted review. If you already edited an earlier page, save its annotations JSON and import it here first. '
            'Earlier boxes/corrections are preserved. Teal dashed boxes are unreviewed RF suggestions, not training labels. '
            'A percentage is a model score, not a guarantee of correctness.</p>')
    # Prevent source text escaping JSON script blocks. Displayed text uses textContent.
    payload_data = {'seed': seed, 'state': state}
    if proposals is not None:
        payload_data['proposals'] = proposals
    payload = json.dumps(payload_data, ensure_ascii=True).replace('<', '\\u003c')
    script = EDITOR_SCRIPT.read_text(encoding='utf-8')
    if '</script' in script.lower():
        raise ValueError('Editor script cannot close its HTML script block')
    path.write_text(document.replace('__ANNOTATION_SCRIPT__', script).replace('__ANNOTATION_PAYLOAD__', payload), encoding='utf-8')


def apply_corrections(state, path, source_hash):
    corrections = read_json(path)
    if corrections['source_manifest_sha256'] != source_hash:
        raise ValueError('Correction plan belongs to another intake')
    for change in corrections['changes']:
        image = next(x for x in state['images'] if x['id'] == change['image_id'])
        if change['kind'] == 'add':
            box = change['box']
            if change.get('normalized'):
                box = [round(x * (image['width'] if n % 2 == 0 else image['height']), 3) for n, x in enumerate(box)]
            after = {'id': change['object_id'], 'raw_id': change['raw_id'], 'box': box,
                     'status': change.get('status', 'pending'), 'note': change['reason'], 'origin': {'kind': 'manual'}}
        else:
            after = copy.deepcopy(next(x for x in image['objects'] if x['id'] == change['object_id']))
            after.update(change['fields'])
            after['note'] = change['reason']
        event(state, image['id'], change['kind'], change['object_id'], after, 'assistant-draft-correction')


def summary(state):
    objects = [obj for image in state['images'] for obj in image['objects']]
    observations = [obj for image in state['images'] for obj in image.get('observations', [])]
    return {'schema': 1, 'purpose': 'annotation-draft-only', 'approved_for_training': False,
            'images': len(state['images']), 'objects_by_state': {s: sum(x['status'] == s for x in objects) for s in STATES},
            'objects_by_origin': {s: sum(x['origin']['kind'] == s for x in objects) for s in ('publisher', 'model', 'manual')},
            'correction_events': len(state['events']),
            'unsupported_observations_by_state': {s: sum(x['status'] == s for x in observations) for s in STATES},
            'geometry_passes': sum(x['review']['geometry_pass'] for x in state['images']),
            'coverage_passes': sum(x['review']['coverage_pass'] for x in state['images']),
            'images_with_holds': sum(bool(x['review']['holds']) for x in state['images']),
            'limits': 'Counts describe drafts, not complete annotations, rights clearance, training readiness or accuracy.'}


def load_checked(workspace, annotations):
    workspace = Path(workspace).resolve(strict=True)
    meta = read_json(workspace / 'workspace.json')
    if digest(workspace / 'seed.json') != meta['seed_sha256'] or digest(POLICY) != meta['policy_sha256']:
        raise ValueError('Workspace seed or annotation policy changed')
    if digest(meta['source_manifest']) != meta['source_manifest_sha256']:
        raise ValueError('Immutable intake manifest changed')
    source = check_intake(meta['source_manifest'])
    seed = read_json(workspace / 'seed.json')
    state = validate_state(seed, read_json(annotations), load_proposals(workspace, seed))
    return source, state


def load_proposals(workspace, seed):
    meta = read_json(Path(workspace)/'workspace.json')
    if 'rfdetr_proposals' not in meta:
        return None
    from rfdetr_annotations import validate_pack
    receipt = meta['rfdetr_proposals']
    path = contained(workspace, receipt['path'])
    if digest(path) != receipt['sha256']:
        raise ValueError('RF proposal catalogue changed')
    return validate_pack(read_json(path), seed)


def export_draft(workspace, annotations, output):
    source, state = load_checked(workspace, annotations)
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError('Choose a new draft export directory')
    output.mkdir(parents=True, exist_ok=False)
    (output / 'labels').mkdir()
    coco = {'info': {'purpose': 'annotation-draft-only', 'approved_for_training': False},
            'images': [], 'annotations': [], 'categories': [{'id': x['raw_id'], 'name': x['name']} for x in vocabulary()]}
    corrected = copy.deepcopy(source)
    corrected['purpose'] = 'annotation-draft-only'
    corrected['approved_for_training'] = False
    for n, image in enumerate(state['images'], 1):
        source_root = Path(read_json(Path(workspace) / 'workspace.json')['source_manifest']).parent
        original_path = Path(os.path.relpath(contained(source_root, source['images'][n-1]['path']), output)).as_posix()
        coco['images'].append({'id': n, 'file_name': original_path, 'width': image['width'], 'height': image['height'],
                               'original_sha256': image['sha256']})
        labels, objects = [], []
        for obj in image['objects']:
            if obj['status'] == 'rejected':
                continue
            x1, y1, x2, y2 = obj['box']
            labels.append(f'{obj["raw_id"]} {(x1+x2)/2/image["width"]:.9f} {(y1+y2)/2/image["height"]:.9f} {(x2-x1)/image["width"]:.9f} {(y2-y1)/image["height"]:.9f}')
            coco['annotations'].append({'id': len(coco['annotations'])+1, 'image_id': n, 'category_id': obj['raw_id'],
                'bbox': [x1, y1, x2-x1, y2-y1], 'area': (x2-x1)*(y2-y1),
                'iscrowd': int(obj['origin'].get('record', {}).get('group_of') == 1),
                'draft_state': obj['status'], 'origin': obj['origin'], 'correction_id': obj['id']})
            objects.append({'raw_id': obj['raw_id'], 'box': obj['box'], 'source': 'annotation-draft', 'draft_state': obj['status']})
        (output / 'labels' / (image['id'] + '.txt')).write_text('\n'.join(labels) + ('\n' if labels else ''), encoding='utf-8')
        corrected['images'][n-1]['objects'] = objects
        corrected['images'][n-1]['split'] = 'unassigned'
        corrected['images'][n-1]['review'] = {'complete_target_classes': False, 'rights_verified': False,
                                            'lighting': 'unreviewed', 'reviewer': None, 'reviewed_at_utc': None}
    # Relative paths in a draft manifest point back to clean originals, never copied/altered photos.
    source_root = Path(read_json(Path(workspace) / 'workspace.json')['source_manifest']).parent
    for image in corrected['images']:
        image['path'] = Path(os.path.relpath(contained(source_root, image['path']), output)).as_posix()
    write_json(output / 'draft-manifest.json', corrected)
    write_json(output / 'draft-coco.json', coco)
    write_json(output / 'annotations.json', state)
    write_json(output / 'unsupported-observations.json', observation_export(state))
    write_json(output / 'validation-summary.json', summary(state))
    (output / 'DRAFT-NOT-FOR-TRAINING.md').write_text(
        '# Draft annotation export — do not train\n\nYOLO text and COCO JSON include pending proposals. '
        'Original images are referenced, not copied. Class IDs stay 0–600. Unsupported-object observation boxes '
        'are saved separately in unsupported-observations.json and excluded from COCO/YOLO targets. '
        'No data.yaml or dataset lock exists. '
        'Image completeness, rights, hierarchy/flag policy, source-group splits and leakage review remain independent gates.\n', encoding='utf-8')
    return summary(state)


def observation_export(state):
    return {'schema': 1, 'purpose': 'unsupported-object-observations-only', 'approved_for_training': False,
            'excluded_from_training_targets': True, 'source_manifest_sha256': state['source_manifest_sha256'],
            'images': [{'image_id': image['id'], 'width': image['width'], 'height': image['height'],
                        'observations': copy.deepcopy(image.get('observations', []))} for image in state['images']]}
