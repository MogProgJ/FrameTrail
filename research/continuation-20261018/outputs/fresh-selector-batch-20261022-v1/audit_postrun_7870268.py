"""Independent read-only audit of completed records. No torch, inference or selection edits."""
import json, hashlib, statistics
from pathlib import Path

ROOT = Path(r'C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation')
OUT = ROOT / 'outputs'
BATCH = OUT / 'fresh-selector-batch-20261022-v1'
EVAL = BATCH / 'retrieval/local-evaluation'
CONTROLS = OUT / 'fresh-paired-controls-20261021-v1'
REFERENCE = OUT / 'selector-batch-proposal-7809335-20261018-v1/rf-selector-a77d9663-v1'
STEPS = [0, 100, 250, 500, 1000, 1500]

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def failures(candidate, baseline):
    assert set(candidate['per_class']) == set(baseline['per_class'])
    result = []
    for cid, old in baseline['per_class'].items():
        now = candidate['per_class'][cid]
        for key, sign in [('complete_tp', -1), ('complete_fp', 1), ('partial_hits', -1)]:
            if sign * (now[key] - old[key]) > 0:
                result.append(dict(class_id=cid, metric=key, baseline=old[key], candidate=now[key]))
    if candidate['metrics']['unscored_predictions'] > baseline['metrics']['unscored_predictions'] + 5:
        result.append(dict(metric='unscored_predictions', baseline=baseline['metrics']['unscored_predictions'], candidate=candidate['metrics']['unscored_predictions']))
    return result

def check_metrics(value):
    for key in ['complete_tp', 'complete_fp', 'complete_fn', 'partial_hits', 'partial_misses', 'unscored_predictions']:
        assert value[key] == sum(row[key] for row in value['per_image']), key
    tp, fp, fn = [value[k] for k in ['complete_tp', 'complete_fp', 'complete_fn']]
    f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0
    assert abs(value['complete_f1'] - f1) < 1e-12

def main():
    final, selection = read(EVAL / 'FINAL_REPORT.json'), read(EVAL / 'GLOBAL_SELECTION.json')
    original, current = [read(REFERENCE / f'inputs/validation-{name}.json') for name in ['original', 'resume']]
    fresh_base = read(OUT / 'fresh-data-baseline-20261021-v1/BASELINE_REPORT.json')['metrics']
    rows, refs, log_summary = [], [], []
    for method in ['M0', 'M1']:
        for index, seed in enumerate([17, 29]):
            for step in STEPS:
                path = (CONTROLS / f'seed-{seed}/validation-{step:04}.json' if method == 'M0'
                        else EVAL / f'M1-{seed}-validation-{step:04}.json')
                value = read(path)
                old, fresh = value['old'], value['fresh']
                check_metrics(fresh)
                check_metrics(old['metrics'])
                for metrics in old['per_class'].values():
                    check_metrics(metrics)
                fail_original, fail_current = failures(old, original), failures(old, current)
                cap = old['metrics']['unscored_predictions'] <= 530
                gain = fresh['complete_tp'] - fresh_base['complete_tp']
                extra_fp = fresh['complete_fp'] - fresh_base['complete_fp']
                qualifies = not fail_original and not fail_current and cap and gain >= 3 and extra_fp <= 0
                assert value['retention_both_baselines'] == (not fail_original and not fail_current)
                assert value['original_unknown_cap_passed'] == cap
                assert value['gain_hits'] == gain and value['extra_fp'] == extra_fp
                assert value['qualifies'] == qualifies
                rows.append(dict(method=method, seed=seed, step=step, tp=fresh['complete_tp'], fp=fresh['complete_fp'], fn=fresh['complete_fn'],
                    unknown_old=old['metrics']['unscored_predictions'], qualifies=qualifies,
                    original_failures=fail_original, current_failures=fail_current,
                    false_alarm_image_ids=[r['image_id'] for r in fresh['per_image'] if r['complete_fp'] > 0]))
                refs.append(dict(path=str(path), sha256=digest(path)))
            if method == 'M0':
                logs = read(CONTROLS / f'seed-{seed}/TRAINING_STEPS.json')
            else:
                logs = [json.loads(line) for line in (BATCH / f'retrieval/verified-7870268_{index}/TRAINING_STEPS.jsonl').read_text().splitlines()]
            schedule = read(CONTROLS / f'schedule-{seed}.json')
            assert len(logs) == len(schedule) == 1500
            assert all(r['step'] == i + 1 and r['train_ids'] == schedule[i] for i, r in enumerate(logs))
            summary = dict(method=method, seed=seed, updates=len(logs))
            for start, end, label in [(0, 100, 'first_100'), (1400, 1500, 'last_100')]:
                part = logs[start:end]
                summary[label] = dict(mean_logged_loss=statistics.mean(r['loss'] for r in part),
                                     mean_gradient_norm=statistics.mean(r['gradient_norm'] for r in part))
                if method == 'M1':
                    summary[label]['mean_dense_loss'] = statistics.mean(r['dense_loss'] for r in part)
                    summary[label]['mean_main_loss'] = statistics.mean(r['loss'] - r['dense_loss'] for r in part)
            log_summary.append(summary)
    methods = {m: all(any(r['qualifies'] for r in rows if r['method'] == m and r['seed'] == seed) for seed in [17,29]) for m in ['M0','M1']}
    condition_map = {(c['method'], c['seed']): c for c in selection['conditions']}
    assert set(condition_map) == {(m,s) for m in ['M0','M1'] for s in [17,29]}
    assert all(c['complete'] for c in condition_map.values())
    assert all(0 < c['combined_training_validation_seconds'] < 1800 for c in condition_map.values() if c['method'] == 'M1')
    eligible = [r for r in rows if methods[r['method']] and r['qualifies']]
    if not eligible:
        assert selection['winner'] is None
        assert final['status'] == 'no-qualifying-method-keep-starting-model'
        assert final['test_photos_used'] == 0
        assert not (EVAL / 'WINNER_LOCK.json').exists()
        assert not (EVAL / 'FRESH_TEST_CONSUMPTION_LOCK.json').exists()
    assert final['production_adoption'] is False
    report = dict(status='independent-record-audit-passed', job='7870268', records_audited=len(rows),
                  method_eligible=methods, validation_rows=rows, training_log_summary=log_summary,
                  conditions=selection['conditions'], final_report=final, references=refs,
                  limitations=['No new predictions, parameter changes or fits.', 'TRAIN logs are descriptive optimization evidence, not held-out accuracy.',
                               'Unscored predictions are not automatically false positives.'], test_photos_used_by_audit=0)
    destination = BATCH / 'postrun-audit-7870268-v1'
    destination.mkdir(exist_ok=False)
    (destination / 'INDEPENDENT_AUDIT.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['status', 'records_audited', 'method_eligible', 'training_log_summary', 'final_report']}, indent=2))
    print('VALIDATION_TABLE')
    for r in rows:
        print(json.dumps(r))

if __name__ == '__main__':
    main()
