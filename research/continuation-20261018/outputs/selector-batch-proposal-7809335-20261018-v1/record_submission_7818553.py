"""Preserve observed submission evidence; no network, retry or new submission."""
import datetime,hashlib,json,re,shutil
from pathlib import Path
P=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as f:f.write(v if isinstance(v,str) else json.dumps(v,indent=2)+'\n')
receipt=read(P/'run-receipt.json');identity=read(P/'PROPOSAL_IDENTITY.json');job='7818553'
assert receipt['actual_job_id']==job and receipt['protocol_sha256']==identity['protocol_sha256']
raw=(P/'launch-output.txt').read_bytes();log=raw.decode('utf-16') if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else raw.decode('utf-8-sig')
assert re.search(r'(?m)^FRAMETRAIL_JOB_ID='+job+r'\s*$',log)
assert 'KIT-runtime-and-input-preflight-passed' in log and 'approved-code-assets-and-scope-verified' in log
assert 'PENDING' in log and 'Submitted ONE approved array' in log
evidence=P/'submission-evidence-7818553';evidence.mkdir(exist_ok=False)
for name in ('launch-output.txt','run-receipt.json'):shutil.copy2(P/name,evidence/name)
state=dict(read(P/'CURRENT_STATE_APPROVED.json'))
state.update(status='selector-four-trial-array-submitted-last-observed-pending',SSH_contacted=True,cluster_submitted=True,real_array_job_id=job,last_observed_scheduler_state='PENDING',observation_source='preserved launch-output.txt; not a fresh scheduler query',launch_output_mtime_UTC=datetime.datetime.fromtimestamp((P/'launch-output.txt').stat().st_mtime,datetime.timezone.utc).isoformat(),runtime_and_input_preflight_passed=True,scheduler_admitted_actual_array=True,live_account_limits_verified=False,account_evidence='Submission script recorded remote scheduler/account diagnostics and ran sbatch --test-only before the accepted submission. Those diagnostic files have not been downloaded, so detailed limits remain uninspected.',next_action='Run Check-Run.ps1 against recorded array7818553; direct KIT authentication is needed. Do not run the launcher again.',status_command='powershell -NoProfile -ExecutionPolicy Bypass -File "'+str(P/'Check-Run.ps1')+'"',default_model_unchanged=True)
save(P/'CURRENT_STATE_SUBMITTED_7818553.json',state)
text=f'''# Latest FrameTrail state — selector array {job} submitted

Array {job} was successfully submitted as one four-task selector array, at most two concurrent GPUs. Last observed scheduler state was PENDING in the launch output, not a fresh status query. Code/assets/scope and KIT runtime/input preflights passed. The package upload reported four seconds; total authentication/preflight/launch duration was not instrumented. Do not relaunch or create a replacement.

Exact scope remains the approved protocol {identity['protocol_sha256']}: billboard row133 in main and encoder proposal classifiers; encoder learning rates0.00001/0.00003 crossed with sign-region penalties1/3; main learning rate0.0001; eight separate TRAIN sign panels and dense encoder classification. Other rows/parameters/buffers frozen bitwise, but proposal changes can affect boxes and other detections. Preserve validation-only selection and both-baseline guards. One A100/two CPUs/8GiB/45minutes per task, maximum3000updates,1800seconds training and480seconds known regression; stop1500without gain. Array0-3%2, aggregate requested maximum3GPUhours, no retries/replacements.

Submission evidence is preserved in submission-evidence-7818553. CURRENT_STATE_SUBMITTED_7818553.json supersedes the earlier approved-but-unsubmitted snapshots. Remote scheduler/account diagnostics were recorded and admission testing preceded the accepted sbatch; detailed account limits have not been downloaded or independently inspected.

Status command:

```powershell
{state['status_command']}
```

Check-Run.ps1 follows the actual recorded array and records the four result hashes when ready. Once all four archives are available, Retrieve-Results.ps1 retrieves the full batch in one SFTP connection and runs bounded extraction, scope/schedule checks, provisional comparison and independent local validation/selection/tensor audits. Preserve failed-task evidence. Direct KIT OTP/password entry is currently required for remote checks; never ask for pasted credentials.

Current app/model remains job7805570step100, known washing3/15 and billboard0/19. Strict ONNX numerical qualification is held, explicit preview remains, standard YOLOX-S default is preserved and production_adoption=false. Consumed reference sets are known regression evidence, not fresh tests.

Latest standing instruction: continue authorized local and bounded cluster work without routine approval prompts. Preserve resource limits, batching, exact scope/authorization provenance, model/data guards and no retries/replacements. Ask only for genuinely necessary human input. End every user-facing response with the best concrete next step and why. Do not edit MiniERP/Carrington or open a visible GUI without request.

Full evidence and helpers: {P}

Next step: run the status command and enter KIT authentication directly, because array {job} is submitted and its current execution/result state is the next missing evidence.
'''
save(P/'SUBMITTED_HANDOFF_7818553.md',text)
root=P.parents[1];shutil.copy2(root/'CURRENT_HANDOFF.md',evidence/'HANDOFF_BEFORE_SUBMISSION.md');(root/'CURRENT_HANDOFF.md').write_text(text,encoding='utf-8',newline='\n')
save(P.parent/'LATEST_FRAMETRAIL_STATE_SUBMITTED_7818553.json',state)
save(P/'submission-stage-7818553-sha256.json',dict(actual_array_job_id=job,protocol_sha256=identity['protocol_sha256'],files={name:sha(P/name) for name in ('CURRENT_STATE_SUBMITTED_7818553.json','SUBMITTED_HANDOFF_7818553.md','record_submission_7818553.py')},evidence={p.name:sha(p) for p in evidence.iterdir() if p.is_file()}))
print(json.dumps(dict(actual_array_job_id=job,last_observed_state='PENDING',evidence_preserved=True,new_jobs_submitted_by_this_script=0)))
