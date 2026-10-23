"""Recover only missing historical review bytes; exact pinned SHA required, no new dataset acquisition."""
import json,urllib.request,hashlib
from pathlib import Path
R=Path(__file__).resolve().parent
old=Path(r'C:\Users\nazee\.codex\visualizations\2026\10\11\01a12a01-d564-7de0-91f4-a16484eea2cb')
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
missing=read(R/'PRIOR_SCENE_REVIEW_PAGES.json')['missing']
prior={r['id']:r for r in read(R.parent/'billboard-data-refresh-7818553-20261018-v1/data-tools-v1/exclusions.json')['images']}
source={r['id']:r for r in read(old/'photo-qa-closeout-20261011/annotations-assistant-reviewed-v5.json')['images']}
dst=R/'historical-photo-recovery';dst.mkdir(exist_ok=True);rows=[]
for iid in missing:
 s=source.get(iid);row=dict(id=iid,status='missing-source-record')
 if s:
  url=s['attribution']['original_url'];row.update(url=url,anchor=s.get('anchor'),title=s['attribution'].get('title'))
  try:
   assert url.startswith('https://') and 'staticflickr.com/' in url
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'FrameTrail historical evidence recovery'}),timeout=20) as response:
    data=response.read(40_000_001)
   assert len(data)<=40_000_000
   if hashlib.sha256(data).hexdigest()!=prior[iid]['sha256']:raise ValueError('Historical byte SHA mismatch; no substitute accepted')
   p=dst/(iid+'.jpg');p.write_bytes(data);row.update(status='exact-historical-bytes-recovered',path=str(p),sha256=prior[iid]['sha256'])
  except Exception as e:row.update(status='historical-recovery-unavailable',error=str(e))
 rows.append(row)
 (R/'HISTORICAL_PHOTO_RECOVERY.json').write_text(json.dumps(dict(no_new_training_photos=True,records=rows),indent=2)+'\n',encoding='utf-8')
print(json.dumps(rows))

