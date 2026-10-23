"""Safe extraction plus exact actual-job/schedule/patch validation. Never replace a failed task."""
import argparse,math
from pathlib import Path
import torch
from batch_guard import *
def verify_result(folder,base,job,index):
    job=valid_job(job);folder=Path(folder);base=Path(base);run_id=f'{job}_{index}'
    if index not in (0,1):raise ValueError('Task index')
    verify_files(folder,'result-files.json');s=validate_scope(read(base/'SCOPE.json'));scope_sha=sha(base/'SCOPE.json');seed=s['seeds'][index]
    exit_record=read(folder/'EXIT.json')
    if exit_record.get('actual_job_id')!=run_id or exit_record.get('scope_sha256')!=scope_sha:raise ValueError('Result job/scope differs')
    if (folder/'FAILED.json').exists() or exit_record['process_exit_code']!=0:
        return dict(status='failed-task-preserved-no-retry',actual_job_id=run_id,complete=False,production_adoption=False)
    report=read(folder/'REPORT.json')
    expected=dict(status='complete-awaiting-local-CPU-selection',actual_job_id=run_id,scope_sha256=scope_sha,seed=seed,index=index,
      starting_checkpoint_sha256=CHECKPOINT,schedule_sha256=s['schedule_sha256'][str(seed)],updates=1500,
      frozen_state_unchanged=True,inactive_rows_bitwise_unchanged=True,validation_selection_performed=False,test_photos_used=0,production_adoption=False,automatic_retries=0)
    if any(report.get(k)!=v for k,v in expected.items()):raise ValueError('Result report differs')
    elapsed=report['elapsed_active_seconds']
    if not isinstance(elapsed,(int,float)) or not math.isfinite(elapsed) or not 0<elapsed<1800:raise ValueError('Task budget')
    if [r['step'] for r in report['patches']]!=list(STEPS):raise ValueError('All fixed checkpoints required')
    for r in report['patches']:
        if r['path']!=f"patch-{r['step']:04}.pt":raise ValueError('Unexpected patch name')
        p=contained(folder,r['path'])
        if sha(p)!=r['sha256']:raise ValueError('Patch SHA differs')
        meta=check_patch(torch.load(p,map_location='cpu',weights_only=True),scope_sha,seed,r['step'],run_id)
        if meta.get('schedule_sha256')!=report['schedule_sha256'] or meta.get('frozen_digest')!=report['frozen_digest']:raise ValueError('Patch schedule/invariance identity')
    last=folder/'last.pt'
    if sha(last)!=report['last_sha256']:raise ValueError('Last patch SHA')
    last_value=torch.load(last,map_location='cpu',weights_only=True);check_patch(last_value,scope_sha,seed,1500,run_id)
    final=torch.load(folder/'patch-1500.pt',map_location='cpu',weights_only=True)
    if any(tensor_digest(last_value['rows'][k])!=tensor_digest(final['rows'][k]) for k in KEYS):raise ValueError('Last and step1500 differ')
    schedule=read(base/f'schedule-{seed}.json');lines=(folder/'TRAINING_STEPS.jsonl').read_text().splitlines()
    if len(lines)!=1500:raise ValueError('Missing update evidence')
    for step,line in enumerate(lines,1):
        r=__import__('json').loads(line)
        if r['step']!=step or r['train_ids']!=schedule[step-1]:raise ValueError('TRAIN schedule differs')
        if not all(math.isfinite(r[k]) for k in ('loss','dense_loss','gradient_norm')):raise ValueError('Nonfinite training evidence')
    for name in ('account-limits.txt','user-default.txt','qos-live.txt','partition-live.txt','admission-test.txt','submission-reply.txt'):
        if not (folder/name).is_file():raise ValueError('Missing live admission evidence')
    from admission import account
    account(folder,'ka_udxvl')
    reply=(folder/'submission-reply.txt').read_text().strip().split(';')[0]
    if reply!=job:raise ValueError('Submission reply job differs')
    return dict(status='complete-structurally-verified-awaiting-local-selection',actual_job_id=run_id,complete=True,production_adoption=False)
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--base',type=Path,required=True);a.add_argument('--downloads',type=Path,required=True);a.add_argument('--job',required=True);v=a.parse_args();valid_job(v.job)
    reports=[]
    for i in (0,1):
        archive=v.downloads/f'frametrail-fresh-selector-results-{v.job}_{i}.tar.gz'
        digest=Path(str(archive)+'.sha256').read_text().strip().split()[0]
        if not __import__('re').fullmatch('[0-9a-f]{64}',digest):raise ValueError('SHA sidecar')
        destination=v.downloads/f'verified-{v.job}_{i}'
        safe_extract(archive,destination,digest)
        reports.append(verify_result(destination,v.base,v.job,i))
    write(v.downloads/'VERIFICATION.json',dict(job=v.job,tasks=reports,all_complete=all(r['complete'] for r in reports),production_adoption=False))
    print(json.dumps(reports,indent=2))
