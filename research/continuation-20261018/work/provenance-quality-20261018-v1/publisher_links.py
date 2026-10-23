import json,urllib.request,re
from pathlib import Path
O=Path('outputs/external-provenance-quality-20261018-v1')
pages={
 'satori':'https://satoridesignforliving.com/small-kitchen-appliances-youll-use-and-love-i-do/',
 'design-dazzle':'https://www.designdazzle.com/kitchen-remodel-final-reveal/',
 'zdesign':'https://www.zdesignathome.com/kitchen-tour/',
 'thou-swell':'https://thouswell.com/smart-toaster-toast-recipes-revolution-cooking/',
 'beauparlant':'https://www.beauparlant.ca/spaces/hocken-avenue'}
result=[]
for key,url in pages.items():
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
  with urllib.request.urlopen(req,timeout=20) as r:body=r.read().decode('utf-8',errors='replace');status=r.status
  tags=re.findall(r'<img\b[^>]*>',body,re.I)
  imgs=[]
  for tag in tags:
   attrs=dict(re.findall(r'([\w-]+)=[\"\x27](.*?)[\"\x27]',tag,re.S))
   imgs.append({k:v for k,v in attrs.items() if k in ['src','data-src','data-lazy-src','alt','srcset']})
  row={'id':key,'url':url,'status':status,'images':imgs}
 except Exception as e:row={'id':key,'url':url,'error':str(e)}
 result.append(row)
 print(key,row.get('status',row.get('error')))
(O/'publisher-image-links.json').write_text(json.dumps(result,indent=2))
for r in result:
 print(r['id'],json.dumps(r.get('images',[])[:35],indent=2)[:11000])
