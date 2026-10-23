"""Assemble pre-prediction content decisions and render annotation/scene QA; no release approval."""
import json, hashlib
from pathlib import Path
from collections import Counter
from PIL import Image, ImageDraw, ImageFont, ImageOps
R=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
meta={r['image_id']:r for r in read(R/'DETAILED_REVIEW_ORDER.json')['records']}
superseded={r['id'] for r in read(R/'DECISION_SUPERSESSION.json')['records']}
selected=[];done={}
for f in sorted(R.glob('detailed-*.json')):
 for d in read(f).get('records',[]):
  if d['id'] in done:raise ValueError(('Repeated decision',d['id'],f,done[d['id']]))
  done[d['id']]=str(f)
  if d['id'] in superseded:continue
  if d['disposition'] not in ('complete-positive-content-reviewed','whole-photo-billboard-absent-content-reviewed'):continue
  r=meta[d['id']]
  assert sha(r['path'])==r['sha256']
  selected.append(dict(r,content_decision=d,content_review_ref=dict(path=str(f),sha256=sha(f))))
selected.sort(key=lambda r:(r['role'],r['content_decision']['disposition'],r['order_key']))
counts=Counter((r['role'],r['content_decision']['disposition']) for r in selected)
assert len(selected)==124,(len(selected),counts)
font=ImageFont.truetype(r'C:\Windows\Fonts\segoeui.ttf',15)
pages=[]
for role in ('train','val','test'):
 for kind in ('complete-positive-content-reviewed','whole-photo-billboard-absent-content-reviewed'):
  subset=[r for r in selected if r['role']==role and r['content_decision']['disposition']==kind]
  for start in range(0,len(subset),12):
   batch=subset[start:start+12];canvas=Image.new('RGB',(1600,1230),'#f7f7f7');draw=ImageDraw.Draw(canvas)
   for k,r in enumerate(batch):
    x=(k%4)*400;y=(k//4)*410
    draw.text((x+3,y+3),r['image_id']+' '+role,font=font,fill='black')
    with Image.open(r['path']) as im:
     im=im.convert('RGB');idraw=ImageDraw.Draw(im)
     for j,b in enumerate(r['content_decision']['normalized_xyxy']):
      x1,y1,x2,y2=b;idraw.rectangle((x1*im.width,y1*im.height,x2*im.width,y2*im.height),outline='#00ff50',width=3)
      idraw.text((x1*im.width+3,y1*im.height+2),str(j+1),font=font,fill='#00ff50')
     view=ImageOps.contain(im,(394,350));canvas.paste(view,(x+3+(394-view.width)//2,y+30+(350-view.height)//2))
    text=r['content_decision'].get('scene_description','')
    draw.text((x+3,y+381),text[:49],font=font,fill='black')
   path=R/('qa-v2-'+role+'-'+('positive' if kind.startswith('complete') else 'absent')+'-'+str(start//12+1)+'.jpg')
   canvas.save(path,quality=96);pages.append(dict(path=str(path),ids=[r['image_id'] for r in batch]))
obj=dict(status='content-reviewed-pending-final-source-scene-and-box-qa',model_predictions_seen=False,approved_for_training=False,counts=[dict(role=k[0],kind=k[1],photos=n) for k,n in sorted(counts.items())],records=selected,pages=pages)
(R/'CONTENT_REVIEW_ASSEMBLY_V2.json').write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(counts=obj['counts'],pages=pages)))

