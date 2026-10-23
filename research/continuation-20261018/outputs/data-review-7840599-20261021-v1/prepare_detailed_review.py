"""Freeze deterministic pre-prediction detailed-review order across two fresh cohorts."""
import json,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent
O=R.parent/'data-review-7824179-20261020-v1'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
a=[]
for root in (O,R):
    source={r['image_id']:r for r in read(root/'VISUAL_REVIEW_QUEUE.json')['records']}
    triage=[r for f in sorted(root.glob('scene-triage-*.json')) for r in read(f)['records']]
    override={}
    if (root/'ORIGINAL_IMAGE_FOLLOWUP.json').exists():override={r['id']:r for r in read(root/'ORIGINAL_IMAGE_FOLLOWUP.json')['records']}
    for row in triage:
        row=dict(row,**{k:v for k,v in override.get(row['id'],{}).items() if k in ('disposition',)})
        meta=source[row['id']]
        a.append(dict(image_id=row['id'],role=row['role'],anchor=row['anchor'],disposition=row['disposition'],
            path=meta['path'],sha256=meta['sha256'],identity_group=meta['identity_group'],
            publisher_billboard_boxes=meta['publisher_billboard_boxes'],
            review_root=str(root),scene_note=row['note']))
assert len(a)==len({r['image_id'] for r in a})==347
# Fixed source/scene semantic inclusion before detector outputs, never model-score selection.
for r in a:
    r['order_key']=hashlib.sha256(('frametrail-detailed-review-20261021-v1:'+r['image_id']).encode()).hexdigest()
a.sort(key=lambda r:(r['role'],r['order_key']))
result=dict(schema=1,status='fixed-detailed-review-order-before-predictions',
    definition='nextdata7769109-taxonomy-v1: large physical advertising boards; ordinary shop lettering/traffic information distinct',
    curation='Inspect originals in fixed order. Scene-check cases remain held. Only explicitly reviewed complete positives/whole-photo absences can count; role never changes. No detector predictions used.',
    geometric_convention='Normalized axis-aligned enclosure of visible advertising panel/face; include its thin frame when inseparable, exclude poles/roof/supports. Every separate visible target must be enumerated. Hold uncertain material, object boundary, distant face or completeness; never treat held cases as absence.',
    model_predictions_seen=False,approved_for_training=False,records=a)
with (R/'DETAILED_REVIEW_ORDER.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({role:[dict(id=r['image_id'],path=r['path'],boxes=r['publisher_billboard_boxes']) for r in a if r['role']==role and r['disposition']=='positive-context'] for role in ('train','val','test')}))

