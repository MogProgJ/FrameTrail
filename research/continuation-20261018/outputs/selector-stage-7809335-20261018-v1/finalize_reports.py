"""Audit CPU controls, seal proposal and write an updated durable project handoff."""
import hashlib,json,shutil,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;OUT=HERE.parent;P=OUT/'selector-batch-proposal-7809335-20261018-v1';F=OUT/'frozen-head-cpu-7809335-20261018-v1';OLD=OUT/'billboard-batch-proposal-7805570-20261018-v1'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,v):
    with p.open('x',encoding='utf-8',newline='\n') as f:f.write(v if isinstance(v,str) else json.dumps(v,indent=2,allow_nan=False)+'\n')
def main():
    identity=read(P/'PROPOSAL_IDENTITY.json');T=P/identity['package_directory'];sys.path.insert(0,str(T))
    from continuation_guard import counts_equal
    from selection_policy import evaluate,eligible,ranking
    controls=read(HERE/'CPU_CONTROLS_RECEIPT.json');rows=[r for r in read(T/'release/candidate-manifest-v2.json')['images'] if r['split']=='val'];original=read(T/'inputs/validation-original.json');resume=read(T/'inputs/validation-resume.json');audits=[]
    schedule=read(HERE/'CPU_CONTROL_SCHEDULE.json');assert schedule==read(T/'schedules/task-0.json')[:1500]
    for control in controls['controls']:
        assert control['status']=='complete' and control['updates']==1500
        folder=HERE/f"CPU-control-region{int(control['region_weight'])}";best=resume;best_step=0
        for step in range(0,1501,100):
            item=read(folder/f'validation-{step:04}.json');rescored=evaluate(rows,item['predictions'])
            assert rescored['metrics']==item['metrics'] and rescored['per_class']==item['per_class']
            ok=eligible(item,resume) and eligible(item,original);assert item['eligible']==ok
            if step==0:assert counts_equal(item,resume)
            if ok and ranking(item)>ranking(best) and ranking(item)>ranking(original):best=item;best_step=step
        for step in range(1,1501):assert read(folder/f'step-{step:04}.json')['train_ids']==schedule[step-1]
        assert best_step==control['selected_step'];audits.append(dict(region_weight=control['region_weight'],validations_rescored=16,updates_trace_checked=1500,selected_step=best_step,strict_gain=best_step>0))
    assert not any(r['strict_gain'] for r in audits),'Local qualifying candidate needs full evaluation before proposing more GPU work'
    save(HERE/'CPU_CONTROLS_AUDIT.json',dict(status='two-controls-independently-rescored-and-selection-replayed',controls=audits,new_GPU_jobs=0))
    for name in ('CPU_CONTROLS_RECEIPT.json','CPU_CONTROLS_AUDIT.json'):
        shutil.copy2(HERE/name,T/'local-evidence'/name)
    probe_paths=[F/'LOCAL_PROBE_RECEIPT.json',F/'reviewed-contrast/RECEIPT.json',F/'teacher-preservation/RECEIPT.json',F/'rms-constrained/RECEIPT.json']
    probes=[]
    for path in probe_paths:
        r=read(path);trials=r.get('trials',[r]);assert not any(t['strict_gain'] for t in trials);probes.extend(trials)
    assert len(probes)==17
    real=read(P/'REAL_CPU_UPDATE.json');assert real['only_two_billboard_rows_changed'] and real['source_checkpoint_unchanged'] and real['post_update_forward_finite']
    audit=read(OLD/'retrieval-7809335/independent-audit/AUDIT.json');assert audit['validation_only_winner_index'] is None and len(audit['tasks'])==4
    coverage=read(F/'PROPOSAL_COVERAGE.json');assert (coverage['all_encoder_covered'],coverage['selected_encoder_covered'],coverage['final_decoder_covered'])==(52,36,37)
    controls_table='\n'.join(f"| {c['region_weight']:g} | {c['updates']} | {c['trace'][-1]['billboard_known_hits']}/11 | {c['trace'][-1]['billboard_complete_fp']} | {c['trace'][-1]['unscored']} | step {c['selected_step']} |" for c in controls['controls'])
    report=f'''# FrameTrail audited result and next experiment

Array7809335 is complete, downloaded and independently audited. All four tasks stopped at1500updates under the approved no-gain rule. All selected step0, whose model tensors equal job7805570step100. No returned model was adopted. Replayed64validation records and checked all best/last model tensors, schedules and selection decisions. The four tasks used43min31s aggregate allocation time (about0.725GPUhours), below the3GPUhour requested ceiling.

The main-head trials learned billboard detections (maximum training-run validation hits7,5,9,7 of11), but each improving checkpoint failed existing guards. Unknown-region predictions are unscored predictions, not measured false positives. The tight aggregate cap is530 because the original baseline525+5 is stricter than the current baseline528+5. Measured false positives also included regulatory signs.

Seventeen additional local heads tested uniform/hard-negative weighting, eight reviewed sign regions, teacher preservation on645otherwise-unknown TRAIN photos and a training-only RMS constraint. None passed strict-gain selection. All used exact cached frozen features or training-only sufficient statistics; no extra cluster jobs. This is development exploration, not fresh independent accuracy evidence.

Two matching frozen-selector controls were then run locally for1500updates each (one positive, two explicit negatives and one reviewed sign-region photo per update). Their32validation records and3000update traces were independently checked:

| Sign penalty | Updates | Final billboard hits | Measured complete FP | Final unscored | Selected |
| --- | --- | --- | --- | --- | --- |
{controls_table}

Training-only geometry inspection finds encoder proposals covering52/54targets before top300selection,36/54after selection and37/54in final decoder boxes. This supports a proposal-selector experiment; it does not prove that selector training will improve accuracy. No fresh test images were used to choose this mechanism.

## Exact proposed cluster scope — NEW approval required

One upload/launch, one Slurm array0-3%2 on gpu_a100_il. Four trials: encoder billboard learning rate0.00001or0.00003 crossed with sign-region negative penalty1or3. Main billboard learning rate0.0001 throughout. Start the unchanged selected job7805570step100 checkpoint. Update only row133 in main and encoder proposal classifiers. All other rows, including washing machine, and all backbone/transformer/box-regressor parameters and buffers remain bitwise frozen. Changed proposal selection can change decoder features, box outputs and other detections.

Objective adds dense encoder billboard classification on the full proposal grid to the existing scoped main/aux/selected-encoder objective. Geometry Hungarian matches require IoU>=.5. The eight assistant-reviewed TRAIN sign panels supply billboard-negative queries at IoU>=.7 only within each panel; all outside scope remains unchanged. Original965photo release labels/scopes are preserved. No new downloads, test labels or whole-image absence claims. Same paired schedule: one positive +two distinct explicit negatives +one region photo each update (63distinct existing TRAIN photos).

Each task requests oneA100, twoCPUs,8GiB and45minutes wall time, bounded to3000updates,1800seconds training process and480seconds known regression. Stop at1500if no qualifying gain. Four tasks total<=12000updates,48000presentations, two concurrent GPUs and3aggregate requested GPUhours (2hours summed training process caps). No retries, requeue or replacement jobs. Failed/partial archives are retained.

Validation step0and every100 on the same135development photos. Same confidence.35/NMS.45/IoU.5 and both-baseline per-class retention/unscored+5 guard. Select by validation ranking only; earlier step/lower index wins ties. Score any frozen selected candidate automatically on202unique known-regression images/six references. Regression may veto adoption but never select a different trial. Step0 reuses current scores. Download all four tasks with one batch SFTP command, then structurally verify, independently rescore and audit both active rows/all frozen tensors locally.

Two cacheable controls have already run on CPU; the four new trials require fresh forward passes as encoder selection changes. Additional learning-rate/grid jobs would increase selection pressure before this mechanism shows a benefit. Account entitlements are not assumed: the approved launcher records authenticated scheduler/account evidence and requires sbatch --test-only before a single submission. No authenticated check has been performed for this NEW proposal yet.

Protocol SHA256: {identity['protocol_sha256']}. Code/asset seal is package-files.json. New approval is absent; no transport archive, SSH, upload or submission has occurred. Earlier four-trial authorization applied to completed array7809335 and does not authorize this changed mechanism/region overlay.

Existing model remains job7805570step100: known washing3/15 and billboard0/19. Strict ONNX numerical qualification remains held; the explicit native preview is available, default YOLOX-S preserved and production_adoption=false. Known references are consumed, and fresh independently frozen evidence is still needed for a generalization claim.

Standing instructions: recommend the concrete next step at the end of every response; continue all authorized local audits/exports/parity/CPU benchmarks/reversible integration/packaging/fixes autonomously; pause before NEW cluster scope submission; batch useful independent work and preserve failure evidence. Do not launch a visible GUI without request. Never ask for pasted credentials. Preserve earlier receipts.

Next step: obtain explicit approval for this exact four-trial selector batch, because preparation and local controls are complete and posting a new cluster job is the remaining user decision.
'''
    save(P/'PROPOSAL.md',report)
    save(OUT/'billboard-batch-diagnosis-7809335-20261018-v1/COMPLETED_LOCAL_RESEARCH.md',report)
    seal={'files':{p.relative_to(T).as_posix():sha(p) for p in sorted(T.rglob('*')) if p.is_file() and p.name!='package-files.json'}}
    (T/'package-files.json').write_text(json.dumps(seal,indent=2)+'\n',encoding='utf-8')
    save(P/'PREPARATION_RECEIPT.json',dict(status='exact-selector-batch-prepared-awaiting-new-cluster-approval',protocol_sha256=identity['protocol_sha256'],sealed_files=len(seal['files']),core_seal_sha256=sha(T/'package-files.json'),completed_prior_batch='7809335',prior_batch_audit_sha256=sha(OLD/'retrieval-7809335/independent-audit/AUDIT.json'),local_probe_heads=17,cached_CPU_controls=2,control_audit_sha256=sha(HERE/'CPU_CONTROLS_AUDIT.json'),real_CPU_update_sha256=sha(P/'REAL_CPU_UPDATE.json'),approval_present=False,cluster_submitted=False,SSH_contacted=False,live_account_limits_verified=False,production_adoption=False))
    save(P/'preparation-files.json',dict(files={p.name:sha(p) for p in sorted(P.iterdir()) if p.is_file() and p.name!='preparation-files.json'}))
    save(OUT/'LATEST_FRAMETRAIL_STATE_7809335.json',dict(status='retrieval-audited-local-research-complete-awaiting-new-selector-batch-approval',selected_model_job='7805570',selected_model_step=100,selected_checkpoint_sha256='c1e7b571476a9bdc02533359dfe3f599afab98822aa90df265e9068f43f46bd3',completed_array='7809335',new_candidate_from_array=False,local_heads_and_controls=19,next_proposal=str(P/'PROPOSAL.md'),next_protocol_sha256=identity['protocol_sha256'],new_cluster_approval=False,new_cluster_job_submitted=False,strict_ONNX_hold=True,production_adoption=False,standing_instructions='Continue authorized local work autonomously; end responses with concrete next step and why; pause before new cluster submission; batch useful evidence and preserve failures.'))
    print('Independent control audit, final proposal, seals and latest state saved. No approval or submission.')
if __name__=='__main__':main()
