import json,hashlib,collections,copy,html,math
from pathlib import Path
from datetime import datetime,timezone
from PIL import Image,ImageDraw,ImageFont
B=Path(r'C:/Users/nazee/.codex/visualizations/2026/10/15/01a141ae-c7a6-7303-a280-403af88736f3')
F=B/'external-datasets-filtered-20261018-v1';O=Path('outputs/external-provenance-quality-20261018-v1')
assert not (O/'FINAL_RECEIPT.json').exists(),'Use a new version after sealing'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
write=lambda n,v:(O/n).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
now=datetime.now(timezone.utc).isoformat();c=read(F/'draft/annotations.partial.coco.json');ds=read(F/'decisions.json');dm={r['id']:r for r in ds};cat={x['id']:x['name'] for x in c['categories']}
# These are observations from the visual pass, never independent human certification.
uncertain={'hanger-003':'Clothing hides most hanger bodies; additional deeply occluded instances cannot be excluded.','hanger-023':'Dense clothing occlusion and a faint repeated stock-style mark; source permission evidence missing.','hanger-053':'Nested bars, clips and clothing conceal parts; three identifiable hangers, unknown hidden instances.','hanger-059':'Edge-truncated narrow hangers and clothing occlusion; eight identifiable positives, hidden instances unknown.'}
leads=[
 {'ids':['toaster-028','toaster-029'],'publisher':'Satori Design for Living / Shauna Oberg','url':'https://satoridesignforliving.com/small-kitchen-appliances-youll-use-and-love-i-do/','proof_id':'satori-2','exact_photo_matches':['toaster-028'],'scene_associations':['toaster-029'],'evidence':'Toaster-028 matches the appliance, hand, bread board, dishes, flowers and chair in the publisher photo. Toaster-029 is the existing confirmed same-scene partner; exact file match remains unresolved. The page attributes the photography to its author.'},
 {'ids':['toaster-021'],'publisher':'Design Dazzle / Toni Roberts','url':'https://www.designdazzle.com/kitchen-remodel-final-reveal/','proof_id':'design-dazzle-4','exact_photo_matches':['toaster-021'],'scene_associations':[],'evidence':'Matching raised cabinet door, support, blender, toaster, outlet and visible Design Dazzle mark.'},
 {'ids':['toaster-022'],'publisher':'ZDesign At Home / Bree','url':'https://www.zdesignathome.com/kitchen-tour/','proof_id':'zdesign-1','exact_photo_matches':['toaster-022'],'scene_associations':[],'evidence':'Matching appliance cabinet, refrigerator edge, slow cooker, toaster and cabinet handles.'},
 {'ids':['toaster-031'],'publisher':'Thou Swell','url':'https://thouswell.com/smart-toaster-toast-recipes-revolution-cooking/','proof_id':'thou-swell-1','exact_photo_matches':['toaster-031'],'scene_associations':[],'evidence':'Matching touchscreen toaster, outlet plates, tile pattern, blue jar, flowers and sliced-bread board.'},
 {'ids':['toaster-043'],'publisher':'Philippe Beauparlant / Hocken Avenue','url':'https://www.beauparlant.ca/spaces/hocken-avenue','proof_id':'beauparlant-8','exact_photo_matches':['toaster-043'],'scene_associations':[],'evidence':'Matching cabinet niche, espresso machine, toaster, cups, shelf, doorway and island edge. Page identifies the design project, not the photographer.'}
]
proofs={p['id']:p for p in read(O/'publisher-proof-index.json')}
for lead in leads:
 p=proofs[lead['proof_id']];lead.update({'photo_url':p['url'],'retrieved_at':now,'rights_verified':False,'reusable_license_found':False,'permission_status':'unresolved','method':'assistant visual comparison of local retained image against headlessly rendered publisher photo','independent_human_review':False})
write('publisher-matches.json',leads)
sources=read(B/'external-datasets-audit-20261018-v1/source-register.json')
for row in sources:
 row['current_page_check']={'tool':'web','result':'retrieved-uploader-license-declaration' if row['archive'].startswith('Cleaning') else 'not-retrievable-by-web-tool','checked_at':now}
 row['upstream_image_rights_verified']=False
write('dataset-source-register.json',sources)
review=[];provenance=[]
for im in c['images']:
 ident=im['external_id'];anns=[a for a in c['annotations'] if a['image_id']==im['id']];counts=collections.Counter(cat[a['category_id']] for a in anns)
 masks={name:{'state':'unknown','positive_annotations':counts.get(name,0),'negative_supervision_allowed':False,'reason':'Class not exhaustively reviewed in this image.'} for name in cat.values()}
 for name in counts:
  masks[name]={'state':'positive-only-unknown-hidden-instances' if ident in uncertain else 'assistant-complete-identifiable-visible-instances','positive_annotations':counts[name],'negative_supervision_allowed':False,'reason':uncertain.get(ident,'All identifiable visible instances of this target class accounted for in this assistant pass. Independent review pending.')}
 note=uncertain.get(ident,'No additional identifiable target-class instance found during this pass.')
 if ident=='toaster-003':note+=' One box tightened to the visible appliance; adjacent cup and excess background removed where possible.'
 review.append({'id':ident,'source_image_sha256':im['sha256'],'counts':dict(counts),'class_scope':masks,'all_other_app_classes':'unknown','unidentifiable_or_fully_occluded_instances':'unknown','scope_definition':'Identifiable visible physical objects, including visible hooks/handles. No inferred hidden extent. No box for printed package pictures, mirrors or object parts.','geometry_valid':True,'annotation_issue':'bbox-refined' if ident=='toaster-003' else 'occlusion-completeness-unknown' if ident in uncertain else 'none-found','note':note,'proof_page':f'proofs/page-{(im["id"]-1)//6+1:02d}.jpg','independent_human_review':False,'approved_for_training':False})
 lead=next((v for v in leads if ident in v['ids']),None)
 provenance.append({'id':ident,'sha256':im['sha256'],'archive':im['source']['archive'],'member':im['source']['member'],'original_source_name':dm[ident]['source_name'],'original_group_id':im['group_id'],'publisher_page':lead['url'] if lead else None,'photo_url':lead['photo_url'] if lead and ident in lead['exact_photo_matches'] else None,'source_status':'suspected-stock-watermark-hold' if ident=='hanger-023' else 'publisher-photo-visually-matched' if lead and ident in lead['exact_photo_matches'] else 'publisher-scene-associated' if lead else 'unresolved-original-photo-source','embedded_exif':'absent','rights_verified':False,'permission_status':'unresolved','next_evidence':'Specific upstream permission/license chain, photographer attribution, and independent annotation review.'})
write('annotation-completeness.json',{'schema':1,'reviewer':'assistant','independent_human_review':False,'negative_supervision_default':'disabled','reviewed_images':58,'images':review})
write('image-provenance.json',provenance)
# Apply only a versioned delta; frozen filtering results remain untouched.
held_family=[r['id'] for r in ds if r['archive'].startswith('hangers') and r['source_name']=='17_jpeg']
newds=copy.deepcopy(ds)
for row in newds:
 if row['id'] in held_family:
  row['prior_disposition']=row['disposition'];row['quality_retained']=False;row['disposition']='suspected-stock-watermark-provenance-hold';row['reason']='Faint repeated stock-style mark on retained representative hanger-023; all three source-family variants require upstream photo evidence.';row['reviewed_annotations']=0
write('effective-decisions.json',newds)
eff=copy.deepcopy(c);eff['images']=[im for im in eff['images'] if im['external_id']!='hanger-023'];held_iid=next(im['id'] for im in c['images'] if im['external_id']=='hanger-023');eff['annotations']=[a for a in eff['annotations'] if a['image_id']!=held_iid]
for im in eff['images']:
 im['file_name']='images/'+im['external_id']+'.jpg';im['completeness_sidecar']='annotation-completeness.json';im['negative_supervision_allowed']=False
for a in eff['annotations']:
 if a['id']==80:
  a['prior_bbox']=a['bbox'];a['bbox']=[260,350,120,54];a['area']=6480;a['origin']='assistant-visible-extent-refinement'
eff['info'].update({'description':'Continuation positive-only draft after provenance hold and one extent refinement. Not a training release.','parent_sha256':sha(F/'draft/annotations.partial.coco.json'),'complete_all_class_annotation':False,'standard_coco_training_safe':False,'negative_supervision_allowed':False,'rights_verified':False})
write('effective.annotations.partial.coco.json',eff)
write('change-register.json',{'parent_unchanged':True,'new_source_family_hold':held_family,'newly_withheld_retained_image':'hanger-023','newly_withheld_boxes':5,'bbox_refinements':[{'image':'toaster-003','annotation_id':80,'old_bbox':[250,333,141.5,84.5],'new_bbox':[260,350,120,54],'reason':'Tighten to visible toaster; avoid cup and background overreach.'}],'positive_boxes_added':0,'app_vocabulary_changed':False})
# Compare recorded exact hashes only; this cannot exclude crops/recompression or common authors.
cohorts=['fresh-street-household-20261017-v1/reviewed-draft.json','new-category-source-pilot-20261017-v1/intake-v3/manifest.json','gap363-catdog-completeness-7787611-v2/effective-broad-draft-v2.json','nextdata-reviewed-release-7769109-v1/candidate-manifest-v2.json']
collisions=[];checks=[]
for rel in cohorts:
 p=B/rel;v=read(p);rows=v['images'];hits=[];usable=0
 for row in rows:
  digest=row.get('sha256') or row.get('image_sha256') or row.get('acquisition',{}).get('sha256')
  if digest:
   usable+=1
   for im in c['images']:
    if digest==im['sha256']:hits.append({'external_id':im['external_id'],'prior_image_id':row.get('id',row.get('image_id'))})
 checks.append({'manifest':str(p),'manifest_sha256':sha(p),'records':len(rows),'records_with_sha256':usable,'exact_hash_matches':hits});collisions.extend(hits)
write('cross-cohort-exact-hash-check.json',{'method':'Compare recorded SHA256 fields in explicitly named manifests; earlier files not rehashed.','checks':checks,'matches':collisions,'limits':'Not a perceptual duplicate, photo-author or scene-family clearance. All evaluation eligibility remains false.'})
# Full-resolution current overlays support the local review gallery.
(O/'overlays').mkdir(exist_ok=True)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15)
for im in c['images']:
 pic=Image.open(O/'images'/f'{im["external_id"]}.jpg').convert('RGB');draw=ImageDraw.Draw(pic)
 aa=eff['annotations'] if im['external_id']!='hanger-023' else c['annotations']
 for a in aa:
  if a['image_id']==im['id']:
   x,y,w,h=a['bbox'];draw.rectangle((x,y,x+w,y+h),outline='#4ade80',width=2);draw.text((x+2,y+2),str(a['id']),font=font,fill='#4ade80',stroke_width=1,stroke_fill='black')
 pic.save(O/'overlays'/f'{im["external_id"]}.jpg',quality=93)
write('RELEASE_GATE.json',{'schema':1,'rights_verified':False,'independent_human_review':False,'approved_for_training':False,'evaluation_eligible':False,'complete_all_class_annotation':False,'standard_coco_training_safe':False,'negative_supervision_allowed':False,'training_started':False,'pending_trial':{'job_id':'7780632','last_report':'pending; no newer scheduler evidence received','scheduler_checked':False,'export_or_adoption':'deferred'},'blockers':['Upstream-image rights unresolved for all 58 source images.','Independent annotation review pending.','Only target classes scoped; other classes and hidden instances unknown.','Cross-cohort author/scene and perceptual-duplicate checks incomplete.','No concrete future training protocol approved.']})
write('summary.json',{'input_frozen_draft_images':58,'input_frozen_positive_boxes':120,'continuation_draft_images':len(eff['images']),'continuation_positive_boxes':len(eff['annotations']),'all_external_files_accounted':len(newds),'held_or_redundant':sum(not r['quality_retained'] for r in newds),'newly_withheld_source_family_files':len(held_family),'publisher_photo_matches':5,'publisher_scene_associations':1,'per_image_class_scope_records':58,'target_completeness_unknown_images':len(uncertain),'assistant_visible_target_complete_images':58-len(uncertain),'bbox_refinements':1,'rights_cleared':0,'new_jobs_submitted':0,'trial_7780632_untouched':True,'earlier_artifacts_untouched':True,'created_at':now})
print(json.dumps(read(O/'summary.json'),indent=2));print('cross_cohort',[(x['records'],x['records_with_sha256'],len(x['exact_hash_matches'])) for x in checks])

