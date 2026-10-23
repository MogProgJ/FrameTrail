from pathlib import Path
from collections import Counter
import gzip,hashlib,importlib.util,json,re,csv
R=Path('C:\\Users\\nazee\\Documents\\Codex\\2026-10-18\\frametrail-continuation\\outputs\\data-review-7840599-20261021-v1')
BASE=Path('C:\\Users\\nazee\\Documents\\Codex\\2026-10-18\\frametrail-continuation\\outputs\\billboard-targeted-intake-7824179-20261020-v1\\retrieval-7840599\\verified-7840599\\output\\billboard-data-refresh-7840599');OUT=R/'source-review'
OLD=Path(r'C:\Users\nazee\.codex\visualizations\2026\10\11\01a12a01-d564-7de0-91f4-a16484eea2cb')
spec=importlib.util.spec_from_file_location('source_parser',OLD/'source-review-7626978/verify_and_review.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):
 with path.open('x',encoding='utf-8') as f:json.dump(value,f,indent=2,ensure_ascii=False);f.write('\n')
assert sha(BASE/'manifest.json')=='0bd27558ab9ae9f5005492db719e90af37883ee9b9577e5fb0a3afa51028fbd8'
manifest=read(BASE/'manifest.json');assert len(manifest['images'])==180
OUT.mkdir(exist_ok=False)
rows=[]
for n,original in enumerate(manifest['images'],1):
 iid=original['id'];source=read(BASE/'source-receipts'/(iid+'.json'));attribution=original['attribution']
 assert source['source_url']==attribution['landing_url']
 row=dict(image_id=iid,image_sha256=original['sha256'],selected_category=original['selected_category'],selected_domain=original['selected_domain'],prospective_split=original['prospective_split'],source_url=source['source_url'],publisher_attribution=attribution,intake_holds=original['intake_hold_reasons'],rights_verified=False,approved_for_training=False)
 if source['status']!='retrieved-unreviewed':
  row.update(status='hold-source-unavailable',error=source.get('error',''));rows.append(row);continue
 try:
  page=(BASE/source['page_file']).resolve()
  assert page.is_relative_to(BASE.resolve()) and not page.is_symlink()
  with gzip.open(page,'rb') as f:raw=f.read(2_000_001)
  assert len(raw)==source['html_bytes']<=2_000_000 and sha(page)==source['stored_sha256'] and hashlib.sha256(raw).hexdigest()==source['html_sha256']
  parser=p.Parser();parser.feed(raw.decode('utf-8'));source_identity=p.photo(source['source_url'])
  if not source_identity:raise ValueError('Unsupported photo identity')
  source_account,photo_id=source_identity;images=[]
  for script in parser.ld:
   value=json.loads(script);items=value if isinstance(value,list) else value.get('@graph',[value]);images += [x for x in items if isinstance(x,dict) and x.get('@type')=='ImageObject']
  matched=[x for x in images if p.photo(x.get('acquireLicensePage','')) and p.photo(x['acquireLicensePage'])[1]==photo_id]
  if len(matched)!=1:raise ValueError('Photo-specific structured image missing or ambiguous')
  image=matched[0];author=image['author'];links=[x for x in parser.license_links if any('__photoId_'+photo_id+'__' in panel.get('data-view-signature','') for panel in x['panels'])]
  from urllib.parse import unquote
  owners={unquote(re.search(r'__nsid_([^_]+)__',panel['data-view-signature'])[1]) for link in links for panel in link['panels'] if re.search(r'__nsid_([^_]+)__',panel.get('data-view-signature',''))}
  direct=p.account(author['url'])==p.account(attribution['author_url']);alias=source_account in owners and source_account in author.get('image','') and p.account(author['url'])==p.photo(image['acquireLicensePage'])[0]
  og=p.photo(parser.meta.get('og:url',''));nsid=re.search(r'(?:buddyicons/|#)([0-9]+@N[0-9]+)(?:\.jpg|$)',author.get('image',''))
  checks=dict(source_photo_id=bool(og and og[1]==photo_id),original_photo_id=bool(re.search('/'+re.escape(photo_id)+'_',attribution['original_url'])),structured_photo_id=bool(re.search('/'+re.escape(photo_id)+'_',image['contentUrl'])),author_account_or_documented_alias=bool(direct or alias),structured_license_matches_publisher=p.normalized_url(image['license'])==p.normalized_url(attribution['license']),two_photo_panel_links=len(links)==2,photo_panel_links_cc_by_2=bool(links) and all(p.normalized_url(x['attributes'].get('href',''))==('creativecommons.org','/licenses/by/2.0/deed.en') for x in links),photo_panel_titles_cc_by_2=bool(links) and all(x['attributes'].get('title')=='CC BY 2.0' for x in links),stable_author_NSID_present=bool(nsid),panel_owner_matches_structured_NSID=bool(nsid and owners=={nsid[1]}))
  notices=dict(structured={k:image.get(k) for k in ('description','copyrightNotice','creditText','creator')},meta_description=parser.meta.get('description',parser.meta.get('og:description','')))
  row.update(status='photo-specific-license-corroborated' if all(checks.values()) else 'hold-source-check-mismatch',checks=checks,current_creator=author,current_title=parser.meta.get('og:title',''),creator_notices=notices,identity_group='flickr-nsid:'+nsid[1] if nsid else None,structured_license_url=image['license'],canonical_page_url=image['acquireLicensePage'],html_sha256=source['html_sha256'],stored_sha256=source['stored_sha256'],evidence_page=str(page),account_alias_resolved=not direct and alias)
 except (ValueError,KeyError,TypeError,UnicodeDecodeError) as exc:row.update(status='hold-source-parse-or-identity',error=str(exc))
 rows.append(row)
 if n%100==0:print(f'Photo-specific evidence checked {n}/180',flush=True)
report=dict(schema=1,actual_job_id='7840599',intended_use='Private research on user PC and KIT; no public distribution',source_manifest_sha256=sha(BASE/'manifest.json'),status_counts=dict(Counter(x['status'] for x in rows)),images=rows,rights_verified=False,approved_for_training=False,original_files_modified=False,network_requests=0,limits='Offline photo-specific source/author/licence corroboration. Source-content notices, visual content, duplicates, owners and partition gates remain separate. This is not human independent review, blanket rights clearance, annotation approval or training.')
save(OUT/'source-evidence-review.json',report)
with (OUT/'source-review-register.csv').open('x',encoding='utf-8',newline='') as f:
 keys=['image_id','selected_category','selected_domain','status','identity_group','source_url','current_title','structured_license_url','html_sha256','rights_verified','approved_for_training'];w=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore');w.writeheader();w.writerows(rows)
print(json.dumps(dict(status_counts=report['status_counts'],failed_checks=dict(Counter(k for row in rows for k,v in row.get('checks',{}).items() if not v)),unavailable_errors=dict(Counter(x.get('error') for x in rows if x['status']=='hold-source-unavailable'))),indent=2))