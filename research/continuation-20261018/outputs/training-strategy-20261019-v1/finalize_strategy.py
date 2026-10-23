"""Hash-verify immutable inputs, record the current blocked data gate and handoff."""
import json
from pathlib import Path

from check_data_readiness import ROOT, check, digest, read

OUT = ROOT.parent
CONT = OUT.parent
TOOLS = OUT / 'selector-batch-proposal-7809335-20261018-v1/rf-selector-a77d9663-v1'
FROZEN = OUT / 'frozen-head-cpu-7809335-20261018-v1'
DIAG = OUT / 'selector-diagnosis-7818553-20261018-v1'
APP = OUT / 'native-unified-20261019-v1'


def save(name, obj):
    (ROOT / name).write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def ref(path):
    return {'path': str(path), 'sha256': digest(path)}


def main():
    inputs = read(ROOT / 'INPUT_AUDIT.json')
    release = TOOLS / 'release/candidate-manifest-v2.json'
    checkpoint = TOOLS / 'inputs/selected-7805570.pt'
    unchanged = []
    for path, expected in (
        (ROOT / 'DIAGNOSTIC_PLAN.json', inputs['plan_sha256']),
        (release, inputs['manifest_sha256']),
        (checkpoint, inputs['checkpoint_sha256']),
        (FROZEN / 'cache-full-layout/initial-head.pt', inputs['initial_head_sha256']),
    ):
        actual = digest(path)
        assert actual == expected, path
        unchanged.append({'path': str(path), 'sha256': actual, 'unchanged': True})
    index = read(FROZEN / 'CACHE_INDEX_FULL_LAYOUT.json')
    for row in inputs['cache_records']:
        assert row['split'] == 'train'
        path = ((FROZEN / 'cache-full-layout') if row['image_id'] in index else
                (DIAG / 'local-contrast/cache')) / (row['image_id'] + '.pt')
        assert digest(path) == row['cache_sha256'], path
    models = []
    for row in read(APP / 'MODEL_INTEGRITY.json'):
        actual = digest(APP / 'app/models' / row['file'])
        assert actual == row['sha256'], row['file']
        models.append({'file': row['file'], 'sha256': actual, 'unchanged': True})
    save('FINAL_INPUT_INTEGRITY.json', {'source_inputs': unchanged, 'TRAIN_caches_unchanged': len(inputs['cache_records']),
                                       'app_models': models, 'app_models_unchanged': len(models)})
    intake = OUT / 'billboard-data-refresh-7818553-20261018-v1/data-tools-v1/exclusions.json'
    current = {'schema': 'frametrail-billboard-readiness-v1', 'taxonomy_id': 'nextdata7769109-taxonomy-v1',
               'protected_release_ref': ref(release), 'prior_intakes_ref': ref(intake), 'records': [],
               'collection_state': 'KIT unavailable per user; latest submission/completion unconfirmed',
               'local_unused_candidates': '13 scene-triaged, rights/box/scene release checks pending; TRAIN-only candidates, not fresh held-out evidence'}
    save('CURRENT_READINESS_INPUT.json', current)
    report = check(current)
    assert not report['ready_for_package_preparation']
    save('CURRENT_READINESS.json', report)
    tests = read(ROOT / 'READINESS_TESTS.json')
    assert len(tests['checks']) == 15 and all(r['passed'] for r in tests['checks'])
    ledger = read(ROOT / 'EXPERIMENT_LEDGER.json')
    count = sum(r['configurations'] for r in ledger['families'])
    assert count == 31
    state = {
        'status': 'training-strategy-and-TRAIN-only-diagnostics-complete-fresh-data-blocked',
        'date': '2026-10-19', 'primary_priority': 'fine-tuning strategy', 'secondary_priority': 'lean app packaging and small user guide',
        'report': str(ROOT / 'STRATEGY.md'), 'experiment_design': str(ROOT / 'EXPERIMENT_DESIGN.json'),
        'previous_documented_configurations': count, 'new_TRAIN_only_probe_fits': 8,
        'TRAIN_geometry_coverage': {'matched': 37, 'targets': 54, 'matching_bug_found': False},
        'nonlinear_head_advantage_established': False,
        'data_ready': False, 'readiness_contract_tests_passed': 15,
        'new_cluster_contact': False, 'new_cluster_jobs': 0, 'cluster_entitlements_currently_verified': False,
        'cluster_state': 'Down per user; latest data collection submission/completion unconfirmed; do not retry or replace',
        'checkpoint_sha256': inputs['checkpoint_sha256'], 'candidate_selected': False,
        'production_adoption': False, 'ONNX_numerical_hold_preserved': True,
        'app_files_changed': False, 'seven_app_models_hash_verified_unchanged': True,
        'standing_authorization': 'Continue bounded authorized work without routine approval; direct KIT authentication and real consequential blockers only. No pasted credentials.',
        'communication': 'End every response with one concrete FrameTrail next step and why; carry this into every continuation.',
        'next_step': 'When KIT returns, recover the existing data-collection state and complete source/identity/scene/box review; do not submit a replacement or another same-data training sweep.',
    }
    save('CURRENT_STATE.json', state)
    handoff = CONT / 'CURRENT_HANDOFF.md'
    prior = ROOT / 'PRIOR_HANDOFF.md'
    if not prior.exists():
        prior.write_bytes(handoff.read_bytes())
    header = f'''# Current FrameTrail state — training strategy first, 19 October 2026

Latest user priority is fine-tuning strategy before further app work. The strategy pass is complete at:
{ROOT}

Read STRATEGY.md and CURRENT_STATE.json there first. The new evidence includes a TRAIN-only one-to-one assignment audit (37/54 covered; actual matcher also 37), eight fixed identity-fold CPU capacity probes, independent metric recomputation, a 31-configuration prior-experiment ledger, and visual triage of 13 unused local photos (one clear advertising-board context, eight boundary holds, four non-target anchor contexts). No matcher bug or consistent nonlinear-head ranking advantage was found. These are TRAIN/development diagnostics, not fresh test accuracy. Source checkpoint/release/caches and seven app model hashes were rechecked unchanged.

The conditional next experiment is two existing head methods crossed with two sampling seeds, after a genuinely reviewed fresh release. Four scientific conditions, with the two frozen-selector controls on local CPU caches; only two changing-selector trials need GPUs. Max two concurrent A100s, 45 minutes/GPU task, 1.5 allocated GPU-hours, 1,500 updates/condition, no retries/replacements. Paired sample schedules, common pinned CPU-reference selection scores and both-seed gains are required. Exact design is not sealed or runnable: fresh data, source/loss/schema/cache preflight and live account admission are still required. Preserve both-baseline per-class and unknown-count guards, fresh-test isolation and the independent ONNX numerical gate. No new candidate was selected; RF remains job7805570 step100; production_adoption=false.

The readiness screen passed 15 synthetic contracts and correctly reports current data shortfalls. Its linked review assertions do not replace semantic, rights, perceptual/scene or authoritative full-release checks. No held-out images/caches were used in the new fits. Old local residual candidates are TRAIN-only review material, never fresh validation/test. Do not launch another grid on the same 20 positive photos or add model capacity just because it fits TRAIN.

KIT remains down per the user; no SSH or cluster contact occurred. Latest data-collection submission/completion remains unconfirmed. When access returns, inspect/retrieve existing state, never submit a duplicate/replacement. Latest standing authorization permits bounded continuation without routine approval, but does not waive resource/data/model gates. Direct OTP/password authentication stays with the user.

App is secondary. No app files changed in this pass. Measured current app payload is 731,418,828 bytes, including 481,562,612 bytes in seven models. Next app scope: audit the minimum model set that retains actual category coverage, then reversible lean CPU packaging with optional model/backend packs and a small local Quick Guide/section jump, with before/after real workflow and cost checks. Default YOLOX-S alone must not be assumed to satisfy billboard/washer coverage. Size reduction is not an inference speed claim. Existing unified-window package and stable launchers below remain current.

Continue local work autonomously; do not ask for routine permission. End every user-facing response with the single best concrete project next step and why. Preserve these instructions in every handoff.

Next step: recover the existing collection when KIT is available and finish frozen source/scene/box review, because reviewed fresh data is the missing prerequisite for a useful training comparison.

---

## Preserved app and earlier evidence handoff

'''
    handoff.write_text(header + prior.read_text(encoding='utf-8-sig'), encoding='utf-8')
    excluded = {'FINAL_RECEIPT.json'}
    files = [p for p in ROOT.iterdir() if p.is_file() and p.name not in excluded]
    save('FINAL_RECEIPT.json', {'status': state['status'], 'files': [ref(p) for p in sorted(files)],
                                'new_cluster_jobs': 0, 'model_promotions': 0, 'app_changes': 0,
                                'readiness_contracts_passed': 15, 'data_gate_correctly_blocked': True})
    print(json.dumps({'status': state['status'], 'prior_configurations': count, 'probe_fits': 8,
                      'readiness_tests': 15, 'data_ready': False, 'app_model_hashes_unchanged': len(models)}))


if __name__ == '__main__':
    main()
