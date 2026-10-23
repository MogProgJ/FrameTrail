"""Import user-supplied cluster evidence without another SSH status connection."""
import datetime,hashlib,json,re,shutil
from pathlib import Path
P=Path(__file__).resolve().parent
SOURCE=Path(r'C:\Users\nazee\.codex\attachments\3607a95b-0c78-4ecf-b1c2-09084ad0bb7b\Pasted text.txt')
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as f:f.write(v if isinstance(v,str) else json.dumps(v,indent=2,allow_nan=False)+'\n')
raw=SOURCE.read_bytes();text=raw.decode('utf-16') if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else raw.decode('utf-8-sig');job='7818553'
identity=read(P/'PROPOSAL_IDENTITY.json');protocol=read(P/'protocol.json')
assert re.findall(r'(?m)^FRAMETRAIL_JOB_ID=(\d+)\s*$',text)==[job]
archives=re.findall(r'(?m)^FRAMETRAIL_TASK_ARCHIVE=([0-3]):([0-9a-f]{64})\s*$',text)
assert len(archives)==4 and sorted(int(i) for i,h in archives)==[0,1,2,3]
reports=[];decoder=json.JSONDecoder()
for match in re.finditer(r'(?m)^\{\s*$',text):
    obj,_=decoder.raw_decode(text[match.start():]);reports.append(obj)
assert len(reports)==4;total_seconds=0
for index,r in enumerate(reports):
    assert r['actual_job_id']==f'{job}_{index}' and r['array_task_index']==index and r['variant']==protocol['variants'][index]
    assert r['status']=='complete-no-improving-candidate' and r['updates']==1500 and r['best_step']==0 and r['new_candidate_selected'] is False
    assert r['completion_reason']=='protocol-early-stop-no-gain' and r['starting_checkpoint_sha256']==protocol['starting_checkpoint']['sha256']
    assert r['active_classifier_heads']==protocol['active_classifier_heads'] and r['active_classifier_rows']==[133]
    assert r['frozen_parameters_and_buffers_unchanged'] is True and r['inactive_classifier_rows_unchanged'] is True and r['retention_against_both_baselines'] is True
    assert r['test_and_video_used'] is False and r['approved_for_application'] is False
    line=re.search(r'(?m)^'+job+'_'+str(index)+r'\s+frametrail-rf-selector\s+COMPLETED\s+0:0\s+\S+\s+(\d\d):(\d\d):(\d\d)\s*$',text)
    assert line,'Need completed scheduler row for task '+str(index)
    hh,mm,ss=map(int,line.groups());total_seconds+=hh*3600+mm*60+ss
evidence=P/'completion-evidence-7818553';evidence.mkdir(exist_ok=False);shutil.copy2(SOURCE,evidence/'cluster-output.txt');shutil.copy2(P/'run-receipt.json',evidence/'run-receipt-before-completion.json')
for i,r in enumerate(reports):save(evidence/f'task-{i}-report-from-cluster.json',r)
receipt=dict(actual_job_id=job,protocol_sha256=identity['protocol_sha256'],archives=[dict(index=int(i),sha256=h) for i,h in sorted(archives)],approved_for_application=False,evidence_source=str(evidence/'cluster-output.txt'),evidence_sha256=sha(evidence/'cluster-output.txt'),status='all-four-tasks-completed-archives-ready-awaiting-local-retrieval-and-audit')
(P/'run-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
state=dict(read(P/'CURRENT_STATE_SUBMITTED_7818553.json'));state.update(status=receipt['status'],last_observed_scheduler_state='COMPLETED',observation_source='User-supplied cluster show-output command, preserved locally; no extra SSH query',tasks_completed=4,task_exit_codes=['0:0']*4,reports_claim_no_improving_candidate=True,reported_selected_steps=[0]*4,independent_archive_and_tensor_audit_complete=False,aggregate_scheduler_allocation_seconds=total_seconds,aggregate_scheduler_allocation_GPU_hours=total_seconds/3600,archives=receipt['archives'],archive_checksums_imported_locally=True,results_retrieved=False,new_cluster_jobs_submitted_by_this_step=0,next_action='Run Retrieve-Results.ps1 in Windows PowerShell for one SFTP connection; no further status login is needed.',retrieval_command='powershell -NoProfile -ExecutionPolicy Bypass -File "'+str(P/'Retrieve-Results.ps1')+'"')
save(P/'CURRENT_STATE_COMPLETED_7818553.json',state)
handoff=f'''# Latest FrameTrail state — array 7818553 complete; retrieval ready

All four scheduler tasks completed with exit0:0. Each cluster report claims no eligible strict gain, 1500updates under the early-stop rule, selected step0 and unchanged frozen parameters/inactive rows. This is provisional cluster evidence: full local archive, independent prediction/selection rescore and tensor audits have not run. Current model remains job7805570step100; no app adoption. Aggregate task allocation time was {total_seconds} seconds ({total_seconds/3600:.4f} GPU-hours), below the3GPU-hour requested budget.

All four result hashes were imported from the user's existing cluster-session output into run-receipt.json. That raw output and the previous receipt are preserved under completion-evidence-7818553. No additional SSH status connection is needed. The existing Retrieve-Results.ps1 uses one batch SFTP connection for all four archives and four sidecars, verifies the expected names/checksums, safely extracts each archive, compares frozen validation selections and runs the independent CPU audit automatically.

Run in Windows PowerShell:

```powershell
{state['retrieval_command']}
```

Enter KIT OTP/password directly in the terminal. Never paste credentials into chat. If a transfer/audit fails, preserve all bytes and inspect; do not automatically retry, overwrite, relaunch or submit replacement jobs. Do not infer why the trials failed to qualify until the validation traces have been retrieved and independently audited.

Protocol a77d9663fcc898b6a257f6722dd37bc24b1d3a2d3065eb8cce5f0625403f019a is unchanged. Four trials trained only billboard row133 in main/encoder proposal heads, eight separate reviewed TRAIN sign regions, dense encoder classification, same135validation/both-baseline guards. Frozen parameters do not imply unchanged box outputs. Known regression references are consumed, not fresh tests. Strict ONNX hold remains, explicit native preview exists, standard YOLOX-S default preserved and production_adoption=false.

Standing instruction: continue authorized local and bounded cluster work without routine approval prompts, preserving exact scopes/provenance, resource limits, efficient batching, model/data gates, validation-only selection and no retries/replacements. Stop only for genuinely needed human input. End every user-facing response with the best concrete next project step and why. Do not edit MiniERP/Carrington or launch a visible GUI without request.

Full receipts/helpers: {P}

Next step: run the retrieval command once, because all result hashes are recorded and direct KIT authentication is the remaining input before the independent local audit.
'''
save(P/'COMPLETED_HANDOFF_7818553.md',handoff);root=P.parents[1];shutil.copy2(root/'CURRENT_HANDOFF.md',evidence/'HANDOFF_BEFORE_COMPLETION.md');(root/'CURRENT_HANDOFF.md').write_text(handoff,encoding='utf-8',newline='\n')
save(P.parent/'LATEST_FRAMETRAIL_STATE_COMPLETED_7818553.json',state)
save(P/'completion-stage-7818553-sha256.json',dict(actual_array_job_id=job,protocol_sha256=identity['protocol_sha256'],files={name:sha(P/name) for name in ('run-receipt.json','CURRENT_STATE_COMPLETED_7818553.json','COMPLETED_HANDOFF_7818553.md','record_completion_7818553.py')},evidence={f.name:sha(f) for f in evidence.iterdir() if f.is_file()}))
print(json.dumps(dict(actual_array_job_id=job,completed_tasks=4,selected_steps=[0]*4,archives=receipt['archives'],aggregate_scheduler_allocation_seconds=total_seconds,extra_SSH_status_connections=0,retrieval_ready=True),indent=2))
