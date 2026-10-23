import argparse,hashlib,json,re,tarfile
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--job',required=True);ap.add_argument('--exit',type=int,required=True);a=ap.parse_args()
if not re.fullmatch(r'[0-9]+',a.job):raise ValueError('Actual numeric job required')
out=a.root/'output'/('billboard-data-refresh-'+a.job);out.mkdir(exist_ok=True)
with (out/'transfer.json').open('x',encoding='utf-8') as f:json.dump(dict(actual_job_id=a.job,process_exit_code=a.exit,report_finalized=(out/'collection-report.json').exists(),model_inference=False,training=False,rights_verified=False,approved_for_training=False,approved_for_application=False),f,indent=2)
archive=a.root/'output'/('frametrail-data-refresh-results-'+a.job+'.tar.gz')
with tarfile.open(archive,'x:gz') as tar:
    tar.add(out,arcname='output/'+out.name)
    log=a.root/('frametrail-data-refresh-'+a.job+'.log')
    if log.exists():tar.add(log,arcname=log.name)
with archive.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
with Path(str(archive)+'.sha256').open('x') as f:f.write(digest+'  '+archive.name+'\n')
print(json.dumps(dict(actual_job_id=a.job,archive=str(archive),sha256=digest)))
