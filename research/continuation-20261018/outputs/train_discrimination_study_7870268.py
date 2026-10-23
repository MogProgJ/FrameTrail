"""Eight fixed TRAIN-only CPU capacity diagnostics; no detector model is retained."""
import os, sys, json, hashlib, time, argparse, copy
from pathlib import Path
ROOT=Path(r'C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation')
OUT=ROOT/'outputs'; DEST=OUT/'train-discrimination-7870268-20261022-v1'
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
    save(DEST/'AUTHORIZATION.json',dict(status='explicit-new-scope-authorized',date='2026-10-22',
        user_reply='Run the separate TRAIN-only discrimination study (recommended)',
        question_scope='Eight bounded CPU diagnostic fits; no validation/TEST data; no deployed model.',
        proposal_ref=dict(path=str(BATCH/'NEXT_STUDY_SCOPE.md'),sha256=sha(BATCH/'NEXT_STUDY_SCOPE.md')),
        relationship='Separate study after completed no-winner7870268; not a retry/extension of the four conditions.',
        prior_experiment_receipt_sha256=sha(BATCH/'COMPLETION_RECEIPT_7870268.json')))
    raw=read(C/'INPUTS.json');rows=[r for r in raw['records'] if r['row']['split']=='train']
    assert len(rows)==124 and len({r['image_id'] for r in rows})==124
    assert all(r['pool'] in ['fresh_positive','old_positive','fresh_absent','old_absent'] for r in rows)
    assert all(r['row']['supervision']=='gold' and r['row'].get('scene_group') and r['row'].get('identity_group') for r in rows)
    source=dict(inputs=dict(path=str(C/'INPUTS.json'),sha256=sha(C/'INPUTS.json')),
        initial_head=raw['initial_head_ref'],prior_probe=dict(path=str(OUT/'training-strategy-20261019-v1/run_diagnostics.py'),sha256=sha(OUT/'training-strategy-20261019-v1/run_diagnostics.py')),
        checkpoint=dict(path=str(T/'inputs/selected-7805570.pt'),sha256=sha(T/'inputs/selected-7805570.pt')),
        script_sha256=sha(Path(__file__)))
    assert source['checkpoint']['sha256']=='c1e7b571476a9bdc02533359dfe3f599afab98822aa90df265e9068f43f46bd3'
    head=torch.load(linked(raw['initial_head_ref']),map_location='cpu',weights_only=True)
    records={}; assignments=[];cache_refs=[]
    for r in rows:
        row=r['row'];iid=r['image_id'];ref=r['cache_ref'];path=linked(ref)
        value=torch.load(path,map_location='cpu',weights_only=True);cache=value.get('cache',value)
        assert tuple(cache['features'].shape)==(3,1,300,256)
        x=cache['features'][-1,0].float();output=replay(cache,head['weight'],head['bias'])
        targets=[t['normalized_cxcywh'] for t in row['targets'] if t['canonical_id']==133]
        is_positive=r['pool'].endswith('positive')
        assert bool(targets)==is_positive
        if is_positive:
            overlaps=box_ops.box_iou(box_ops.box_cxcywh_to_xyxy(output['pred_boxes'][0]),box_ops.box_cxcywh_to_xyxy(torch.tensor(targets)))[0].numpy()
            q,t=linear_sum_assignment(-(overlaps>=.5).astype(float)-overlaps*1e-5)
            selected=sorted(int(query) for query,target in zip(q,t) if overlaps[query,target]>=.5)
            training=evaluation=x[selected];evaluation_queries=selected;train_queries=selected
        else:
            assert row['scope'].get('133')=='absent'
            scores=output['pred_logits'][0,:,133]
            hard=scores.argsort(descending=True,stable=True)[:32].tolist();rest=[i for i in range(300) if i not in hard]
            uniform=[rest[round(k*(len(rest)-1)/31)] for k in range(32)]
            train_queries=sorted(hard+uniform);evaluation_queries=list(range(300));selected=[]
            assert len(set(train_queries))==64
            training=x[train_queries];evaluation=x
        assignments.append(dict(image_id=iid,pool=r['pool'],targets=len(targets),positive_queries=selected,
            train_query_indices=train_queries,evaluation_query_indices=evaluation_queries,geometry_covered=len(selected),
            participates=len(training)>0,identity_group=row['identity_group'],scene_group=row['scene_group']))
        cache_refs.append(dict(image_id=iid,split='train',path=str(path),sha256=ref['sha256']))
        if len(training):records[iid]=dict(train=training.clone(),eval=evaluation.clone(),y=int(is_positive),
            identity=row['identity_group'],scene=row['scene_group'],pool=r['pool'],train_queries=train_queries,eval_queries=evaluation_queries)
    # Transitive union ensures the known cross-author Times Square merge also
    # keeps every other photo by a linked author in the same held fold.
    parent={r['image_id']:r['image_id'] for r in rows}
    def find(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    def union(a,b):
        a,b=find(a),find(b)
        if a!=b:parent[max(a,b)]=min(a,b)
    for key in ['identity_group','scene_group']:
        seen={}
        for r in rows:
            iid=r['image_id'];group=r['row'][key]
            if group in seen:union(iid,seen[group])
            else:seen[group]=iid
    groups={}
    for iid in records:groups.setdefault(find(iid),[]).append(iid)
    fold_ids=[[] for _ in range(4)];loads=[[0,0,0,0] for _ in range(4)];component_fold={}
    def group_counts(g):
        ids=groups[g];return [sum(len(records[i]['eval']) for i in ids if records[i]['y']),sum(records[i]['y'] for i in ids),sum(not records[i]['y'] for i in ids),sum(records[i]['pool']=='fresh_positive' for i in ids)]
    order=sorted(groups,key=lambda g:(-int(group_counts(g)[0]>0),-group_counts(g)[0],hashlib.sha256(('17|'+g).encode()).hexdigest()))
    for group in order:
        counts=group_counts(group);column=0 if counts[0] else 2
        fold=min(range(4),key=lambda f:(loads[f][column],loads[f][3] if counts[0] else sum(loads[f][1:3]),sum(loads[f]),f))
        component_fold[group]=fold;fold_ids[fold]+=sorted(groups[group]);loads[fold]=[a+b for a,b in zip(loads[fold],counts)]
    assert all(load[0]>0 and load[1]>0 and load[2]>0 for load in loads)
    for fold,ids in enumerate(fold_ids):
        other=set(records)-set(ids)
        assert not {records[i]['identity'] for i in ids}&{records[i]['identity'] for i in other}
        assert not {records[i]['scene'] for i in ids}&{records[i]['scene'] for i in other}
    fold_doc=dict(held_photo_ids=fold_ids,fold_load_columns=['positive_queries','positive_photos','absent_photos','fresh_positive_photos'],fold_loads=loads,
        components={g:dict(fold=component_fold[g],photo_ids=groups[g]) for g in groups},excluded_geometry_uncovered=[a['image_id'] for a in assignments if not a['participates']],
        recorded_scene_and_identity_disjoint=True,limitations='Enforces all recorded scene/identity links including old Times Square. Old cross-author scene exhaustiveness is not established; not independent held-out test accuracy.')
    save(DEST/'TRAIN_ASSIGNMENTS.json',assignments);save(DEST/'FOLDS.json',fold_doc)
    torch.save(dict(records=records),DEST/'TRAIN_FEATURES.pt')
    plan=dict(status='frozen-before-eight-new-fits',scope='TRAIN-only query discrimination; no detector selection or deployable model',
        models=['linear','mlp32'],folds=4,fits=8,updates_per_fit=160,max_total_updates=1280,threads=2,max_active_seconds=1800,
        optimizer=dict(name='AdamW',lr=.003,weight_decay=.0001,initialization_seed=17),
        normalization='Mean/std from fitting fold only; std clamp minimum0.1; same as prior probe.',
        balance='Each class total mass0.5; equal photo mass within class; equal query mass within photo.',
        positive_policy='Only one-to-one IoU>=0.5 baseline queries of known TRAIN billboard targets; no unmatched positive-photo query becomes negative.',
        negative_policy='Only reviewed whole-photo absent TRAIN scope;32 full-layout baseline-highest-logit queries plus32 evenly spaced other queries per fitting photo; evaluate all300.',
        metrics=['held TRAIN query AP','fixed0.5 positive recovery and absent-photo query alarms','held scores at threshold chosen only from fitting-fold negatives'],
        operating_criterion='Strictly above the maximum score across all300 queries of each fitting-fold absent photo. Zero fitting-fold absent-photo alarms; evaluate held fold once at this fixed threshold. No held-fold calibration.',
        nonlinear_support_rule='Across all4folds: queryAP nondecrease, held positive recovery nondecrease and held absent-photo alarm count nonincrease at the fitting-fold zero-alarm criterion; at least one strict improvement. Diagnostic support only; no model adoption.',
        changes_from_prior_probe=['Fresh TRAIN additions included.','Transitive recorded scene+identity grouping instead of identity alone.','Geometry assignment uses current reviewed targets.','Hard negatives ranked using full-layout replay.','Added predeclared fitting-fold zero-alarm criterion; fixed0.5 scores retained.','Budget1800s total, as authorized.'],
        source=source,features_ref=dict(path=str(DEST/'TRAIN_FEATURES.pt'),sha256=sha(DEST/'TRAIN_FEATURES.pt')),
        folds_sha256=sha(DEST/'FOLDS.json'),assignments_sha256=sha(DEST/'TRAIN_ASSIGNMENTS.json'),cache_refs=cache_refs,
        original_TRAIN_photos=124,participating_photos=len(records),positive_queries=sum(len(r['eval']) for r in records.values() if r['y']),
        validation_cache_reads=0,test_cache_reads=0,new_image_inference=0,production_adoption=False,models_saved=False)
    save(DEST/'PLAN.json',plan)
    print(json.dumps(dict(status=plan['status'],participating_photos=len(records),positive_queries=plan['positive_queries'],fold_loads=loads,excluded=fold_doc['excluded_geometry_uncovered']),indent=2),flush=True)

def refold():
    setup();assert not (DEST/'fits').exists()
    plan=read(DEST/'PLAN.json');folds=read(DEST/'FOLDS.json')
    records=torch.load(linked(plan['features_ref']),map_location='cpu',weights_only=True)['records']
    groups={g:v['photo_ids'] for g,v in folds['components'].items()}
    loads=[[0,0,0,0] for _ in range(4)];ids=[[] for _ in range(4)];components={}
    def counts(g):
        return [sum(len(records[i]['eval']) for i in groups[g] if records[i]['y']),sum(records[i]['y'] for i in groups[g]),sum(not records[i]['y'] for i in groups[g]),sum(records[i]['pool']=='fresh_positive' for i in groups[g])]
    order=sorted(groups,key=lambda g:(-int(counts(g)[0]>0),-counts(g)[0],hashlib.sha256(('17|'+g).encode()).hexdigest()))
    for g in order:
        count=counts(g)
        if count[3]:key=lambda f:(loads[f][3],loads[f][0],loads[f][1],f)
        elif count[0]:key=lambda f:(loads[f][0],loads[f][1],loads[f][3],f)
        else:key=lambda f:(loads[f][2],sum(loads[f][1:3]),f)
        fold=min(range(4),key=key);ids[fold]+=groups[g];loads[fold]=[a+b for a,b in zip(loads[fold],count)]
        components[g]=dict(fold=fold,photo_ids=groups[g])
    assert all(load[0]>0 and load[1]>0 and load[2]>0 and load[3]>0 for load in loads)
    for held in ids:
        train=set(records)-set(held)
        assert not {records[i]['identity'] for i in held}&{records[i]['identity'] for i in train}
        assert not {records[i]['scene'] for i in held}&{records[i]['scene'] for i in train}
    folds.update(held_photo_ids=ids,fold_loads=loads,components=components)
    save(DEST/'FOLDS_V2.json',folds)
    plan['folds_sha256']=sha(DEST/'FOLDS_V2.json');plan['folds_file']='FOLDS_V2.json'
    plan['source']['script_sha256']=sha(Path(__file__))
    plan['prefit_metadata_revision']=dict(original_plan_sha256=sha(DEST/'PLAN.json'),original_folds_sha256=sha(DEST/'FOLDS.json'),
        reason='Initial query-balanced fold0 held no fresh positive photo. Revised balance gives fresh positive counts priority within fresh-positive components before any fit or prediction; recorded scene/identity groups unchanged.',
        prior_optimizer_updates=0,prior_fit_predictions=0,original_preparation_preserved=True)
    plan['changes_from_prior_probe'].append('Every held fold must contain fresh positive photos; deterministic group balance uses that count first for fresh-positive groups.')
    save(DEST/'PLAN_V2.json',plan)
    print(json.dumps(dict(status='prefit-fold-balance-fixed',fold_loads=loads,original_plan_preserved=True,optimizer_updates=0),indent=2))

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
    started=time.monotonic();plan=read(DEST/'PLAN_V2.json');folds=read(DEST/'FOLDS_V2.json')
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
            weights=torch.cat([torch.full((len(records[i]['train']),),.5/((positive_photos if records[i]['y'] else negative_photos)*len(records[i]['train']))) for i in train_ids])
            assert abs(float(weights[y==1].sum())-.5)<1e-6 and abs(float(weights[y==0].sum())-.5)<1e-6
            mean=x.mean(0);std=x.std(0).clamp_min(.1);z=(x-mean)/std
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
                        maximum_negative_score=float(maximum),locked_threshold=threshold),
                    held_predictions=dict(scores=scores.tolist(),labels=ty.tolist(),image_ids=tids))
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
            source_inputs_unchanged=True,production_adoption=False,plan_sha256=sha(DEST/'PLAN_V2.json'),
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
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['prepare','refold','fit']);args=parser.parse_args()
    if args.stage=='prepare':prepare()
    elif args.stage=='refold':refold()
    else:fit()

