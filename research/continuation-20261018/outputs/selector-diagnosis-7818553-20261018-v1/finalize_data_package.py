"""Seal/testable CPU intake transport; upload and existing cluster session separate."""
import hashlib,json,tarfile
from pathlib import Path
D=Path(__file__).resolve().parent;P=D.parent/'billboard-data-refresh-7818553-20261018-v1';T=P/'data-tools-v1'
OLD=D.parent/'selector-batch-proposal-7809335-20261018-v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(v if isinstance(v,str) else json.dumps(v,indent=2)+'\n',encoding='utf-8',newline='\n')
def main():
    plan=json.loads((T/'collection-plan.json').read_text());h=sha(T/'collection-plan.json');remote='data-refresh-'+h[:8]+'-v1'
    write(T/'bundle.py','''import argparse,hashlib,json,re,tarfile
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
with Path(str(archive)+'.sha256').open('x') as f:f.write(digest+'  '+archive.name+'\\n')
print(json.dumps(dict(actual_job_id=a.job,archive=str(archive),sha256=digest)))
''')
    write(T/'run.sbatch',f'''#!/bin/bash -l
#SBATCH --job-name=frametrail-data-refresh
#SBATCH --partition=cpu_il
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:45:00
#SBATCH --no-requeue
#SBATCH --output=frametrail-data-refresh-%j.log
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
task_tools="$PWD/output/training-general-v1/{remote}"
module load devel/miniforge/25.3.1-python-3.12
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
finish() {{
  task_exit=$?
  trap - EXIT
  if ! "$PWD/.venv/bin/python" -B "$task_tools/bundle.py" --root "$PWD" --job "$SLURM_JOB_ID" --exit "$task_exit"; then
    if [[ "$task_exit" -eq 0 ]]; then task_exit=3; fi
  fi
  exit "$task_exit"
}}
trap finish EXIT
timeout --signal=TERM --kill-after=20s 2460s srun "$PWD/.venv/bin/python" -u -B "$task_tools/collector.py" --root "$PWD" --job "$SLURM_JOB_ID"
''')
    write(T/'show-output.sh','''#!/bin/bash
set -euo pipefail
task_tools=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd "$(ws_find frametrail)/FrameTrail"
[[ -f "$task_tools/submitted-job-id.txt" ]] || { echo 'No recorded data job; inspect retained submission lock before any action.'; exit 0; }
task_job=$(cat "$task_tools/submitted-job-id.txt")
[[ "$task_job" =~ ^[0-9]+$ ]] || exit 1
echo "FRAMETRAIL_JOB_ID=$task_job"
sacct -j "$task_job" --format=JobID,JobName%32,State,ExitCode,Start,Elapsed
task_report="output/billboard-data-refresh-$task_job/collection-report.json"
if [[ -f "$task_report" ]]; then cat "$task_report"; printf '\\n'; else echo 'Collection report not ready.'; fi
task_sidecar="output/frametrail-data-refresh-results-$task_job.tar.gz.sha256"
if [[ -f "$task_sidecar" ]]; then task_hash=$(awk '{print $1}' "$task_sidecar"); [[ "$task_hash" =~ ^[0-9a-f]{64}$ ]] || exit 1; echo "FRAMETRAIL_ARCHIVE_SHA256=$task_hash"; else echo 'Archive not ready.'; fi
''')
    write(T/'submit.sh','''#!/bin/bash
set -euo pipefail
task_tools=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd "$(ws_find frametrail)/FrameTrail"
if [[ -f "$task_tools/submitted-job-id.txt" ]]; then bash "$task_tools/show-output.sh"; exit 0; fi
module load devel/miniforge/25.3.1-python-3.12
export PYTHONDONTWRITEBYTECODE=1
"$PWD/.venv/bin/python" -B "$task_tools/collector.py" --root "$PWD" --job 0 --check-only
for task_script in submit.sh show-output.sh run.sbatch; do bash -n "$task_tools/$task_script"; done
scontrol show config > "$task_tools/scheduler-config.txt" 2>&1 || true
sacctmgr -nP show assoc where user="$(id -un)" format=User,Account,Partition,QOS,MaxJobs,MaxSubmitJobs,GrpTRES > "$task_tools/account-limits.txt" 2>&1 || true
sbatch --test-only "$task_tools/run.sbatch" > "$task_tools/scheduler-test-only.txt" 2>&1 || { cat "$task_tools/scheduler-test-only.txt"; exit 1; }
mkdir "$task_tools/submission-lock" || { echo 'Lock retained: inspect Slurm history, never resubmit automatically.'; exit 1; }
task_reply=$(sbatch --parsable "$task_tools/run.sbatch")
task_job=${task_reply%%;*}
[[ "$task_job" =~ ^[0-9]+$ ]] || { echo 'Ambiguous sbatch response; lock retained.'; exit 1; }
(set -o noclobber; printf '%s\\n' "$task_job" > "$task_tools/submitted-job-id.txt")
echo 'Submitted one bounded CPU data collection job; zero GPUs and no training.'
bash "$task_tools/show-output.sh"
''')
    write(T/'AUTHORIZATION.json',json.loads((P/'USER_AUTHORIZATION.json').read_text()))
    seal=dict(files={p.relative_to(T).as_posix():sha(p) for p in sorted(T.rglob('*')) if p.is_file() and p.name!='package-files.json'})
    write(T/'package-files.json',seal)
    archive=P/('frametrail-'+remote+'.tar.gz')
    with tarfile.open(archive,'x:gz') as tar:
        for p in sorted(T.iterdir()):
            if p.is_file():tar.add(p,arcname=remote+'/'+p.name,recursive=False)
    archivehash=sha(archive);write(P/(archive.name+'.sha256'),archivehash+'  '+archive.name+'\n')
    expected=dict(seal['files'],**{'package-files.json':sha(T/'package-files.json')});seen=set()
    with tarfile.open(archive,'r:gz') as tar:
        for m in tar:
            assert m.isfile() and m.name.startswith(remote+'/');name=m.name[len(remote)+1:];assert name in expected and name not in seen
            with tar.extractfile(m) as f:assert hashlib.file_digest(f,'sha256').hexdigest()==expected[name]
            seen.add(name)
    assert seen==set(expected)
    write(P/'archive-receipt.json',dict(archive=archive.name,archive_sha256=archivehash,bytes=archive.stat().st_size,remote_directory=remote,plan_sha256=h,package_seal_sha256=sha(T/'package-files.json'),archived_files_verified=len(seen),cluster_submitted=False))
    write(P/'Upload-Data-Package.ps1',r'''$ErrorActionPreference='Stop'
$taskReceipt=Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'archive-receipt.json') | ConvertFrom-Json
$taskPath=Join-Path $PSScriptRoot $taskReceipt.archive
if ((Get-FileHash -LiteralPath $taskPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskReceipt.archive_sha256) { throw 'Package checksum differs; no upload.' }
Write-Host 'Upload only. Enter KIT OTP/password directly. Submit using your existing cluster session afterward.'
& scp -o StrictHostKeyChecking=yes $taskPath 'ka_udxvl@uc3.scc.kit.edu:/pfs/work9/workspace/scratch/ka_udxvl-frametrail/FrameTrail/output/'
if ($LASTEXITCODE -ne 0) { throw 'Upload stopped; preserve output. No job was submitted by this helper.' }
Write-Host 'Upload finished. Run the command in START_ON_CLUSTER.sh from the already authenticated cluster terminal.'
''')
    bootstrap=f'''#!/bin/bash
set -euo pipefail
cd "$(ws_find frametrail)/FrameTrail"
task_archive="$PWD/output/{archive.name}"
task_hash=$(sha256sum "$task_archive" | awk '{{print $1}}')
[[ "$task_hash" == "{archivehash}" ]] || {{ echo 'Upload checksum differs; stop.'; exit 1; }}
task_tools="$PWD/output/training-general-v1/{remote}"
if [[ -e "$task_tools" ]]; then
  [[ -d "$task_tools" && ! -L "$task_tools" && -f "$task_tools/package-files.json" ]] || exit 1
else
  mkdir -p "$task_tools"
  tar --extract --gzip --file="$task_archive" --strip-components=1 --no-same-owner --directory="$task_tools"
fi
task_seal=$(sha256sum "$task_tools/package-files.json" | awk '{{print $1}}')
[[ "$task_seal" == "{sha(T/'package-files.json')}" ]] || {{ echo 'Package identity differs; stop.'; exit 1; }}
bash "$task_tools/submit.sh"
'''
    write(P/'START_ON_CLUSTER.sh',bootstrap)
    # Short copy/paste form avoids another authenticated SSH connection for submission.
    import base64
    payload=base64.b64encode(bootstrap.encode()).decode('ascii')
    write(P/'CLUSTER_COMMAND.txt','printf %s '+payload+' | base64 -d | bash\n')
    # Reuse safe extraction implementation; collection-specific receipts are checked below.
    old=(OLD/'verify_results.py').read_text();start=old.index('def members_checked');end=old.index('def verify_schedule')
    safety=old[start:end].replace("'rf-selector-'+job","'billboard-data-refresh-'+job").replace("'frametrail-rf-selector-'+job","'frametrail-data-refresh-'+job")
    write(P/'verify_results.py','''import argparse,hashlib,json,re,shutil,tarfile
from pathlib import Path,PurePosixPath
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
'''+safety+'''
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
        if p.is_absolute() or '..' in p.parts or sha(out/row['path'])!=row['sha256'] or row['approved_for_training'] or row['rights_verified']:raise ValueError('Photo provenance/hold differs')
    result.update(status='data-intake-verified-awaiting-source-identity-content-and-label-review',photos=len(manifest['images']),source_rights_verified=False)
with (a.archive.parent/'verification-receipt.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(result,indent=2))
''')
    write(P/'Retrieve-Data.ps1',r'''$ErrorActionPreference='Stop'
$taskReceipt=Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'run-receipt.json') | ConvertFrom-Json
if ($taskReceipt.actual_job_id -notmatch '^\d+$' -or $taskReceipt.archive_sha256 -notmatch '^[0-9a-f]{64}$') { throw 'Import the cluster completion output first; exact job/hash required.' }
$taskJob=[string]$taskReceipt.actual_job_id
$taskDestination=Join-Path $PSScriptRoot ('retrieval-'+$taskJob)
if (Test-Path -LiteralPath $taskDestination) { throw 'Existing retrieval preserved; inspect without retry/overwrite.' }
New-Item -ItemType Directory -Path $taskDestination | Out-Null
$taskName='frametrail-data-refresh-results-'+$taskJob+'.tar.gz'
& scp -o StrictHostKeyChecking=yes ('ka_udxvl@uc3.scc.kit.edu:/pfs/work9/workspace/scratch/ka_udxvl-frametrail/FrameTrail/output/'+$taskName+'*') $taskDestination
if ($LASTEXITCODE -ne 0) { throw 'Transfer stopped; preserve bytes.' }
$taskNames=@(Get-ChildItem -LiteralPath $taskDestination -File | ForEach-Object { $_.Name })
if (@(Compare-Object @($taskName,($taskName+'.sha256')) $taskNames).Count -ne 0) { throw 'Unexpected transfer files.' }
$taskLine=(Get-Content -Raw -LiteralPath (Join-Path $taskDestination ($taskName+'.sha256'))).Trim()
if ($taskLine -notmatch ('^'+$taskReceipt.archive_sha256+'\s+\*?'+[regex]::Escape($taskName)+'$')) { throw 'Server sidecar differs from the recorded cluster hash.' }
& 'C:/Users/nazee/Documents/All Modules/FrameTrail/.deps/rfdetr-probe-cpu/Scripts/python.exe' -B -X utf8 (Join-Path $PSScriptRoot 'verify_results.py') --archive (Join-Path $taskDestination $taskName) --job $taskJob --expected-sha $taskReceipt.archive_sha256
if ($LASTEXITCODE -ne 0) { throw 'Data verification failed; preserve all files.' }
''')
    write(P/'PACKAGE_IDENTITY.json',dict(remote_directory=remote,plan_sha256=h,archive_sha256=archivehash,standing_authorization_recorded=True,cluster_submitted=False))
    print(json.dumps(dict(package=str(P),archive=archive.name,bytes=archive.stat().st_size,sha256=archivehash,remote_directory=remote)))
if __name__=='__main__':main()
