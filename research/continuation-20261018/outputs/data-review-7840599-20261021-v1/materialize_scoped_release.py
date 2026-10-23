"""Materialize reviewed fresh additions in the unchanged scoped RF data contract."""
import json,hashlib,shutil
from pathlib import Path
from PIL import Image
R=Path(__file__).resolve().parent
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(p,v):
 with p.open('x',encoding='utf-8') as f:f.write(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
assert read(R/'READINESS_REPORT.json')['ready_for_package_preparation']
release=R/'reviewed-release-v1'
for name in ('images','rights','source-pages'):(release/name).mkdir(exist_ok=True)
images=[]
for r in read(release/'release-detail.json')['records']:
 rev=r['review'];iid=r['image_id'];source=read(rev['source_evidence_ref']['path']);s=source['source_record']
 assert sha(rev['source_evidence_ref']['path'])==rev['source_evidence_ref']['sha256']
 p=release/'images'/(iid+'.jpg');shutil.copyfile(r['image_ref']['path'],p);assert sha(p)==r['image_ref']['sha256']
 with Image.open(p) as im:
  w,h=im.size;assert im.format=='JPEG' and im.getexif().get(274,1)==1
 page=release/'source-pages'/(iid+'.html.gz');shutil.copyfile(s['evidence_page'],page);assert sha(page)==s['stored_sha256']
 rights=release/'rights'/(iid+'.json')
 write(rights,dict(rights_gate='pass-private-research',image_id=iid,image_sha256=r['image_ref']['sha256'],
  source_review=s,source_evidence_ref=rev['source_evidence_ref'],content_scene_review_ref=r['review_ref'],
  attribution=s['publisher_attribution'],reviewer='assistant',independent_human_review=False,
  original_receipts_preserved=True,public_distribution=False))
 targets=[]
 for x1,y1,x2,y2 in rev['normalized_xyxy']:
  targets.append(dict(canonical_id=133,normalized_cxcywh=[(x1+x2)/2,(y1+y2)/2,x2-x1,y2-y1]))
 images.append(dict(image_id=iid,image_sha256=r['image_ref']['sha256'],split=rev['prospective_split'],
  supervision='gold',supervision_meaning='Assistant-reviewed complete class scope; not independent human annotation',
  loss_weight=1,identity_group=rev['identity_group'],scene_group=rev['scene_group'],
  scope={'133':'complete' if targets else 'absent'},targets=targets,
  source_path='images/'+iid+'.jpg',width=w,height=h,rights_verified_private_research=True,
  rights_receipt_path='rights/'+iid+'.json',rights_receipt_sha256=sha(rights),
  content_review_ref=r['review_ref'],confuser_family=rev.get('confuser_family','')))
manifest=dict(contract='frametrail-rf-scoped-release-v1',taxonomy_id='nextdata7769109-taxonomy-v1',
 approved_for_training=True,approved_for_application=False,weak_policy='excluded',
 labels_frozen_before_predictions=True,unknown_classes_remain_unknown=True,images=images,
 readiness_manifest_sha256=sha(release/'readiness-manifest.json'),readiness_report_sha256=sha(R/'READINESS_REPORT.json'),
 source_cohorts=['7824179','7840599'],authorization='Standing user18Oct2026 private research/local qualification instruction; superseding reviewed124-photo receipts',
 limitations='Assistant-reviewed engineering pilot; no independent human annotation claim; evaluation outcomes unknown. Historical23 non-protected originals absent; preserved rendered historical scene references used.')
write(release/'scoped-fresh-additions-v1.json',manifest)
print(json.dumps(dict(photos=len(images),manifest_sha256=sha(release/'scoped-fresh-additions-v1.json'),billboard_targets=sum(len(r['targets']) for r in images))))

