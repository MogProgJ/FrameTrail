"""Record visual scene triage; never turn publisher anchors into training labels."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NOTES = {
    'de8839b5f26c19f7': ('boundary-hold', 'CNN Grill storefront/business branding, event graphics and painted wall text; no clear advertising-board label established.'),
    '785265d5f6013c73': ('boundary-hold', 'Holiday Motel pole sign, vacancy and land-sale panel; business/property-sign boundary needs adjudication.'),
    'a9a1f1fddf8d6beb': ('boundary-hold', 'Dense hanging shop-name, medicine and property-agency signs; distant panels remain uncertain.'),
    '57f7721c23bf3259': ('non-target-anchor-context', 'Regimental Museum entrance information board; potential reviewed negative region, not whole-photo absence.'),
    '8e93c4fc32fc09d7': ('boundary-hold', 'Large construction hoarding with event/public slogans; promotional mural versus advertising board is unresolved.'),
    '1b4a042fd2a8f913': ('boundary-hold', 'Gulf African Bank shopfront/service advertising and business-name panel; strict category boundary unresolved.'),
    '000a8a98e1de3e25': ('advertising-board-context-supported', 'Freestanding roadside product advertising board visible in a distant street scene; exhaustive instance/box review still required.'),
    '6355602b20a4e59f': ('boundary-hold', 'Restaurant and shop-name hanging signs, menu/service lettering; no clear strict advertising-board label established.'),
    'd1527ee44c1c83f1': ('non-target-anchor-context', 'Close-up authorized lottery play-station shopfront notice; no whole-photo absence assigned.'),
    '69aa32c101acaf75': ('non-target-anchor-context', 'Furnishers Warehouse facade lettering and directional traffic signs; motion blur also limits review.'),
    'af36dce45d0b464b': ('non-target-anchor-context', 'Road-noise information display and church/nursery direction boards; no whole-photo absence assigned.'),
    'a0929b73c4db13c2': ('boundary-hold', 'Country Mart business-name directory and pony-rides notice; strict advertising-board boundary unresolved.'),
    '5a18b17f45949a38': ('boundary-hold', 'Sands Motel/RV Park name and price pole sign; strict advertising-board boundary unresolved.'),
}

def main():
    source = ROOT / 'LOCAL_REVIEW_QUEUE.json'
    queue = json.loads(source.read_text(encoding='utf-8'))
    assert set(NOTES) == {r['image_id'] for r in queue['records']}
    records = []
    for row in queue['records']:
        path = Path(row['source_path'])
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        assert digest == row['image_sha256']
        status, note = NOTES[row['image_id']]
        records.append({
            'image_id': row['image_id'], 'image_sha256': digest,
            'source_path': str(path), 'identity_group': row['identity_group'],
            'review': status, 'note': note,
            'reviewer': 'Codex visual scene triage, 2026-10-19',
            'independent_human_review': False, 'model_predictions_used': False,
            'exhaustive_boxes_reviewed': False, 'whole_photo_absence_assigned': False,
            'rights_verified': False, 'approved_for_training': False,
            'permitted_next_use': 'TRAIN-only candidate review; never fresh validation/test evidence',
        })
    counts = {s: sum(r['review'] == s for r in records) for s in sorted({r['review'] for r in records})}
    report = {
        'status': '13-local-scenes-visually-triaged-no-release-or-label-mutation',
        'queue_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'definition_source': 'nextdata7769109-taxonomy-v1: large physical advertising boards; distinguish traffic signs/shop lettering',
        'counts': counts, 'records': records,
        'limitation': 'Biased residual intake after earlier selection. Counts do not estimate publisher label purity. Context triage is not exhaustive annotation, rights clearance, or independent test evidence.',
    }
    (ROOT / 'LOCAL_SCENE_TRIAGE.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(counts))

if __name__ == '__main__':
    main()
