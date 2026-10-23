"""Independent intake/source/identity review; pixel hashes only, no model inference."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
from PIL import Image

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent
PACKAGE = OUT / 'billboard-targeted-intake-7824179-20261020-v1'
BASE = PACKAGE / 'retrieval-7840599/verified-7840599/output/billboard-data-refresh-7840599'
OLD = Path(r'C:\Users\nazee\.codex\visualizations\2026\10\15\01a141ae-c7a6-7303-a280-403af88736f3')


def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def sha(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()
def save(name, value): (ROOT/name).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def main():
    manifest = read(BASE/'manifest.json'); selection = read(BASE/'selection.json'); report = read(BASE/'collection-report.json')
    receipt = read(PACKAGE/'run-receipt.json'); source = read(ROOT/'source-review/source-evidence-review.json')
    archive = PACKAGE/'retrieval-7840599/frametrail-data-refresh-results-7840599.tar.gz'
    assert sha(archive) == receipt['archive_sha256']
    assert sha(BASE/'manifest.json') == receipt['manifest_sha256'] == report['manifest_sha256']
    assert report['plan_sha256'] == selection['plan_sha256'] == sha(PACKAGE/'SCOPE.json')
    assert report['downloaded'] == len(manifest['images']) == len(selection['images']) == 180
    assert not report['failures'] and not report['training'] and not report['model_inference']
    assert selection['split_frozen_before_download_and_predictions']
    expected = {r['id']: r for r in selection['images']}; sources = {r['image_id']: r for r in source['images']}
    prior = read(PACKAGE/'data-tools-v1/exclusions.json')['images']
    assert len(prior) == 2171
    prior_ids = {r['id'] for r in prior}; prior_hashes = {r['sha256'] for r in prior}
    prior_owner_ids = defaultdict(set); evidence_sources = []
    for relative in ('scale-review-7752340-v1/source-evidence-review.json',
                     'nextdata-source-review-7769109-v1/source-evidence-review.json',
                     'gap363-source-review-7787611-v1/source-evidence-review.json'):
        path = OLD/relative; data = read(path); evidence_sources.append({'path': str(path), 'sha256': sha(path)})
        for row in data['images']:
            if row.get('identity_group'):
                prior_owner_ids[row['identity_group']].add(row['image_id'])
    previous_source = OUT/'data-review-7824179-20261020-v1/source-review/source-evidence-review.json'
    evidence_sources.append({'path':str(previous_source),'sha256':sha(previous_source)})
    for prior_row in read(previous_source)['images']:
        if prior_row.get('identity_group'):
            prior_owner_ids[prior_row['identity_group']].add(prior_row['image_id'])
    release = read(OUT/'selector-batch-proposal-7809335-20261018-v1/rf-selector-a77d9663-v1/release/candidate-manifest-v2.json')
    for row in release['images']: prior_owner_ids[row['identity_group']].add(row['image_id'])
    rows = []; owner_new = defaultdict(list); seen_ids = set(); seen_hashes = set()
    for row in manifest['images']:
        i = row['id']; path = BASE/row['path']; original = expected[i]; s = sources[i]
        assert re.fullmatch(r'[0-9a-f]{16}', i) and path.resolve().is_relative_to(BASE.resolve())
        assert sha(path) == row['sha256'] and path.stat().st_size == row['bytes']
        assert i not in seen_ids and row['sha256'] not in seen_hashes
        seen_ids.add(i); seen_hashes.add(row['sha256'])
        assert row['prospective_split'] == original['prospective_split']
        assert not row['approved_for_training'] and not row['rights_verified']
        with Image.open(path) as image:
            assert image.format == 'JPEG' and image.size == (row['width'], row['height'])
            assert image.width*image.height <= 40_000_000
            gray = image.convert('L').resize((9,8)); values = list(gray.getdata()); bits = 0
            for y in range(8):
                for x in range(8): bits = (bits<<1) | int(values[y*9+x] > values[y*9+x+1])
            assert f'{bits:016x}' == row['dhash']
        known_exact = i in prior_ids or row['sha256'] in prior_hashes
        prior_matches = [{'id': p['id'], 'distance': (bits ^ int(p['dhash'],16)).bit_count()}
                         for p in prior if p.get('dhash') and (bits ^ int(p['dhash'],16)).bit_count() <= 6]
        group = s.get('identity_group'); owner_new[group].append(i) if group else None
        description = str(s.get('creator_notices',{}))
        notices = [m.group(0) for m in re.finditer(r'\b(?:no\s+AI|not\s+for\s+AI|all\s+rights\s+reserved|do\s+not\s+(?:use|train)|no\s+machine\s+learning)\b', description, re.I)]
        rows.append({'image_id': i, 'path': str(path), 'sha256': row['sha256'], 'dhash': row['dhash'],
                     'anchor': row['selected_category'], 'role': row['prospective_split'],
                     'source_status': s['status'], 'identity_group': group,
                     'known_exact_duplicate': known_exact,
                     'known_prior_identity': sorted(prior_owner_ids.get(group, set())),
                     'prior_perceptual_candidates': sorted(prior_matches, key=lambda r:r['distance']),
                     'photo_notice_fragments_for_review': notices,
                     'publisher_billboard_boxes': [b for b in row['publisher_boxes'] if b['raw_id']==46],
                     'rights_cleared': False, 'content_reviewed': False, 'approved_for_training': False})
    for row in rows:
        row['same_resolved_owner_new'] = owner_new.get(row['identity_group'], []) if row['identity_group'] else []
        row['new_perceptual_candidates'] = [{'id': other['image_id'], 'distance': (int(row['dhash'],16)^int(other['dhash'],16)).bit_count()}
                                             for other in rows if other['image_id']!=row['image_id'] and (int(row['dhash'],16)^int(other['dhash'],16)).bit_count() <= 6]
        row['source_and_identity_eligible_for_visual_review'] = (row['source_status']=='photo-specific-license-corroborated'
            and not row['known_exact_duplicate'] and not row['known_prior_identity'] and len(row['same_resolved_owner_new'])==1)
    counts = Counter((r['anchor'], r['role']) for r in rows if r['source_and_identity_eligible_for_visual_review'])
    save('INTAKE_AUDIT.json', {'status':'archive-selection-pixels-and-source-identities-independently-audited',
        'manifest_sha256': sha(BASE/'manifest.json'), 'selection_sha256': sha(BASE/'selection.json'),
        'source_review_sha256': sha(ROOT/'source-review/source-evidence-review.json'),
        'prior_owner_evidence': evidence_sources, 'prior_intake_images':len(prior),
        'photos':len(rows), 'known_exact_duplicates':sum(r['known_exact_duplicate'] for r in rows),
        'known_prior_owner_photos':sum(bool(r['known_prior_identity']) for r in rows),
        'new_owner_collision_photos':sum(len(r['same_resolved_owner_new'])>1 for r in rows),
        'prior_perceptual_candidate_photos':sum(bool(r['prior_perceptual_candidates']) for r in rows),
        'new_perceptual_candidate_photos':sum(bool(r['new_perceptual_candidates']) for r in rows),
        'source_identity_eligible_counts':[{'anchor':a,'role':role,'count':n} for (a,role),n in sorted(counts.items())],
        'pixel_decode_and_dhash_recomputed': True, 'prospective_splits_unchanged': True,
        'model_inference':False, 'training':False, 'records': rows})
    eligible = [r for r in rows if r['source_and_identity_eligible_for_visual_review']]
    save('VISUAL_REVIEW_QUEUE.json', {'records': sorted(eligible,key=lambda r:(r['anchor']!='billboard',r['role'],r['anchor'],r['image_id'])),
                                    'limits':'Perceptual/scene candidates and photo notices still require review. Source/identity eligible is not annotation/training clearance.'})
    print(json.dumps({'photos':len(rows),'source_identity_eligible':len(eligible),'prior_owner':sum(bool(r['known_prior_identity']) for r in rows),
                      'new_owner_collisions':sum(len(r['same_resolved_owner_new'])>1 for r in rows),
                      'prior_perceptual':sum(bool(r['prior_perceptual_candidates']) for r in rows),
                      'new_perceptual':sum(bool(r['new_perceptual_candidates']) for r in rows)}))


if __name__ == '__main__': main()
