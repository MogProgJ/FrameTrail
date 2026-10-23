"""Fail-closed planning screen for a future reviewed billboard addition release.

Checks evidence links, explicit scopes, counts and known split leakage. It cannot
adjudicate image content, licensing or perceptual similarity, and does not replace
the authoritative FrameTrail release/runtime guards. No model or cluster access.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ROLES = ('fresh_train', 'fresh_validation', 'fresh_test')
POSITIVE = 'billboard-complete-positive'
ABSENT = 'billboard-whole-photo-absent'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def linked(ref):
    path = Path(ref['path'])
    if not path.is_absolute() or not path.is_file():
        raise ValueError('Evidence/image path must be an existing absolute file')
    if digest(path) != ref['sha256']:
        raise ValueError('Evidence/image SHA-256 mismatch: ' + str(path))
    return path


def check(manifest):
    design = read(ROOT / 'EXPERIMENT_DESIGN.json')['data_required']
    errors = []
    rows = []
    counts = {role: Counter() for role in ROLES}
    if manifest.get('schema') != 'frametrail-billboard-readiness-v1':
        errors.append('Unknown readiness schema')
    if manifest.get('taxonomy_id') != 'nextdata7769109-taxonomy-v1':
        errors.append('Operational billboard definition is not pinned')
    try:
        protected_path = linked(manifest['protected_release_ref'])
        prior_path = linked(manifest['prior_intakes_ref'])
        protected = read(protected_path)['images']
        prior = read(prior_path)
        prior_images = prior['images']
        if not protected or not prior_images:
            raise ValueError('Protected release/intake lists must be nonempty')
    except (KeyError, ValueError, OSError, TypeError) as exc:
        return {'ready_for_package_preparation': False, 'errors': errors + [str(exc)], 'counts': counts}
    protected_ids = {r['image_id'] for r in protected}
    protected_hashes = {r['image_sha256'] for r in protected}
    held_ids = {r['image_id'] for r in protected if r['split'] != 'train'}
    held_groups = {r['identity_group'] for r in protected if r['split'] != 'train'}
    prior_ids = {r['id'] for r in prior_images}
    prior_hashes = {r['sha256'] for r in prior_images}
    prior_groups = set(prior['known_current_identity_groups'])
    seen_ids, seen_hashes = set(), set()
    group_roles, scene_roles = defaultdict(set), defaultdict(set)
    scene_counts = Counter()
    positive_scenes, absent_scenes = defaultdict(set), defaultdict(set)
    families = Counter()
    for index, entry in enumerate(manifest.get('records', [])):
        label = 'record ' + str(index) + ': '
        try:
            image_id, role = entry['image_id'], entry['split']
            if role not in ROLES:
                raise ValueError('Unknown role')
            image_path = linked(entry['image_ref'])
            review = read(linked(entry['review_ref']))
            sha = entry['image_ref']['sha256']
            if review['image_id'] != image_id or review['image_sha256'] != sha:
                raise ValueError('Review is for a different image')
            if image_id in seen_ids or sha in seen_hashes:
                raise ValueError('Repeated image ID or exact image bytes')
            seen_ids.add(image_id)
            seen_hashes.add(sha)
            identity, scene = review['identity_group'], review['scene_group']
            if not identity or not scene or identity == 'unknown' or scene == 'unknown':
                raise ValueError('Resolved identity and scene/session groups required')
            group_roles[identity].add(role)
            scene_roles[scene].add(role)
            scene_counts[role, scene] += 1
            if image_id in protected_ids or sha in protected_hashes:
                raise ValueError('Existing release photo is replay, not a new addition')
            if image_id in prior_ids or sha in prior_hashes:
                raise ValueError('Previously acquired bytes/ID cannot count as a fresh addition; preserve separately as TRAIN-only review/replay when eligible')
            if image_id in held_ids or identity in held_groups:
                raise ValueError('Old validation/test identity cannot enter a new role')
            if role != 'fresh_train' and identity in prior_groups:
                raise ValueError('Previously acquired/developed image or identity is not fresh held-out evidence')
            if role != 'fresh_train' and review.get('model_predictions_seen') is not False:
                raise ValueError('Fresh held-out content must be frozen before model predictions')
            linked(review['source_evidence_ref'])
            if review.get('rights_status') != 'cleared-for-private-research':
                raise ValueError('Source/rights review is not cleared')
            duplicates = review['duplicate_and_scene_review']
            if (duplicates.get('complete') is not True
                    or duplicates.get('compared_against_prior_sha256') != manifest['prior_intakes_ref']['sha256']
                    or duplicates.get('scene_session_overlap_with_protected') is not False):
                raise ValueError('Perceptual/identity/scene review against pinned exclusions is incomplete')
            if review.get('other_unknown_classes_remain_unknown') is not True:
                raise ValueError('Unknown classes must not become global background')
            state = review['billboard_scope']
            boxes = review['normalized_xyxy']
            if state not in (POSITIVE, ABSENT):
                raise ValueError('Only complete positives or explicit whole-photo absence count; ROI/unknown/holds do not')
            if not isinstance(boxes, list) or bool(boxes) != (state == POSITIVE):
                raise ValueError('Complete positives need boxes; absence must have no boxes')
            for box in boxes:
                if (len(box) != 4 or not all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in box)
                        or not 0 <= box[0] < box[2] <= 1 or not 0 <= box[1] < box[3] <= 1):
                    raise ValueError('Invalid normalized billboard box')
            kind = 'positive' if state == POSITIVE else 'absent'
            counts[role][kind] += 1
            (positive_scenes if kind == 'positive' else absent_scenes)[role].add(scene)
            if role == 'fresh_train' and kind == 'absent':
                families[review.get('confuser_family', '')] += 1
            rows.append({'image_id': image_id, 'role': role, 'path': str(image_path), 'kind': kind})
        except (KeyError, ValueError, OSError, TypeError) as exc:
            errors.append(label + str(exc))
    for group, roles in group_roles.items():
        if len(roles) > 1:
            errors.append('Identity crosses roles: ' + group)
    for scene, roles in scene_roles.items():
        if len(roles) > 1:
            errors.append('Scene/session crosses roles: ' + scene)
    for (role, scene), number in scene_counts.items():
        if number > design[role]['max_photos_per_scene']:
            errors.append('Scene concentration exceeds role cap: ' + role + '/' + scene)
    for role in ROLES:
        for kind in ('positive', 'absent'):
            minimum = design[role][kind + '_photos']
            if counts[role][kind] < minimum:
                errors.append(f'{role} {kind} shortfall: {counts[role][kind]}/{minimum}')
        for kind, scenes in (('positive', positive_scenes), ('absent', absent_scenes)):
            minimum = design[role].get(kind + '_scenes', design[role][kind + '_photos'])
            if len(scenes[role]) < minimum:
                errors.append(f'{role} {kind} scene shortfall: {len(scenes[role])}/{minimum}')
    for family in design['train_absent_families']:
        if families[family] < design['minimum_train_absent_photos_per_family']:
            errors.append('TRAIN absent-family shortfall: ' + family)
    return {
        'ready_for_package_preparation': not errors, 'errors': errors,
        'counts': counts, 'train_absent_families': families, 'eligible_records': rows,
        'scope': 'Planning screen only. Semantic/rights reviews are linked assertions, not automatically adjudicated. Existing authoritative source/release/runtime guards remain mandatory. No image decoding, model fitting, cluster access or launch authorization is performed.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        report = check(read(args.manifest))
    except (KeyError, ValueError, OSError, TypeError) as exc:
        report = {'ready_for_package_preparation': False, 'errors': [str(exc)]}
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'eligible_records'}))
    raise SystemExit(0 if report['ready_for_package_preparation'] else 2)


if __name__ == '__main__':
    main()
