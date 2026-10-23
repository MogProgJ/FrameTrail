import argparse,hashlib,json,re,shutil,tarfile
from pathlib import Path,PurePosixPath
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def members_checked(tar,job):
    seen=set();total=0;items=tar.getmembers()
    if len(items)>4096:raise ValueError('Too many archive members')
    for m in items:
        p=PurePosixPath(m.name)
        if p.is_absolute() or '..' in p.parts or '\\' in m.name or ':' in m.name or m.name in seen or not (m.isdir() or m.isfile()):raise ValueError('Unsafe member '+m.name)
        allowed=(len(p.parts)>=2 and p.parts[:2]==('output','billboard-data-refresh-'+job)) or (p.parts==('output',) and m.isdir()) or (m.name=='frametrail-data-refresh-'+job+'.log' and m.isfile())
        if not allowed or m.size>1024**3:raise ValueError('Unexpected member '+m.name)
        seen.add(m.name);total+=m.size
    if total>4*1024**3:raise ValueError('Archive exceeds bounded result size')
    return items
def extract(archive,dest,job):
    with tarfile.open(archive,'r:gz') as tar:
        items=members_checked(tar,job);dest.mkdir(exist_ok=False)
        for m in items:
            out=dest.joinpath(*PurePosixPath(m.name).parts)
            if m.isdir():out.mkdir(parents=True,exist_ok=True)
            else:
                out.parent.mkdir(parents=True,exist_ok=True)
                with tar.extractfile(m) as src,out.open('xb') as dst:shutil.copyfileobj(src,dst)

ap=argparse.ArgumentParser();ap.add_argument('--archive',type=Path,required=True);ap.add_argument('--job',required=True);ap.add_argument('--expected-sha',required=True);a=ap.parse_args()
if not re.fullmatch(r'[0-9]+',a.job) or sha(a.archive)!=a.expected_sha:raise ValueError('Archive identity/checksum differs')
destination=a.archive.parent/('verified-'+a.job);extract(a.archive,destination,a.job);out=destination/'output'/('billboard-data-refresh-'+a.job);transfer=read(out/'transfer.json')
if transfer['actual_job_id']!=a.job or transfer['training'] is not False or transfer['approved_for_training'] is not False:raise ValueError('Transfer scope differs')
result=dict(status='failed-or-partial-data-job-preserved',actual_job_id=a.job,approved_for_training=False,production_adoption=False)
if transfer['report_finalized']:
    report=read(out/'collection-report.json');selection=read(out/'selection.json');manifest=read(out/'manifest.json');plan=read(Path(__file__).parent/'SCOPE.json')
    if report['plan_sha256']!=selection['plan_sha256'] or report['actual_job_id']!=a.job or report['model_inference'] or report['training'] or manifest['approved_for_training']:raise ValueError('Collection scope differs')
    if report['plan_sha256']!=sha(Path(__file__).parent/'SCOPE.json'):raise ValueError('Collection plan differs')
    if report['manifest_sha256']!=sha(out/'manifest.json') or len(manifest['images'])>plan['maximum_photos'] or report['original_bytes']>plan['maximum_original_bytes'] or report['HTML_bytes']>plan['maximum_HTML_bytes']:raise ValueError('Collection bounds/hash differ')
    for row in manifest['images']:
        p=PurePosixPath(row['path'])
        if p.is_absolute() or '..' in p.parts or '\\' in row['path'] or ':' in row['path'] or not re.fullmatch(r'images/[0-9a-f]{16}\.jpg',row['path']) or sha(out/row['path'])!=row['sha256'] or row['approved_for_training'] or row['rights_verified']:raise ValueError('Photo provenance/hold differs')
    result.update(status='data-intake-verified-awaiting-source-identity-content-and-label-review',photos=len(manifest['images']),source_rights_verified=False)
with (a.archive.parent/'verification-receipt.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(result,indent=2))
