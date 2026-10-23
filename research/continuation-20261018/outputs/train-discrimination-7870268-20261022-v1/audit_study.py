"""Plain-Python recomputation of all eight TRAIN probe records and scope."""
import json, hashlib, struct, math
from pathlib import Path
ROOT=Path(r'C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation')
D=ROOT/'outputs/train-discrimination-7870268-20261022-v1'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,v):
    with p.open('x',encoding='utf-8') as f:f.write(json.dumps(v,indent=2,allow_nan=False)+'\n')
def calculate(row,threshold):
    p=row['held_predictions'];scores=p['scores'];labels=p['labels'];ids=p['image_ids']
    assert len(scores)==len(labels)==len(ids) and all(math.isfinite(x) for x in scores)
    ordered=sorted(range(len(scores)),key=lambda i:(-scores[i],i));hits=0;area=0
    for rank,i in enumerate(ordered,1):
        if labels[i]:hits+=1;area+=hits/rank
    positive=sum(labels);pos_hits=sum(s>=threshold for s,y in zip(scores,labels) if y)
    neg_ids={i for i,y in zip(ids,labels) if not y};pos_ids={i for i,y in zip(ids,labels) if y}
    alarms={i for s,y,i in zip(scores,labels,ids) if not y and s>=threshold}
    recalls=[sum(s>=threshold for s,y,i in zip(scores,labels,ids) if i==iid)/sum(i==iid for i in ids) for iid in pos_ids]
    return dict(query_average_precision=area/positive,positive_hits=pos_hits,positive_queries=int(positive),
        negative_queries_positive=sum(s>=threshold for s,y in zip(scores,labels) if not y),negative_queries=len(labels)-int(positive),
        positive_photos=len(pos_ids),negative_photos=len(neg_ids),positive_query_recall=pos_hits/positive,
        positive_photo_macro_query_recall=sum(recalls)/len(recalls),absent_photos_with_alarm=len(alarms),absent_photo_alarm_fraction=len(alarms)/len(neg_ids))

def main():
    plan=read(D/'PLAN_V2.json');folds=read(D/'FOLDS_V2.json');report=read(D/'REPORT.json');assign=read(D/'TRAIN_ASSIGNMENTS.json')
    assert report['fits']==8 and report['total_updates']==1280 and report['seconds']<1800
    assert report['plan_sha256']==sha(D/'PLAN_V2.json') and plan['folds_sha256']==sha(D/'FOLDS_V2.json')
    all_ids=[i for ids in folds['held_photo_ids'] for i in ids];assert len(all_ids)==len(set(all_ids))==122
    inputs={r['image_id']:r for r in assign};assert len(inputs)==124 and sum(r['geometry_covered'] for r in assign)==71
    for held in folds['held_photo_ids']:
        train=set(all_ids)-set(held)
        for key in ['identity_group','scene_group']:
            assert not {inputs[i][key] for i in train}&{inputs[i][key] for i in held}
        assert any(inputs[i]['pool']=='fresh_positive' for i in held)
    results=[];aggregate={m:{'AP':[],'fixed_hits':0,'zero_hits':0,'positive_queries':0,'negative_photos':0,'fixed_alarm_photos':0,'zero_alarm_photos':0} for m in ['linear','mlp32']}
    for ref in report['result_refs']:
        assert sha(Path(ref['path']))==ref['sha256'];r=read(Path(ref['path']));fold=r['fold'];held=set(folds['held_photo_ids'][fold])
        train=set(all_ids)-held;assert r['updates']==160
        assert set(r['normalization']['fit_photo_ids'])==train
        assert set(r['calibration']['photo_ids'])=={i for i in train if inputs[i]['pool'].endswith('absent')}
        assert set(r['held_predictions']['image_ids'])==held
        for iid,y in zip(r['held_predictions']['image_ids'],r['held_predictions']['labels']):assert y==int(inputs[iid]['pool'].endswith('positive'))
        for iid in held:
            actual=sum(i==iid for i in r['held_predictions']['image_ids'])
            expected=len(inputs[iid]['evaluation_query_indices']);assert actual==expected
        maximum=max(r['calibration']['per_photo_max']);assert maximum==r['calibration']['maximum_negative_score']
        bits=struct.unpack('<I',struct.pack('<f',maximum))[0];next_float=struct.unpack('<f',struct.pack('<I',bits+1))[0]
        assert r['calibration']['locked_threshold']==next_float
        for key,threshold in [('held_TRAIN_fold_fixed0_5',.5),('held_TRAIN_fold_training_zero_alarm',next_float)]:
            calculated=calculate(r,threshold)
            for metric,value in calculated.items():assert abs(r[key][metric]-value)<1e-6,(r['fold'],r['model'],metric)
        a=aggregate[r['model']];fixed=r['held_TRAIN_fold_fixed0_5'];zero=r['held_TRAIN_fold_training_zero_alarm']
        a['AP'].append(fixed['query_average_precision']);a['fixed_hits']+=fixed['positive_hits'];a['zero_hits']+=zero['positive_hits'];a['positive_queries']+=fixed['positive_queries'];a['negative_photos']+=fixed['negative_photos'];a['fixed_alarm_photos']+=fixed['absent_photos_with_alarm'];a['zero_alarm_photos']+=zero['absent_photos_with_alarm']
        results.append(dict(fold=r['fold'],model=r['model'],AP=fixed['query_average_precision'],fixed_hits=fixed['positive_hits'],zero_hits=zero['positive_hits'],positive_queries=fixed['positive_queries'],
            fixed_alarm_photos=fixed['absent_photos_with_alarm'],zero_alarm_photos=zero['absent_photos_with_alarm'],negative_photos=fixed['negative_photos'],
            fitting_absent_photos_with_any_alarm_at0_5=sum(v>=.5 for v in r['calibration']['per_photo_max']),fitting_absent_photos=len(r['calibration']['photo_ids']),
            training_positive_recall_zero_alarm=r['training_positive_query_recall_at_zero_alarm']))
    for model,a in aggregate.items():a['mean_fold_AP']=sum(a['AP'])/4
    by={(r['fold'],r['model']):r for r in results};comparisons=[]
    for fold in range(4):
        a=by[fold,'linear'];b=by[fold,'mlp32'];comparisons.append(dict(fold=fold,AP_delta=b['AP']-a['AP'],zero_hits_delta=b['zero_hits']-a['zero_hits'],zero_alarm_photos_delta=b['zero_alarm_photos']-a['zero_alarm_photos']))
    support=all(c['AP_delta']>=0 and c['zero_hits_delta']>=0 and c['zero_alarm_photos_delta']<=0 for c in comparisons) and any(c['AP_delta']>0 or c['zero_hits_delta']>0 or c['zero_alarm_photos_delta']<0 for c in comparisons)
    assert support==report['nonlinear_consistent_support_under_frozen_rule']
    for ref in plan['cache_refs']:assert sha(Path(ref['path']))==ref['sha256'] and ref['split']=='train'
    for key in ['inputs','initial_head','prior_probe','checkpoint']:
        ref=plan['source'][key];assert sha(Path(ref['path']))==ref['sha256']
    assert report['validation_cache_reads']==report['test_cache_reads']==report['new_image_inference']==report['new_cluster_jobs']==0
    save(D/'INDEPENDENT_AUDIT.json',dict(status='all-eight-records-metrics-thresholds-folds-and-source-hashes-independently-audited',aggregate=aggregate,fold_comparisons=comparisons,records=results,
        nonlinear_consistent_support=support,validation_or_test_data_used=False,optimizer_updates_by_audit=0,
        caveat='Only64 of300 absent-photo queries entered each fit. Remaining fitting-photo queries were scored for calibration. Alarms on fitting photos are observed, but the retained per-photo maxima do not establish whether each alarm query was sampled or omitted.'))
    print(json.dumps(dict(aggregate=aggregate,comparisons=comparisons,consistent_support=support),indent=2))

if __name__=='__main__':main()
