"""Score frozen canonical detections with separate complete/partial denominators."""
import argparse,collections,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parent/'evaluation-qa-20261011'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def overlap(a,b):
    intersection=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-intersection
    return intersection/union if union>0 else 0
def fraction(a,b):return a/b if b else None
def load_frozen_reference():
    path=ROOT/'scoped-reference-v1.json';lock=read(ROOT/'snapshot-lock-v1.json')
    if sha(path)!=lock['reference_sha256']:raise ValueError('Reference differs from pre-inference snapshot lock')
    ref=read(path)
    if ref['approved_for_training'] is not False or ref['frozen_label_and_metric_scope'] is not True:raise ValueError('Not a frozen evaluation-only reference')
    for f in ref['frames']:
        if sha(f['path'])!=f['sha256'] or f['sha256']!=lock['source_frame_hashes'][f['id']]:raise ValueError('Source evaluation frame changed')
    return ref,lock
def score(ref,payload,reference_sha256):
    if payload.get('reference_sha256')!=reference_sha256:raise ValueError('Predictions reference the wrong answer key')
    if payload.get('class_namespace')!='native-canonical':raise ValueError('Predictions must use native canonical IDs, not raw head indexes')
    if payload.get('vocabulary_sha256')!=ref['vocabulary_sha256']:raise ValueError('Prediction vocabulary mismatch')
    if payload.get('confidence_threshold')!=ref['baseline_identity']['confidence']:raise ValueError('Changed confidence threshold; do not tune from this test')
    rows=payload.get('frames',[]);expected={f['id']:f for f in ref['frames']}
    if len(rows)!=len(expected) or len({r['frame_id'] for r in rows})!=len(rows) or {r['frame_id'] for r in rows}!=set(expected):raise ValueError('Need exactly one row for every frozen frame, including zero detections')
    known_ids={c['canonical_id'] for c in ref['vocabulary']}
    names={c['canonical_id']:c['canonical_name'] for c in ref['vocabulary']}
    by_class=collections.defaultdict(lambda:collections.Counter())
    result=[];totals=collections.Counter();by_sequence=collections.defaultdict(lambda:collections.Counter())
    for row in rows:
        frame=expected[row['frame_id']];targets=frame['targets']
        complete={s['canonical_id'] for s in frame['complete_class_scopes'] if s['complete']}
        preds=[];ignored=[]
        for number,p in enumerate(row['detections']):
            cid=p.get('canonical_id');conf=p.get('confidence');box=p.get('box')
            if type(cid) is not int or cid not in known_ids:raise ValueError('Unsupported canonical prediction ID')
            if isinstance(conf,bool) or not isinstance(conf,(int,float)) or not math.isfinite(conf) or not 0<=conf<=1:raise ValueError('Invalid confidence')
            if not isinstance(box,list) or len(box)!=4 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in box):raise ValueError('Invalid prediction geometry')
            if not (0<=box[0]<box[2]<=frame['width'] and 0<=box[1]<box[3]<=frame['height']):raise ValueError('Prediction box outside original source dimensions')
            if conf<ref['baseline_identity']['confidence']:
                ignored.append({'prediction_index':number,'reason':'below-frozen-confidence-threshold'});continue
            preds.append((number,p))
        matched=set();outcomes=[];counts=collections.Counter()
        for index,p in sorted(preds,key=lambda row:(-row[1]['confidence'],row[0])):
            choices=[(overlap(t['box'],p['box']),n) for n,t in enumerate(targets) if n not in matched and t['canonical_id']==p['canonical_id']]
            best,n=max(choices,default=(0,None))
            if best>=ref['evaluation']['iou_threshold']:
                matched.add(n);kind='complete_tp' if p['canonical_id'] in complete else 'partial_tp'
                counts[kind]+=1;by_class[p['canonical_id']][kind]+=1
                outcomes.append({'prediction_index':index,'target_id':targets[n]['id'],'iou':best,'kind':kind})
            elif p['canonical_id'] in complete:
                counts['complete_fp']+=1;by_class[p['canonical_id']]['complete_fp']+=1
                outcomes.append({'prediction_index':index,'kind':'complete_fp','label':names[p['canonical_id']]})
            else:
                counts['unscored_predictions']+=1
                ignored.append({'prediction_index':index,'reason':'class-frame-completeness-not-established'})
        missed=[]
        for n,t in enumerate(targets):
            if n in matched:continue
            kind='complete_fn' if t['canonical_id'] in complete else 'partial_fn'
            counts[kind]+=1;by_class[t['canonical_id']][kind]+=1
            near=[(overlap(t['box'],p['box']),p['canonical_id']) for _,p in preds if p['canonical_id']!=t['canonical_id']]
            best,cid=max(near,default=(0,None))
            missed.append({'target_id':t['id'],'label':t['label'],'kind':kind,'nearby_other_class':names[cid] if cid is not None and best>=.5 else None,'nearby_iou':best if best>=.5 else None})
        totals.update(counts);by_sequence[frame['sequence']].update(counts)
        result.append({'frame_id':frame['id'],'counts':dict(counts),'matches_and_complete_scope_false_positives':outcomes,'missed_targets':missed,'ignored_predictions':ignored})
    def metrics(c):
        return {'complete_tp':c['complete_tp'],'complete_fp':c['complete_fp'],'complete_fn':c['complete_fn'],
          'complete_precision':fraction(c['complete_tp'],c['complete_tp']+c['complete_fp']),
          'complete_recall':fraction(c['complete_tp'],c['complete_tp']+c['complete_fn']),
          'partial_positive_hits':c['partial_tp'],'partial_positive_misses':c['partial_fn'],
          'partial_known_positive_recall':fraction(c['partial_tp'],c['partial_tp']+c['partial_fn']),
          'unscored_predictions':c['unscored_predictions']}
    return {'schema':1,'purpose':'scoped-pilot-baseline-or-candidate-comparison','reference_sha256':reference_sha256,
      'identity':payload.get('identity'),'aggregate':metrics(totals),
      'by_sequence':{sid:metrics(c) for sid,c in sorted(by_sequence.items())},
      'by_class':{names[cid]:metrics(c) for cid,c in sorted(by_class.items())},'frames':result,
      'limits':'Strict canonical class + visible-box IoU 0.5 at confidence 0.35. Precision only applies to 68 audited class/frame scopes. Partial scopes report known-positive recall, with no false-positive claims. No tracking AP, official LV-VIS AP, 597-category accuracy or improvement/adoption claim.'}
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--predictions',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();ref,lock=load_frozen_reference();payload=read(args.predictions);report=score(ref,payload,lock['reference_sha256'])
    with args.output.open('x',encoding='utf-8') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report['aggregate'],indent=2))
if __name__=='__main__':main()
