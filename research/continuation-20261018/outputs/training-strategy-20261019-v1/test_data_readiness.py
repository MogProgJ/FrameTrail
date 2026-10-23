"""Synthetic contract checks. Fixtures are byte/hash records, not real images."""
import copy
import json
from pathlib import Path
import tempfile

from check_data_readiness import ABSENT, POSITIVE, ROOT, check, digest, read


def run():
    results = []
    fixture_root = ROOT / 'test-fixtures'
    fixture_root.mkdir(exist_ok=True)
    assert fixture_root.resolve().is_relative_to(ROOT.resolve())
    with tempfile.TemporaryDirectory(prefix='frametrail-readiness-', dir=fixture_root) as folder:
        base = Path(folder)
        assert base.resolve().is_relative_to(fixture_root.resolve())

        def write(name, obj):
            path = base / name
            path.write_text(json.dumps(obj), encoding='utf-8')
            return {'path': str(path), 'sha256': digest(path)}

        protected = write('protected.json', {'images': [
            {'image_id': 'old-val', 'image_sha256': '1'*64, 'identity_group': 'old-held-group', 'split': 'val'},
            {'image_id': 'old-train', 'image_sha256': '2'*64, 'identity_group': 'old-train-group', 'split': 'train'},
        ]})
        prior = write('prior.json', {'images': [{'id': 'old-unused', 'sha256': '3'*64}],
                                     'known_current_identity_groups': ['old-train-group', 'old-held-group']})
        evidence = write('source.json', {'fixture': 'synthetic source review; not a licensing decision'})
        manifest = {'schema': 'frametrail-billboard-readiness-v1', 'taxonomy_id': 'nextdata7769109-taxonomy-v1',
                    'protected_release_ref': protected, 'prior_intakes_ref': prior, 'records': []}
        design = read(ROOT / 'EXPERIMENT_DESIGN.json')['data_required']
        for role in ('fresh_train', 'fresh_validation', 'fresh_test'):
            for kind in ('positive', 'absent'):
                for i in range(design[role][kind + '_photos']):
                    key = f'{role}-{kind}-{i}'
                    image = base / (key + '.bytes')
                    image.write_bytes(('synthetic, not image: ' + key).encode())
                    review = {'image_id': key, 'image_sha256': digest(image), 'identity_group': 'author-' + key,
                              'scene_group': 'scene-' + key, 'source_evidence_ref': evidence,
                              'rights_status': 'cleared-for-private-research', 'model_predictions_seen': False,
                              'duplicate_and_scene_review': {'complete': True,
                                  'compared_against_prior_sha256': prior['sha256'], 'scene_session_overlap_with_protected': False},
                              'other_unknown_classes_remain_unknown': True,
                              'billboard_scope': POSITIVE if kind == 'positive' else ABSENT,
                              'normalized_xyxy': [[.1, .2, .4, .6]] if kind == 'positive' else [],
                              'confuser_family': design['train_absent_families'][i % 4]}
                    manifest['records'].append({'image_id': key, 'split': role,
                        'image_ref': {'path': str(image), 'sha256': digest(image)},
                        'review_ref': write(key + '.json', review)})

        def verify(name, candidate, expected=None):
            report = check(candidate)
            if expected is None:
                assert report['ready_for_package_preparation'], report['errors']
            else:
                assert not report['ready_for_package_preparation'], name
                assert any(expected in error for error in report['errors']), (name, report['errors'])
            results.append({'case': name, 'passed': True})

        def review_change(name, index, updates):
            candidate = copy.deepcopy(manifest)
            record = candidate['records'][index]
            review = read(record['review_ref']['path'])
            review.update(updates)
            record['review_ref'] = write(name + '.json', review)
            return candidate

        verify('complete synthetic contract accepted', manifest)
        candidate = copy.deepcopy(manifest)
        candidate['records'] = []
        verify('empty/unreturned data fails minima', candidate, 'shortfall')
        verify('unknown class scope cannot become absence', review_change('unknown', 30, {'billboard_scope': 'unknown'}), 'Only complete')
        verify('ROI-only negative is insufficient', review_change('roi', 30, {'billboard_scope': 'negative-region-only'}), 'Only complete')
        verify('unknown multiclass labels preserved', review_change('global-bg', 0, {'other_unknown_classes_remain_unknown': False}), 'global background')
        verify('reversed/invalid boxes rejected', review_change('box', 0, {'normalized_xyxy': [[.8, .2, .1, .6]]}), 'Invalid normalized')
        verify('uncleared rights rejected', review_change('rights', 0, {'rights_status': 'pending'}), 'rights review')
        candidate = copy.deepcopy(manifest)
        candidate['records'][0]['image_ref']['sha256'] = '0'*64
        verify('changed source bytes rejected', candidate, 'SHA-256 mismatch')
        first_train = read(manifest['records'][0]['review_ref']['path'])
        first_val = 60
        verify('identity role leakage rejected', review_change('identity', first_val, {'identity_group': first_train['identity_group']}), 'Identity crosses roles')
        verify('scene/session role leakage rejected', review_change('scene', first_val, {'scene_group': first_train['scene_group']}), 'Scene/session crosses roles')
        verify('consumed predictions cannot count fresh', review_change('predictions', first_val, {'model_predictions_seen': True}), 'before model predictions')
        verify('old held identity cannot enter TRAIN', review_change('old-author', 0, {'identity_group': 'old-held-group'}), 'Old validation/test identity')
        candidate = review_change('old-unused', 0, {'image_id': 'old-unused'})
        candidate['records'][0]['image_id'] = 'old-unused'
        verify('unused old intake is not a fresh addition', candidate, 'Previously acquired')
        candidate = copy.deepcopy(manifest)
        candidate['records'][1]['review_ref'] = candidate['records'][0]['review_ref']
        verify('review for wrong image rejected', candidate, 'different image')
        verify('duplicate review coverage required', review_change('duplicates', 0, {'duplicate_and_scene_review': {'complete': False}}), 'Perceptual/identity/scene')
    report = {'status': 'synthetic-planning-contracts-passed', 'checks': results,
              'limitations': 'Byte/hash fixture contracts only; no semantic accuracy, legal determination, image decode, training eligibility or cluster admission established.'}
    (ROOT / 'READINESS_TESTS.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'passed': len(results)}))


if __name__ == '__main__':
    run()
