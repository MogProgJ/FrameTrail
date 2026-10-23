"""Summarize the completed read-only audit and existing prediction diagnostics."""
import hashlib,json,sys
from pathlib import Path
P=Path(__file__).resolve().parent
OLD=Path(r'C:\Users\nazee\.codex\visualizations\2026\10\15\01a141ae-c7a6-7303-a280-403af88736f3')
TOOLS=OLD/'nextdata-rf-trial-7769109-v1/rf-nextdata-tools-v1'
RUN=Path(r'C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\outputs\trial-results-7780632-20261018-v1/retrieval/verified-7780632/output/rf-nextdata-7780632')
sys.path.insert(0,str(TOOLS))
from scoped_metrics import iou
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(name,data):(P/name).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n',encoding='utf-8')
audit=read(P/'AUDIT.json'); manifest=read(OLD/'nextdata-reviewed-release-7769109-v1/candidate-manifest-v2.json')
predictions=read(RUN/'validation-0600.json')['predictions']; active={15,16,133,593}; misses=[]
for row in manifest['images']:
    if row['split']!='val':continue
    matched=set(); ps=predictions[row['image_id']]
    def box(t):
        cx,cy,w,h=t['normalized_cxcywh'];return [(cx-w/2)*row['width'],(cy-h/2)*row['height'],(cx+w/2)*row['width'],(cy+h/2)*row['height']]
    for p in sorted(ps,key=lambda x:-x['confidence']):
        overlap,index=max(((iou(p['box'],box(t)),i) for i,t in enumerate(row['targets']) if i not in matched and p['canonical_id']==t['canonical_id']),default=(0,-1))
        if overlap>=.5:matched.add(index)
    for i,t in enumerate(row['targets']):
        if i in matched or t['canonical_id'] not in active:continue
        nearest=max(ps,key=lambda p:iou(p['box'],box(t)),default=None)
        same=[p for p in ps if p['canonical_id']==t['canonical_id']]
        misses.append(dict(image_id=row['image_id'],photo_number=row.get('photo_number'),canonical_id=t['canonical_id'],scope=row['scope'][str(t['canonical_id'])],target_xyxy=box(t),source_path=row['source_path'],
            emitted_same_class_count=len(same),best_same_class_iou=max((iou(p['box'],box(t)) for p in same),default=0),
            nearest_emitted_prediction=nearest,nearest_emitted_iou=iou(nearest['box'],box(t)) if nearest else 0))
assert len(misses)==28
save('validation-misses.json',dict(step=600,misses=misses,limits='Existing post-threshold predictions only. No inference or annotation changes; overlaps are diagnostic, not a revised score.'))
table='\n'.join(f"| {x['name'].title()} | {x['complete_tp']} / {x['complete_tp']+x['complete_fn']} | {x['partial_hits']} / {x['partial_hits']+x['partial_misses']} | {x['complete_fp']} |" for x in audit['active_class_summary'].values())
steps='\n'.join(f"| {v['step']} | {v['metrics']['complete_tp']} | {v['metrics']['complete_fp']} | {v['metrics']['complete_fn']} | {v['metrics']['partial_hits']} | {v['metrics']['partial_misses']} | {v['metrics']['unscored_predictions']} | {'yes' if v['eligible'] else 'no'} |" for v in audit['validation'])
report=f'''# Trial 7780632: completed, no improved checkpoint

The retrieved run completed 600 updates, but every validation checkpoint tied the starting model on the frozen selection ranking. The correct selected checkpoint is **step 0**. There is no trained candidate to export or adopt from this run.

## Validation result

All seven checkpoints have 22 complete true positives, 4 complete false positives, 36 complete misses, and 97 hits / 232 known partial targets. Complete F1 is 0.5238095; complete recall is 22/58 (37.93%). These are scoped development results across reviewed classes, not application accuracy or full-vocabulary mAP.

For the four trainable classes, the following counts are unchanged from step 0 to step 600:

| Class | Complete hits / targets | Partial hits / known targets | Complete false positives |
|---|---:|---:|---:|
{table}

Billboard and washing-machine rows have **zero known-target hits**. Their targets are partially annotated; zero complete targets or false positives does not establish perfect precision or absence of false positives. Cat's small reviewed subset has no remaining known misses; that is not a general accuracy claim.

| Step | Complete TP | FP | FN | Partial hits | Partial misses | Unscored predictions | Eligible |
|---|---:|---:|---:|---:|---:|---:|---|
{steps}

The selection ranking is `(119 reviewed positive hits, 0.5238095 complete F1)` at every checkpoint. Exact ties retain the earlier checkpoint under the frozen protocol. Unknown predictions are unscored, not false positives.

## What was independently verified

- Archive SHA-256 matches the pinned retrieval value: `{audit['archive_sha256']}`.
- Candidate, protocol and approval identities match the preflight receipt.
- All 600 numbered update records match the reproduced seeded schedule: 2,400 presentations from 158 distinct training photos (111 positive-pool photos and 47 negative-pool photos). No validation or test IDs appear in the schedule.
- All seven saved prediction sets reproduce their aggregate and all 72 per-class metric records using the frozen scorer. Eligibility and selection were recomputed.
- `best.pt` is byte-identical to `checkpoints/step-0000.pt`, with hash `3a9adf74b11b851fba7393cc41b12b538a7aa1576b0a4e179468cc36c2279389`.
- CPU tensor comparisons of step 0 and step 600 show changes only in `class_embed.weight` and `class_embed.bias`, and only in rows 15, 16, 133 and 593. All other parameters, buffers and classifier rows are exactly equal.
- The four trainable rows changed, so this was not a case of zero weight updates. Nonzero recorded gradients and finite losses agree with that finding. Mean loss across the first 100 updates was 9.1862; across the last 100 it was 8.8366. This small change did not improve the frozen validation ranking.

There were 38 cat predictions above threshold at step 0 versus 37 at step 600, 12 dog predictions at both, no billboard predictions at either, and 0 versus 1 washing-machine predictions. The single washing-machine prediction did not match a reviewed target. Prediction counts alone are not accuracy metrics.

## Evaluation and application disposition

The 130 held-out photographs and 24 reserved frames from six sequences were not evaluated in this audit. Their gate remains **deferred, not passed**. Step 0 is the starting reference, and the predeclared adoption gate requires a useful strict gain. This trial has already failed to produce a development candidate with that gain; using reserved data cannot turn the selected step-0 checkpoint into an improved trained model.

No new training, model download, inference, export, application weight replacement or GUI change was performed. The separate GUI Studio package remains available with its previously packaged models; job 7780632 has not been integrated.

## Concrete follow-up

Run a validation-only confidence and localization probe on the **28 known misses** listed in `validation-misses.json`: 4 dog, 11 billboard and 13 washing-machine targets. Prioritize the 24 new-class misses. Compare step 0 and step 600 before thresholding: strongest target-class logits, same-class query overlap, best query-box overlap regardless of label, and the encoder proposal's overlap/category. Keep the frozen scorer and threshold unchanged; store these diagnostics separately.

This separates low class confidence from missing localization/proposals before proposing a broader training scope. Frozen random new-class encoder rows and frozen features/boxes are possible constraints from the implementation, **not a demonstrated cause**. The saved thresholded predictions cannot establish that cause. Do not rerun training, lower production thresholds, or consume held-out data as part of this diagnostic.

## Limits and reproducibility

The annotations were assistant-reviewed, with no independent human recheck. Partial classes support known-positive recall only; unknown classes do not establish negatives. The audit reads existing artifacts and loads tensor checkpoints with `weights_only=True` on CPU. `audit_trial.py`, `finish_report.py`, `AUDIT.json`, the two diagnostic worklists and `INPUT_INTEGRITY.json` preserve the procedure and evidence. Running the audit scripts writes only their own output folder.
'''
(P/'REPORT.md').write_text(report,encoding='utf-8')
save('CONTINUATION_STATE.json',dict(project='FrameTrail',latest_job='7780632',status=audit['status'],selected_step=0,approved_for_application=False,
    heldout_evaluation='not run; no improved validation candidate',gui='gui-studio-20261018-v1 remains packaged separately; no 7780632 adoption',
    next_best_step='Validation-only raw-logit and query-localization probe on the 24 billboard/washing-machine misses, then 4 dog misses; compare step 0 and 600 before proposing new training.',
    standing_communication_preference='End every user-facing response with the single best plausible concrete next step for FrameTrail and briefly explain why; carry this into every handoff.',
    restrictions=['No new GPU job or automatic retry','No automatic model export or adoption','Preserve held-out photos/video for a frozen useful candidate','No annotation, vocabulary, source or prior package changes','No desktop takeover or visible app launch']))
save('FINAL_RECEIPT.json',dict(status='complete-read-only-trial-audit',job='7780632',selection_reproduced=True,metrics_reproduced=True,sampling_reproduced=True,
    tensor_freeze_checks_passed=True,known_active_validation_misses=28,heldout_used=False,training_submitted=False,model_exported=False,approved_for_application=False))
print(json.dumps(dict(status='report-complete',known_misses=len(misses),new_class_misses=sum(m['canonical_id'] in (133,593) for m in misses)),indent=2))
