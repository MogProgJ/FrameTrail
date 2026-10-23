"""Finalize verified local artifacts and update the stable continuation launchers."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent
CONT = ROOT.parent.parent
OLD = ROOT.parent / 'native-unified-20261019-v1'
STRATEGY = ROOT.parent / 'training-strategy-20261019-v1'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(name, obj):
    (ROOT / name).write_text(json.dumps(obj, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def main():
    checks = read(ROOT / 'VERIFICATION_PROGRESS.json')
    assert len(checks) == 9 and all(r['exit_code'] == 0 for r in checks)
    assert '100% tests passed, 0 tests failed out of 13' in (ROOT / 'regression-final-console.txt').read_text()
    for folder in ('guide-verified', 'guide-verified-scale125', 'unified-final', 'unified-scale125', 'full-cache-balanced'):
        assert read(ROOT / 'evidence' / folder / 'result.json')['status'] == 'passed'
    models = read(ROOT / 'MODEL_INTEGRITY.json')
    assert len(models) == 7 and sum(r['core'] for r in models) == 4
    for model in models:
        assert sha(ROOT / model['relative_path']) == model['sha256']
        assert sha(OLD / 'app/models' / model['file']) == model['sha256']
    assert sha(ROOT / 'app/frametrail-desktop.exe') == sha(ROOT / 'build/Release/frametrail-desktop.exe')
    for directory in ('src', 'include'):
        for old in (OLD / 'source' / directory).rglob('*'):
            if old.is_file():
                assert sha(old) == sha(ROOT / 'source' / old.relative_to(OLD / 'source'))
    strategy = read(STRATEGY / 'CURRENT_STATE.json')
    assert not strategy['data_ready'] and not strategy['production_adoption']
    save('CORE_MODELS.json', {'models': [r for r in models if r['core']],
                             'category_coverage': read(ROOT / 'MODEL_COVERAGE.json'),
                             'accuracy_or_inference_speed_change': False})
    archive = ROOT / 'FrameTrail-core.zip'
    members = [(p, 'FrameTrail/app/' + p.relative_to(ROOT / 'app').as_posix()) for p in sorted((ROOT / 'app').rglob('*')) if p.is_file()]
    for name in ('Run-FrameTrail.cmd', 'READ-ME.txt', 'CORE_MODELS.json'):
        members.append((ROOT / name, 'FrameTrail/' + name))
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=3) as bundle:
        for path, name in members:
            assert path.resolve().is_relative_to(ROOT.resolve())
            bundle.write(path, name)
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.namelist() == [name for _, name in members]
        for path, name in members:
            with bundle.open(name) as stream:
                assert hashlib.file_digest(stream, 'sha256').hexdigest() == sha(path)
    save('CORE_ARCHIVE.json', {'archive': str(archive), 'bytes': archive.stat().st_size, 'sha256': sha(archive),
                              'members': len(members), 'readback_hashes_verified': True,
                              'optional_models_included': False, 'models': 4})
    for name in ('Run-FrameTrail.cmd', 'Run-Balanced-Preview.cmd'):
        target = CONT / name
        backup = ROOT / ('PREVIOUS-' + name)
        if not backup.exists():
            backup.write_bytes(target.read_bytes())
        target.write_bytes(f'@echo off\r\ncall "%~dp0outputs\\{ROOT.name}\\{name}" %*\r\n'.encode())
    sizes = read(ROOT / 'PACKAGE_SIZE.json')
    guide = read(ROOT / 'evidence/guide-verified/result.json')
    receipt = {
        'status': 'lean-core-and-local-guide-packaged-and-verified', 'date': '2026-10-19',
        'package': str(ROOT), 'launcher': str(CONT / 'Run-FrameTrail.cmd'),
        'application_sha256': sha(ROOT / 'app/frametrail-desktop.exe'),
        'features': ['Embedded searchable Quick Guide, Ctrl+K/F1', 'Object-category lookup with explicit model selection',
                     'Existing single-window sections/state preserved', 'Slower main-preview polling while idle; fast active polling retained'],
        'package_sizes': sizes, 'core_archive': read(ROOT / 'CORE_ARCHIVE.json'),
        'default_model': 'YOLOX-S', 'core_model_label_union': 615,
        'optional_models': [r['file'] for r in models if not r['core']],
        'all_seven_weights_unchanged': True, 'inference_and_core_sources_unchanged': True,
        'existing_regression_checks_passed': 13, 'checks': checks,
        'guide_main_idle_polls_observed_per_second': guide['idle_main_polls_observed_in_1_second'],
        'previous_main_polling_interval_ms': 10, 'new_idle_main_interval_ms': 100, 'active_main_interval_ms': 10,
        'inference_speedup_claimed': False, 'working_memory_reduction_claimed': False,
        'production_adoption': False, 'RF_ONNX_numerical_hold': True,
        'RF_checkpoint': strategy['checkpoint_sha256'], 'new_cluster_jobs': 0, 'cluster_contact': False,
        'training_status': 'Fresh reviewed collection remains unavailable/unconfirmed during KIT outage; strategy unchanged, no duplicate job.',
        'verification_limits': ['Qt offscreen and simulated 125% scale, not physical display/screen-reader certification',
                                'Camera entered only while off; no live camera hardware test',
                                'Full core plus optional models uses approximately the former total bytes; research history is preserved',
                                'Label availability is not measured accuracy for every object type',
                                'Only main-preview polling cadence changed; other section timers are unchanged'],
        'environment_findings': ['Default sandbox TEMP denied creation of analysis database; full suite passed with a writable local TEMP/TMP',
                                 'Earlier overlapping build/test caused an executable lock; subsequent checks ran only after builds completed',
                                 'Parallel runtime-copy conflict resolved by serialized final build; native source/runtime behaviour unchanged'],
    }
    save('FINAL_RECEIPT.json', receipt)
    overview = f'''# FrameTrail: lean core and a useful local guide

Training remains the primary project priority. KIT is still unavailable per the user, and the newest collection's submission/completion remains unconfirmed. No cluster contact or training was attempted. The conditional training strategy is unchanged at {STRATEGY / 'STRATEGY.md'}; no additional same-data grid was prepared.

The authorized local side task is complete. The stable continuation launcher now opens this package. The previous package and all research evidence remain preserved.

## What changed

- A fifth embedded section, Quick Guide, explains eight tasks in plain language. Ctrl+K or F1 opens it and focuses search. Task actions navigate to existing sections, preserving background work and state.
- Search an object name to inspect installed model category support. A clear action selects the suggested model in Preview. Billboard/washing-machine searches choose Broad recognition; common COCO objects prefer YOLOX-S. Support is explicitly described as label availability, never a detection-accuracy guarantee. Empty searches recover safely. No model inference, network, new library or web component is needed for the guide.
- The four core models retain all 615 canonical labels across their combined profiles. The six labels requiring World-S beyond the YOLOX/Open Images union are wolf, firefly, traffic cone, stroller, forklift and shopping cart. World-S remains explicitly experimental. The larger World-M and two RF previews live in sibling optional/models/; local model paths retain precedence. Missing optional choices are disabled, and normal core startup works without the optional folder. RF remains an explicit held preview.
- Removed the test-only Qt6Test.dll from the distributable. Runtime codec and GPU libraries are retained; their size alone does not make them unnecessary.
- The main Preview timer schedules idle checks every 100ms instead of every 10ms. Opening, active playback, reconfiguration and shutdown retain fast checks. The guide test observed {guide['idle_main_polls_observed_in_1_second']} idle main-timer events over one second. Unchanged activity text is no longer reassigned. This is fewer scheduled main-loop checks, not a measured CPU-percentage or model-inference speed claim. Other section timers are unchanged.

## Measured package size

Previous app folder: {sizes['previous_app_bytes']:,} bytes. New core app folder: {sizes['core_app_bytes']:,} bytes, a {sizes['core_reduction_percent']:.2f}% reduction. Optional models: {sizes['optional_models_bytes']:,} bytes stored separately. Keeping all optional files still uses approximately the old total size; no workspace-wide disk saving is claimed. The core ZIP is {archive.stat().st_size:,} bytes, contains four models and no optional previews, and every member was hash-checked after writing.

## Verification

All 13 selected existing regression checks passed. New guide checks passed at normal and simulated 125% scale, including exact-name ordering, model selection, task navigation, empty search and optional/local model resolution. Extended unified-window tests passed at both scales, including guide navigation during active analysis, state retention, save/CSV/reopen and coordinated Save/Discard/Cancel shutdown. RF cache overlay parity, pause and replay without its test model passed. Three packaged smoke launches passed: normal, balanced optional preview, and core with optional models temporarily absent. Seven model hashes match the previous package; all inference/core sources are unchanged. Verified captures were inspected.

The first analysis check failed because this environment's sandbox TEMP denied database creation. A declared writable local TEMP/TMP resolved it; the strengthened test now reports completed-error states instead of hiding them behind a generic timeout. The early failed logs are retained. A build/test overlap also locked a test executable, and concurrent runtime copies conflicted; the final serialized build and subsequent tests completed successfully. These are recorded build/test environment limitations, not a model-accuracy result.

Live camera hardware, physical-monitor accessibility, model speedups and new detection accuracy are not established. Existing ONNX numerical hold and production_adoption=false remain intact. No optional model downloads occur automatically.

## Use

Run {CONT / 'Run-FrameTrail.cmd'}. Press Ctrl+K, type billboard or export, and use the relevant action. READ-ME.txt explains the portable folder layout. FrameTrail-core.zip is the standalone four-model distribution; the separate optional/models folder enables the preserved experimental alternatives when placed beside app/.

![Object lookup in the embedded guide]({(ROOT / 'evidence/guide-verified/guide-billboard.png').as_posix()})

Next step: when KIT access returns, inspect/retrieve the existing collection and complete source/scene/box review, because trustworthy fresh data remains the prerequisite for the next training comparison.
'''
    (ROOT / 'REPORT.md').write_text(overview, encoding='utf-8')
    handoff = CONT / 'CURRENT_HANDOFF.md'
    prior = ROOT / 'HANDOFF_BEFORE_LEAN_GUIDE.md'
    if not prior.exists():
        prior.write_bytes(handoff.read_bytes())
    header = f'''# Current FrameTrail state — verified lean app, training still data-blocked

19 October 2026. Continue to prioritize the fine-tuning strategy, explained to the user in plain language. New user-facing explanations should be ordinary language; technical reports are supporting artifacts, not the sole explanation.

While KIT remains down, the authorized app side task is complete at:
{ROOT}

Stable normal launcher: {CONT / 'Run-FrameTrail.cmd'}
Stable explicit RF preview launcher: {CONT / 'Run-Balanced-Preview.cmd'}

New functionality: Quick Guide in the same window (Ctrl+K/F1), eight short searchable task guides, object-category lookup that can explicitly select an installed model in Preview, and safe no-result handling. The four core model profiles retain the complete 615-label union; this is label coverage, not accuracy. Main Preview idle timer now checks at 100ms instead of 10ms, with 10ms active polling preserved. Other section timers are unchanged; no model-speed or whole-app CPU/memory claim.

Core app folder is {sizes['core_app_bytes']:,} bytes versus {sizes['previous_app_bytes']:,}, {sizes['core_reduction_percent']:.2f}% smaller. Three larger/experimental models live in sibling optional/models/; all optional bytes are still retained separately, so total storage with all packs/history is not reduced by 47%. Four core models plus the test-DLL removal form the standalone FrameTrail-core.zip. Runtime codecs and GPU support remain present. No original package or scientific evidence was deleted.

All 13 existing selected regressions, guide checks at normal/125%, extended unified workspace checks at normal/125%, RF cache parity/pause/model-free replay, and three packaged smoke cases passed. Captures were inspected. All seven model hashes and inference/core sources are unchanged. App remains YOLOX-S default; RF job7805570 step100 stays explicit experimental preview, ONNX numerical hold, production_adoption=false. Live camera, physical display and screen-reader testing remain unverified. Build first, then run tests: Windows executable locks forbid relinking active test files. Use a writable local TEMP/TMP under this package for sandbox analysis checks; default sandbox TEMP denied database writes. Final build was serialized to avoid competing copies of shared runtime DLLs.

Training strategy remains at {STRATEGY}. Four scientific conditions after data readiness: two cached CPU main-row controls plus two non-cacheable GPU selector trials, paired seeds17/29, max1.5 allocated GPU-hours, 1500 updates/condition, common CPU-reference selection and both-seed gain. Not sealed/runnable until reviewed release, cache/loss/source preflight and authenticated account admission exist. All old both-baseline/unknown-count guards, fresh-test isolation, no retries/replacements and separate ONNX qualification remain mandatory.

KIT remains unavailable per user. Latest data collection submission/completion unconfirmed. No SSH, retrieval, submission, retry or replacement occurred. On return, recover existing state rather than launch a duplicate. No routine permission prompts for authorized local work or bounded continuation; real credentials/consequential blockers only, never pasted credentials. End every response with one concrete project next step and why.

Next step: recover the existing collection when KIT returns and complete frozen source/scene/box review, because reviewed fresh data is still the missing input for useful training.

---

## Preserved training and earlier app handoff

'''
    handoff.write_text(header + prior.read_text(encoding='utf-8-sig'), encoding='utf-8')
    tracked = [p for p in ROOT.rglob('*') if p.is_file() and p.relative_to(ROOT).parts[0] in ('source', 'app', 'optional')]
    save('FILES_SHA256.json', [{'file': str(p.relative_to(ROOT)), 'sha256': sha(p)} for p in sorted(tracked)])
    print(json.dumps({'status': receipt['status'], 'core_bytes': sizes['core_app_bytes'],
                      'core_archive_bytes': archive.stat().st_size, 'core_reduction_percent': sizes['core_reduction_percent'],
                      'launcher': str(CONT / 'Run-FrameTrail.cmd'), 'new_jobs': 0}))


if __name__ == '__main__':
    main()
