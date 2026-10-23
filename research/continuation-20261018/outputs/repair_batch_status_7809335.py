"""Recover completed-task receipts from existing logs; no network or submission."""
import hashlib,json,re,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BATCH=ROOT/'billboard-batch-proposal-7805570-20261018-v1'
FIX=ROOT/'batch-status-repair-7809335-20261018-v1'
ATTACH=Path(r'C:\Users\nazee\.codex\attachments\26dff4bc-db20-42b3-a998-45138385ab49\Pasted text.txt')
def text(p):
    raw=p.read_bytes();return raw.decode('utf-16' if raw[:2] in (b'\xff\xfe',b'\xfe\xff') else 'utf-8-sig')
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def put(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as f:f.write(v if isinstance(v,str) else json.dumps(v,indent=2)+'\n')
def markers(log):
    pattern=r'(?m)(?:^|(?<=\}))FRAMETRAIL_TASK_ARCHIVE=([0-3]):([0-9a-f]{64})\s*$'
    found=re.findall(pattern,log)
    if len(found)!=4 or {i for i,h in found}!={'0','1','2','3'}:raise ValueError('Need exactly four uniquely identified archive hashes')
    return {int(i):h for i,h in found}
FIX.mkdir(exist_ok=False)
for name in ('Check-Run.ps1','Retrieve-Results.ps1','run-receipt.json','latest-output.txt'):shutil.copyfile(BATCH/name,FIX/('original-'+name))
shutil.copyfile(ATTACH,FIX/'user-console.txt')
saved=text(BATCH/'latest-output.txt');user=text(ATTACH)
hashes=markers(saved);assert hashes==markers(user)
assert re.search(r'(?m)^FRAMETRAIL_JOB_ID=7809335\s*$',saved)
decoder=json.JSONDecoder();reports=[]
for m in re.finditer(r'\{\s*"status"\s*:',saved):
    report,_=decoder.raw_decode(saved,m.start())
    if report.get('actual_job_id','').startswith('7809335_'):reports.append(report)
assert len(reports)==4 and {r['array_task_index'] for r in reports}=={0,1,2,3}
for r in reports:
    i=r['array_task_index'];assert r['actual_job_id']==f'7809335_{i}' and r['best_step']==0 and r['updates']==1500 and not r['new_candidate_selected']
    assert r['completion_reason']=='protocol-early-stop-no-gain'
    assert re.search(r'(?m)^7809335_'+str(i)+r'\s+\S+\s+COMPLETED\s+0:0\s+',saved)
check=text(BATCH/'Check-Run.ps1');old=r'(?m)^FRAMETRAIL_TASK_ARCHIVE=([0-3]):([0-9a-f]{64})\s*$';new=r'(?m)(?:^|(?<=\}))FRAMETRAIL_TASK_ARCHIVE=([0-3]):([0-9a-f]{64})\s*$'
assert old in check
(BATCH/'Check-Run.ps1').write_text(check.replace(old,new),encoding='utf-8',newline='\n')
retrieve=text(BATCH/'Retrieve-Results.ps1')
start=retrieve.index('$taskSources = @()');end=retrieve.index("if ($LASTEXITCODE -ne 0)",start)
retrieve=retrieve[:start]+'''# One fixed SFTP glob source lets OpenSSH retrieve the eight batch files in one connection.
$taskSource = $taskRemote + 'frametrail-rf-billboard-batch-results-' + $taskJob + '_[0-3].tar.gz*'
& scp -o StrictHostKeyChecking=yes $taskSource $taskDestination
'''+retrieve[end:]
retrieve=retrieve.replace("foreach ($taskRecord in $taskReceipt.archives) {",'''$taskExpectedNames = @($taskReceipt.archives | ForEach-Object {
    $taskBaseName = 'frametrail-rf-billboard-batch-results-' + $taskJob + '_' + $_.index + '.tar.gz'
    $taskBaseName
    $taskBaseName + '.sha256'
})
$taskDownloadedNames = @(Get-ChildItem -LiteralPath $taskDestination -File | ForEach-Object { $_.Name })
if (@(Compare-Object $taskExpectedNames $taskDownloadedNames).Count -ne 0) { throw 'Need exactly the four expected archives and four sidecars; preserve downloaded bytes.' }
foreach ($taskRecord in $taskReceipt.archives) {
    if ($taskRecord.index -notin 0,1,2,3 -or $taskRecord.sha256 -notmatch '^[0-9a-f]{64}$') { throw 'Invalid archive receipt' }''',1)
(BATCH/'Retrieve-Results.ps1').write_text(retrieve,encoding='utf-8',newline='\n')
receipt=dict(status='four-task-archives-ready-recovered-from-saved-successful-status',actual_job_id='7809335',protocol_sha256='0a255598b74eb1d29d83ee1be10d517ae407fbda2c57e4565b51028d615343fd',archives=[dict(index=i,sha256=hashes[i]) for i in range(4)],approved_for_application=False)
(BATCH/'run-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8',newline='\n')
put(FIX/'RECOVERY_RECEIPT.json',dict(status='local-status-parser-fixed-four-hashes-recovered-without-network',actual_job_id='7809335',cause='Remote cat prints JSON without a final newline, joining }FRAMETRAIL_TASK_ARCHIVE; original start-of-line parser missed all four hashes.',original_regex_found=0,recovered_archives=receipt['archives'],saved_log_and_user_console_agree=True,retrieval='one fixed SFTP remote glob for all four archives and sidecars; exact downloaded filename and hash verification retained',core_package_modified=False,SSH_contacted=False,new_jobs=0,raw_source_sha256=sha(FIX/'original-latest-output.txt')))
put(FIX/'COMPLETION_STATE.json',dict(status='all-four-tasks-completed-no-eligible-improving-candidate-awaiting-retrieval-audit',actual_job_id='7809335',reports=reports,reported_updates_total=sum(r['updates'] for r in reports),eligible_candidates_selected=0,retained_starting_model=dict(job='7805570',step=100,weights_verified_from_new_results=False),independent_local_audit_pending=True,archive_hashes_recorded=True,production_adoption=False))
put(FIX/'REPORT.md','''# Array7809335 completed; local status parsing repaired

All four tasks reported COMPLETED with exit0:0. Each stopped after1500updates without selecting an eligible strict gain; best_step0 retains the starting model. This does not establish why each trained state was rejected. Returned validation predictions and tensor checks must be independently audited before interpreting the experiment.

All four archive checksums were present in the saved KIT output, directly after JSON closing braces. The line-anchored local parser missed them. It now accepts either a line start or a preceding closing brace. Four unique indices/hashes agree exactly between the saved status log and user console. Original helpers/working receipt/raw output are preserved here. No SSH query, uploaded-core edit or replacement submission was needed.

The local retrieval helper now passes one fixed batch-specific SFTP wildcard source for the four archives and sidecars, then requires exactly the eight expected filenames and all recorded hashes. Installed Windows OpenSSH9.5 uses SFTP by default; source: https://man.openbsd.org/scp . Remote data, training scope and original archived package are unchanged.

Run the existing Retrieve-Results.ps1 with direct KIT authentication. Independent local validation/selection/tensor/regression auditing is already prepared in the sibling billboard-batch-audit-7809335-20261018-v1 folder and is authorized without a new approval. No application model should be changed on the basis of this status output.

Next step: retrieve all four archives in one command, because completed-process receipts alone are not independently audited model results.
''')
print(json.dumps(dict(status='four-hashes-recovered-local-helpers-repaired',actual_job_id='7809335',archives_ready=4,updates_total=6000,eligible_candidates_selected=0,network_contacted=False),indent=2))
