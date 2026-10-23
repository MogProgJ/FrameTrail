"""Read-only recomputation of completed trial receipts; no inference or training."""
import hashlib, json, math, sys
from pathlib import Path
import torch

HERE = Path(__file__).resolve().parent
TOOLS = Path(r'C:\Users\nazee\.codex\visualizations\2026\10\17\01a14c2d-b771-7a40-ba9b-e8277e4905a1\work\rf-balanced-continuation-20261018-v1\rf-balanced-ddbb57c6-v1')
RUN = HERE / 'verified-7805570/output/rf-balanced-7805570'
sys.path.insert(0, str(TOOLS))
from continuation_guard import inputs, approval, counts_equal
from selection_policy import evaluate, eligible, ranking

def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    with p.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()
def save(name, data):
    with (HERE/name).open('x', encoding='utf-8') as f: json.dump(data, f, indent=2, allow_nan=False)

torch.set_num_threads(2)
release, schedule, original, resume = inputs(TOOLS)
a, protocol = approval(TOOLS)
pre = read(RUN/'preflight.json'); report = read(RUN/'experiment-report.json')
assert pre['approval_sha256'] == sha(TOOLS/'approval.json')
assert pre['candidate_sha256'] == sha(TOOLS/'release/candidate-manifest-v2.json')
assert read(RUN/'sampling-plan.json') == schedule
rows = [r for r in release['images'] if r['split']=='val']
train = {r['image_id'] for r in release['images'] if r['split']=='train'}
assert len(rows)==135 and len(train)==700
steps = [read(RUN/f'step-{i:04}.json') for i in range(1,2001)]
assert [s['train_ids'] for s in steps] == schedule
assert set(x for batch in schedule for x in batch) <= train
assert all(math.isfinite(s[k]) for s in steps for k in ('loss','gradient_norm'))
validations = []; best_step=0; best=None
names = read(TOOLS/'rf-mapping.json')['canonical_class_names']
def name(cid): return names[str(cid)] if isinstance(names,dict) else names[cid]
for step in range(0,2001,100):
    current = read(RUN/f'validation-{step:04}.json')
    rescored = evaluate(rows, current['predictions'])
    assert current['metrics']==rescored['metrics'] and current['per_class']==rescored['per_class']
    if step==0:
        baseline=current; best=current
        assert counts_equal(baseline,original) and counts_equal(baseline,resume)
    ok = eligible(current, baseline) and eligible(current, original)
    assert current['eligible']==ok
    if ok and ranking(current)>ranking(best) and ranking(current)>ranking(original):
        best=current; best_step=step
    reasons=[]
    for cid, b in baseline['per_class'].items():
        c=current['per_class'][cid]
        if c['complete_tp']<b['complete_tp']: reasons.append(f'{name(int(cid))}: fewer complete true positives')
        if c['complete_fp']>b['complete_fp']: reasons.append(f'{name(int(cid))}: more scored false positives')
        if c['partial_hits']<b['partial_hits']: reasons.append(f'{name(int(cid))}: fewer partial known-positive hits')
    if current['metrics']['unscored_predictions']>baseline['metrics']['unscored_predictions']+5:
        reasons.append('aggregate unscored predictions exceed allowed +5 drift')
    validations.append(dict(step=step,eligible=ok,rejection_reasons=reasons,
        metrics={k:v for k,v in current['metrics'].items() if k not in ('per_image','limits')}))
assert best_step==report['best_step']==100
assert sha(RUN/'best.pt')==sha(RUN/'checkpoints/step-0100.pt')==report['best_checkpoint_sha256']
assert sha(RUN/'last.pt')==report['last_checkpoint_sha256']
initial=torch.load(TOOLS/'inputs/last-7780632.pt',map_location='cpu',weights_only=True)
state=initial['model_state_dict']; active=[133,593]; inactive=[i for i in range(616) if i not in active]
tensor_checks=[]
for filename,step in [('checkpoints/step-0000.pt',0),('best.pt',100),('last.pt',2000)]:
    ck=torch.load(RUN/filename,map_location='cpu',weights_only=True)
    assert ck['step']==step and ck['approved_for_application'] is False
    assert ck['frametrail']==pre
    other=ck['model_state_dict']; assert set(state)==set(other)
    changed=[k for k in state if not torch.equal(state[k],other[k])]
    assert not (set(changed)-{'class_embed.weight','class_embed.bias'})
    for k in ['class_embed.weight','class_embed.bias']:
        assert torch.equal(state[k][inactive],other[k][inactive])
    if step==0: assert not changed
    tensor_checks.append(dict(file=filename,step=step,changed_keys=changed,
        frozen_features_boxes_encoder_and_inactive_rows_identical=True))
    del ck,other
classes=[]
for cid in [15,16,133,593]:
    before=baseline['per_class'][str(cid)];after=best['per_class'][str(cid)]
    classes.append(dict(canonical_id=cid,name=name(cid),
        before_known_hits=before['complete_tp']+before['partial_hits'],
        selected_known_hits=after['complete_tp']+after['partial_hits'],
        known_targets=before['complete_tp']+before['complete_fn']+before['partial_hits']+before['partial_misses'],
        before_complete_fp=before['complete_fp'],selected_complete_fp=after['complete_fp']))
audit=dict(status='audited-improving-candidate-awaiting-heldout-evaluation',actual_job_id='7805570',
    archive_sha256=read(HERE/'verification-receipt.json')['archive_sha256'],
    selected_step=best_step,selected_checkpoint_sha256=sha(RUN/'best.pt'),
    schedule=dict(updates=2000,image_presentations=8000,exact_approved_order=True,
        unique_training_photos=len(set(x for batch in schedule for x in batch)),
        validation_or_test_ids_sampled=False,all_step_receipts_match=True),
    all_21_validation_records_rescored=True,reviewed_class_count=len(baseline['per_class']),
    selection_recomputed=True,tensor_checks=tensor_checks,classes=classes,validation=validations,
    heldout_evaluated=False,model_exported=False,approved_for_application=False,
    limits=['Validation results on 135 development photos; not held-out performance.',
        'Partial scope supports known-positive recall, not complete false-positive measurement.',
        'Unknown predictions are unscored, not false positives.',
        'Assistant-reviewed annotations; no independent human recheck.'])
save('AUDIT.json',audit)
print(json.dumps({k:audit[k] for k in ['status','selected_step','classes','tensor_checks','schedule']},indent=2))
