"""Separate posthoc validation case review from new TRAIN-only annotation work."""
import json,hashlib
from pathlib import Path
D=Path(__file__).resolve().parent;T=D.parent/'selector-batch-proposal-7809335-20261018-v1/rf-selector-a77d9663-v1'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
release=read(T/'release/candidate-manifest-v2.json');rows={r['image_id']:r for r in release['images']};inventory=read(D/'REVIEW_INVENTORY.json');pools=read(T/'sampling-pools.json')
notes={
'00320a4009f3dcd1':('billboard_present','Large outdoor wall advertisement visible; an empty billboard support is also visible. No per-box truth asserted.'),
'058f5d1672575fd1':('non_billboard_context','Construction hoarding with architectural scene, taxis and windows; not an advertising billboard in the reviewed candidate area.'),
'0ca79618fd149cef':('non_billboard_context','Post-office indoor counters and small service-information panels.'),
'15e8210bd3027289':('non_billboard_context','Laundromat washing instructions/pricing panel.'),
'26e6ff40f73e9155':('non_billboard_context','Domestic kitchen, cupboards and appliances.'),
'279e143d052378ac':('non_billboard_context','Apartment furniture, bookshelf and small framed artwork.'),
'30772ab8300b3373':('non_billboard_context','Framed indoor political poster above kitchen worktop.'),
'496394d40a8afaed':('non_billboard_context','Laundry room with small operating/price notices.'),
'5681845c0d5842e8':('non_billboard_context','Kitchen utensils, cooker and printed consumer packaging.'),
'581c3ad380cdda47':('non_billboard_context','Building doorway and boutique shop lettering.'),
'5e7a5e5bc66b385c':('ambiguous_hold','Hazy high-rise facade has small distant display panels; extent/content cannot be established confidently.'),
'6369620037a286fa':('non_billboard_context','Domestic dining furniture and window blinds.'),
'767a795580355bb3':('ambiguous_hold','Furniture showroom with small sale/price panels; billboard size/category boundary unresolved.'),
'784cbb5bef87fa5e':('non_billboard_context','Shop-front lettering, small store notices and a regulatory parking sign.'),
'87124b264970d627':('non_billboard_context','Hotel name and reception lettering on facade.'),
'8e18b1ffb95ae971':('non_billboard_context','Framed pictures in a dining/lounge interior.'),
'95fc279e6ab4f289':('ambiguous_hold','Street has a bus and distant small facade/advertisement details; per-box semantics need closer annotation.'),
'95ffb1dd18fae849':('ambiguous_hold','Mall facade/signage and taxis; cannot establish physical advertisement-panel extent for every proposed box.'),
'9b4fbfc458b2bf22':('non_billboard_context','Instructions and branding printed on a clothing donation bin, not a separate advertising board.'),
'9e0f4f1f62314d54':('non_billboard_context','Domestic living room, glass doors, framed pictures and reflections.'),
'ac49abf832a3e17d':('non_billboard_context','Building facade, monument and small street-information cases; no clear billboard in the reviewed candidate context.'),
'c5daf51ea9fb3442':('ambiguous_hold','Appliance showroom has large brand display/price signage; boundary with physical advertising board is not sufficiently clear.'),
'ccc524fc3e3648d0':('non_billboard_context','Model-kit box illustration/consumer packaging.'),
'cffdb86a52363a3d':('ambiguous_hold','Construction site with commercial notices and a large flexible branded banner; rigid-panel/category boundary held.'),
'dc9cddc9719c580f':('ambiguous_hold','Cafe facade lettering plus home-delivery advertising notice; mixed signage types require per-panel adjudication.'),
'de4fa41e441142d9':('non_billboard_context','Domestic office, framed pictures, monitor and lamps.'),
'defea01c277fdf13':('non_billboard_context','Projected presentation slide on an indoor screen.'),
'e03fe5a2690d8c98':('non_billboard_context','Shop names/lettering and small entrance notices.'),
'fe7d07f45b85847e':('non_billboard_context','Emergency roadstrip warning/direction sign.'),
'ffc3d3a817840cbd':('non_billboard_context','Restaurant interior with decorative lettering on glass.')}
assert set(notes)=={r['image_id'] for r in inventory['unknown']}
review=dict(status='posthoc-diagnostic-scene-review-only',reviewer='assistant visual review of all30original validation photos',independent_human_review=False,original_labels_scopes_selection_and_metrics_unchanged=True,validation_images_enter_training=False,not_new_ground_truth=True,records=[dict(image_id=i,image_sha256=rows[i]['image_sha256'],split=rows[i]['split'],disposition=v[0],note=v[1],predictions_already_consumed=True) for i,v in notes.items()])
(D/'POSTHOC_VALIDATION_REVIEW.json').write_text(json.dumps(review,indent=2)+'\n',encoding='utf-8')
train_notes={'2bfeb40d33db01ca':'Magic Auto Center and liquor business boards: hold size/shop-sign boundary.','4ee1c6ca28a1bdb8':'Cafe business-name sign: hold category boundary.','9382cfa97e1581e0':'Bay Cruises business-name/direction board: hold category boundary.'}
(D/'TRAIN_POSITIVE_REVIEW.json').write_text(json.dumps(dict(status='visual-training-positive-audit-no-label-changes',reviewer='assistant full-original-photo review of20TRAINphotos',definition_source='nextdata7769109-taxonomy-v1 billboard: large physical advertising boards; distinguish traffic signs/shop lettering',records=[dict(image_id=r['image_id'],image_sha256=rows[r['image_id']]['image_sha256'],positive_targets=sum(t['canonical_id']==133 for t in r['targets']),disposition='category_boundary_hold' if r['image_id'] in train_notes else 'advertising_panel_context_supported',note=train_notes.get(r['image_id'],'Visible physical advertising panels support positive image context; no claim of exhaustive instance/box reannotation.')) for r in inventory['train']],original_release_unchanged=True),indent=2)+'\n',encoding='utf-8')
exclude=set(sum(pools.values(),[]));train={i:r for i,r in rows.items() if r['split']=='train' and i not in exclude and r['scope'].get('133','unknown')=='unknown'}
house=sorted(i for i,r in train.items() if any(t['canonical_id']==593 for t in r['targets']))[:12]
signs=sorted(i for i,r in train.items() if any(t['canonical_id'] in (571,11) for t in r['targets']))[:12]
assert len(house)==len(signs)==12 and not set(house)&set(signs)
out=dict(status='fixed-training-only-review-candidates-no-absence-inferred',selection='First12sorted eligible washing-machine TRAIN photos and first12sorted eligible traffic/stop-sign TRAIN photos, excluding all previous sampled pools. Chosen before their visual review; no validation images included.',records=[dict(image_id=i,image_sha256=train[i]['image_sha256'],source_path=str(T/'release'/train[i]['source_path']),split='train',review_type='whole_photo_absence_candidate' if i in house else 'existing_sign_region_negative_candidate',sign_regions=[t for t in train[i]['targets'] if t['canonical_id'] in (571,11)]) for i in house+signs])
(D/'NEW_TRAIN_REVIEW_CANDIDATES.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(posthoc_scene_dispositions={v:sum(x[0]==v for x in notes.values()) for v in sorted({x[0] for x in notes.values()})},TRAIN_household_candidates=house,TRAIN_sign_candidates=signs),indent=2))
