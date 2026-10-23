"""Preserve actual submission evidence; never polls, submits or retries a job."""
import hashlib,json,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
AUDIT=HERE.parent/'billboard-batch-audit-7809335-20261018-v1'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as f:f.write(v if isinstance(v,str) else json.dumps(v,indent=2)+'\n')
receipt=read(HERE/'run-receipt.json');log_bytes=(HERE/'launch-output.txt').read_bytes()
log=log_bytes.decode('utf-16' if log_bytes[:2] in (b'\xff\xfe',b'\xfe\xff') else 'utf-8-sig')
assert receipt['actual_job_id']=='7809335' and receipt['protocol_sha256']=='0a255598b74eb1d29d83ee1be10d517ae407fbda2c57e4565b51028d615343fd'
for text in ('FRAMETRAIL_JOB_ID=7809335','Submitted ONE approved array containing FOUR fixed billboard trials; at most TWO GPUs concurrently.','KIT-runtime-and-input-preflight-passed','PENDING'):
    assert text in log,text
evidence=HERE/'submission-evidence-7809335';evidence.mkdir(exist_ok=False)
for name in ('run-receipt.json','launch-output.txt'):shutil.copyfile(HERE/name,evidence/name)
assert 'Ran 3 tests' in (AUDIT/'audit-contract-tests.txt').read_text(encoding='utf-8-sig')
state=dict(status='approved-four-trial-array-submitted-last-reported-pending',actual_array_job_id='7809335',task_ids=[f'7809335_{i}' for i in range(4)],maximum_concurrent_GPUs=2,protocol_sha256=receipt['protocol_sha256'],archive_sha256=read(HERE/'archive-receipt.json')['archive_sha256'],observed_at_UTC='2026-10-18T15:57:57Z',observation='Saved successful launcher output and user console transcript; no fresh remote status query performed by Codex.',last_reported_state='PENDING',completed_tasks_known=0,task_archives_reported_ready=0,approval_recorded=True,upload_complete=True,cluster_submitted=True,local_preparation_and_KIT_runtime_preflight_passed=True,scheduler_submission_test_passed_before_actual_submission=True,exact_account_maximums_locally_available=False,automatic_retries=0,replacement_jobs=0,local_audit_prepared=str(AUDIT/'audit_batch.py'),local_audit_contract_tests_passed=3,real_model_training_or_inference_run_locally=False,source_evidence={name:sha(evidence/name) for name in ('run-receipt.json','launch-output.txt')},supersedes=['CURRENT_STATE_APPROVED.json pre-submission status','APPROVED_HANDOFF.md pre-submission status','all earlier unapproved preparation status snapshots'],next_action='Run Check-Run.ps1 for actual array7809335 using direct KIT authentication. When all four task archives are ready, retrieve once and continue independent local auditing automatically. Never run the launch helper to check status.',production_adoption=False,strict_numerical_export_gate_passed=False)
save(HERE/'CURRENT_STATE_SUBMITTED_7809335.json',state)
save(HERE/'SUBMITTED_HANDOFF_7809335.md',f'''# Current FrameTrail state: array7809335 submitted

This is the latest state, superseding earlier approved-but-unsubmitted and unapproved status snapshots. Historical receipts remain preserved. Actual array**7809335** was submitted once with four tasks7809335_0 through7809335_3 and a maximum of two concurrent A100s. The saved submission response reported PENDING; no fresh remote status has been obtained by Codex. Do not infer running/completion from submission success.

The approved package, all3015 sealed files, KIT runtime and starting checkpoint passed preflight. The four fixed variants remain ratio1:1/1:3 by learning rates.0001/.0003, starting job7805570step100, training only row133. Maximum3000updates,45minutes andoneA100/twoCPUs/8GiB per task; total requested wall allocation<=3GPUhours. No retries/requeue/replacements. All previous local-autonomy, communication, batching, frozen scope, validation-only selection and evidence-preservation instructions remain in force.

Submission evidence is preserved under submission-evidence-7809335 with exact launcher transcript and initial actual-ID receipt. Later Check-Run.ps1 updates the working run-receipt.json with completed task archive checksums. Scheduler test-only admission passed before submission; exact account quota maxima and scheduler-query files have not been downloaded locally. No other or replacement job was submitted.

Next remote action requires direct KIT OTP/password: run the existing Check-Run.ps1 in this folder. Do not rerun Launch-Approved-Run.ps1 as a status check. Once all four archives are ready, Retrieve-Results.ps1 downloads/verifies all four and makes a provisional validation-only comparison. Preserve failures; do not select a fallback variant based on consumed regression outcomes.

The independent local auditor is prepared at `{AUDIT/'audit_batch.py'}`. Three CPU contracts passed: current-baseline/tie replay, forged-metric rejection, and detection of changes to frozen features or inactive classifier rows. It rescales no thresholds and runs no model inference or optimizer. After retrieval it will independently replay every validation prediction/selection, check best/last checkpoint tensors against selected job7805570step100, and rescore all known-reference predictions. It has not audited cluster results yet, because no results are retrieved. Run it locally under the existing authorization once results arrive.

Existing model evidence and strict numerical ONNX hold are unchanged: washing3/15, billboard0/19 known targets; explicit preview available, stable default YOLOX-S retained; production_adoption=false. Known references are consumed regression evidence and cannot establish a new independent generalization claim.

Next step: check array7809335, because submission is confirmed and completion/results must now be verified before retrieval.
''')
save(AUDIT/'README.md',f'''# Local audit prepared for array7809335

No cluster results have been audited yet. Three CPU contracts passed using existing saved predictions and tiny synthetic tensors. No real model inference, optimizer updates, cluster contact or new jobs occurred.

After the original Retrieve-Results.ps1 has structurally verified all four actual task archives, run:

```powershell
& "C:\\Users\\nazee\\Documents\\All Modules\\FrameTrail\\.deps\\rfdetr-probe-cpu\\Scripts\\python.exe" -B -X utf8 "{AUDIT/'audit_batch.py'}"
```

The auditor uses the approved package to replay fixed schedules, finite loss traces, every validation metric and checkpoint-selection decision; it independently checks all frozen tensors and inactive rows in best/last checkpoints and rescores known-regression predictions. It requires actual7809335 task identities and preserves failures. A reported winner remains validation-only. Regression can hold a candidate, never select a different one. This stage does not run inference, export a model or approve application adoption.

Outputs are created exclusively in audited-results-v1. Existing results cannot be overwritten. All local follow-up work is already authorized; further cluster submissions require their own exact-scope approval.

Next step: obtain and retrieve all four actual task results, because an audit requires the returned evidence rather than the submission response.
''')
for folder in (HERE,AUDIT):
    selected=[p for p in folder.glob('*') if p.is_file() and (folder==AUDIT or p.name in ('CURRENT_STATE_SUBMITTED_7809335.json','SUBMITTED_HANDOFF_7809335.md','record_submission_7809335.py'))]
    save(folder/'submission-stage-7809335-sha256.json',dict(actual_array_job_id='7809335',files={p.name:sha(p) for p in selected}))
print(json.dumps({k:state[k] for k in ('status','actual_array_job_id','task_ids','maximum_concurrent_GPUs','local_audit_contract_tests_passed')},indent=2))
