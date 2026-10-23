"""Assemble all 124 reviewed original fresh photos into a versioned, unqualified draft."""
import json, hashlib, collections
from pathlib import Path
from PIL import Image, ImageDraw
R=Path(r'C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation')
D=R/'outputs/broad-billboard-definition-20261022-v1'; OUT=D/'fresh-role-draft-v2'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    with p.open('x',encoding='utf-8') as f:f.write(json.dumps(v,indent=2,allow_nan=False)+'\n')
def bbox(t,w,h):
    x,y,bw,bh=t['normalized_cxcywh'];return [(x-bw/2)*w,(y-bh/2)*h,(x+bw/2)*w,(y+bh/2)*h]
def main():
    OUT.mkdir(exist_ok=False);(OUT/'overlays').mkdir()
    queue=read(D/'REVIEW_QUEUE.json');rows={r['image_id']:r for r in queue['records'] if r['source_pool']=='fresh-release'}
    decisions=[];refs=[]
    for split in ['TRAIN','VAL','TEST']:
        p=D/f'{split}_REVIEW_DECISIONS_V1.json';decisions.extend(read(p));refs.append(dict(path=str(p),sha256=sha(p)))
    assert len(rows)==len(decisions)==124 and set(rows)=={d['image_id'] for d in decisions}
    records=[];pages=collections.defaultdict(list)
    for dec in decisions:
        r=rows[dec['image_id']];p=Path(r['source_path']);assert sha(p)==r['image_sha256'];w,h=r['width'],r['height']
        im=Image.open(p).convert('RGB');assert im.size==(w,h)
        targets=[dict(t,provenance='retained-exact-narrow-v1') for t in r['old_billboard_targets']]
        for b in dec['additions_xyxy']:
            x1,y1,x2,y2=b;assert 0<=x1<x2<=w and 0<=y1<y2<=h,(r['image_id'],b,w,h)
            targets.append(dict(canonical_id=133,normalized_cxcywh=[(x1+x2)/(2*w),(y1+y2)/(2*h),(x2-x1)/w,(y2-y1)/h],draft_xyxy=b,provenance='assistant-original-image-expanded-v2-draft'))
        scope=('complete' if targets else 'absent') if dec['completeness']!='unresolved' else ('positive_only' if targets else 'unknown')
        records.append(dict(r,review=dec,draft_scope_133=scope,draft_targets_133=targets,approved_for_training=False))
        if dec['additions_xyxy'] or dec['completeness']=='unresolved':
            draw=ImageDraw.Draw(im)
            for i,t in enumerate(targets):
                b=bbox(t,w,h);color='#31e6ff' if t['provenance'].startswith('retained') else '#ffb000'
                draw.rectangle(b,outline=color,width=3);draw.text((b[0]+3,b[1]+3),str(i+1),fill=color,stroke_width=1,stroke_fill='black')
            im.save(OUT/'overlays'/f"{r['image_id']}.jpg",quality=95)
            im.thumbnail((480,340));c=Image.new('RGB',(500,390),'#1b1b1b');c.paste(im,((500-im.width)//2,30));dr=ImageDraw.Draw(c);dr.text((8,5),r['image_id']+' | '+scope,fill='white');dr.text((8,370),'DRAFT: cyan retained / amber added; no predictions',fill='white');pages[r['split']].append(c)
    save(OUT/'ANNOTATIONS_DRAFT.json',dict(status='assistant-reviewed-originals-draft-not-training-release',task_definition_sha256=sha(D/'TASK_DEFINITION.json'),review_queue_sha256=sha(D/'REVIEW_QUEUE.json'),decision_refs=refs,records=records,approved_for_training=False))
    for split,thumbs in pages.items():
        for page in range((len(thumbs)+5)//6):
            sheet=Image.new('RGB',(1500,780),'#111111')
            for i,im in enumerate(thumbs[page*6:(page+1)*6]):sheet.paste(im,((i%3)*500,(i//3)*390))
            sheet.save(OUT/f'{split.upper()}_QA_SHEET_{page+1:02d}.jpg',quality=94)
    counts={}
    for split in ['train','val','test']:
        rr=[r for r in records if r['split']==split];scopes=collections.Counter(r['draft_scope_133'] for r in rr);min_abs=30 if split=='train' else 20
        counts[split]=dict(photos=len(rr),scopes=dict(scopes),known_positive=sum(bool(r['draft_targets_133']) for r in rr),retained_targets=sum(len(r['old_billboard_targets']) for r in rr),new_targets=sum(len(r['review']['additions_xyxy']) for r in rr),minimum_absent=min_abs,complete_absent=scopes['absent'],absent_shortfall=max(0,min_abs-scopes['absent']))
    receipt=dict(status='124-original-fresh-photos-reviewed-draft-overlay-QA-pending',counts=counts,source_hashes_verified=124,unresolved_photos=[r['image_id'] for r in records if r['review']['completeness']=='unresolved'],pending_old_review=199,approved_for_training=False,new_fits=0,new_inference=0,TEST_predictions=0,production_adoption=False,annotations_sha256=sha(OUT/'ANNOTATIONS_DRAFT.json'))
    save(OUT/'DRAFT_RECEIPT.json',receipt);print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
