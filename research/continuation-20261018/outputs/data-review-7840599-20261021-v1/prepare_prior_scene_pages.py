"""Make full prior-history visual scene comparison sheets, never infer clearance from hashes."""
import json,hashlib
from pathlib import Path
from PIL import Image,ImageOps,ImageDraw,ImageFont
R=Path(__file__).resolve().parent
P=R.parent/'billboard-data-refresh-7818553-20261018-v1/data-tools-v1/exclusions.json'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
prior=read(P)['images'];assert len(prior)==1931
paths={}
for line in (R/'local-image-inventory.txt').read_text(encoding='utf-8-sig').splitlines():
 p=Path(line)
 if p.stem not in paths:paths[p.stem]=[]
 paths[p.stem].append(p)
rows=[];missing=[]
for r in prior:
 match=next((p for p in paths.get(r['id'],[]) if sha(p)==r['sha256']),None)
 if not match:missing.append(r['id']);continue
 rows.append(dict(id=r['id'],path=str(match),sha256=r['sha256']))
font=ImageFont.truetype(r'C:\Windows\Fonts\segoeui.ttf',12)
pages=[]
for start in range(0,len(rows),64):
 batch=rows[start:start+64];canvas=Image.new('RGB',(2048,1536),'#f5f5f5');d=ImageDraw.Draw(canvas)
 for k,r in enumerate(batch):
  x=(k%8)*256;y=(k//8)*192;d.text((x+2,y+2),r['id'],fill='black',font=font)
  with Image.open(r['path']) as im:
   view=ImageOps.contain(im.convert('RGB'),(250,168));canvas.paste(view,(x+3+(250-view.width)//2,y+21+(168-view.height)//2))
 p=R/('prior-scenes-'+str(start//64+1).zfill(2)+'.jpg');canvas.save(p,quality=97)
 pages.append(dict(path=str(p),records=batch))
(R/'PRIOR_SCENE_REVIEW_PAGES.json').write_text(json.dumps(dict(status='prepared-not-yet-visually-reviewed',prior_ref=dict(path=str(P),sha256=sha(P)),total=len(prior),located=len(rows),missing=missing,pages=pages),indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(total=len(prior),located=len(rows),missing=missing,pages=len(pages))))

