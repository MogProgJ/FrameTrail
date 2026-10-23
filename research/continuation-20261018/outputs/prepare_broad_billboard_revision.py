"""Freeze the user-expanded task and exhaustive review queues. No label edits/fits/inference."""
import json,hashlib
from pathlib import Path
R=Path(r'C:\Users\nazee\Documents\Codex\2026-10-18\frametrail-continuation');O=R/'outputs'
D=O/'broad-billboard-definition-20261022-v1';C=O/'fresh-paired-controls-20261021-v1'
FRESH=O/'data-review-7840599-20261021-v1/reviewed-release-v1/scoped-fresh-additions-v1.json'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    with p.open('x',encoding='utf-8') as f:f.write(json.dumps(v,indent=2,allow_nan=False)+'\n')
def main():
    D.mkdir(exist_ok=False)
    assert sha(FRESH)=='b262af61db8141abadd61cc026454953f6c172bd2fff552334c456170b5feb09'
    scope=dict(version='frametrail-billboard-business-identity-v2-20261022',class_id=133,
        user_instruction='they should both be considered. they are both at the end, billboards',
        context='User explicitly includes photo-rich hotel/restaurant promotional boards and large restaurant/business identity boards.',
        includes=['Dedicated physical advertising/campaign display boards or panels.','Physical business, venue, institution, product or service identity boards, including freestanding restaurant names and service/garage panels.','Event promotion/identity boards and public-service campaign billboards.','Printed or digital dedicated advertising panels; existing narrow positive targets remain positives.'],
        excludes=['Traffic regulation/safety signs.','Pure operational route/timetable/wayfinding displays without business/venue identity or advertising as the main displayed function.','Whiteboards, generic computer/TV equipment and classroom projection.','Decorative framed photographs/art and household objects.','Bare lettering directly applied to a facade/object without a dedicated display panel is not automatically a billboard.'],
        mixed_case_policy='Record uncertain identity-versus-operational cases as unresolved for the new release; never infer absence from a publisher category or force a label to change model scores.',
        annotation='Whole-photo class133 completeness/absence review. Preserve exact old boxes when still applicable and add every newly in-scope board, with provenance. Other class scopes/targets unchanged; unknown is never background.',
        scope_interpretation_note='Venue/institution/service identity panels are a documented implementation interpretation of the user expansion, not individual user confirmation of every image.',
        prior_results_policy='All old labels, metrics, checksums and failed experiments remain immutable narrow-v1 history. No retroactive rescoring to claim the old trials qualified.',
        new_fits=0,new_inference=0,new_cluster_jobs=0,production_adoption=False)
    save(D/'TASK_DEFINITION.json',scope)
    save(D/'AUTHORIZATION.json',dict(date='2026-10-22',user_continuation='All right, go ahead. Proceed to the next step.',
        subsequent_user_scope_clarification=scope['user_instruction'],
        authorized_work='Versioned expanded-definition annotation/data qualification and necessary local preparation; no automatic extra loss/classifier grid.',
        independent_human_itemwise_review=False,original_task_receipt_sha256=sha(O/'train-photo-max-loss-7870268-20261022-v1/COMPLETION_RECEIPT.json')))
    fresh=read(FRESH);inputs=read(C/'INPUTS.json')['records'];groups=[]
    for row in fresh['images']:
        groups.append(dict(image_id=row['image_id'],source_pool='fresh-release',split=row['split'],source_root=str(FRESH.parent),row=row))
    for r in inputs:
        if r['pool'].startswith('old_'):
            groups.append(dict(image_id=r['image_id'],source_pool=r['pool'],split=r['row']['split'],source_root=r['base'],row=r['row']))
    assert len(groups)==323 and len({r['image_id'] for r in groups})==323
    queue=[]
    for r in sorted(groups,key=lambda r:({'train':0,'val':1,'test':2}[r['split']],r['source_pool'],r['image_id'])):
        row=r['row'];p=Path(r['source_root'])/row['source_path']
        assert sha(p)==row['image_sha256']
        queue.append(dict(image_id=r['image_id'],source_pool=r['source_pool'],split=r['split'],source_path=str(p),image_sha256=row['image_sha256'],width=row['width'],height=row['height'],
            identity_group=row['identity_group'],scene_group=row.get('scene_group'),old_scope=row['scope'].get('133','unknown'),
            old_billboard_targets=[t for t in row['targets'] if t['canonical_id']==133],confuser_family=row.get('confuser_family'),
            review_state='pending-expanded-whole-photo-review',task_definition_sha256=sha(D/'TASK_DEFINITION.json')))
    save(D/'REVIEW_QUEUE.json',dict(status='fixed-expanded-task-review-queue-before-new-labels-baselines-or-fits',records=queue,
        photos=len(queue),source_refs=[dict(path=str(FRESH),sha256=sha(FRESH)),dict(path=str(C/'INPUTS.json'),sha256=sha(C/'INPUTS.json'))]))
    save(D/'PLAN.json',dict(status='expanded-definition-annotation-qualification-only',task_definition_sha256=sha(D/'TASK_DEFINITION.json'),queue_sha256=sha(D/'REVIEW_QUEUE.json'),
        matrix=dict(fresh_train=60,fresh_val=32,fresh_test=32,old_train_replay=64,old_validation=135),
        source_roles_fixed=True,photos_not_replaced_based_on_model_outcomes=True,
        baseline_order='Freeze new complete labels and rights/scene evidence first; no expanded-task model baseline or fitting yet.',
        development_history='Old validation and TRAIN scores are known from narrow-v1 experiments. This is a task-definition revision, not a new independent fresh cohort or literal preregistration.',
        TEST_policy='No TEST prediction use. Original test role remains isolated. Label review under the new frozen ontology is not model scoring; do not use TEST labels for training/selection.',
        admission='No approved_for_training release until completeness/absence/source/rights/scene/role checks pass, original minimum counts are met, and paired-scoring/retention guard compatibility is resolved.',
        minimum_counts_preserved='Fresh TRAIN>=30positive/30absent;VAL/TEST>=12positive/20absent each; prior scene/identity minima and no unknown-as-background remain. Conversion may create absent shortfalls; do not lower gates.',
        guard_policy='Keep original/current baseline models and frozen legacy metrics. Preserve both-baseline retention, unknown cap530 and other-class guards. Prepare a versioned class133 label overlay and explicitly audit any legacy guard conflict; no silent waiver or relaxed threshold.',
        fitting_policy='No further old-scope classifier/query/loss grid. Any future expanded-task comparison needs separately frozen exact data/scope/resource/account receipts before submission.',
        production_adoption=False,new_optimizer_updates=0,new_image_inference=0,new_cluster_jobs=0))
    text='''# Expanded billboard task: data revision first

The user clarified that restaurant/business identity boards count as billboards, along with hotel/restaurant promotional boards. The earlier narrow task excluded those boards. Some old “false alarms” therefore match the intended product category, and some negative labels conflict with it. This is a supervision/specification mismatch; the old numerical results remain valid only for their frozen narrow task.

TASK_DEFINITION.json freezes the broader working rule before new labels. All323 eligible photos are queued uniformly:124 fresh-role photos,64 old TRAIN replay photos,135 old validation photos. No model fitting/inference or TEST scoring is part of this stage. Human feedback sets the product scope; the image annotations remain assistant reviews, not independent human gold.

The new draft must review every photo for complete class133 labels, including positives that may contain additional identity panels. Existing narrow labels/results remain archived. Other classes remain unchanged or unknown. Dedicated business/venue/service identity panels are included; ordinary traffic regulation and operational transit displays stay excluded. Ambiguous mixed cases are recorded as unresolved rather than forced absent.

After review, count role-specific positive/absent shortfalls before preparing any acquisition. Do not lower the original minima or replace photos based on scores. Prefer unused locally available candidates with their preassigned roles/source/scene evidence if additions are necessary. No new collection or training job has been prepared or submitted.

Both original/current baseline models and historical metrics are retained. A versioned expanded-label baseline/retention plan must explicitly handle class133 semantic conflicts and keep cap530/other-class guards; this document does not waive any gate. No old model can be declared qualified by relabeling its errors.

Next step: complete the expanded-definition original-image annotation audit, because training against the previous narrow negatives would teach the wrong task.
'''
    (D/'PLAN.md').write_text(text,encoding='utf-8')
    print(json.dumps(dict(status='expanded-task-definition-and323-photo-review-queue-frozen',definition=str(D/'TASK_DEFINITION.json'),new_fits=0,new_inference=0,production_adoption=False),indent=2))
if __name__=='__main__':main()
