import json,hashlib,collections
from pathlib import Path
from PIL import Image,ImageDraw,ImageOps,ImageFont
B=Path(r'C:/Users/nazee/.codex/visualizations/2026/10/15/01a141ae-c7a6-7303-a280-403af88736f3')
F=B/'external-datasets-filtered-20261018-v1'
O=Path('outputs/external-provenance-quality-20261018-v1');O.mkdir(parents=True,exist_ok=False)
(O/'proofs').mkdir();(O/'images').mkdir()
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
hashes=read(F/'files-sha256.json');checks=[]
for name,expected in hashes.items():
 actual=sha(F/name);assert actual==expected,name
 checks.append({'path':str(F/name),'sha256':actual})
r=read(F/'FINAL_RECEIPT.json')
for name,expected in r['input_archive_sha256'].items():
 p=Path(r'C:/Users/nazee/Downloads/FrameTrail-Datasets')/name
 assert sha(p)==expected;checks.append({'path':str(p),'sha256':expected})
for p,expected in [(B/'external-datasets-audit-20261018-v1/audit-results.json',r['source_audit_sha256']),(B/'external-datasets-audit-20261018-v1/image-index.json',r['source_index_sha256']),(F/r['package'],r['package_sha256'])]:
 assert sha(p)==expected;checks.append({'path':str(p),'sha256':expected})
(O/'INPUT_INTEGRITY.json').write_text(json.dumps({'status':'passed','checks':checks},indent=2))
c=read(F/'draft/annotations.partial.coco.json');decs=read(F/'decisions.json');dm={d['id']:d for d in decs}
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
records=[]
for im in c['images']:
 p=F/'draft'/im['file_name'];body=p.read_bytes();(O/'images'/p.name).write_bytes(body)
 ii=Image.open(p);exif=dict(ii.getexif());records.append({'id':im['external_id'],'source_name':dm[im['external_id']]['source_name'],'exif_tags':list(exif),'image_info_keys':list(ii.info),'group_id':im['group_id']})
(O/'embedded-metadata.json').write_text(json.dumps(records,indent=2))
for start in range(0,58,6):
 batch=c['images'][start:start+6];sh=Image.new('RGB',(1260,920),'#121b2a');dr=ImageDraw.Draw(sh)
 for k,im in enumerate(batch):
  src=Image.open(F/'draft'/im['file_name']).convert('RGB');d=ImageDraw.Draw(src)
  for a in c['annotations']:
   if a['image_id']==im['id']:
    x,y,w,h=a['bbox'];d.rectangle((x,y,x+w,y+h),outline='#ff2020',width=2);d.text((x+2,y+2),str(a['id']),fill='red',font=font,stroke_width=1,stroke_fill='white')
  tile=ImageOps.contain(src,(416,416));x=(k%3)*420;y=(k//3)*460
  sh.paste(tile,(x,y+36));dr.text((x+3,y+5),im['external_id'],fill='white',font=font)
 sh.save(O/'proofs'/f'page-{start//6+1:02d}.jpg',quality=95)
print(json.dumps({'checked_input_hashes':len(checks),'records':records},indent=2))
