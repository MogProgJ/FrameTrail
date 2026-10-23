"""Combine the block decision files into gap accounting against the fresh-role minima."""
import hashlib, json, pathlib

HERE = pathlib.Path(__file__).resolve().parent
GAPS = {'train': 11, 'val': 6, 'test': 4}
CURRENT_TRAIN_FAMILIES = {'shop-business-lettering': 0, 'traffic-information-signs': 4,
                          'indoor-frames-screens-boards': 8, 'household-laundry': 7}
FAMILY_MINIMUM = 5


def main():
    files = sorted(HERE.glob('REVIEW_*_DECISIONS.json'))
    records = [r for f in files for r in json.loads(f.read_text())['records']]
    by_role = {}
    for r in records:
        by_role.setdefault(r['role'], {}).setdefault(r['decision_133'], []).append(r['image_id'])
    absent_train = [r for r in records if r['role'] == 'train' and r['decision_133'] == 'absent']
    families = dict(CURRENT_TRAIN_FAMILIES)
    unassigned = []
    for r in absent_train:
        if r['confuser_family'] in families:
            families[r['confuser_family']] += 1
        else:
            unassigned.append(r['image_id'])
    roles = {}
    for role, gap in GAPS.items():
        found = len(by_role.get(role, {}).get('absent', []))
        roles[role] = {'gap_before': gap, 'absent_candidates_found': found, 'remaining_gap': max(0, gap - found),
                       'decisions': {k: len(v) for k, v in sorted(by_role.get(role, {}).items())}}
    summary = {
        'schema': 1, 'stage': 'absent-qualification-20261024-v1',
        'decision_files_sha256': {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in files},
        'reviewed_records': len(records),
        'roles': roles,
        'train_absent_families_after_candidates': families,
        'train_family_remaining_gaps': {k: max(0, FAMILY_MINIMUM - v) for k, v in families.items()},
        'train_absent_unassigned_family': unassigned,
        'holds_by_role': {role: by_role.get(role, {}).get('hold', []) for role in GAPS},
        'status': 'draft-candidates-not-admitted',
        'still_required_before_admission': [
            'visual scene/session comparison against prior releases and regression scenes',
            'formal rights clearance (all 223 carry photo-specific license corroboration only)',
            'independent human confirmation of assistant absence decisions',
            'resolution of the shop-business-lettering family shortfall and the TEST shortfall',
        ],
        'approved_for_training': False, 'model_predictions_used': False,
    }
    with (HERE / 'SUMMARY.json').open('x', encoding='utf-8') as handle:
        json.dump(summary, handle, indent=1)
        handle.write('\n')
    print(json.dumps({k: summary[k] for k in ('roles', 'train_absent_families_after_candidates', 'train_family_remaining_gaps', 'train_absent_unassigned_family', 'holds_by_role')}, indent=1))


if __name__ == '__main__':
    main()
