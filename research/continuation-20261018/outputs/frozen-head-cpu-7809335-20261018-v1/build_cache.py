"""Build reusable train/development features on CPU. No optimizer or new data."""
import hashlib,json,time
from pathlib import Path
from cache_engine import *
from scoped_engine import build_model,load_sample
from continuation_guard import read,sha
from determinism_policy import math_attention
WEIGHTS=Path(r'C:\Users\nazee\Documents\All Modules\FrameTrail\.deps\rfdetr-probe-assets\rf-detr-small.pth')
def save(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,indent=2,allow_nan=False)
@math_attention()
def run():
    parity=read(HERE/'CACHE_PARITY.json');assert all(r['passed'] for r in parity['records'])
    plan=dict(status='local-development-linear-probe-plan-frozen-before-new-validation',authorization='Latest user: done, proceed to the next step and then keep goign; standing local autonomy permits reversible local model diagnostics. No new cluster submission.',checkpoint_sha256=parity['checkpoint_sha256'],training_photos=55,development_photos=135,test_photos_used=0,positive_features='One-to-one maximum-IoU frozen final query per known billboard training target, only if IoU>=0.5; uncovered targets are reported. No new annotations or inferred absences.',negative_features='All300queries on each of the35explicitly billboard-absent training photos; equal photo weighting.',loss='Mean covered-positive-query BCE +3*mean explicit-negative-query BCE +0.5*lambda*squared distance of row133 weight and bias from the selected starting row.',ridge_strengths=[.1,1.,10.,100.],optimizer='Deterministic full-batch CPU float64 L-BFGS, max200iterations/250evaluations/120seconds per fit; candidate stored float32.',selection='Each four predeclared fit evaluated once on unchanged135development photos. Same both-baseline per-class retention/FP and effective unscored530 guards; strict ranking gain; exact ties keep baseline/earlier trial. No regression-based reselection.',active_rows=[133],all_other_weights_features_and_boxes_frozen=True,model_mode='eval',threshold=.35,new_GPU_jobs=0,production_adoption=False,known_regression='Already consumed; further independent frozen evidence needed for generalization claims.',limits='New final-layer convex diagnostic, different from original RF auxiliary-layer IA-BCE training. Does not repair missing box coverage or waive strict numerical ONNX hold.')
    save(HERE/'LOCAL_EXPERIMENT_PLAN.json',plan)
    cache_dir=HERE/'cache';cache_dir.mkdir(exist_ok=False)
    torch.set_num_threads(2);torch.manual_seed(17);torch.use_deterministic_algorithms(True)
    net=build_model(WEIGHTS,TOOLS/'rf-mapping.json').cpu().eval();ck=torch.load(TOOLS/'inputs/selected-7805570.pt',map_location='cpu',weights_only=True)
    net.load_state_dict(ck['model_state_dict']);del ck
    for p in net.parameters():p.requires_grad_(False)
    w=net.class_embed.weight.detach().clone();b=net.class_embed.bias.detach().clone()
    release=read(TOOLS/'release/candidate-manifest-v2.json');pools=read(TOOLS/'sampling-pools.json');ids=set(pools['billboard']+pools['explicit_negative'])
    rows=[r for r in release['images'] if r['image_id'] in ids or r['split']=='val'];assert len(rows)==190
    first=next(r for r in rows if r['image_id'] in pools['billboard']);x,_=load_sample(TOOLS/'release',first)
    with torch.no_grad():base,_=capture(net,x)
    last=HERE.parent/'billboard-batch-proposal-7805570-20261018-v1/retrieval-7809335/task-2/verified-7809335_2/output/rf-billboard-batch-7809335_2/last.pt'
    altered=torch.load(last,map_location='cpu',weights_only=True)['model_state_dict']
    net.class_embed.weight[133].copy_(altered['class_embed.weight'][133]);net.class_embed.bias[133].copy_(altered['class_embed.bias'][133]);del altered
    with torch.no_grad():changed,live=capture(net,x);rebuilt=replay(base,net.class_embed.weight,net.class_embed.bias)
    assert torch.equal(changed['features'],base['features']) and max_output_error(live,rebuilt)==0
    save(HERE/'CHANGED_HEAD_PARITY.json',dict(features_bitwise_unchanged=True,full_output_max_error=0.,source='actual rejected task2 row133 at1500updates replayed on one fixed training image',optimizer_updates=0))
    net.class_embed.weight.copy_(w);net.class_embed.bias.copy_(b)
    torch.save(dict(weight=w,bias=b),cache_dir/'initial-head.pt')
    metadata={};started=time.perf_counter()
    for i,row in enumerate(rows,1):
        path=TOOLS/'release'/row['source_path'];assert sha(path)==row['image_sha256']
        image,target=load_sample(TOOLS/'release',row)
        with torch.no_grad():cached,live=capture(net,image,full=row['split']=='train')
        with torch.no_grad():assert max_output_error(dict(pred_logits=live['pred_logits'],pred_boxes=live['pred_boxes']) if row['split']=='val' else live,replay(cached,w,b))==0
        file=cache_dir/(row['image_id']+'.pt');torch.save(cached,file)
        metadata[row['image_id']]=dict(split=row['split'],source_sha256=row['image_sha256'],cache_sha256=sha(file),full_auxiliary_cache=row['split']=='train')
        if i%20==0:print(f'Cached {i}/190 train/development photos on CPU; no optimizer updates',flush=True)
    assert torch.equal(net.class_embed.weight,w) and torch.equal(net.class_embed.bias,b)
    save(HERE/'CACHE_INDEX.json',metadata)
    save(HERE/'CACHE_RECEIPT.json',dict(status='190-frozen-feature-caches-built-with-bitwise-head-forward-parity',training_images=55,development_images=135,test_or_known_regression_used=False,all190_forward_errors_zero=True,optimizer_updates=0,new_GPU_jobs=0,seconds=time.perf_counter()-started,bytes=sum(p.stat().st_size for p in cache_dir.glob('*.pt')),plan_sha256=sha(HERE/'LOCAL_EXPERIMENT_PLAN.json')))
if __name__=='__main__':run()
