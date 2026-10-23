"""Explain independently audited selections without changing selection policy."""
import json,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent;R=P/'retrieval-7818553';D=P.parent/'selector-diagnosis-7818553-20261018-v1'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def failures(c,b,label):
    result=[]
    for cid,v in b['per_class'].items():
        cur=c['per_class'][cid]
        for key in ('complete_tp','complete_fp','partial_hits'):
            if (cur[key]>v[key] if key=='complete_fp' else cur[key]<v[key]):result.append(dict(baseline=label,category=cid,metric=key,before=v[key],after=cur[key]))
    if c['metrics']['unscored_predictions']>b['metrics']['unscored_predictions']+5:result.append(dict(baseline=label,metric='unscored_predictions',before=b['metrics']['unscored_predictions'],after=c['metrics']['unscored_predictions'],cap=b['metrics']['unscored_predictions']+5))
    return result
def main():
    D.mkdir(exist_ok=False);identity=read(P/'PROPOSAL_IDENTITY.json');T=P/identity['package_directory'];audit=read(R/'independent-audit/AUDIT.json')
    assert audit['status']=='batch-independently-audited' and audit['validation_only_winner_index'] is None
    b=read(T/'inputs/validation-resume.json');o=read(T/'inputs/validation-original.json');rows={r['image_id']:r for r in read(T/'release/candidate-manifest-v2.json')['images']};trials=[];unknown=[]
    for i in range(4):
        out=R/f'task-{i}/verified-7818553_{i}/output/rf-selector-7818553_{i}';trace=[]
        for path in sorted(out.glob('validation-*.json')):
            c=read(path);bill=c['per_class']['133'];rejections=failures(c,b,'current')+failures(c,o,'original')
            assert c['eligible']==(not rejections)
            trace.append(dict(step=c['step'],eligible=c['eligible'],billboard_hits=bill['complete_tp']+bill['partial_hits'],billboard_complete_fp=bill['complete_fp'],unscored=c['metrics']['unscored_predictions'],failures=rejections))
        last=read(out/'validation-1500.json');baseline=read(out/'validation-0000.json')
        for image_id,preds in last['predictions'].items():
            row=rows[image_id]
            for det in preds:
                if det['canonical_id']==133 and row['scope'].get('133','unknown')=='unknown':unknown.append(dict(trial=i,image_id=image_id,detection=det,source_path=row['source_path']))
        losses=[read(out/f'step-{s:04}.json') for s in (1,100,500,1000,1500)]
        trials.append(dict(index=i,variant=read(out/'experiment-report.json')['variant'],maximum_billboard_hits=max(t['billboard_hits'] for t in trace),final=trace[-1],first_billboard_gain=next((t for t in trace if t['billboard_hits']>0),None),trace=trace,loss_probes=losses,unknown_billboard_counts=dict(start=sum(d['canonical_id']==133 and rows[k]['scope'].get('133','unknown')=='unknown' for k,v in baseline['predictions'].items() for d in v),last=sum(d['canonical_id']==133 and rows[k]['scope'].get('133','unknown')=='unknown' for k,v in last['predictions'].items() for d in v))))
    result=dict(status='audited-selector-outcomes-explained',actual_array_job_id='7818553',audit_sha256=sha(R/'independent-audit/AUDIT.json'),trials=trials,unknown_billboard_predictions=unknown,current_model_unchanged=True,selection_policy_unchanged=True,new_GPU_jobs=0,production_adoption=False)
    (D/'DIAGNOSIS.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(trials=[{k:v for k,v in t.items() if k not in ('trace','loss_probes')} for t in trials],unknown_billboard_predictions=len(unknown)),indent=2))
if __name__=='__main__':main()
