"""CPU contracts and real gradient/cache preparation; no model optimizer update."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
FROZEN=HERE.parent/'frozen-head-cpu-7809335-20261018-v1';TOOLS=HERE.parent/'billboard-batch-proposal-7805570-20261018-v1/rf-billboard-batch-0a255598-v1'
WHEEL=Path(r'C:\Users\nazee\.codex\visualizations\2026\10\11\01a12a01-d564-7de0-91f4-a16484eea2cb\rf-comparison-package-20261013-v1\local-assignment-wheel\torch_hungarian-0.1.0rc0-py3-none-any.whl')
sys.path[:0]=[str(TOOLS),str(FROZEN),str(WHEEL)]
import torch
from selector_mechanics import *
from cache_engine import capture,replay,max_output_error
from verify_cache_parity import fingerprint
from scoped_engine import build_model,load_sample
from scoped_rf import weighted_loss,ScopedRFCriterion
from determinism_policy import math_attention
from continuation_guard import read,sha
WEIGHTS=Path(r'C:\Users\nazee\Documents\All Modules\FrameTrail\.deps\rfdetr-probe-assets\rf-detr-small.pth')
def save(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,indent=2,allow_nan=False)
def synthetic_contracts():
    net=torch.nn.Module();net.class_embed=torch.nn.Linear(4,616);net.transformer=torch.nn.Module();net.transformer.enc_out_class_embed=torch.nn.ModuleList([torch.nn.Linear(4,616)]);net.frozen=torch.nn.Linear(4,4)
    opt,check,allowed=configure(net,.00003);before=fingerprint_frozen(net,allowed);initial={k:v.clone() for k,v in net.state_dict().items()}
    (net.class_embed(torch.ones(2,4)).square().sum()+net.transformer.enc_out_class_embed[0](torch.ones(2,4)).square().sum()).backward();opt.step();check();assert fingerprint_frozen(net,allowed)==before
    assert all(not torch.equal(initial[k][133],net.state_dict()[k][133]) for k in allowed)
    boxes=torch.tensor([[[.2,.2,.1,.1]]*10+[[.8,.8,.1,.1]]*290]);logits=torch.zeros(1,300,616,requires_grad=True)
    target=dict(labels=torch.tensor([571]),boxes=torch.tensor([[.2,.2,.1,.1]]),scope_negative_mask=torch.zeros(616,dtype=torch.bool))
    loss=weighted_loss(RegionCriterion([.2,.2,.1,.1],3)({'pred_logits':logits,'pred_boxes':boxes},[target]));loss.backward();assert bool(logits.grad[0,:10,133].any()) and not bool(logits.grad[0,10:,133].any())
    raw_logits=torch.zeros(1,400,616,requires_grad=True);raw_boxes=torch.tensor([[[.2,.2,.1,.1]]*10+[[.8,.8,.1,.1]]*390])
    dense_billboard_loss(dict(pred_logits=raw_logits,pred_boxes=raw_boxes),target,[.2,.2,.1,.1],3).backward();assert bool(raw_logits.grad[0,:10,133].any()) and not bool(raw_logits.grad[0,10:,133].any())
    return dict(synthetic_optimizer_only_two_row133s_changed=True,reviewed_region_outside_unknown_gradients_zero=True,dense_region_outside_unknown_gradients_zero=True)
@math_attention()
def run():
    torch.set_num_threads(2);torch.manual_seed(17);torch.use_deterministic_algorithms(True);contracts=synthetic_contracts()
    model=build_model(WEIGHTS,TOOLS/'rf-mapping.json').cpu().eval();loaded=torch.load(TOOLS/'inputs/selected-7805570.pt',map_location='cpu',weights_only=True);model.load_state_dict(loaded['model_state_dict']);del loaded
    before=fingerprint(model);optimizer,check,allowed=configure(model,.00003)
    rows={r['image_id']:r for r in read(TOOLS/'release/candidate-manifest-v2.json')['images']};pools=read(TOOLS/'sampling-pools.json');regions=read(FROZEN/'reviewed-contrast/REGION_REVIEW.json')['regions'];cache_dir=HERE/'roi-cache';cache_dir.mkdir(exist_ok=False)
    first=rows[pools['billboard'][0]];image,target=load_sample(TOOLS/'release',first);model.zero_grad(set_to_none=True)
    outputs,raw=capture_dense(model,image);objective=weighted_loss(RegionCriterion()(outputs,[target]))+dense_billboard_loss(raw,target);objective.backward()
    head_grads={name:float(p.grad[133].abs().sum()) for name,p in model.named_parameters() if name in allowed};assert all(v>0 for v in head_grads.values())
    inactive=[i for i in range(616) if i!=133]
    for name,p in model.named_parameters():
        if name in allowed:assert not bool(p.grad[inactive].any())
        else:assert p.grad is None
    check();cache_index={}
    for region in regions:
        image_id=region['image_id'];row=rows[image_id];assert row['split']=='train' and row['scope'].get('133','unknown')=='unknown'
        image,target=load_sample(TOOLS/'release',row);model.zero_grad(set_to_none=True)
        cached,live=capture(model,image,full=True);criterion=RegionCriterion(region['region'],3);value=weighted_loss(criterion(live,[target]));value.backward()
        for name,p in model.named_parameters():
            if name in allowed:assert p.grad is None or not bool(p.grad[inactive].any())
            else:assert p.grad is None
        with torch.no_grad():rebuilt=replay(cached,model.class_embed.weight,model.class_embed.bias)
        assert max_output_error(live,rebuilt)==0
        path=cache_dir/(image_id+'.pt');torch.save(cached,path);cache_index[image_id]=dict(sha256=sha(path),region=region['region'],image_sha256=region['image_sha256'])
    assert fingerprint(model)==before
    save(HERE/'ROI_CACHE_INDEX.json',cache_index)
    save(HERE/'MECHANICS_RECEIPT.json',dict(status='selector-and-region-mechanics-CPU-verified',synthetic_contracts=contracts,real_positive_main_and_encoder_row_gradients=head_grads,only_permitted_row_gradients=True,all_actual_model_state_unchanged=True,real_optimizer_updates=0,new_GPU_jobs=0,ROI_cache_photos=8,all_eight_cache_output_errors_zero=True,mechanics_sha256=sha(HERE/'selector_mechanics.py')))
    print(json.dumps(read(HERE/'MECHANICS_RECEIPT.json'),indent=2))
if __name__=='__main__':run()
