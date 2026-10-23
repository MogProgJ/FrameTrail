"""Bounded extraction and exact approved-run receipts; no model loading/adoption."""
import argparse,hashlib,json,re,shutil,tarfile
from pathlib import Path,PurePosixPath
PROTOCOL_SHA='716ca2cf411984698e6d096f00fd5ef01995bee9ed4fe0c82a742e26c4bc6e1c'
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def members_checked(tar,job):
    seen=set();total=0;items=tar.getmembers()
    if len(items)>4096:raise ValueError('Too many archive members')
    for m in items:
        p=PurePosixPath(m.name)
        if p.is_absolute() or '..' in p.parts or '\\' in m.name or ':' in m.name or m.name in seen or not (m.isdir() or m.isfile()):raise ValueError('Unsafe member '+m.name)
        allowed=(len(p.parts)>=2 and p.parts[:2]==('output','rf-billboard-'+job)) or (p.parts==('output',) and m.isdir()) or (m.name=='frametrail-rf-billboard-'+job+'.log' and m.isfile())
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
SCHEDULE_SHA='ecd0143d22d4f2844a663702f42ac497a1ce2ab224beb9144a7bf4f675764908'

def verify_schedule(schedule,approved_path=None):
    approved_path=approved_path or Path(__file__).with_name('approved-sampling-plan.json')
    if sha(approved_path)!=SCHEDULE_SHA:raise ValueError('Approved sampler reference seal differs')
    if schedule!=read(approved_path):raise ValueError('Returned sampler differs from the approved fixed schedule')

def verify(archive,job,expected,destination=None):
    if not job.isdigit() or not re.fullmatch('[0-9a-f]{64}',expected):raise ValueError('Actual job ID and pinned SHA256 required')
    if sha(archive)!=expected:raise ValueError('Archive checksum mismatch')
    destination=destination or archive.parent/('verified-'+job);extract(archive,destination,job);out=destination/'output'/('rf-billboard-'+job)
    transfer=read(out/'transfer.json')
    if transfer['actual_job_id']!=job or transfer['approved_for_application'] is not False:raise ValueError('Transfer identity/adoption flag differs')
    result=dict(status='partial-or-failed-run-awaiting-inspection',actual_job_id=job,archive_sha256=expected,process_exit_code=transfer['process_exit_code'],output=str(out),approved_for_application=False)
    if transfer['process_exit_code']==0:
        report=read(out/'experiment-report.json');pre=read(out/'preflight.json')
        if pre['actual_job_id']!=job or pre['protocol_sha256']!=PROTOCOL_SHA or pre['active_classifier_rows']!=[133] or pre['test_photos_used']!=0 or pre['fresh_video_frames_used']!=0:raise ValueError('Wrong preflight scope')
        if report['actual_job_id']!=job or report['approved_for_application'] is not False or report['test_and_video_used'] is not False or report['active_classifier_rows']!=[133] or report['frozen_features_and_boxes_unchanged'] is not True or report['inactive_classifier_rows_unchanged'] is not True or report['retention_against_both_baselines'] is not True:raise ValueError('Run scope/freeze receipt differs')
        count=report['updates'];best=report['best_step']
        if not isinstance(best,int) or not 0<=best<=count or best%100:raise ValueError('Selected step is not an evaluated checkpoint')
        if pre['starting_checkpoint_sha256']!='c1e7b571476a9bdc02533359dfe3f599afab98822aa90df265e9068f43f46bd3' or report['new_candidate_selected']!=(best>0):raise ValueError('Continuation start or selection identity differs')
        if not ((count==1500 and best==0 and report['completion_reason']=='protocol-early-stop-no-gain') or (count==3000 and best>0 and report['completion_reason']=='maximum-updates')):raise ValueError('Run did not match approved completion rule')
        if sha(out/'best.pt')!=report['best_checkpoint_sha256'] or sha(out/'last.pt')!=report['last_checkpoint_sha256']:raise ValueError('Checkpoint checksum differs')
        schedule=read(out/'sampling-plan.json')
        verify_schedule(schedule)
        if len(schedule)!=3000 or len(list(out.glob('step-*.json')))!=count:raise ValueError('Schedule/update count differs')
        for step in range(1,count+1):
            record=read(out/f'step-{step:04}.json')
            if record['step']!=step or record['train_ids']!=schedule[step-1]:raise ValueError('Update escaped frozen schedule')
        expected_vals=set(range(0,count+1,100));actual_vals={read(p)['step'] for p in out.glob('validation-*.json')}
        if actual_vals!=expected_vals or not transfer['finalized'] or report['elapsed_seconds']>=1800:raise ValueError('Incomplete validation or elapsed cap exceeded')
        result.update(status='trial-verified-awaiting-known-regression-evaluation-independent-evidence-needed' if best>0 else 'trial-verified-no-improving-candidate',updates=count,best_step=best,new_candidate_selected=best>0)
    with (destination.parent/'verification-receipt.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    return result
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--archive',type=Path,required=True);ap.add_argument('--job',required=True);ap.add_argument('--expected-sha',required=True);ap.add_argument('--destination',type=Path);a=ap.parse_args();print(json.dumps(verify(a.archive,a.job,a.expected_sha,a.destination),indent=2))
