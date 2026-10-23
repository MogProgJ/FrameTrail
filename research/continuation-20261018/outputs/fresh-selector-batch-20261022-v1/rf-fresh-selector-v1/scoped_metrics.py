"""Fixed scoped validation for canonical RF outputs; never full-vocabulary mAP."""
import math
def iou(a,b):
    overlap=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-overlap
    return overlap/union if union else 0

def decode(outputs,width,height):
    import torch
    boxes,logits=outputs['pred_boxes'],outputs['pred_logits']
    if boxes.shape!=(1,300,4) or logits.shape!=(1,300,616) or not torch.isfinite(boxes).all() or not torch.isfinite(logits).all():raise ValueError('RF output contract changed')
    scores=logits[0,:,:615].sigmoid().flatten() # explicit background slot615 ignored
    values,indices=torch.topk(scores,300);proposals=[]
    for score,index in zip(values.tolist(),indices.tolist()):
        if score<.35:continue
        query,cid=divmod(index,615);cx,cy,bw,bh=boxes[0,query].tolist()
        if bw<=0 or bh<=0:continue
        box=[max(0,min(width,(cx-bw/2)*width)),max(0,min(height,(cy-bh/2)*height)),max(0,min(width,(cx+bw/2)*width)),max(0,min(height,(cy+bh/2)*height))]
        if box[2]<=box[0] or box[3]<=box[1]:continue
        if any(p['canonical_id']==cid and iou(p['box'],box)>.45 for p in proposals):continue
        proposals.append(dict(canonical_id=cid,confidence=score,box=box))
        if len(proposals)==100:break
    return proposals

def score(rows,predictions):
    if any(r['split']!='val' or r['supervision']!='gold' for r in rows):raise ValueError('Only fixed gold validation rows can select checkpoints')
    if set(predictions)!={r['image_id'] for r in rows}:raise ValueError('Missing/extra validation predictions')
    totals=dict(complete_tp=0,complete_fp=0,complete_fn=0,partial_hits=0,partial_misses=0,unscored_predictions=0);details=[]
    for row in rows:
        complete={int(k) for k,v in row['scope'].items() if v in ('complete','absent')}
        targets=row['targets'];matched=set();counts={k:0 for k in totals}
        def box(t):
            cx,cy,bw,bh=t['normalized_cxcywh']
            return [(cx-bw/2)*row['width'],(cy-bh/2)*row['height'],(cx+bw/2)*row['width'],(cy+bh/2)*row['height']]
        for prediction in sorted(predictions[row['image_id']],key=lambda p:-p['confidence']):
            cid=prediction['canonical_id'];b=prediction['box']
            if type(cid)is not int or not 0<=cid<615 or not math.isfinite(prediction['confidence']) or not .35<=prediction['confidence']<=1 or len(b)!=4 or not all(math.isfinite(v) for v in b) or not 0<=b[0]<b[2]<=row['width'] or not 0<=b[1]<b[3]<=row['height']:raise ValueError('Invalid validation prediction')
            options=[(iou(b,box(t)),i) for i,t in enumerate(targets) if i not in matched and t['canonical_id']==cid]
            overlap,index=max(options,default=(0,-1))
            if overlap>=.5:matched.add(index);counts['complete_tp' if cid in complete else 'partial_hits']+=1
            else:counts['complete_fp' if cid in complete else 'unscored_predictions']+=1
        for i,t in enumerate(targets):
            if i not in matched:counts['complete_fn' if t['canonical_id'] in complete else 'partial_misses']+=1
        for k,v in counts.items():totals[k]+=v
        details.append(dict(image_id=row['image_id'],**counts))
    tp,fp,fn=(totals[k] for k in ('complete_tp','complete_fp','complete_fn'))
    return dict(totals,complete_precision=tp/(tp+fp) if tp+fp else 0,complete_recall=tp/(tp+fn) if tp+fn else 0,complete_f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0,complete_positive_targets=tp+fn,partial_known_positive_recall=totals['partial_hits']/(totals['partial_hits']+totals['partial_misses']) if totals['partial_hits']+totals['partial_misses'] else None,per_image=details,limits='Scoped development validation; unknown predictions unscored, partial known targets recall only. Not full-vocabulary mAP or independent accuracy.')
