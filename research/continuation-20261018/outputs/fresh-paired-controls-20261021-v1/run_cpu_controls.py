"""Two bounded sequential M0 CPU controls; no test inference, cluster jobs, retries or app adoption."""
import os,sys,time,json,hashlib,copy,traceback
from pathlib import Path
C=Path(__file__).resolve().parent;OUT=C.parent
T=OUT/'selector-batch-proposal-7809335-20261018-v1/rf-selector-a77d9663-v1'
F=OUT/'frozen-head-cpu-7809335-20261018-v1'
WHEEL=Path(r'C:\Users\nazee\.codex\visualizations\2026\10\11\01a12a01-d564-7de0-91f4-a16484eea2cb\rf-comparison-package-20261013-v1\local-assignment-wheel\torch_hungarian-0.1.0rc0-py3-none-any.whl')
sys.path[:0]=[str(T),str(F),str(WHEEL)]
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',DO_NOT_TRACK='1')
import torch
from scoped_rf import ScopedRFCriterion,weighted_loss,target_from_row
from cache_engine import replay
from scoped_metrics import decode,score
from selection_policy import evaluate,eligible
from continuation_guard import counts_equal
from determinism_policy import math_attention
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def linked(r):
 assert sha(r['path'])==r['sha256'],r['path']
 return Path(r['path'])
def write(p,v):
 with p.open('x',encoding='utf-8') as f:f.write(json.dumps(v,indent=2,allow_nan=False)+'\n')
def rank(fresh,step,index):
 return (fresh['complete_f1'],fresh['complete_tp'],-fresh['complete_fp'],-step,-index)
@math_attention()
def main():
 torch.set_num_threads(2);torch.manual_seed(17);torch.use_deterministic_algorithms(True)
 plan=read(C/'PLAN.json');plan_sha=sha(C/'PLAN.json')
 preflight=read(C/'PREFLIGHT_REPORT.json');assert preflight['status']=='loss-gradient-full-layout-and-selector-mask-preflight-passed' and preflight['plan_sha256']==plan_sha and preflight['optimizer_updates']==0
 inputs=read(linked(plan['input_ref']));baseline=read(linked(plan['baseline_ref']))
 assert baseline['planned_three_hit_gain_is_mathematically_possible'] and baseline['test_photos_used']==0
 # Load and hash all caches before the active task timers; no model inference.
 records={r['image_id']:r for r in inputs['records']};caches={};targets={}
 for iid,r in records.items():
  value=torch.load(linked(r['cache_ref']),map_location='cpu',weights_only=True)
  caches[iid]=value.get('cache',value)
  assert list(caches[iid]['features'].shape)==[3,1,300,256]
  assert r['row']['split'] in ('train','val')
  if r['row']['split']=='train':targets[iid]=target_from_row(r['row'],615)
 initial=torch.load(linked(inputs['initial_head_ref']),map_location='cpu',weights_only=True)
 original=read(linked(inputs['old_original_baseline_ref']));current=read(linked(inputs['old_current_baseline_ref']))
 old_val=[r['row'] for r in records.values() if r['pool']=='old_validation']
 fresh_val=[r['row'] for r in records.values() if r['pool']=='fresh_validation']
 assert len(old_val)==135 and len(fresh_val)==32 and len(targets)==124
 def validate(w,b):
  old_preds={};fresh_preds={}
  with torch.inference_mode():
   for rows,dst in ((old_val,old_preds),(fresh_val,fresh_preds)):
    for row in rows:
     iid=row['image_id'];dst[iid]=decode(replay(caches[iid],w,b),row['width'],row['height'])
  return evaluate(old_val,old_preds),score(fresh_val,fresh_preds),fresh_preds
 start_old,start_fresh,start_preds=validate(initial['weight'],initial['bias'])
 assert counts_equal(start_old,current),'Cached common CPU scorer no longer reproduces current old baseline'
 assert start_fresh==baseline['metrics'],'Fresh step0 metrics differ'
 assert start_preds==read(OUT/'fresh-data-baseline-20261021-v1/validation-predictions.json')
 assert eligible(start_old,original) and eligible(start_old,current) and start_old['metrics']['unscored_predictions']<=530
 write(C/'STEP_ZERO_REPRODUCTION.json',dict(plan_sha256=plan_sha,old_current_counts_equal=True,fresh_predictions_and_metrics_equal=True,
  old_unknown_count=start_old['metrics']['unscored_predictions'],old_unknown_cap=530,validation_device='pinned-CPU-reference',test_photos_used=0,optimizer_updates=0))
 criterion=ScopedRFCriterion(615);results=[];inactive=[i for i in range(616) if i!=133]
 for index,schedref in enumerate(plan['schedule_refs']):
  seed=schedref['seed'];directory=C/('seed-'+str(seed));directory.mkdir(exist_ok=False)
  schedule=read(linked(schedref));assert len(schedule)==1500
  w=torch.nn.Parameter(initial['weight'].clone());b=torch.nn.Parameter(initial['bias'].clone())
  mask=torch.zeros(616);mask[133]=1
  w.register_hook(lambda grad:grad*mask[:,None]);b.register_hook(lambda grad:grad*mask)
  optimizer=torch.optim.AdamW([w,b],lr=plan['main_lr'],weight_decay=0,foreach=False)
  def invariant():
   assert torch.equal(w.detach()[inactive],initial['weight'][inactive]) and torch.equal(b.detach()[inactive],initial['bias'][inactive])
  def save_head(name,step):
   path=directory/name
   assert not path.exists()
   torch.save(dict(weight=w.detach().clone(),bias=b.detach().clone(),step=step,sampling_seed=seed,method='M0-main-row-only',
    starting_checkpoint_sha256=plan['starting_checkpoint_sha256'],plan_sha256=plan_sha,schedule_sha256=schedref['sha256'],approved_for_application=False),path)
   return sha(path)
  def decision(old,fresh):
   return dict(retention_both_baselines=eligible(old,original) and eligible(old,current),
    original_unknown_cap_passed=old['metrics']['unscored_predictions']<=530,
    gain_hits=fresh['complete_tp']-start_fresh['complete_tp'],extra_fp=fresh['complete_fp']-start_fresh['complete_fp'],
    qualifies=(eligible(old,original) and eligible(old,current) and old['metrics']['unscored_predictions']<=530
      and fresh['complete_tp']>=start_fresh['complete_tp']+3 and fresh['complete_fp']<=start_fresh['complete_fp']))
  def record(step,old,fresh):
   d=decision(old,fresh)
   write(directory/('validation-'+str(step).zfill(4)+'.json'),dict(step=step,seed=seed,method='M0-main-row-only',old=old,fresh=fresh,**d))
   return d
  record(0,start_old,start_fresh);save_head('step-0000.pt',0)
  best=dict(step=0,fresh=start_fresh,qualifies=False);best_sha=sha(directory/'step-0000.pt')
  t0=time.monotonic();step=0;reason='maximum-updates';loss_history=[];partial=False
  print(json.dumps(dict(seed=seed,status='started',max_updates=1500,active_seconds=1800)),flush=True)
  try:
   for next_step,batch in enumerate(schedule,1):
    if time.monotonic()-t0>=1800:partial=True;reason='active-time-budget';break
    assert len(set(batch))==4 and all(i in targets for i in batch)
    optimizer.zero_grad(set_to_none=True);total=0.
    for iid in batch:
     out=replay(caches[iid],w,b);value=weighted_loss(criterion(out,[targets[iid]]))/4
     assert bool(torch.isfinite(value));value.backward();total+=float(value.detach())
    assert w.grad is not None and b.grad is not None
    assert not bool(w.grad[inactive].any()) and not bool(b.grad[inactive].any())
    norm=torch.nn.utils.clip_grad_norm_([w,b],.1,error_if_nonfinite=True)
    optimizer.step();step=next_step;invariant()
    loss_history.append(dict(step=step,loss=total,gradient_norm=float(norm),train_ids=batch))
    if step in plan['validation_steps']:
     if time.monotonic()-t0>=1800:partial=True;reason='active-time-budget-before-validation';break
     old,fresh,_=validate(w,b);invariant();d=record(step,old,fresh)
     if d['qualifies'] and (not best['qualifies'] or rank(fresh,step,index)>rank(best['fresh'],best['step'],index)):
      best=dict(step=step,fresh=fresh,qualifies=True);best_sha=save_head('step-'+str(step).zfill(4)+'.pt',step)
     print(json.dumps(dict(seed=seed,step=step,elapsed_seconds=round(time.monotonic()-t0,1),fresh_tp=fresh['complete_tp'],fresh_fp=fresh['complete_fp'],
      old_unknown=old['metrics']['unscored_predictions'],retention=d['retention_both_baselines'],qualifies=d['qualifies'],best_step=best['step'])),flush=True)
    if time.monotonic()-t0>=1800:partial=step<1500;reason='active-time-budget' if partial else reason;break
   invariant();elapsed=time.monotonic()-t0
   last_sha=save_head('last.pt',step)
   best_file=directory/('step-'+str(best['step']).zfill(4)+'.pt')
   assert sha(best_file)==best_sha
   report=dict(status='partial-time-budget-stop' if partial else 'complete',seed=seed,index=index,method='M0-main-row-only',updates=step,
    best_step=best['step'],new_candidate_selected=best['qualifies'],best_fresh=best['fresh'],best_head_ref=dict(path=str(best_file),sha256=best_sha),
    last_head_sha256=last_sha,reason=reason,elapsed_active_seconds=round(elapsed,2),inactive_classifier_rows_bitwise_unchanged=True,
    all_other_model_weights_and_buffers_unchanged='Full model was not mutated or trained; only standalone copy of main classifier tensor optimized. Compose only with pinned starting checkpoint.',
    selection_device='pinned-CPU-reference',test_photos_used=0,production_adoption=False,plan_sha256=plan_sha,
    execution_order_deviation_ref=plan['execution_order_note_ref'],constant_frozen_encoder_dense_loss_omitted=True)
   write(directory/'TRAINING_STEPS.json',loss_history);write(directory/'REPORT.json',report);results.append(report)
  except Exception as e:
   write(directory/'FAILED.json',dict(status='failed-preserve-evidence-no-retry',seed=seed,step=step,error=str(e),traceback=traceback.format_exc(),production_adoption=False))
   raise
 summary=dict(status='paired-local-controls-completed' if all(r['status']=='complete' for r in results) else 'paired-local-controls-incomplete',
  both_seeds_qualify=all(r['new_candidate_selected'] for r in results),conditions=results,total_updates=sum(r['updates'] for r in results),
  max_total_updates=3000,test_photos_used=0,cluster_jobs_submitted=0,production_adoption=False,plan_sha256=plan_sha,
  execution_order_deviation_ref=plan['execution_order_note_ref'])
 write(C/'PAIRED_CONTROL_REPORT.json',summary);print(json.dumps(summary),flush=True)
if __name__=='__main__':main()

