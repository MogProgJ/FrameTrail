"""Synthetic-only scoring/routing tests against the immutable submitted batch. No photos/models/jobs."""
import sys,runpy,unittest,copy,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;OUT=HERE.parent
PIPE=OUT/'fresh-selector-batch-20261022-v1'
namespace=runpy.run_path(str(PIPE/'local_followup.py'),run_name='synthetic_test_import')
score_role=namespace['score_role'];qualification=namespace['qualification'];choose=namespace['choose'];rank=namespace['rank']
from scoped_metrics import score,decode
from batch_guard import sha

def row(role='val',scope='complete',positive=True):
    return dict(image_id='synthetic-only',split=role,supervision='gold',width=100,height=100,scope={'133':scope},
      targets=[dict(canonical_id=133,normalized_cxcywh=[.5,.5,.4,.4])] if positive else [])
def pred(cid=133,confidence=.9):return dict(canonical_id=cid,confidence=confidence,box=[30,30,70,70])
class PostrunRules(unittest.TestCase):
    def test_unknown_predictions_are_not_false_billboards(self):
        result=score([row()],{'synthetic-only':[pred(),pred(593)]})
        self.assertEqual((result['complete_tp'],result['complete_fp'],result['unscored_predictions']),(1,0,1))
    def test_duplicate_billboard_is_false_alarm(self):
        result=score([row()],{'synthetic-only':[pred(),pred(confidence=.8)]})
        self.assertEqual((result['complete_tp'],result['complete_fp']),(1,1))
    def test_whole_absent_billboard_counts_fp(self):
        result=score([row(scope='absent',positive=False)],{'synthetic-only':[pred()]})
        self.assertEqual((result['complete_tp'],result['complete_fp']),(0,1))
    def test_partial_scope_does_not_claim_whole_photo_precision(self):
        result=score([row(scope='positive_only')],{'synthetic-only':[pred(),pred(confidence=.8)]})
        self.assertEqual((result['partial_hits'],result['complete_fp'],result['unscored_predictions']),(1,0,1))
    def test_heldout_adapter_preserves_original_roles_and_labels(self):
        rows=[row(role='test')];before=copy.deepcopy(rows)
        result=score_role(rows,{'synthetic-only':[pred()]},'test')
        self.assertEqual(rows,before);self.assertEqual(result['complete_tp'],1)
        with self.assertRaises(ValueError):score(rows,{'synthetic-only':[pred()]})
        with self.assertRaises(ValueError):score_role(rows,{'synthetic-only':[pred()]},'val')
    def test_missing_extra_and_invalid_predictions_rejected(self):
        for predictions in ({},{'synthetic-only':[],'extra':[]},{'synthetic-only':[pred(confidence=.34)]},{'synthetic-only':[pred(cid=615)]}):
            with self.subTest(predictions=predictions),self.assertRaises(ValueError):score([row()],predictions)
    def test_both_baselines_and_unknown_cap(self):
        def state(tp,fp,partial,unknown):return dict(per_class={'593':dict(complete_tp=tp,complete_fp=fp,partial_hits=partial)},metrics=dict(unscored_predictions=unknown))
        old=state(4,0,2,528);original=state(4,0,2,525);current=state(5,0,2,528)
        decision=qualification(old,dict(complete_tp=3,complete_fp=0),original,current,dict(complete_tp=0,complete_fp=0))
        self.assertFalse(decision['qualifies'])
        old=state(5,0,2,531)
        self.assertFalse(qualification(old,dict(complete_tp=3,complete_fp=0),original,current,dict(complete_tp=0,complete_fp=0))['qualifies'])
    def test_one_seed_or_partial_method_cannot_win(self):
        best=dict(index=2,step=100,fresh=dict(complete_f1=1.,complete_tp=14,complete_fp=0))
        a=dict(method='M1',seed=17,complete=True,best=best);b=dict(method='M1',seed=29,complete=True,best=None)
        self.assertIsNone(choose([a,b]));b.update(complete=False,best=best);self.assertIsNone(choose([a,b]))
    def test_global_tie_break_uses_earlier_step_then_trial_index(self):
        candidates=[dict(index=3,step=100,fresh=dict(complete_f1=.5,complete_tp=3,complete_fp=0)),dict(index=2,step=100,fresh=dict(complete_f1=.5,complete_tp=3,complete_fp=0)),dict(index=0,step=250,fresh=dict(complete_f1=.5,complete_tp=3,complete_fp=0))]
        winner=max(candidates,key=rank);self.assertEqual((winner['step'],winner['index']),(100,2))
    def test_decoder_never_emits_background_row(self):
        import torch
        logits=torch.full((1,300,616),-30.);logits[0,0,615]=30.;logits[0,0,133]=2.
        boxes=torch.tensor([.5,.5,.4,.4]).reshape(1,1,4).repeat(1,300,1)
        result=decode(dict(pred_logits=logits,pred_boxes=boxes),100,100)
        self.assertEqual([p['canonical_id'] for p in result],[133])
if __name__=='__main__':
    before=sha(PIPE/'rf-fresh-selector-v1/package-files.json');suite=unittest.defaultTestLoader.loadTestsFromTestCase(PostrunRules)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    after=sha(PIPE/'rf-fresh-selector-v1/package-files.json');assert before==after
    report=dict(status='passed' if result.wasSuccessful() else 'failed',tests=result.testsRun,synthetic_only=True,real_photos_used=0,
      model_inference=False,optimizer_updates=0,cluster_jobs_submitted=0,submitted_package_changed=False,submitted_package_seal_sha256=before)
    (HERE/'POSTRUN_RULE_TESTS.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
