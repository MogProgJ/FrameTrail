"""Resolve historical paths by bytes and export scene-match pairs for direct review."""
import json,hashlib
from pathlib import Path
from PIL import Image,ImageOps,ImageDraw,ImageFont
R=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
prior=read(R/'PRIOR_SCENE_REVIEW_PAGES.json')
exclusions=read(Path(prior['prior_ref']['path']))['images']
missing={r['sha256']:r['id'] for r in exclusions if r['id'] in prior['missing']}
found={}
for line in (R/'expanded-local-image-inventory.txt').read_text(encoding='utf-8-sig').splitlines():
 p=Path(line)
 if p.stem in {r['id'] for r in exclusions}:continue
 digest=sha(p)
 if digest in missing:found[missing[digest]]=str(p)
allprior={r['id']:r['path'] for page in prior['pages'] for r in page['records']}
fresh={r['image_id']:r for r in read(R/'CONTENT_REVIEW_ASSEMBLY.json')['records']}
font=ImageFont.truetype(r'C:\Windows\Fonts\segoeui.ttf',18)
pairs=[]
for old,new in [('58be3b0d121716a7','c169d65520795324'),('09c7722c1d5bc718','3c49b6fe8d3f1115')]:
 canvas=Image.new('RGB',(1800,1100),'white');d=ImageDraw.Draw(canvas)
 for k,(iid,p) in enumerate([(old,allprior[old]),(new,fresh[new]['path'])]):
  d.text((k*900+8,8),('PRIOR ' if k==0 else 'FRESH ')+iid,font=font,fill='black')
  with Image.open(p) as im:
   view=ImageOps.contain(im.convert('RGB'),(880,1040));canvas.paste(view,(k*900+8+(880-view.width)//2,45+(1040-view.height)//2))
 p=R/('scene-pair-'+old+'-'+new+'.jpg');canvas.save(p,quality=97);pairs.append(str(p))
release=read(R.parent/'selector-batch-proposal-7809335-20261018-v1/rf-selector-a77d9663-v1/release/candidate-manifest-v2.json')
protected={r['image_id'] for r in release['images']}
output=dict(found_by_hash=found,still_missing=[i for i in prior['missing'] if i not in found],protected_missing=sorted(protected & set(prior['missing'])-set(found)),pairs=pairs)
(R/'HISTORICAL_PATH_RESOLUTION.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
print(json.dumps(output))

