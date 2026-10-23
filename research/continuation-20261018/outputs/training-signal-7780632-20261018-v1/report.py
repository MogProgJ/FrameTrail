"""Summarize the read-only diagnostic and freeze a non-approved next-run proposal."""
import collections,hashlib,json,random,statistics
from pathlib import Path
P=Path(__file__).resolve().parent
OLD=Path(r'C:\Users\nazee\.codex\visualizations\2026\10\15\01a141ae-c7a6-7303-a280-403af88736f3')
RELEASE=OLD/'nextdata-reviewed-release-7769109-v1'
T=OLD/'nextdata-rf-trial-7769109-v1/rf-nextdata-tools-v1'
BASE=Path(r'C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\outputs')
RUN=BASE/'trial-results-7780632-20261018-v1/retrieval/verified-7780632/output/rf-nextdata-7780632'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(name,data):(P/name).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
d=read(P/'DIAGNOSTIC.json');assert d['checkpoint_photo_checks']==24 and d['optimizer_updates']==0 and not d['weights_changed']
names={15:'Cat',16:'Dog',133:'Billboard',593:'Washing machine'};summary=[];table=[]
for cid in names:
    stages=[]
    for step in [0,600]:
        positives=[r for r in d['records'] if r['step']==step and any(x['canonical_id']==cid and x['role']=='positive' for x in r['selection_roles'])]
        negatives=[r for r in d['records'] if r['step']==step and any(x['canonical_id']==cid and x['role']=='explicit-negative' for x in r['selection_roles'])]
        matches=[m for r in positives for m in r['stages'][0]['matches'] if m['canonical_id']==cid]
        assert len(positives)==len(negatives)==2
        assert all(r['stages'][0]['classes'][str(cid)]['unmatched_negative_logit_gradient_sum']>0 for r in negatives)
        stages.append(dict(step=step,positive_photos=2,explicit_negative_photos=2,matched_targets=len(matches),
            median_matched_iou=statistics.median(m['iou'] for m in matches),median_matched_probability=statistics.median(m['probability'] for m in matches),
            median_soft_target=statistics.median(m['soft_target'] for m in matches),matched_logits_with_upward_descent_direction=sum(m['descent_would_raise_matched_logit'] for m in matches),
            mean_full_head_row_weight_gradient_norm_on_positive_photos=statistics.mean(r['head_gradients'][str(cid)]['weight_l2'] for r in positives),
            median_matched_weighted_logit_gradient=statistics.median(m['actual_weighted_logit_gradient'] for m in matches),
            explicit_negatives_suppress_class=True))
    summary.append(dict(canonical_id=cid,name=names[cid],steps=stages))
    a,b=stages;table.append(f"| {names[cid]} | {a['matched_targets']} | {a['median_matched_probability']:.1%} → {b['median_matched_probability']:.1%} | {b['median_soft_target']:.1%} | {b['matched_logits_with_upward_descent_direction']} / {b['matched_targets']} |")
constant_share={str(step):statistics.mean(r['constant_weighted_loss']/r['weighted_total'] for r in d['records'] if r['step']==step) for step in [0,600]}
save('SUMMARY.json',dict(status='complete',classes=summary,mean_constant_loss_fraction=constant_share,
    inactive_row_gradient_mask_passed=True,unknown_logit_gradient_mask_passed=True,explicit_negative_suppression_passed=True,
    classification_gradient_reconstruction_passed=True,optimizer_updates=0,
    limits='Two positive photos per class and selected explicit negatives. This diagnoses signal direction, not convergence, generalization, optimal learning rate or sufficient training duration.'))

manifest_path=RELEASE/'candidate-manifest-v2.json';manifest=read(manifest_path);train={r['image_id']:r for r in manifest['images'] if r['split']=='train'}
pools=dict(billboard=sorted(r['image_id'] for r in train.values() if any(t['canonical_id']==133 for t in r['targets'])),
    washing_machine=sorted(r['image_id'] for r in train.values() if any(t['canonical_id']==593 for t in r['targets'])),
    explicit_negative_for_both=sorted(r['image_id'] for r in train.values() if all(r['scope'].get(str(c))=='absent' for c in [133,593]) and not any(t['canonical_id'] in [133,593] for t in r['targets'])))
assert len(pools['billboard'])==20 and len(pools['washing_machine'])==21 and len(pools['explicit_negative_for_both'])>0
assert not set(pools['explicit_negative_for_both'])&(set(pools['billboard'])|set(pools['washing_machine']))
save('proposed-sampling-pools.json',pools)
def stream(ids,n,seed):
    rng=random.Random(seed);result=[]
    while len(result)<n:
        cycle=list(ids);rng.shuffle(cycle);result.extend(cycle)
    return result[:n]
bill=stream(pools['billboard'],2000,171019);wash=stream(pools['washing_machine'],2000,171020);negative=stream(pools['explicit_negative_for_both'],4000,171021)
schedule=[[bill[i],wash[i],negative[2*i],negative[2*i+1]] for i in range(2000)]
assert all(len(batch)==4 and set(batch)<=set(train) for batch in schedule)
save('proposed-sampling-plan.json',schedule)
old_protocol=read(T/'protocol.json')
proposal=dict(schema=1,status='proposal-only-awaiting-separate-GPU-scope-approval',experiment_approved=False,
    previous_job='7780632',candidate_sha256=sha(manifest_path),starting_checkpoint=dict(source='retrieved job 7780632 last.pt, old step 600',sha256=sha(RUN/'last.pt'),old_step=600,new_run_step_zero_is_this_checkpoint=True,optimizer_state='fresh AdamW; no optimizer state was saved in the old checkpoint'),
    active_classifier_rows=[133,593],active_categories=['billboard','washing machine'],all_other_classifier_rows='frozen and bitwise checked, including cat and dog',
    frozen_components=['feature extractor','transformer encoder','encoder classifier','decoder features','all box regressors','all other parameters and buffers'],
    data=dict(candidate_photos=965,train_partition=700,validation_partition=135,test_partition_reserved=130,
        billboard_positive_pool=20,washing_machine_positive_pool=21,explicit_negative_for_both_pool=len(pools['explicit_negative_for_both']),
        pools_sha256=sha(P/'proposed-sampling-pools.json'),schedule_sha256=sha(P/'proposed-sampling-plan.json'),no_labels_or_scopes_changed=True),
    training=dict(optimizer='AdamW',lr=.0001,weight_decay=0,maximum_updates=2000,accumulation=4,maximum_presentations=8000,
        per_update='one billboard-positive + one washing-machine-positive + two photos explicitly absent for both categories; preserve all targets/scopes on each photo',
        sampling_seeds=[171019,171020,171021],model_seed=17,AMP=False,gradient_clip=.1,model_mode='eval with only two final classifier rows trainable',
        validation_steps=list(range(0,2001,100)),early_stop='At update 1000, stop if no eligible strict improvement over new-run step 0 has been selected. Otherwise continue to maximum 2000 updates.',
        active_run_elapsed_seconds_cap=1800,Slurm_wall_minutes_cap=45,GPUs=1,partition='gpu_a100_il',cpus=2,
        automatic_retries=0,new_model_downloads=0,validation_margin='Stop before the elapsed cap with sufficient margin for receipt/checkpoint finalization; a partial run is not a completed fixed-budget trial.'),
    selection=old_protocol['selection'],evaluation=old_protocol['evaluation'],
    extra_guard='Reference new-run step 0 and original job 7780632 step 0. The original per-class counts are identical at old steps 0 and 600; verify this preflight. Never relax the original retention guard.',
    strict_gain_definition='An eligible checkpoint must increase the original lexicographic validation ranking. Ties retain new-run step 0. No claim of useful gain from confidence shifts alone.',
    limits=['This tests a continuation with balanced exposure and more updates, not a causal ablation of every change.','Selected negatives are explicitly absent for both categories; unknown images are never relabeled negative.','Small assistant-reviewed dataset and repeated exposure can overfit; no general accuracy claim.','Read-only diagnostic gradients cannot establish the best learning rate or required update count.'],
    automatic_export=False,automatic_application_adoption=False,heldout_before_frozen_improved_candidate=False,
    approval_required_reason='The recorded approval authorized exactly one four-row 600-update GPU trial. That trial is complete; this proposed two-row continuation is a separate scope and job.',
    execution_package_status='Not created or submitted. These files freeze the reviewable proposed scope and sampler; an implementation must pass its contracts before manual remote submission.')
save('proposed-protocol.json',proposal)
proposal_sha=sha(P/'proposed-protocol.json')
save('PROPOSAL_IDENTITY.json',dict(status='not-approved',protocol_sha256=proposal_sha,pools_sha256=sha(P/'proposed-sampling-pools.json'),schedule_sha256=sha(P/'proposed-sampling-plan.json')))
proposal_md=f'''# Proposed next run: balanced two-class head continuation

**Proposal only; not approved, implemented as a training runner, or submitted.**

Continue from job 7780632's final checkpoint (old step 600), not its selected step-0 checkpoint and not the app's installed weights. Use a fresh AdamW optimizer because the old checkpoint contains no optimizer state. Only the final **billboard and washing-machine classifier rows** may change. Cat/dog rows, every other row, encoder classifier, features and all box heads stay frozen and bitwise checked.

- **Maximum:** 2,000 updates, accumulation 4, 8,000 image presentations; stop at update 1,000 if no eligible strict validation gain has been selected.
- **Learning rate:** unchanged at 0.0001; AdamW, zero decay, gradient clip 0.1, no AMP. This proposal does not simultaneously raise the learning rate or replace the loss.
- **Sampling:** each update has one photo from the 20 known-positive billboard training photos, one from the 21 washing-machine training photos, and two from the **{len(pools['explicit_negative_for_both'])} training photos explicitly reviewed absent for both**. Preserve every existing target and scope. Frozen sampler seeds and the exact 2,000-update schedule are included.
- **Resources:** one A100 GPU, two CPU cores; at most 30 minutes of active-run elapsed time and a 45-minute Slurm allocation; no retries or downloads.
- **Checks:** validate at step 0 and every 100 updates. Keep confidence .35, NMS .45, matching IoU .5, top 300 pairs and maximum 100 detections. Retain all 72 reviewed classes' no-regression guards and the unscored-prediction drift alarm. Check against both the continuation baseline and the original trial baseline. Exact ties keep the earlier checkpoint.
- **Reserved evidence:** freeze/hash a strict improving candidate before using the existing 130 held-out photos and 24 reserved video frames. Export and app adoption remain separate gates; neither is automatic.

Why this is the narrowest supported next experiment: usable boxes already exist, both new classes retain upward classification gradients, and the original mixed sampler gave them only 217 and 226 positive-photo presentations. The proposal concentrates positive exposure while keeping the architecture, loss, learning rate and detection thresholds unchanged. Improvement is uncertain; the schedule repeats a small training set and can overfit. This is an optimization attempt, not a promise that more updates will solve recognition.

The protocol identity is `{proposal_sha}`. `proposed-sampling-pools.json` and `proposed-sampling-plan.json` are hash-pinned in the protocol. A separately authorized implementation must verify the starting checkpoint hash and every sampler ID/asset before execution.

Separate GPU approval is required because `approval.json` for the completed run authorized exactly one four-classifier-row, 600-update trial and explicitly disabled automatic retries and application adoption. The new proposal changes the trainable rows, starting checkpoint, sampler and update budget. The current instruction authorized a read-only loss/gradient check and preparation of a proposal; it did not approve this new GPU job.
'''
(P/'PROPOSAL.md').write_text(proposal_md,encoding='utf-8')
report=f'''# Training signal check after job 7780632

The classification signal is present. This read-only CPU check used the **12 previously frozen training photos** at steps 0 and 600: 24 model/criterion/backward checks and **zero optimizer updates**. It found no disconnected new-class gradient or violation of the scoped masks in these samples. All parameter/buffer fingerprints and source-file hashes are unchanged.

## Matched positive targets

| Class | Matched targets in two positive photos | Median matched confidence, step 0 → 600 | Median IoU-aware soft target at step 600 | Matched logits whose gradient would raise confidence at step 600 |
|---|---:|---:|---:|---:|
{chr(10).join(table)}

All **4 sampled billboard matches** and **2 sampled washing-machine matches** still have an upward classification signal at step 600. Their mean full classifier-row weight-gradient norms on positive photos are about 18.0 and 24.8 respectively; neither is zero. This is evidence of remaining optimization pressure in these samples, not a forecast of validation improvement. Per-logit descent does not guarantee a shared classifier-row update improves every other query.

The IoU-aware soft target depends on both current confidence and matched-box overlap. The sampled billboard median soft target rises from 24.2% to 33.7%; washing-machine soft target rises from 35.3% to 68.9%. A soft target below 35% at one instant is not a fixed ceiling: it is recomputed as confidence changes. The matched washing-machine IoU changes slightly because Hungarian assignment selects different queries; the box weights did not change.

## Scope, suppression and loss accounting

- Explicit-negative samples produce gradients that suppress the corresponding class. Unknown/unreviewed logits have zero direct gradient, and unmatched logits in positive-only scopes have zero direct gradient.
- All inactive classifier rows have exactly zero masked parameter gradient. No feature, encoder or box parameter receives a gradient. Only the previously approved four final classifier rows were enabled for inspection.
- Gradients from final and auxiliary decoder classification losses reconstruct the actual head gradient. The encoder classification and all box losses are constant with respect to the trainable head.
- On this deliberately small diagnostic set, those frozen loss components account for about **{constant_share['0']:.1%}** of total weighted loss at step 0 and **{constant_share['600']:.1%}** at step 600. Therefore a modest change in the total loss is not a direct measure of how much the new classifier learned.
- Normalization is by the total number of reviewed targets in the photo, clamped to at least one, including targets whose classifier rows are frozen. That can dilute active-class contributions in crowded images; this check does not establish that normalization is a bug or justify replacing it.

The completed sampler already showed 217 billboard-positive and 226 washing-machine-positive photo presentations, drawn from 20 and 21 distinct training photos. All those positives were sampled. They were not omitted, but mixed-class sampling gave each new class less exposure than a class-balanced continuation would.

## Decision supported by the evidence

Together with the earlier validation probe—all 24 new-class targets have a distinct sufficiently overlapping decoder query—this supports testing **more focused classifier optimization before unfreezing features or box heads**. It does not establish the optimal learning rate or enough training duration. A small training-only check cannot demonstrate generalization.

`PROPOSAL.md` and `proposed-protocol.json` specify one bounded two-row continuation: unchanged 0.0001 learning rate, balanced new-class exposure, maximum 2,000 updates, early stop if no eligible gain by 1,000, one A100, maximum 30 active minutes / 45 allocation minutes. Everything except the two new final classifier rows stays frozen. The same validation retention guards and untouched held-out gate apply.

This next GPU run is **not approved or submitted**. Existing approval covered the completed one-off 600-update trial. No training runner, remote action, export or app adoption was created by this diagnostic.

## Evidence and limits

`DIAGNOSTIC.json` and the 24 per-photo records contain each loss component, every active matched target's query/IoU/confidence/soft target/logit gradient, per-row and per-stage gradient norms, and whole-model before/after fingerprints. `INPUT_INTEGRITY.json` pins the original inputs. `SUMMARY.json` contains these aggregates. `proposed-sampling-plan.json` is an unexecuted schedule, not a record of training.

The sample contains only two positive photos per class and the fixed selected explicit negatives, with no independent annotation recheck. No validation or held-out photo was loaded for this training-signal check, no optimizer was instantiated, and no model weights were written. The proposal references the prior validation conclusion but does not run a new validation experiment. The app, annotation scopes, vocabulary, cohorts and previous packages remain unchanged.
'''
(P/'REPORT.md').write_text(report,encoding='utf-8')
save('VALIDATION_RECEIPT.json',dict(status='pass',training_photos=12,checkpoint_photo_backward_checks=24,
    positive_role_checks=16,explicit_negative_role_checks=16,scoped_mask_checks_passed=True,head_gradient_reconstruction_passed=True,
    model_state_fingerprints_unchanged=True,original_input_hashes_unchanged=True,optimizer_instantiated=False,optimizer_updates=0,
    validation_inference=False,heldout_used=False,proposal_sampler_partition_checks_passed=True,proposed_update_count=2000,new_training_submitted=False))
save('CONTINUATION_STATE.json',dict(project='FrameTrail',status='training-only-gradient-diagnostic-complete-proposal-awaiting-scope-approval',job='7780632',
    finding='New-class classifier gradients are connected and still push matched positive logits upward on the fixed training-only diagnostic. All usable validation box geometry was already present.',
    proposed_next_job=dict(trainable_rows=[133,593],maximum_updates=2000,early_stop_if_no_gain_at=1000,learning_rate=.0001,GPUs=1,active_elapsed_minutes_cap=30,Slurm_minutes_cap=45,approved=False,submitted=False,protocol_sha256=proposal_sha),
    next_best_step='Review and separately approve the bounded two-class head-only continuation before implementing/verifying the remote training package or submitting a GPU job.',
    optimizer_updates_in_this_diagnostic=0,heldout_used=False,app_adoption=False,
    standing_communication_preference='End every user-facing response with the single best plausible concrete FrameTrail next step and briefly why. Carry this preference into every handoff.'))
print(json.dumps(dict(status='reports-and-unapproved-proposal-prepared',summary=summary,constant_loss_fractions=constant_share,negative_pool=len(pools['explicit_negative_for_both']),proposal_sha256=proposal_sha),indent=2))
