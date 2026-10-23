"""Four predeclared convex local heads with training-only teacher regularization."""
import json,time
from cache_engine import *
from build_cache import save
from run_local_probes import predict,CACHE
from continuation_guard import read,sha,counts_equal
from selection_policy import eligible,ranking
OUT=HERE/'teacher-preservation'
def fit(X,y,weights,initial,C,teacher_weight):
    theta=initial.clone().requires_grad_(True);started=time.perf_counter();history=[]
    opt=torch.optim.LBFGS([theta],lr=1,max_iter=200,max_eval=250,tolerance_grad=1e-7,tolerance_change=1e-10,line_search_fn='strong_wolfe')
    def closure():
        if time.perf_counter()-started>120:raise RuntimeError('Local teacher fit time cap')
        opt.zero_grad(set_to_none=True);delta=theta-initial;logits=X@theta[:-1]+theta[-1]
        data=(F.binary_cross_entropy_with_logits(logits,y,reduction='none')*weights).sum();preserve=.5*teacher_weight*(delta@C@delta);ridge=.5*.0001*delta.square().sum();total=data+preserve+ridge
        assert torch.isfinite(total);total.backward();history.append(dict(objective=float(total.detach()),data=float(data.detach()),preserve=float(preserve.detach()),ridge=float(ridge.detach()),gradient_norm=float(theta.grad.norm())));return total
    opt.step(closure);assert torch.isfinite(theta).all()
    return theta.detach(),dict(iterations=opt.state[theta]['n_iter'],evaluations=len(history),seconds=time.perf_counter()-started,history=history)
def run():
    torch.set_num_threads(2);torch.manual_seed(17);torch.use_deterministic_algorithms(True)
    plan=read(OUT/'PLAN.json');receipt=read(OUT/'STATISTICS_RECEIPT.json');assert receipt['plan_sha256']==sha(OUT/'PLAN.json') and receipt['statistics_sha256']==sha(OUT/'training-statistics.pt')
    stats=torch.load(OUT/'training-statistics.pt',map_location='cpu',weights_only=True);C=stats['covariance'];assert torch.allclose(C,C.T,atol=1e-12,rtol=0)
    pos=[];pw=[]
    for item in read(HERE/'TRAIN_FEATURE_COVERAGE.json')['coverage']:
        ids=item['selected_queries']
        if ids:
            cache=torch.load(CACHE/(item['image_id']+'.pt'),map_location='cpu',weights_only=True);pos.append(cache['features'][-1,0,ids].double());pw.extend([1/len(ids)]*len(ids))
    neg=[]
    for image_id in read(TOOLS/'sampling-pools.json')['explicit_negative']:
        cache=torch.load(CACHE/(image_id+'.pt'),map_location='cpu',weights_only=True);neg.append(cache['features'][-1,0].double())
    roi=[];rw=[]
    for image_id,features in sorted(stats['reviewed_roi_features'].items()):roi.append(features.double());rw.extend([1/len(features)]*len(features))
    p=torch.cat(pos);n=torch.cat(neg);r=torch.cat(roi);pw=torch.tensor(pw,dtype=torch.float64);pw/=pw.sum();rw=torch.tensor(rw,dtype=torch.float64);rw/=rw.sum()
    X=torch.cat([p,n,r]);y=torch.cat([torch.ones(len(p)),torch.zeros(len(n)+len(r))]).double();weights=torch.cat([pw,torch.full((len(n),),3/len(n),dtype=torch.float64),3*rw])
    head0=torch.load(CACHE/'initial-head.pt',map_location='cpu',weights_only=True);theta0=torch.cat([head0['weight'][133],head0['bias'][133:134]]).double();heads=[]
    for i,strength in enumerate(plan['teacher_weights']):
        theta,log=fit(X,y,weights,theta0,C,strength);head={k:v.clone() for k,v in head0.items()};head['weight'][133].copy_(theta[:-1].float());head['bias'][133].copy_(theta[-1].float())
        inactive=[k for k in range(616) if k!=133];assert all(torch.equal(head[k][inactive],head0[k][inactive]) for k in head)
        torch.save(head,OUT/f'head-{i}.pt');save(OUT/f'fit-{i}.json',dict(index=i,teacher_weight=strength,plan_sha256=sha(OUT/'PLAN.json'),**log));heads.append(head)
        print(f'Fitted teacher-preserved local head {i+1}/4; no development outcome inspected',flush=True)
    rows=[r for r in read(TOOLS/'release/candidate-manifest-v2.json')['images'] if r['split']=='val'];baseline=read(HERE/'local-probes/validation-baseline.json');original=read(TOOLS/'inputs/validation-original.json');assert counts_equal(baseline,read(TOOLS/'inputs/validation-resume.json'))
    best=baseline;selected=None;records=[]
    for i,head in enumerate(heads):
        result,seconds=predict(rows,head);save(OUT/f'validation-{i}.json',result);ok=eligible(result,baseline) and eligible(result,original);gain=ok and ranking(result)>ranking(best) and ranking(result)>ranking(original)
        if gain:best=result;selected=i
        bill=result['per_class']['133'];record=dict(index=i,teacher_weight=plan['teacher_weights'][i],eligible=ok,strict_gain=bool(gain),billboard_known_hits=bill['complete_tp']+bill['partial_hits'],billboard_complete_fp=bill['complete_fp'],unscored_predictions=result['metrics']['unscored_predictions'],ranking=list(ranking(result)),validation_seconds=seconds);records.append(record);print(json.dumps(record),flush=True)
    save(OUT/'RECEIPT.json',dict(status='four-teacher-preserved-local-probes-complete',selected_index=selected,trials=records,plan_sha256=sha(OUT/'PLAN.json'),only_training_data_in_objective=True,unknowns_not_labelled_negative=True,all_other_weights_features_boxes_and_data_labels_unchanged=True,new_GPU_jobs=0,production_adoption=False,strict_ONNX_hold_not_waived=True,independent_fresh_test_available=False))
if __name__=='__main__':run()
