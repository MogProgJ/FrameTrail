"""Additive draft receipt/handoff. Does not create approval, archive or SSH session."""
import ast,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def put(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as f:f.write(v if isinstance(v,str) else json.dumps(v,indent=2)+'\n')
identity=read(HERE/'PROPOSAL_IDENTITY.json');T=HERE/identity['package_directory']
assert not (T/'approval.json').exists() and not (HERE/'archive-receipt.json').exists()
seal=read(T/'package-files.json')
for rel,h in seal['files'].items():assert sha(T/rel)==h,rel
sources=[*T.glob('*.py'),*HERE.glob('*.py')]
for p in sources:ast.parse(p.read_text(encoding='utf-8-sig'),filename=str(p))
assert 'Ran 10 tests' in (HERE/'contract-tests.txt').read_text(encoding='utf-8-sig')
assert 'Ran 2 tests' in (HERE/'archive-verifier-tests.txt').read_text(encoding='utf-8-sig')
for f in ('contract-tests.txt','archive-verifier-tests.txt'):assert '\nOK' in (HERE/f).read_text(encoding='utf-8-sig')
fixture=HERE/'slurm-mock-fixtures'
for case in ('preflight-fails','test-only-reject'):assert not (fixture/case/'sbatch-calls.txt').exists()
for case in ('normal','ambiguous'):assert (fixture/case/'sbatch-calls.txt').read_text().splitlines()==['called']
for case,expected in [('normal',['verify_package.py','train_balanced.py','regression_stage.py','bundle_results.py']),('training-failure',['verify_package.py','train_balanced.py','bundle_results.py'])]:assert (fixture/'batch-entry'/(case+'-calls.txt')).read_text().splitlines()==expected
assert read(HERE/'powershell-syntax.txt')['status']=='Windows-PowerShell-5.1-syntax-passed'
assert 'Explicit approval' in (HERE/'missing-approval-guard.txt').read_text(encoding='utf-8-sig')
p=read(T/'protocol.json')
put(HERE/'PREPARATION_RECEIPT.json',dict(status='four-trial-batch-prepared-awaiting-exact-human-approval',protocol_sha256=identity['protocol_sha256'],package_seal_sha256=sha(T/'package-files.json'),sealed_files=len(seal['files']),all_seals_match=True,Python_AST_files=len(sources),CPU_and_structural_tests_passed=12,local_mock_submission_and_batch_cases_passed=6,powershell_51_syntax_passed=True,missing_approval_blocks_before_archive_and_SSH=True,approval_present=False,archive_created=False,SSH_contacted=False,new_cluster_submissions=0,real_model_training_updates=0,local_GPU_inference=False,trials=p['variants'],maximum_concurrent_GPUs=2,maximum_requested_GPU_hours=3,live_account_limits_verified=False,limit_check='Authenticated scheduler/account queries plus sbatch --test-only run before the approved real submission; do not equate public partition maxima with account entitlement.',old_single_trial_proposal='Preserved, superseded for proposed scope only',automatic_known_regression=dict(reference_sets=6,unique_images=202,selection_uses_regression=False),production_adoption=False))
put(HERE/'CONTINUATION_STATE.json',dict(status='awaiting-four-trial-cluster-scope-approval',latest_proposal=str(HERE/'PROPOSAL.md'),protocol_sha256=identity['protocol_sha256'],selected_existing_model=dict(job='7805570',step=100,checkpoint_sha256=p['starting_checkpoint']['sha256'],known_washing_machine='3/15',known_billboard='0/19'),strict_ONNX_export_gate_passed=False,native_preview_available=True,default_model='YOLOX-S',batch=dict(tasks=4,array='0-3%2',per_task=dict(GPUs=1,CPU_cores=2,host_memory_GiB=8,Slurm_wall_minutes=45,training_process_seconds=1800,postprocess_seconds=480,maximum_updates=3000),total_requested_GPU_hours=3,maximum_concurrent_GPUs=2,retries=0),approval_recorded=False,upload_done=False,cluster_submitted=False,next_action='Obtain explicit approval for this full scope; then create the separate exact approval record, prepare the sealed archive and provide the launch command for direct KIT authentication.',standing_preferences=['End each user-facing response with the best concrete next project step and why.','Continue local exports, audits, parity, benchmarks, reversible integration, packaging and fixes autonomously.','Batch useful independent experiments and automatic checks before each cluster submission approval/authentication cycle.','Explain matrix, dependencies, aggregate budget and account evidence.','Never maximize arbitrary job count or treat public partition maxima as account entitlement.','Pause before a new cluster submission with exact scope; no retries/replacements without a new decision.','Keep references frozen, validation-only selection, all older data/models/builds/receipts and failed-task evidence.'],audit_followup='After retrieval, independently replay all validation-selection metrics and compare inactive/frozen tensors against the starting checkpoint before accepting the provisional winner. Local work is authorized. Regression reports cannot reselect a winner; any retention failure holds it. Known references are consumed, not fresh tests.'))
put(HERE/'HANDOFF.md',f'''# FrameTrail: efficient batch replaces single-trial proposal

Latest user instruction: prepare useful independent trials and automatic checks together before each cluster submission. This preference is saved in global, FrameTrail, Codex and continuation AGENTS.md files and explicitly confirmed in the latest user-provided AGENTS.md.

The unsubmitted single-trial draft is preserved. The new latest proposal is `{HERE/'PROPOSAL.md'}`. No approval, upload or new job exists. Exact scope: one four-task array `0-3%2`, one A100/two CPUs/8 GiB/45 minutes per task, maximum two concurrent A100s, three aggregate requested GPU-hours. Each task has <=3000 updates, <=30 minutes training-process time and <=8 minutes automatic consumed-reference processing. No retries or replacements.

Matrix: positive:explicit-negative ratios 1:1 and 1:3, each at learning rates .0001 and .0003. Paired image schedules and one common input package. All start selected job7805570 step100; train only classifier row133. Everything else, including washing-machine gain, is frozen. Validate every100; stop at1500 if no eligible gain. Preserve guards against current and original baselines. All four selected checkpoints freeze before known regression; zero-gain tasks reuse current baseline scores. One Check and one Retrieve cover all four tasks and preserve failures.

Twelve CPU/structural tests and six local fake-Slurm/entry tests passed; five PowerShell5.1 helper syntax checks passed; all {len(seal['files'])} sealed files match. Tests used inert fixtures and synthetic optimizer heads, not real model training or GPU inference. Mock job123456789 is never a real KIT job. Actual approval.json is absent and launch blocks before packaging/SSH.

Account maximums are NOT yet verified. Authenticated launch records scheduler/account evidence and executes sbatch --test-only before the single real sbatch. Stop if rejected; do not automatically change scope or submit replacements. The requested two-GPU concurrency is a cap, not a guarantee of simultaneous scheduling or a claim to account entitlement.

Existing model evidence: selected step100 improved known washing-machine targets0/15 to3/15, billboard0/19. Strict numerical ONNX gate remains FAILED (three confidence cases above.002, three raw-array probes fail), though202-image scoped results match. Explicit native preview remains available in the sibling native-balanced folder; standard default YOLOX-S is unchanged. No production promotion. GPU training is separate from fixing numerical export qualification.

After retrieval the built-in validation-only comparison is provisional. Independently rescore validation predictions, replay selection against both baselines, inspect frozen/inactive tensors for best and last checkpoints, and independently replay known-regression reports locally before accepting any winner. Do not choose a different variant based on consumed regression. Any failure holds adoption; no automatic new job. Local audit/export/parity/integration are already authorized. Additional independent frozen evidence is required for a new generalization claim.

Next step: approve the complete four-trial scope, because it collects a controlled calibration comparison and regression evidence in one cluster submission.
''')
files={p.relative_to(HERE).as_posix():sha(p) for p in sorted(HERE.rglob('*')) if p.is_file() and identity['package_directory'] not in p.relative_to(HERE).parts and 'slurm-mock-fixtures' not in p.relative_to(HERE).parts}
put(HERE/'files-sha256-final.json',dict(schema=1,files=files,core_package_seal_sha256=sha(T/'package-files.json')))
print(json.dumps(dict(status='ready-for-four-trial-scope-review',sealed_files=len(seal['files']),new_jobs=0,proposal=str(HERE/'PROPOSAL.md')),indent=2))
