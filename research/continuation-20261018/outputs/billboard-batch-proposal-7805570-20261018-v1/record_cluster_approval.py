"""Record the user's exact four-trial approval; preserve proposal snapshots."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,value):
    with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
identity=read(HERE/'PROPOSAL_IDENTITY.json');tools=HERE/identity['package_directory']
protocol=read(tools/'protocol.json')
assert sha(tools/'protocol.json')==identity['protocol_sha256']=='0a255598b74eb1d29d83ee1be10d517ae407fbda2c57e4565b51028d615343fd'
assert sha(HERE/'protocol.json')==identity['protocol_sha256']
for rel,digest in read(tools/'package-files.json')['files'].items():assert sha(tools/rel)==digest,rel
for rel,digest in read(HERE/'files-sha256-final.json')['files'].items():assert sha(HERE/rel)==digest,rel
approval=dict(approved=True,protocol_sha256=identity['protocol_sha256'],scope=protocol['scope'],active_classifier_rows=[133],user_authorization_evidence='User in this FrameTrail chat: "All right, I approve the four trial batch to proceed to the next stage with all the previous instructions."',recorded_at_UTC='2026-10-18T15:50:35Z',approved_batch=dict(array='0-3%2',tasks=4,maximum_concurrent_GPUs=2,per_task=dict(GPUs=1,partition='gpu_a100_il',CPU_cores=2,host_memory_GiB=8,maximum_updates=3000,maximum_training_process_seconds=1800,maximum_known_regression_seconds=480,Slurm_wall_minutes=45),maximum_requested_GPU_hours=3,automatic_retries=0),standing_instructions='Carry forward all latest user-provided AGENTS.md communication, local autonomy and efficient batching instructions. Local audit/export/parity/reversible integration/packaging are authorized. This record authorizes the reviewed batch only; it does not authorize replacement jobs, scope expansion, changed labels/data/thresholds or production adoption.',approved_for_application=False)
path=tools/'approval.json'
if path.exists():
    if read(path)!=approval:raise ValueError('Existing approval differs; preserve it without overwrite')
else:save(path,approval)
receipt=dict(status='exact-four-trial-cluster-scope-approved-local-package-preparation-authorized',approval_path=str(path),approval_sha256=sha(path),protocol_sha256=identity['protocol_sha256'],proposal_sha256=sha(HERE/'PROPOSAL.md'),package_seal_sha256=sha(tools/'package-files.json'),proposal_snapshots_preserved=True,cluster_submitted=False,SSH_contacted=False,credentials_required='User must enter KIT OTP/password directly in terminal prompts; never paste them into chat.')
save(HERE/'APPROVAL_RECEIPT.json',receipt)
print(json.dumps(receipt,indent=2))
