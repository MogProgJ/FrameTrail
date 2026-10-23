"""Preserve actual job outputs, including explicit partial-failure receipts."""
import argparse,json,hashlib,tarfile,re
from pathlib import Path
def bundle(project,job,exit_code,training_exit,post_exit):
    if not re.fullmatch(r'[0-9]+_[0-3]',job):raise ValueError('Actual numeric job ID required')
    out=project/'output'/('rf-billboard-batch-'+job);out.mkdir(exist_ok=True)
    with (out/'transfer.json').open('x',encoding='utf-8') as f:json.dump(dict(actual_job_id=job,process_exit_code=exit_code,training_exit_code=training_exit,postprocessing_exit_code=post_exit,finalized=(out/'experiment-report.json').exists(),approved_for_application=False),f,indent=2)
    archive=project/'output'/('frametrail-rf-billboard-batch-results-'+job+'.tar.gz')
    with tarfile.open(archive,'x:gz') as tar:
        tar.add(out,arcname='output/'+out.name,filter=lambda info: None if '/checkpoints' in info.name else info)
        log=project/('frametrail-rf-billboard-batch-'+job+'.log')
        if log.exists():tar.add(log,arcname=log.name)
    with archive.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
    with Path(str(archive)+'.sha256').open('x',encoding='utf-8') as f:f.write(digest+'  '+archive.name+'\n')
    return dict(archive=str(archive),sha256=digest,actual_job_id=job)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--project',type=Path,required=True);ap.add_argument('--job',required=True);ap.add_argument('--exit-code',type=int,required=True);ap.add_argument('--training-exit',type=int,required=True);ap.add_argument('--post-exit',type=int,required=True);a=ap.parse_args();print(json.dumps(bundle(a.project,a.job,a.exit_code,a.training_exit,a.post_exit)))
