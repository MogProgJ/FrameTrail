"""Prepare an unapproved four-trial array locally. Never opens SSH or submits jobs."""
import ast,copy,hashlib,json,random,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OLD=ROOT/'billboard-only-proposal-7805570-20261018-v1'
BASE=OLD/'rf-billboard-716ca2cf-v1'
OUT=ROOT/'billboard-batch-proposal-7805570-20261018-v1'
EVAL=ROOT/'heldout-evaluation-7805570-20261018-v1'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def put(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(v if isinstance(v,str) else json.dumps(v,indent=2)+'\n',encoding='utf-8',newline='\n')
OUT.mkdir(exist_ok=False)
p=read(BASE/'protocol.json')
p.update(status='four-trial-batch-prepared-awaiting-exact-cluster-approval',experiment_approved=False)
p['training'].update(model_mode='eval; only final classifier row 133 trainable',lr='per fixed variant',accumulation='2 or 4 per fixed variant',maximum_presentations=36000,per_update='One billboard positive, plus one or three distinct explicitly absent photos; paired schedules across learning rates.',Slurm_wall_minutes_cap=45)
p['batch']=dict(trials=4,array='0-3%2',maximum_concurrent_GPUs=2,GPUs_per_task=1,cpus_per_task=2,host_memory_per_task_GiB=8,maximum_total_updates=12000,maximum_total_presentations=36000,maximum_training_GPU_hours=2,maximum_requested_GPU_hours=3,postprocessing_seconds_per_task=480,automatic_retries=0,task_failure_policy='Other array tasks continue; failed tasks are preserved, never replaced automatically.',partition='gpu_a100_il')
p['variants']=[dict(index=i,name=f'n{n}-lr{lr:g}',negative_presentations=n,lr=lr,accumulation=n+1,maximum_updates=3000) for i,(n,lr) in enumerate(((1,.0001),(3,.0001),(1,.0003),(3,.0003)))]
p['selection']['across_variants']='Select solely by the predeclared validation ranking after every task is terminal and audited. Eligible strict gain required. Exact ties retain lower array index. Known regression cannot reselect a checkpoint or variant. If all tasks fail/no gain, retain current model.'
p['evaluation'].update(automatic_known_regression=True,unique_images_per_selected_candidate=202,reference_sets=6,postprocessing='Freeze each validation-selected checkpoint hash before scoring all known references; no optimizer, no test-based reselection. A step-zero result reuses pinned current-model scores without inference.')
p['automatic_export']=False
p['local_autonomy']='No extra user approval is needed for later local audit, export, CPU parity, reversible integration or packaging. Automatic_export=false means this cluster batch has no ONNX export stage; it is not a permission boundary.'
p['execution_package_status']='Prepared array draft; approval absent; no SSH or submission.'
p['rationale']='A small 2x2 development comparison isolates negative-share and learning-rate effects at paired sampling seeds. Maximum useful planned independent work, not the maximum account queue size. Increased validation comparisons do not create fresh test evidence.'
p['scope']='four-billboard-trials-array0-3-percent2-max3000-45min-each-known-regression'
pool=read(BASE/'sampling-pools.json')
rng=random.Random(171022);positive=[]
while len(positive)<3000:
    cycle=list(pool['billboard']);rng.shuffle(cycle);positive.extend(cycle)
rng=random.Random(171023);negatives=[rng.sample(pool['explicit_negative'],3) for _ in range(3000)]
schedules=[]
for v in p['variants']:
    s=[[positive[i],*negatives[i][:v['negative_presentations']]] for i in range(3000)]
    raw=(json.dumps(s,indent=2)+'\n').encode();v['schedule_file']=f"schedules/task-{v['index']}.json";v['schedule_sha256']=hashlib.sha256(raw).hexdigest();schedules.append(s)
p['data'].pop('schedule_sha256',None)
raw=(json.dumps(p,indent=2)+'\n').encode();digest=hashlib.sha256(raw).hexdigest();name='rf-billboard-batch-'+digest[:8]+'-v1';T=OUT/name
T.mkdir()
for rel,h in read(BASE/'package-files.json')['files'].items():
    if rel in ('activation-fragment.txt','test_contract.py','sampling-plan.json'):continue
    src=BASE/rel;assert sha(src)==h,rel
    dst=T/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
put(T/'protocol.json',p);put(OUT/'protocol.json',p)
for v,s in zip(p['variants'],schedules):put(T/v['schedule_file'],s)
put(OUT/'PROPOSAL_IDENTITY.json',dict(protocol_sha256=digest,package_directory=name,cluster_job_approved=False,cluster_job_submitted=False))
put(OUT/'approval-template.json',dict(approved=False,protocol_sha256=digest,scope=p['scope'],active_classifier_rows=[133],user_authorization_evidence=None))

# Adapt the proven single-row trainer and guard to a strictly selected array task.
guard=(BASE/'continuation_guard.py').read_text()
guard=guard.replace("PROTOCOL_SHA='716ca2cf411984698e6d096f00fd5ef01995bee9ed4fe0c82a742e26c4bc6e1c'",f"PROTOCOL_SHA='{digest}'").replace("SCOPE='one-billboard-row-negative-calibration-max3000-oneGPU-45minutes'",f"SCOPE='{p['scope']}'")
guard=guard.replace(" or p['training']['lr']!=.0001", " or p['batch']['array']!='0-3%2'")
guard=guard.replace('def inputs(t,require_approval=True):','''def variant(t,index=None):
    import os
    if index is None:
        raw=os.environ.get('SLURM_ARRAY_TASK_ID')
        if raw not in ('0','1','2','3'):raise ValueError('Exact array task index required')
        index=int(raw)
    if type(index) is not int or not 0<=index<4:raise ValueError('Unknown array task index')
    return read(t/'protocol.json')['variants'][index]

def inputs(t,require_approval=True,task_index=None):''')
guard=guard.replace("pools=read(t/'sampling-pools.json');schedule=read(t/'sampling-plan.json')", "v=variant(t,task_index);pools=read(t/'sampling-pools.json');schedule=read(t/v['schedule_file'])")
guard=guard.replace("sha(t/'sampling-plan.json')!=p['data']['schedule_sha256']", "sha(t/v['schedule_file'])!=v['schedule_sha256']")
guard=guard.replace("expected_schedule=[[positive[i],*rng.sample(pools['explicit_negative'],3)] for i in range(3000)]", "negatives=[rng.sample(pools['explicit_negative'],3) for _ in range(3000)];expected_schedule=[[positive[i],*negatives[i][:v['negative_presentations']]] for i in range(3000)]")
guard=guard.replace('len(set(batch))!=4','len(set(batch))!=v[\'accumulation\']')
guard=guard.replace("out=t/'release/approved-core.json'", "out=t/'release'/('approved-core-task-'+str(variant(t)['index'])+'.json')")
put(T/'continuation_guard.py',guard)
verify=(BASE/'verify_package.py').read_text().replace("release,schedule,_,_=inputs(T,require_approval=not preparation_only)","for index in range(4):release,schedule,_,_=inputs(T,require_approval=not preparation_only,task_index=index)").replace('planned_updates=len(schedule)','planned_updates=len(schedule)*4,trial_tasks=4')
put(T/'verify_package.py',verify)
train=(BASE/'train_balanced.py').read_text().replace('One approved two-row continuation','One approved array element; only billboard row 133')
train=train.replace('stop_without_gain,read,sha','stop_without_gain,read,sha,variant')
train=train.replace("release,schedule,original,resume=inputs(T);", "v=variant(T);run_id=os.environ['SLURM_ARRAY_JOB_ID']+'_'+str(v['index']);release,schedule,original,resume=inputs(T);")
train=train.replace('f"output/rf-billboard-{os.environ[\'SLURM_JOB_ID\']}"','f"output/rf-billboard-batch-{run_id}"')
train=train.replace("configure(model,[133],.0001)","configure(model,[133],v['lr'])")
train=train.replace("actual_job_id=os.environ['SLURM_JOB_ID']", "actual_job_id=run_id,slurm_job_id=os.environ['SLURM_JOB_ID'],array_task_index=v['index'],variant=v")
train=train.replace('backward(loss/4);total+=float(loss.detach())/4',"backward(loss/v['accumulation']);total+=float(loss.detach())/v['accumulation']")
train=train.replace("print(f'balanced {step}/3000;", "print(f'billboard {step}/3000;")
put(T/'train_balanced.py',train)

# Transportable copies of already-consumed references; training never reads these.
lock=read(EVAL/'evaluation-lock.json');release=read(T/'release/candidate-manifest-v2.json')
photo_paths={r['image_sha256']:'release/'+r['source_path'] for r in release['images']}
image_map={}
for h,row in lock['images'].items():
    if h in photo_paths:relative=photo_paths[h]
    else:
        relative='known-regression/images/'+h+Path(row['path']).suffix
        target=T/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(row['path'],target)
    assert sha(T/relative)==h
    image_map[h]=dict(path=relative,width=row['width'],height=row['height'])
put(T/'known-regression/images.json',image_map)
for refpath in (EVAL/'references').glob('*.json'):
    ref=read(refpath)
    for frame in ref['frames']:frame['path']=image_map[frame['sha256']]['path']
    put(T/'known-regression/references'/refpath.name,ref)
    for baseline,src in [('original','original_baseline'),('current','candidate')]:
        shutil.copyfile(EVAL/src/refpath.stem/'scoped-results.json',T/'known-regression'/f'{baseline}-{refpath.stem}.json')
shutil.copyfile(Path(r'C:\Users\nazee\.codex\visualizations\2026\10\11\01a12a01-d564-7de0-91f4-a16484eea2cb\score_video_reference.py'),T/'score_video_reference.py')
put(T/'regression_stage.py','''"""Score frozen selected state against KNOWN references; never reselect/train."""
import argparse,json,os,time
from pathlib import Path
import torch
from PIL import Image
from torchvision.transforms import functional as TF
from continuation_guard import read,sha,variant
from scoped_engine import build_model
from scoped_metrics import decode
from determinism_policy import math_attention
from head_policy import fingerprint_frozen
from score_video_reference import score
T=Path(__file__).resolve().parent
def save(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,indent=2,allow_nan=False)
def gate(b,c):
    zero=dict(complete_tp=0,complete_fp=0,partial_positive_hits=0);failures=[]
    for name in sorted(set(b['by_class'])|set(c['by_class'])):
        before=b['by_class'].get(name,zero);after=c['by_class'].get(name,zero)
        for k in zero:
            good=after[k]<=before[k] if k=='complete_fp' else after[k]>=before[k]
            if not good:failures.append(dict(category=name,metric=k,before=before[k],after=after[k]))
    return dict(passed=not failures,failures=failures)
@math_attention()
def run(project):
    v=variant(T);run_id=os.environ['SLURM_ARRAY_JOB_ID']+'_'+str(v['index'])
    out=project/'output'/('rf-billboard-batch-'+run_id);report=read(out/'experiment-report.json')
    best=out/'best.pt';pinned=sha(best)
    if pinned!=report['best_checkpoint_sha256']:raise ValueError('Selected checkpoint differs')
    save(out/'regression-lock.json',dict(best_checkpoint_sha256=pinned,best_step=report['best_step'],selection='already frozen by validation alone',references='known, consumed; not fresh heldout',production_adoption=False))
    if not report['new_candidate_selected']:
        save(out/'known-regression.json',dict(status='step-zero-unchanged-reuse-pinned-current-scores',best_checkpoint_sha256=pinned,scored_new_images=0,retention_passed=True,reference_sets=6,production_adoption=False));return
    torch.set_num_threads(2);torch.manual_seed(17);torch.cuda.manual_seed_all(17);torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.backends.cudnn.benchmark=False
    model=build_model(project/'output/rf-comparison-v1/assets/rf-detr-small.pth',T/'rf-mapping.json')
    ck=torch.load(best,map_location='cpu',weights_only=True);model.load_state_dict(ck['model_state_dict'],strict=True);del ck
    model=model.to('cuda:0').eval();frozen=fingerprint_frozen(model);predictions={};started=time.monotonic()
    with torch.inference_mode():
        for h,row in read(T/'known-regression/images.json').items():
            if time.monotonic()-started>420:raise ValueError('Regression time cap; preserve partial output')
            path=T/row['path']
            if sha(path)!=h:raise ValueError('Known image changed')
            with Image.open(path) as im:x=TF.normalize(TF.resize(TF.to_tensor(im.convert('RGB')),[512,512],antialias=False),[.485,.456,.406],[.229,.224,.225]).unsqueeze(0).to('cuda:0')
            predictions[h]=decode(model(x),row['width'],row['height'])
    save(out/'known-regression-predictions.json',predictions);checks={}
    for path in sorted((T/'known-regression/references').glob('*.json')):
        ref=read(path);payload=dict(reference_sha256=ref['source_sha256'],class_namespace='native-canonical',vocabulary_sha256=ref['vocabulary_sha256'],confidence_threshold=.35,frames=[dict(frame_id=f['id'],detections=predictions[f['sha256']]) for f in ref['frames']])
        result=score(ref,payload,ref['source_sha256']);save(out/('known-scored-'+path.stem+'.json'),result)
        checks[path.stem]={b:gate(read(T/'known-regression'/f'{b}-{path.stem}.json'),result) for b in ('original','current')}
    if fingerprint_frozen(model)!=frozen or sha(best)!=pinned:raise ValueError('Frozen inference state/checkpoint changed')
    save(out/'known-regression.json',dict(status='known-regression-scored-no-reselection',best_checkpoint_sha256=pinned,scored_new_images=len(predictions),reference_sets=6,retention_passed=all(c['passed'] for group in checks.values() for c in group.values()),checks=checks,references_consumed=True,optimizer_updates=0,production_adoption=False,elapsed_seconds=time.monotonic()-started))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--project',type=Path,required=True);run(ap.parse_args().project)
''')

put(T/'run-array.sbatch',f'''#!/bin/bash -l
#SBATCH --job-name=frametrail-rf-billboard-batch
#SBATCH --partition=gpu_a100_il
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --gres=gpu:1
#SBATCH --array=0-3%2
#SBATCH --no-requeue
#SBATCH --time=00:45:00
#SBATCH --output=frametrail-rf-billboard-batch-%A_%a.log
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
[[ "$SLURM_ARRAY_JOB_ID" =~ ^[0-9]+$ && "$SLURM_ARRAY_TASK_ID" =~ ^[0-3]$ && "$SLURM_ARRAY_TASK_COUNT" == 4 ]] || exit 65
task_tools="$PWD/output/training-general-v1/{name}"
task_run_id="${{SLURM_ARRAY_JOB_ID}}_${{SLURM_ARRAY_TASK_ID}}"
export PYTHONPATH="$PWD/output/rf-comparison-v1/python-overlay"
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 CUBLAS_WORKSPACE_CONFIG=:4096:8
module load devel/miniforge/25.3.1-python-3.12
task_training_exit=77
task_post_exit=77
finish() {{
  task_exit=$?
  trap - EXIT
  if ! "$PWD/.venv/bin/python" -B "$task_tools/bundle_results.py" --project "$PWD" --job "$task_run_id" --exit-code "$task_exit" --training-exit "$task_training_exit" --post-exit "$task_post_exit"; then
    echo 'Archive failed; preserve task output and log.'
    if [[ "$task_exit" -eq 0 ]]; then task_exit=3; fi
  fi
  exit "$task_exit"
}}
trap finish EXIT
"$PWD/.venv/bin/python" -B "$task_tools/verify_package.py"
set +e
timeout --signal=TERM --kill-after=30s 1800s srun "$PWD/.venv/bin/python" -u -B "$task_tools/train_balanced.py"
task_training_exit=$?
set -e
[[ "$task_training_exit" -eq 0 ]] || exit "$task_training_exit"
set +e
timeout --signal=TERM --kill-after=30s 480s srun "$PWD/.venv/bin/python" -u -B "$task_tools/regression_stage.py" --project "$PWD"
task_post_exit=$?
set -e
exit "$task_post_exit"
''')
(T/'run-balanced.sbatch').unlink()
bundle=(BASE/'bundle_results.py').read_text().replace('import argparse,json,hashlib,tarfile','import argparse,json,hashlib,tarfile,re')
bundle=bundle.replace('def bundle(project,job,exit_code):','def bundle(project,job,exit_code,training_exit,post_exit):').replace("if not job.isdigit()", "if not re.fullmatch(r'[0-9]+_[0-3]',job)")
bundle=bundle.replace('rf-billboard-','rf-billboard-batch-').replace('process_exit_code=exit_code,','process_exit_code=exit_code,training_exit_code=training_exit,postprocessing_exit_code=post_exit,')
bundle=bundle.replace("tar.add(out,arcname='output/'+out.name)","tar.add(out,arcname='output/'+out.name,filter=lambda info: None if '/checkpoints' in info.name else info)")
bundle=bundle.replace("ap.add_argument('--exit-code',type=int,required=True);", "ap.add_argument('--exit-code',type=int,required=True);ap.add_argument('--training-exit',type=int,required=True);ap.add_argument('--post-exit',type=int,required=True);")
bundle=bundle.replace('bundle(a.project,a.job,a.exit_code)','bundle(a.project,a.job,a.exit_code,a.training_exit,a.post_exit)')
put(T/'bundle_results.py',bundle)

submit=(BASE/'submit.sh').read_text().replace('run-balanced.sbatch','run-array.sbatch')
submit=submit.replace('mkdir "$task_tools/submission-lock"', '''# Read-only scheduler/account evidence; never assume public maxima are account entitlements.
scontrol show config > "$task_tools/scheduler-config.txt" 2>&1 || true
sacctmgr -nP show assoc where user="$(id -un)" format=User,Account,Partition,QOS,MaxJobs,MaxSubmitJobs,GrpTRES > "$task_tools/account-limits.txt" 2>&1 || true
sbatch --test-only "$task_tools/run-array.sbatch" > "$task_tools/scheduler-test-only.txt" 2>&1 || { cat "$task_tools/scheduler-test-only.txt"; exit 1; }
mkdir "$task_tools/submission-lock"''')
submit=submit.replace('Submitted ONE approved billboard calibration continuation.','Submitted ONE approved array containing FOUR fixed billboard trials; at most TWO GPUs concurrently.')
put(T/'submit.sh',submit)
put(T/'show-output.sh','''#!/bin/bash
set -euo pipefail
task_tools=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd "$(ws_find frametrail)/FrameTrail"
[[ -f "$task_tools/submitted-job-id.txt" ]] || { echo 'No recorded array; inspect a retained submission lock before any retry.'; exit 0; }
task_job=$(cat "$task_tools/submitted-job-id.txt")
[[ "$task_job" =~ ^[0-9]+$ ]] || exit 1
echo "FRAMETRAIL_JOB_ID=$task_job"
sacct -j "$task_job" --format=JobID,JobName%32,State,ExitCode,Start,Elapsed
for task_index in 0 1 2 3; do
  task_run="${task_job}_${task_index}"
  task_report="output/rf-billboard-batch-$task_run/experiment-report.json"
  if [[ -f "$task_report" ]]; then cat "$task_report"; else echo "Task $task_index report not ready"; fi
  task_sidecar="output/frametrail-rf-billboard-batch-results-$task_run.tar.gz.sha256"
  if [[ -f "$task_sidecar" ]]; then
    task_hash=$(awk '{print $1}' "$task_sidecar")
    [[ "$task_hash" =~ ^[0-9a-f]{64}$ ]] || exit 1
    echo "FRAMETRAIL_TASK_ARCHIVE=$task_index:$task_hash"
  else echo "Task $task_index archive not ready"; fi
done
''')

# Existing transport remains Base64 over verified SSH, with fresh exact identity.
for f in ('Invoke-KitScript.ps1','Validate-Helpers.ps1'):shutil.copyfile(OLD/f,OUT/f)
for f in ('bootstrap-template.sh','prepare_archive.py','Launch-Approved-Run.ps1'):
    s=(OLD/f).read_text().replace('rf-billboard-716ca2cf-v1',name).replace('one approved billboard calibration package','approved four-trial billboard array package')
    put(OUT/f,s)
put(OUT/'Check-Run.ps1',f'''$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Invoke-KitScript.ps1')
$taskScript = 'set -euo pipefail; cd "$(ws_find frametrail)/FrameTrail"; bash "$PWD/output/training-general-v1/{name}/show-output.sh"'
$taskResult = Invoke-FrameTrailKitScript -Script $taskScript -LogPath (Join-Path $PSScriptRoot 'latest-output.txt')
if ($taskResult.ExitCode -ne 0) {{ throw 'Status failed; no new submission.' }}
$taskJob = [regex]::Match($taskResult.Text, '(?m)^FRAMETRAIL_JOB_ID=(\d+)\s*$')
if ($taskJob.Success) {{
    $taskArchives = @([regex]::Matches($taskResult.Text, '(?m)^FRAMETRAIL_TASK_ARCHIVE=([0-3]):([0-9a-f]{{64}})\s*$') | ForEach-Object {{ [ordered]@{{index=[int]$_.Groups[1].Value; sha256=$_.Groups[2].Value}} }})
    [ordered]@{{actual_job_id=$taskJob.Groups[1].Value;protocol_sha256='{digest}';archives=$taskArchives;approved_for_application=$false}} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'run-receipt.json') -Encoding utf8
    if ($taskArchives.Count -eq 4) {{ Write-Host 'All four archives are ready. Run Retrieve-Results.ps1 once for the full batch.' }}
}}
''')
put(OUT/'Retrieve-Results.ps1','''$ErrorActionPreference = 'Stop'
$taskReceipt = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'run-receipt.json') | ConvertFrom-Json
if ($taskReceipt.actual_job_id -notmatch '^\d+$' -or @($taskReceipt.archives).Count -ne 4) { throw 'Run Check-Run.ps1 after all four tasks finish; preserve failed-task archives too.' }
$taskJob = [string]$taskReceipt.actual_job_id
$taskDestination = Join-Path $PSScriptRoot ('retrieval-' + $taskJob)
if (Test-Path -LiteralPath $taskDestination) { throw 'Retrieval already exists; inspect without overwrite or automatic retry.' }
New-Item -ItemType Directory -Path $taskDestination | Out-Null
$taskRemote = 'ka_udxvl@uc3.scc.kit.edu:/pfs/work9/workspace/scratch/ka_udxvl-frametrail/FrameTrail/output/'
$taskSources = @()
foreach ($taskRecord in $taskReceipt.archives) {
    if ($taskRecord.index -notin 0,1,2,3 -or $taskRecord.sha256 -notmatch '^[0-9a-f]{64}$') { throw 'Invalid archive receipt' }
    $taskName = 'frametrail-rf-billboard-batch-results-' + $taskJob + '_' + $taskRecord.index + '.tar.gz'
    $taskSources += $taskRemote + $taskName
    $taskSources += $taskRemote + $taskName + '.sha256'
}
& scp -o StrictHostKeyChecking=yes @taskSources $taskDestination
if ($LASTEXITCODE -ne 0) { throw 'Batch retrieval stopped; preserve partial bytes.' }
foreach ($taskRecord in $taskReceipt.archives) {
    $taskRun = $taskJob + '_' + $taskRecord.index
    $taskName = 'frametrail-rf-billboard-batch-results-' + $taskRun + '.tar.gz'
    $taskLine = (Get-Content -Raw -LiteralPath (Join-Path $taskDestination ($taskName + '.sha256'))).Trim()
    if ($taskLine -notmatch ('^' + $taskRecord.sha256 + '\s+\*?' + [regex]::Escape($taskName) + '$')) { throw 'Server checksum disagrees with completed-task receipt.' }
    $taskVerifiedParent = Join-Path $taskDestination ('task-' + $taskRecord.index)
    New-Item -ItemType Directory -Path $taskVerifiedParent | Out-Null
    & 'C:/Users/nazee/Documents/All Modules/FrameTrail/.deps/rfdetr-probe-cpu/Scripts/python.exe' -B -X utf8 (Join-Path $PSScriptRoot 'verify_results.py') --archive (Join-Path $taskDestination $taskName) --job $taskRun --expected-sha $taskRecord.sha256 --destination (Join-Path $taskVerifiedParent ('verified-' + $taskRun))
    if ($LASTEXITCODE -ne 0) { throw 'Task structural verification failed; all bytes preserved.' }
}
& 'C:/Users/nazee/Documents/All Modules/FrameTrail/.deps/rfdetr-probe-cpu/Scripts/python.exe' -B -X utf8 (Join-Path $PSScriptRoot 'compare_batch.py') --retrieval $taskDestination
if ($LASTEXITCODE -ne 0) { throw 'Batch comparison needs inspection; no model adopted.' }
''')
verifier=(OLD/'verify_results.py').read_text().replace('rf-billboard-','rf-billboard-batch-').replace("PROTOCOL_SHA='716ca2cf411984698e6d096f00fd5ef01995bee9ed4fe0c82a742e26c4bc6e1c'",f"PROTOCOL_SHA='{digest}'")
start=verifier.index('SCHEDULE_SHA=');end=verifier.index('\ndef verify(',start)
verifier=verifier[:start]+'''def verify_schedule(schedule,job):
    index=int(job.rsplit('_',1)[1]);identity=read(Path(__file__).with_name('PROPOSAL_IDENTITY.json'))
    tools=Path(__file__).parent/identity['package_directory'];p=read(tools/'protocol.json')
    if sha(tools/'protocol.json')!=PROTOCOL_SHA:raise ValueError('Batch protocol differs')
    v=p['variants'][index];approved_path=tools/v['schedule_file']
    if sha(approved_path)!=v['schedule_sha256'] or schedule!=read(approved_path):raise ValueError('Returned task sampler differs')
'''+verifier[end:]
verifier=verifier.replace('not job.isdigit()',"not re.fullmatch(r'[0-9]+_[0-3]',job)").replace("if transfer['process_exit_code']==0:","if transfer.get('training_exit_code')==0:")
verifier=verifier.replace('verify_schedule(schedule)','verify_schedule(schedule,job)')
verifier=verifier.replace("report=read(out/'experiment-report.json');pre=read(out/'preflight.json')", "report=read(out/'experiment-report.json');pre=read(out/'preflight.json');index=int(job.rsplit('_',1)[1]);expected_variant=read(Path(__file__).with_name('protocol.json'))['variants'][index]\n        if report.get('variant')!=expected_variant or pre.get('variant')!=expected_variant or report.get('array_task_index')!=index:raise ValueError('Wrong array variant')")
put(OUT/'verify_results.py',verifier)
put(OUT/'compare_batch.py','''"""Compare fixed validation-selected states; never choose using known regression."""
import argparse,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
identity=json.loads((HERE/'PROPOSAL_IDENTITY.json').read_text());sys.path.insert(0,str(HERE/identity['package_directory']))
from continuation_guard import read,sha
from selection_policy import ranking
def compare(retrieval):
    rows=[];complete=True
    for i in range(4):
        matches=list((retrieval/('task-'+str(i))).glob('verified-*/output/rf-billboard-batch-*'))
        if len(matches)!=1:raise ValueError('Need all four verified task outputs, including failures')
        out=matches[0];t=read(out/'transfer.json')
        if t['training_exit_code']!=0:
            rows.append(dict(index=i,status='training-failed-or-partial',exit_code=t['training_exit_code']));complete=False;continue
        r=read(out/'experiment-report.json');v=read(out/f"validation-{r['best_step']:04}.json")
        if sha(out/'best.pt')!=r['best_checkpoint_sha256']:raise ValueError('Selected checkpoint changed')
        reg=read(out/'known-regression.json') if (out/'known-regression.json').exists() else None
        rows.append(dict(index=i,status='complete',best_step=r['best_step'],strict_gain=r['new_candidate_selected'],validation_ranking=list(ranking(v)),checkpoint_sha256=r['best_checkpoint_sha256'],regression_retained=reg.get('retention_passed') if reg else None,postprocessing_exit=t['postprocessing_exit_code']))
    candidates=[r for r in rows if r.get('strict_gain')]
    winner=max(candidates,key=lambda r:(tuple(r['validation_ranking']),-r['index'])) if complete and candidates else None
    result=dict(status='validation-comparison-complete' if complete else 'incomplete-batch-inspect-failures-before-selection',trials=rows,validation_only_winner_index=winner['index'] if winner else None,ranking_frozen_before_using_regression=True,production_adoption=False,independent_fresh_test_available=False,strict_export_hold_from_previous_model_not_waived=True)
    with (retrieval/'batch-comparison.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--retrieval',type=Path,required=True);compare(ap.parse_args().retrieval)
''')
files={x.relative_to(T).as_posix():sha(x) for x in sorted(T.rglob('*')) if x.is_file()}
put(T/'package-files.json',dict(schema=1,protocol_sha256=digest,files=files))
for x in [*T.glob('*.py'),*OUT.glob('*.py')]:ast.parse(x.read_text(encoding='utf-8-sig'),filename=str(x))
print(json.dumps(dict(output=str(OUT),package=name,protocol_sha256=digest,sealed_files=len(files),regression_images=len(image_map),new_GPU_jobs=0),indent=2))
