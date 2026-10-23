"""Historical render references for scene comparison only; never training pixels."""
from pathlib import Path
import json,hashlib
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parent
O=Path(r'C:\Users\nazee\.codex\visualizations\2026\10\04\01a10654-052b-7933-b51b-b32609e31e2e\annotation-proof-20261010')
A=Path(r'C:\Users\nazee\.codex\visualizations\2026\10\11\01a12a01-d564-7de0-91f4-a16484eea2cb\photo-qa-closeout-20261011\annotations-assistant-reviewed-v5.json')
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
missing=set(read(R/'PRIOR_SCENE_REVIEW_PAGES.json')['missing'])
rows=[r for r in read(A)['images'] if r['id'] in missing]
assert len(rows)==23
sheets=[];references=[]
for start in range(0,len(rows),6):
 batch=rows[start:start+6];canvas=Image.new('RGB',(1800,2250),'white')
 for j,r in enumerate(batch):
  number=r['number'];base=((number-1)//6)*6+1;p=O/('photos-'+str(base).zfill(2)+'-'+str(base+5).zfill(2)+'.jpg')
  slot=(number-1)%6
  with Image.open(p) as im:
   assert im.size==(1800,2250),im.size
   cell=im.crop(((slot%2)*900,(slot//2)*750,(slot%2+1)*900,(slot//2+1)*750))
   canvas.paste(cell,((j%2)*900,(j//2)*750))
  references.append(dict(id=r['id'],number=number,original_sha256=r['sha256'],render_ref=dict(path=str(p),sha256=sha(p)),cell_index=slot))
 p=R/('historical-render-scenes-'+str(start//6+1)+'.jpg');canvas.save(p,quality=97)
 sheets.append(dict(path=str(p),ids=[r['id'] for r in batch]))
(R/'HISTORICAL_RENDER_REFERENCES.json').write_text(json.dumps(dict(purpose='Scene comparison only; originals unavailable; labelled preserved historical rendered photos identify IDs visually. No reconstructed or substituted training bytes.',annotation_ref=dict(path=str(A),sha256=sha(A)),references=references,sheets=sheets),indent=2)+'\n',encoding='utf-8')
print(json.dumps(sheets))

