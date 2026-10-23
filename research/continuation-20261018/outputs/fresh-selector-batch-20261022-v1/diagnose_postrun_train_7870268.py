"""Fixed final-state TRAIN diagnosis only. Never fits, selects, scores VAL/TEST or exports."""
import os, sys, json, copy, time, hashlib
from pathlib import Path
ROOT = Path(r'C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation')
OUT = ROOT / 'outputs'
BATCH = OUT / 'fresh-selector-batch-20261022-v1'
T = OUT / 'selector-batch-proposal-7809335-20261018-v1/rf-selector-a77d9663-v1'
C = OUT / 'fresh-paired-controls-20261021-v1'
F = OUT / 'frozen-head-cpu-7809335-20261018-v1'
WHEEL = Path(r'C:\Users\nazee\.codex\visualizations\2026\10\11\01a12a01-d564-7de0-91f4-a16484eea2cb\rf-comparison-package-20261013-v1\local-assignment-wheel\torch_hungarian-0.1.0rc0-py3-none-any.whl')
sys.path[:0] = [str(BATCH / 'rf-fresh-selector-v1'), str(T), str(F), str(WHEEL)]
os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1', DO_NOT_TRACK='1')
import torch
from scipy.optimize import linear_sum_assignment
from rfdetr.utilities import box_ops
from batch_guard import read, sha, write, apply_patch_rows, frozen_digest, CHECKPOINT
from scoped_engine import build_model, load_sample
from cache_engine import replay
from scoped_metrics import decode, score, iou
from determinism_policy import math_attention

@math_attention()
def main():
    torch.set_num_threads(2)
    torch.manual_seed(17)
    torch.use_deterministic_algorithms(True)
    evaluation = BATCH / 'retrieval/local-evaluation'
    final = read(evaluation / 'FINAL_REPORT.json')
    assert final['status'] == 'no-qualifying-method-keep-starting-model'
    assert final['test_photos_used'] == 0 and not (evaluation / 'WINNER_LOCK.json').exists()
    destination = BATCH / 'postrun-train-diagnosis-7870268-v1'
    destination.mkdir(exist_ok=False)
    source = read(C / 'INPUTS.json')
    records = [r for r in source['records'] if r['pool'] in ['fresh_positive', 'old_positive', 'fresh_absent', 'old_absent']]
    assert len(records) == 124 and all(r['row']['split'] == 'train' and r['row']['supervision'] == 'gold' for r in records)
    assert {r['pool'] for r in records} == {'fresh_positive', 'old_positive', 'fresh_absent', 'old_absent'}
    plan = dict(status='fixed-before-postrun-TRAIN-inference', job='7870268',
                states=['starting-model-cached', 'M0-seed17-step1500-cached', 'M0-seed29-step1500-cached', 'M1-seed17-step1500-fullforward', 'M1-seed29-step1500-fullforward'],
                photos=124, positive_photos=47, absent_photos=77, target_class=133,
                optimizer_updates=0, validation_photos_probed=0, test_photos_used=0,
                max_active_seconds_per_fullforward_state=900, threads=2, selection_allowed=False,
                checkpoint_sha256=CHECKPOINT, inputs_sha256=sha(C / 'INPUTS.json'),
                diagnostic_script_sha256=sha(Path(__file__)),
                purpose='Distinguish fixed final TRAIN recognition/geometry behavior from generalization; no sweep or selection.',
                scoring_adapter='Deep copies of TRAIN rows use split=val only for unchanged score primitive; source rows and release untouched.')
    write(destination / 'PLAN.json', plan)
    caches = {}
    for r in records:
        photo = Path(r['base']) / r['row']['source_path']
        assert sha(photo) == r['row']['image_sha256']
        ref = r['cache_ref']
        assert sha(ref['path']) == ref['sha256']
        value = torch.load(ref['path'], map_location='cpu', weights_only=True)
        caches[r['image_id']] = value.get('cache', value)
    initial_ref = source['initial_head_ref']
    assert sha(initial_ref['path']) == initial_ref['sha256']
    initial = torch.load(initial_ref['path'], map_location='cpu', weights_only=True)

    def measure(name, outputs_for):
        predictions, geometry, errors = {}, [], []
        started = time.monotonic()
        with torch.inference_mode():
            for r in records:
                assert time.monotonic() - started < 900, 'Preserve incomplete diagnostic; no retry'
                row = r['row']
                output = outputs_for(r)
                predictions[r['image_id']] = [p for p in decode(output, row['width'], row['height']) if p['canonical_id'] == 133]
                wanted = [t['normalized_cxcywh'] for t in row['targets'] if t['canonical_id'] == 133]
                target_boxes = [[(cx-bw/2)*row['width'], (cy-bh/2)*row['height'], (cx+bw/2)*row['width'], (cy+bh/2)*row['height']] for cx,cy,bw,bh in wanted]
                matched = set()
                for prediction in sorted(predictions[r['image_id']], key=lambda p:-p['confidence']):
                    overlaps_list = [iou(prediction['box'], b) for b in target_boxes]
                    available = [(v,i) for i,v in enumerate(overlaps_list) if i not in matched]
                    overlap, target_index = max(available, default=(0,-1))
                    if overlap >= .5:
                        matched.add(target_index)
                    elif row['scope'].get('133') in ['complete', 'absent']:
                        max_overlap = max(overlaps_list, default=0)
                        category = 'reviewed-absent-photo' if not wanted else ('duplicate-over-target' if max_overlap >= .5 else ('near-target-IoU-below-0.5' if max_overlap > 0 else 'away-from-target'))
                        errors.append(dict(image_id=r['image_id'], pool=r['pool'], category=category, max_target_iou=max_overlap, prediction=prediction))
                if wanted:
                    overlaps = box_ops.box_iou(box_ops.box_cxcywh_to_xyxy(output['pred_boxes'][0]), box_ops.box_cxcywh_to_xyxy(torch.tensor(wanted)))[0].numpy()
                    q, t = linear_sum_assignment(-(overlaps >= .5).astype(float) - overlaps * 1e-5)
                    geometry.append(dict(image_id=r['image_id'], pool=r['pool'], targets=len(wanted), geometry_covered=int((overlaps[q,t] >= .5).sum())))
        adapted = []
        for r in records:
            row = copy.deepcopy(r['row'])
            row['split'] = 'val'
            row['targets'] = [t for t in row['targets'] if t['canonical_id'] == 133]
            row['scope'] = {k:v for k,v in row['scope'].items() if int(k) == 133}
            adapted.append(row)
        all_metrics = score(adapted, predictions)
        assert len(errors) == all_metrics['complete_fp']
        pools = {}
        for pool in sorted({r['pool'] for r in records}):
            ids = {r['image_id'] for r in records if r['pool'] == pool}
            pools[pool] = score([r for r in adapted if r['image_id'] in ids], {i:p for i,p in predictions.items() if i in ids})
        value = dict(state=name, source_role='train', selection_allowed=False, metrics=all_metrics, pools=pools,
                     geometry=geometry, predictions=predictions, false_alarm_details=errors, elapsed_seconds=time.monotonic()-started,
                     validation_photos_probed=0, test_photos_used=0, optimizer_updates=0)
        write(destination / f'{name}.json', value)
        brief = dict(state=name, tp=all_metrics['complete_tp'], fp=all_metrics['complete_fp'], fn=all_metrics['complete_fn'],
                     geometry_covered=sum(g['geometry_covered'] for g in geometry), targets=sum(g['targets'] for g in geometry),
                     false_alarm_categories={category:sum(e['category']==category for e in errors) for category in sorted({e['category'] for e in errors})},
                     pools={k:{metric:v[metric] for metric in ['complete_tp','complete_fp','complete_fn']} for k,v in pools.items()})
        print(json.dumps(brief), flush=True)
        return brief

    summaries = [measure('starting-model', lambda r: replay(caches[r['image_id']], initial['weight'], initial['bias']))]
    inactive = [i for i in range(616) if i != 133]
    for seed in [17,29]:
        head_path = C / f'seed-{seed}/last.pt'
        head = torch.load(head_path, map_location='cpu', weights_only=True)
        receipt = read(C / f'seed-{seed}/REPORT.json')
        assert sha(head_path) == receipt['last_head_sha256'] and head['step'] == 1500
        assert torch.equal(head['weight'][inactive], initial['weight'][inactive]) and torch.equal(head['bias'][inactive], initial['bias'][inactive])
        summaries.append(measure(f'M0-{seed}-1500', lambda r: replay(caches[r['image_id']], head['weight'], head['bias'])))
    weights = Path(r'C:\Users\nazee\Documents\All Modules\FrameTrail\.deps\rfdetr-probe-assets\rf-detr-small.pth')
    checkpoint = T / 'inputs/selected-7805570.pt'
    assert sha(checkpoint) == CHECKPOINT
    model = build_model(weights, BATCH / 'rf-fresh-selector-v1/rf-mapping.json').cpu().eval()
    state = torch.load(checkpoint, map_location='cpu', weights_only=True)
    model.load_state_dict(state['model_state_dict'], strict=True)
    del state
    for p in model.parameters(): p.requires_grad_(False)
    frozen = frozen_digest(model.state_dict())
    for index, seed in enumerate([17,29]):
        folder = BATCH / f'retrieval/verified-7870268_{index}'
        receipt = read(folder / 'REPORT.json')
        path = folder / 'patch-1500.pt'
        assert sha(path) == next(p['sha256'] for p in receipt['patches'] if p['step'] == 1500)
        assert frozen == receipt['frozen_digest']
        apply_patch_rows(model, torch.load(path, map_location='cpu', weights_only=True))
        assert frozen_digest(model.state_dict()) == frozen
        def predict(r):
            assert r['row']['split'] == 'train'
            image, _ = load_sample(Path(r['base']), r['row'], 'cpu')
            return model(image)
        summaries.append(measure(f'M1-{seed}-1500', predict))
        assert frozen_digest(model.state_dict()) == frozen
    assert sha(checkpoint) == CHECKPOINT and sha(C / 'INPUTS.json') == plan['inputs_sha256']
    assert not (evaluation / 'WINNER_LOCK.json').exists() and not (evaluation / 'FRESH_TEST_CONSUMPTION_LOCK.json').exists()
    write(destination / 'REPORT.json', dict(status='fixed-final-state-TRAIN-diagnosis-completed', summaries=summaries,
          validation_photos_probed=0, test_photos_used=0, optimizer_updates=0, production_adoption=False,
          frozen_state_unchanged=True, source_roles_unchanged=True, selection_allowed=False))

if __name__ == '__main__': main()
