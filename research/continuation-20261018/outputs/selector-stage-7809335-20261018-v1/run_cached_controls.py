"""Two frozen-selector CPU controls for the prospective selector experiment."""
import json,random,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
FROZEN=HERE.parent/'frozen-head-cpu-7809335-20261018-v1';TOOLS=HERE.parent/'billboard-batch-proposal-7805570-20261018-v1/rf-billboard-batch-0a255598-v1'
WHEEL=Path(r'C:\Users\nazee\.codex\visualizations\2026\10\11\01a12a01-d564-7de0-91f4-a16484eea2cb\rf-comparison-package-20261013-v1\local-assignment-wheel\torch_hungarian-0.1.0rc0-py3-none-any.whl')
sys.path[:0]=[str(TOOLS),str(FROZEN),str(WHEEL)]
import torch
from selector_mechanics import RegionCriterion
from cache_engine import replay
from scoped_rf import target_from_row,weighted_loss
from scoped_metrics import decode
from selection_policy import evaluate,eligible,ranking
from continuation_guard import read,sha,counts_equal
def save(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,indent=2,allow_nan=False)
def run():
    assert read(HERE/'MECHANICS_RECEIPT.json')['mechanics_sha256']==sha(HERE/'selector_mechanics.py')
    plan=dict(status='two-frozen-selector-CPU-controls-before-new-GPU-proposal',region_weights=[1.,3.],main_lr=.0001,encoder_classifier_frozen=True,updates=1500,accumulation=4,batch='One billboard-positive, two distinct explicitly absent photos, one separately reviewed training traffic-sign region',seeds=[171022,171023,171024],optimizer='FP32 AdamW,weight_decay0,foreachFalse,clip.1,evalmode',validation='Step0and every100, same135development images/both-baseline guard/unscored530/strict ranking/earliest ties',partial_seconds_cap_each=900,new_GPU_jobs=0,notes='Dense encoder auxiliary loss has zero main-head gradient while encoder is frozen, so that constant is omitted from these controls. Feature/box/encoder outputs are cached at the starting checkpoint.')
    save(HERE/'CPU_CONTROL_PLAN.json',plan);torch.set_num_threads(2);torch.manual_seed(17);torch.use_deterministic_algorithms(True)
    release=read(TOOLS/'release/candidate-manifest-v2.json');rows={r['image_id']:r for r in release['images']};val=[r for r in release['images'] if r['split']=='val'];pools=read(TOOLS/'sampling-pools.json');roi=read(HERE/'ROI_CACHE_INDEX.json');roi_ids=sorted(roi)
    def cycles(ids,seed):
        rng=random.Random(seed);out=[]
        while len(out)<1500:
            c=list(ids);rng.shuffle(c);out+=c
        return out[:1500]
    positives=cycles(pools['billboard'],171022);region_cycle=cycles(roi_ids,171024);rng=random.Random(171023)
    schedule=[[positives[i],*rng.sample(pools['explicit_negative'],2),region_cycle[i]] for i in range(1500)]
    save(HERE/'CPU_CONTROL_SCHEDULE.json',schedule)
    train_ids=set(pools['billboard']+pools['explicit_negative']+roi_ids);assert all(rows[i]['split']=='train' for i in train_ids)
    cache={i:torch.load((HERE/'roi-cache' if i in roi else FROZEN/'cache-full-layout')/(i+'.pt'),map_location='cpu',weights_only=True) for i in train_ids}
    vc={r['image_id']:torch.load(FROZEN/'cache-full-layout'/(r['image_id']+'.pt'),map_location='cpu',weights_only=True) for r in val}
    targets={i:target_from_row(rows[i],615) for i in train_ids}
    baseline=read(FROZEN/'local-probes/validation-baseline.json');original=read(TOOLS/'inputs/validation-original.json');assert counts_equal(baseline,read(TOOLS/'inputs/validation-resume.json'))
    initial=torch.load(FROZEN/'cache-full-layout/initial-head.pt',map_location='cpu',weights_only=True);inactive=[i for i in range(616) if i!=133];summaries=[]
    def validate(head):
        with torch.inference_mode():preds={r['image_id']:decode(replay(vc[r['image_id']],head.weight,head.bias),r['width'],r['height']) for r in val}
        return evaluate(val,preds)
    for rw in plan['region_weights']:
        out=HERE/f'CPU-control-region{int(rw)}';out.mkdir(exist_ok=False);head=torch.nn.Linear(256,616);head.load_state_dict(initial);mask=torch.zeros(616);mask[133]=1
        head.weight.register_hook(lambda g:g*mask[:,None]);head.bias.register_hook(lambda g:g*mask)
        opt=torch.optim.AdamW(head.parameters(),lr=.0001,weight_decay=0,foreach=False);best=baseline;best_step=0;steps=0;partial=False;started=time.perf_counter();trace=[]
        save(out/'validation-0000.json',dict(step=0,eligible=True,**baseline));torch.save(initial,out/'BEST.pt')
        for step,batch in enumerate(schedule,1):
            if time.perf_counter()-started>900:partial=True;break
            opt.zero_grad(set_to_none=True);total=0
            for image_id in batch:
                outputs=replay(cache[image_id],head.weight,head.bias);criterion=RegionCriterion(roi[image_id]['region'] if image_id in roi else None,rw);objective=weighted_loss(criterion(outputs,[targets[image_id]]))/4;objective.backward();total+=float(objective.detach())
            norm=torch.nn.utils.clip_grad_norm_(head.parameters(),.1,error_if_nonfinite=True);opt.step();steps=step
            assert all(torch.equal(head.state_dict()[k][inactive],initial[k][inactive]) for k in initial)
            save(out/f'step-{step:04}.json',dict(step=step,train_ids=batch,loss=total,gradient_norm=float(norm)))
            if step%100==0:
                current=validate(head);ok=eligible(current,baseline) and eligible(current,original)
                save(out/f'validation-{step:04}.json',dict(step=step,eligible=ok,**current))
                if ok and ranking(current)>ranking(best) and ranking(current)>ranking(original):best=current;best_step=step;torch.save({k:v.detach().clone() for k,v in head.state_dict().items()},out/'BEST.pt')
                b=current['per_class']['133'];item=dict(step=step,eligible=ok,billboard_known_hits=b['complete_tp']+b['partial_hits'],billboard_complete_fp=b['complete_fp'],unscored=current['metrics']['unscored_predictions'],selected=best_step);trace.append(item);print(json.dumps(dict(region_weight=rw,**item)),flush=True)
        torch.save({k:v.detach().clone() for k,v in head.state_dict().items()},out/'LAST.pt');result=dict(status='partial-time-cap' if partial else 'complete',region_weight=rw,updates=steps,selected_step=best_step,new_candidate_selected=best_step>0,seconds=time.perf_counter()-started,trace=trace,only_main_row133_changed=True,encoder_features_boxes_and_other_rows_frozen=True,new_GPU_jobs=0,production_adoption=False)
        save(out/'RECEIPT.json',result);summaries.append(result)
    save(HERE/'CPU_CONTROLS_RECEIPT.json',dict(status='two-CPU-controls-finished',controls=summaries,new_GPU_jobs=0,production_adoption=False))
if __name__=='__main__':run()
