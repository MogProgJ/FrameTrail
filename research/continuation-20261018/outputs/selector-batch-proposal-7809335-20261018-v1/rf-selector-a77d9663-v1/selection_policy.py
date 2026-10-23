"""Validation-only selection guards every reviewed class, including expansion rows."""
import copy
from scoped_metrics import score

def evaluate(rows,predictions):
    ids=sorted({int(k) for r in rows for k,v in r['scope'].items() if v!='unknown'}|{t['canonical_id'] for r in rows for t in r['targets']})
    classes={}
    for cid in ids:
        subset=[]
        for row in rows:
            r=copy.deepcopy(row);r['targets']=[t for t in r['targets'] if t['canonical_id']==cid];r['scope']={k:v for k,v in r['scope'].items() if int(k)==cid};subset.append(r)
        classes[str(cid)]=score(subset,{k:[p for p in v if p['canonical_id']==cid] for k,v in predictions.items()})
    return dict(metrics=score(rows,predictions),per_class=classes,predictions=predictions)

def eligible(current,baseline):
    if set(current['per_class'])!=set(baseline['per_class']):return False
    for cid,b in baseline['per_class'].items():
        c=current['per_class'][cid]
        if c['complete_tp']<b['complete_tp'] or c['complete_fp']>b['complete_fp'] or c['partial_hits']<b['partial_hits']:return False
    return current['metrics']['unscored_predictions']<=baseline['metrics']['unscored_predictions']+5

def ranking(result):
    m=result['metrics'];return (m['complete_tp']+m['partial_hits'],m['complete_f1'])
def improves(current,best,baseline):return eligible(current,baseline) and ranking(current)>ranking(best)
