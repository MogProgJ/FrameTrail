"""One newly approved selector task; two billboard rows, no automatic retries."""
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
import json,time,shutil
from pathlib import Path
import torch
from continuation_guard import approval,inputs,activate,counts_equal,stop_without_gain,read,sha,variant,HEADS
from verify_package import verify
from preflight import preflight
from scoped_engine import build_model,load_sample,validate_release
from scoped_rf import weighted_loss
from scoped_metrics import decode
from selection_policy import evaluate,eligible,ranking
from selector_mechanics import configure,fingerprint_frozen,RegionCriterion,capture_dense,dense_billboard_loss
from determinism_policy import math_attention,assert_math_attention,backward
T=Path(__file__).resolve().parent
def save(path,data):
    with path.open('x',encoding='utf-8') as f:json.dump(data,f,indent=2,allow_nan=False)
def checkpoint(path,model,step,metadata):
    torch.save(dict(model_state_dict={k:v.detach().cpu().clone() for k,v in model.state_dict().items()},step=step,frametrail=metadata,group_detr=1,foreground_classes=615,approved_for_application=False),path)
def validate(model,base,rows):
    if len(rows)!=135 or any(r['split']!='val' for r in rows):raise ValueError('Validation partition changed')
    model.eval();predictions={}
    with torch.inference_mode():
        for r in rows:
            image,_=load_sample(base,r,'cuda:0');predictions[r['image_id']]=decode(model(image),r['width'],r['height'])
    return evaluate(rows,predictions)
@math_attention()
def run():
    verify();a,p=approval(T);project=T.parents[2];preflight(project)
    if not os.environ.get('SLURM_JOB_ID','').isdigit() or not torch.cuda.is_available() or torch.cuda.device_count()!=1:raise ValueError('Requires actual single-GPU Slurm allocation')
    v=variant(T);run_id=os.environ['SLURM_ARRAY_JOB_ID']+'_'+str(v['index']);release,schedule,original,resume=inputs(T);release_path=activate(T);release=validate_release(release_path)
    train={r['image_id']:r for r in release['images'] if r['split']=='train'};val=[r for r in release['images'] if r['split']=='val'];regions={r['image_id']:r['region'] for r in read(T/'region-review.json')['regions']}
    if len(train)!=700 or len(val)!=135 or any(r['supervision']!='gold' for r in release['images']):raise ValueError('Reviewed partition/supervision differs; gold schema is not independent human audit')
    out=project/f'output/rf-selector-{run_id}';out.mkdir(exist_ok=False);(out/'checkpoints').mkdir()
    torch.set_num_threads(2);torch.manual_seed(17);torch.cuda.manual_seed_all(17);torch.backends.cudnn.benchmark=False;torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.use_deterministic_algorithms(True)
    weights=project/'output/rf-comparison-v1/assets/rf-detr-small.pth';model=build_model(weights,T/'rf-mapping.json').cpu().eval()
    initial=torch.load(T/'inputs/selected-7805570.pt',map_location='cpu',weights_only=True);model.load_state_dict(initial['model_state_dict'],strict=True);del initial
    model=model.to('cuda:0');optimizer,check,allowed=configure(model,v['encoder_lr'],v['main_lr']);frozen=fingerprint_frozen(model,allowed)
    metadata=dict(actual_job_id=run_id,slurm_job_id=os.environ['SLURM_JOB_ID'],array_task_index=v['index'],variant=v,previous_job='7805570',candidate_sha256=p['candidate_sha256'],protocol_sha256=sha(T/'protocol.json'),approval_sha256=sha(T/'approval.json'),starting_checkpoint_sha256=p['starting_checkpoint']['sha256'],original_pretrained_sha256=sha(weights),active_classifier_rows=[133],active_classifier_heads=HEADS,region_overlay_sha256=sha(T/'region-review.json'),train_photos=700,sampled_training_photos=63,validation_photos=135,test_photos_used=0,fresh_video_frames_used=0,independent_human_recheck=False,approved_for_application=False)
    save(out/'preflight.json',metadata);save(out/'sampling-plan.json',schedule);start=time.monotonic();step=0;best_step=0;reason='maximum-updates';partial=False
    baseline=validate(model,release_path.parent,val)
    if not counts_equal(baseline,resume) or not eligible(baseline,original):raise ValueError('Starting baseline differs; never relax guards')
    best=baseline;save(out/'validation-0000.json',dict(step=0,eligible=True,**baseline));checkpoint(out/'checkpoints/step-0000.pt',model,0,metadata)
    params=[x for group in optimizer.param_groups for x in group['params']]
    for next_step,batch_ids in enumerate(schedule,1):
        if time.monotonic()-start>1650:reason='time-budget-margin';partial=True;break
        model.eval();optimizer.zero_grad(set_to_none=True);total=0.;dense_total=0.
        for image_id in batch_ids:
            image,target=load_sample(release_path.parent,train[image_id],'cuda:0');region=regions.get(image_id)
            outputs,raw=capture_dense(model,image);dense=dense_billboard_loss(raw,target,region,v['region_weight'])
            main=weighted_loss(RegionCriterion(region,v['region_weight'])(outputs,[target]));loss=(main+dense)/4
            if not bool(torch.isfinite(loss)):raise ValueError('Nonfinite loss')
            backward(loss);total+=float(loss.detach());dense_total+=float(dense.detach())/4
        if next_step==1:
            if any(param.grad is not None for name,param in model.named_parameters() if name not in allowed):raise ValueError('Frozen component received gradient')
            inactive=[i for i in range(616) if i!=133]
            for head in [model.class_embed,model.transformer.enc_out_class_embed[0]]:
                if head.weight.grad is None or head.bias.grad is None or not bool(head.weight.grad[133].abs().sum()):raise ValueError('Missing active row gradient')
                if bool(head.weight.grad[inactive].any()) or bool(head.bias.grad[inactive].any()):raise ValueError('Inactive row received gradient')
            save(out/'gradient-probe.json',dict(only_two_billboard_head_gradients=True,active_rows=[133],active_heads=HEADS,inactive_row_gradients_zero=True))
        norm=torch.nn.utils.clip_grad_norm_(params,.1,error_if_nonfinite=True);optimizer.step();step=next_step;check();assert_math_attention()
        save(out/f'step-{step:04}.json',dict(step=step,loss=total,dense_encoder_loss=dense_total,gradient_norm=float(norm),train_ids=batch_ids))
        if step%100==0:
            if time.monotonic()-start>1650:reason='time-budget-before-validation';partial=True;break
            current=validate(model,release_path.parent,val);ok=eligible(current,baseline) and eligible(current,original);check()
            if fingerprint_frozen(model,allowed)!=frozen:raise ValueError('Frozen parameters/buffers changed')
            save(out/f'validation-{step:04}.json',dict(step=step,eligible=ok,**current))
            if ok and ranking(current)>ranking(best) and ranking(current)>ranking(original):best=current;best_step=step;checkpoint(out/f'checkpoints/step-{step:04}.pt',model,step,metadata)
            print(f'selector {step}/3000; retention={ok}; selected={best_step}',flush=True)
            if stop_without_gain(step,best_step):reason='protocol-early-stop-no-gain';break
    check()
    if fingerprint_frozen(model,allowed)!=frozen:raise ValueError('Final frozen parameters changed')
    checkpoint(out/'last.pt',model,step,metadata);shutil.copyfile(out/f'checkpoints/step-{best_step:04}.pt',out/'best.pt');elapsed=time.monotonic()-start
    if elapsed>=1800:partial=True;reason='elapsed-cap-exceeded'
    status='partial-time-budget-stop' if partial else 'complete-awaiting-known-regression-evaluation-independent-evidence-needed' if best_step>0 else 'complete-no-improving-candidate'
    save(out/'experiment-report.json',dict(status=status,actual_job_id=run_id,slurm_job_id=os.environ['SLURM_JOB_ID'],array_task_index=v['index'],variant=v,previous_job='7805570',updates=step,completion_reason=reason,best_step=best_step,new_candidate_selected=best_step>0,best_checkpoint_sha256=sha(out/'best.pt'),last_checkpoint_sha256=sha(out/'last.pt'),starting_checkpoint_sha256=p['starting_checkpoint']['sha256'],active_classifier_rows=[133],active_classifier_heads=HEADS,frozen_parameters_and_buffers_unchanged=True,box_outputs_may_change=True,inactive_classifier_rows_unchanged=True,retention_against_both_baselines=True,elapsed_seconds=round(elapsed,2),test_and_video_used=False,approved_for_application=False))
    if partial:raise SystemExit(2)
if __name__=='__main__':run()
