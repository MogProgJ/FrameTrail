"""Read-only analytical contact sheets, preserving pixels/aspect; no augmentation or predictions."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT=Path(__file__).resolve().parent
rows=json.loads((ROOT/'VISUAL_REVIEW_QUEUE.json').read_text())['records']
font=ImageFont.truetype(r'C:\Windows\Fonts\segoeui.ttf',14)
folder=ROOT/'review-sheets';folder.mkdir(exist_ok=True)
pages=[]
for group in ('billboard','contrast'):
    selected=[r for r in rows if (r['anchor']=='billboard')==(group=='billboard')]
    for start in range(0,len(selected),20):
        batch=selected[start:start+20];canvas=Image.new('RGB',(1280,1320),'#f4f4f4');draw=ImageDraw.Draw(canvas)
        for index,row in enumerate(batch):
            x=(index%4)*320;y=(index//4)*264
            draw.text((x+5,y+3),f"{index+1:02} {row['image_id']} {row['role']}",font=font,fill='black')
            draw.text((x+5,y+23),row['anchor'],font=font,fill='#333333')
            with Image.open(row['path']) as image:
                view=ImageOps.contain(image.convert('RGB'),(312,212))
                canvas.paste(view,(x+4+(312-view.width)//2,y+48+(212-view.height)//2))
        name=f'{group}-{start//20+1:02}.jpg';canvas.save(folder/name,quality=95)
        pages.append({'file':str(folder/name),'records':batch})
(ROOT/'REVIEW_SHEETS.json').write_text(json.dumps({'method':'Contact sheets for initial scene triage only. Uncertain scopes/boxes require full-resolution inspection. No detector predictions.','pages':pages},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'billboards':sum(r['anchor']=='billboard' for r in rows),'contrasts':sum(r['anchor']!='billboard' for r in rows),'pages':len(pages)}))
