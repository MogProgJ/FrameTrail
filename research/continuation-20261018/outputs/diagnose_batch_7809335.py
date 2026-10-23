"""Analyze independently audited development traces; no inference or reselection."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BASE=ROOT/'billboard-batch-proposal-7805570-20261018-v1'
RET=BASE/'retrieval-7809335';TOOLS=BASE/'rf-billboard-batch-0a255598-v1'
OUT=ROOT/'billboard-batch-diagnosis-7809335-20261018-v1'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(p,v):
    with p.open('x',encoding='utf-8') as f:f.write(v if isinstance(v,str) else json.dumps(v,indent=2)+'\n')
audit=read(RET/'independent-audit/AUDIT.json');assert audit['status']=='batch-independently-audited' and audit['validation_only_winner_index'] is None
OUT.mkdir(exist_ok=False)
original=read(TOOLS/'inputs/validation-original.json');current=read(TOOLS/'inputs/validation-resume.json')
names=read(TOOLS/'rf-mapping.json')['canonical_class_names']
def name(k):return names[str(k)] if isinstance(names,dict) else names[int(k)]
results=[];input_hashes={str(RET/'independent-audit/AUDIT.json'):sha(RET/'independent-audit/AUDIT.json')}
for i in range(4):
    run=RET/f'task-{i}/verified-7809335_{i}/output/rf-billboard-batch-7809335_{i}'
    records=[]
    for step in range(0,1501,100):
        path=run/f'validation-{step:04}.json';r=read(path);input_hashes[str(path)]=sha(path)
        failures=[]
        for bn,b in [('current',current),('original',original)]:
            for cid,bm in b['per_class'].items():
                m=r['per_class'][cid]
                for key in ('complete_tp','partial_hits','complete_fp'):
                    bad=m[key]>bm[key] if key=='complete_fp' else m[key]<bm[key]
                    if bad:failures.append(dict(baseline=bn,category=name(cid),metric=key,before=bm[key],after=m[key]))
            before=b['metrics']['unscored_predictions'];after=r['metrics']['unscored_predictions']
            if after>before+5:failures.append(dict(baseline=bn,category='all',metric='unscored_predictions',before=before,cap=before+5,after=after))
        bill=r['per_class']['133'];washer=r['per_class']['593']
        def cid_counts(cid):
            all_pred=[p for row in r['predictions'].values() for p in row if p['canonical_id']==cid]
            return len(all_pred)
        records.append(dict(step=step,eligible=r['eligible'],billboard_known_hits=bill['complete_tp']+bill['partial_hits'],billboard_known_targets=bill['complete_tp']+bill['complete_fn']+bill['partial_hits']+bill['partial_misses'],billboard_complete_fp=bill['complete_fp'],billboard_predictions=cid_counts(133),washing_known_hits=washer['complete_tp']+washer['partial_hits'],all_unscored_predictions=r['metrics']['unscored_predictions'],aggregate_known_hits=r['metrics']['complete_tp']+r['metrics']['partial_hits'],failures=failures))
    report=read(run/'experiment-report.json')
    result=dict(index=i,variant=report['variant'],selected_step=report['best_step'],max_billboard_hits=max(r['billboard_known_hits'] for r in records),first_billboard_hit_step=next((r['step'] for r in records if r['billboard_known_hits']>0),None),first_rejection=next((r for r in records if not r['eligible']),None),best_positive_but_rejected=max((r for r in records if r['billboard_known_hits']>0),key=lambda r:(r['billboard_known_hits'],-r['billboard_complete_fp'],-r['all_unscored_predictions']),default=None),final=records[-1],trace=records)
    results.append(result)
write(OUT/'DIAGNOSIS.json',dict(actual_array_job_id='7809335',source='all64 independently rescored validation records',validation_photos=135,effective_unscored_cap=min(original['metrics']['unscored_predictions'],current['metrics']['unscored_predictions'])+5,trials=results,checkpoint_reselected=False,holdout_or_new_inference_used=False,model_or_threshold_changed=False,new_jobs=0))
write(OUT/'INPUT_HASHES.json',input_hashes)
print(json.dumps([{k:r[k] for k in ('index','variant','max_billboard_hits','first_billboard_hit_step','first_rejection','best_positive_but_rejected','final')} for r in results],indent=2))
