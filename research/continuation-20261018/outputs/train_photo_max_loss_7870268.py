"""Eight fixed TRAIN-only CPU capacity diagnostics; no detector model is retained."""
import os, sys, json, hashlib, time, argparse, copy
from pathlib import Path
ROOT=Path(r'C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation')
OUT=ROOT/'outputs'; DEST=OUT/'train-photo-max-loss-7870268-20261022-v1'
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
    parent=OUT/'train-discrimination-full-query-7870268-20261022-v1'
    prior=read(parent/'PLAN_V3.json');completed=read(parent/'REPORT.json')
    assert completed['fits']==8
    save(DEST/'AUTHORIZATION.json',dict(date='2026-10-22',status='explicit-separate-photo-level-loss-study-authorized',
        user_reply='Run the eight-fit photo-level loss study (recommended)',
        exact_scope='Eight new fixed CPU fits; positive-photo mean softplus + absent-photo max300logit softplus; same TRAINfolds/features/normalization/models/160updates/1800s2CPUcap;noVAL/TEST/GPU/deployment.',
        proposal_ref=dict(path=str(parent/'NEXT_OBJECTIVE_STUDY_PROPOSAL.md'),sha256=sha(parent/'NEXT_OBJECTIVE_STUDY_PROPOSAL.md')),
        parent_receipt_sha256=sha(parent/'COMPLETION_RECEIPT.json')))
    records=torch.load(linked(prior['features_ref']),map_location='cpu',weights_only=True)['records']
    assert all(len(r['train'])==300 for r in records.values() if not r['y'])
    folds=read(parent/'FOLDS_V2.json');save(DEST/'FOLDS.json',folds)
    assignments=read(parent/'TRAIN_ASSIGNMENTS.json');save(DEST/'TRAIN_ASSIGNMENTS.json',assignments)
    current=copy.deepcopy(prior);current['source']['script_sha256']=sha(Path(__file__))
    current['source']['parent_control_script']=dict(path=str(OUT/'train_discrimination_full_query_7870268.py'),sha256=sha(OUT/'train_discrimination_full_query_7870268.py'))
    current['folds_sha256']=sha(DEST/'FOLDS.json');current['folds_file']='FOLDS.json';current['assignments_sha256']=sha(DEST/'TRAIN_ASSIGNMENTS.json')
    current['scope']='Distinct eight-fit photo-level max-negative objective diagnostic; no detector selection or deployable model'
    current['loss']='0.5*mean_over_positive_photos(mean_over_known_covered_positive_queries softplus(-logit)) +0.5*mean_over_absent_photos softplus(max_over_all300_query_logits)'
    current['negative_policy']='All300 fitting-absent query logits enter differentiable max; only maximal query receives active max gradient on a step. Baseline-hard/rest membership is historical instrumentation, not negative loss weighting.'
    current['balance']='Each class mass0.5; equal photo mass within class; positives mean query loss; absent photos max-logit loss.'
    current['single_treatment']='Photo-level max-negative aggregation replaces weighted query-average negative BCE; positive objective and all other controls unchanged.'
    current['bce_controls']={f'{fold}-{kind}':dict(path=str(parent/f'fits/fold-{fold}-{kind}.json'),sha256=sha(parent/f'fits/fold-{fold}-{kind}.json')) for fold in range(4) for kind in current['models']}
    current['objective_support_rule']='For a method, all4paired heldTRAINfolds must have hits>=its frozen BCE control and alarmed absentphotos<=control at fitting-only zero-alarm criterion, with at leastone strict count improvement. AP is reported, not a new objective gate. No model promotion.'
    current['post_control_stop_rule']='After8fits, stop automatic loss/capacity/query-sampling fits regardless of outcome. If no consistent clean support, prepare broader representation/supervision strategy decision, not another grid.'
    current['parent_study_ref']=dict(plan_sha256=sha(parent/'PLAN_V3.json'),report_sha256=sha(parent/'REPORT.json'),receipt_sha256=sha(parent/'COMPLETION_RECEIPT.json'))
    current['changes_from_prior_probe'].append('Explicitly authorized photo-level max-negative loss study; prior BCE controls reused without refitting.')
    save(DEST/'PLAN.json',current)
    print(json.dumps(dict(status='photo-max-loss-study-frozen-before-fits',fits=8,all_other_controls_identical=True,optimizer_updates=0),indent=2),flush=True)

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
    started=time.monotonic();plan=read(DEST/'PLAN.json');folds=read(DEST/'FOLDS.json')
    assert plan['status']=='frozen-before-eight-new-fits' and plan['source']['script_sha256']==sha(Path(__file__))
    assert plan['folds_sha256']==sha(DEST/'FOLDS.json') and plan['assignments_sha256']==sha(DEST/'TRAIN_ASSIGNMENTS.json')
    records=torch.load(linked(plan['features_ref']),map_location='cpu',weights_only=True)['records']
    results=[]
    try:
        for fold,held_ids in enumerate(folds['held_photo_ids']):
            train_ids=sorted(set(records)-set(held_ids))
            assert not {records[i]['identity'] for i in train_ids}&{records[i]['identity'] for i in held_ids}
            assert not {records[i]['scene'] for i in train_ids}&{records[i]['scene'] for i in held_ids}
            x=torch.cat([records[i]['train'] for i in train_ids]);y=torch.cat([torch.full((len(records[i]['train']),),float(records[i]['y'])) for i in train_ids])
            positive_photos=sum(records[i]['y'] for i in train_ids);negative_photos=len(train_ids)-positive_photos
            weights=torch.cat([torch.full((len(records[i]['train']),),.5/(positive_photos*len(records[i]['train']))) if records[i]['y'] else torch.zeros(len(records[i]['train'])) for i in train_ids])
            assert abs(float(weights[y==1].sum())-.5)<1e-6 and float(weights[y==0].sum())==0
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
                    loss=(F.softplus(-logits[y==1])*weights[y==1]).sum()+.5*F.softplus(logits[y==0].reshape(negative_photos,300).max(1).values).mean()
                    assert bool(torch.isfinite(loss));loss.backward();optimizer.step()
                with torch.inference_mode():
                    model.eval();train_logits=model(z).flatten();train_scores=train_logits.sigmoid()
                    calibration_scores=model(nz).flatten().sigmoid()
                    maximum=calibration_scores.max();threshold=torch.nextafter(maximum,torch.tensor(float('inf'))).item()
                    assert not bool((calibration_scores>=threshold).any())
                    # Held fold is scored after its operating threshold is locked.
                    scores=model(tz).flatten().sigmoid()
                zero=metrics(scores,ty,tids,threshold);fixed=metrics(scores,ty,tids,.5)
                row=dict(fold=fold,model=kind,updates=160,parameters=sum(p.numel() for p in model.parameters()),
                    train_photo_max_loss=float(loss.detach()),training_positive_query_recall_at_0_5=float((train_scores[y==1]>=.5).float().mean()),
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
                        positive_query_loss_weights=weights.tolist(),negative_photo_mass=.5/negative_photos,negative_aggregation='softplus(max300logits)',final_active_max_queries=train_logits[y==0].reshape(negative_photos,300).argmax(1).tolist()))
                save(run/f'fold-{fold}-{kind}.json',row)
                results.append(row)
                print(json.dumps({k:row[k] for k in ['fold','model','train_photo_max_loss','held_TRAIN_fold_fixed0_5','held_TRAIN_fold_training_zero_alarm']}),flush=True)
                del model,optimizer
        lookup={(r['fold'],r['model']):r for r in results};support=True;strict=False
        for fold in range(4):
            a=lookup[fold,'linear']['held_TRAIN_fold_training_zero_alarm'];b=lookup[fold,'mlp32']['held_TRAIN_fold_training_zero_alarm']
            support &= b['query_average_precision']>=a['query_average_precision'] and b['positive_hits']>=a['positive_hits'] and b['absent_photos_with_alarm']<=a['absent_photos_with_alarm']
            strict |= b['query_average_precision']>a['query_average_precision'] or b['positive_hits']>a['positive_hits'] or b['absent_photos_with_alarm']<a['absent_photos_with_alarm']
        assert len(results)==8
        objective_comparisons=[];supported_methods=[]
        for kind in plan['models']:
            clean=True;strict_improvement=False
            for fold in range(4):
                candidate=lookup[fold,kind]['held_TRAIN_fold_training_zero_alarm']
                reference=read(Path(plan['bce_controls'][f'{fold}-{kind}']['path']))['held_TRAIN_fold_training_zero_alarm']
                hit_delta=candidate['positive_hits']-reference['positive_hits'];alarm_delta=candidate['absent_photos_with_alarm']-reference['absent_photos_with_alarm']
                clean &= hit_delta>=0 and alarm_delta<=0
                strict_improvement |= hit_delta>0 or alarm_delta<0
                objective_comparisons.append(dict(fold=fold,model=kind,positive_hit_delta=hit_delta,absent_photo_alarm_delta=alarm_delta,AP_delta=candidate['query_average_precision']-reference['query_average_precision']))
            if clean and strict_improvement:supported_methods.append(kind)
        for ref in plan['bce_controls'].values():linked(ref)
        for r in plan['cache_refs']:linked(r)
        for key in ['inputs','initial_head','prior_probe','checkpoint']:linked(plan['source'][key])
        assert sha(Path(__file__))==plan['source']['script_sha256']
        report=dict(status='eight-fixed-TRAIN-only-fits-complete',fits=8,total_updates=1280,seconds=time.monotonic()-started,
            nonlinear_consistent_support_under_frozen_rule=bool(support and strict),objective_clean_support_methods=supported_methods,objective_vs_BCE_comparisons=objective_comparisons,
            validation_cache_reads=0,test_cache_reads=0,new_image_inference=0,new_cluster_jobs=0,models_saved=False,
            source_inputs_unchanged=True,production_adoption=False,plan_sha256=sha(DEST/'PLAN.json'),
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
