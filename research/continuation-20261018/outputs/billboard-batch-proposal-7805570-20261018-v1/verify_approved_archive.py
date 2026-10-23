"""Independently read the approved transport archive and write a current handoff."""
import hashlib,json,tarfile
from pathlib import Path,PurePosixPath
HERE=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as f:f.write(v if isinstance(v,str) else json.dumps(v,indent=2)+'\n')
identity=read(HERE/'PROPOSAL_IDENTITY.json');T=HERE/identity['package_directory'];receipt=read(HERE/'archive-receipt.json')
archive=HERE/receipt['archive'];assert sha(archive)==receipt['archive_sha256']
expected=dict(read(T/'package-files.json')['files']);expected.update({'package-files.json':sha(T/'package-files.json'),'approval.json':sha(T/'approval.json')})
seen=set()
with tarfile.open(archive,'r:gz') as tar:
    for member in tar:
        path=PurePosixPath(member.name)
        assert member.isfile() and len(path.parts)>1 and path.parts[0]==T.name and '..' not in path.parts
        relative='/'.join(path.parts[1:]);assert relative in expected and relative not in seen
        with tar.extractfile(member) as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==expected[relative],relative
        seen.add(relative)
assert seen==set(expected)
bootstrap=(HERE/'bootstrap-approved.sh').read_text(encoding='utf-8-sig')
assert '@@' not in bootstrap and T.name in bootstrap and receipt['archive_sha256'] in bootstrap and receipt['package_seal_sha256'] in bootstrap
approval=read(T/'approval.json');assert approval['approved'] is True and sha(T/'approval.json')==receipt['approval_sha256']
state=dict(status='four-trial-batch-approved-packaged-and-content-verified-awaiting-direct-KIT-authentication',protocol_sha256=identity['protocol_sha256'],approval_sha256=receipt['approval_sha256'],archive_sha256=receipt['archive_sha256'],archive=str(archive),archive_bytes=archive.stat().st_size,verified_archive_files=len(seen),batch='one Slurm array 0-3%2; four trials, at most two concurrent A100s, up to 3000 updates and45 minutes/task; aggregate requested limit3 GPU-hours; no retries',approval_recorded=True,archive_verified=True,SSH_contacted=False,cluster_submitted=False,real_job_id=None,live_account_limits_verified=False,credentials='Enter KIT OTP/password directly in terminal prompts; do not paste credentials into chat.',launch_command='powershell -NoProfile -ExecutionPolicy Bypass -File "'+str(HERE/'Launch-Approved-Run.ps1')+'"',next_action='User runs the approved launch command with direct KIT authentication. Launcher checks runtime/assets and scheduler admission before one real array submission; preserve any ambiguous response and use Check-Run.ps1.',supersedes_draft_status_files=['PROPOSAL_IDENTITY.json approval status snapshot','PREPARATION_RECEIPT.json','CONTINUATION_STATE.json','HANDOFF.md'],standing_instructions='Latest user AGENTS.md communication/local autonomy/efficient batching instructions all retained. Authorization is for this exact reviewed four-trial batch only. Independent CPU rescore/tensor audits after retrieval remain required and locally authorized. Numerical ONNX hold remains in force; no production adoption.')
save(HERE/'CURRENT_STATE_APPROVED.json',state)
save(HERE/'APPROVED_HANDOFF.md',f'''# Current approved FrameTrail batch

This handoff supersedes the unapproved draft status in HANDOFF.md, CONTINUATION_STATE.json and preparation/proposal snapshots. Those files are historical and intentionally preserved. The user explicitly approved the exact four-trial batch: "All right, I approve the four trial batch to proceed to the next stage with all the previous instructions."

Approval is recorded separately in `{T/'approval.json'}` and APPROVAL_RECEIPT.json. Protocol SHA-256: `{identity['protocol_sha256']}`. Core data/code and proposal scope are unchanged.

Approved scope: one four-task Slurm array 0-3%2, regular gpu_a100_il. Each task: one A100, two CPUs,8GiB host memory,45minutes wall,<=3000updates,<=1800seconds training process and<=480seconds known-regression processing. Maximum two concurrent A100s and three aggregate requested GPU-hours. No retries, requeue or replacement jobs. Matrix is1:1 versus1:3 positive/explicit-negative photos at learning rates.0001 and.0003. Start job7805570 selectedstep100; update only billboard row133, freeze all other model parameters. Same sealed data, thresholds, guards and validation-only selection.

The package `{archive.name}` is ready: {archive.stat().st_size}bytes, SHA-256`{receipt['archive_sha256']}`. Independent archive reading verified all {len(seen)} member identities and hashes against the core seal plus separate approval; there are no extra members. Bootstrap has the exact archive and seal hashes with all placeholders resolved. All earlier12CPU/structural and6mock-Slurm checks remain applicable. No real GPU inference or model training was performed locally.

No SSH connection, upload or new submission has occurred. Real array ID is unknown. Direct KIT OTP/password authentication is the remaining human input. The launcher runs scheduler/account queries and sbatch --test-only before the single real submission. If rejected, stop and inspect the recorded evidence. If response is ambiguous, preserve launch-output.txt and use Check-Run.ps1; never automatically re-run submission or create a replacement. Scheduler limits remain unverified until authenticated checks run.

Launch command:

```powershell
{state['launch_command']}
```

After submission, Check-Run.ps1 records actual root array ID and four task archive checksums. Retrieve-Results.ps1 retrieves/verifies all four in one invocation. Continue the independent validation rescoring, selection replay and frozen/inactive tensor audit locally before accepting a provisional winner. Known regression outcomes must not reselect a checkpoint/variant; old references are consumed, not fresh independent tests. Local audit/export/parity/reversible integration/packaging require no routine approval. Preserve all older data/models/receipts/builds and failed task evidence.

Existing selected model remains job7805570step100 (washing3/15, billboard0/19 known targets). Existing strict ONNX numerical hold is unchanged; native preview is explicit, standard default YOLOX-S preserved, production_adoption=false. Training is not a fix for runtime numerical qualification.

Next step: run the approved launcher and enter KIT authentication directly, because the approved package is sealed and submission now needs authenticated access.
''')
files=['approval.json']
new_files=['APPROVAL_RECEIPT.json','archive-receipt.json','bootstrap-approved.sh','CURRENT_STATE_APPROVED.json','APPROVED_HANDOFF.md','record_cluster_approval.py','verify_approved_archive.py']
save(HERE/'approved-stage-sha256.json',dict(protocol_sha256=identity['protocol_sha256'],core_package_seal_sha256=sha(T/'package-files.json'),approval_sha256=sha(T/'approval.json'),archive_sha256=receipt['archive_sha256'],files={name:sha(HERE/name) for name in new_files}))
print(json.dumps(state,indent=2))
