"""Two fixed M1 trials. Save all prespecified states; selection runs later on pinned local CPU."""
import os
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
import argparse,time,signal,traceback
from pathlib import Path
import torch
from batch_guard import *
from scoped_engine import build_model,load_sample
from scoped_rf import ScopedRFCriterion,weighted_loss
from selector_mechanics import configure,capture_dense,dense_billboard_loss
from determinism_policy import math_attention,assert_math_attention,backward

@math_attention()
def run(project):
    base=Path(__file__).resolve().parent;s=validate_scope(read(base/'SCOPE.json'));scope_sha=sha(base/'SCOPE.json')
    index=int(os.environ['SLURM_ARRAY_TASK_ID']);job=valid_job(os.environ['SLURM_ARRAY_JOB_ID'])
    if index not in (0,1) or not os.environ['SLURM_JOB_ID'].isdigit() or not torch.cuda.is_available() or torch.cuda.device_count()!=1:raise ValueError('Require one actual Slurm GPU task')
    seed=s['seeds'][index];run_id=f'{job}_{index}';out=project/'output'/('rf-fresh-selector-'+run_id);out.mkdir(exist_ok=False)
    start=time.monotonic();step=0;stopped=False;patches=[]
    def stop(sig,frame):raise TimeoutError('Active time budget signal; preserve partial task')
    signal.signal(signal.SIGTERM,stop)
    try:
        from verify_package import verify
        preflight=verify(base,project);write(out/'PREFLIGHT.json',preflight)
        torch.set_num_threads(2);torch.manual_seed(17);torch.cuda.manual_seed_all(17)
        torch.use_deterministic_algorithms(True);torch.backends.cudnn.benchmark=False
        torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        old=project/'output/training-general-v1/rf-selector-a77d9663-v1'
        model=build_model(project/'output/rf-comparison-v1/assets/rf-detr-small.pth',base/'rf-mapping.json').cpu().eval()
        initial=torch.load(old/'inputs/selected-7805570.pt',map_location='cpu',weights_only=True)
        model.load_state_dict(initial['model_state_dict'],strict=True);del initial
        frozen=frozen_digest(model.state_dict());model=model.to('cuda:0').eval()
        optimizer,check,allowed=configure(model,s['encoder_lr'],s['main_lr']);criterion=ScopedRFCriterion(615)
        records=read(base/'INPUTS.json')['records'];schedule=read(base/f'schedule-{seed}.json')
        ids=validate_inputs(records,[schedule]);train={k:r for k,r in ids.items() if r['row']['split']=='train'}
        meta=dict(actual_job_id=run_id,scope_sha256=scope_sha,seed=seed,index=index,starting_checkpoint_sha256=CHECKPOINT,
          schedule_sha256=sha(base/f'schedule-{seed}.json'),frozen_digest=frozen,production_adoption=False)
        def checkpoint(n):
            check()
            if frozen_digest(model.state_dict())!=frozen:raise ValueError('Frozen state bytes changed')
            name=f'patch-{n:04}.pt';torch.save(make_patch(model.state_dict(),dict(meta,step=n)),out/name)
            patches.append(dict(step=n,path=name,sha256=sha(out/name)))
        checkpoint(0);params=[p for g in optimizer.param_groups for p in g['params']]
        with (out/'TRAINING_STEPS.jsonl').open('x',encoding='utf-8',buffering=1) as log:
            for n,batch in enumerate(schedule,1):
                if time.monotonic()-start>=1740:raise TimeoutError('Active time budget margin')
                optimizer.zero_grad(set_to_none=True);total=0.;dense_total=0.
                for iid in batch:
                    r=train[iid];root=base/'fresh' if r['source']=='fresh' else old/'release'
                    image,target=load_sample(root,r['row'],'cuda:0');outputs,raw=capture_dense(model,image)
                    dense=dense_billboard_loss(raw,target,None,1.)
                    loss=(weighted_loss(criterion(outputs,[target]))+dense)/4
                    if not bool(torch.isfinite(loss)):raise ValueError('Nonfinite loss')
                    backward(loss);total+=float(loss.detach());dense_total+=float(dense.detach())/4
                for name,p in model.named_parameters():
                    if name not in allowed and p.grad is not None:raise ValueError('Frozen gradient')
                    if name in allowed:
                        if p.grad is None or bool(p.grad[[i for i in range(616) if i!=133]].any()):raise ValueError('Inactive gradient')
                norm=torch.nn.utils.clip_grad_norm_(params,.1,error_if_nonfinite=True)
                optimizer.step();step=n;check();assert_math_attention()
                log.write(json.dumps(dict(step=step,train_ids=batch,loss=total,dense_loss=dense_total,gradient_norm=float(norm)),allow_nan=False)+'\n')
                if step in STEPS:checkpoint(step);print(json.dumps(dict(job=run_id,step=step,elapsed_seconds=round(time.monotonic()-start,2))),flush=True)
        checkpoint_last=out/'last.pt';torch.save(make_patch(model.state_dict(),dict(meta,step=step)),checkpoint_last)
        elapsed=time.monotonic()-start
        if elapsed>=1800:raise TimeoutError('Active budget exceeded')
        write(out/'REPORT.json',dict(status='complete-awaiting-local-CPU-selection',**meta,updates=step,elapsed_active_seconds=elapsed,
          patches=patches,last_sha256=sha(checkpoint_last),frozen_state_unchanged=True,inactive_rows_bitwise_unchanged=True,
          validation_selection_performed=False,test_photos_used=0,automatic_retries=0))
    except BaseException as e:
        write(out/'FAILED.json',dict(status='failed-or-partial-preserve-evidence-no-retry',actual_job_id=run_id,scope_sha256=scope_sha,
          updates=step,patches=patches,error=str(e),traceback=traceback.format_exc(),elapsed_active_seconds=time.monotonic()-start,
          test_photos_used=0,production_adoption=False))
        raise
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--project',type=Path,required=True);run(ap.parse_args().project)
