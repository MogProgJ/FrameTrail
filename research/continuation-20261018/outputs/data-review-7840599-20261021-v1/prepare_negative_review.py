"""Pre-prediction original-image negative-review queues, not inferred absence labels."""
import json
from pathlib import Path
R=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
rows=read(R/'DETAILED_REVIEW_ORDER.json')['records']
done={x['id'] for f in R.glob('detailed-*.json') for x in read(f).get('records',[])}
def family(r):
    if r['anchor']=='washing machine':return 'household-laundry'
    if r['anchor']=='traffic sign':return 'traffic-information-signs'
    if r['anchor'] in ('whiteboard','picture frame','computer monitor'):return 'indoor-frames-screens-boards'
    return 'traffic-information-signs' if any(w in r['scene_note'].lower() for w in ('direction','station','motorway','danger','information','road')) else 'shop-business-lettering'
queues={}
for role in ('train','val','test'):
    pool=[dict(r,confuser_family=family(r)) for r in rows if r['role']==role and r['image_id'] not in done
          and r['disposition'] in ('billboard-absence-candidate','non-target-context')]
    if role=='train':
        for fam in ('traffic-information-signs','household-laundry','indoor-frames-screens-boards'):
            queues[role+'-'+fam]=[r for r in pool if r['confuser_family']==fam]
    else:queues[role]=pool
(R/'NEGATIVE_ORIGINAL_REVIEW_QUEUES.json').write_text(json.dumps(dict(
 status='review-order-only-no-absence-assumed',model_predictions_seen=False,approved_for_training=False,
 goals=dict(train_shop_already_reviewed=6,train_each_other_family=8,val_additional_needed=19,test_needed=20),
 queues=queues),indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:[dict(id=r['image_id'],path=r['path'],anchor=r['anchor'],family=r['confuser_family'],role=r['role']) for r in a] for k,a in queues.items()}))

