"""Eight fixed TRAIN-only CPU capacity diagnostics; no detector model is retained."""
import os, sys, json, hashlib, time, argparse, copy
from pathlib import Path
ROOT=Path(r'C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation')
OUT=ROOT/'outputs'; DEST=OUT/'train-discrimination-full-query-7870268-20261022-v1'
C=OUT/'fresh-paired-controls-20261021-v1'
BATCH=OUT/'fresh-selector-batch-20261022-v1'
T=OUT/'selector-batch-proposal-7809335-20261018-v1/rf-selector-a77d9663-v1'
sys.path[:0]=[str(T),str(OUT/'frozen-head-cpu-7809335-20261018-v1')]
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',DO_NOT_TRACK='1')
import torch
import torch.nn.functional as F
from cache_engine import replay
from rfdetr.utilities import box_ops
from scipy.optimize import linear_sum_assignment
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,v):
    with Path(p).open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(v,indent=2,allow_nan=False)+'\n')
def linked(ref):
    assert sha(ref['path'])==ref['sha256'],ref['path']
    return Path(ref['path'])
def setup():
    assert str(torch.__version__)=='2.8.0+cpu'
    torch.set_num_threads(2);torch.manual_seed(17);torch.use_deterministic_algorithms(True)


def prepare():
    setup();DEST.mkdir(exist_ok=False)
    parent=OUT/'train-discrimination-7870268-20261022-v1'
    prior=read(parent/'PLAN_V2.json');completed=read(parent/'REPORT.json')
    assert completed['fits']==8 and not completed['nonlinear_consistent_support_under_frozen_rule']
    save(DEST/'AUTHORIZATION.json',dict(date='2026-10-22',status='explicit-separate-eight-fit-control-authorized',
        user_reply='Run the eight-fit full-query control (recommended)',
        exact_scope='Eight additional fixed CPU fits; all300 fitting-absent queries; same recorded scene/identity folds, weights, settings and1800s cap; noVAL/TEST/GPU/deployment.',
        proposal_ref=dict(path=str(parent/'FULL_QUERY_CONTROL_PROPOSAL.md'),sha256=sha(parent/'FULL_QUERY_CONTROL_PROPOSAL.md')),
        parent_receipt_sha256=sha(parent/'COMPLETION_RECEIPT.json')))
    records=torch.load(linked(prior['features_ref']),map_location='cpu',weights_only=True)['records']
    head=torch.load(linked(prior['source']['initial_head']),map_location='cpu',weights_only=True)
    original_assign=read(parent/'TRAIN_ASSIGNMENTS.json');assign=copy.deepcopy(original_assign)
    byid={r['image_id']:r for r in assign};cache_refs={r['image_id']:r for r in prior['cache_refs']}
    for iid,r in records.items():
        if r['y']:continue
        value=torch.load(linked(cache_refs[iid]),map_location='cpu',weights_only=True);cache=value.get('cache',value)
        scores=replay(cache,head['weight'],head['bias'])['pred_logits'][0,:,133]
        hard=scores.argsort(descending=True,stable=True)[:32].tolist();rest=[q for q in range(300) if q not in hard]
        uniform=[rest[round(k*(len(rest)-1)/31)] for k in range(32)]
        assert sorted(hard+uniform)==r['train_queries']==byid[iid]['train_query_indices']
        r['prior_sample_queries']=r['train_queries'];r['baseline_hard_queries']=hard
        r['train']=r['eval'].clone();r['train_queries']=list(range(300))
        r['query_mass']=torch.full((300,),.5/268);r['query_mass'][hard]=.5/32
        assert abs(float(r['query_mass'].sum())-1)<1e-6
        assert abs(float(r['query_mass'][hard].sum())-.5)<1e-6 and abs(float(r['query_mass'][rest].sum())-.5)<1e-6
        byid[iid]['prior_sample_queries']=byid[iid]['train_query_indices'];byid[iid]['train_query_indices']=list(range(300))
        byid[iid]['baseline_hard_queries']=hard;byid[iid]['within_photo_query_mass']=r['query_mass'].tolist()
    save(DEST/'TRAIN_ASSIGNMENTS.json',assign)
    folds=read(parent/'FOLDS_V2.json');save(DEST/'FOLDS_V2.json',folds)
    torch.save(dict(records=records),DEST/'TRAIN_FEATURES.pt')
    current=copy.deepcopy(prior)
    current['source']['script_sha256']=sha(Path(__file__))
    current['source']['parent_study_script']=dict(path=str(OUT/'train_discrimination_study_7870268.py'),sha256=sha(OUT/'train_discrimination_study_7870268.py'))
    current['features_ref']=dict(path=str(DEST/'TRAIN_FEATURES.pt'),sha256=sha(DEST/'TRAIN_FEATURES.pt'))
    current['assignments_sha256']=sha(DEST/'TRAIN_ASSIGNMENTS.json');current['folds_sha256']=sha(DEST/'FOLDS_V2.json')
    assert sha(DEST/'FOLDS_V2.json')==sha(parent/'FOLDS_V2.json')
    current['negative_policy']='All300 fitting-absent queries.32 unchanged baseline-hard queries receive half each photo mass; all268others share half. Held/evaluation/calibration retainall300.'
    current['balance']='Each class mass0.5; equal photo mass within class; positives equal query mass; negatives hard/rest0.5/0.5.'
    current['scope']='Separate eight-fit complete-negative-query control; no detector selection or deployable model'
    current['parent_study_ref']=dict(plan_sha256=sha(parent/'PLAN_V2.json'),report_sha256=sha(parent/'REPORT.json'),receipt_sha256=sha(parent/'COMPLETION_RECEIPT.json'))
    current['single_treatment']='Replace sampled32other queries by all268other queries while retaining hard32 and exact expected hard/rest,class,photo mass.'
    current['instrumentation']='Retain full fitting-negative query scores, query indices, hard membership and training loss weights; no fitted model saved.'
    current['changes_from_prior_probe'].append('Explicitly authorized full-query coverage control following completed64-query study;8additionalfits only.')
    current['post_control_stop_rule']='After8fits, no automatic further query-sampling/capacity fits; preserve failure or diagnostic support and prepare a distinct next research scope.'
    save(DEST/'PLAN_V2.json',current)
    print(json.dumps(dict(status='full-query-control-frozen-before-fits',fits=8,participating_photos=len(records),all_negative_queries=77*300,
        recorded_folds_identical=True,hard_rest_mass_verified=True,optimizer_updates=0),indent=2),flush=True)

def metrics(scores,labels,ids,threshold):
    order=torch.argsort(scores,descending=True,stable=True);ranked=labels[order].to(torch.float64)
    ap=float((ranked*ranked.cumsum(0)/torch.arange(1,len(ranked)+1,dtype=torch.float64)).sum()/ranked.sum())
    predicted=scores>=threshold;positive=labels==1;negative=labels==0
    pos_ids=sorted({i for i,y in zip(ids,labels.tolist()) if y==1});neg_ids=sorted({i for i,y in zip(ids,labels.tolist()) if y==0})
    macro=[];alarms=[]
    for iid in pos_ids:
        mask=torch.tensor([i==iid for i in ids]);macro.append(float(predicted[mask].float().mean()))
    for iid in neg_ids:
        mask=torch.tensor([i==iid for i in ids]);alarms.append(bool(predicted[mask].any()))
    return dict(query_average_precision=ap,threshold=float(threshold),positive_hits=int(predicted[positive].sum()),positive_queries=int(positive.sum()),
        negative_queries_positive=int(predicted[negative].sum()),negative_queries=int(negative.sum()),positive_photos=len(pos_ids),negative_photos=len(neg_ids),
        positive_query_recall=float(predicted[positive].to(torch.float64).mean()),positive_photo_macro_query_recall=sum(macro)/len(macro),
        absent_photos_with_alarm=sum(alarms),absent_photo_alarm_fraction=sum(alarms)/len(alarms))

def fit():
    setup();run=DEST/'fits';run.mkdir(exist_ok=False)
    started=time.monotonic();plan=read(DEST/'PLAN_V3.json');folds=read(DEST/'FOLDS_V2.json')
    assert plan['status']=='frozen-before-eight-new-fits' and plan['source']['script_sha256']==sha(Path(__file__))
    assert plan['folds_sha256']==sha(DEST/'FOLDS_V2.json') and plan['assignments_sha256']==sha(DEST/'TRAIN_ASSIGNMENTS.json')
    records=torch.load(linked(plan['features_ref']),map_location='cpu',weights_only=True)['records']
    results=[]
    try:
        for fold,held_ids in enumerate(folds['held_photo_ids']):
            train_ids=sorted(set(records)-set(held_ids))
            assert not {records[i]['identity'] for i in train_ids}&{records[i]['identity'] for i in held_ids}
            assert not {records[i]['scene'] for i in train_ids}&{records[i]['scene'] for i in held_ids}
            x=torch.cat([records[i]['train'] for i in train_ids]);y=torch.cat([torch.full((len(records[i]['train']),),float(records[i]['y'])) for i in train_ids])
            positive_photos=sum(records[i]['y'] for i in train_ids);negative_photos=len(train_ids)-positive_photos
            weights=torch.cat([(.5/(positive_photos if records[i]['y'] else negative_photos))*(torch.full((len(records[i]['train']),),1/len(records[i]['train'])) if records[i]['y'] else records[i]['query_mass']) for i in train_ids])
            assert abs(float(weights[y==1].sum())-.5)<1e-6 and abs(float(weights[y==0].sum())-.5)<1e-6
            normal=plan['frozen_fitting_normalization'][str(fold)];mean=torch.tensor(normal['mean']);std=torch.tensor(normal['std']);z=(x-mean)/std
            tx=torch.cat([records[i]['eval'] for i in held_ids]);ty=torch.cat([torch.full((len(records[i]['eval']),),float(records[i]['y'])) for i in held_ids])
            tids=[i for i in held_ids for _ in range(len(records[i]['eval']))];tz=(tx-mean)/std
            negative_train_ids=[i for i in train_ids if not records[i]['y']]
            nx=torch.cat([records[i]['eval'] for i in negative_train_ids]);nz=(nx-mean)/std
            for kind in plan['models']:
                torch.manual_seed(17)
                model=torch.nn.Linear(256,1) if kind=='linear' else torch.nn.Sequential(torch.nn.Linear(256,32),torch.nn.ReLU(),torch.nn.Linear(32,1))
                optimizer=torch.optim.AdamW(model.parameters(),lr=.003,weight_decay=.0001)
                for step in range(160):
                    if time.monotonic()-started>=1800:raise TimeoutError('Preserve partial eight-fit study; no budget extension or retry')
                    optimizer.zero_grad();logits=model(z).flatten()
                    loss=(F.binary_cross_entropy_with_logits(logits,y,reduction='none')*weights).sum()
                    assert bool(torch.isfinite(loss));loss.backward();optimizer.step()
                with torch.inference_mode():
                    model.eval();train_scores=model(z).flatten().sigmoid()
                    calibration_scores=model(nz).flatten().sigmoid()
                    maximum=calibration_scores.max();threshold=torch.nextafter(maximum,torch.tensor(float('inf'))).item()
                    assert not bool((calibration_scores>=threshold).any())
                    # Held fold is scored after its operating threshold is locked.
                    scores=model(tz).flatten().sigmoid()
                zero=metrics(scores,ty,tids,threshold);fixed=metrics(scores,ty,tids,.5)
                row=dict(fold=fold,model=kind,updates=160,parameters=sum(p.numel() for p in model.parameters()),
                    train_weighted_BCE=float(loss.detach()),training_positive_query_recall_at_0_5=float((train_scores[y==1]>=.5).float().mean()),
                    training_positive_query_recall_at_zero_alarm=float((train_scores[y==1]>=threshold).float().mean()),
                    held_TRAIN_fold_fixed0_5=fixed,held_TRAIN_fold_training_zero_alarm=zero,
                    normalization=dict(mean=mean.tolist(),std=std.tolist(),fit_photo_ids=train_ids),
                    calibration=dict(source='fitting-fold reviewed absent photos only; all300queries',photo_ids=negative_train_ids,
                        per_photo_max=calibration_scores.reshape(len(negative_train_ids),300).max(1).values.tolist(),
                        full_query_scores=calibration_scores.reshape(len(negative_train_ids),300).tolist(),
                        query_indices=list(range(300)),all_fitting_negative_queries_supervised=True,
                        baseline_hard_queries={i:records[i]['baseline_hard_queries'] for i in negative_train_ids},
                        maximum_negative_score=float(maximum),locked_threshold=threshold),
                    held_predictions=dict(scores=scores.tolist(),labels=ty.tolist(),image_ids=tids),
                    train_prediction_trace=dict(scores=train_scores.tolist(),labels=y.tolist(),
                        image_ids=[i for i in train_ids for _ in range(len(records[i]['train']))],
                        query_indices=[q for i in train_ids for q in records[i]['train_queries']],
                        loss_weights=weights.tolist()))
                save(run/f'fold-{fold}-{kind}.json',row)
                results.append(row)
                print(json.dumps({k:row[k] for k in ['fold','model','train_weighted_BCE','held_TRAIN_fold_fixed0_5','held_TRAIN_fold_training_zero_alarm']}),flush=True)
                del model,optimizer
        lookup={(r['fold'],r['model']):r for r in results};support=True;strict=False
        for fold in range(4):
            a=lookup[fold,'linear']['held_TRAIN_fold_training_zero_alarm'];b=lookup[fold,'mlp32']['held_TRAIN_fold_training_zero_alarm']
            support &= b['query_average_precision']>=a['query_average_precision'] and b['positive_hits']>=a['positive_hits'] and b['absent_photos_with_alarm']<=a['absent_photos_with_alarm']
            strict |= b['query_average_precision']>a['query_average_precision'] or b['positive_hits']>a['positive_hits'] or b['absent_photos_with_alarm']<a['absent_photos_with_alarm']
        assert len(results)==8
        for r in plan['cache_refs']:linked(r)
        for key in ['inputs','initial_head','prior_probe','checkpoint']:linked(plan['source'][key])
        assert sha(Path(__file__))==plan['source']['script_sha256']
        report=dict(status='eight-fixed-TRAIN-only-fits-complete',fits=8,total_updates=1280,seconds=time.monotonic()-started,
            nonlinear_consistent_support_under_frozen_rule=bool(support and strict),
            validation_cache_reads=0,test_cache_reads=0,new_image_inference=0,new_cluster_jobs=0,models_saved=False,
            source_inputs_unchanged=True,production_adoption=False,plan_sha256=sha(DEST/'PLAN_V3.json'),
            result_refs=[dict(path=str(run/f"fold-{r['fold']}-{r['model']}.json"),sha256=sha(run/f"fold-{r['fold']}-{r['model']}.json")) for r in results],
            limitations=['Exploratory TRAIN-only diagnostic after development history, not independent detector performance.',
                'Conditioned on frozen geometry-covered positive queries; no final decoder/NMS/other-class competition.',
                'Recorded scene/identity links disjoint, but exhaustive old cross-author scene clearance not claimed.',
                'TRAIN-fold calibrated thresholds are binary probe scores, not app thresholds or transferable confidence.',
                'No architecture/model selected or exported by these results.'])
        assert report['seconds']<1800
        save(DEST/'REPORT.json',report);print(json.dumps(report),flush=True)
    except BaseException as error:
        import traceback
        save(run/'FAILED.json',dict(error=str(error),traceback=traceback.format_exc(),completed_fits=len(results),seconds=time.monotonic()-started,preserve_no_retry=True))
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['prepare','fit']);args=parser.parse_args()
    if args.stage=='prepare':prepare()
    else:fit()
