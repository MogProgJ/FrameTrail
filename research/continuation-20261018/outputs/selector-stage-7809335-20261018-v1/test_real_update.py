"""One in-memory CPU update of the packaged exact four-photo training objective."""
import json,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;P=HERE.parent/'selector-batch-proposal-7809335-20261018-v1'
identity=json.loads((P/'PROPOSAL_IDENTITY.json').read_text());T=P/identity['package_directory']
WHEEL=Path(r'C:\Users\nazee\.codex\visualizations\2026\10\11\01a12a01-d564-7de0-91f4-a16484eea2cb\rf-comparison-package-20261013-v1\local-assignment-wheel\torch_hungarian-0.1.0rc0-py3-none-any.whl')
sys.path[:0]=[str(T),str(WHEEL)]
import torch
from scoped_engine import build_model,load_sample
from scoped_rf import weighted_loss
from selector_mechanics import configure,fingerprint_frozen,RegionCriterion,capture_dense,dense_billboard_loss
from determinism_policy import math_attention,backward,assert_math_attention
from continuation_guard import read,sha,inputs
@math_attention()
def run():
    started=time.perf_counter();torch.set_num_threads(2);torch.manual_seed(17);torch.use_deterministic_algorithms(True)
    release,schedule,_,_=inputs(T,False,0);rows={r['image_id']:r for r in release['images']};regions={r['image_id']:r['region'] for r in read(T/'region-review.json')['regions']}
    weights=Path(r'C:\Users\nazee\Documents\All Modules\FrameTrail\.deps\rfdetr-probe-assets\rf-detr-small.pth');pinned=sha(T/'inputs/selected-7805570.pt')
    model=build_model(weights,T/'rf-mapping.json').cpu().eval();ck=torch.load(T/'inputs/selected-7805570.pt',map_location='cpu',weights_only=True);model.load_state_dict(ck['model_state_dict']);del ck
    opt,check,allowed=configure(model,.00001);before=fingerprint_frozen(model,allowed);active_before={k:v.detach().clone() for k,v in model.state_dict().items() if k in allowed};total=0;dense_values=[]
    for i in schedule[0]:
        image,target=load_sample(T/'release',rows[i]);region=regions.get(i);outputs,raw=capture_dense(model,image)
        dense=dense_billboard_loss(raw,target,region,1);objective=(weighted_loss(RegionCriterion(region,1)(outputs,[target]))+dense)/4
        assert bool(torch.isfinite(objective));backward(objective);total+=float(objective.detach());dense_values.append(float(dense.detach()))
    inactive=[i for i in range(616) if i!=133]
    for name,param in model.named_parameters():
        if name in allowed:assert param.grad is not None and not bool(param.grad[inactive].any()) and bool(param.grad[133].abs().sum())
        else:assert param.grad is None
    params=[p for g in opt.param_groups for p in g['params']];norm=torch.nn.utils.clip_grad_norm_(params,.1,error_if_nonfinite=True);opt.step();check();assert_math_attention()
    assert fingerprint_frozen(model,allowed)==before
    changed=[k for k in allowed if not torch.equal(active_before[k][133],model.state_dict()[k][133])];assert len(changed)==4
    with torch.inference_mode():
        image,_=load_sample(T/'release',rows[schedule[0][0]]);after=model(image);assert bool(torch.isfinite(after['pred_logits']).all()) and bool(torch.isfinite(after['pred_boxes']).all())
    assert sha(T/'inputs/selected-7805570.pt')==pinned
    receipt=dict(status='packaged-four-photo-objective-one-real-CPU-update-passed',protocol_sha256=identity['protocol_sha256'],photos=schedule[0],loss=total,dense_per_photo=dense_values,gradient_norm=float(norm),changed_state_keys=sorted(changed),only_two_billboard_rows_changed=True,frozen_parameters_buffers_and_other_rows_identical=True,in_memory_updates=1,persisted_checkpoint_changes=0,source_checkpoint_unchanged=True,post_update_forward_finite=True,seconds=time.perf_counter()-started,new_GPU_jobs=0,production_adoption=False)
    with (P/'REAL_CPU_UPDATE.json').open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2)
    print(json.dumps(receipt,indent=2))
if __name__=='__main__':run()
