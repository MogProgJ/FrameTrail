"""Stored TRAIN-score context audit; no fitting, inference, relabeling or TEST reads."""
import json,hashlib
from pathlib import Path
R=Path(r'C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation');O=R/'outputs'
D=O/'error-context-audit-7870268-20261022-v1'
PHOTO=O/'train-photo-max-loss-7870268-20261022-v1';BCE=O/'train-discrimination-full-query-7870268-20261022-v1'
C=O/'fresh-paired-controls-20261021-v1'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    with p.open('x',encoding='utf-8') as f:f.write(json.dumps(v,indent=2,allow_nan=False)+'\n')
def main():
    D.mkdir(exist_ok=False)
    save(D/'CONTINUATION_SCOPE.json',dict(date='2026-10-22',user_instruction='All right, go ahead. Proceed to the next step.',
        scope='Assistant review of six frozen TRAIN examples, stored-score error context audit and next data/representation strategy preparation.',
        human_independent_annotation_completed=False,new_fits=0,new_inference=0,new_cluster_jobs=0,production_adoption=False))
    inputs=read(C/'INPUTS.json');source={r['image_id']:r for r in inputs['records'] if r['row']['split']=='train'}
    assert len(source)==124
    assignment={r['image_id']:r for r in read(PHOTO/'TRAIN_ASSIGNMENTS.json')}
    snapshots={};refs=[]
    for label,folder in [('BCE',BCE),('photo_max',PHOTO)]:
        photos={}
        for fold in range(4):
            path=folder/f'fits/fold-{fold}-mlp32.json';result=read(path);p=result['held_predictions']
            refs.append(dict(path=str(path),sha256=sha(path)))
            for score,y,iid in zip(p['scores'],p['labels'],p['image_ids']):
                assert source[iid]['row']['split']=='train'
                row=photos.setdefault(iid,dict(fold=fold,scores=[],label=int(y)))
                assert row['fold']==fold and row['label']==int(y);row['scores'].append(score)
        for iid,row in photos.items():
            a=assignment[iid];r=source[iid];expected=a['evaluation_query_indices']
            assert len(row['scores'])==len(expected)
            row.update(query_indices=expected,pool=r['pool'],scope=r['row']['scope']['133'],
                family=r['row'].get('confuser_family','old-absent-unstratified' if row['label']==0 else 'positive'),
                scene=r['row']['scene_group'],identity=r['row']['identity_group'],source_path=str(Path(r['base'])/r['row']['source_path']),
                image_sha256=r['row']['image_sha256'],positive_queries=len(expected) if row['label'] else 0,
                hits=sum(s>=.5 for s in row['scores']) if row['label'] else 0,
                alarm=bool(not row['label'] and max(row['scores'])>=.5),maximum_score=max(row['scores']))
        assert len(photos)==122;snapshots[label]=photos
    summary={}
    for label,photos in snapshots.items():
        pooled={};families={}
        for iid,p in photos.items():
            pool=pooled.setdefault(p['pool'],dict(photos=0,positive_queries=0,hits=0,alarmed_absent_photos=0))
            pool['photos']+=1;pool['positive_queries']+=p['positive_queries'];pool['hits']+=p['hits'];pool['alarmed_absent_photos']+=int(p['alarm'])
            if not p['label']:
                f=families.setdefault(p['family'],dict(photos=0,alarmed=0,image_ids=[]));f['photos']+=1;f['alarmed']+=int(p['alarm'])
                if p['alarm']:f['image_ids'].append(iid)
        summary[label]=dict(pools=pooled,absent_families=families)
    comparison=[]
    for iid,p in snapshots['photo_max'].items():
        b=snapshots['BCE'][iid]
        comparison.append(dict(image_id=iid,pool=p['pool'],family=p['family'],fold=p['fold'],scene=p['scene'],
            source_path=p['source_path'],image_sha256=p['image_sha256'],positive_queries=p['positive_queries'],
            bce_hits=b['hits'],photo_hits=p['hits'],bce_alarm=b['alarm'],photo_alarm=p['alarm'],
            bce_maximum=b['maximum_score'],photo_maximum=p['maximum_score']))
    negative=[r for r in comparison if r['photo_alarm']]
    missed=[r for r in comparison if r['positive_queries']>r['photo_hits']]
    changed=dict(shared_alarm_photos=sum(r['bce_alarm'] and r['photo_alarm'] for r in comparison),
        removed_alarm_photos=sum(r['bce_alarm'] and not r['photo_alarm'] for r in comparison),
        introduced_alarm_photos=sum(not r['bce_alarm'] and r['photo_alarm'] for r in comparison),
        positive_queries_gained=sum(max(0,r['photo_hits']-r['bce_hits']) for r in comparison),
        positive_queries_lost=sum(max(0,r['bce_hits']-r['photo_hits']) for r in comparison))
    save(D/'ERROR_CONTEXT.json',dict(status='TRAIN-stored-score-context-audited',fixed_probe_threshold=.5,
        summary=summary,paired_changes=changed,all_photo_comparisons=comparison,
        limitations=['MLP-only comparison at previously fixed0.5; no threshold tuning.','Covered positive queries, not detector recall.','TRAIN development folds reused; no independent test claim.','Old absent families not assigned without original-image review.']))
    save(D/'ORIGINAL_REVIEW_QUEUE.json',dict(status='TRAIN-only-original-review-queue',absent_errors=sorted(negative,key=lambda x:(x['family'],x['image_id'])),
        positive_errors=sorted(missed,key=lambda x:x['image_id']),selection='All fixed0.5photo-max heldTRAIN errors; no subset cherry-picking.',label_edits_allowed=False))
    six=read(PHOTO/'BOUNDARY_REVIEW_PACKET.json')
    descriptions={
        '0c39f6a763ce3ec0':'Names a specific restaurant; freestanding placement alone does not make it an in-scope advertising campaign board under the frozen narrow definition.',
        '37c1b3a6b5c824d4':'Restaurant identity and drive-through/open-hours information. Preserve absent scope.',
        '757556fbf9393cff':'Museum identity/direction panel; no exhibition or product campaign visible. Preserve absent scope.',
        '5a1cea0bb9f7b721':'Large dated exhibition promotion with pictorial campaign and event title; museum name lettering above it is a separate excluded context.',
        '13909d11dbe65be8':'Large bank/product advertisement behind a transit departure display. Include the ad, exclude the foreground transit information.',
        '20a3a8cd5733db8c':'Bus-stop route, location and contact information; preserve absent scope.'}
    review=[]
    for p in six['photos']:
        assert sha(Path(p['source_path']))==p['image_sha256']
        review.append(dict(image_id=p['image_id'],source_path=p['source_path'],image_sha256=p['image_sha256'],
            existing_scope=p['current_billboard_scope'],assistant_review='consistent-with-frozen-definition',reason=descriptions[p['image_id']]))
    save(D/'BOUNDARY_REVIEW.json',dict(status='assistant-original-image-review-complete',records=review,
        independence='Same assistant continuation, unblinded to labels and prior error selection; not independent human review.',
        user_instruction_is_continuation_not_itemwise_annotation_confirmation=True,labels_changed=False,test_images_used=0))
    save(D/'SOURCE_REFS.json',dict(refs=refs+[dict(path=str(C/'INPUTS.json'),sha256=sha(C/'INPUTS.json')),
        dict(path=str(PHOTO/'COMPLETION_RECEIPT.json'),sha256=sha(PHOTO/'COMPLETION_RECEIPT.json'))]))
    print(json.dumps(dict(summary=summary,paired_changes=changed,absent_error_photos=len(negative),positive_error_photos=len(missed)),indent=2))
if __name__=='__main__':main()
