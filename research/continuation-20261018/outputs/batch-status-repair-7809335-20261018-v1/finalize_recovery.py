"""Record repaired local helpers and completed-array evidence; no network."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
BATCH=HERE.parent/'billboard-batch-proposal-7805570-20261018-v1'
AUDIT=HERE.parent/'billboard-batch-audit-7809335-20261018-v1'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,v):
    with p.open('x',encoding='utf-8') as f:f.write(v if isinstance(v,str) else json.dumps(v,indent=2)+'\n')
state=read(HERE/'COMPLETION_STATE.json')
state.update(last_reported_state='all-four-COMPLETED-exit0:0',results_retrieved=False,independent_local_audit_pending=True,current_receipt=str(BATCH/'run-receipt.json'),local_status_parser_repaired=True,source_log_and_paste_hashes_agree=True,download_and_local_audit_automated_in_retrieval_helper=True,actual_reported_training_presentations=18000,reported_allocated_GPU_wall_seconds=2611,reported_allocated_GPU_wall_hours=2611/3600,resource_limit_exceeded=False,resource_note='Sum of four reported elapsed allocations:10:04+10:56+8:26+14:05. Logged task rows, not a billing/accounting report.',next_action='Run Retrieve-Results.ps1 once with direct KIT authentication. It downloads all four archives/sidecars, verifies them and runs the prepared independent CPU audit. Do not submit further training before interpreting the returned validation evidence.')
save(BATCH/'CURRENT_STATE_COMPLETED_7809335.json',state)
save(BATCH/'COMPLETED_HANDOFF_7809335.md',f'''# Current state: all four tasks completed; retrieval pending

This supersedes pending/submitted/pre-submission status snapshots. Array7809335 tasks0–3 all reported COMPLETED0:0. All stopped at1500updates without an eligible strict gain and selected step0, so the current starting model remains selected job7805570step100. This is the cluster's report, not yet independent confirmation of returned model tensors or an explanation of rejection causes. No new model is adopted.

Reported budget used:6000total updates/18000presentations. Sum of allocated task wall times is2611seconds (~0.725GPU-hours), below the approved three-GPU-hour ceiling. This is derived from elapsed task rows, not an account billing report. No replacement job is authorized or submitted.

All four archive hashes are recovered in run-receipt.json. The original remote output omitted final JSON newlines, joining }}FRAMETRAIL_TASK_ARCHIVE. The original local line-start regex missed all markers. The local parser is repaired and tested under actual WindowsPowerShell5.1 for both line-start and JSON-adjacent markers. Saved KIT log and user-pasted console hashes agree for every task. Original helpers/receipt/raw log are preserved in `{HERE}`. No network contact, remote package edit, threshold change or new training occurred for this repair.

Retrieve-Results.ps1 is ready in this folder. It uses one fixed SFTP source expression for this array's four archives and four sidecars, requires exactly those eight filenames and each recorded hash, then performs structural verification, provisional validation-only comparison and automatic independent local CPU audit. The auditor is `{AUDIT/'audit_batch.py'}`. It rescored no newly returned data yet; results have not been downloaded. Three audit contracts and the status-regex recovery test passed; all five helpers still parse under PowerShell5.1. The added progress print is cosmetic.

Retrieval needs the user's direct KIT OTP/password. After results arrive, continue independently: replay validation ranking/guards and every saved prediction, verify frozen/inactive tensors in best/last against selected7805570step100, rescore any regression predictions, then explain why candidate checkpoints were rejected. Known references remain consumed; regression cannot reselect a checkpoint/variant. Local diagnostics, reporting, exports, CPU parity, reversible integration and packaging remain authorized without routine permission. Pause before any new cluster scope. Keep all failed/rejected evidence and older files intact.

Existing strict ONNX numerical hold and stable app default are unchanged; explicit preview is not production promotion. Standing communication/local-autonomy/efficient-batching preferences apply to future chats and handoffs.

Next step: run Retrieve-Results.ps1, because model conclusions require independently checked returned artifacts rather than successful process status.
''')
paths=[BATCH/'Check-Run.ps1',BATCH/'Retrieve-Results.ps1',BATCH/'run-receipt.json',AUDIT/'audit_batch.py',BATCH/'CURRENT_STATE_COMPLETED_7809335.json',BATCH/'COMPLETED_HANDOFF_7809335.md',HERE/'Test-Status-Repair.ps1']
save(HERE/'LOCAL_HELPER_REVISION_RECEIPT.json',dict(status='four-hashes-recovered-parser-repair-tested-retrieval-and-local-audit-ready',PS51_syntax_passed=True,PS51_production_regex_test_passed=True,hash_recovery_cross_checked_against_user_paste=True,core_package_changed=False,network_contacted=False,new_cluster_jobs=0,files={str(p):sha(p) for p in paths}))
save(HERE/'files-sha256.json',dict(files={p.name:sha(p) for p in HERE.iterdir() if p.is_file()}))
print(json.dumps(dict(status=state['status'],actual_job_id='7809335',archives_ready=4,new_jobs=0,retrieval_and_CPU_audit_ready=True),indent=2))
