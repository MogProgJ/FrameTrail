"""Four predeclared TRAIN-only local contrast fits; no cluster job or adoption."""
import json,sys,time
from pathlib import Path
D=Path(__file__).resolve().parent;FROZEN=D.parent/'frozen-head-cpu-7809335-20261018-v1';T=D.parent/'selector-batch-proposal-7809335-20261018-v1/rf-selector-a77d9663-v1'
sys.path.insert(0,str(FROZEN))
from cache_engine import *
from scoped_engine import build_model,load_sample
from verify_cache_parity import fingerprint
from run_local_probes import predict,CACHE
from fit_teacher_preserved_probes import fit
from continuation_guard import read,sha,counts_equal
from selection_policy import eligible,ranking,evaluate
from determinism_policy import math_attention
from rfdetr.utilities import box_ops
WEIGHTS=Path(r'C:\Users\nazee\Documents\All Modules\FrameTrail\.deps\rfdetr-probe-assets\rf-detr-small.pth')
def save(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,indent=2,allow_nan=False)
def mask_region(boxes,region):
    pred=box_ops.box_cxcywh_to_xyxy(boxes).clamp(0,1);gt=box_ops.box_cxcywh_to_xyxy(torch.tensor([region],dtype=boxes.dtype));return box_ops.box_iou(pred,gt)[0][:,0]>=.7
@math_attention()
def run():
    torch.set_num_threads(2);torch.manual_seed(17);torch.use_deterministic_algorithms(True);plan=read(D/'LOCAL_CONTRAST_PLAN.json');overlay=read(D/'TRAIN_CONTRAST_OVERLAY.json');assert plan['training_overlay_sha256']==sha(D/'TRAIN_CONTRAST_OVERLAY.json')
    source_hash=sha(T/'inputs/selected-7805570.pt');release_hash=sha(T/'release/candidate-manifest-v2.json');rows={r['image_id']:r for r in read(T/'release/candidate-manifest-v2.json')['images']}
    out=D/'local-contrast';out.mkdir(exist_ok=False);cache_dir=out/'cache';cache_dir.mkdir();model=build_model(WEIGHTS,T/'rf-mapping.json').cpu().eval();ck=torch.load(T/'inputs/selected-7805570.pt',map_location='cpu',weights_only=True);model.load_state_dict(ck['model_state_dict']);del ck
    for param in model.parameters():param.requires_grad_(False)
    initial=fingerprint(model);head0={k:v.detach().clone() for k,v in model.class_embed.state_dict().items()};cache={};index=[]
    for record in overlay['records']:
        i=record['image_id'];row=rows[i];assert row['split']=='train' and row['scope'].get('133','unknown')=='unknown' and sha(T/'release'/row['source_path'])==record['image_sha256']
        with torch.inference_mode():
            image,_=load_sample(T/'release',row);c,live=capture(model,image,full=True);rebuilt=replay(c,head0['weight'],head0['bias']);error=max_output_error(live,rebuilt)
        assert error==0;torch.save(c,cache_dir/(i+'.pt'));cache[i]=c;index.append(dict(image_id=i,cache_sha256=sha(cache_dir/(i+'.pt')),max_output_error=error))
    assert fingerprint(model)==initial;del model
    save(out/'CACHE_RECEIPT.json',dict(status='24-new-TRAIN-feature-caches-exact',plan_sha256=sha(D/'LOCAL_CONTRAST_PLAN.json'),overlay_sha256=sha(D/'TRAIN_CONTRAST_OVERLAY.json'),all_model_state_unchanged=True,optimizer_updates=0,records=index))
    stats=torch.load(FROZEN/'teacher-preservation/training-statistics.pt',map_location='cpu',weights_only=True);assert sha(FROZEN/'teacher-preservation/training-statistics.pt')==read(FROZEN/'teacher-preservation/STATISTICS_RECEIPT.json')['statistics_sha256'];C=stats['covariance']
    n=[]
    for i in read(T/'sampling-pools.json')['explicit_negative']:
        c=torch.load(CACHE/(i+'.pt'),map_location='cpu',weights_only=True);n.append(c['features'][-1,0].double())
    for r in overlay['records']:
        if r['supervision']=='whole_photo_billboard_absent':n.append(cache[r['image_id']]['features'][-1,0].double())
    region_features=[value.double() for i,value in sorted(stats['reviewed_roi_features'].items())];region_coverage=[]
    for r in overlay['records']:
        if r['supervision']=='region_billboard_negative_only':
            c=cache[r['image_id']];mask=mask_region(c['boxes'][-1,0],r['region']);features=c['features'][-1,0,mask].double();region_coverage.append(dict(image_id=r['image_id'],queries=int(mask.sum())))
            if len(features):region_features.append(features)
    neg=torch.cat(n);roi=torch.cat(region_features);rw=torch.cat([torch.full((len(x),),1/len(x),dtype=torch.float64) for x in region_features]);rw*=3/rw.sum();nw=torch.full((len(neg),),3/len(neg),dtype=torch.float64)
    initial_theta=torch.cat([head0['weight'][133],head0['bias'][133:134]]).double();heads=[];recipes=plan['variants'];input_audit=[]
    for recipe in recipes:
        p=[];pw=[];positive_ids=[]
        for item in read(FROZEN/'TRAIN_FEATURE_COVERAGE.json')['coverage']:
            i=item['image_id'];selected=item['selected_queries']
            if recipe['positive_policy']=='boundary_hold17' and i in plan['held_positive_image_ids']:continue
            if selected:
                c=torch.load(CACHE/(i+'.pt'),map_location='cpu',weights_only=True);p.append(c['features'][-1,0,selected].double());pw.extend([1/len(selected)]*len(selected));positive_ids.append(i)
        pos=torch.cat(p);pw=torch.tensor(pw,dtype=torch.float64);pw/=pw.sum();X=torch.cat([pos,neg,roi]);y=torch.cat([torch.ones(len(pos)),torch.zeros(len(neg)+len(roi))]).double();weights=torch.cat([pw,nw,rw])
        theta,log=fit(X,y,weights,initial_theta,C,recipe['teacher_weight']);head={k:v.clone() for k,v in head0.items()};head['weight'][133].copy_(theta[:-1].float());head['bias'][133].copy_(theta[-1].float());inactive=[i for i in range(616) if i!=133];assert all(torch.equal(head[k][inactive],head0[k][inactive]) for k in head)
        i=recipe['index'];torch.save(head,out/f'head-{i}.pt');save(out/f'fit-{i}.json',dict(recipe,plan_sha256=sha(D/'LOCAL_CONTRAST_PLAN.json'),**log));heads.append(head);input_audit.append(dict(index=i,positive_image_ids=positive_ids,positive_queries=len(pos),negative_photos=len(n),negative_queries=len(neg),region_photos_with_covering_queries=len(region_features),region_queries=len(roi)))
        print(f'Fitted contrast head {i+1}/4 before inspecting any new validation outcome',flush=True)
    save(out/'TRAIN_INPUT_AUDIT.json',dict(variants=input_audit,new_region_query_coverage=region_coverage,all_training_only=True))
    val=[r for r in rows.values() if r['split']=='val'];baseline=read(FROZEN/'local-probes/validation-baseline.json');original=read(T/'inputs/validation-original.json');assert counts_equal(baseline,read(T/'inputs/validation-resume.json'));best=baseline;winner=None;summaries=[]
    for recipe,head in zip(recipes,heads):
        result,seconds=predict(val,head);i=recipe['index'];save(out/f'validation-{i}.json',result);ok=eligible(result,baseline) and eligible(result,original);strict=ok and ranking(result)>ranking(baseline) and ranking(result)>ranking(original)
        if strict and ranking(result)>ranking(best):best=result;winner=i
        b=result['per_class']['133'];item=dict(recipe,eligible=ok,strict_gain=bool(strict),billboard_hits=b['complete_tp']+b['partial_hits'],billboard_complete_fp=b['complete_fp'],unscored_predictions=result['metrics']['unscored_predictions'],ranking=list(ranking(result)),validation_seconds=seconds);summaries.append(item);print(json.dumps(item),flush=True)
    assert sha(T/'inputs/selected-7805570.pt')==source_hash and sha(T/'release/candidate-manifest-v2.json')==release_hash
    save(out/'RECEIPT.json',dict(status='four-local-contrast-probes-complete',selected_index=winner,trials=summaries,plan_sha256=sha(D/'LOCAL_CONTRAST_PLAN.json'),all_four_fits_before_new_validation=True,original_release_and_checkpoint_unchanged=True,validation_and_test_images_used_as_training=False,selection_policy_unchanged=True,new_GPU_jobs=0,production_adoption=False,strict_ONNX_hold=True,independent_fresh_test_available=False))
if __name__=='__main__':run()
