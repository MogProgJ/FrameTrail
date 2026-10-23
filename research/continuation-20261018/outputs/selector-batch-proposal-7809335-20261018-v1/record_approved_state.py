"""Record the approved, content-verified package; no network or submission."""
import hashlib,json,shutil
from pathlib import Path
P=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as f:f.write(v if isinstance(v,str) else json.dumps(v,indent=2)+'\n')
identity=read(P/'PROPOSAL_IDENTITY.json');T=P/identity['package_directory'];receipt=read(P/'archive-receipt.json');approval=read(T/'approval.json')
assert approval['approved'] is True and approval['protocol_sha256']==identity['protocol_sha256']==receipt['protocol_sha256']
assert sha(T/'approval.json')==receipt['approval_sha256'] and sha(T/'package-files.json')==receipt['package_seal_sha256']
archive=P/receipt['archive'];assert sha(archive)==receipt['archive_sha256']
bootstrap=(P/'bootstrap-approved.sh').read_text(encoding='utf-8-sig')
assert '@@' not in bootstrap and receipt['archive_sha256'] in bootstrap and receipt['package_seal_sha256'] in bootstrap and T.name in bootstrap
assert not (P/'run-receipt.json').exists() and not (T/'submitted-job-id.txt').exists()
command='powershell -NoProfile -ExecutionPolicy Bypass -File "'+str(P/'Launch-Approved-Run.ps1')+'"'
state=dict(status='selector-four-trial-batch-approved-packaged-content-verified-awaiting-direct-KIT-authentication',protocol_sha256=identity['protocol_sha256'],approval_sha256=receipt['approval_sha256'],archive_sha256=receipt['archive_sha256'],archive=str(archive),archive_bytes=archive.stat().st_size,verified_archive_files=len(read(T/'package-files.json')['files'])+2,batch=dict(tasks=4,array='0-3%2',maximum_concurrent_GPUs=2,maximum_requested_GPU_hours=3,per_task=dict(GPUs=1,CPU_cores=2,host_memory_GiB=8,maximum_updates=3000,Slurm_wall_minutes=45,training_process_seconds=1800,known_regression_seconds=480),automatic_retries=0),approval_recorded=True,archive_verified=True,SSH_contacted=False,cluster_submitted=False,real_array_job_id=None,live_account_limits_verified=False,launch_command=command,current_model_job='7805570',current_model_step=100,strict_ONNX_hold=True,production_adoption=False,standing_preference='Continue bounded FrameTrail project work without routine approval prompts. Latest user supersedes the older mandatory cluster-approval pause. Preserve resource limits, exact scope/provenance, scheduler checks, batching, model/data gates and no retries/replacements. Ask only when human input is truly required; direct KIT authentication is currently required. End responses with a concrete next step and why.',supersedes=['unapproved status snapshots in protocol/proposal/preparation/identity files','previous CURRENT_HANDOFF approval-needed statement','older standing requirement to pause solely for new cluster approval'],credentials='User enters KIT OTP/password directly into their own terminal prompts; never into chat.')
save(P/'CURRENT_STATE_APPROVED.json',state)
save(P/'APPROVAL_RECEIPT.json',dict(status='exact-selector-scope-approved',authorization_source=str(P/'USER_AUTHORIZATION.json'),authorization_source_sha256=sha(P/'USER_AUTHORIZATION.json'),verbatim_user_authorization=approval['user_authorization_evidence'],approval_sha256=receipt['approval_sha256'],protocol_sha256=identity['protocol_sha256'],core_package_seal_sha256=receipt['package_seal_sha256'],cluster_submitted=False,continuous_work_instruction_saved=True))
text=f'''# Current FrameTrail state: selector batch approved and ready

The user approved the exact four-trial selector batch and removed routine approval checkpoints for bounded FrameTrail continuation. Their exact authorization is preserved in USER_AUTHORIZATION.json and the separate approval.json/APPROVAL_RECEIPT.json. Superseding continuous-work instructions were saved in global, FrameTrail, Codex and continuation AGENTS.md files. Earlier protocol/proposal status flags are preserved historical snapshots; this handoff and CURRENT_STATE_APPROVED.json supersede their unapproved status.

Protocol: {identity['protocol_sha256']}. Package: {archive.name}; {archive.stat().st_size} bytes; SHA-256 {receipt['archive_sha256']}. Every archived regular member was read back and hash-verified against the unchanged core seal plus the separate approval ({state['verified_archive_files']} files). Bootstrap placeholders are resolved with the exact archive and seal hashes. Twelve contracts, six inert Slurm mocks, PowerShell helper parsing and a real four-photo CPU update passed before approval; approved code/assets/scope verification also passed.

One upload and one array 0-3%2: encoder billboard learning rates 0.00001/0.00003 crossed with reviewed sign-region penalties 1/3; final billboard learning rate 0.0001. Train only row 133 in the main and encoder proposal classifiers, with dense encoder classification and eight separate TRAIN sign-region overlays. Other parameters, buffers and rows stay bitwise frozen. Proposal changes may affect boxes and other detections; both-baseline per-class retention and aggregate unscored guards remain mandatory. Preserve validation-only selection and automatic frozen-candidate known regression; known references are consumed, not fresh test evidence.

Each task: one A100 on gpu_a100_il, two CPUs, 8 GiB, maximum 3,000 updates, 1,800 seconds training process, 480 seconds known regression, 45 minutes Slurm wall time. Stop at 1,500 without eligible gain. Maximum two GPUs concurrently and three aggregate requested GPU-hours. No retries/requeue/replacements. Account entitlements are unverified until the authenticated launch records scheduler/account evidence and passes sbatch --test-only.

No SSH, upload or cluster submission has occurred. Actual array ID is unknown. Direct KIT OTP/password authentication is the remaining human input. Run:

```powershell
{command}
```

If submission output is ambiguous or fails, preserve launch-output.txt and run Check-Run.ps1; never automatically resubmit. After all four tasks are terminal, Retrieve-Results.ps1 downloads all eight batch files in one SFTP connection, then verifies/extracts safely, compares validation-selected states and performs the independent CPU rescore/selection/tensor audit. Preserve partial/failed evidence.

Current model remains job 7805570 step 100 (known washing machine 3/15, billboard 0/19). Strict ONNX numerical qualification remains held, native preview is explicit, standard YOLOX-S default remains, production adoption is false. Completed array 7809335, 17 local evaluated heads and two 1,500-update controls produced no eligible strict gain. Do not edit MiniERP or Carrington or launch a visible GUI without request.

Continue authorized local and bounded cluster work autonomously under the latest standing instruction. A real credential requirement or consequential unresolved change may need the human. Never request pasted credentials. End each response with the best concrete next project step and why.

Next step: run the approved launcher and enter KIT authentication directly, because the package is ready and authenticated submission is the only remaining blocker.
'''
save(P/'APPROVED_HANDOFF.md',text)
root=P.parents[1];previous=root/'CURRENT_HANDOFF.md'
shutil.copy2(previous,P/'HANDOFF_BEFORE_APPROVAL.md')
previous.write_text(text+'\nFull receipts: '+str(P)+'\n',encoding='utf-8',newline='\n')
save(P.parent/'LATEST_FRAMETRAIL_STATE_SELECTOR_APPROVED.json',state)
names=['USER_AUTHORIZATION.json','APPROVAL_RECEIPT.json','archive-receipt.json','bootstrap-approved.sh','CURRENT_STATE_APPROVED.json','APPROVED_HANDOFF.md','record_approved_state.py','update_standing_preference.py']
save(P/'approved-stage-sha256.json',dict(protocol_sha256=identity['protocol_sha256'],approval_sha256=receipt['approval_sha256'],archive_sha256=receipt['archive_sha256'],files={n:sha(P/n) for n in names}))
print(json.dumps(state,indent=2))
