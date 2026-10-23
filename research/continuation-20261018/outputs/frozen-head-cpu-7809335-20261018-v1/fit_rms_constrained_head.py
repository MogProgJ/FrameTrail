"""One training-RMS-constrained local head; dual parameter never uses validation."""
import json,math,time
from cache_engine import *
from build_cache import save
from run_local_probes import CACHE,predict
from fit_teacher_preserved_probes import fit
from continuation_guard import read,sha
from selection_policy import eligible,ranking
def run():
    OUT=HERE/'rms-constrained';OUT.mkdir(exist_ok=False)
    plan=dict(status='frozen-before-constrained-fit-and-validation',unknown_training_logit_RMS_bound=.1,dual_search='Start lambda10, multiply10 until feasible, then12geometric bisection fits; choose lowest feasible multiplier using training covariance only. Max16fits; every fit has the existing200iteration/120second cap.',parameter_ridge=.0001,data_objective='Same37covered positives,35explicit-absence photos and8reviewed sign regions at masses1,3,3.',validation='Evaluate exactly one final feasible head on135development images; unchanged both-baseline retention/FP/unscored530 gate and strict gain. Never use validation to select multiplier.',new_labels_or_threshold_changes=False,new_GPU_jobs=0,limits='RMS0.1is a conservative local engineering choice, not a per-query bound or a guarantee of drift/accuracy. This remains development exploration; no independent accuracy claim.')
    save(OUT/'PLAN.json',plan);torch.set_num_threads(2);torch.manual_seed(17);torch.use_deterministic_algorithms(True)
    stats=torch.load(HERE/'teacher-preservation/training-statistics.pt',map_location='cpu',weights_only=True);C=stats['covariance'];pos=[];pw=[]
    for item in read(HERE/'TRAIN_FEATURE_COVERAGE.json')['coverage']:
        q=item['selected_queries']
        if q:
            c=torch.load(CACHE/(item['image_id']+'.pt'),map_location='cpu',weights_only=True);pos.append(c['features'][-1,0,q].double());pw.extend([1/len(q)]*len(q))
    negative=[]
    for image_id in read(TOOLS/'sampling-pools.json')['explicit_negative']:
        c=torch.load(CACHE/(image_id+'.pt'),map_location='cpu',weights_only=True);negative.append(c['features'][-1,0].double())
    roi=[];rw=[]
    for _,features in sorted(stats['reviewed_roi_features'].items()):roi.append(features.double());rw.extend([1/len(features)]*len(features))
    p=torch.cat(pos);n=torch.cat(negative);r=torch.cat(roi);pw=torch.tensor(pw,dtype=torch.float64);pw/=pw.sum();rw=torch.tensor(rw,dtype=torch.float64);rw/=rw.sum()
    X=torch.cat([p,n,r]);y=torch.cat([torch.ones(len(p)),torch.zeros(len(n)+len(r))]).double();weights=torch.cat([pw,torch.full((len(n),),3/len(n),dtype=torch.float64),3*rw]);h0=torch.load(CACHE/'initial-head.pt',map_location='cpu',weights_only=True);t0=torch.cat([h0['weight'][133],h0['bias'][133:134]]).double()
    trace=[]
    def train(strength):
        theta,log=fit(X,y,weights,t0,C,strength);d=theta-t0;rms=math.sqrt(max(0,float(d@C@d)));trace.append(dict(teacher_weight=strength,RMS=rms,feasible=rms<=.1,iterations=log['iterations'],seconds=log['seconds']));print(json.dumps(trace[-1]),flush=True);return theta,rms
    lo=10.;theta,rms=train(lo);hi=lo
    for _ in range(3):
        if rms<=.1:break
        lo=hi;hi*=10;theta,rms=train(hi)
    assert rms<=.1,'Feasible bound not found within declared training-only search'
    selected=theta
    for _ in range(12):
        mid=math.sqrt(lo*hi);theta,rms=train(mid)
        if rms<=.1:hi=mid;selected=theta
        else:lo=mid
    d=selected-t0;assert math.sqrt(float(d@C@d))<=.1
    head={k:v.clone() for k,v in h0.items()};head['weight'][133].copy_(selected[:-1].float());head['bias'][133].copy_(selected[-1].float());inactive=[i for i in range(616) if i!=133];assert all(torch.equal(head[k][inactive],h0[k][inactive]) for k in head)
    torch.save(head,OUT/'HEAD.pt');save(OUT/'TRAINING_SELECTION.json',dict(multiplier=hi,logit_RMS=math.sqrt(float(d@C@d)),trace=trace,validation_used=False))
    val=[r for r in read(TOOLS/'release/candidate-manifest-v2.json')['images'] if r['split']=='val'];baseline=read(HERE/'local-probes/validation-baseline.json');original=read(TOOLS/'inputs/validation-original.json');result,seconds=predict(val,head);save(OUT/'validation.json',result)
    ok=eligible(result,baseline) and eligible(result,original);gain=ok and ranking(result)>ranking(baseline) and ranking(result)>ranking(original);b=result['per_class']['133']
    receipt=dict(status='one-training-RMS-constrained-head-development-checked',eligible=ok,strict_gain=bool(gain),billboard_known_hits=b['complete_tp']+b['partial_hits'],billboard_complete_fp=b['complete_fp'],unscored_predictions=result['metrics']['unscored_predictions'],ranking=list(ranking(result)),training_multiplier=hi,training_logit_RMS=math.sqrt(float(d@C@d)),head_sha256=sha(OUT/'HEAD.pt'),validation_seconds=seconds,new_GPU_jobs=0,production_adoption=False,strict_ONNX_hold_not_waived=True)
    save(OUT/'RECEIPT.json',receipt);print(json.dumps(receipt,indent=2))
if __name__=='__main__':run()
