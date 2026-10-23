"""Seal reviewed private-research data assertions; old intake receipts remain unchanged."""
from pathlib import Path
from collections import Counter
import json,hashlib,gzip,re,unicodedata
R=Path(__file__).resolve().parent
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def ref(p):return dict(path=str(Path(p).resolve()),sha256=sha(p))
def write(p,obj):
 with p.open('x',encoding='utf-8') as f:f.write(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
assembly=read(R/'CONTENT_REVIEW_ASSEMBLY_V2.json')
prior=R.parent/'billboard-data-refresh-7818553-20261018-v1/data-tools-v1/exclusions.json'
protected=R.parent/'selector-batch-proposal-7809335-20261018-v1/rf-selector-a77d9663-v1/release/candidate-manifest-v2.json'
sources={};audits={}
for root in (R,R.parent/'data-review-7824179-20261020-v1'):
 p=root/'source-review/source-evidence-review.json'
 for row in read(p)['images']:sources[row['image_id']]=(row,p)
 for row in read(root/'INTAKE_AUDIT.json')['records']:audits[row['image_id']]=row
assert len(assembly['records'])==124
scene_review=dict(status='assistant-visual-scene-and-annotation-review-completed-for-selected-release',
 independent_human_review=False,model_predictions_seen=False,
 assembly_ref=ref(R/'CONTENT_REVIEW_ASSEMBLY_V2.json'),
 content_and_overlay_progress_ref=ref(R/'SCENE_AND_OVERLAY_QA_PROGRESS.json'),
 scene_hold_supersession_ref=ref(R/'DECISION_SUPERSESSION.json'),
 full_prior_visual_reference_ref=ref(R/'PRIOR_SCENE_REVIEW_PAGES.json'),
 historical_render_reference_ref=ref(R/'HISTORICAL_RENDER_REFERENCES.json'),
 historical_path_resolution_ref=ref(R/'HISTORICAL_PATH_RESOLUTION.json'),
 prior_photos_compared=1931,prior_original_photos_visually_compared=1908,prior_rendered_photos_visually_compared=23,
 rendered_reference_pages_viewed=[1,2,3,4],prior_reference_pages_viewed=list(range(1,31)),
 protected_original_photos_missing=0,
 pair_decisions=[
 dict(prior='58be3b0d121716a7',fresh='c169d65520795324',result='different-identifiable-scene',reason='Monterey2009 conference marine-biology presentation versus kitchen/tearoom cartoon board; different visible content, source context and owner.'),
 dict(prior='09c7722c1d5bc718',fresh='3c49b6fe8d3f1115',result='uncertain-venue-overlap-fresh-photo-held',reason='Different view/machines/owner do not establish different laundrette venue; fresh photo excluded.')],
 selected_cross_role_scene_findings='No shared identifiable location/session across selected124 photos after original-image reviews,12role QA pages and replacement-original review. Descriptive scene keys identify physical scene; owner/ID alone is not the scene criterion.',
 prior_scene_findings='No identifiable selected scene overlaps with1931 prior references. All965 protected-release photos are represented by original-byte references;23 non-protected historical originals are unavailable but preserved labelled historical full-scene renders were visually inspected.',
 limitations='Visual/source/identity/hash review is evidence-backed assistant adjudication, not a mathematical guarantee of all possible scene overlap.23 historical original files remain unavailable; preserved renders were used only as historical scene references, never replacement training pixels.',
 boxes='All54positive originals inspected and corrected, then green-box overlays reviewed. No unresolved material/completeness/geometry case counted.',
 frozen_roles='Prospective train/val/test retained; no model outcomes used for curation; laundrette replacement occurred before any predictions.')
write(R/'FINAL_SCENE_AND_ANNOTATION_REVIEW.json',scene_review)
release_dir=R/'reviewed-release-v1';release_dir.mkdir(exist_ok=False);reviews=release_dir/'reviews';reviews.mkdir();evidence=release_dir/'source-evidence';evidence.mkdir()
entries=[];full=[];scenes=set();owners=set();counts=Counter()
prior_ids={x['id'] for x in read(prior)['images']};prior_hashes={x['sha256'] for x in read(prior)['images']}
for r in assembly['records']:
 iid=r['image_id'];d=r['content_decision'];s,sp=sources[iid];audit=audits[iid]
 assert s['status']=='photo-specific-license-corroborated' and all(s['checks'].values())
 assert s['image_sha256']==r['sha256']==sha(r['path'])
 assert s['prospective_split']==r['role'] and s['identity_group']==r['identity_group']
 assert not audit['known_exact_duplicate'] and not audit['known_prior_identity'] and not audit['prior_perceptual_candidates'] and not audit['new_perceptual_candidates']
 assert iid not in prior_ids and r['sha256'] not in prior_hashes
 assert iid not in ('9b5635760011caeb','2dee13f2d925574c','3c49b6fe8d3f1115')
 text=json.dumps(s.get('creator_notices',{}))+' '+str(s.get('current_title',''))
 assert not re.search(r'PhotoRepost|Flickr Toys|bighugelabs|not for AI|no machine learning|do not train',text,re.I)
 page=Path(s['evidence_page']);assert sha(page)==s['stored_sha256']
 assert hashlib.sha256(gzip.decompress(page.read_bytes())).hexdigest()==s['html_sha256']
 scene='scene:'+re.sub('[^a-z0-9]+','-',unicodedata.normalize('NFKD',d['scene_description']).encode('ascii','ignore').decode().lower()).strip('-')
 assert scene not in scenes and r['identity_group'] not in owners
 scenes.add(scene);owners.add(r['identity_group'])
 source_path=evidence/(iid+'.json')
 write(source_path,dict(image_id=iid,image_sha256=r['sha256'],reviewer='assistant',independent_human_review=False,
   scope='Private research on user PC/KIT; attribution retained; no public redistribution authorized by this release.',
   status='photo-specific-source-license-and-creator-review-cleared-for-private-research',
   source_review_bundle_ref=ref(sp),source_record=s,stored_page_ref=ref(page),
   intended_use_authorization='Standing FrameTrail instructions18Oct2026, autonomous local review and bounded research continuation',
   decision='Publisher and current photo-specific CC BY2.0 metadata, photo identifiers, NSID owner and attribution corroborate. No identified conflicting source notice, repost or mockup evidence in selected record or inspected photo.',
   limits='Source evidence corroboration is not a blanket legal warranty about independently held rights in depicted material.'))
 kind='positive' if d['disposition']=='complete-positive-content-reviewed' else 'absent'
 role={'train':'fresh_train','val':'fresh_validation','test':'fresh_test'}[r['role']]
 review=dict(image_id=iid,image_sha256=r['sha256'],identity_group=r['identity_group'],scene_group=scene,
   source_evidence_ref=ref(source_path),rights_status='cleared-for-private-research',model_predictions_seen=False,
   duplicate_and_scene_review=dict(complete=True,compared_against_prior_sha256=sha(prior),scene_session_overlap_with_protected=False,evidence_ref=ref(R/'FINAL_SCENE_AND_ANNOTATION_REVIEW.json')),
   other_unknown_classes_remain_unknown=True,billboard_scope='billboard-complete-positive' if kind=='positive' else 'billboard-whole-photo-absent',
   normalized_xyxy=d['normalized_xyxy'],content_review_ref=r['content_review_ref'],
   content_decision=d,prospective_split=r['role'],confuser_family=d.get('confuser_family',''),reviewer='assistant',independent_human_review=False)
 review_path=reviews/(iid+'.json');write(review_path,review)
 entry=dict(image_id=iid,split=role,image_ref=dict(path=r['path'],sha256=r['sha256']),review_ref=ref(review_path))
 entries.append(entry);full.append(dict(entry,review=review))
 counts[role,kind]+=1
manifest=dict(schema='frametrail-billboard-readiness-v1',taxonomy_id='nextdata7769109-taxonomy-v1',
 protected_release_ref=ref(protected),prior_intakes_ref=ref(prior),records=entries,
 fresh_cohorts=['7824179','7840599'],scope='Private research addition; validation/test frozen before predictions; billboard-only label scope.',
 history_boundary='1931photos acquired before these two prospective fresh cohorts.7840599 additionally checked against2171history including7824179; cross-cohort identities/bytes/scenes reviewed. No old intake removed to qualify a fresh photo.',
 production_adoption=False)
write(release_dir/'readiness-manifest.json',manifest)
write(release_dir/'release-detail.json',dict(schema='frametrail-reviewed-billboard-additions-v1',counts=[dict(role=k[0],kind=k[1],photos=v) for k,v in sorted(counts.items())],scene_review_ref=ref(R/'FINAL_SCENE_AND_ANNOTATION_REVIEW.json'),records=full,training_not_started=True,production_adoption=False))
print(json.dumps(dict(photos=len(entries),scenes=len(scenes),counts=[dict(role=k[0],kind=k[1],photos=v) for k,v in sorted(counts.items())],manifest_ref=ref(release_dir/'readiness-manifest.json'))))

