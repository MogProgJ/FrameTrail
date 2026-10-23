"""Local, separately reviewed traffic-sign region contrast; original data unchanged."""
import hashlib,json,time
from cache_engine import *
from build_cache import WEIGHTS,save
from verify_cache_parity import fingerprint
from run_local_probes import fit,predict,xyxy,CACHE
from scoped_engine import build_model,load_sample
from continuation_guard import read,sha,counts_equal
from scoped_metrics import iou
from selection_policy import eligible,ranking
from determinism_policy import math_attention
REVIEWS={
 'ae470b502efe1304':'Foreground ROAD WORK warning panel. Distant businesses/background remain unknown.',
 'b9a8737cb91b7f6d':'Foreground octagonal STOP regulatory sign; no advertisement within this sign region.',
 '822a3cdf226995d7':'Foreground STOP panel. Banner and all background outside the panel remain unknown.',
 'baeb2e9d9a26baa5':'Triangular road-warning panel on pavement. Other signs/background remain unknown.',
 '865e5ad3d526c866':'Foreground STOP panel; regulatory traffic sign rather than an advertising board.',
 'd4d369f5f5f1fb43':'Handheld SLOW traffic-control paddle. Background buildings/advertisements remain unknown.',
 '6408ad432de00474':'Green Zzyzx Rd highway direction panel; road information, no advertisement in panel.',
 'ce924fe52d00e437':'Yellow school-crossing regulatory sign. Commercial wall/background remain unknown.'}
@math_attention()
def run():
    out=HERE/'reviewed-contrast';out.mkdir(exist_ok=False)
    release=read(TOOLS/'release/candidate-manifest-v2.json');rows={r['image_id']:r for r in release['images']};regions=[]
    for image_id,note in REVIEWS.items():
        row=rows[image_id];assert row['split']=='train' and row['scope'].get('133','unknown')=='unknown'
        targets=[t for t in row['targets'] if t['canonical_id'] in (571,11)];target=max(targets,key=lambda t:t['normalized_cxcywh'][2]*t['normalized_cxcywh'][3])
        regions.append(dict(image_id=image_id,image_sha256=row['image_sha256'],split='train',reviewer='assistant visual review of full original image',review_note=note,region=target['normalized_cxcywh'],existing_region_canonical_id=target['canonical_id'],new_supervision='billboard-negative queries only inside this reviewed traffic-sign region; NOT whole-image absence',query_minimum_IoU=.7))
    save(out/'REGION_REVIEW.json',dict(status='separate-training-only-region-overlay',original_manifest_sha256=sha(TOOLS/'release/candidate-manifest-v2.json'),original_labels_and_scopes_modified=False,independent_human_review=False,regions=regions))
    plan=dict(status='frozen-before-new-contrast-fit-or-validation',hypothesis='Additional reviewed training-sign contrast may teach billboard-vs-traffic-sign specificity that the35-image absence pool underrepresents.',source_of_new_regions='Eight existing TRAIN photos visually inspected by assistant; retain unknown billboard scope outside reviewed panels. No validation/test image or new downloaded photo used.',fit='Same positive/full-absence BCE as prior uniform probes; add mean per-reviewed-region negative BCE at weight3or10; anchor ridge1or10.',recipes=[dict(index=i,region_weight=rw,ridge=r) for i,(rw,r) in enumerate(((3.,1.),(3.,10.),(10.,1.),(10.,10.)))],selection='Fit allfour before evaluation. Same135development photos and both-baseline retention/FP/unscored530 guard, strict ranking gain; baseline and earlier recipe retain ties.',threshold=.35,annotation_limit='New assistant-reviewed region exclusions, not independently human verified. Original release/validation/heldout annotations remain untouched. Whole-image absence is not inferred.',new_GPU_jobs=0,production_adoption=False)
    save(out/'PLAN.json',plan)
    torch.set_num_threads(2);torch.manual_seed(17);torch.use_deterministic_algorithms(True)
    net=build_model(WEIGHTS,TOOLS/'rf-mapping.json').cpu().eval();loaded=torch.load(TOOLS/'inputs/selected-7805570.pt',map_location='cpu',weights_only=True);net.load_state_dict(loaded['model_state_dict']);del loaded
    for p in net.parameters():p.requires_grad_(False)
    before=fingerprint(net);roi_features=[];roi_weights=[];coverage=[]
    for r in regions:
        row=rows[r['image_id']];assert sha(TOOLS/'release'/row['source_path'])==r['image_sha256']
        image,_=load_sample(TOOLS/'release',row)
        with torch.no_grad():cached,live=capture(net,image,full=False);rebuilt=replay(cached,net.class_embed.weight,net.class_embed.bias)
        assert max_output_error(live,rebuilt)==0
        box=xyxy(r['region']);pred=[list(map(lambda v:max(0.,min(1.,v)),xyxy(b))) for b in cached['boxes'][-1,0].tolist()]
        ids=[i for i,b in enumerate(pred) if iou(b,box)>=.7]
        coverage.append(dict(image_id=r['image_id'],query_indices=ids,query_count=len(ids)))
        if ids:
            roi_features.append(cached['features'][-1,0,ids].double());roi_weights.extend([1/len(ids)]*len(ids))
    assert fingerprint(net)==before
    require_features=torch.cat(roi_features);roi_w=torch.tensor(roi_weights,dtype=torch.float64);roi_w/=roi_w.sum()
    save(out/'REGION_COVERAGE.json',dict(examples=coverage,query_features=len(require_features),all_eight_forward_errors_zero=True,model_state_unchanged=True))
    old_coverage=read(HERE/'TRAIN_FEATURE_COVERAGE.json')['coverage'];positive=[];pw=[]
    for item in old_coverage:
        ids=item['selected_queries']
        if ids:
            cached=torch.load(CACHE/(item['image_id']+'.pt'),map_location='cpu',weights_only=True);positive.append(cached['features'][-1,0,ids].double());pw.extend([1/len(ids)]*len(ids))
    pools=read(TOOLS/'sampling-pools.json');negative=[]
    for image_id in pools['explicit_negative']:
        cached=torch.load(CACHE/(image_id+'.pt'),map_location='cpu',weights_only=True);negative.append(cached['features'][-1,0].double())
    pos=torch.cat(positive);neg=torch.cat(negative);pw=torch.tensor(pw,dtype=torch.float64);pw/=pw.sum()
    features=torch.cat([pos,neg,require_features]);labels=torch.cat([torch.ones(len(pos)),torch.zeros(len(neg)+len(require_features))]).double()
    initial_head=torch.load(CACHE/'initial-head.pt',map_location='cpu',weights_only=True);initial=torch.cat([initial_head['weight'][133],initial_head['bias'][133:134]]).double();heads=[]
    for recipe in plan['recipes']:
        weights=torch.cat([pw,torch.full((len(neg),),3/len(neg),dtype=torch.float64),recipe['region_weight']*roi_w])
        theta,log=fit(features,labels,weights,initial,recipe['ridge']);head={k:v.clone() for k,v in initial_head.items()};head['weight'][133].copy_(theta[:-1].float());head['bias'][133].copy_(theta[-1].float())
        inactive=[i for i in range(616) if i!=133];assert all(torch.equal(head[k][inactive],initial_head[k][inactive]) for k in head)
        torch.save(head,out/f"head-{recipe['index']}.pt");save(out/f"fit-{recipe['index']}.json",dict(recipe,**log));heads.append(head)
        print(f"Fitted reviewed-region probe {recipe['index']+1}/4 without validation",flush=True)
    val=[r for r in release['images'] if r['split']=='val'];baseline=read(HERE/'local-probes/validation-baseline.json');current=read(TOOLS/'inputs/validation-resume.json');original=read(TOOLS/'inputs/validation-original.json');assert counts_equal(baseline,current)
    best=baseline;selected=None;records=[]
    for recipe,head in zip(plan['recipes'],heads):
        result,seconds=predict(val,head);save(out/f"validation-{recipe['index']}.json",result);ok=eligible(result,baseline) and eligible(result,original);strict=ok and ranking(result)>ranking(best) and ranking(result)>ranking(original)
        if strict:best=result;selected=recipe['index']
        bill=result['per_class']['133'];record=dict(recipe,eligible=ok,strict_gain=bool(strict),billboard_known_hits=bill['complete_tp']+bill['partial_hits'],billboard_complete_fp=bill['complete_fp'],unscored_predictions=result['metrics']['unscored_predictions'],ranking=list(ranking(result)),validation_seconds=seconds);records.append(record);print(json.dumps(record),flush=True)
    save(out/'RECEIPT.json',dict(status='reviewed-training-region-local-probes-complete',plan_sha256=sha(out/'PLAN.json'),selected_index=selected,trials=records,original_data_labels_and_scopes_unchanged=True,new_region_overlay_assistant_reviewed=True,validation_or_test_used_in_training=False,all_other_model_weights_unchanged=True,new_GPU_jobs=0,production_adoption=False,strict_ONNX_hold_not_waived=True))
if __name__=='__main__':run()
