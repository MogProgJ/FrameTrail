"""Preserve completed first-pass review, qualification holds and current handoff."""
import json,hashlib,collections,shutil
from pathlib import Path
R=Path(r'C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation');D=R/'outputs/broad-billboard-definition-20261022-v1';B=D/'review-stage-v3';V=D/'first-pass-v4'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    with p.open('x',encoding='utf-8') as f:f.write(json.dumps(v,indent=2,allow_nan=False)+'\n')
def main():
    V.mkdir(exist_ok=False)
    unknown=read(D/'OLD_VAL_UNKNOWN_FIRST_PASS.json');a=read(B/'ANNOTATIONS_DRAFT.json');audit=read(B/'STRUCTURAL_AUDIT.json')
    byid={x['image_id']:x for x in unknown['records']};assert len(byid)==119
    for r in a['records']:
        if r['image_id'] in byid:
            assert r['review'] is None and r['draft_scope_133']=='unknown'
            r['first_pass_review']=byid[r['image_id']];r['review_state']='original-viewed-unknown-preserved-annotation-unqualified'
    conflict=dict(image_id='88ced829147507c7',retained_target_index=1,retained_normalized_cxcywh=[0.1366665,0.509375,0.273333,0.06000000000000005],finding='Inherited class133 target encloses 7 Av street-name sign, which conflicts with explicit operational-wayfinding exclusion in both narrow and broad working rules.',action='Hold inherited target from any future training/scoring release. Preserve old source target and old results; remove/correct only in a future versioned truth overlay with an exact exclusion receipt.',production_change=False)
    rr=next(r for r in a['records'] if r['image_id']==conflict['image_id']);assert rr['draft_scope_133']=='positive_only';assert rr['draft_targets_133'][1]['normalized_cxcywh']==conflict['retained_normalized_cxcywh']
    rr['draft_targets_133'][1]['semantic_review_status']='excluded-operational-sign-conflict-held-not-admissible';rr['draft_targets_133'][1]['eligible_for_training_or_scoring']=False
    a.update(status='323-originals-first-pass-reviewed-labels-unqualified',first_pass_unknown_review_ref=dict(path=str(D/'OLD_VAL_UNKNOWN_FIRST_PASS.json'),sha256=sha(D/'OLD_VAL_UNKNOWN_FIRST_PASS.json')),all_originals_viewed=True,qualified_release=False)
    save(V/'ANNOTATIONS_DRAFT.json',a);save(V/'INHERITED_TARGET_CONFLICT.json',conflict)
    potential=[x for x in unknown['records'] if x['display_or_boundary_followup']]
    save(V/'QUALIFICATION_QUEUE.json',dict(unknown_validation_display_or_boundary_followups=potential,unknown_validation_retained=119,unknown_as_background=False,reviewed_draft_holds=audit['unresolved_reviewed'],inherited_target_conflicts=[conflict],all_first_pass_originals_viewed=323,approved_for_training=False))
    sheets=[p for folder in [D/'fresh-train-draft-v1',D/'fresh-role-draft-v2',B] for p in folder.glob('*QA_SHEET*.jpg')]
    save(V/'OVERLAY_QA_REVIEW.json',dict(reviewer='assistant-same-session-not-independent-human',sheets_viewed=[dict(path=str(p),sha256=sha(p)) for p in sorted(sheets)],result='Draft additions visually checked; unresolved/dense/segmentation cases remain held. One inherited street-name target conflict found and explicitly held. No blanket semantic approval.',source_originals_viewed=323,approved_for_training=False))
    checks=[]
    for r in a['records']:
        assert sha(Path(r['source_path']))==r['image_sha256'];assert r['approved_for_training'] is False
        assert r['review'] or r.get('first_pass_review')
        for i,t in enumerate(r['old_billboard_targets']):
            assert r['draft_targets_133'][i]['canonical_id']==t['canonical_id'] and r['draft_targets_133'][i]['normalized_cxcywh']==t['normalized_cxcywh']
        if r.get('first_pass_review'):assert r['draft_scope_133']=='unknown'
    assert len(a['records'])==len({r['image_id'] for r in a['records']})==323
    assert not any(r['draft_targets_133'] for r in a['records'] if r['draft_scope_133']=='absent')
    fresh=R/'outputs/data-review-7840599-20261021-v1/reviewed-release-v1/scoped-fresh-additions-v1.json'
    assert sha(fresh)=='b262af61db8141abadd61cc026454953f6c172bd2fff552334c456170b5feb09'
    receipt=dict(status='first-pass-complete-not-a-qualified-dataset',originals_viewed=323,explicit_draft_annotation_records=204,legacy_unknown_first_pass_records=119,legacy_unknown_display_or_boundary_followups=len(potential),new_draft_boxes=41,inherited_targets_retained_for_provenance=129,inherited_targets_explicitly_held_for_semantic_conflict=1,old_absent_photos_now_known_positive=20,fresh_absent_photos_now_known_positive=19,fresh_absent_shortfalls=dict(train=11,val=6,test=4),train_family_shortfalls=audit['train_family_shortfalls'],unused_local_candidates=223,approved_for_training=False,new_optimizer_updates=0,new_model_inference=0,TEST_predictions=0,new_cluster_jobs=0,production_adoption=False,source_hashes_verified=323,original_fresh_release_sha256=sha(fresh),annotations_sha256=sha(V/'ANNOTATIONS_DRAFT.json'),structural_integrity_checks='pass; semantic/rights/scene/role/guard qualification incomplete')
    save(V/'COMPLETION_RECEIPT.json',receipt)
    report='''# Billboard definition revision: first image-review pass complete

Business/restaurant identity boards and promotional advertising boards both count, following the user's clarification: "they should both be considered. they are both at the end, billboards". The broader working definition is frozen in TASK_DEFINITION.json. Venue/institution/service identity is a recorded implementation interpretation; uncertain small cards, nonplanar signs, mixed operational displays and dense scenes remain on hold.

All 323 fixed original photos have now been viewed: 124 fresh-role photos, 64 older TRAIN replay photos and 135 older validation photos. This is an assistant review, not independent human annotation. There is no new model fitting, image inference, TEST prediction use, cluster job or app/model change.

The versioned draft adds 41 proposed boxes to the 204 previously scoped photos. It identifies 20 previously absent photos with in-scope boards (19 fresh, one older laundromat replay). Some earlier negative supervision therefore conflicts with the user's intended task. The old experiment results remain frozen narrow-task history; this does not qualify an old model or prove that all remaining errors come from labels.

| Fresh role | Complete positive photos | Partial positive photos | Whole-photo absent | Unknown/hold | Absent-photo shortfall |
|---|---:|---:|---:|---:|---:|
| TRAIN | 34 | 6 | 19 | 1 | 11 |
| Validation | 16 | 1 | 14 | 1 | 6 |
| TEST | 13 | 3 | 16 | 0 | 4 |

These are draft counts, not admitted release counts. The original 30/30 TRAIN and 12/20 validation/TEST positive/absent minima are unchanged. The original minimum is five TRAIN absent photos per confuser family: the current draft lacks five shop/business-lettering negatives and one traffic/information negative. Do not refill shop negatives with physical business boards that now belong to the positive class. Bare facade lettering and other genuinely out-of-scope street objects are candidate confusers, subject to review. Scene, identity, rights, concentration and role checks remain mandatory.

The 119 previously unknown validation photos received a first visual pass, and 32 have display or boundary follow-ups. All 119 remain unknown in this draft: they do not become negative supervision or cleared scoring truth by default. This preserves the meaning of the old unknown-count guard while a separate complete truth overlay is prepared. Crowded old positives remain partial where boxes are incomplete.

Overlay QA also found an inherited class133 box around the 7 Av street-name plate in photo 88ced829147507c7. That target conflicts with the explicit traffic/wayfinding exclusion. It is marked ineligible in the new draft and recorded separately; the old source label and all old results remain preserved. Inherited boxes are provenance, not a guarantee of valid new truth.

All 323 image hashes were rechecked, and the original fresh-release manifest remains b262af61db8141abadd61cc026454953f6c172bd2fff552334c456170b5feb09. Structural checks pass for role retention, exact inherited boxes, bounded new boxes and no automatic unknown-to-negative conversion. The draft is explicitly not approved for training.

The complete unused local inventory contains 223 source-eligible visual-queue candidates with original prospective roles: 175 billboard-anchor records and 48 other-anchor records (33 TRAIN, 11 validation, four TEST). No current exact-hash or cross-role resolved-owner conflicts were found in that metadata inventory. This is not rights/content/scene clearance, and it does not guarantee enough suitable negatives. Enumerate and review candidates without model-outcome filtering before considering collection.

Before any expanded-task baseline or fit: finish complete target/absence QA, resolve the recorded target conflict, fill role/family shortfalls with prospectively assigned data, revalidate source/rights/scene evidence, and freeze an explicit guard-compatible comparison. Retain both baseline models, other-class invariance, legacy receipts and unknown cap 530. Any semantic conflict with a legacy class133 retention gate must be documented and resolved, never silently waived. Validation remains development evidence already used under the narrow task; TEST remains prediction-unconsumed and cannot select a model. No further old-scope classifier/query/loss grid is authorized by this data revision.

Next step: review the unused local candidates for the missing 11 TRAIN, six validation and four TEST absent photos, including five valid shop-lettering confusers, because the broader task now has a concrete data-coverage gap before another training comparison.
'''
    (D/'REVISION_REPORT.md').write_text(report,encoding='utf-8')
    handoff='''# FrameTrail: broader billboard scope accepted; first image-review pass complete

LATEST 22 October 2026: User answered the product boundary question: "they should both be considered. they are both at the end, billboards". This explicitly includes business/restaurant identity boards along with promotional boards. Do not ask that same question again. The previous handoff's pending human-boundary review is superseded by this user answer. User also said "All right, go ahead. Proceed to the next step." Continue necessary local data qualification autonomously; no routine approval checkpoints.

Canonical workspace C:/Users/nazee/Documents/Codex/2026-10-18/frametrail-continuation. Ignore unrelated saved MiniERP project; never edit it. Read AGENTS.md. Strictly ignore Carrington Event and all unrelated cluster/files/jobs. No SSH, new jobs, inference, fitting, export, model or app changes in this data-review stage. Production unchanged: YOLOX-S default, RF7805570 step100 explicit preview, ONNX hold, production_adoption=false. No background process/session/automation remains.

Authoritative revision folder: outputs/broad-billboard-definition-20261022-v1. Read REVISION_REPORT.md, TASK_DEFINITION.json, AUTHORIZATION.json, PLAN.json, then first-pass-v4/COMPLETION_RECEIPT.json, ANNOTATIONS_DRAFT.json, QUALIFICATION_QUEUE.json, INHERITED_TARGET_CONFLICT.json, OVERLAY_QA_REVIEW.json. Initial queue frozen 323 photos before revised labels; all323 originals now viewed. 204 previously scoped records have draft target/absence decisions; 119 old validation unknowns have visual notes and retain unknown (32 display/boundary followups). All annotations assistant-reviewed, NOT independent human gold. 41 new proposed boxes; 20 old absent photos now known positive (19 fresh + old laundry identity photo399048f892919b4c). All old original labels/roles/results immutable; no retroactive rescoring/old-model qualification. 323 source image hashes verified and original fresh release manifest SHA b262af61db8141abadd61cc026454953f6c172bd2fff552334c456170b5feb09 unchanged.

Fresh draft counts: TRAIN34complete positive+6partial positive+19absent+1unknown; VAL16complete+1partial+14absent+1unknown; TEST13complete+3partial+16absent. NOT approved_for_training. Original minima retained: TRAIN30positive/30absent; VAL/TEST12positive/20absent. Missing absent photos11/6/4. Original design data_required.minimum_train_absent_photos_per_family is FIVE (not six/eight): current household7,indoor8,traffic4,shop0; gaps traffic1/shop5. Do not call physical business boards negative to refill that family. Inventory at review-stage-v3/UNUSED_LOCAL_INVENTORY.json:223 unused candidates from347 source-eligible visual-queue records,175billboard-anchor+48contrast(33TRAIN,11VAL,4TEST). Original roles fixed, no model outcome filtering. All223 image hashes verified, no current exact-hash/cross-role owner conflict metadata; rights/scene/content clearance and within/cross-cohort perceptual QA still required. Do not claim admission or enough usable negatives yet.

Important QA finding: inherited positive target index1 in old TRAIN88ced829147507c7 is actually 7 Av street-name sign. New v4 draft marks that specific inherited target excluded-operational-sign-conflict-held-not-admissible and eligible_for_training_or_scoring=false, preserving old original source+results. Keep it out of a future qualified overlay. Old positive_only dense Times Square/other scenes stay partial; unknown never becomes background by default. 29 reviewed draft photo holds plus119 unknown qualification pending (see queue), even though first-pass originals review is done. Small retail price cards, nonplanar lantern/umbrella and mixed service-operational displays held, no need to broaden scope by guessing. Owner/permit/contractor markings integral to a billboard fixture aren't separate independent display faces; dedicated business panels are. Keep any unit ambiguity held.

Before any expanded model baseline/fit: complete label/unit/absence QA, resolve source/rights/scene/role/family minima and explicit legacy class133 gate compatibility. Both baseline models, other-class retention/model invariance, unknown cap530 and legacy metrics/receipts retained. Do not silently waive a guard or promote failed old runs under new truth. Old VAL has narrow-task development history; not a new independent cohort. TEST still0predictions, no selection/fit/threshold use. No further automatic old-scope classifier/query/loss grids.

Prior experiments all COMPLETE: detector7870268 four conditions no eligible state/winner=null/TEST0; M1final12TP8FP/13TP7FP, M0final11TP8FP/10TP8FP under narrow freshVAL truth. Old unknown counts542/538M1,538/538M0>cap530, not allFP. Retrieval exclusive local follow-up already consumed; do not reretrieve/retrain/resubmit/reseal/re-evaluate old package. Three separate authorized TRAIN-only CPU studies each8fits/1280updates complete (24fits/3840updates total), no saved model/image inference/VAL/TEST. Full-query control disproved omitted-supervised-negative coverage as sole explanation; photo-max MLP fit all fitting positive/negative queries cleanly at0.5 but held48/71hits15/77alarmed, no allfold clean support. These metrics condition on frozen narrow labels and cached covered queries; broadened task changes interpretation of some alarms. No model architecture selected.

Technical: pinned Python C:/Users/nazee/Documents/All Modules/FrameTrail/.deps/rfdetr-probe-cpu/Scripts/python.exe; use -u -B -X utf8. Canonical outside current writable roots, require_escalated approved for project writes; staging C:/Users/nazee/.codex/visualizations/2026/10/22/01a16501-3de9-7b62-b605-a133a8d2fc29. No subagents unless explicitly asked. Preserve old receipts and versioned draft snapshots. End every user-facing response with one concrete next FrameTrail step plus why, in ordinary language; do not turn progress into routine approval prompts.

Next step: review unused local candidates for11TRAIN/6VAL/4TEST truly absent additions, including five shop-lettering confusers, because correcting the intended task created a specific coverage gap that must be closed before training.
'''
    hp=R/'CURRENT_HANDOFF.md';old=hp.read_text(encoding='utf-8-sig');(D/'PRIOR_HANDOFF.md').write_text(old,encoding='utf-8')
    hp.write_text(handoff+'\n---\n\n# Preserved historical handoff\n\n'+old,encoding='utf-8');(R/'NEXT_CHAT_BROAD_BILLBOARD_20261022.md').write_text(handoff,encoding='utf-8')
    save(V/'FINAL_FILES_SHA256.json',{str(p.relative_to(D)):sha(p) for p in sorted(D.rglob('*')) if p.is_file() and p.name!='FINAL_FILES_SHA256.json'})
    print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
