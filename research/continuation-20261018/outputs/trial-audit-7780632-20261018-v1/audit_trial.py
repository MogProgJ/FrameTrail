"""Read-only audit of existing trial artifacts; no inference, training or export."""
import collections, hashlib, json, math, random, statistics, sys
from pathlib import Path
import torch

OLD = Path(r'C:\Users\nazee\.codex\visualizations\2026\10\15\01a141ae-c7a6-7303-a280-403af88736f3')
TOOLS = OLD/'nextdata-rf-trial-7769109-v1/rf-nextdata-tools-v1'
BASE = Path(r'C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\outputs\trial-results-7780632-20261018-v1')
RUN = BASE/'retrieval/verified-7780632/output/rf-nextdata-7780632'
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
from selection_policy import evaluate, eligible, ranking, improves

def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    with p.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
def save(name, data):
    (OUT/name).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def stream(ids,n,seed):
    rng=random.Random(seed); result=[]
    while len(result)<n:
        cycle=list(ids); rng.shuffle(cycle); result.extend(cycle)
    return result[:n]

torch.set_num_threads(2)
manifest_path=OLD/'nextdata-reviewed-release-7769109-v1/candidate-manifest-v2.json'
manifest=read(manifest_path); protocol=read(TOOLS/'protocol.json'); approval=read(TOOLS/'approval.json')
preflight=read(RUN/'preflight.json'); report=read(RUN/'experiment-report.json')
assert sha(manifest_path)==preflight['candidate_sha256']==protocol['candidate_sha256']
assert sha(TOOLS/'protocol.json')==preflight['protocol_sha256']==approval['protocol_sha256']
assert sha(TOOLS/'approval.json')==preflight['approval_sha256'] and approval['approved']
archive=BASE/'retrieval/frametrail-rf-nextdata-results-7780632.tar.gz'
assert sha(archive)=='ae4fcd247566cc0a9c2abe81f8e25a61626e1987d1f950d8af5ddecc2db8a3ff'
rows=[r for r in manifest['images'] if r['split']=='val']; assert len(rows)==135
train={r['image_id'] for r in manifest['images'] if r['split']=='train'}
test={r['image_id'] for r in manifest['images'] if r['split']=='test'}
pools=read(TOOLS/'sampling-pools.json'); positive=stream(pools['positive'],1200,171017); negative=stream(pools['negative'],1200,171018)
expected=[[positive[2*i],positive[2*i+1],negative[2*i],negative[2*i+1]] for i in range(600)]
assert read(RUN/'sampling-plan.json')==expected
steps=[read(RUN/f'step-{i:04}.json') for i in range(1,601)]
assert [s['step'] for s in steps]==list(range(1,601))
assert [s['train_ids'] for s in steps]==expected
assert set(x for batch in expected for x in batch)<=train
assert all(math.isfinite(s[k]) for s in steps for k in ('loss','gradient_norm'))

validations=[]; best=None; best_step=None
for step in range(0,601,100):
    current=read(RUN/f'validation-{step:04}.json')
    rescored=evaluate(rows,current['predictions'])
    assert rescored['metrics']==current['metrics'] and rescored['per_class']==current['per_class']
    if step==0: baseline=current; best=current; best_step=0
    ok=eligible(current,baseline); assert ok==current['eligible']
    if improves(current,best,baseline): best=current; best_step=step
    validations.append(dict(step=step,eligible=ok,ranking=list(ranking(current)),
        metrics={k:v for k,v in current['metrics'].items() if k not in ('per_image','limits')},
        active_classes={str(c):{k:v for k,v in current['per_class'][str(c)].items() if k not in ('per_image','limits')} for c in protocol['active_classifier_rows']}))
assert best_step==report['best_step']==0 and report['new_candidate_selected'] is False
assert sha(RUN/'best.pt')==sha(RUN/'checkpoints/step-0000.pt')==report['best_checkpoint_sha256']
assert sha(RUN/'last.pt')==report['last_checkpoint_sha256']
initial=torch.load(RUN/'best.pt',map_location='cpu',weights_only=True)
last=torch.load(RUN/'last.pt',map_location='cpu',weights_only=True)
assert initial['step']==0 and last['step']==600
a,b=initial['model_state_dict'],last['model_state_dict']; assert set(a)==set(b)
changed=[k for k in a if not torch.equal(a[k],b[k])]
assert set(changed)=={'class_embed.weight','class_embed.bias'}
active=protocol['active_classifier_rows']; inactive=[i for i in range(616) if i not in active]
assert all(torch.equal(a[k][inactive],b[k][inactive]) for k in changed)
names=read(TOOLS/'rf-mapping.json')['canonical_class_names']
def name(cid): return names[str(cid)] if isinstance(names,dict) else names[cid]
deltas={str(cid):dict(name=name(cid),weight_l2=float((b['class_embed.weight'][cid]-a['class_embed.weight'][cid]).norm()),
    max_abs_weight_change=float((b['class_embed.weight'][cid]-a['class_embed.weight'][cid]).abs().max()),
    bias_before=float(a['class_embed.bias'][cid]),bias_after=float(b['class_embed.bias'][cid])) for cid in active}
final=read(RUN/'validation-0600.json'); diagnostics=[]
for row in rows:
    truth=[t for t in row['targets'] if t['canonical_id'] in active]
    if not truth: continue
    diagnostics.append(dict(image_id=row['image_id'],photo_number=row.get('photo_number'),source_path=row['source_path'],
        scope={str(c):row['scope'].get(str(c),'unknown') for c in active},targets=truth,
        baseline_predictions=[p for p in baseline['predictions'][row['image_id']] if p['canonical_id'] in active],
        last_predictions=[p for p in final['predictions'][row['image_id']] if p['canonical_id'] in active]))
active_summary={str(c):dict(name=name(c),**validations[0]['active_classes'][str(c)],
    baseline_emitted_predictions=sum(p['canonical_id']==c for ps in baseline['predictions'].values() for p in ps),
    last_emitted_predictions=sum(p['canonical_id']==c for ps in final['predictions'].values() for p in ps)) for c in active}
audit=dict(status='audited-no-improving-checkpoint-selected',actual_job_id='7780632',
    archive_sha256=sha(archive),selected_step=0,selected_is_byte_identical_to_step_zero=True,
    trained_state_changed_keys=changed,head_deltas=deltas,validation=validations,active_class_summary=active_summary,
    sampling=dict(updates=600,presentations=2400,unique_training_photos=len(set(x for batch in expected for x in batch)),
        training_pool_photos=len(train),positive_pool=len(pools['positive']),negative_pool=len(pools['negative']),
        deterministic_schedule_reproduced=True,step_receipts_match_schedule=True,validation_or_test_ids_sampled=False),
    loss_blocks=[dict(first_step=i+1,last_step=i+100,mean_loss=statistics.mean(s['loss'] for s in steps[i:i+100])) for i in range(0,600,100)],
    gradient_norm_min=min(s['gradient_norm'] for s in steps),gradient_norm_max=max(s['gradient_norm'] for s in steps),
    validation_metrics_and_per_class_recomputed=True,selection_recomputed=True,
    frozen_features_boxes_and_inactive_rows_verified_by_cpu_tensor_comparison=True,
    heldout=dict(photo_count=len(test),reserved_video_frames=24,reserved_sequences=6,
        evaluated_in_this_audit=False,status='deferred-no-improved-candidate; not a passed evaluation gate'),
    approved_for_application=False,model_exported=False,new_training_submitted=False,
    limits=['135 development photos; fixed confidence .35, NMS .45 and IoU .5.',
        'Complete/absent classes support FP counts; partial targets support known-positive recall only; unknown predictions are not false positives.',
        'Assistant-reviewed scoped annotations, no independent human recheck, not full-vocabulary mAP.',
        'Emitted predictions cannot reveal sub-threshold logits or unseen query localization; causal diagnosis needs a separate validation-only instrumented probe.'])
save('AUDIT.json',audit); save('validation-diagnostic-worklist.json',diagnostics)
inputs=[archive,manifest_path,*sorted(p for p in RUN.rglob('*') if p.is_file()),TOOLS/'approval.json',TOOLS/'protocol.json',TOOLS/'sampling-pools.json',TOOLS/'selection_policy.py',TOOLS/'scoped_metrics.py',TOOLS/'head_policy.py',TOOLS/'scoped_engine.py',TOOLS/'scoped_rf.py',TOOLS/'train_nextdata.py']
save('INPUT_INTEGRITY.json',dict(files=[dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size) for p in inputs]))
print(json.dumps({k:audit[k] for k in ('status','selected_step','trained_state_changed_keys','head_deltas','active_class_summary','sampling','loss_blocks')},indent=2))
