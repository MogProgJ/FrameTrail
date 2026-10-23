"""Eight predeclared CPU linear probes, trained on existing training labels only."""
import json,time
from pathlib import Path
from cache_engine import *
from continuation_guard import read,sha,counts_equal
from scoped_metrics import iou
from selection_policy import evaluate,eligible,ranking
from scipy.optimize import linear_sum_assignment
CACHE=HERE/'cache-full-layout'

def save(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,indent=2,allow_nan=False)
def xyxy(box):
    x,y,w,h=box;return [x-w/2,y-h/2,x+w/2,y+h/2]
def predict(rows,head):
    predictions={};started=time.perf_counter()
    for row in rows:
        cached=torch.load(CACHE/(row['image_id']+'.pt'),map_location='cpu',weights_only=True)
        with torch.no_grad():outputs=replay(cached,head['weight'],head['bias'])
        predictions[row['image_id']]=decode(outputs,row['width'],row['height'])
    return evaluate(rows,predictions),time.perf_counter()-started

def fit(features,labels,weights,initial,ridge):
    theta=initial.clone().requires_grad_(True);started=time.perf_counter();history=[]
    opt=torch.optim.LBFGS([theta],lr=1,max_iter=200,max_eval=250,tolerance_grad=1e-7,tolerance_change=1e-10,line_search_fn='strong_wolfe')
    def closure():
        if time.perf_counter()-started>120:raise RuntimeError('Predeclared local fit time cap reached')
        opt.zero_grad(set_to_none=True)
        logits=features@theta[:-1]+theta[-1]
        data_loss=(F.binary_cross_entropy_with_logits(logits,labels,reduction='none')*weights).sum()
        anchor=.5*ridge*(theta-initial).square().sum();total=data_loss+anchor
        if not torch.isfinite(total):raise ValueError('Nonfinite local objective')
        total.backward();history.append(dict(objective=float(total.detach()),data_loss=float(data_loss.detach()),anchor=float(anchor.detach()),gradient_norm=float(theta.grad.norm())))
        return total
    opt.step(closure)
    assert torch.isfinite(theta).all()
    return theta.detach(),dict(optimizer='CPU float64 full-batch LBFGS',iterations=opt.state[theta]['n_iter'],function_evaluations=len(history),seconds=time.perf_counter()-started,history=history)

def run():
    torch.set_num_threads(2);torch.manual_seed(17);torch.use_deterministic_algorithms(True)
    plan=read(HERE/'LOCAL_EXPERIMENT_PLAN.json');receipt=read(HERE/'CACHE_RECEIPT_FULL_LAYOUT.json');assert receipt['plan_sha256']==sha(HERE/'LOCAL_EXPERIMENT_PLAN.json')
    release=read(TOOLS/'release/candidate-manifest-v2.json');pools=read(TOOLS/'sampling-pools.json');rows={r['image_id']:r for r in release['images']};index=read(HERE/'CACHE_INDEX_FULL_LAYOUT.json')
    for image_id,row in index.items():assert sha(CACHE/(image_id+'.pt'))==row['cache_sha256']
    initial_head=torch.load(CACHE/'initial-head.pt',map_location='cpu',weights_only=True);initial=torch.cat([initial_head['weight'][133],initial_head['bias'][133:134]]).double()
    positives=[];positive_weights=[];negative=[];coverage=[]
    for image_id in pools['billboard']:
        row=rows[image_id];cached=torch.load(CACHE/(image_id+'.pt'),map_location='cpu',weights_only=True)
        pred=[list(map(lambda v:max(0.,min(1.,v)),xyxy(box))) for box in cached['boxes'][-1,0].tolist()]
        target=[xyxy(t['normalized_cxcywh']) for t in row['targets'] if t['canonical_id']==133]
        overlaps=torch.tensor([[iou(p,t) for t in target] for p in pred],dtype=torch.float64)
        query_ids,target_ids=linear_sum_assignment(-overlaps.numpy());selected=[int(q) for q,t in zip(query_ids,target_ids) if overlaps[q,t]>=.5]
        coverage.append(dict(image_id=image_id,known_targets=len(target),covered_targets=len(selected),selected_queries=selected))
        if selected:
            positives.append(cached['features'][-1,0,selected].double());positive_weights.extend([1/len(selected)]*len(selected))
    for image_id in pools['explicit_negative']:
        assert rows[image_id]['scope'].get('133')=='absent' and rows[image_id]['split']=='train'
        cached=torch.load(CACHE/(image_id+'.pt'),map_location='cpu',weights_only=True);negative.append(cached['features'][-1,0].double())
    pos=torch.cat(positives);neg=torch.cat(negative)
    pw=torch.tensor(positive_weights,dtype=torch.float64);pw/=pw.sum()
    features=torch.cat([pos,neg]);labels=torch.cat([torch.ones(len(pos)),torch.zeros(len(neg))]).double()
    addendum=read(HERE/'HARD_NEGATIVE_ADDENDUM.json');assert addendum['local_trials']==8
    negative_uniform=torch.full((len(neg),),3/len(neg),dtype=torch.float64)
    teacher=[];teacher_hashes=[]
    base=HERE.parent/'billboard-batch-proposal-7805570-20261018-v1/retrieval-7809335'
    for i in range(4):
        path=base/f'task-{i}/verified-7809335_{i}/output/rf-billboard-batch-7809335_{i}/last.pt'
        ck=torch.load(path,map_location='cpu',weights_only=True);state=ck['model_state_dict']
        teacher.append(state['class_embed.weight'][133].double().clone());teacher_hashes.append(sha(path));del ck,state
    teacher_mean=torch.stack(teacher).mean(0)
    hard=.5*negative_uniform.clone();mined=[]
    for i,image_id in enumerate(pools['explicit_negative']):
        q=torch.argsort(negative[i]@teacher_mean,descending=True,stable=True)[:20]
        hard[i*300+q]+=.5*3/(35*20)
        mined.append(dict(image_id=image_id,query_indices=q.tolist()))
    assert abs(float(hard.sum())-3)<1e-10
    weight_schemes=[torch.cat([pw,negative_uniform]),torch.cat([pw,hard])]
    recipes=[dict(index=i*4+j,weighting='uniform' if i==0 else 'half-hard-negative',ridge=ridge) for i in range(2) for j,ridge in enumerate(plan['ridge_strengths'])]
    save(HERE/'TRAIN_HARD_NEGATIVE_MINING.json',dict(training_only=True,teachers='equal mean of all four rejected last rows; no validation-based teacher choice',teacher_sha256=teacher_hashes,photos=35,top_queries_per_photo=20,negative_weight_mass=float(hard.sum()),mined=mined))
    save(HERE/'TRAIN_FEATURE_COVERAGE.json',dict(training_photos=55,positive_photos=20,explicit_negative_photos=35,known_positive_targets=sum(r['known_targets'] for r in coverage),covered_positive_targets=len(pos),explicit_negative_query_features=len(neg),training_rows_only=True,coverage=coverage))
    out=HERE/'local-probes';out.mkdir(exist_ok=False)
    trained=[]
    # Fit all predeclared candidates before inspecting any new validation outcome.
    for recipe in recipes:
        trial=recipe['index'];ridge=recipe['ridge'];weights=weight_schemes[trial//4]
        theta,log=fit(features,labels,weights,initial,ridge)
        head={k:v.clone() for k,v in initial_head.items()};head['weight'][133].copy_(theta[:-1].float());head['bias'][133].copy_(theta[-1].float())
        inactive=[i for i in range(616) if i!=133]
        assert all(torch.equal(head[k][inactive],initial_head[k][inactive]) for k in head)
        torch.save(head,out/f'head-{trial}.pt');save(out/f'fit-{trial}.json',dict(recipe,training_feature_count=len(features),plan_sha256=sha(HERE/'LOCAL_EXPERIMENT_PLAN.json'),addendum_sha256=sha(HERE/'HARD_NEGATIVE_ADDENDUM.json'),only_row133_changed=True,**log))
        trained.append(head);print(f'Fitted local probe {trial+1}/8: {recipe}; train objective only; no validation used',flush=True)
    val=[r for r in release['images'] if r['split']=='val'];original=read(TOOLS/'inputs/validation-original.json');current=read(TOOLS/'inputs/validation-resume.json')
    baseline,seconds=predict(val,initial_head);save(out/'validation-baseline.json',baseline)
    assert counts_equal(baseline,current),'Cached CPU validation baseline differs from the pinned selected GPU counts; hold local selection'
    records=[];best=baseline;selected=None
    for trial,head in enumerate(trained):
        result,seconds=predict(val,head);save(out/f'validation-{trial}.json',result)
        ok=eligible(result,baseline) and eligible(result,original);strict=ok and ranking(result)>ranking(best) and ranking(result)>ranking(original)
        if strict:best=result;selected=trial
        bill=result['per_class']['133'];washer=result['per_class']['593']
        record=dict(recipes[trial],eligible=ok,strict_gain=bool(strict),billboard_known_hits=bill['complete_tp']+bill['partial_hits'],billboard_complete_fp=bill['complete_fp'],unscored_predictions=result['metrics']['unscored_predictions'],washing_known_hits=washer['complete_tp']+washer['partial_hits'],ranking=list(ranking(result)),validation_replay_seconds=seconds)
        records.append(record);print(json.dumps(record),flush=True)
    save(HERE/'LOCAL_PROBE_RECEIPT.json',dict(status='eight-local-training-only-fits-development-checked',plan_sha256=sha(HERE/'LOCAL_EXPERIMENT_PLAN.json'),addendum_sha256=sha(HERE/'HARD_NEGATIVE_ADDENDUM.json'),selected_index=selected,trials=records,cache_baseline_matches_current_GPU_counts=True,all_other_classifier_rows_unchanged=True,all_features_boxes_and_other_model_state_untouched=True,full_model_inference_during_fits=False,new_cluster_jobs=0,production_adoption=False,independent_fresh_test_available=False,strict_ONNX_hold_not_waived=True))
if __name__=='__main__':run()
