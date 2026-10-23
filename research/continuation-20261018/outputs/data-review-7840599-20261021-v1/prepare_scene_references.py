"""Known-regression billboard scene reference; source manipulation-notice screening."""
import json,re,hashlib
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
R=Path(__file__).resolve().parent
O=R.parent/'data-review-7824179-20261020-v1'
T=R.parent/'selector-batch-proposal-7809335-20261018-v1/rf-selector-a77d9663-v1/release'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
rows=[r for r in read(T/'candidate-manifest-v2.json')['images'] if any(t['canonical_id']==133 for t in r['targets'])]
rows.sort(key=lambda r:(r['split'],r['image_id']))
font=ImageFont.truetype(r'C:\Windows\Fonts\segoeui.ttf',14)
sheets=[]
for start in range(0,len(rows),12):
    batch=rows[start:start+12];canvas=Image.new('RGB',(1536,1152),'#f4f4f4');draw=ImageDraw.Draw(canvas)
    for i,r in enumerate(batch):
        x=(i%4)*384;y=(i//4)*384
        draw.text((x+4,y+4),r['image_id']+' '+r['split'],font=font,fill='black')
        p=T/r['source_path']
        with Image.open(p) as im:
            view=ImageOps.contain(im.convert('RGB'),(376,350));canvas.paste(view,(x+4+(376-view.width)//2,y+30+(350-view.height)//2))
    p=R/('known-billboard-scenes-'+str(start//12+1)+'.jpg');canvas.save(p,quality=96)
    sheets.append(dict(path=str(p),records=[dict(id=r['image_id'],role=r['split']) for r in batch]))
flags=[]
for root in (O,R):
    for r in read(root/'source-review/source-evidence-review.json')['images']:
        if r['status']!='photo-specific-license-corroborated':continue
        text=' '.join([str(r.get('current_title','')),str(r.get('creator_notices',{}))])
        hits=re.findall(r"flickr toys|created with|photofunia|bighugelabs|photoshop|photo montage|photomontage|mosaic|digitally|manipulat|fake|collage",text,re.I)
        if hits:flags.append(dict(id=r['image_id'],role=r['prospective_split'],hits=hits,title=r.get('current_title'),notices=r.get('creator_notices')))
(R/'SOURCE_MANIPULATION_NOTICE_CANDIDATES.json').write_text(json.dumps(dict(candidates=flags,flags_are_manual_review_candidates_not_automatic_exclusions=True),indent=2)+'\n',encoding='utf-8')
(R/'KNOWN_BILLBOARD_SCENE_SHEETS.json').write_text(json.dumps(dict(sheets=sheets,limits='Known31positive-regression scenes only; does not establish all1931/2171 prior-image scene clearance by itself.'),indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(sheets=sheets,manipulation_candidates=flags),ensure_ascii=False))

