"""Create inspectable TRAIN error figures from already saved predictions only."""
import json, hashlib, math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ROOT = Path(r'C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\outputs')
BATCH = ROOT / 'fresh-selector-batch-20261022-v1'
D = BATCH / 'postrun-train-diagnosis-7870268-v1'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    assert read(D / 'REPORT.json')['status'] == 'fixed-final-state-TRAIN-diagnosis-completed'
    destination = D / 'review'
    destination.mkdir(exist_ok=False)
    records = {r['image_id']:r for r in read(ROOT / 'fresh-paired-controls-20261021-v1/INPUTS.json')['records'] if r['row']['split']=='train'}
    states = ['M1-17-1500','M1-29-1500','M0-17-1500','M0-29-1500']
    results = {s:read(D / f'{s}.json') for s in states}
    counters = {s:{r['image_id']:r for r in v['metrics']['per_image']} for s,v in results.items()}
    ids = sorted({r['image_id'] for v in results.values() for r in v['metrics']['per_image'] if r['complete_fp']})
    queue = []
    for iid in ids:
        r = records[iid]; row = r['row']; assert row['split']=='train'
        state = next(s for s in states if counters[s][iid]['complete_fp'])
        photo = Path(r['base']) / row['source_path']
        assert sha(photo)==row['image_sha256']
        queue.append(dict(image_id=iid,pool=r['pool'],family=row.get('confuser_family'),scene=row.get('scene_group'),
                          source_path=str(photo),image_sha256=row['image_sha256'],display_state=state,
                          counts={s:{k:counters[s][iid][k] for k in ['complete_tp','complete_fp','complete_fn']} for s in states}))
    queue.sort(key=lambda r:(r['pool'],r['family'] or '',r['image_id']))
    font = ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf', 17)
    figures = []
    for start in range(0,len(queue),9):
        part = queue[start:start+9]
        sheet = Image.new('RGB',(1536,80+470*math.ceil(len(part)/3)), '#f7f7f7')
        drawing = ImageDraw.Draw(sheet)
        drawing.text((16,10),'FrameTrail: fixed final TRAIN false alarms; orange = predictions, green = frozen targets',font=font,fill='#111111')
        drawing.text((16,35),'Illustrative diagnostic views only. Original labels/splits unchanged. No new inference or selection.',font=font,fill='#444444')
        for index,item in enumerate(part):
            r=records[item['image_id']];row=r['row'];state=item['display_state']
            with Image.open(item['source_path']) as original:
                photo=original.convert('RGB');photo.thumbnail((494,350))
            left=(index%3)*512+9; top=80+(index//3)*470
            x=left+(494-photo.width)//2; y=top+92
            sheet.paste(photo,(x,y));sx=photo.width/row['width'];sy=photo.height/row['height']
            for target in row['targets']:
                if target['canonical_id']!=133:continue
                cx,cy,w,h=target['normalized_cxcywh']
                box=[x+(cx-w/2)*photo.width,y+(cy-h/2)*photo.height,x+(cx+w/2)*photo.width,y+(cy+h/2)*photo.height]
                drawing.rectangle(box,outline='#00bd5a',width=4)
            for prediction in results[state]['predictions'][item['image_id']]:
                a,b,c,d=prediction['box'];drawing.rectangle([x+a*sx,y+b*sy,x+c*sx,y+d*sy],outline='#ff6600',width=3)
            counts=item['counts'][state]
            for line,text in enumerate([item['image_id'],item['pool']+' / '+str(item['family'] or 'original review scope'),state+f"  TP {counts['complete_tp']} FP {counts['complete_fp']} FN {counts['complete_fn']}"]):
                drawing.text((left,top+line*25),text,font=font,fill='#111111')
        path=destination / f'TRAIN-errors-{start//9+1}.jpg';sheet.save(path,quality=92)
        figures.append(str(path))
    payload=dict(status='stored-TRAIN-predictions-review-queue',photos=len(queue),queue=queue,figures=figures,
                 selection_allowed=False,labels_changed=False,validation_photos_probed=0,test_photos_used=0)
    (destination/'REVIEW_QUEUE.json').write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(photos=len(queue),figures=figures),indent=2))
if __name__=='__main__': main()
