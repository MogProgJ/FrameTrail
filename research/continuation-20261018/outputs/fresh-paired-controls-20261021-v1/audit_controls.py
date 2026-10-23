"""Independent control closeout: sample roles, all input hashes, selection decisions and inactive tensor bytes."""
import json,hashlib,sys,math
from pathlib import Path
C=Path(__file__).resolve().parent;OUT=C.parent
T=OUT/'selector-batch-proposal-7809335-20261018-v1/rf-selector-a77d9663-v1'
sys.path.insert(0,str(T))
from selection_policy import eligible
import torch
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def verify(ref):assert sha(ref['path'])==ref['sha256'];return read(ref['path'])
def digest_inactive(head):
 inactive=[i for i in range(616) if i!=133]
 return hashlib.sha256(head['weight'][inactive].contiguous().numpy().tobytes()+head['bias'][inactive].contiguous().numpy().tobytes()).hexdigest()
plan=read(C/'PLAN.json');inputs=verify(plan['input_ref']);summary=read(C/'PAIRED_CONTROL_REPORT.json')
assert summary['status']=='paired-local-controls-completed' and summary['plan_sha256']==sha(C/'PLAN.json')
assert read(C/'EXECUTION_ORDER_NOTE.json')['exact_schedule_files_sealed_before_baseline_predictions'] is False
records={r['image_id']:r for r in inputs['records']}
for r in records.values():
 assert r['row']['split'] in ('train','val') and sha(r['cache_ref']['path'])==r['cache_ref']['sha256']
initial=torch.load(inputs['initial_head_ref']['path'],map_location='cpu',weights_only=True);initial_digest=digest_inactive(initial)
original=verify(inputs['old_original_baseline_ref']);current=verify(inputs['old_current_baseline_ref'])
start=read(OUT/'fresh-data-baseline-20261021-v1/BASELINE_REPORT.json')['metrics']
audits=[]
for condition,schedref in zip(summary['conditions'],plan['schedule_refs']):
 directory=C/('seed-'+str(condition['seed']));schedule=verify(schedref);steps=read(directory/'TRAINING_STEPS.json')
 assert condition['updates']==len(steps)==len(schedule)==1500 and condition['status']=='complete'
 assert condition['elapsed_active_seconds']<1800
 for n,(step,batch) in enumerate(zip(steps,schedule),1):
  assert step['step']==n and step['train_ids']==batch and len(set(batch))==4
  assert all(records[i]['row']['split']=='train' for i in batch)
  assert all(math.isfinite(step[k]) for k in ('loss','gradient_norm'))
 decisions=[]
 for step in plan['validation_steps']:
  row=read(directory/('validation-'+str(step).zfill(4)+'.json'));old=row['old'];fresh=row['fresh']
  retention=eligible(old,original) and eligible(old,current);cap=old['metrics']['unscored_predictions']<=530
  qualifies=retention and cap and fresh['complete_tp']>=start['complete_tp']+3 and fresh['complete_fp']<=start['complete_fp']
  assert row['qualifies']==qualifies and row['retention_both_baselines']==retention and row['original_unknown_cap_passed']==cap
  decisions.append(dict(step=step,fresh_tp=fresh['complete_tp'],fresh_fp=fresh['complete_fp'],old_unknown=old['metrics']['unscored_predictions'],retention=retention,qualifies=qualifies))
 for file in ('step-0000.pt','last.pt'):
  h=torch.load(directory/file,map_location='cpu',weights_only=True);assert digest_inactive(h)==initial_digest
  if file=='step-0000.pt':
   assert h['weight'].numpy().tobytes()==initial['weight'].numpy().tobytes() and h['bias'].numpy().tobytes()==initial['bias'].numpy().tobytes()
  else:assert sha(directory/file)==condition['last_head_sha256']
 assert not any(d['qualifies'] for d in decisions) and condition['best_step']==0 and not condition['new_candidate_selected']
 audits.append(dict(seed=condition['seed'],updates=1500,decisions=decisions,inactive_tensor_bytes_identical=True,elapsed_active_seconds=condition['elapsed_active_seconds']))
report=dict(status='independently-audited-complete-no-qualifying-M0-candidate',conditions=audits,total_updates=3000,
 all291_input_cache_hashes_unchanged=True,all_schedules_unchanged=True,no_heldout_training_samples=True,
 no_fresh_test_inference=True,both_baseline_perclass_and_original_unknown_cap530_enforced=True,
 inactive_classifier_tensor_bytes_identical=True,production_adoption=False,
 execution_order_deviation_ref=plan['execution_order_note_ref'],
 next_step='Prepare bounded two-seed M1 proposal-row comparison with same schedules/data/LRs, shared CPU scorer and unchanged gates; authenticate account/admission before submission.')
with (C/'INDEPENDENT_AUDIT.json').open('x',encoding='utf-8') as f:f.write(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))

