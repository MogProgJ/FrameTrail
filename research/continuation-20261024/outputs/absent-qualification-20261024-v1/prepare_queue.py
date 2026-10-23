"""Freeze the review order for the 223 unused candidates before any original is fetched or viewed.

Reads only text evidence already in the repository. No model, network or image access.
"""
import hashlib, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[4]
CONT = ROOT / 'research/continuation-20261018/outputs'
OUT = pathlib.Path(__file__).resolve().parent / 'QUEUE.json'
PINNED = {
    'broad-billboard-definition-20261022-v1/review-stage-v3/UNUSED_LOCAL_INVENTORY.json':
        'fc8fdff51977dcc9b34d5153181b6c32c7fc2117fbf9b64168d554fee9b61e22',
    'broad-billboard-definition-20261022-v1/TASK_DEFINITION.json':
        '03bb6d7d22af67b3bf19825c59f7ffa2d2461ea1bb6d7385d5f281fc78c3d553',
    'broad-billboard-definition-20261022-v1/first-pass-v4/ANNOTATIONS_DRAFT.json':
        '6bc12636d7d71242527c7742b3a66872f193775bae45a9d95d3c12ed3c0def2d',
    'training-strategy-20261019-v1/EXPERIMENT_DESIGN.json':
        '1287a9eeeb22baa6d45b8a9a9f85180a9b0f8f5b923c63bac24ad8596734edd9',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    for rel, expected in PINNED.items():
        if sha(CONT / rel) != expected:
            sys.exit(f'Pinned input changed: {rel}')
    inventory = json.loads((CONT / 'broad-billboard-definition-20261022-v1/review-stage-v3/UNUSED_LOCAL_INVENTORY.json').read_text())['records']
    triage = {}
    for path in sorted(CONT.glob('data-review-78*/scene-triage-*.json')):
        for item in json.loads(path.read_text())['records']:
            triage.setdefault(item.get('id') or item.get('image_id'), {
                'sheet': f'{path.parent.name}/{path.name}', 'disposition': item.get('disposition'), 'note': item.get('note')})
    role_rank = {'train': 0, 'val': 1, 'test': 2}
    # Narrow-definition dispositions most likely to contain out-of-scope confusers come first in block B/C.
    prior_rank = {'non-target-context': 0, 'boundary-hold': 1, 'exclude-composite': 2,
                  'positive-context': 3, 'positive-context-scene-check': 4}

    def block(record):
        if record['anchor'] != 'billboard':
            return 'A-contrast-anchor-all-roles'
        return 'B-train-billboard-anchor' if record['role'] == 'train' else 'C-heldout-billboard-anchor'

    entries = []
    for record in inventory:
        prior = triage[record['image_id']]
        entries.append({
            'image_id': record['image_id'], 'role': record['role'], 'anchor': record['anchor'],
            'block': block(record), 'sha256': record['sha256'], 'recorded_dhash': record['dhash'],
            'identity_group': record['identity_group'], 'intake_job': record['intake_job'],
            'source_status': record['source_status'],
            'prior_perceptual_candidates': record['prior_perceptual_candidates'],
            'publisher_billboard_box_count': len(record['publisher_billboard_boxes']),
            'prior_narrow_triage': prior,
            'public_original_url': f"https://open-images-dataset.s3.amazonaws.com/train/{record['image_id']}.jpg",
        })
    entries.sort(key=lambda e: (e['block'], role_rank[e['role']],
                                prior_rank.get(e['prior_narrow_triage']['disposition'], 9), e['image_id']))
    for index, entry in enumerate(entries):
        entry['queue_index'] = index
    queue = {
        'schema': 1,
        'stage': 'absent-qualification-20261024-v1',
        'frozen_before_original_fetch_or_viewing': True,
        'model_predictions_used': False,
        'roles_fixed': True,
        'pinned_inputs_sha256': PINNED,
        'purpose': ('Whole-photo class133 review of the unused inventory under task definition v2, seeking truly '
                    'absent photos for the fresh draft gaps TRAIN 11 / validation 6 / TEST 4, including TRAIN '
                    'shop-business-lettering 5 and traffic-information-signs 1.'),
        'execution_order': {
            'A-contrast-anchor-all-roles': 'Review all; primary absent candidates for every role.',
            'B-train-billboard-anchor': 'Review all; only source of possible genuine shop/traffic confusers in TRAIN.',
            'C-heldout-billboard-anchor': 'Review only to fill validation/TEST gaps left after block A.',
        },
        'counts': {b: sum(e['block'] == b for e in entries) for b in sorted({e['block'] for e in entries})},
        'entries': entries,
    }
    with OUT.open('x', encoding='utf-8') as handle:
        json.dump(queue, handle, indent=1)
        handle.write('\n')
    print(json.dumps(queue['counts']), sha(OUT))


if __name__ == '__main__':
    main()
