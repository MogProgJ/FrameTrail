"""Bounded failure-preserving result archive; no retry or submission."""
import argparse,os,tarfile,shutil
from pathlib import Path
from batch_guard import *
def bundle(project,exit_code):
    base=Path(__file__).parent;job=valid_job(os.environ['SLURM_ARRAY_JOB_ID']);index=int(os.environ['SLURM_ARRAY_TASK_ID'])
    if index not in (0,1):raise ValueError('Task index')
    run_id=f'{job}_{index}';out=project/'output'/('rf-fresh-selector-'+run_id);out.mkdir(exist_ok=True)
    write(out/'EXIT.json',dict(actual_job_id=run_id,process_exit_code=exit_code,scope_sha256=sha(base/'SCOPE.json'),production_adoption=False))
    for name in ('account-limits.txt','user-default.txt','qos-live.txt','partition-live.txt','queue-live.txt','admission-test.txt','submission-reply.txt'):
        if (base/'admission'/name).is_file():shutil.copyfile(base/'admission'/name,out/name)
    files={p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()}
    write(out/'result-files.json',files)
    archive=project/'output'/f'frametrail-fresh-selector-results-{run_id}.tar.gz'
    if archive.exists():raise ValueError('Preserve existing result archive')
    with tarfile.open(archive,'x:gz') as tf:
        for p in sorted(out.iterdir()):
            if not p.is_file() or p.is_symlink():raise ValueError('Unexpected result member')
            tf.add(p,arcname=p.name,recursive=False)
    digest=sha(archive)
    with Path(str(archive)+'.sha256').open('x',encoding='ascii') as f:f.write(digest+'  '+archive.name+'\n')
    # Stable exact paths allow both tasks and the job receipt to be retrieved in one SCP authentication.
    results=base/'results';results.mkdir(exist_ok=True)
    with archive.open('rb') as src,(results/f'task-{index}.tar.gz').open('xb') as dst:shutil.copyfileobj(src,dst)
    with (results/f'task-{index}.tar.gz.sha256').open('x',encoding='ascii') as f:f.write(digest+'  '+archive.name+'\n')
    print(json.dumps(dict(actual_job_id=run_id,archive=str(archive),sha256=digest)),flush=True)
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--project',type=Path,required=True);a.add_argument('--exit-code',type=int,required=True);v=a.parse_args();bundle(v.project,v.exit_code)
