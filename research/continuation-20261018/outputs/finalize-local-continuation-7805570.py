"""Write additive local reports and a handoff; never contacts KIT or changes model bytes."""
import ast, hashlib, json, statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NATIVE = ROOT/'native-balanced-7805570-20261018-v1'
NUM = ROOT/'export-numerics-7805570-20261018-v1'
REVIEW = ROOT/'billboard-training-review-7805570-20261018-v1'
PROPOSAL = ROOT/'billboard-only-proposal-7805570-20261018-v1'
HANDOFF = ROOT/'local-continuation-handoff-7805570-20261018-v1'

def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    with p.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
def write(p, value):
    with p.open('x',encoding='utf-8',newline='\n') as f:
        f.write(json.dumps(value,indent=2)+'\n' if not isinstance(value,str) else value)

# The unapproved draft was corrected before any archive or approval existed.
tools=PROPOSAL/read(PROPOSAL/'PROPOSAL_IDENTITY.json')['package_directory']
assert not (tools/'approval.json').exists()
assert not (PROPOSAL/'archive-receipt.json').exists()
seal=read(tools/'package-files.json')
for name in ('run-balanced.sbatch','train_balanced.py'):
    seal['files'][name]=sha(tools/name)
(tools/'package-files.json').write_text(json.dumps(seal,indent=2)+'\n',encoding='utf-8',newline='\n')
for name,digest in seal['files'].items(): assert sha(tools/name)==digest,name
python_sources=[*tools.glob('*.py'),PROPOSAL/'prepare_archive.py',PROPOSAL/'verify_results.py',PROPOSAL/'test_verifier.py']
for p in python_sources: ast.parse(p.read_text(encoding='utf-8-sig'),filename=str(p))
assert 'rf-billboard-ddbb57c6' not in (tools/'run-balanced.sbatch').read_text()
assert tools.name in (tools/'run-balanced.sbatch').read_text()
assert (PROPOSAL/'batch-entry-fixture/entry-calls.txt').read_text().splitlines()==['verify_package.py','train_balanced.py','bundle_results.py']

native=read(NATIVE/'FINAL_RECEIPT.json')
assert native['strict_numerical_export_gate_passed'] is False
assert native['production_adoption'] is False
write(NATIVE/'REPORT.md', '''# FrameTrail local studio preview

The refreshed native app is packaged in `app`. `Run-FrameTrail.cmd` opens the existing YOLOX-S default; `Run-Balanced-Preview.cmd` explicitly selects the job-7805570 step-100 candidate. Both launchers are alongside this report. Older builds and model files are preserved. Source and build are isolated in this output folder.

The candidate found 3/15 known washing-machine targets on the frozen photo reference, compared with 0/15 for either baseline. Billboard remained 0/19. The six scoped references retained all measured per-class retention counts. These small assistant-reviewed references do not establish broad accuracy.

The original strict numerical export gate remains failed. Counts, classes and scoped scores agree across 202 unique images, but three images exceed the 0.002 confidence-difference bound, with maximum 0.004229903 (0.423 percentage points). Three of six raw-query-array probes also fail their numerical check. The new model is an explicit local preview, not a production promotion or fully parity-certified export. No tolerance or detection threshold was relaxed.

Validation: thirteen existing native regression checks passed, six native decoded parity probes passed, and the offscreen preview/analyse/save/CSV/reopen flow passed. Packaged standard and experimental launches exited successfully offscreen; the old RF profile correctly rejected the new model metadata. No visible app was launched. An initial intake test scratch-permission failure passed on recheck with task-owned writable temporary storage.

CPU inference median was approximately 612 ms/frame on six probes. The smooth-playback cache test prepared 120 frames in 133.705 seconds and passed exact overlay, pause and replay-without-model checks. Its synthetic two-second replay timing is not a general real-time inference claim.

Inspect FINAL_RECEIPT.json, NATIVE_PARITY.json, PACKAGED_SMOKE.json and evidence for details.

Next step: approve the separately prepared bounded billboard-only GPU trial, because billboard remains undetected while the selected washing-machine gain can be frozen.
''')

semantic=read(NUM/'SEMANTIC_PARITY.json')
assert semantic['all_metrics_and_frame_counts_identical'] and not semantic['strict_export_gate_passed']
write(NUM/'REPORT.md', '''# Export numerical investigation

The original export stays held. On 202 unique images across six references, the ONNX model preserves decoded counts/classes and all measured scoped scores. Three confidence comparisons exceed the original 0.002 tolerance; the maximum difference is 0.004229903. Three of six raw-array probes also fail. Metrics agreement does not waive the numerical failures.

The fixed nine-probe diagnostic found decoded PyTorch results unchanged by the stock export preparation. ORT optimization settings and selected fusion changes moved individual numerical failures without producing a uniform fix. A regular-forward legacy export hit unsupported antialiased bicubic interpolation. Caching the fixed input positional table enabled a regular export, but the three decoded confidence cases persisted. A newer Dynamo/opset-18 export also preserved those failures.

The newer export helpers were installed only into this output's isolated exporter-overlay; the pinned training environment was not upgraded. Installation provenance is recorded in exporter-overlay-install.json. Alternate ONNX files are diagnostic outputs and are not packaged as app defaults.

No model weights, thresholds or original gate results were changed. The explicit native preview carries the numerical limitation; production_adoption remains false. The training proposal is a separate accuracy experiment and cannot resolve this engineering hold.

Inspect DIAGNOSIS.json, FUSION_DIAGNOSIS.json, REGULAR_POSITIONS_DIAGNOSIS.json, DYNAMO_POSITIONS_DIAGNOSIS.json and SEMANTIC_PARITY.json for reproducible observations.

Next step: retain this numerical hold during the proposed billboard trial, so any model gain remains separate from runtime qualification.
''')

review=read(REVIEW/'REVIEW.json')
assert review['optimizer_updates']==0 and review['all_weights_unchanged'] and not review['heldout_or_validation_used']
medians={}
for ck in ('selected-100','rejected-last-2000'):
    medians[ck]={role:statistics.median(r['max_billboard_probability'] for r in review['records'] if r['checkpoint']==ck and r['role']==role) for role in ('positive','explicit-negative')}
write(REVIEW/'SUMMARY.json',dict(status=review['status'],medians=medians,training_photos=8,forward_backward_checks=16,optimizer_updates=0,weights_unchanged=True,validation_or_heldout_used=False))
write(REVIEW/'REPORT.md', '''# Billboard training-only review

Eight fixed training photos (four positive, four explicitly absent) were inspected at the selected step-100 and rejected step-2000 states. Sixteen CPU forward/backward checks used no optimizer and made no parameter updates. Input hashes and complete model-state fingerprints stayed unchanged. Validation and held-out images were not used in this diagnostic.

At step 100, median maximum billboard probability was 0.0730 on positives and 0.0447 on explicit negatives. At the rejected step 2000 it was 0.5717 and 0.1009 respectively. Three of four positive photos had queries covering their known targets at IoU >= 0.5. The remaining photo's two targets had no covering queries, which a frozen-box experiment cannot repair. Explicit negative images generated suppressive gradients on the permitted billboard row.

This supports a bounded calibration hypothesis: try a higher explicit-negative share while training only billboard and freezing washing machine. It does not guarantee improvement or causally isolate sampling from budget changes. Step 2000 remains rejected and cannot replace the selected model.

The draft proposal uses one positive plus three distinct explicit negatives per update, drawn from the existing 20-positive/35-negative training pools. It retains both current and original validation guards. No new labels, data or thresholds are proposed.

Next step: approve the bounded single-row GPU proposal, because this small diagnostic identifies a plausible learning signal while explaining its limitations.
''')

write(PROPOSAL/'PREPARATION_RECEIPT.json',dict(status='prepared-awaiting-exact-human-cluster-approval',protocol_sha256=read(PROPOSAL/'PROPOSAL_IDENTITY.json')['protocol_sha256'],package_seal_sha256=sha(tools/'package-files.json'),sealed_files=len(seal['files']),all_sealed_files_match=True,python_AST_files=len(python_sources),contract_tests_passed=5,result_verifier_tests_passed=6,mock_submission_cases_passed=3,inert_batch_entry_passed=True,powershell_51_syntax_passed=True,missing_approval_blocks_before_archive_and_SSH=True,stale_batch_path_corrected_before_submission=True,known_references_are_not_fresh_heldout=True,approval_present=False,archive_created=False,SSH_contacted=False,new_GPU_jobs=0))

HANDOFF.mkdir(exist_ok=False)
state=dict(status='local-work-complete-awaiting-cluster-scope-approval',actual_completed_jobs=['7780632','7805570'],selected_job='7805570',selected_step=100,checkpoint_sha256=native['checkpoint_sha256'],ONNX_sha256=native['ONNX_sha256'],heldout_known_targets=dict(washing_machine='3/15 vs 0/15 for both baselines',billboard='0/19'),references_consumed=True,strict_export_gate_passed=False,production_adoption=False,explicit_local_preview_available=True,default_model='YOLOX-S',default_model_changed=False,new_cluster_job_approved=False,new_cluster_job_submitted=False,proposal_protocol_sha256=read(PROPOSAL/'PROPOSAL_IDENTITY.json')['protocol_sha256'],next_action='Obtain human approval for exactly one A100 billboard-only trial: <=3000 updates, <=1800s active, 45min wall, no retries; then record approval and prepare the sealed archive. KIT authentication must be entered directly by the user.',artifacts=dict(native=str(NATIVE),numerics=str(NUM),training_review=str(REVIEW),proposal=str(PROPOSAL),heldout=str(ROOT/'heldout-evaluation-7805570-20261018-v1')),standing_preferences=['End every user-facing response with the single best concrete next step and why.','Continue authorized local exports, tests, integration, packaging and fixes autonomously.','Pause before a NEW cluster job with its exact scope; unavailable credentials or restricted consequential actions can also require input.','Older assistant automatic_export flags are superseded as local approval barriers; preserve their historical bytes.','No visible desktop/app control or visible launches.','Preserve old data, labels, builds, checkpoints and receipts; do not touch MiniERP/Carrington.'])
write(HANDOFF/'CONTINUATION_STATE.json',state)
write(HANDOFF/'HANDOFF.md',f'''# FrameTrail continuation handoff

Local work is complete through the explicit native preview and the sealed billboard-only cluster proposal. **No new job is approved or submitted.** The user's latest Continue authorized finishing local preparation; exact GPU scope must be approved before submission. Their communication and local-autonomy instructions are persisted in global, FrameTrail and Codex AGENTS.md files.

Selected state: job 7805570 step 100, checkpoint `{native['checkpoint_sha256']}`. The later step-2000 state remains rejected. Job 7780632 originally retained step zero. Frozen evaluation found washing machine 3/15 versus 0/15 for both baselines, billboard 0/19, and retained all scoped per-class guards. All 202 unique images were scored for each of three frozen models. These references are now consumed regression evidence, not a fresh test for the next experiment.

The native studio preview is `{NATIVE}`. Standard launcher retains YOLOX-S; experimental launcher selects the new RF profile. Thirteen existing regression checks, six native parity probes, packaged offscreen smokes, saved-run/CSV round trip and 120-frame cache checks passed. No visible UI was opened. Main source and older model files remain preserved; new source/build/app are isolated.

Strict numerical ONNX qualification remains FAILED: three confidence cases exceed 0.002 (max 0.004229903), and three raw-array probes fail. All decoded counts/classes and scoped scores agree on the 202 images, but this is not numerical certification. Several export/runtime paths were investigated without a uniform fix. Preview is reversible and explicit; production_adoption=false. Preserve gate failures and original tolerances.

Prepared proposal: `{PROPOSAL}`. One A100 / two CPUs, <=3000 updates / 12000 presentations, <=30 minutes active / 45 minutes Slurm wall, no retries. Start selected step 100; train only billboard classifier row 133. Freeze every other row, features and boxes. Per update: one existing positive and three distinct explicitly absent training photos. No labels, thresholds, vocabulary or new data. Validate every 100; stop at 1500 if no eligible strict gain, otherwise max3000. Guard every reviewed class against both baselines. Known references remain regression evidence; further independent frozen evidence is required for a new generalization claim.

A final check corrected a stale batch folder before approval/submission. All 2921 sealed files match. Five CPU contracts, six structural verifier tests, three fake-Slurm cases, inert batch entry execution, Bash syntax and PowerShell 5.1 parsing passed. Mock job 123456789 is a fixture, never a real KIT job. Actual approval.json and archive remain absent. Launch helper stops before archive creation or SSH without exact approval. After approval record it separately, run prepare_archive.py, and let the user enter KIT OTP/password directly for the one submission. Do not auto-resubmit ambiguous output.

Protocol contains historical automatic_export=false text; this is not a request to pause routine local work. Latest user instructions supersede assistant-imposed approval boundaries. New cluster submissions still require explicit approval. Continue future authorized local evaluation/export/packaging without routine confirmation.

Next step: obtain approval for that one bounded GPU trial, because billboard remains 0/19 and this scope protects the selected washing-machine gain.
''')

# Seal durable code, reports and receipts. Omit SDK/runtime caches, build outputs and
# isolated helper dependencies; native/model identities are pinned in FINAL_RECEIPT.
for folder in (NATIVE,NUM,REVIEW,PROPOSAL,HANDOFF):
    files={}
    for p in sorted(folder.rglob('*')):
        if not p.is_file() or p.is_symlink(): continue
        rel=p.relative_to(folder)
        if any(part in ('build','exporter-overlay','runtime-temp','submission-fixtures','batch-entry-fixture') for part in rel.parts): continue
        if rel.parts[0]==tools.name: continue # independently sealed and verified above
        if p.name=='files-sha256-final.json': continue
        if folder==NATIVE and rel.parts[0]=='app': continue
        files[rel.as_posix()]=sha(p)
    write(folder/'files-sha256-final.json',dict(schema=1,files=files))
print(json.dumps(dict(status=state['status'],handoff=str(HANDOFF),package_sealed_files=len(seal['files']),new_GPU_jobs=0),indent=2))
