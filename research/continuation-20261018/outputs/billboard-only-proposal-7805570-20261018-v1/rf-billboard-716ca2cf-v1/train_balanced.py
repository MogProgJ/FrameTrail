"""One approved two-row continuation; no retry, downloads, export or adoption."""
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
import json,time,shutil
from pathlib import Path
import torch
from continuation_guard import approval,inputs,activate,counts_equal,stop_without_gain,read,sha
from verify_package import verify
from preflight import preflight
from scoped_engine import build_model,load_sample,validate_release,scoped_batch_one_loss
from scoped_metrics import decode
from selection_policy import evaluate,eligible,ranking
from head_policy import configure,fingerprint_frozen
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
def retain(current,baseline,original):return eligible(current,baseline) and eligible(current,original)
@math_attention()
def run():
    verify();a,p=approval(T);project=T.parents[2];preflight(project)
    if not os.environ.get('SLURM_JOB_ID','').isdigit() or not torch.cuda.is_available() or torch.cuda.device_count()!=1:raise ValueError('Requires actual single-GPU Slurm allocation')
    release,schedule,original,resume=inputs(T);release_path=activate(T);release=validate_release(release_path)
    train={r['image_id']:r for r in release['images'] if r['split']=='train'};val=[r for r in release['images'] if r['split']=='val']
    if len(train)!=700 or len(val)!=135 or any(r['supervision']!='gold' for r in release['images']):raise ValueError('Reviewed partition/supervision differs; gold is schema wording, not an independent human audit')
    out=project/f"output/rf-billboard-{os.environ['SLURM_JOB_ID']}";out.mkdir(exist_ok=False);(out/'checkpoints').mkdir()
    torch.set_num_threads(2);torch.manual_seed(17);torch.cuda.manual_seed_all(17);torch.backends.cudnn.benchmark=False;torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.use_deterministic_algorithms(True)
    weights=project/'output/rf-comparison-v1/assets/rf-detr-small.pth';model=build_model(weights,T/'rf-mapping.json').cpu().eval()
    initial=torch.load(T/'inputs/selected-7805570.pt',map_location='cpu',weights_only=True);model.load_state_dict(initial['model_state_dict'],strict=True);del initial
    model=model.to('cuda:0');optimizer,check=configure(model,[133],.0001);frozen=fingerprint_frozen(model)
    metadata=dict(actual_job_id=os.environ['SLURM_JOB_ID'],previous_job='7805570',candidate_sha256=p['candidate_sha256'],protocol_sha256=sha(T/'protocol.json'),approval_sha256=sha(T/'approval.json'),starting_checkpoint_sha256=p['starting_checkpoint']['sha256'],original_pretrained_sha256=sha(weights),active_classifier_rows=[133],train_photos=700,validation_photos=135,test_photos_used=0,fresh_video_frames_used=0,independent_human_recheck=False,approved_for_application=False)
    save(out/'preflight.json',metadata);save(out/'sampling-plan.json',schedule);start=time.monotonic();step=0;best_step=0;reason='maximum-updates';partial=False
    baseline=validate(model,release_path.parent,val)
    if not counts_equal(baseline,resume) or not eligible(baseline,original):raise ValueError('Baseline counts differ from both pinned references; no automatic guard relaxation')
    best=baseline;save(out/'validation-0000.json',dict(step=0,eligible=True,**baseline));checkpoint(out/'checkpoints/step-0000.pt',model,0,metadata)
    for next_step,batch_ids in enumerate(schedule,1):
        if time.monotonic()-start>1650:reason='time-budget-margin';partial=True;break
        model.eval();optimizer.zero_grad(set_to_none=True);total=0
        for image_id in batch_ids:
            image,target=load_sample(release_path.parent,train[image_id],'cuda:0');loss,_,_=scoped_batch_one_loss(model,image,target);backward(loss/4);total+=float(loss.detach())/4
        if next_step==1:
            allowed={id(model.class_embed.weight),id(model.class_embed.bias)}
            if any(v.grad is not None for v in model.parameters() if id(v) not in allowed):raise ValueError('Frozen component received gradients')
            if not bool(model.class_embed.weight.grad[[133]].abs().sum()):raise ValueError('No active classifier gradient')
            inactive=[i for i in range(616) if i not in [133]]
            if bool(model.class_embed.weight.grad[inactive].any()) or bool(model.class_embed.bias.grad[inactive].any()):raise ValueError('Inactive row received gradients')
            save(out/'gradient-probe.json',dict(only_main_classifier_gradients=True,active_rows=[133],inactive_row_gradients_zero=True))
        norm=torch.nn.utils.clip_grad_norm_(model.class_embed.parameters(),.1,error_if_nonfinite=True);optimizer.step();step=next_step;check();assert_math_attention()
        save(out/f'step-{step:04}.json',dict(step=step,loss=total,gradient_norm=float(norm),train_ids=batch_ids))
        if step%100==0:
            if time.monotonic()-start>1650:reason='time-budget-before-validation';partial=True;break
            current=validate(model,release_path.parent,val);ok=retain(current,baseline,original);check()
            if fingerprint_frozen(model)!=frozen:raise ValueError('Frozen features/boxes/encoder changed')
            save(out/f'validation-{step:04}.json',dict(step=step,eligible=ok,**current))
            if ok and ranking(current)>ranking(best) and ranking(current)>ranking(original):
                best=current;best_step=step;checkpoint(out/f'checkpoints/step-{step:04}.pt',model,step,metadata)
            print(f'balanced {step}/3000; retention={ok}; selected={best_step}',flush=True)
            if stop_without_gain(step,best_step):reason='protocol-early-stop-no-gain';break
    check()
    if fingerprint_frozen(model)!=frozen:raise ValueError('Final frozen state changed')
    checkpoint(out/'last.pt',model,step,metadata);shutil.copyfile(out/f'checkpoints/step-{best_step:04}.pt',out/'best.pt')
    elapsed=time.monotonic()-start
    if elapsed>=1800:partial=True;reason='elapsed-cap-exceeded'
    status='partial-time-budget-stop' if partial else 'complete-awaiting-known-regression-evaluation-independent-evidence-needed' if best_step>0 else 'complete-no-improving-candidate'
    save(out/'experiment-report.json',dict(status=status,actual_job_id=os.environ['SLURM_JOB_ID'],previous_job='7805570',updates=step,completion_reason=reason,best_step=best_step,new_candidate_selected=best_step>0,best_checkpoint_sha256=sha(out/'best.pt'),last_checkpoint_sha256=sha(out/'last.pt'),starting_checkpoint_sha256=p['starting_checkpoint']['sha256'],active_classifier_rows=[133],frozen_features_and_boxes_unchanged=True,inactive_classifier_rows_unchanged=True,retention_against_both_baselines=True,elapsed_seconds=round(elapsed,2),test_and_video_used=False,approved_for_application=False))
    if partial:raise SystemExit(2)
if __name__=='__main__':run()
