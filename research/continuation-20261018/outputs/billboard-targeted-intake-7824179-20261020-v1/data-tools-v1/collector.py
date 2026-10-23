"""Deterministic bounded data intake; unknown labels stay unknown; no inference."""
import argparse,gzip,hashlib,json,math,re,sqlite3,time,urllib.parse,urllib.request
from pathlib import Path
import photo_transport as transport
import source_transport as source
T=Path(__file__).resolve().parent
read=transport.read;sha=transport.sha;save=transport.save
def group(value):
    u=urllib.parse.urlsplit(value);m=re.match(r'^/(?:people|photos)/([^/]+)',u.path)
    return 'flickr:'+m[1].lower() if u.hostname in ('flickr.com','www.flickr.com') and m else value.lower().rstrip('/')
def split_for(author,seed):
    bucket=int(hashlib.sha256((seed+':split:'+author).encode()).hexdigest(),16)%10
    return 'test' if bucket<2 else 'val' if bucket<4 else 'train'
def check_seal():
    seal=read(T/'package-files.json')
    for rel,digest in seal['files'].items():
        p=Path(rel)
        if p.is_absolute() or '..' in p.parts or (T/p).is_symlink() or sha(T/p)!=digest:raise ValueError('Changed/escaping package '+rel)
    plan=read(T/'collection-plan.json')
    if sha(T/'exclusions.json')!=plan['exclusions_sha256'] or sha(T/'classes-source.json')!=plan['classes_source_sha256']:raise ValueError('Changed history/classes')
    return plan
def remaining_image_budget(directory,plan):
    return max(0,plan['maximum_original_bytes']-transport.payload_bytes(directory))
def select_rows(db,plan,excluded,classes):
    oldids={r['id'] for r in excluded['images']};oldgroups={group(r.get(k,'')) for r in excluded['images'] for k in ('group_id','author_alias','author_url') if r.get(k)};oldgroups.update(group(x) for x in excluded.get('known_current_identity_groups',[]))
    used=set();wanted=[];shortfalls=[];classmap={r['raw_id']:r for r in classes}
    for anchor in plan['anchors']:
        assert classmap[anchor['raw_id']]['canonical_name']==anchor['name'];counts=dict(train=0,val=0,test=0)
        candidates=[r[0] for r in db.execute('SELECT DISTINCT image_id FROM boxes WHERE raw_id=? ORDER BY image_id',(anchor['raw_id'],))]
        candidates.sort(key=lambda i:hashlib.sha256((plan['selection_seed']+':'+i).encode()).hexdigest())
        for image_id in candidates:
            if image_id in oldids or any(x['id']==image_id for x in wanted):continue
            row=db.execute('SELECT * FROM images WHERE id=?',(image_id,)).fetchone()
            if row is None or row['rotation'] not in ('0','0.0') or row['license'] not in ('https://creativecommons.org/licenses/by/2.0/','http://creativecommons.org/licenses/by/2.0/'):continue
            attribution={k:row[k] for k in ('landing_url','original_url','license','author','author_url','title','rotation')}
            try:source.checked_url(attribution['landing_url'])
            except (ValueError,TypeError):continue
            author=group(attribution['author_url'] or attribution['landing_url'])
            if not author or author in oldgroups or author in used:continue
            prospective=split_for(author,plan['selection_seed'])
            if counts[prospective]>=anchor['quota'][prospective]:continue
            boxes=[dict(r) for r in db.execute('SELECT * FROM boxes WHERE image_id=? ORDER BY raw_id,x1,y1,x2,y2',(image_id,))]
            valid=[]
            for box in boxes:
                xy=[box[k] for k in ('x1','y1','x2','y2')]
                if box['group_of'] or box['depiction'] or box['raw_id'] not in classmap or not all(isinstance(v,(float,int)) and math.isfinite(v) for v in xy) or not 0<=xy[0]<xy[2]<=1 or not 0<=xy[1]<xy[3]<=1:continue
                valid.append(box)
            if not any(b['raw_id']==anchor['raw_id'] for b in valid):continue
            wanted.append(dict(id=image_id,selected_domain='billboard' if anchor['name']=='billboard' else 'contrast',selected_category=anchor['name'],canonical_id=classmap[anchor['raw_id']]['canonical_id'],author_alias=author,prospective_split=prospective,rights_verified=False,approved_for_training=False,attribution=attribution,publisher_boxes=valid));used.add(author);counts[prospective]+=1
            if counts==anchor['quota']:break
        shortfalls.append(dict(anchor=anchor['name'],requested=anchor['quota'],selected=counts))
    assert len(wanted)<=plan['maximum_photos'] and len({r['id'] for r in wanted})==len(wanted) and len(used)==len(wanted)
    return wanted,shortfalls
class NoImageRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise transport.PermanentError('Image redirect refused; no alternate endpoint')
def page_record(directory,item,remaining,fetcher=source.fetch):
    i=item['id'];url=item['attribution']['landing_url'];source.checked_url(url)
    result=dict(image_id=i,source_url=url,rights_verified=False,approved_for_training=False)
    try:
        body,meta=fetcher(url)
        if len(body)>min(2000000,remaining):raise ValueError('Source HTML byte cap')
        path=directory/'pages'/(i+'.html.gz');path.write_bytes(gzip.compress(body,mtime=0));result.update(meta,status='retrieved-unreviewed',page_file='pages/'+path.name,html_bytes=len(body),html_sha256=hashlib.sha256(body).hexdigest(),stored_sha256=sha(path))
    except (OSError,ValueError,TypeError) as error:result.update(status='held-source-unavailable',error=str(error)[:400])
    save(directory/'source-receipts'/(i+'.json'),result);return result
def run(root,job,check_only=False):
    if not re.fullmatch(r'[0-9]+',job):raise ValueError('Numeric actual job ID required')
    started=time.monotonic();plan=check_seal();database=root/plan['catalogue_relative_path']
    if database.is_symlink() or any(Path(str(database)+s).exists() for s in ('-wal','-journal')) or sha(database)!=plan['catalogue_sha256']:raise ValueError('Pinned catalogue differs or is writable/journalled')
    from PIL import Image
    out=root/'output'/('billboard-data-refresh-'+job)
    if out.exists():raise ValueError('Existing output preserved; no automatic rerun')
    if check_only:print(json.dumps(dict(status='sealed-CPU-data-input-preflight-passed',network_requests=0,GPUs=0,training=False)));return
    foundation=read(T/'classes-source.json');excluded=read(T/'exclusions.json');db=sqlite3.connect(database.as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
    try:wanted,shortfalls=select_rows(db,plan,excluded,foundation['classes'])
    finally:db.close()
    out.mkdir(exist_ok=False)
    for name in ('images','receipts','pages','source-receipts'):(out/name).mkdir()
    selection=dict(actual_job_id=job,plan_sha256=sha(T/'collection-plan.json'),images=wanted,shortfalls=shortfalls,split_frozen_before_download_and_predictions=True,source_alias_checks_only=True,resolved_NSID_checks_required_before_release=True)
    save(out/'selection.json',selection);context=dict(actual_job_id=job,plan_sha256=sha(T/'collection-plan.json'),selection_sha256=sha(out/'selection.json'));records={};pages={};failures=[];bytes_used=0;html_used=0;opener=urllib.request.build_opener(NoImageRedirect()).open
    try:
        for item in wanted:
            if time.monotonic()-started>plan['active_seconds_cap']:failures.append(dict(reason='bounded-time-cap-no-retry'));break
            i=item['id']
            try:
                record=transport.acquire_one(out,i,remaining_image_budget(out,plan),context,opener=opener);records[i]=record;bytes_used+=record['bytes']
                page=page_record(out,item,plan['maximum_HTML_bytes']-html_used);pages[i]=page;html_used+=page.get('html_bytes',0)
            except transport.IntegrityError:raise
            except (OSError,ValueError,transport.PermanentError,transport.RetryableError) as error:failures.append(dict(id=i,error=str(error)[:400],attempts=1,automatic_retry=False))
            print(f'Data intake {len(records)}/{len(wanted)}; source pages{sum(p["status"]=="retrieved-unreviewed" for p in pages.values())}',flush=True)
    finally:
        manifest=transport.make_manifest(dict(images=wanted,selection_job=job,context=context),records,{i['id']:dict(attribution=i['attribution'],boxes=i['publisher_boxes']) for i in wanted},foundation['classes'],foundation['source'],excluded['images'])
        manifest.update(id='billboard-data-refresh-'+job,split_policy='prospective author-alias split frozen before download; identity/NSID/duplicates/content/boxes/rights review still required; no automatic activation',maximum_photos=plan['maximum_photos'])
        for row in manifest['images']:
            row['prospective_split']=next(i['prospective_split'] for i in wanted if i['id']==row['id'])
            if pages.get(row['id'],{}).get('status')!='retrieved-unreviewed':row['intake_hold_reasons'].append('source-evidence-unavailable')
        save(out/'manifest.json',manifest)
        save(out/'collection-report.json',dict(status='completed-unreviewed-intake' if len(records)==len(wanted) and not failures else 'partial-intake-preserved',actual_job_id=job,plan_sha256=sha(T/'collection-plan.json'),selected=len(wanted),downloaded=len(records),original_bytes=bytes_used,HTML_bytes=html_used,failures=failures,shortfalls=shortfalls,manifest_sha256=sha(out/'manifest.json'),model_inference=False,training=False,rights_verified=False,approved_for_training=False,approved_for_application=False,elapsed_seconds=time.monotonic()-started))
    if not wanted or len(records)<len(wanted):raise SystemExit(2)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--job',required=True);ap.add_argument('--check-only',action='store_true');a=ap.parse_args();run(a.root.resolve(),a.job,a.check_only)
