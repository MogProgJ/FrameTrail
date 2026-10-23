"""Write evidence-linked conclusion and preserve superseded handoffs. No inference/fits."""
import json, hashlib
from pathlib import Path
ROOT = Path(r'C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation')
BATCH = ROOT / 'outputs/fresh-selector-batch-20261022-v1'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def new(p,text):
    with p.open('x',encoding='utf-8',newline='\n') as f:f.write(text)

def main():
    audit = read(BATCH/'postrun-audit-7870268-v1/INDEPENDENT_AUDIT.json')
    diagnosis = read(BATCH/'postrun-train-diagnosis-7870268-v1/REPORT.json')
    selection = read(BATCH/'retrieval/local-evaluation/GLOBAL_SELECTION.json')
    final = read(BATCH/'retrieval/local-evaluation/FINAL_REPORT.json')
    assert final['status']=='no-qualifying-method-keep-starting-model' and final['test_photos_used']==0
    assert audit['records_audited']==24 and diagnosis['test_photos_used']==0
    assert all(c['complete'] for c in selection['conditions']) and selection['winner'] is None
    lines = ['# FrameTrail paired comparison: completed, no qualifying model', '',
        '22 October 2026. The exact existing local follow-up completed successfully on verified array 7870268. All four scientific conditions are complete. Neither method qualifies in either seed. Keep the starting model; production adoption remains false.', '',
        'The two-head method learned to detect more billboards, but it also labeled other signs and rectangular objects as billboards. This problem appears on TRAIN as well as validation. The evidence supports changing the discrimination study, not extending this recipe or unfreezing box layers.', '',
        '## Validation at every frozen checkpoint', '',
        'Each cell is fresh billboard hits / false alarms on 32 validation photos with 14 targets. No thresholds or annotations changed.', '',
        '| Method / seed | 0 | 100 | 250 | 500 | 1000 | 1500 |',
        '| --- | --- | --- | --- | --- | --- | --- |']
    for method in ['M0','M1']:
        for seed in [17,29]:
            part=[r for r in audit['validation_rows'] if r['method']==method and r['seed']==seed]
            lines.append(f'| {method} / {seed} | '+' | '.join(f"{r['tp']} / {r['fp']}" for r in part)+' |')
    lines += ['', 'M0 updates only the main billboard classifier row. M1 updates the main and encoder proposal billboard rows. The starting model has zero hits and zero billboard false alarms on this fresh validation set.', '',
        'Every checkpoint that gained at least three fresh hits added false alarms. Each also added one billboard false alarm on the older reviewed set, failing retention against both baselines. At step1500, old unscored counts are M0 538/538 and M1 542/538, above the original fixed cap530. Unscored predictions are not automatically false positives. No other reviewed class metric triggered the per-class retention failures recorded here.', '',
        '## Fixed final TRAIN diagnosis', '',
        'These postrun diagnostics used only the 124 already-approved TRAIN photos, no optimization and no new validation/TEST predictions. They do not reopen checkpoint selection. Fresh positives have complete billboard annotations (38 targets); the 50 old positive targets remain partial-scope recall evidence.', '',
        '| State | Fresh TRAIN hits /38 | Fresh-positive false alarms | Fresh-absent false alarms | Old-absent false alarms | Fresh geometry coverage /38 | Old geometry coverage /50 |',
        '| --- | --- | --- | --- | --- | --- | --- |']
    detail_refs=[]
    for brief in diagnosis['summaries']:
        p=BATCH/f"postrun-train-diagnosis-7870268-v1/{brief['state']}.json";v=read(p)
        counts={pool:sum(r['geometry_covered'] for r in v['geometry'] if r['pool']==pool) for pool in ['fresh_positive','old_positive']}
        f=v['pools'];lines.append(f"| {brief['state']} | {f['fresh_positive']['complete_tp']} | {f['fresh_positive']['complete_fp']} | {f['fresh_absent']['complete_fp']} | {f['old_absent']['complete_fp']} | {counts['fresh_positive']} | {counts['old_positive']} |")
        detail_refs.append(dict(path=str(p),sha256=sha(p)))
    lines += ['', 'The M1 seeds provide usable boxes for38/38 and37/38 fresh TRAIN targets, yet miss8 and11 at the unchanged operating point and alarm on 13 and 12 fresh absent-photo objects. This is evidence of a discrimination/operating-point problem even on TRAIN; it does not prove whether loss weighting, frozen features or limited classifier capacity is the cause. There is no basis here for claiming box-regressor unfreezing is necessary.', '',
        '## Error inspection', '',
        'All three derived error sheets (23 distinct TRAIN photos with a final-state false alarm in at least one condition) were visually inspected. Clear confusions include road restriction/warning signs, a bus-stop board, whiteboard, framed pictures, shop identity signs and business lettering. Positive-photo errors include a transit display beside a real billboard, a subpanel instead of the whole board, and merging/splitting adjacent advertising panels. These are qualitative observations from derived overlays, not a new exhaustive original-image annotation audit.', '',
        'The recorded category near-target-IoU-below-0.5 means any positive target overlap below0.5; it does not alone establish a localization error. Source labels, scopes, split roles and hashes remain unchanged. No errors were relabeled after seeing predictions. The cohort remains assistant-reviewed private research, not independent human annotation.', '',
        '## Execution and limits', '',
        f"- M1 combined training plus validation: seed17 {selection['conditions'][2]['combined_training_validation_seconds']:.3f}s; seed29 {selection['conditions'][3]['combined_training_validation_seconds']:.3f}s, both below1800s.",
        '- All24 saved validation records, per-image count totals/F1, qualification decisions and6000 paired update-log entries were independently audited. This is a record/decision audit; fresh per-box predictions were not independently re-inferred.',
        '- Starting-state identity and inactive/frozen parameters passed the original pipeline and TRAIN diagnosis. Starting checkpoint SHA c1e7b571476a9bdc02533359dfe3f599afab98822aa90df265e9068f43f46bd3 remains unchanged.',
        '- No winner lock, fresh-TEST consumption lock, known-regression inference or fresh-TEST inference. TEST photos used0. No export, app changes, production adoption, new cluster jobs, retrieval, resealing, retraining, retries or replacements.',
        '- No access to Carrington Event or other projects. No MiniERP edits. No background process or automation remains after completion.',
        '- Schedule files were sealed after the baseline but before fits, as preserved in EXECUTION_ORDER_NOTE.json; do not describe the implementation as literally fully preregistered.', '',
        '## Next decision', '',
        'Close this four-condition experiment under its frozen failure rule. The best next separate study is TRAIN-only billboard-versus-sign discrimination: reuse existing frozen TRAIN features and compare a fixed linear control with a small nonlinear probe in scene/identity-disjoint TRAIN folds before any deployable architecture or GPU proposal. The prior small-data capacity test found no consistent nonlinear advantage, so a fresh-data repeat must be treated as a diagnostic question, not a justified new model already selected.', '',
        'No further fit is authorized by this result. The focused continuation explicitly prohibited retraining, and the frozen strategy says to stop this recipe when neither method qualifies. A separately agreed study scope is needed before new fits; keep the taxonomy, both baselines, unknown cap, TEST isolation and resource limits intact. See NEXT_STUDY_SCOPE.md for the concrete bounded proposal.', '',
        'Evidence: retrieval/local-evaluation/{FINAL_REPORT,GLOBAL_SELECTION}.json; postrun-audit-7870268-v1/INDEPENDENT_AUDIT.json; postrun-train-diagnosis-7870268-v1/{PLAN,REPORT}.json and review/REVIEW_QUEUE.json.', '']
    new(BATCH/'POSTRUN_REPORT.md','\n'.join(lines))
    proposal='''# Proposed separate TRAIN-only discrimination study

Status: prepared for a scope decision; no new fit, upload, job or model produced.

Why: both frozen methods failed all qualification rules despite fresh validation gains. The final two-head states still alarm on12–13 fresh TRAIN absent objects and miss8–11 fresh TRAIN targets with38/38 and37/38 usable geometry. The inspected mistakes include obvious traffic signs, whiteboards and framed pictures, so broadening billboard labels would not resolve the demonstrated confusion. Do not tune thresholds against the completed validation outcomes.

Recommended scope: a diagnostic comparison using only the124 existing TRAIN photos and pinned cached features. Four deterministic folds must keep each scene, linked author/identity and known merged scene entirely in one fold. Compare a linear query classifier with the existing32-unit nonlinear probe,160 fixed updates per fit, two CPU threads, eight fits total, no parameter sweep or deployed checkpoint. Exact balancing, optimizer settings, training-only normalization, cache identities, query assignments and fold feasibility must be frozen and checked before any fit. Reuse the prior capacity-diagnostic settings where compatible; record any necessary change. Known positives only; unmatched queries on partial old positives remain unknown. Negative queries may come only from reviewed complete/absent billboard scope.

This proposal is not runnable or sealed. Scene/identity group counts and feasible fold assignments must be verified; do not silently substitute random query folds. Cap total diagnostic CPU active time at1800seconds; preserve partial evidence without extending/retrying. No GPU or cluster cost. Do not use old/fresh validation or TEST images/features for fitting, early stopping, model choice or calibration. The existing fresh TEST remains untouched for a future single qualified locked winner.

Readouts: per-fold query ranking and a fixed training-fold operating criterion, held-fold positive recovery and absent-photo alarm counts, and variation across folds. These are TRAIN diagnostic results, not detector validation accuracy. No model release or architecture adoption follows automatically. A nonlinear probe must show a consistent improvement at a comparable false-alarm criterion before a separate deployment/adapter experiment is justified; otherwise study supervision/loss/representation rather than adding capacity by assumption.

Choice needed: proceed with this new TRAIN-only study, or close the RF fine-tuning line and redirect the next model work. This is a new scientific fit scope after the frozen four-trial stop rule, not a retry or extension of7870268. No scope decision has been inferred from the failed results.

Next step: resolve this separate TRAIN-only study scope, because the current experiment has no eligible model and further fits would exceed its frozen design.
'''
    new(BATCH/'NEXT_STUDY_SCOPE.md',proposal)
    receipt=dict(status='evaluation-audit-TRAIN-diagnosis-and-review-completed',job='7870268',winner=None,
                 test_photos_used=0,production_adoption=False,all_four_conditions_complete=True,
                 new_cluster_jobs=0,new_optimizer_updates=0,no_background_processes=True,
                 next_scope_decision='Separate TRAIN-only discrimination study proposed; no new fit started',
                 source_refs=detail_refs+[dict(path=str(BATCH/p),sha256=sha(BATCH/p)) for p in ['POSTRUN_REPORT.md','NEXT_STUDY_SCOPE.md','postrun-audit-7870268-v1/INDEPENDENT_AUDIT.json','retrieval/local-evaluation/GLOBAL_SELECTION.json','retrieval/local-evaluation/FINAL_REPORT.json','postrun-train-diagnosis-7870268-v1/REPORT.json']])
    new(BATCH/'COMPLETION_RECEIPT_7870268.json',json.dumps(receipt,indent=2)+'\n')
    handoff='''# FrameTrail7870268: evaluated, no qualifying model; separate study scope decision next

LATEST22October2026: the exact existing local_followup.py completed once on the previously verified retrieval. All four scientific conditions complete; no checkpoint in either method/seed qualifies; global winner=null. M1 seed17 final12TP8FP;seed29 final13TP7FP on freshVAL32photos/14targets. M0final11TP8FP/10TP8FP. At500 M1already3TP2FP/4TP1FP. Every gain>=3 adds freshFP and one old reviewed billboardFP; final unknown counts542/538 forM1,538/538 forM0 exceed cap530. No other reviewed class metric triggered recorded per-class failures. Unscored is not automaticallyFP. Keep starting model; production_adoption=false. No known-regression/TEST inference; TESTphotos0; no winner or TEST consumption lock.

M1 combinedtraining+validation1071.3753973479907s/1063.400694043019s below1800 each. Independent audit passed all24 saved records, count/F1 arithmetic, qualification, method eligibility, paired schedules and6000update logs. Audit is of records/decisions, not new fresh prediction inference. All117 local input checks and local starting-state/frozen fingerprint passed existing pipeline.

Additional fixed-final TRAIN-only diagnosis completed:124TRAINphotos,47positive/77absent,zerooptimizer/VAL/TESTprobes. M1freshgeometry38/38and37/38;freshTRAINdetections30/38and27/38;fresh-positiveFP4/7,fresh-absentFP13/12,old-absentFP8/6. Oldgeometry47/50bothseeds (partial-scope old targets). M0freshgeometry36/38;freshhits27/38both;fresh-absentFP12/8,old-absentFP7/7. All frozen state and source identities unchanged.23distinct TRAINerrorphotos generated into3sheets and visuallyinspected: roadsigns,whiteboards,framedpictures,businesslettering; also billboard-subpanel/merged-panel mistakes. This was derived-overlay inspection, not a new exhaustive original-image audit. No label/scope/split edits or post-baseline curation.

Primary conclusion: existing row-only recipe learned recall but cannot discriminate cleanly even onTRAIN. Stop this recipe under frozen strategy; do not extend updates, sweep thresholds, unfreeze box layers, rerun or substitute a winner. Prior nonlinear diagnostic had no consistent advantage, so adding capacity is not already justified. Concrete separate TRAIN-only discrimination proposal prepared in NEXT_STUDY_SCOPE.md; no new fit started. Human scope choice is needed before that new study because the focused request prohibited retraining and frozen strategy stops this four-condition family. Do not request routine approval for completed work, credentials or a cluster submission.

Evidence folder: C:/Users/nazee/Documents/Codex/2026-10-18/frametrail-continuation/outputs/fresh-selector-batch-20261022-v1. Read POSTRUN_REPORT.md, COMPLETION_RECEIPT_7870268.json, NEXT_STUDY_SCOPE.md, retrieval/local-evaluation/{FINAL_REPORT,GLOBAL_SELECTION}.json, postrun-audit-7870268-v1/INDEPENDENT_AUDIT.json, postrun-train-diagnosis-7870268-v1/{PLAN,REPORT}.json, review/REVIEW_QUEUE.json under that diagnosis. Consolelogs preserved. No process/session/automation running. Do not rerun local_followup.py: exclusive evaluation directory already consumed; preserve receipts/locks. Do not reretrieve/retrain/resubmit/reseal. Actual archives remain verified7870268_0/_1, unchanged.

Canonicalfolder above; savedproject points unrelatedMiniERP—nevereditMiniERP. App unchanged:YOLOX-Sdefault,RF7805570step100explicitpreview,ONNXhold,production_adoption=false. StartingcheckpointSHA c1e7b571476a9bdc02533359dfe3f599afab98822aa90df265e9068f43f46bd3 unchanged. NoFrameTrailSSHneeded in this evaluation; renewedkey-onlyaccess was verified in precedingchat. Never request pasted credentials. StrictlyignoreCarringtonEvent/allotherprojects'files/jobs/logs/results/environments/sessions; only receipt-verified FrameTrailjobIDs/paths permitted.

Read AGENTS.md and preserve latest continuous-work authorization, paired seeds/both baselines/cap530/budgets/model-invariance/validation-onlyselection/locked-winnerTESTveto/noautomaticretries. No newmodel/dataqualification gates waived. Explain ordinary language; every response ends with single concrete nextFrameTrailstep andwhy. Retain honestexecutionorder: schedulessealed afterbaseline beforefits; assistantrevieweddata not independenthumanannotation.

Next step: resolve the separate TRAIN-only discrimination study scope, because the completed paired experiment has no eligible model and a new fit would change its frozen design.
'''
    new(ROOT/'NEXT_CHAT_7870268_EVALUATED.md',handoff)
    for name in ['CURRENT_HANDOFF.md','NEXT_CHAT_7870268.md']:
        p=ROOT/name;old=p.read_text(encoding='utf-8-sig')
        prefix=handoff if name=='CURRENT_HANDOFF.md' else '# Superseded: local evaluation already completed\n\nRead NEXT_CHAT_7870268_EVALUATED.md and outputs/fresh-selector-batch-20261022-v1/POSTRUN_REPORT.md. Do not rerun the command below. All four conditions complete; no eligible model; TEST untouched. A separate TRAIN-only study scope decision is next.\n'
        p.write_text(prefix+'\n---\n\n# Preserved historical handoff\n\n'+old,encoding='utf-8')
    print(json.dumps(dict(status=receipt['status'],report=str(BATCH/'POSTRUN_REPORT.md'),proposal=str(BATCH/'NEXT_STUDY_SCOPE.md'),handoff=str(ROOT/'NEXT_CHAT_7870268_EVALUATED.md')),indent=2))

if __name__=='__main__':main()
