"""Aggregate raw validation diagnostics and create a local evidence gallery."""
from pathlib import Path
import collections,hashlib,html,json,math,shutil,statistics
import numpy as np
from scipy.optimize import linear_sum_assignment
P=Path(__file__).resolve().parent
OLD=Path(r'C:\Users\nazee\.codex\visualizations\2026\10\15\01a141ae-c7a6-7303-a280-403af88736f3')
RELEASE=OLD/'nextdata-reviewed-release-7769109-v1'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(name,data):(P/name).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n',encoding='utf-8')
probe=read(P/'PROBE.json');pairs={}
manifest=read(RELEASE/'candidate-manifest-v2.json');train={r['image_id']:r for r in manifest['images'] if r['split']=='train'}
run=Path(r'C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation\outputs\trial-results-7780632-20261018-v1/retrieval/verified-7780632/output/rf-nextdata-7780632')
schedule=read(run/'sampling-plan.json');frequency=collections.Counter(x for batch in schedule for x in batch)
assert set(frequency)<=set(train)
exposure=[]
for cid in [15,16,133,593]:
    positive=[r for r in train.values() if any(t['canonical_id']==cid for t in r['targets'])]
    exposure.append(dict(canonical_id=cid,known_positive_training_photos=len(positive),sampled_positive_photos=sum(r['image_id'] in frequency for r in positive),
        positive_photo_presentations=sum(frequency[r['image_id']] for r in positive),
        known_positive_target_presentations=sum(frequency[r['image_id']]*sum(t['canonical_id']==cid for t in r['targets']) for r in positive),
        complete_or_absent_photo_presentations=sum(n for image_id,n in frequency.items() if train[image_id]['scope'].get(str(cid)) in ('complete','absent'))))
save('training-exposure.json',dict(status='read-only-reconstruction-of-completed-run',classes=exposure,updates=600,presentations=2400,new_training=False,limits='Presentations describe supervision opportunities, not matched queries or effective gradients.'))
selection=[]
for cid in [15,16,133,593]:
    positives=sorted((r for r in train.values() if any(t['canonical_id']==cid for t in r['targets'])),key=lambda r:r['image_id'])[:2]
    negatives=sorted((r for r in train.values() if r['scope'].get(str(cid))=='absent' and not any(t['canonical_id']==cid for t in r['targets'])),key=lambda r:r['image_id'])[:2]
    selection.extend(dict(canonical_id=cid,role=role,image_id=r['image_id'],image_sha256=r['image_sha256']) for role,rs in [('positive',positives),('explicit-negative',negatives)] for r in rs)
save('training-diagnostic-sample-selection.json',dict(status='prepared-not-executed',split='train',selection=selection,distinct_photos=len({s['image_id'] for s in selection}),optimizer_updates=0))
(P/'TRAINING_DIAGNOSTIC_PLAN.md').write_text('''# Next diagnostic: training-only classification signal

Status: prepared, not executed. This is a proposed read-only CPU gradient diagnostic, not approval for a GPU training run.

1. Use only the frozen IDs and hashes in `training-diagnostic-sample-selection.json`: two known-positive and, where available, two explicit-absent training photos per active class. Keep all existing targets and scope masks. The deterministic sample is for debugging, not a representative evaluation.
2. Load the same pinned model at step 0 and step 600. Keep eval mode, group one, the original 512×512 preprocessing, math attention, and all feature/box/encoder parameters frozen. Enable gradients only for the four previously approved final classifier rows.
3. For each sample, run the sealed scoped criterion. Record matched query IDs and IoUs, per-target class probabilities and IoU-aware soft targets, total target count used for normalization, individual loss components and the weighted total. Record each active row's gradient norm and direction at its matched positives. Distinguish frozen auxiliary/box losses from losses that can update the permitted head.
4. Check that explicit-negative scopes contribute suppression, unknown scopes contribute no direct logit gradient, and inactive classifier rows remain gradient-masked. Compare the recorded total against the sealed loss implementation; do not replace the objective during this check.
5. Do not create an optimizer or perform any parameter update. Verify parameter tensors and checkpoint hashes before and after. No test/validation-based hyperparameter tuning, model export, app change, new model download or remote job.
6. Use the resulting signal and `training-exposure.json` to prepare the narrowest next optimization proposal. If classifier gradients remain useful, consider a bounded classifier optimization budget/learning-rate change before expanding trainable model components. Preserve per-class retention guards and leave held-out data for a frozen useful candidate. A new GPU trial needs separate scope approval.

Why this comes next: every one of the 24 new-class validation targets already has a distinct decoder query with IoU ≥ .5. The measured failure is inadequate class confidence on those queries, so wider box-head training is not supported by this probe.
''',encoding='utf-8')
for c in probe['cases']:pairs.setdefault(c['miss_index'],{})[c['step']]=c
assert len(pairs)==28 and all(set(p)=={0,600} for p in pairs.values())
summary=[];comparisons=[]
for cid,name in [(133,'Billboard'),(593,'Washing machine'),(16,'Dog')]:
    items=[v for v in pairs.values() if v[0]['canonical_id']==cid];entry=dict(canonical_id=cid,name=name,known_misses=len(items),steps=[])
    for step in [0,600]:
        cs=[p[step] for p in items];layer={}
        for stage in ['decoder','encoder_selected','encoder_all']:
            confidence=[c[stage]['strongest_target_confidence']['target_confidence'] for c in cs]
            covered=[c[stage]['best_covering_query']['target_confidence'] for c in cs if c[stage]['best_covering_query']]
            layer[stage]=dict(targets_with_any_box_iou_at_least_half=sum(c[stage]['covering_queries']>0 for c in cs),
                targets_with_query_meeting_confidence_and_geometry=sum(c[stage]['queries_meeting_class_and_geometry']>0 for c in cs),
                max_target_confidence_any_query_min=min(confidence),max_target_confidence_any_query_median=statistics.median(confidence),max_target_confidence_any_query_max=max(confidence),
                best_confidence_on_covering_queries_min=min(covered) if covered else None,best_confidence_on_covering_queries_median=statistics.median(covered) if covered else None,best_confidence_on_covering_queries_max=max(covered) if covered else None)
        entry['steps'].append(dict(step=step,stages=layer))
    summary.append(entry)
for index,pair in sorted(pairs.items()):
    a,b=pair[0],pair[600];d=b['decoder'];e=b['encoder_selected'];all_e=b['encoder_all']
    comparisons.append(dict(miss_index=index,image_id=b['image_id'],canonical_id=b['canonical_id'],
        observed_limit=('classification confidence below .35 despite a decoder box at IoU >= .5' if d['covering_queries'] and not d['queries_meeting_class_and_geometry'] else 'no decoder box reaches IoU .5' if not d['covering_queries'] else 'raw qualifying query exists; investigate one-to-one matching/NMS'),
        proposal_coverage_lost_at_selection=all_e['covering_queries']>0 and e['covering_queries']==0,
        encoder_coverage_lost_in_decoder=e['covering_queries']>0 and d['covering_queries']==0,
        best_decoder_iou=d['best_overlap']['iou'],confidence_on_best_overlap_before=a['decoder']['best_overlap']['target_confidence'],confidence_on_best_overlap_after=d['best_overlap']['target_confidence'],
        max_target_confidence_before=a['decoder']['strongest_target_confidence']['target_confidence'],max_target_confidence_after=d['strongest_target_confidence']['target_confidence']))

# Recompute every recorded target diagnostic directly from the compact raw arrays.
checked=0
for c in probe['cases']:
    raw=np.load(P/'raw'/f"step-{c['step']:04}-{c['image_id']}.npz",allow_pickle=False)
    class_column=list(raw['active_class_ids']).index(c['canonical_id']);target=np.array(c['target_xyxy'])
    for stage in ['decoder','encoder_selected','encoder_all']:
        boxes=raw[stage+'_boxes_xyxy'];logits=raw[stage+'_active_logits'][:,class_column];confidence=1/(1+np.exp(-logits))
        inter=np.maximum(np.minimum(boxes[:,2:],target[2:])-np.maximum(boxes[:,:2],target[:2]),0).prod(1)
        union=np.maximum(boxes[:,2:]-boxes[:,:2],0).prod(1)+(target[2]-target[0])*(target[3]-target[1])-inter
        ov=inter/np.maximum(union,1e-10);s=c[stage]
        assert abs(float(ov.max())-s['best_overlap']['iou'])<1e-6
        assert int((ov>=.5).sum())==s['covering_queries']
        assert int(((ov>=.5)&(confidence>=.35)).sum())==s['queries_meeting_class_and_geometry']
        assert abs(float(confidence.max())-s['strongest_target_confidence']['target_confidence'])<1e-6
        checked+=1
    raw.close()
save('SUMMARY.json',dict(status='complete',classes=summary,target_comparisons=comparisons,raw_stage_checks=checked,
    limits='Failure subset; coverage allows any query and repeated use, not one-to-one detection recall. No threshold optimization.'))
assignments=[]
for step in [0,600]:
    for image_id in sorted({c['image_id'] for c in probe['cases']}):
        with np.load(P/'raw'/f'step-{step:04}-{image_id}.npz',allow_pickle=False) as raw:
            for cid in [133,593,16]:
                cs=[c for c in probe['cases'] if c['step']==step and c['image_id']==image_id and c['canonical_id']==cid]
                if not cs:continue
                boxes=raw['decoder_boxes_xyxy'];ov=[]
                for c in cs:
                    target=np.array(c['target_xyxy']);inter=np.maximum(np.minimum(boxes[:,2:],target[2:])-np.maximum(boxes[:,:2],target[:2]),0).prod(1)
                    union=np.maximum(boxes[:,2:]-boxes[:,:2],0).prod(1)+(target[2]-target[0])*(target[3]-target[1])-inter
                    ov.append(inter/np.maximum(union,1e-10))
                ov=np.array(ov);ai,bi=linear_sum_assignment(np.where(ov>=.5,1-ov,1000))
                count=int((ov[ai,bi]>=.5).sum())
                assignments.append(dict(step=step,image_id=image_id,canonical_id=cid,targets=len(cs),targets_with_distinct_covering_query=count))
new_assignments=[a for a in assignments if a['step']==600 and a['canonical_id'] in (133,593)]
assert sum(a['targets_with_distinct_covering_query'] for a in new_assignments)==24
save('geometry-assignment.json',dict(status='pass',new_class_targets_with_distinct_covering_decoder_queries=24,assignments=assignments,
    limits='Oracle class-agnostic geometry assignment on failure subset, not detection accuracy.'))
table=[]
for s in summary:
    a=s['steps'][0]['stages']['decoder'];b=s['steps'][1]['stages']['decoder'];enc=s['steps'][1]['stages']
    table.append(f"| {s['name']} | {s['known_misses']} | {b['targets_with_any_box_iou_at_least_half']} | {a['max_target_confidence_any_query_median']:.2%} → {b['max_target_confidence_any_query_median']:.2%} | {b['max_target_confidence_any_query_max']:.2%} | {enc['encoder_all']['targets_with_any_box_iou_at_least_half']} → {enc['encoder_selected']['targets_with_any_box_iou_at_least_half']} |")
new=[c for c in comparisons if c['canonical_id'] in (133,593)]
localized=sum(c['observed_limit'].startswith('classification') for c in new);missing=sum(c['observed_limit'].startswith('no decoder') for c in new)
proposal_losses=sum(c['proposal_coverage_lost_at_selection'] for c in new);refinement_losses=sum(c['encoder_coverage_lost_in_decoder'] for c in new)
save('VALIDATION_RECEIPT.json',dict(status='pass',validation_photos=probe['images'],full_model_forwards=len(probe['image_checks']),
    cpu_saved_prediction_parity_passed=all(c['parity']['passed'] for c in probe['image_checks']),
    raw_target_stage_checks=checked,encoder_reconstruction_checks_passed=True,
    all_24_new_class_targets_have_distinct_covering_decoder_queries=True,
    checkpoint_box_identity_checks_passed=all(all(c['boxes_identical_to_step_zero'].values()) for c in probe['image_checks'] if c['step']==600),
    original_input_hashes_unchanged=probe['input_hashes_unchanged'],heldout_used=False,new_training=False,model_export=False))
report=f'''# Why trial 7780632 missed the new classes

This offline CPU probe compared step 0 and step 600 on **{probe['images']} existing validation photos containing 28 known misses**: 11 billboards, 13 washing machines and 4 dogs. All {len(probe['image_checks'])} full-model forwards reproduced the saved KIT decoded outputs within the declared parity checks (same detection count/classes, matched box IoU ≥ .99 and confidence difference ≤ .002).

## Measured result

| Class | Known misses | Targets with a decoder box at IoU ≥ .5 | Median of per-target strongest class confidence, step 0 → 600 | Maximum class confidence at step 600 | Targets covered by all encoder proposals → selected proposals |
|---|---:|---:|---:|---:|---:|
{chr(10).join(table)}

The median uses one strongest query confidence per target; targets in the same photo share that value. These are raw scores before filtering. The confidence cutoff remains .35 (35%); no threshold was tuned. A geometrically covering box ignores its class label and is an oracle diagnostic, not a successful detection.

Of the **24 new-class misses**, **{localized}** already have a decoder box overlapping the target at IoU ≥ .5 but no query with both adequate overlap and class confidence ≥ .35. The other **{missing}** lack any final decoder box at that overlap. There are **{proposal_losses}** targets covered by some encoder proposal but absent from the selected 300 proposals, and **{refinement_losses}** covered by selected encoder proposals but lost after decoder refinement; these stage comparisons describe coverage and may overlap.

The classifier rows did learn different numbers, but their confidence changes did not yield a usable new-class detection. Crucially, **all 24 new-class targets already have a geometrically usable decoder box**. An additional one-to-one assignment check confirms that distinct queries can cover all 24; this is not merely counting the same query for multiple targets. Localization is not the demonstrated bottleneck on this failure subset. The one encoder-selection coverage loss is recovered by the decoder. There is no measured reason here to unfreeze the box regressor.

On queries that actually overlap the targets sufficiently, median best billboard confidence rises from 0.93% to 3.30%, and washing-machine confidence rises from 2.39% to 22.58%. The highest washing-machine score anywhere reaches 36.90%, but that query does not sufficiently overlap a reviewed washing-machine target. The highest washing-machine score on a covering query is 32.17%, still below 35%.

The final decoder boxes, selected encoder boxes and all encoder boxes were bit-identical between the checkpoints on every probed photo. This verifies the frozen localization scope; unchanged geometry does not mean the existing boxes were unusable.

## What this does and does not establish

The measured limitation for the 24 new-class targets is inadequate correct-class confidence on existing boxes. The data do not establish whether the best remedy is more classifier optimization, different learning rates, better loss balance, additional reviewed data or adaptation of shared features. A wider fine-tuning scope has not been justified by this probe. Scores are not calibrated probabilities of real-world correctness. The 4 dog misses also have a covering decoder box but insufficient confidence on covering queries; this is a separate retention diagnostic, not a claim about all dogs.

The training loss is IoU-aware: its positive classification target depends on the matched box overlap, while box parameters were frozen. This is a source-code observation in the sealed `scoped_rf.py`; poor overlap can constrain the supervision signal. This validation probe did not inspect training-time matches and does not establish that mechanism as the sole cause.

No GPU job, training, threshold change, model export, application update, annotation edit or held-out evaluation occurred. All original input hashes are unchanged. The reserved 130 test photographs and 24 video frames remain unused. The existing app model remains installed separately.

## Best next step

Run a small **training-only classification-loss and gradient diagnostic**, without optimizer updates, on fixed positive and explicit-negative samples for the four approved rows. Inspect per-class exposure, matched box overlaps, IoU-aware soft targets, loss normalization and row-gradient norms at steps 0 and 600. `training-exposure.json` already reconstructs the completed sampler's exposure; `TRAINING_DIAGNOSTIC_PLAN.md` defines the remaining check.

Use that evidence to prepare a bounded next optimization proposal with the same retention guards and untouched held-out gate. Prefer the narrowest scope that addresses the measured classification problem; a new GPU trial needs separate approval. Do not repeat the same run blindly, unfreeze box parameters based on this probe, or lower the app threshold to make validation misses appear solved.

## Evidence

- `index.html`: photo-by-photo overlays and before/after raw scores for all 28 targets.
- `PROBE.json`: full per-target, per-stage diagnostics and CPU/KIT parity checks.
- `SUMMARY.json`: aggregate results and each target's observed limitation.
- `raw/`: compact NumPy outputs for decoder, all encoder proposals and selected proposals at both checkpoints; no model weights.
- `INPUT_INTEGRITY.json`, `VALIDATION_RECEIPT.json`: source identities and checks.
- `probe.py`, `summarize.py`: reproducible offline procedure. Runtime: Torch 2.8.0+cpu, RF-DETR 1.11.2; the completed KIT trial used Torch 2.8.0+cu128. Numerical parity was checked rather than assuming CPU/CUDA identity.

An initial local CPU attempt was interrupted after six photos when the tool session reset; its partial files were preserved in the prior work directory. This deliverable uses a fresh complete run. It contains no remote resubmission or additional training.
'''
(P/'REPORT.md').write_text(report,encoding='utf-8')

manifest=read(RELEASE/'candidate-manifest-v2.json');rows={r['image_id']:r for r in manifest['images'] if r['split']=='val'}
names=read(OLD/'nextdata-rf-trial-7769109-v1/rf-nextdata-tools-v1/rf-mapping.json')['canonical_class_names']
def cname(cid):return names[str(cid)] if isinstance(names,dict) else names[cid]
(P/'photos').mkdir(exist_ok=True)
for image_id in {p[0]['image_id'] for p in pairs.values()}:shutil.copyfile(RELEASE/rows[image_id]['source_path'],P/'photos'/f'{image_id}.jpg')
cards=[]
for index,pair in sorted(pairs.items(),key=lambda v:({133:0,593:1,16:2}[v[1][0]['canonical_id']],v[0])):
    c=pair[600];row=rows[c['image_id']];target=c['target_xyxy'];w,h=row['width'],row['height']
    def rect(box,color,dash=''):
        x,y,x2,y2=box;return f'<rect x="{x}" y="{y}" width="{x2-x}" height="{y2-y}" fill="none" stroke="{color}" stroke-width="{max(w,h)/250}" {dash}/>'
    svg=f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="Reviewed target, nearest decoder box and nearest selected encoder proposal"><image href="photos/{c["image_id"]}.jpg" width="{w}" height="{h}"/>'+rect(c['encoder_selected']['best_overlap']['box'],'#ffb84d','stroke-dasharray="12 7"')+rect(c['decoder']['best_overlap']['box'],'#67d8ff')+rect(target,'#75f0a1')+'</svg>'
    a=pair[0]['decoder'];b=c['decoder'];best=b['best_overlap'];comparison=next(x for x in comparisons if x['miss_index']==index)
    scope_label={'positive_only':'Known positives only','complete':'Complete annotation','absent':'Reviewed absent'}.get(c['scope'],c['scope'])
    cards.append(f'''<article class="case"><div>{svg}</div><section><p class="eyebrow">Photo {row.get('photo_number')} · {html.escape(scope_label)}</p><h2>{html.escape(cname(c['canonical_id']).title())} · target {index+1}</h2><p>{html.escape(comparison['observed_limit'])}</p><dl><dt>Best decoder overlap</dt><dd>{best['iou']:.3f} IoU</dd><dt>Target confidence on that box</dt><dd>{a['best_overlap']['target_confidence']:.2%} → {best['target_confidence']:.2%}</dd><dt>Highest target confidence, any query</dt><dd>{a['strongest_target_confidence']['target_confidence']:.2%} → {b['strongest_target_confidence']['target_confidence']:.2%}</dd><dt>Top label on nearest decoder box</dt><dd>{html.escape(cname(best['top_class']))} ({best['top_class_confidence']:.1%})</dd><dt>Best selected encoder overlap</dt><dd>{c['encoder_selected']['best_overlap']['iou']:.3f} IoU</dd><dt>Best overlap before proposal selection</dt><dd>{c['encoder_all']['best_overlap']['iou']:.3f} IoU</dd></dl><p class="muted">Box coordinates are identical at steps 0 and 600. Scores shown before filtering; neither a label change nor an oracle box counts as a detection.</p></section></article>''')
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>FrameTrail · Trial 7780632 diagnostic</title><style>*{box-sizing:border-box}body{margin:0;background:#111318;color:#eef0f5;font:15px/1.55 system-ui,Segoe UI,sans-serif}main{max-width:1220px;margin:auto;padding:45px 28px}h1{font-size:34px;letter-spacing:-1px;margin:8px 0 12px}h2{font-size:22px;line-height:1.25;margin:5px 0 18px}.eyebrow{font-size:12px;letter-spacing:1.4px;text-transform:uppercase;color:#afa5ef}.intro{max-width:850px;color:#bdc2cf}a{color:#bcb0ff}.legend{display:flex;gap:22px;flex-wrap:wrap;margin:24px 0 32px}.legend span{border-left:4px solid;padding-left:10px}.case{display:grid;grid-template-columns:1.2fr 1fr;background:#1b1e26;border:1px solid #303541;border-radius:16px;overflow:hidden;margin:22px 0}.case>div{display:flex;align-items:center;justify-content:center;background:#090b0e;padding:16px}.case svg{display:block;width:100%;max-height:620px}.case section{padding:26px}dl{display:grid;grid-template-columns:1.1fr 1fr;gap:10px 18px;font-size:13px}dt{color:#aeb5c4}dd{margin:0}.muted{font-size:12px;color:#929bad}footer{margin:35px 0;color:#aeb5c4;font-size:13px}@media(max-width:800px){main{padding:24px 15px}.case{grid-template-columns:1fr}h1{font-size:27px}dl{grid-template-columns:1fr 1fr}}</style><main><p class="eyebrow">FrameTrail / completed trial 7780632</p><h1>Where the detections stopped improving</h1><p class="intro">28 known validation misses across 15 photos. Both checkpoints reproduce the saved KIT predictions. Compare class confidence with usable box coverage; all model boxes shown remained unchanged during the classifier-only trial. Fixed detection thresholds: 35% confidence and .5 IoU.</p><p><a href="REPORT.md">Read the findings</a> · <a href="SUMMARY.json">Aggregate evidence</a> · <a href="PROBE.json">Full diagnostic records</a></p><div class="legend"><span style="border-color:#75f0a1">Reviewed target</span><span style="border-color:#67d8ff">Decoder box with highest target overlap</span><span style="border-color:#ffb84d">Selected encoder box with highest overlap</span></div>'''+''.join(cards)+'''<footer>Failure-subset diagnostic, not an accuracy benchmark. Any-query overlap ignores one-to-one matching and class correctness. Partial labels establish known positives only. No held-out data, new training, threshold changes or app adoption.</footer></main></html>'''
(P/'index.html').write_text(page,encoding='utf-8')
save('CONTINUATION_STATE.json',dict(project='FrameTrail',job='7780632',status='validation-confidence-localization-probe-complete',selected_checkpoint_step=0,
    diagnostic_counts=dict(new_class_targets=24,confidence_limited_with_usable_decoder_box=localized,without_decoder_box_iou_half=missing,proposal_selection_coverage_losses=proposal_losses,decoder_coverage_losses=refinement_losses),
    next_best_step='Run a training-only classification-loss and row-gradient diagnostic without optimizer updates, then prepare the narrowest evidence-supported bounded optimization proposal. All 24 new-class targets already have usable decoder boxes; wider localization adaptation is not supported by this probe.',
    application_adoption=False,heldout_used=False,new_training=False,
    standing_communication_preference='End every user-facing response with the single best plausible concrete FrameTrail next step and briefly why; propagate this preference in every handoff.'))
print(json.dumps(dict(classes=summary,new_class_confidence_limited=localized,new_class_geometry_limited=missing,proposal_selection_losses=proposal_losses,decoder_refinement_losses=refinement_losses,raw_checks=checked),indent=2))
