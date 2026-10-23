"""Save a fail-closed ontology revision audit; no training/model/cache operations."""
import json,hashlib,collections,math
from pathlib import Path
from PIL import Image, ImageDraw
R=Path(r'C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation'); O=R/'outputs'; D=O/'broad-billboard-definition-20261022-v1'; B=D/'review-stage-v3'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    with p.open('x',encoding='utf-8') as f:f.write(json.dumps(v,indent=2,allow_nan=False)+'\n')
def main():
    B.mkdir(exist_ok=False);(B/'old-overlays').mkdir()
    q=read(D/'REVIEW_QUEUE.json');assert len(q['records'])==323
    refs=[];decisions={}
    for name in ['TRAIN','VAL','TEST','OLD_TRAIN','OLD_VAL_KNOWN']:
        p=D/f'{name}_REVIEW_DECISIONS_V1.json';rr=read(p);refs.append(dict(path=str(p),sha256=sha(p)))
        for r in rr:assert r['image_id'] not in decisions;decisions[r['image_id']]=r
    assert len(decisions)==204
    records=[];converted=[];oldthumb=[]
    for r in q['records']:
        assert sha(Path(r['source_path']))==r['image_sha256']
        assert r['task_definition_sha256']==sha(D/'TASK_DEFINITION.json')
        dec=decisions.get(r['image_id']); targets=[dict(t,provenance='retained-exact-narrow-v1') for t in r['old_billboard_targets']]
        if dec:
            assert dec['original_viewed'] is True and dec['independent_human_review'] is False
            for b in dec['additions_xyxy']:
                x1,y1,x2,y2=b;w,h=r['width'],r['height'];assert 0<=x1<x2<=w and 0<=y1<y2<=h
                targets.append(dict(canonical_id=133,normalized_cxcywh=[(x1+x2)/(2*w),(y1+y2)/(2*h),(x2-x1)/w,(y2-y1)/h],draft_xyxy=b,provenance='assistant-original-image-expanded-v2-draft'))
            scope=('complete' if targets else 'absent') if dec['completeness']!='unresolved' else ('positive_only' if targets else 'unknown')
            if r['old_scope']=='absent' and targets:converted.append(r['image_id'])
        else:
            assert r['source_pool']=='old_validation' and r['old_scope']=='unknown'
            scope='unknown'
        rec=dict(r,review=dec,review_state='reviewed-original-draft' if dec else 'pending-original-review-unknown-preserved',draft_scope_133=scope,draft_targets_133=targets,approved_for_training=False)
        records.append(rec)
        if dec and r['source_pool']!='fresh-release' and (dec['additions_xyxy'] or dec['completeness']=='unresolved'):
            im=Image.open(r['source_path']).convert('RGB');dr=ImageDraw.Draw(im);w,h=im.size
            for i,t in enumerate(targets):
                x,y,bw,bh=t['normalized_cxcywh'];b=[(x-bw/2)*w,(y-bh/2)*h,(x+bw/2)*w,(y+bh/2)*h];co='#31e6ff' if t['provenance'].startswith('retained') else '#ffb000';dr.rectangle(b,outline=co,width=3);dr.text((b[0]+3,b[1]+3),str(i+1),fill=co,stroke_width=1,stroke_fill='black')
            im.save(B/'old-overlays'/f"{r['image_id']}.jpg",quality=95);im.thumbnail((480,340));c=Image.new('RGB',(500,390),'#161616');c.paste(im,((500-im.width)//2,30));dd=ImageDraw.Draw(c);dd.text((8,5),r['image_id']+' | '+scope,fill='white');dd.text((8,370),'DRAFT - cyan retained / amber added; no predictions',fill='white');oldthumb.append(c)
    for page in range((len(oldthumb)+5)//6):
        sheet=Image.new('RGB',(1500,780),'#111111')
        for i,im in enumerate(oldthumb[page*6:(page+1)*6]):sheet.paste(im,((i%3)*500,(i//3)*390))
        sheet.save(B/f'OLD_QA_SHEET_{page+1:02d}.jpg',quality=94)
    save(B/'ANNOTATIONS_DRAFT.json',dict(status='204-reviewed-originals-119-unknown-pending-not-training-release',records=records,task_definition_sha256=sha(D/'TASK_DEFINITION.json'),queue_sha256=sha(D/'REVIEW_QUEUE.json'),decision_refs=refs,approved_for_training=False))
    stats={}
    for role in ['train','val','test']:
        rr=[r for r in records if r['source_pool']=='fresh-release' and r['split']==role];s=collections.Counter(r['draft_scope_133'] for r in rr);stats[role]=dict(photos=len(rr),scopes=dict(s),known_positive=sum(bool(r['draft_targets_133']) for r in rr),absent_shortfall=max(0,(30 if role=='train' else 20)-s['absent']))
    family=collections.Counter(r['confuser_family'] for r in records if r['source_pool']=='fresh-release' and r['split']=='train' and r['draft_scope_133']=='absent')
    design=read(O/'training-strategy-20261019-v1/EXPERIMENT_DESIGN.json')['data_required']
    family_gaps={f:max(0,design['minimum_train_absent_photos_per_family']-family[f]) for f in design['train_absent_families']}
    # Inventory every unused item from the existing source-eligible visual queues; do not select by model outcomes.
    allrows=[];source_refs=[]
    for job,date in [('7824179','20261020'),('7840599','20261021')]:
        p=O/f'data-review-{job}-{date}-v1/VISUAL_REVIEW_QUEUE.json';source_refs.append(dict(path=str(p),sha256=sha(p)));allrows.extend(dict(r,intake_job=job) for r in read(p)['records'])
    used={r['image_id'] for r in q['records']};unused=[r for r in allrows if r['image_id'] not in used];assert len(allrows)==347 and len(unused)==223
    current_groups=collections.defaultdict(set)
    for r in q['records']:current_groups[r['identity_group']].add(r['split'])
    exact_hashes={r['image_sha256'] for r in q['records']}; inventory=[]
    for r in unused:
        assert sha(Path(r['path']))==r['sha256']
        cross=sorted(current_groups[r['identity_group']]-{r['role']})
        inventory.append(dict(r,current_role_identity_conflicts=cross,current_exact_hash_conflict=r['sha256'] in exact_hashes,review_state='unreviewed-under-expanded-definition',admitted=False))
    save(B/'UNUSED_LOCAL_INVENTORY.json',dict(status='inventory-not-admission',records=inventory,total_visual_queue_records=347,unused_records=223,role_anchor=dict(collections.Counter(r['role']+'|'+r['anchor'] for r in inventory)),source_refs=source_refs,selection_policy='All unused source-eligible queue records enumerated. Original roles preserved. No model outcome filtering; no automatic admission; content/rights/scene and within-cohort duplicate QA still required.',new_collection=0))
    oldstats={pool:dict(collections.Counter(r['draft_scope_133'] for r in records if r['source_pool']==pool)) for pool in sorted({r['source_pool'] for r in records if r['source_pool']!='fresh-release'})}
    audit=dict(status='structural-source-integrity-pass-data-not-ready',photos_queued=323,originals_reviewed=204,pending_unknown_old_validation=119,source_hashes_verified=323,new_targets=sum(len(d['additions_xyxy']) for d in decisions.values()),retained_targets=sum(len(r['old_billboard_targets']) for r in records),old_absent_to_known_positive=converted,fresh_role_counts=stats,old_pool_scopes=oldstats,train_absent_families=dict(family),train_family_shortfalls=family_gaps,train_family_minimum=design['minimum_train_absent_photos_per_family'],unresolved_reviewed=[r['image_id'] for r in records if r['review'] and r['review']['completeness']=='unresolved'],approved_for_training=False,model_baselines_run=0,new_fits=0,new_inference=0,TEST_predictions=0,new_cluster_jobs=0,production_adoption=False,annotation_sha256=sha(B/'ANNOTATIONS_DRAFT.json'),inventory_sha256=sha(B/'UNUSED_LOCAL_INVENTORY.json'),prior_fresh_release_sha256=sha(O/'data-review-7840599-20261021-v1/reviewed-release-v1/scoped-fresh-additions-v1.json'))
    assert audit['prior_fresh_release_sha256']=='b262af61db8141abadd61cc026454953f6c172bd2fff552334c456170b5feb09'
    save(B/'STRUCTURAL_AUDIT.json',audit);print(json.dumps({k:v for k,v in audit.items() if k not in ['old_absent_to_known_positive','unresolved_reviewed']},indent=2))
if __name__=='__main__':main()
